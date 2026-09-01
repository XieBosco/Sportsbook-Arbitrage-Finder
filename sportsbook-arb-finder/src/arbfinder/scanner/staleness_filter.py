"""Staleness filter — rejects selections with outdated odds."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from arbfinder.matching.output import MatchedSelection

__all__ = ["StalenessFilter"]


class StalenessFilter:
    """Filters a :class:`MatchedSelection` by removing any books whose
    timestamps are older than *max_age_seconds*.

    Returns a new :class:`MatchedSelection` with only the fresh books,
    or ``None`` if no fresh books remain.

    This guards against silently disconnected feeds (dead websocket /
    backgrounded browser tab) and suspended markets whose last-known
    price is stale but still present in the bucket — both produce
    phantom arbitrage if not filtered.
    """

    def __init__(self, max_age_seconds: float) -> None:
        self._max_age = timedelta(seconds=max_age_seconds)

    def filter_stale_books(self, matched: MatchedSelection, now: datetime) -> MatchedSelection | None:
        """Return a copy of *matched* containing only fresh books, or None if empty."""
        if not matched.updated_at:
            return None
            
        # Ensure now is tz-aware for comparison
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
            
        fresh_odds = {}
        fresh_updates = {}
        
        for book_id, captured_at in matched.updated_at.items():
            ts = captured_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            
            if (now - ts) <= self._max_age:
                fresh_odds[book_id] = matched.book_odds[book_id]
                fresh_updates[book_id] = captured_at
                
        if not fresh_odds:
            return None
            
        # Instead of modifying the shared instance, return a new one
        import copy
        filtered = copy.copy(matched)
        filtered.book_odds = fresh_odds
        filtered.updated_at = fresh_updates
        return filtered
