"""Output data structures for matched selections."""

from __future__ import annotations

from dataclasses import dataclass
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
    market_type: str
    selection: str
    line: float | None
    book_odds: dict[str, float]           # book_id -> odds
    updated_at: dict[str, datetime]       # book_id -> captured_at


class MatchOutputBuilder:
    """Converts a :class:`Bucket` into a :class:`MatchedSelection`."""

    @staticmethod
    def from_bucket(bucket: Bucket) -> MatchedSelection:
        """Build a ``MatchedSelection`` from a populated bucket."""
        book_odds: dict[str, float] = {}
        updated_at: dict[str, datetime] = {}
        for book_id, entry in bucket.entries.items():
            book_odds[book_id] = entry.odds
            updated_at[book_id] = entry.captured_at

        return MatchedSelection(
            canonical_game_id=bucket.canonical_game_id,
            sport_key=bucket.key.sport_key,
            league_key=bucket.key.league_key,
            home_team=bucket.key.home_team,
            away_team=bucket.key.away_team,
            market_type=bucket.key.market_type,
            selection=bucket.key.selection,
            line=bucket.key.line,
            book_odds=book_odds,
            updated_at=updated_at,
        )
