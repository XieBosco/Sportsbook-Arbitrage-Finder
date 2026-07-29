"""BetMGM parser."""
from arbfinder.parsers.base import BookParser
from arbfinder.normalize.models import OddsUpdate

__all__ = ["BetMGMParser"]

class BetMGMParser(BookParser):
    """Parser for BetMGM."""

    book_name: str = "BetMGM"

    def can_handle(self, raw: str) -> bool:
        """Determine if this parser can handle the raw CDP message."""
        pass

    def parse(self, raw: str) -> list[OddsUpdate]:
        """Parse the raw CDP message into odds updates."""
        pass
