"""Betano parser.

Ported from betano_scraper.py.
Handles Betano's SignalR over WebSocket protocol with LZ4-compressed JSON payloads
and intercepts the live overview HTTP reference dictionary.

Note: The fictional 'UpdateSelectionOdds' message-type check from earlier draft code
has been removed in favor of the real SignalR NewLiveOverviewDiffs LZ4 pipeline with
both selectionChanges updates (Scenario 1) and inline market injections (Scenario 2).
"""

import base64
import json
import logging
import re
from datetime import datetime

import lz4.frame

from arbfinder.normalization.models import OddsUpdate
from arbfinder.normalization.odds_math import decimal_to_american
from arbfinder.parsers._helpers import split_fixture_name
from arbfinder.parsers.base import BookParser

__all__ = ["BetanoParser"]

logger = logging.getLogger(__name__)

_LIVE_OVERVIEW_URL_RE = re.compile(
    r"danae-webapi/api/live/overview/\d+\?isInit=false&includeVirtuals=true"
)


def _build_event_dict(ev_data: dict) -> dict:
    """Build an event reference entry, resolving home/away teams from the
    two-participant list when present."""
    ev_dict = {
        "name": ev_data.get("name"),
        "sport_code": str(ev_data.get("sportId") or ev_data.get("ardSportId", "")),
        "league_name": str(ev_data.get("leagueId", "")),
        "start_time": str(ev_data.get("startTime", "")),
    }
    participants = ev_data.get("participants", [])
    if len(participants) == 2:
        t1, t2 = participants[0], participants[1]
        if t1.get("isHome"):
            ev_dict["home_team"] = t1.get("name", "")
            ev_dict["away_team"] = t2.get("name", "")
        else:
            ev_dict["home_team"] = t2.get("name", "")
            ev_dict["away_team"] = t1.get("name", "")
    return ev_dict


def _build_selection_dict(s_data: dict) -> dict:
    """Build a selection reference entry."""
    sel_dict = {"name": s_data.get("name")}
    if s_data.get("fullName") != s_data.get("name"):
        sel_dict["fullName"] = s_data.get("fullName")
    if s_data.get("handicap") is not None:
        sel_dict["handicap"] = s_data.get("handicap")
    return sel_dict


def _resolve_handicap_from_change(change: dict, sel_meta: dict) -> float | None:
    """Resolve a Scenario-1 selection change's handicap: the change's own
    handicap wins, then the selection's stored handicap, then its shortName
    (Betano sometimes encodes the handicap there, e.g. "+1.5", "-2.5")."""
    if "handicap" in change and change["handicap"] is not None:
        try:
            return float(change["handicap"])
        except (ValueError, TypeError):
            return None
    if "handicap" in sel_meta and sel_meta["handicap"] is not None:
        try:
            return float(sel_meta["handicap"])
        except (ValueError, TypeError):
            return None
    if "shortName" in sel_meta and sel_meta["shortName"]:
        try:
            return float(sel_meta["shortName"])
        except (ValueError, TypeError):
            return None
    return None


def _resolve_handicap_from_selection(sel: dict) -> float | None:
    """Resolve a Scenario-2 (inline market injection) selection's handicap:
    its own handicap field, else its shortName fallback."""
    if "handicap" in sel and sel["handicap"] is not None:
        try:
            return float(sel["handicap"])
        except (ValueError, TypeError):
            return None
    if "shortName" in sel and sel["shortName"]:
        try:
            return float(sel["shortName"])
        except (ValueError, TypeError):
            return None
    return None


