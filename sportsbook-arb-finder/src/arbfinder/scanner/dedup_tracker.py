"""Dedup tracker — prevents re-alerting on the same open arb."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from arbfinder.scanner.market_grouper import MarketGroupKey

__all__ = ["DedupTracker"]


class DedupTracker:
    """Tracks recently-emitted opportunities by :class:`MarketGroupKey`.

    Prevents re-alerting on every single odds tick for an arb that
    remains open across multiple updates.
    """

    def __init__(self, cooldown_seconds: float) -> None:
        self._cooldown = timedelta(seconds=cooldown_seconds)
        self._last_emitted: dict[MarketGroupKey, datetime] = {}

    def should_emit(self, key: MarketGroupKey, now: datetime) -> bool:
        """Return True (and record *now*) if no alert was emitted for
        *key* within the cooldown period.
        """
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        last = self._last_emitted.get(key)
        if last is not None and (now - last) < self._cooldown:
            return False

        self._last_emitted[key] = now
        return True

    def prune_expired(self, now: datetime | None = None) -> int:
        """Remove entries whose last emitted time is older than twice the cooldown."""
        if now is None:
            now = datetime.now(timezone.utc)
        elif now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        threshold = self._cooldown * 2
        keys_to_remove = [
            k for k, ts in self._last_emitted.items()
            if (now - ts) > threshold
        ]
        for k in keys_to_remove:
            del self._last_emitted[k]
        return len(keys_to_remove)
