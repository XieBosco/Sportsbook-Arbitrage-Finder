"""Domain models for normalized data."""

from dataclasses import dataclass
from datetime import datetime

__all__ = ["OddsUpdate", "Event", "Market"]


@dataclass(frozen=True)
class OddsUpdate:
    """Represents a standardized odds update from a sportsbook."""

    book: str
    event_id: str
    home_team: str
    away_team: str
    market: str
    selection: str
    line: float | None
    price_american: int
    timestamp: datetime


@dataclass(frozen=True)
class Event:
    """Represents a sporting event."""

    canonical_key: str
    sport: str
    home_team: str
    away_team: str
    start_time: datetime


@dataclass(frozen=True)
class Market:
    """Represents a betting market for an event."""

    canonical_key: str
    event_key: str
    market_type: str
    line: float | None


# ----------------------------- TODO -----------------------------
@dataclass
class NormalizedOutcome:
    name: str              # canonical outcome name, e.g. "home", "away", "draw", "over", "under"
    odds_decimal: float
    line: float | None     # for spreads/totals; None for moneyline

@dataclass
class NormalizedMarket:
    market_type: str       # canonical: "moneyline", "spread", "total", "btts", etc.
    outcomes: list[NormalizedOutcome]
    period: str            # "full_game", "1st_half", "1st_period", etc.

@dataclass
class NormalizedEvent:
    book_id: str            # which sportsbook this came from
    book_event_id: str      # book's own internal event/game ID (raw)
    sport_key: str           # "soccer", "nfl", "tennis"...
    league_key: str          # canonical league id, e.g. "epl", "nfl"
    home_team: str            # canonical team name
    away_team: str
    start_time: datetime      # UTC, normalized
    markets: list[NormalizedMarket]
    fetched_at: datetime       # when this snapshot was captured — matters a lot for latency tracking