"""Storage sink — in-memory list for testing and later inspection."""

from __future__ import annotations

import dataclasses

from arbfinder.scanner.schema import Opportunity
from arbfinder.scanner.sinks.base_sink import OpportunitySink

__all__ = ["StorageSink"]


class StorageSink(OpportunitySink):
    """Appends each opportunity (as a dict) to an in-memory list.

    A stub implementation — to be replaced with real persistence later.
    """

    def __init__(self) -> None:
        self._items: list[dict] = []

    def emit(self, opportunity: Opportunity) -> None:
        """Append the opportunity as a plain dict."""
        self._items.append(dataclasses.asdict(opportunity))

    def get_all(self) -> list[dict]:
        """Return all stored opportunities."""
        return list(self._items)

    def emit_close(
        self, canonical_game_id: str, market_type: str, line: float | None
    ) -> None:
        """Handle the closure of a previously emitted opportunity."""
        # For simple storage, we just ignore closes
        pass
