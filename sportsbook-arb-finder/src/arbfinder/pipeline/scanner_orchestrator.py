"""Pipeline orchestrator — matched selection → scanner."""

from __future__ import annotations

from arbfinder.matching.output import MatchedSelection
from arbfinder.scanner.scanner import Scanner
from arbfinder.scanner.schema import Opportunity

__all__ = ["handle_matched_selection"]


def handle_matched_selection(
    matched: MatchedSelection,
    scanner: Scanner,
) -> Opportunity | None:
    """Pass a :class:`MatchedSelection` through the scanner pipeline.
    """
    return scanner.process(matched)
