"""BetMGM parser."""

import json
import logging
from datetime import datetime

from arbfinder.normalize.models import OddsUpdate
from arbfinder.parsers._helpers import clean_american_odds, split_fixture_name
from arbfinder.parsers.base import BookParser

__all__ = ["BetMGMParser"]

logger = logging.getLogger(__name__)


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

    # _clean_american_odds and _split_fixture_name extracted to parsers/_helpers.py

    def _parse_game_update(self, payload: dict, now: datetime) -> list[OddsUpdate]:
        updates = []
        game = payload.get("game", {})
        fixture_id = payload.get("fixtureId")
        market_id = game.get("id")
        market_name = game.get("name", {}).get("value", f"Market {market_id}")
        results = game.get("results", [])

        fixture_name = self.reference_data["events"].get(
            str(fixture_id), "Unknown Game"
        )

        if fixture_name == "Unknown Game":
            return updates

        home_team, away_team = split_fixture_name(fixture_name)

        for result in results:
            selection_name = result.get("name", {}).get("value", "Unknown Selection")
            raw_odds = result.get("americanOdds")
            odds = clean_american_odds(raw_odds)

            if odds is None:
                continue

            # Fallback to game-level attr (e.g. 3rd quarter totals handicap on game object)
            attr = (
                result.get("attr")
                if result.get("attr") is not None
                else game.get("attr")
            )
            handicap_val = None
            if attr is not None:
                try:
                    handicap_val = float(attr)
                except (ValueError, TypeError):
                    pass

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

    def _parse_option_market_update(
        self, payload: dict, now: datetime
    ) -> list[OddsUpdate]:
        updates = []
        option_market = payload.get("optionMarket", {})
        fixture_id = payload.get("fixtureId")
        market_id = option_market.get("id")
        market_name = option_market.get("name", {}).get("value", f"Market {market_id}")
        options = option_market.get("options", [])

        fixture_name = self.reference_data["events"].get(
            str(fixture_id), "Unknown Game"
        )

        if fixture_name == "Unknown Game":
            return updates

        home_team, away_team = split_fixture_name(fixture_name)

        for option in options:
            selection_name = option.get("name", {}).get("value", "Unknown Selection")
            price = option.get("price", {})
            raw_odds = price.get("americanOdds")
            odds = clean_american_odds(raw_odds)

            if odds is None:
                continue

            attr = option.get("attr") if option.get("attr") is not None else option_market.get("attr")
            handicap_val = None
            if attr is not None:
                try:
                    handicap_val = float(attr)
                except (ValueError, TypeError):
                    pass

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
