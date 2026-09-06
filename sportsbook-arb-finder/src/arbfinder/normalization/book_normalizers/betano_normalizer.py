"""Concrete normalizer for Betano.

Handles Betano-specific quirks:
 • Timestamps: **epoch milliseconds** (``'1787275500000'``)
 • Odds: American floats (e.g. ``-250.0``, ``170.0``)
 • Sport codes: short strings (``'TENN'``, ``'BASE'``, ``'BASK'``, ``'FOOT'``, ``'AMFO'``)
 • League IDs: numeric strings (``'205093'``)
 • Selections: team names, ``'Over'``/``'Under'``, or European-style ``'1'``/``'X'``/``'2'``/``'1X'``/``'12'``/``'X2'``
 • Market types: ``'Winner'``, ``'Total'``, ``'Spread'``, ``'Both Teams to Score'``, etc.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from arbfinder.normalization.alias_resolver import AliasResolver
from arbfinder.normalization.base_normalizer import BaseNormalizer
from arbfinder.normalization.models import OddsUpdate, NormalizedOddsUpdate
from arbfinder.normalization.odds_math import american_to_decimal

from arbfinder.normalization.unresolved_log import record_unresolved_variable
from arbfinder.utils.deeplinks import generate_deeplink

__all__ = ["BetanoNormalizer"]

logger = logging.getLogger(__name__)

_MAPS_DIR = Path(__file__).resolve().parent.parent / "maps"


class BetanoNormalizer(BaseNormalizer):
    """Normalizer for Betano."""

    def __init__(self, target_odds_format: str = "decimal", target_timezone: str = "America/New_York") -> None:
        super().__init__(target_odds_format, target_timezone)
        self._team_resolver = AliasResolver(_MAPS_DIR / "team_aliases.json")
        self._league_resolver = AliasResolver(_MAPS_DIR / "league_map.json")
        self._market_resolver = AliasResolver(_MAPS_DIR / "market_type_map.json")
        self._selection_resolver = AliasResolver(_MAPS_DIR / "selection_map.json")
        self._sport_resolver = AliasResolver(_MAPS_DIR / "sport_map.json")

    @staticmethod
    def _parse_start_time(raw: str) -> datetime | None:
        """Betano timestamps are epoch milliseconds."""
        if not raw:
            return None
        try:
            # Try epoch ms first
            epoch_ms = int(raw)
            return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
        except (ValueError, OverflowError):
            pass
        # Fallback to ISO
        try:
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_odds(odds_value: float | int | str) -> float | None:
        try:
            val = float(odds_value)
            if 1.0 < val < 100:
                return val
            return american_to_decimal(int(val))
        except (ValueError, TypeError):
            return None

    def _classify_selection(
        self, raw_selection: str, home_team: str, away_team: str
    ) -> str | None:
        # Check alias resolver
        resolved = self._selection_resolver.resolve("Betano", raw_selection)
        if resolved:
            return resolved

        # Match against team names
        if raw_selection == home_team:
            return "home"
        if raw_selection == away_team:
            return "away"

        return None

    def normalize(self, update: OddsUpdate) -> NormalizedOddsUpdate | None:
        book_id = update.book_id

        home_team = self._team_resolver.resolve(book_id, update.raw_home_team)
        if home_team is None:
            record_unresolved_variable(update, "home_team", update.raw_home_team)
            return None
            
        away_team = self._team_resolver.resolve(book_id, update.raw_away_team)
        if away_team is None:
            record_unresolved_variable(update, "away_team", update.raw_away_team)
            return None

        league_key = self._league_resolver.resolve(book_id, update.raw_league_name)
        if league_key is None:
            record_unresolved_variable(update, "league_key", update.raw_league_name)
            return None

        sport_key = self._sport_resolver.resolve(book_id, update.raw_sport_code)
        if sport_key is None:
            record_unresolved_variable(update, "sport_key", update.raw_sport_code)
            return None

        market_type = self._market_resolver.resolve(book_id, update.raw_market_type)
        if market_type is None:
            record_unresolved_variable(update, "market_type", update.raw_market_type)
            return None

        selection = self._classify_selection(
            update.raw_selection, update.raw_home_team, update.raw_away_team
        )
        if selection is None:
            record_unresolved_variable(update, "selection", update.raw_selection)
            return None

        start_time = self._parse_start_time(update.raw_start_time)
        if start_time is None:
            return None
        start_time = self._format_datetime(start_time)

        odds_decimal = self._parse_odds(update.odds_value)
        if odds_decimal is None:
            return None
            
        odds = self._format_odds(odds_decimal)

        line = update.raw_line

        captured_at = self._format_datetime(update.captured_at)
        deeplink = generate_deeplink(
            book_id=book_id,
            selection_id=update.raw_selection_id,
            market_id=update.raw_market_id,
            event_id=update.raw_event_id,
            home_team=home_team,
            away_team=away_team,
        )

        return NormalizedOddsUpdate(
            book_id=book_id,
            book_event_id=update.raw_event_id,
            sport_key=sport_key,
            league_key=league_key,
            home_team=home_team,
            away_team=away_team,
            start_time=start_time,
            market_type=market_type,
            selection=selection,
            line=line,
            odds=odds,
            captured_at=captured_at,
            deeplink=deeplink,
        )
