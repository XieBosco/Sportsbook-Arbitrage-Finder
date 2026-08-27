"""Market matching logic."""
from arbfinder.normalization.models import OddsUpdate

__all__ = ["MarketMatcher"]

class MarketMatcher:
    """Matches raw updates to canonical markets."""

    def __init__(self, alias_table: dict[str, str]) -> None:
        """Initialize the matcher with an alias table."""
        pass

    def canonical_key_for(self, update: OddsUpdate) -> str:
        """Generate a canonical key for a given odds update."""
        pass

    def match(self, update: OddsUpdate) -> str:
        """Match an update to a canonical market, caching the result."""
        pass
