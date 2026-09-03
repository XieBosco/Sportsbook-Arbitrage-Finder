"""Stake calculator — distributes a budget across arb legs."""

from __future__ import annotations

__all__ = ["compute_stakes"]


def compute_stakes(
    odds_by_selection: dict[str, float],
    amount: float,
    method: int = 1,
) -> dict[str, float]:
    """Compute stakes for each selection to form a fully hedged arbitrage.

    Parameters
    ----------
    odds_by_selection:
        Mapping of ``selection -> decimal_odds`` (e.g. ``{"home": 2.5, "away": 1.8}``).
    amount:
        The budget or unit size to use for calculation.
    method:
        1 = total_bet_amount (stakes sum to amount)
        2 = unit_size (underdog stake is set to amount)

    Returns
    -------
    dict[str, float]
        Mapping of ``selection -> stake``
    """
    if method == 1:
        total_stake = amount
        inv_sum = sum(1.0 / odds for odds in odds_by_selection.values())
        return {
            selection: total_stake * (1.0 / odds) / inv_sum
            for selection, odds in odds_by_selection.items()
        }
    elif method == 2:
        unit_size = amount
        # Find the underdog leg (highest decimal odds)
        underdog_selection = max(odds_by_selection, key=odds_by_selection.get)
        underdog_odds = odds_by_selection[underdog_selection]
        
        # To be fully hedged, every leg must have the same payout
        target_payout = unit_size * underdog_odds
        
        return {
            selection: target_payout / odds
            for selection, odds in odds_by_selection.items()
        }
    else:
        raise ValueError(f"Unknown stake calculating method: {method}")
