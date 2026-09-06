"""Output data structures for matched selections."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from arbfinder.matching.bucket import Bucket

__all__ = ["MatchedSelection", "MatchOutputBuilder"]


@dataclass
class MatchedSelection:
    """A fully matched selection across one or more books.

    Ready for consumption by the arbitrage-detection engine.
    """

    canonical_game_id: str
    sport_key: str
    league_key: str
    home_team: str
    away_team: str
    time_window: str
    market_type: str
    selection: str
    line: float | None
    book_odds: dict[str, float]           # book_id -> odds
    updated_at: dict[str, datetime]       # book_id -> captured_at
    start_time: datetime | None = None
    book_deeplinks: dict[str, str] = field(default_factory=dict)


class MatchOutputBuilder:
    """Converts a :class:`Bucket` into a :class:`MatchedSelection`."""

    @staticmethod
    def from_bucket(bucket: Bucket) -> MatchedSelection:
        """Build a ``MatchedSelection`` from a populated bucket."""
        book_odds: dict[str, float] = {}
        updated_at: dict[str, datetime] = {}
        book_deeplinks: dict[str, str] = {}
        start_time: datetime | None = None

        for book_id, entry in bucket.entries.items():
            book_odds[book_id] = entry.odds
            updated_at[book_id] = entry.captured_at
            if getattr(entry, "deeplink", None):
                book_deeplinks[book_id] = entry.deeplink
            if start_time is None and getattr(entry, "start_time", None) is not None:
                start_time = entry.start_time

        if start_time is None and bucket.key.time_window:
            try:
                start_time = datetime.fromisoformat(bucket.key.time_window)
            except Exception:
                pass

        return MatchedSelection(
            canonical_game_id=bucket.canonical_game_id,
            sport_key=bucket.key.sport_key,
            league_key=bucket.key.league_key,
            home_team=bucket.key.home_team,
            away_team=bucket.key.away_team,
            time_window=bucket.key.time_window,
            market_type=bucket.key.market_type,
            selection=bucket.key.selection,
            line=bucket.key.line,
            book_odds=book_odds,
            updated_at=updated_at,
            start_time=start_time,
            book_deeplinks=book_deeplinks,
        )
