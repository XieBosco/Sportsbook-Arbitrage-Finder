"""Pure arbitrage-detection functions — no I/O, highest test priority."""

from __future__ import annotations

from dataclasses import dataclass

from arbfinder.matching.output import MatchedSelection
from arbfinder.normalization.odds_math import american_to_decimal

__all__ = ["ArbCheckResult", "check_arbitrage", "has_single_book_conflict"]


@dataclass(frozen=True)
class ArbCheckResult:
    """Result of an arbitrage check across a group of selections."""

    is_arbitrage: bool
    margin: float
    best_odds_by_selection: dict[str, tuple[str, float]]
    # selection -> (book_id, best_odds_decimal)


def check_arbitrage(
    group: dict[str, MatchedSelection],
) -> ArbCheckResult:
    """Check whether a complete group of selections constitutes an arb.

    For each selection, finds the book offering the highest decimal odds
    (converting from American format).  Computes the implied-probability
    sum across all best prices:

        implied_sum = Σ (1 / best_decimal_odds)
        margin      = 1 − implied_sum
        is_arb      = margin > 0

    Parameters
    ----------
    group:
        Mapping of ``selection -> MatchedSelection``, e.g.
        ``{"home": <ms>, "away": <ms>}``.

    Returns
    -------
    ArbCheckResult
        Contains the computed margin and the best book/odds per selection.
    """
    best_odds_by_selection: dict[str, tuple[str, float]] = {}

    for selection, matched in group.items():
        best_book: str | None = None
        best_decimal: float = 0.0

        for book_id, american_odds in matched.book_odds.items():
            decimal_odds = american_to_decimal(int(american_odds))
            if decimal_odds > best_decimal:
                best_decimal = decimal_odds
                best_book = book_id

        if best_book is not None:
            best_odds_by_selection[selection] = (best_book, best_decimal)

    if not best_odds_by_selection:
        return ArbCheckResult(
            is_arbitrage=False,
            margin=0.0,
            best_odds_by_selection={},
        )

    implied_sum = sum(
        1.0 / odds for _, odds in best_odds_by_selection.values()
    )
    margin = 1.0 - implied_sum

    return ArbCheckResult(
        is_arbitrage=margin > 0,
        margin=margin,
        best_odds_by_selection=best_odds_by_selection,
    )


def has_single_book_conflict(result: ArbCheckResult) -> bool:
    """Return True if the same book is the best price for more than one selection.

    Such an "arb" cannot be hedged across different books and must be
    rejected — placing opposite sides of a bet at the same sportsbook
    violates their terms and will be voided.
    """
    books = [book_id for book_id, _ in result.best_odds_by_selection.values()]
    return len(books) != len(set(books))
