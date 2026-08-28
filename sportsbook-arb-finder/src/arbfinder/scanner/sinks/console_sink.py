"""Console sink — prints a formatted opportunity summary."""

from __future__ import annotations

from arbfinder.scanner.schema import Opportunity
from arbfinder.scanner.sinks.base_sink import OpportunitySink

__all__ = ["ConsoleSink"]


class ConsoleSink(OpportunitySink):
    """Prints a human-readable summary of each opportunity to stdout."""

    def emit(self, opportunity: Opportunity) -> None:
        """Print a formatted summary of the opportunity."""
        print(
            f"{'=' * 60}\n"
            f"ARB DETECTED  |  margin: {opportunity.margin:.4%}\n"
            f"Game: {opportunity.home_team} vs {opportunity.away_team}\n"
            f"Sport: {opportunity.sport_key} / {opportunity.league_key}\n"
            f"Market: {opportunity.market_type}"
            f"{f'  line={opportunity.line}' if opportunity.line is not None else ''}\n"
            f"ID: {opportunity.opportunity_id}\n"
            f"{'-' * 60}"
        )
        for leg in opportunity.legs:
            print(
                f"  {leg.selection:<10}  "
                f"book={leg.book_id:<12}  "
                f"odds={leg.odds_decimal:.4f}  "
                f"stake=${leg.stake:.2f}"
            )
        print(f"{'=' * 60}\n")
