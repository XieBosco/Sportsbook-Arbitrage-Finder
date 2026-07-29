"""FanDuel parser."""
from arbfinder.parsers.base import BookParser
from arbfinder.normalize.models import OddsUpdate

__all__ = ["FanDuelParser"]

class FanDuelParser(BookParser):
    """Parser for FanDuel."""

    book_name: str = "FanDuel"

    def can_handle(self, raw: str) -> bool:
        """Determine if this parser can handle the raw CDP message."""
        pass

    def parse(self, raw: str) -> list[OddsUpdate]:
        """Parse the raw CDP message into odds updates."""
        pass
