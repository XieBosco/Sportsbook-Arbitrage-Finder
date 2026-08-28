"""Stake calculator — distributes a budget across arb legs."""

from __future__ import annotations

__all__ = ["compute_stakes"]


def compute_stakes(
    odds_by_selection: dict[str, float],
    total_stake: float,
) -> dict[str, float]:
    """Compute stakes for each selection proportional to 1/odds.

    Parameters
    ----------
    odds_by_selection:
        Mapping of ``selection -> decimal_odds`` (e.g. ``{"home": 2.5, "away": 1.8}``).
    total_stake:
        Total budget to distribute across all legs.

    Returns
    -------
    dict[str, float]
        Mapping of ``selection -> stake``, summing to *total_stake*
        (within floating-point tolerance).
    """
    inv_sum = sum(1.0 / odds for odds in odds_by_selection.values())
    return {
        selection: total_stake * (1.0 / odds) / inv_sum
        for selection, odds in odds_by_selection.items()
    }
