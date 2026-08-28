"""Core arbitrage-detection package."""

from arbfinder.core.arbitrage import ArbCheckResult, check_arbitrage, has_single_book_conflict
from arbfinder.core.stake_calculator import compute_stakes

__all__ = [
    "ArbCheckResult",
    "check_arbitrage",
    "compute_stakes",
    "has_single_book_conflict",
]
