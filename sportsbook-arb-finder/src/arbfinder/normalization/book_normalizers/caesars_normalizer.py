"""Concrete normalizer for Caesars.

Handles Caesars-specific quirks:
 • Timestamps: ISO-8601 (``2026-07-26T17:35:00Z``)
 • Odds: **decimal** format (not American!) — e.g. ``1.95``, ``6.94``
 • Sport/league: string names (``'Baseball'``, ``'MLB'``)
 • Market types: ``'Money Line'``, ``'Run Line'``, ``'Total Runs'`` with optional ``' Live'`` suffix
 • Selections: team names or ``'Over'``/``'Under'``
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

__all__ = ["CaesarsNormalizer"]

logger = logging.getLogger(__name__)

_MAPS_DIR = Path(__file__).resolve().parent.parent / "maps"


class CaesarsNormalizer(BaseNormalizer):
    """Normalizer for Caesars."""

    def __init__(self, target_odds_format: str = "american", target_timezone: str = "America/New_York") -> None:
        super().__init__(target_odds_format, target_timezone)
        self._team_resolver = AliasResolver(_MAPS_DIR / "team_aliases.json")
        self._league_resolver = AliasResolver(_MAPS_DIR / "league_map.json")
        self._market_resolver = AliasResolver(_MAPS_DIR / "market_type_map.json")
        self._selection_resolver = AliasResolver(_MAPS_DIR / "selection_map.json")
        self._sport_resolver = AliasResolver(_MAPS_DIR / "sport_map.json")

    @staticmethod
    def _parse_start_time(raw: str) -> datetime | None:
        if not raw:
            return None
        try:
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _to_decimal_odds(odds_value: float | int | str, odds_format: str) -> float | None:
        """Caesars odds are already decimal — just validate."""
        try:
            val = float(odds_value)
            if odds_format == "decimal":
                return val
            # If somehow American, convert
            return american_to_decimal(int(val))
        except (ValueError, TypeError):
            return None

    def _classify_selection(
        self, raw_selection: str, home_team: str, away_team: str
    ) -> str | None:
        low = raw_selection.lower()
        if low == "over":
            return "over"
        if low == "under":
            return "under"
        if low == "draw":
            return "draw"
        resolved = self._selection_resolver.resolve("Caesars", raw_selection)
        if resolved:
            return resolved
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

        # Caesar ends live markets with "Live" to distinguish pre-game markets
        raw_market = update.raw_market_type
        if raw_market and raw_market.endswith(" Live"):
            raw_market = raw_market[:-5]

        market_type = self._market_resolver.resolve(book_id, raw_market)
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

        odds_decimal = self._to_decimal_odds(update.odds_value, update.odds_format)
        if odds_decimal is None:
            return None
            
        odds = self._format_odds(odds_decimal)

        line = update.raw_line

        sport_key = self._sport_resolver.resolve(book_id, update.raw_sport_code)
        if sport_key is None:
            record_unresolved_variable(update, "sport_key", update.raw_sport_code)
            return None

        captured_at = self._format_datetime(update.captured_at)

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
        )
