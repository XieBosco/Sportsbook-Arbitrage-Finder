"""In-memory data store for odds."""
from arbfinder.normalization.models import OddsUpdate

__all__ = ["OddsStore"]

class OddsStore:
    """Stores and manages the latest odds from various books."""

    def __init__(self) -> None:
        """Initialize the odds store."""
        pass

    def update(self, key: str, book: str, update: OddsUpdate) -> None:
        """Update the odds for a given key and book."""
        pass

    def get_market(self, key: str) -> dict[str, OddsUpdate]:
        """Retrieve all current odds for a given market key."""
        pass

    def all_keys(self) -> list[str]:
        """Get a list of all market keys in the store."""
        pass
