"""Arbitrage detection engine."""
from typing import Callable
from arbfinder.engine.store import OddsStore

__all__ = ["find_arb", "ArbitrageEngine"]

def find_arb(prices: dict[str, int]) -> dict | None:
    """Detect if an arbitrage opportunity exists in a set of prices."""
    pass

class ArbitrageEngine:
    """Engine for continuously scanning for arbitrage opportunities."""

    def __init__(self, store: OddsStore, threshold_pct: float) -> None:
        """Initialize the arbitrage engine."""
        pass

    def scan_once(self) -> list[dict]:
        """Perform a single scan of the store for opportunities."""
        pass

    def run_forever(self, alert_fn: Callable[[dict], None], interval_ms: int = 250) -> None:
        """Run the arbitrage scan loop indefinitely."""
        pass
