"""DraftKings parser."""

import base64
import json
import logging
import re
from datetime import datetime

import msgpack

from arbfinder.normalization.models import OddsUpdate
from arbfinder.parsers._helpers import split_fixture_name
from arbfinder.parsers.base import BookParser
__all__ = ["DraftKingsParser"]

logger = logging.getLogger(__name__)

# see draftkings.md §4 — core-ID fallback
# DraftKings IDs look like: 0OU85458301O850_1 (Prefix + CoreID + Handicap)
_CORE_ID_RE = re.compile(r"^0[A-Z]{2}(\d+)")

_HANDICAP_MARKET_TYPES = {
    "Spread",
    "Total",
    "Run Line",
    "Total Runs",
    "Point Spread",
    "Total Points",
}


class DraftKingsParser(BookParser):
    """Parser for DraftKings."""

    book_name: str = "DraftKings"

    def __init__(self):
        # Global state to store reference data
        self.reference_data = {
            "events": {},  # eventId -> event name
            "markets": {},  # marketId -> {eventId, name}
            "selections": {},  # selectionId -> marketId
        }

    def relevant_http_url(self, url: str) -> bool:
        """True if this HTTP response body should be fetched via getResponseBody."""
        return "/v1/markets" in url and "api/sportscontent" in url

    def handle_http_body(self, url: str, body: str) -> list[OddsUpdate]:
        """Parse an HTTP response body."""
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return []

        if "events" in payload and "markets" in payload and "selections" in payload:
            # Parse Events (Games)
            for ev in payload.get("events", []):
                self.reference_data["events"][str(ev.get("id"))] = {
                    "name": ev.get("name", "Unknown Event"),
                    "sport_code": str(ev.get("sportId", "")),
                    "league_name": str(ev.get("leagueId", "")),
                    "start_time": str(ev.get("startEventDate", "")),
                }

            # Parse Markets
            for m in payload.get("markets", []):
                m_id = str(m.get("id"))
                self.reference_data["markets"][m_id] = {
                    "eventId": str(m.get("eventId")),
                    "name": m.get("name", "Unknown Market"),
                }

            # Parse Selections
            for s in payload.get("selections", []):
                s_id = str(s.get("id"))
                self.reference_data["selections"][s_id] = str(s.get("marketId"))

        return []

    def _decode_payload(self, b64_payload: str) -> list:
        # Clean the string
        cleaned = re.sub(r"[^a-zA-Z0-9+/=]", "", b64_payload)
        # Add padding if necessary
        cleaned += "=" * ((4 - len(cleaned) % 4) % 4)

        objects = []
        try:
            raw_bytes = base64.b64decode(cleaned)
            unpacker = msgpack.Unpacker(strict_map_key=False)
            unpacker.feed(raw_bytes)
            for obj in unpacker:
                objects.append(obj)
        except Exception:
            pass
        return objects

    def _find_outcomes(self, obj: object) -> list:
        outcomes = []
        if isinstance(obj, list):
            # Check if this array matches the known outcome signature
            # [selectionId, selectionName, odds_array, ..., tags_array, marketId]
            # Example len is usually >= 7
            if (
                len(obj) >= 7
                and isinstance(obj[0], str)
                and isinstance(obj[1], str)
                and isinstance(obj[2], list)
                and (
                    isinstance(obj[-1], str) or obj[-1] is None
                )  # see draftkings.md §3 - marketId can legitimately be None
                and isinstance(obj[-2], list)
            ):
                outcomes.append(obj)

            # Traverse recursively
            for item in obj:
                outcomes.extend(self._find_outcomes(item))

        elif isinstance(obj, dict):
            for k, v in obj.items():
                outcomes.extend(self._find_outcomes(v))

        return outcomes

    def _resolve_market_type(
        self, market_meta: dict, selection_id: str, outcome: list
    ) -> str:
        """Resolve a human-readable market type, falling back to selection-ID
        prefix conventions and finally the outcome's own tags."""
        market_type = market_meta.get("name")
        if market_type:
            return market_type

        if selection_id.startswith("0ML"):
            return "Moneyline"
        if selection_id.startswith("0HC"):
            return "Spread"
        if selection_id.startswith("0OU"):
            return "Total"

        tags = outcome[-2]
        return str(tags[0]) if len(tags) > 0 else "UNKNOWN_MARKET"

    def _resolve_event(
        self, event_id: str, event_meta: dict, selection_id: str, selection_name: str
    ) -> tuple[str, dict]:
        """Resolve (event_id, event_meta) via fallback heuristics when the
        static reference dictionary doesn't have a mapping for this selection.

        HEURISTIC FALLBACK: If DraftKings created a new market/handicap on the fly,
        the ID won't be in our static dictionary. We can extract the CoreID from the
        selection ID and find a sibling selection in our dictionary to get the game,
        or otherwise fall back to matching the selection name against known games.
        """
        event_name = event_meta.get("name", "Unknown Game")
        if event_name != "Unknown Game":
            return event_id, event_meta

        core_id_match = _CORE_ID_RE.search(selection_id)
        if core_id_match:
            core_id = core_id_match.group(1)
            
            # O(1) Optimized Inference: construct the expected market_id directly
            inferred_market_id = ""
            if selection_id.startswith("0ML"):
                inferred_market_id = f"1_{core_id}"
            elif selection_id.startswith("0HC"):
                inferred_market_id = f"2_{core_id}"
            elif selection_id.startswith("0OU"):
                inferred_market_id = f"3_{core_id}"
                
            if inferred_market_id:
                fallback_meta = self.reference_data["markets"].get(inferred_market_id, {})
                fallback_event_id = fallback_meta.get("eventId", "")
                if fallback_event_id in self.reference_data["events"]:
                    event_id = fallback_event_id
                    event_meta = self.reference_data["events"][fallback_event_id]
                    event_name = event_meta.get("name", "Unknown Game")
                    # Cache it for future updates
                    self.reference_data["selections"][selection_id] = inferred_market_id
                    
            # If inference didn't work, fall back to O(N) scan of known selections
            if event_name == "Unknown Game":
                for known_sel_id, known_market_id in self.reference_data["selections"].items():
                    if core_id in known_sel_id:
                        fallback_meta = self.reference_data["markets"].get(known_market_id, {})
                        fallback_event_id = fallback_meta.get("eventId", "")
                        if fallback_event_id in self.reference_data["events"]:
                            event_id = fallback_event_id
                            event_meta = self.reference_data["events"][fallback_event_id]
                            event_name = event_meta.get("name", "Unknown Game")
                            break

        # If STILL unknown, try the string-matching heuristic for Spreads/Moneylines
        if event_name == "Unknown Game":
            for known_id, known_meta in self.reference_data["events"].items():
                known_game = known_meta.get("name", "")
                clean_selection = (
                    selection_name.replace("Over ", "").replace("Under ", "").strip()
                )
                if clean_selection and clean_selection in known_game:
                    event_meta = known_meta
                    event_id = known_id
                    break

        return event_id, event_meta

    @staticmethod
    def _resolve_handicap(market_type: str, outcome: list) -> float | None:
        if market_type in _HANDICAP_MARKET_TYPES:
            if len(outcome) > 4 and isinstance(outcome[4], (int, float)):
                return float(outcome[4])
        return None

    def handle_ws_frame(self, payload: str) -> list[OddsUpdate]:
        """Parse a raw WebSocket frame payload."""
        objects = self._decode_payload(payload)
        outcomes = self._find_outcomes(objects)
        updates = []

        if not outcomes or not self.reference_data["events"]:
            return updates

        now = datetime.now()

        for outcome in outcomes:
            selection_id = str(outcome[0])
            selection_name = str(outcome[1])
            odds_array = outcome[2]

            raw_odds = odds_array[0] if len(odds_array) > 0 else None
            if raw_odds is None:
                continue

            market_id = self.reference_data["selections"].get(selection_id, "")

            # Some updates have the market_id as the last element of the outcome array!
            if not market_id and len(outcome) > 0 and isinstance(outcome[-1], str):
                potential_market = str(outcome[-1])
                if potential_market != selection_id:
                    market_id = potential_market

            market_meta = self.reference_data["markets"].get(market_id)
            if not market_meta:
                market_meta = {}

            market_type = self._resolve_market_type(market_meta, selection_id, outcome)

            event_id = market_meta.get("eventId", "")
            event_meta = self.reference_data["events"].get(event_id, {})
            event_id, event_meta = self._resolve_event(
                event_id, event_meta, selection_id, selection_name
            )

            handicap_val = self._resolve_handicap(market_type, outcome)
            event_name = event_meta.get("name", "Unknown Game")
            if event_name == "Unknown Game":
                from arbfinder.parsers.unresolved_log import record_unresolved_parser_id
                if not market_meta:
                    record_unresolved_parser_id(self.book_name, "market_id", market_id or selection_id)
                record_unresolved_parser_id(self.book_name, "event_id", event_id or "UNKNOWN")

            home_team, away_team = split_fixture_name(event_name)

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
                    raw_selection=selection_name,
                    raw_line=handicap_val,
                    odds_value=raw_odds,
                    odds_format="american",
                    captured_at=now,
                )
            )

        return updates
