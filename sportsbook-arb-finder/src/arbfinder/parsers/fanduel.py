"""FanDuel parser."""

import json
import logging
from datetime import datetime

from arbfinder.normalization.models import OddsUpdate
from arbfinder.parsers._helpers import split_fixture_name
from arbfinder.parsers.base import BookParser

__all__ = ["FanDuelParser"]

logger = logging.getLogger(__name__)


def _extract_raw_american_odds(runner: dict) -> object:
    """Dig a runner's raw American odds out of winRunnerOdds, preferring the
    display odds and falling back to trueOdds (see fanduel.md §4.2)."""
    win_odds = runner.get("winRunnerOdds", {})
    if not isinstance(win_odds, dict):
        return None

    odds = None
    american = win_odds.get("americanDisplayOdds", {})
    if isinstance(american, dict):
        odds = american.get("americanOdds")

    if odds is None:
        true_odds = win_odds.get("trueOdds", {})
        if isinstance(true_odds, dict):
            odds = true_odds.get("americanOdds")

    return odds


class FanDuelParser(BookParser):
    """Parser for FanDuel."""

    book_name: str = "FanDuel"

    def __init__(self):
        # Global state to store reference data
        self.reference_data = {
            "events": {},  # eventId -> event name
            "markets": {},  # marketId -> market metadata
            "selections": {},  # marketId_selectionId -> runner metadata
        }

    def relevant_http_url(self, url: str) -> bool:
        """True if this HTTP response body should be fetched via getResponseBody."""
        return "content-managed-page" in url or "getMarketPrices" in url

    def _find_markets(self, obj: object) -> list:
        markets = []
        if isinstance(obj, dict):
            if "marketId" in obj and "runnerDetails" in obj:
                markets.append(obj)
            for k, v in obj.items():
                markets.extend(self._find_markets(v))
        elif isinstance(obj, list):
            for item in obj:
                markets.extend(self._find_markets(item))
        return markets

    def _register_reference_data(self, attachments: dict) -> None:
        """Parse the events/markets/runners reference dictionary."""
        events = attachments.get("events", {})
        for ev_id, ev_data in events.items():
            self.reference_data["events"][str(ev_id)] = {
                "name": ev_data.get("name", "Unknown Event"),
                "sport_code": str(ev_data.get("eventTypeId", "")),
                "league_name": str(ev_data.get("competitionId", "")),
                "start_time": str(ev_data.get("openDate", "")),
            }

        markets = attachments.get("markets", {})
        for m_id, m_data in markets.items():
            self.reference_data["markets"][str(m_id)] = {
                "eventId": str(m_data.get("eventId")),
                "marketName": m_data.get("marketName", ""),
                "marketType": m_data.get("marketType", ""),
            }

            for runner in m_data.get("runners", []):
                s_id = str(runner.get("selectionId"))
                r_name = runner.get("runnerName", "Unknown")
                handicap = runner.get("handicap", 0)

                self.reference_data["selections"][f"{m_id}_{s_id}"] = {
                    "name": r_name,
                    "handicap": handicap,
                }

    def _parse_live_odds(self, payload: dict, now: datetime) -> list[OddsUpdate]:
        markets = self._find_markets(payload)
        updates = []

        if not markets or not self.reference_data["events"]:
            return updates

        for market in markets:
            m_id = str(market.get("marketId"))

            # Lookup metadata from the reference dictionary
            market_meta = self.reference_data["markets"].get(m_id)
            if not market_meta:
                from arbfinder.parsers.unresolved_log import record_unresolved_parser_id
                record_unresolved_parser_id(self.book_name, "market_id", m_id)
                market_meta = {}
            
            event_id = market_meta.get("eventId", "")
            event_meta = self.reference_data["events"].get(event_id)
            if not event_meta and event_id:
                from arbfinder.parsers.unresolved_log import record_unresolved_parser_id
                record_unresolved_parser_id(self.book_name, "event_id", event_id)
                event_meta = {}
            elif not event_meta:
                event_meta = {}

            event_name = event_meta.get("name", "Unknown Game")
            market_type = market_meta.get("marketType", "UNKNOWN_MARKET")

            # Skip if event is unknown
            if event_name == "Unknown Game":
                continue

            home_team, away_team = split_fixture_name(event_name)

            for runner in market.get("runnerDetails", []):
                s_id = str(runner.get("selectionId"))

                raw_odds = _extract_raw_american_odds(runner)
                if raw_odds is None:
                    continue

                # Lookup Selection metadata
                sel_meta = self.reference_data["selections"].get(f"{m_id}_{s_id}")
                if not sel_meta:
                    from arbfinder.parsers.unresolved_log import record_unresolved_parser_id
                    record_unresolved_parser_id(self.book_name, "selection_id", f"{m_id}_{s_id}")
                    sel_meta = {}
                
                runner_name = sel_meta.get("name", f"Selection {s_id}")
                
                # Use live handicap if available, otherwise fall back to cached
                handicap = runner.get("handicap", sel_meta.get("handicap", 0))

                handicap_val = None if handicap == 0 else float(handicap)

                updates.append(
                    OddsUpdate(
                        book_id=self.book_name,
                        raw_event_id=event_id,
                        raw_sport_code=event_meta.get("sport_code", ""),
                        raw_league_name=event_meta.get("league_name", ""),
                        raw_home_team=home_team,
                        raw_away_team=away_team,
                        raw_start_time=event_meta.get("start_time", ""),
                        raw_market_type=market_type,
                        raw_selection=runner_name,
                        raw_line=handicap_val,
                        odds_value=raw_odds,
                        odds_format="american",
                        captured_at=now,
                    )
                )

        return updates

    def handle_http_body(self, url: str, body: str) -> list[OddsUpdate]:
        """Parse an HTTP response body."""
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return []

        # --- PARSE REFERENCE DICTIONARY ---
        if "attachments" in payload and "markets" in payload["attachments"]:
            self._register_reference_data(payload["attachments"])
            return []

        # --- PARSE LIVE ODDS UPDATE ---
        return self._parse_live_odds(payload, datetime.now())

    def handle_ws_frame(self, payload: str) -> list[OddsUpdate]:
        """FanDuel uses long-polling HTTP requests for updates, no WebSocket odds."""
        return []
