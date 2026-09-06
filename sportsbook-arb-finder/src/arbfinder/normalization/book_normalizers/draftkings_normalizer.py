"""Concrete normalizer for DraftKings.

Handles DraftKings-specific quirks:
 • Timestamps: ISO-8601 with extra precision (``2026-08-21T00:08:08.0000000Z``)
 • Odds: American format, often as strings with unicode minus (U+2212 ``'−147'``)
 • Sport/league codes: numeric IDs (``'7'``, ``'84240'``)
 • Team names: abbreviated (``'HOU Astros'``, ``'LA Angels'``)
 • Selections: team names or ``'Over'``/``'Under'``
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from arbfinder.normalization.alias_resolver import AliasResolver
from arbfinder.normalization.base_normalizer import BaseNormalizer
from arbfinder.normalization.models import OddsUpdate, NormalizedOddsUpdate
from arbfinder.normalization.odds_math import american_to_decimal

from arbfinder.normalization.unresolved_log import record_unresolved_variable
from arbfinder.utils.deeplinks import generate_deeplink

__all__ = ["DraftKingsNormalizer"]

logger = logging.getLogger(__name__)

_MAPS_DIR = Path(__file__).resolve().parent.parent / "maps"


class DraftKingsNormalizer(BaseNormalizer):
    """Normalizer for DraftKings."""

    def __init__(self, target_odds_format: str = "decimal", target_timezone: str = "America/New_York") -> None:
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
            # DraftKings uses extended precision: 2026-08-21T00:08:08.0000000Z
            # Truncate fractional seconds beyond 6 digits for fromisoformat
            cleaned = re.sub(r"(\.\d{6})\d+", r"\1", raw)
            dt = datetime.fromisoformat(cleaned)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_american_odds(odds_value: float | int | str) -> float | None:
        """Parse DraftKings odds (may contain unicode minus U+2212)."""
        try:
            s = str(odds_value).strip().replace("\u2212", "-").replace("+", "")
            american = int(float(s))
            return american_to_decimal(american)
        except (ValueError, TypeError):
            return None

    def _classify_selection(
        self, raw_selection: str, home_team: str, away_team: str
    ) -> str | None:
        """Classify selection as home/away/over/under/draw."""
        low = raw_selection.lower()
        if low == "over":
            return "over"
        if low == "under":
            return "under"
        if low == "draw":
            return "draw"
        # Check alias resolver first
        resolved = self._selection_resolver.resolve("DraftKings", raw_selection)
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

        # Team resolution
        home_team = self._team_resolver.resolve(book_id, update.raw_home_team)
        if home_team is None:
            record_unresolved_variable(update, "home_team", update.raw_home_team)
            return None
        
        away_team = self._team_resolver.resolve(book_id, update.raw_away_team)
        if away_team is None:
            record_unresolved_variable(update, "away_team", update.raw_away_team)
            return None

        # League
        league_key = self._league_resolver.resolve(book_id, update.raw_league_name)
        if league_key is None:
            record_unresolved_variable(update, "league_key", update.raw_league_name)
            return None

        # Market type
        market_type = self._market_resolver.resolve(book_id, update.raw_market_type)
        if market_type is None:
            record_unresolved_variable(update, "market_type", update.raw_market_type)
            return None

        # Selection
        selection = self._classify_selection(
            update.raw_selection, update.raw_home_team, update.raw_away_team
        )
        if selection is None:
            record_unresolved_variable(update, "selection", update.raw_selection)
            return None

        # Start time
        start_time = self._parse_start_time(update.raw_start_time)
        if start_time is None:
            return None
        start_time = self._format_datetime(start_time)

        # Odds
        odds_decimal = self._parse_american_odds(update.odds_value)
        if odds_decimal is None:
            return None
            
        odds = self._format_odds(odds_decimal)

        line = update.raw_line

        sport_key = self._sport_resolver.resolve(book_id, update.raw_sport_code)
        if sport_key is None:
            record_unresolved_variable(update, "sport_key", update.raw_sport_code)
            return None

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
