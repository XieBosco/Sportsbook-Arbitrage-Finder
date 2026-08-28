"""Staleness filter — rejects selections with outdated odds."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from arbfinder.matching.output import MatchedSelection

__all__ = ["StalenessFilter"]


class StalenessFilter:
    """Rejects a :class:`MatchedSelection` if any of its book timestamps
    are older than *max_age_seconds*.

    This guards against silently disconnected feeds (dead websocket /
    backgrounded browser tab) and suspended markets whose last-known
    price is stale but still present in the bucket — both produce
    phantom arbitrage if not filtered.
    """

    def __init__(self, max_age_seconds: float) -> None:
        self._max_age = timedelta(seconds=max_age_seconds)

    def is_fresh(self, matched: MatchedSelection, now: datetime) -> bool:
        """Return True only if every timestamp in *matched.updated_at*
        is within *max_age_seconds* of *now*.
        """
        if not matched.updated_at:
            return False
        # Ensure now is tz-aware for comparison
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        for captured_at in matched.updated_at.values():
            ts = captured_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if (now - ts) > self._max_age:
                return False
        return True
