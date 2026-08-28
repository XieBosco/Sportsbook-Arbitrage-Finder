"""Abstract base class for opportunity sinks."""

from __future__ import annotations

from abc import ABC, abstractmethod

from arbfinder.scanner.schema import Opportunity

__all__ = ["OpportunitySink"]


class OpportunitySink(ABC):
    """Receives detected arbitrage opportunities for processing."""

    @abstractmethod
    def emit(self, opportunity: Opportunity) -> None:
        """Handle a detected opportunity (alert, store, log, etc.)."""
