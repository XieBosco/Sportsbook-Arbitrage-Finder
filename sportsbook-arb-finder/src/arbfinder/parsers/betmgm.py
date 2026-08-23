"""BetMGM parser."""

import json
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from arbfinder.normalize.models import OddsUpdate
from arbfinder.parsers._helpers import clean_american_odds, split_fixture_name
from arbfinder.parsers.base import BookParser

__all__ = ["BetMGMParser"]

logger = logging.getLogger(__name__)


def _to_float_or_none(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


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

            if fixture_id not in self.reference_data["events"]:
                self.reference_data["events"][fixture_id] = fixture_name

        return []

    def _resolve_fixture_teams(self, fixture_id: object) -> tuple[str, str] | None:
        """Look up a fixture's teams by ID, or None if the fixture is unknown."""
        fixture_name = self.reference_data["events"].get(str(fixture_id), "Unknown Game")
        if fixture_name == "Unknown Game":
            return None
        return split_fixture_name(fixture_name)

    def _build_selection_updates(
        self,
        *,
        fixture_id: object,
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
        teams = self._resolve_fixture_teams(fixture_id)
        if teams is None:
            return []
        home_team, away_team = teams

        updates = []
        for item in items:
            selection_name = get_name(item)
            odds = clean_american_odds(get_raw_odds(item))
            if odds is None:
                continue

            attr = get_attr(item)
            if attr is None:
                attr = fallback_attr
            handicap_val = _to_float_or_none(attr)

            updates.append(
                OddsUpdate(
                    book=self.book_name,
                    event_id=str(fixture_id),
                    home_team=home_team,
                    away_team=away_team,
                    market=market_name,
                    selection=selection_name,
                    line=handicap_val,
                    price_american=odds,
                    timestamp=now,
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
        now = datetime.now()

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