class BetanoParser(BookParser):
    """Parser for Betano Sportsbook."""

    book_name: str = "Betano"

    def __init__(self):
        # Global state to store reference data
        self.reference_data: dict[str, dict] = {
            "events": {},  # eventId -> event metadata dict
            "markets": {},  # marketId -> market metadata dict
            "selections": {},  # selectionId -> selection metadata dict
        }

    def relevant_http_url(self, url: str) -> bool:
        """True if this HTTP response body should be fetched via getResponseBody.

        Matches exact live overview endpoint pattern from betano_scraper.py:
        danae-webapi/api/live/overview/<id>?isInit=false&includeVirtuals=true
        """
        return _LIVE_OVERVIEW_URL_RE.search(url) is not None

    def relevant_ws_url(self, url: str) -> bool:
        """True if this WebSocket connection's frames should be parsed."""
        # Confirmed odds WebSocket endpoint from betano.md & betano_scraper.py: wss://www.betano.ca/contenthub?platformType=1
        return "contenthub" in url

    def _register_events(self, events: object) -> None:
        if isinstance(events, dict):
            for ev_id, ev_data in events.items():
                self.reference_data["events"][str(ev_id)] = _build_event_dict(ev_data)
        elif isinstance(events, list):
            for ev_data in events:
                if isinstance(ev_data, dict) and "id" in ev_data:
                    self.reference_data["events"][str(ev_data["id"])] = (
                        _build_event_dict(ev_data)
                    )

    def _register_markets(self, markets: object) -> None:
        if isinstance(markets, dict):
            for m_id, m_data in markets.items():
                self.reference_data["markets"][str(m_id)] = {"name": m_data.get("name")}
        elif isinstance(markets, list):
            for m_data in markets:
                if isinstance(m_data, dict) and "id" in m_data:
                    self.reference_data["markets"][str(m_data["id"])] = {
                        "name": m_data.get("name")
                    }

    def _register_selections(self, selections: object) -> None:
        if isinstance(selections, dict):
            for s_id, s_data in selections.items():
                self.reference_data["selections"][str(s_id)] = _build_selection_dict(
                    s_data
                )
        elif isinstance(selections, list):
            for s_data in selections:
                if isinstance(s_data, dict) and "id" in s_data:
                    self.reference_data["selections"][str(s_data["id"])] = (
                        _build_selection_dict(s_data)
                    )

    def handle_http_body(self, url: str, body: str) -> list[OddsUpdate]:
        """Parse the reference dictionary HTTP payload."""
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, TypeError):
            return []

        data = payload.get("data", payload)
        if not isinstance(data, dict):
            return []

        self._register_events(data.get("events", {}))
        self._register_markets(data.get("markets", {}))
        self._register_selections(data.get("selections", {}))

        return []

    def _resolve_teams(self, event_id: str, event_meta: dict) -> tuple[str, str]:
        if "home_team" in event_meta and "away_team" in event_meta:
            return event_meta["home_team"], event_meta["away_team"]
        ev_name = event_meta.get("name", f"Event {event_id}")
        return split_fixture_name(ev_name)

    def _process_selection_changes(
        self,
        event_id: str,
        event_meta: dict,
        home_team: str,
        away_team: str,
        selection_changes: object,
        now: datetime,
    ) -> list[OddsUpdate]:
        """Scenario 1: selection price changes under existing markets."""
        updates = []
        if not isinstance(selection_changes, dict):
            return updates

        for market_id_str, changes in selection_changes.items():
            if not isinstance(changes, list):
                continue

            market_meta = self.reference_data["markets"].get(str(market_id_str))
            if not market_meta:
                from arbfinder.parsers.unresolved_log import record_unresolved_parser_id
                record_unresolved_parser_id(self.book_name, "market_id", str(market_id_str))
                market_meta = {}
                
            market_name = market_meta.get("name", f"Market {market_id_str}")

            for change in changes:
                if not isinstance(change, dict):
                    continue

                selection_id = str(change.get("id", ""))
                price = change.get("price")
                if price is None:
                    continue

                try:
                    american_odds = decimal_to_american(float(price))
                except (ValueError, TypeError, ZeroDivisionError):
                    continue

                sel_meta = self.reference_data["selections"].get(selection_id)
                if not sel_meta:
                    from arbfinder.parsers.unresolved_log import record_unresolved_parser_id
                    record_unresolved_parser_id(self.book_name, "selection_id", selection_id)
                    sel_meta = {}
                    
                sel_name = sel_meta.get(
                    "fullName", sel_meta.get("name", f"Selection {selection_id}")
                )
                handicap_val = _resolve_handicap_from_change(change, sel_meta)

                updates.append(
                    OddsUpdate(
                        book_id=self.book_name,
                        raw_event_id=event_id,
                        raw_sport_code=event_meta.get("sport_code", ""),
                        raw_league_name=event_meta.get("league_name", ""),
                        raw_home_team=home_team,
                        raw_away_team=away_team,
                        raw_start_time=event_meta.get("start_time", ""),
                        raw_market_type=market_name,
                        raw_selection=sel_name,
                        raw_line=handicap_val,
                        odds_value=float(american_odds),
                        odds_format="american",
                        captured_at=now,
                    )
                )

        return updates

    def _process_new_market(
        self,
        event_id: str,
        event_meta: dict,
        home_team: str,
        away_team: str,
        new_market: object,
        now: datetime,
    ) -> list[OddsUpdate]:
        """Scenario 2: new inline market injection."""
        updates = []
        if not isinstance(new_market, dict):
            return updates

        market_id_str = str(new_market.get("id", ""))
        market_name = new_market.get("name", f"Market {market_id_str}")
        self.reference_data["markets"][market_id_str] = {"name": new_market.get("name")}

        for sel in new_market.get("selections", []):
            if not isinstance(sel, dict):
                continue

            selection_id = str(sel.get("id", ""))
            price = sel.get("price")
            if price is None:
                continue

            try:
                american_odds = decimal_to_american(float(price))
            except (ValueError, TypeError, ZeroDivisionError):
                continue

            sel_name = sel.get("fullName", sel.get("name", f"Selection {selection_id}"))
            self.reference_data["selections"][selection_id] = _build_selection_dict(sel)
            handicap_val = _resolve_handicap_from_selection(sel)

            updates.append(
                OddsUpdate(
                    book_id=self.book_name,
                    raw_event_id=event_id,
                    raw_sport_code=event_meta.get("sport_code", ""),
                    raw_league_name=event_meta.get("league_name", ""),
                    raw_home_team=home_team,
                    raw_away_team=away_team,
                    raw_start_time=event_meta.get("start_time", ""),
                    raw_market_type=market_name,
                    raw_selection=sel_name,
                    raw_line=handicap_val,
                    odds_value=float(american_odds),
                    odds_format="american",
                    captured_at=now,
                )
            )

        return updates

    def _process_diff_item(self, item: object, now: datetime) -> list[OddsUpdate]:
        if not isinstance(item, dict):
            return []

        event_id = str(item.get("eventId", ""))
        payload_data = item.get("payload", {})
        if not isinstance(payload_data, dict):
            return []

        # Note on Betano live event registration:
        # Betano's live WS stream can push full event definitions (type 1 with participants/url/sport,
        # e.g., betano_message2.json / betano_message3.json). When participants/event metadata arrives
        # mid-session in payload_data, we dynamically register/update self.reference_data["events"]
        # so subsequent updates can resolve home/away team names even without an HTTP refresh.
        if "participants" in payload_data:
            self.reference_data["events"][event_id] = _build_event_dict(payload_data)

        event_meta = self.reference_data["events"].get(event_id)
        if not event_meta and event_id:
            from arbfinder.parsers.unresolved_log import record_unresolved_parser_id
            record_unresolved_parser_id(self.book_name, "event_id", event_id)
            event_meta = {}
        elif not event_meta:
            event_meta = {}
        home_team, away_team = self._resolve_teams(event_id, event_meta)

        updates = []
        updates.extend(
            self._process_selection_changes(
                event_id,
                event_meta,
                home_team,
                away_team,
                payload_data.get("selectionChanges", {}),
                now,
            )
        )
        updates.extend(
            self._process_new_market(
                event_id, event_meta, home_team, away_team, payload_data.get("market"), now
            )
        )
        return updates

    def handle_ws_frame(self, payload: str) -> list[OddsUpdate]:
        """Parse a WebSocket frame payload from Betano.

        Ported from betano_scraper.py. Uses raw substring pre-filter for
        'NewLiveOverviewDiffs' on the frame, splits on SignalR record separator '\x1e',
        and decompresses Base64 LZ4 frames in arguments[0].
        """
        if not payload or "NewLiveOverviewDiffs" not in payload:
            return []

        updates: list[OddsUpdate] = []
        now = datetime.now()

        # SignalR messages are delimited by the ASCII record separator (\x1e)
        for segment in payload.split("\x1e"):
            segment = segment.strip()
            if not segment:
                continue

            try:
                msg = json.loads(segment)
            except json.JSONDecodeError:
                continue

            args = msg.get("arguments", [])
            if not args or not isinstance(args[0], str):
                continue

            b64_payload = args[0]
            try:
                compressed_bytes = base64.b64decode(b64_payload)
                decompressed_bytes = lz4.frame.decompress(compressed_bytes)
                diff_data = json.loads(decompressed_bytes.decode("utf-8"))
            except Exception:
                logger.debug("Betano: failed to decompress LZ4 frame, skipping segment")
                continue

            if not isinstance(diff_data, list):
                continue

            for item in diff_data:
                updates.extend(self._process_diff_item(item, now))

        return updates
