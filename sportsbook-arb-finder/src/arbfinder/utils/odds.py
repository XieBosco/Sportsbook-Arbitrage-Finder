"""Odds formatting utilities."""

from __future__ import annotations

from fractions import Fraction

__all__ = ["format_odds"]


def format_odds(decimal: float, odds_format: str = "american") -> str:
    """Format decimal odds into a string of the specified format."""
    fmt = odds_format.lower()
    if fmt == "decimal":
        return f"{decimal:.2f}"
    elif fmt == "fractional":
        frac = Fraction(decimal - 1).limit_denominator(100)
        return f"{frac.numerator}/{frac.denominator}"
    else:  # american default
        if decimal <= 1.0:
            return "0"
        elif decimal >= 2.0:
            american = round((decimal - 1) * 100)
            return f"+{american}"
        else:
            american = round(-100 / (decimal - 1))
            return str(american)
