"""Bucket data structures for cross-book matching."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from arbfinder.normalization.models import NormalizedOddsUpdate

__all__ = ["BucketKey", "Bucket", "compute_time_window"]


def compute_time_window(dt: datetime) -> str:
    """Floor *dt* to the nearest 15-minute UTC boundary and return as ISO string.

    The result is always tz-aware UTC, formatted as
    ``"YYYY-MM-DDTHH:MM:00+00:00"``.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    floored_minute = (dt.minute // 15) * 15
    floored = dt.replace(minute=floored_minute, second=0, microsecond=0)
    return floored.isoformat()


@dataclass(frozen=True)
class BucketKey:
    """Immutable composite key that uniquely identifies a matchable selection.

    Two ``NormalizedOddsUpdate`` objects from different books should
    produce the same ``BucketKey`` if they refer to the same game,
    market, selection, and line (within the same 15-minute time window).
    """

    sport_key: str
    league_key: str
    time_window: str          # ISO string — start_time floored to 15 min
    home_team: str
    away_team: str
    market_type: str
    selection: str
    line: float | None


@dataclass
class Bucket:
    """Mutable container that aggregates odds from multiple books for one
    matchable selection.
    """

    key: BucketKey
    canonical_game_id: str # internally generated UUID
    entries: dict[str, NormalizedOddsUpdate] = field(default_factory=dict) # entries_key: str = book_id (e.g., "draftkings", "fanduel")
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
