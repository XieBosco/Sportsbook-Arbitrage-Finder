"""Math utilities for odds conversions."""

__all__ = ["implied_prob", "american_to_decimal", "decimal_to_american"]


def implied_prob(american_odds: int) -> float:
    """Calculate the implied probability of American odds."""
    if american_odds < 0:
        return (-american_odds) / (-american_odds + 100)
    else:
        return 100 / (american_odds + 100)


def american_to_decimal(american_odds: int) -> float:
    """Convert American odds to decimal odds."""
    if american_odds < 0:
        return 1 - (100 / american_odds)
    else:
        return 1 + (american_odds / 100)


def decimal_to_american(decimal_odds: float) -> int:
    """Convert decimal odds to American odds."""
    if decimal_odds >= 2.0:
        return int(round((decimal_odds - 1) * 100))
    elif decimal_odds > 1.0:
        return int(round(-100 / (decimal_odds - 1)))
    return 0
