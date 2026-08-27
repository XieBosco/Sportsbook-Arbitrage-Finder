"""Math utilities for odds conversions."""

__all__ = ["implied_prob", "american_to_decimal", "decimal_to_american",
           "fractional_to_decimal", "decimal_to_fractional", "convert_odds"]

import fractions


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


def fractional_to_decimal(fractional: str) -> float:
    """Convert fractional odds string (e.g. '5/2') to decimal odds.

    Raises ValueError if the string cannot be parsed.
    """
    parts = fractional.strip().split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid fractional odds: {fractional!r}")
    numerator = float(parts[0])
    denominator = float(parts[1])
    if denominator == 0:
        raise ValueError(f"Zero denominator in fractional odds: {fractional!r}")
    return (numerator / denominator) + 1.0


def decimal_to_fractional(decimal_odds: float) -> str:
    """Convert decimal odds to fractional odds."""
    if decimal_odds <= 1.0:
        return "1/1"
    f = fractions.Fraction(decimal_odds - 1).limit_denominator(100)
    return f"{f.numerator}/{f.denominator}"


def convert_odds(decimal_odds: float, target_format: str) -> float | str:
    """Convert decimal odds to the target format."""
    fmt = target_format.lower()
    if fmt == "decimal":
        return decimal_odds
    elif fmt == "american":
        return decimal_to_american(decimal_odds)
    elif fmt == "fractional":
        return decimal_to_fractional(decimal_odds)
    else:
        raise ValueError(f"Unknown odds format: {target_format}")
