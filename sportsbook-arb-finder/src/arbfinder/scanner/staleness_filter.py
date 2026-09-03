"""Staleness filter — rejects selections with outdated odds."""

from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone

from arbfinder.matching.output import MatchedSelection
from arbfinder.scanner.threshold_config import ScannerThresholds

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

    def __init__(self, thresholds: ScannerThresholds) -> None:
        self._thresholds = thresholds

    def filter_stale_books(
        self, matched: MatchedSelection, now: datetime
    ) -> MatchedSelection | None:
        """Return a filtered copy or None if no books remain."""
        max_age = timedelta(seconds=self._thresholds.max_odds_age_seconds)

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

            if (now - ts) <= max_age:
                fresh_odds[book_id] = matched.book_odds[book_id]
                fresh_updates[book_id] = captured_at

        if not fresh_odds:
            return None

        # Instead of modifying the shared instance, return a new one
        filtered = copy.copy(matched)
        filtered.book_odds = fresh_odds
        filtered.updated_at = fresh_updates
        return filtered