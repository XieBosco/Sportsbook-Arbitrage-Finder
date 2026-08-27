"""Domain models for normalized data."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

__all__ = ["OddsUpdate", "NormalizedOddsUpdate"]

@dataclass(frozen=True)
class OddsUpdate:
    """Raw-but-structured output of a book-specific parser.
    Field names are the parser's own vocabulary — not yet canonical."""
    book_id: str                      # "bookA"
    raw_event_id: str                  # book's internal event/game ID
    raw_sport_code: str                 # book's own sport code, e.g. "SOC", "1"
    raw_league_name: str                # book's own competition string
    raw_home_team: str                    # book's own team string, unresolved
    raw_away_team: str
    raw_start_time: str                  # unparsed timestamp, book's own format/tz
    raw_market_type: str                  # book's own market label
    raw_selection: str                    # book's own outcome label, e.g. "1", "Over"
    raw_line: float | None                # spread/total line, None for moneyline
    odds_value: float | int | str         # as reported by book (raw string/number)
    odds_format: Literal["decimal", "american", "fractional"]
    captured_at: datetime                  # UTC timestamp when parser observed this — NOT book's clock


@dataclass(frozen=True)
class NormalizedOddsUpdate:
    """A fully-canonical odds update, ready for cross-book matching.

    All string fields use canonical values (resolved via alias maps).
    ``start_time`` is always tz-aware UTC.  ``odds`` is always
    in decimal format regardless of the source book's native format.
    """

    book_id: str
    book_event_id: str
    sport_key: str
    league_key: str
    home_team: str
    away_team: str
    start_time: datetime          # tz-aware UTC
    market_type: str
    selection: str
    line: float | None
    odds: float | str
    captured_at: datetime
