"""Pure arbitrage-detection functions — no I/O, highest test priority."""

from __future__ import annotations

from dataclasses import dataclass

from arbfinder.matching.output import MatchedSelection

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
    """Evaluate whether a set of matched selections constitutes an arbitrage.

    Parameters
    ----------
    group : dict[str, MatchedSelection]
        Mapping of selection name to the corresponding ``MatchedSelection``.
        All selections within the group are expected to have the same
        canonical game ID, market type, time window, and line.

    Returns
    -------
    ArbCheckResult
        Contains the computed margin and the best book/odds per selection.
    """
    best_odds_by_selection: dict[str, tuple[str, float]] = {}

    for selection, matched in group.items():
        best_book: str | None = None
        best_decimal: float = 0.0

        for book_id, raw_odds in matched.book_odds.items():
            if raw_odds is None:
                continue
            try:
                odds_num = float(raw_odds)
            except (ValueError, TypeError):
                continue

            # Strict pipeline invariant: MatchedSelection.book_odds is always canonical decimal float > 1.0
            if odds_num > 1.0:
                decimal_odds = odds_num
            else:
                continue

            if decimal_odds > best_decimal:
                best_decimal = decimal_odds
                best_book = book_id

        if best_book is not None:
            best_odds_by_selection[selection] = (best_book, best_decimal)

    if len(best_odds_by_selection) < len(group):
        return ArbCheckResult(
            is_arbitrage=False,
            margin=0.0,
            best_odds_by_selection=best_odds_by_selection,
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
