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

from arbfinder.normalize.models import OddsUpdate
from arbfinder.normalize.odds_math import decimal_to_american
from arbfinder.parsers._helpers import split_fixture_name
from arbfinder.parsers.base import BookParser

__all__ = ["BetanoParser"]

logger = logging.getLogger(__name__)


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
        return (
            re.search(
                r"danae-webapi/api/live/overview/\d+\?isInit=false&includeVirtuals=true",
                url,
            )
            is not None
        )

    def relevant_ws_url(self, url: str) -> bool:
        """True if this WebSocket connection's frames should be parsed."""
        # Confirmed odds WebSocket endpoint from betano.md & betano_scraper.py: wss://www.betano.ca/contenthub?platformType=1
        return "contenthub" in url

    def handle_http_body(self, url: str, body: str) -> list[OddsUpdate]:
        """Parse the reference dictionary HTTP payload."""
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, TypeError):
            return []

        data = payload.get("data", payload)
        if not isinstance(data, dict):
            return []

        # Parse Events
        events = data.get("events", {})
        if isinstance(events, dict):
            for ev_id, ev_data in events.items():
                ev_dict = {"name": ev_data.get("name")}
                participants = ev_data.get("participants", [])
                if len(participants) == 2:
                    t1, t2 = participants[0], participants[1]
                    if t1.get("isHome"):
                        ev_dict["home_team"] = t1.get("name", "")
                        ev_dict["away_team"] = t2.get("name", "")
                    else:
                        ev_dict["home_team"] = t2.get("name", "")
                        ev_dict["away_team"] = t1.get("name", "")
                self.reference_data["events"][str(ev_id)] = ev_dict
        elif isinstance(events, list):
            for ev_data in events:
                if isinstance(ev_data, dict) and "id" in ev_data:
                    ev_dict = {"name": ev_data.get("name")}
                    participants = ev_data.get("participants", [])
                    if len(participants) == 2:
                        t1, t2 = participants[0], participants[1]
                        if t1.get("isHome"):
                            ev_dict["home_team"] = t1.get("name", "")
                            ev_dict["away_team"] = t2.get("name", "")
                        else:
                            ev_dict["home_team"] = t2.get("name", "")
                            ev_dict["away_team"] = t1.get("name", "")
                    self.reference_data["events"][str(ev_data["id"])] = ev_dict

        # Parse Markets
        markets = data.get("markets", {})
        if isinstance(markets, dict):
            for m_id, m_data in markets.items():
                self.reference_data["markets"][str(m_id)] = {
                    "name": m_data.get("name")
                }
        elif isinstance(markets, list):
            for m_data in markets:
                if isinstance(m_data, dict) and "id" in m_data:
                    self.reference_data["markets"][str(m_data["id"])] = {
                        "name": m_data.get("name")
                    }

        # Parse Selections
        selections = data.get("selections", {})
        if isinstance(selections, dict):
            for s_id, s_data in selections.items():
                sel_dict = {"name": s_data.get("name")}
                if s_data.get("fullName") != s_data.get("name"):
                    sel_dict["fullName"] = s_data.get("fullName")
                if s_data.get("handicap") is not None:
                    sel_dict["handicap"] = s_data.get("handicap")
                self.reference_data["selections"][str(s_id)] = sel_dict
        elif isinstance(selections, list):
            for s_data in selections:
                if isinstance(s_data, dict) and "id" in s_data:
                    sel_dict = {"name": s_data.get("name")}
                    if s_data.get("fullName") != s_data.get("name"):
                        sel_dict["fullName"] = s_data.get("fullName")
                    if s_data.get("handicap") is not None:
                        sel_dict["handicap"] = s_data.get("handicap")
                    self.reference_data["selections"][str(s_data["id"])] = sel_dict

        return []

    # _split_fixture_name extracted to parsers/_helpers.py

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
                if not isinstance(item, dict):
                    continue

                event_id = str(item.get("eventId", ""))
                payload_data = item.get("payload", {})
                if not isinstance(payload_data, dict):
                    continue

                # Note on Betano live event registration:
                # Betano's live WS stream can push full event definitions (type 1 with participants/url/sport,
                # e.g., betano_message2.json / betano_message3.json). When participants/event metadata arrives
                # mid-session in payload_data, we dynamically register/update self.reference_data["events"]
                # so subsequent updates can resolve home/away team names even without an HTTP refresh.
                if "participants" in payload_data:
                    ev_dict = {"name": payload_data.get("name")}
                    participants = payload_data.get("participants", [])
                    if len(participants) == 2:
                        t1, t2 = participants[0], participants[1]
                        if t1.get("isHome"):
                            ev_dict["home_team"] = t1.get("name", "")
                            ev_dict["away_team"] = t2.get("name", "")
                        else:
                            ev_dict["home_team"] = t2.get("name", "")
                            ev_dict["away_team"] = t1.get("name", "")
                    self.reference_data["events"][event_id] = ev_dict

                event_meta = self.reference_data["events"].get(event_id, {})

                # Team resolution natively from pre-parsed reference_data
                if "home_team" in event_meta and "away_team" in event_meta:
                    home_team = event_meta["home_team"]
                    away_team = event_meta["away_team"]
                else:
                    ev_name = event_meta.get("name", f"Event {event_id}")
                    home_team, away_team = split_fixture_name(ev_name)

                # ── Scenario 1: Selection price changes under existing markets ──
                selection_changes = payload_data.get("selectionChanges", {})
                if isinstance(selection_changes, dict):
                    for market_id_str, changes in selection_changes.items():
                        if not isinstance(changes, list):
                            continue

                        market_meta = self.reference_data["markets"].get(
                            str(market_id_str), {}
                        )
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

                            sel_meta = self.reference_data["selections"].get(
                                selection_id, {}
                            )
                            sel_name = sel_meta.get(
                                "fullName",
                                sel_meta.get("name", f"Selection {selection_id}"),
                            )

                            handicap_val = None
                            if "handicap" in change and change["handicap"] is not None:
                                try:
                                    handicap_val = float(change["handicap"])
                                except (ValueError, TypeError):
                                    pass
                            elif (
                                "handicap" in sel_meta
                                and sel_meta["handicap"] is not None
                            ):
                                try:
                                    handicap_val = float(sel_meta["handicap"])
                                except (ValueError, TypeError):
                                    pass
                            elif "shortName" in sel_meta and sel_meta["shortName"]:
                                # Ported from betano_scraper.py: sometimes handicap is stored in shortName e.g. "+1.5", "-2.5"
                                try:
                                    handicap_val = float(sel_meta["shortName"])
                                except (ValueError, TypeError):
                                    pass

                            updates.append(
                                OddsUpdate(
                                    book=self.book_name,
                                    event_id=event_id,
                                    home_team=home_team,
                                    away_team=away_team,
                                    market=market_name,
                                    selection=sel_name,
                                    line=handicap_val,
                                    price_american=american_odds,
                                    timestamp=now,
                                )
                            )

                # ── Scenario 2: New inline market injection ──
                new_market = payload_data.get("market")
                if isinstance(new_market, dict):
                    market_id_str = str(new_market.get("id", ""))
                    market_name = new_market.get("name", f"Market {market_id_str}")
                    self.reference_data["markets"][market_id_str] = {
                        "name": new_market.get("name")
                    }

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

                        sel_name = sel.get(
                            "fullName", sel.get("name", f"Selection {selection_id}")
                        )
                        sel_dict = {"name": sel.get("name")}
                        if sel.get("fullName") != sel.get("name"):
                            sel_dict["fullName"] = sel.get("fullName")
                        if sel.get("handicap") is not None:
                            sel_dict["handicap"] = sel.get("handicap")
                        self.reference_data["selections"][selection_id] = sel_dict

                        handicap_val = None
                        if "handicap" in sel and sel["handicap"] is not None:
                            try:
                                handicap_val = float(sel["handicap"])
                            except (ValueError, TypeError):
                                pass
                        elif "shortName" in sel and sel["shortName"]:
                            # Ported from betano_scraper.py: shortName fallback
                            try:
                                handicap_val = float(sel["shortName"])
                            except (ValueError, TypeError):
                                pass

                        updates.append(
                            OddsUpdate(
                                book=self.book_name,
                                event_id=event_id,
                                home_team=home_team,
                                away_team=away_team,
                                market=market_name,
                                selection=sel_name,
                                line=handicap_val,
                                price_american=american_odds,
                                timestamp=now,
                            )
                        )

        return updates
