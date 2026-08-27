"""Time tolerance helper for bucket matching."""

from __future__ import annotations

from datetime import datetime, timedelta

__all__ = ["TimeResolver"]


class TimeResolver:
    """Determines whether two timestamps are close enough to be
    considered the same game."""

    def is_within_tolerance(
        self,
        time_a: datetime,
        time_b: datetime,
        tolerance_minutes: int = 60,
    ) -> bool:
        """Return ``True`` if *time_a* and *time_b* are within
        *tolerance_minutes* of each other."""
        return abs(time_a - time_b) <= timedelta(minutes=tolerance_minutes)
