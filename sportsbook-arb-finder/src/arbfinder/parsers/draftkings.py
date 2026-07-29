"""DraftKings parser."""
from arbfinder.parsers.base import BookParser
from arbfinder.normalize.models import OddsUpdate

__all__ = ["DraftKingsParser"]

class DraftKingsParser(BookParser):
    """Parser for DraftKings."""

    book_name: str = "DraftKings"

    def can_handle(self, raw: str) -> bool:
        """Determine if this parser can handle the raw CDP message."""
        pass

    def parse(self, raw: str) -> list[OddsUpdate]:
        """Parse the raw CDP message into odds updates."""
        pass
