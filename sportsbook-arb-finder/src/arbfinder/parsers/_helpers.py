"""Shared parsing helpers for sportsbook parsers.

Pure string/numeric utilities used by multiple book parsers. These are NOT
book-specific binary protocol logic — they handle common formatting concerns
like unicode-minus cleanup and fixture name splitting that every book shares.
"""

import logging
import re

__all__ = ["clean_american_odds", "split_fixture_name"]

logger = logging.getLogger(__name__)

_PITCHER_TAG_RE = re.compile(r"\s*\([^)]*\)")

# Fixture-name delimiters, in priority order, and how each orders the teams.
# (delimiter, home_is_first_part)
_FIXTURE_DELIMITERS: list[tuple[str, bool]] = [
    (" at ", False),  # "Away at Home"
    (" @ ", False),  # "Away @ Home"
    (" vs. ", True),  # "Home vs. Away"
    (" vs ", True),  # "Home vs Away"
    (" - ", True),  # "Home - Away" (fallback)
]


def strip_pitcher_tags(name: str) -> str:
    """Remove pitcher tags like '(D Rasmussen)' from baseball team names."""
    return _PITCHER_TAG_RE.sub("", name).strip()


def clean_american_odds(val: object) -> int | None:
    """Parse American odds safely handling unicode minus, strings, floats, and ints.

    Real captured odds strings from DraftKings (and potentially others) use Unicode
    MINUS SIGN (U+2212 '−'), not ASCII hyphen (U+002D '-'). int() cannot parse U+2212,
    so we normalize before conversion. Confirmed via real message8/message9 captured bytes.
    """
    if val is None:
        return None
    try:
        if isinstance(val, (int, float)):
            return int(val)
        cleaned = str(val).strip().replace("\u2212", "-").replace("+", "")
        return int(float(cleaned))
    except (ValueError, TypeError):
        return None


def split_fixture_name(fixture_name: str) -> tuple[str, str]:
    """Split fixture name into (home_team, away_team).

    Supports delimiters confirmed across real captured data from multiple books:
      ' at '  — BetMGM, Caesars (e.g. "Indiana Fever at Las Vegas Aces")
      ' @ '   — DraftKings, FanDuel
      ' vs. ' — various
      ' vs '  — various
      ' - '   — fallback
    """
    for delimiter, home_is_first_part in _FIXTURE_DELIMITERS:
        if delimiter in fixture_name:
            first, second = (p.strip() for p in fixture_name.split(delimiter, 1))
            home, away = (first, second) if home_is_first_part else (second, first)
            return strip_pitcher_tags(home), strip_pitcher_tags(away)

    unchanged = fixture_name.strip()
    return strip_pitcher_tags(unchanged), strip_pitcher_tags(unchanged)
