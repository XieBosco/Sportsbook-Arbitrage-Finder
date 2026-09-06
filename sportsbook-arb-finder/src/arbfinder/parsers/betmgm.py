"""BetMGM parser."""

import json
import logging
import re
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from arbfinder.normalization.models import OddsUpdate
from arbfinder.parsers._helpers import clean_american_odds, split_fixture_name
from arbfinder.parsers.base import BookParser
from arbfinder.parsers.unresolved_log import record_unresolved_parser_id

__all__ = ["BetMGMParser"]

logger = logging.getLogger(__name__)


def _to_float_or_none(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _clean_selection_name(name: str) -> str:
    """Remove handicap from selection name, e.g. 'Houston Astros +1.5' -> 'Houston Astros', 'Over 8.5' -> 'Over'."""
    low = name.lower()
    if low.startswith("over "):
        return "Over"
    if low.startswith("under "):
        return "Under"
    return re.sub(r"\s*[+-][\d.,]+$", "", name).strip()



class BetMGMParser(BookParser):
    """Parser for BetMGM."""

    book_name: str = "BetMGM"

    def __init__(self):
        # Global state to store reference data
        self.reference_data = {
            "events": {},  # fixtureId -> fixture name
            "markets": {},
            "selections": {},
        }

    def relevant_http_url(self, url: str) -> bool:
        """True if this HTTP response body should be fetched via getResponseBody."""
        return "fixture-view" in url

    def handle_http_body(self, url: str, body: str) -> list[OddsUpdate]:
        """Parse an HTTP response body."""
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return []

        if "fixture" in payload and "id" in payload["fixture"]:
            fixture = payload["fixture"]
            fixture_id = str(fixture["id"])
            fixture_name = fixture.get("name", {}).get("value", "Unknown Game")

            sport_obj = fixture.get("sport", {})
            sport_code = str(sport_obj.get("name", {}).get("value") or sport_obj.get("id", ""))
            
            comp_obj = fixture.get("competition", {})
            league_name = str(comp_obj.get("name", {}).get("value") or comp_obj.get("id", ""))
            
            start_time = fixture.get("startDate", "")

            if fixture_id not in self.reference_data["events"]:
                self.reference_data["events"][fixture_id] = {
                    "name": fixture_name,
                    "sport_code": sport_code,
                    "league_name": league_name,
                    "start_time": start_time,
                }

        return []

    def _resolve_fixture_meta(self, fixture_id: object) -> dict | None:
        """Look up a fixture's metadata by ID, or None if the fixture is unknown."""
        meta = self.reference_data["events"].get(str(fixture_id))
        if not meta:
            record_unresolved_parser_id(self.book_name, "fixture_id", str(fixture_id))
            return None
        return meta

    def _build_selection_updates(
        self,
        *,
        fixture_id: object,
        market_id: object = None,
        market_name: str,
        items: list[dict],
        get_name: Callable[[dict], str],
        get_raw_odds: Callable[[dict], object],
        get_attr: Callable[[dict], object],
        fallback_attr: object,
        now: datetime,
    ) -> list[OddsUpdate]:
        """Build OddsUpdate entries for a market's selections/options.

        Shared by GameUpdate ("results") and OptionMarketUpdate ("options")
        messages, which carry the same shape modulo field names.
        """
        meta = self._resolve_fixture_meta(fixture_id)
        if meta is None:
            return []
        
        home_team, away_team = split_fixture_name(meta["name"])

        updates = []
        for item in items:
            selection_name = _clean_selection_name(get_name(item))
            raw_odds = get_raw_odds(item)
            odds = clean_american_odds(raw_odds)
            if odds is None:
                continue

            attr = get_attr(item)
            if attr is None:
                attr = fallback_attr
            handicap_val = _to_float_or_none(attr)
            sel_id = str(item.get("id", ""))
            m_id = str(market_id or "")

            updates.append(
                OddsUpdate(
                    book_id=self.book_name,
                    raw_event_id=str(fixture_id),
                    raw_sport_code=meta["sport_code"],
                    raw_league_name=meta["league_name"],
                    raw_home_team=home_team,
                    raw_away_team=away_team,
                    raw_start_time=meta["start_time"],
                    raw_market_type=market_name,
                    raw_selection=selection_name,
                    raw_line=handicap_val,
                    odds_value=float(odds),
                    odds_format="american",
                    captured_at=now,
                    raw_selection_id=sel_id,
                    raw_market_id=m_id,
                )
            )

        return updates

    def _parse_game_update(self, payload: dict, now: datetime) -> list[OddsUpdate]:
        game = payload.get("game", {})
        fixture_id = payload.get("fixtureId")
        market_id = game.get("id")
        market_name = game.get("name", {}).get("value", f"Market {market_id}")
        results = game.get("results", [])

        return self._build_selection_updates(
            fixture_id=fixture_id,
            market_id=market_id,
            market_name=market_name,
            items=results,
            get_name=lambda r: r.get("name", {}).get("value", "Unknown Selection"),
            get_raw_odds=lambda r: r.get("americanOdds"),
            # Fallback to game-level attr (e.g. 3rd quarter totals handicap on game object)
            get_attr=lambda r: r.get("attr"),
            fallback_attr=game.get("attr"),
            now=now,
        )

    def _parse_option_market_update(
        self, payload: dict, now: datetime
    ) -> list[OddsUpdate]:
        option_market = payload.get("optionMarket", {})
        fixture_id = payload.get("fixtureId")
        market_id = option_market.get("id")
        market_name = option_market.get("name", {}).get("value", f"Market {market_id}")
        options = option_market.get("options", [])

        return self._build_selection_updates(
            fixture_id=fixture_id,
            market_id=market_id,
            market_name=market_name,
            items=options,
            get_name=lambda o: o.get("name", {}).get("value", "Unknown Selection"),
            get_raw_odds=lambda o: o.get("price", {}).get("americanOdds"),
            get_attr=lambda o: o.get("attr"),
            fallback_attr=option_market.get("attr"),
            now=now,
        )

    def handle_ws_frame(self, payload: str) -> list[OddsUpdate]:
        """Parse a raw WebSocket frame payload."""
        updates = []

        # see betmgm.md - BetMGM uses SignalR, which delimits messages with the ASCII record separator (\x1e)
        # MUST split by \x1e BEFORE parsing JSON
        signalr_frames = payload.split("\x1e")
        now = datetime.now(timezone.utc)

        for s_frame in signalr_frames:
            if not s_frame:
                continue

            try:
                frame_data = json.loads(s_frame)
            except json.JSONDecodeError:
                continue

            if not isinstance(frame_data, dict):
                continue

            args = frame_data.get("arguments", [])
            if not args:
                continue

            for arg in args:
                if not isinstance(arg, dict):
                    continue

                message_type = arg.get("messageType")
                msg_payload = arg.get("payload")

                if not message_type or not msg_payload:
                    continue

                if message_type == "GameUpdate":
                    updates.extend(self._parse_game_update(msg_payload, now))
                elif message_type == "OptionMarketUpdate":
                    updates.extend(self._parse_option_market_update(msg_payload, now))

        return updates
