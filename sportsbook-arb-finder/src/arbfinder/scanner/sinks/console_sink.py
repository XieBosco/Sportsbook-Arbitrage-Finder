"""Console sink — prints a formatted opportunity summary."""

from __future__ import annotations

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from arbfinder.pipeline.config import SinksConfig

from arbfinder.scanner.schema import Opportunity
from arbfinder.scanner.sinks.base_sink import OpportunitySink
from arbfinder.utils.odds import format_odds

__all__ = ["ConsoleSink"]

import logging
logger = logging.getLogger(__name__)

_HEADER_SEPARATOR = "=" * 60
_SECTION_SEPARATOR = "-" * 60


class ConsoleSink(OpportunitySink):
    """Outputs opportunities as nicely formatted text to the console."""

    def __init__(self, sinks_config: SinksConfig) -> None:
        self._sinks_config = sinks_config

    def emit(self, opportunity: Opportunity) -> None:
        """Format and log *opportunity*."""
        odds_format = self._sinks_config.odds_format
        line_suffix = (
            f"  line={opportunity.line}" if opportunity.line is not None else ""
        )
        print(
            f"{_HEADER_SEPARATOR}\n"
            f"ARB DETECTED  |  margin: {opportunity.margin:.4%}\n"
            f"Game: {opportunity.home_team} vs {opportunity.away_team}\n"
            f"Sport: {opportunity.sport_key} / {opportunity.league_key}\n"
            f"Market: {opportunity.market_type}{line_suffix}\n"
            f"ID: {opportunity.opportunity_id}\n"
            f"{_SECTION_SEPARATOR}"
        )
        for leg in opportunity.legs:
            formatted_odds = format_odds(leg.odds_decimal, odds_format)
            print(
                f"  {leg.selection:<10}  "
                f"book={leg.book_id:<12}  "
                f"odds={formatted_odds:<8}  "
                f"stake=${leg.stake:.2f}"
            )
        print(f"{_HEADER_SEPARATOR}\n")

    def emit_close(
        self, canonical_game_id: str, market_type: str, line: float | None
    ) -> None:
        """Handle the closure of a previously emitted opportunity."""
        # For console, we don't spam closes unless debugging
        pass