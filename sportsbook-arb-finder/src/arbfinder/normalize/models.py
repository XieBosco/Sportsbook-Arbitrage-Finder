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
