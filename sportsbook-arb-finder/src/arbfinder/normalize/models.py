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