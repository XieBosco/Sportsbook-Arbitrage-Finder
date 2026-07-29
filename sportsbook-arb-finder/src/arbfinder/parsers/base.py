"""Base parser interfaces."""
from abc import ABC, abstractmethod
from arbfinder.normalize.models import OddsUpdate

__all__ = ["BookParser"]

class BookParser(ABC):
    """Abstract base class for sportsbook parsers."""

    book_name: str

    @abstractmethod
    def can_handle(self, raw: str) -> bool:
        """Determine if this parser can handle the raw CDP message."""
        pass

    @abstractmethod
    def parse(self, raw: str) -> list[OddsUpdate]:
        """Parse the raw CDP message into odds updates."""
        pass
