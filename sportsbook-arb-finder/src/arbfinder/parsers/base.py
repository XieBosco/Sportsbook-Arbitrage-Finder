"""Base parser interfaces."""

import logging
from abc import ABC, abstractmethod

from arbfinder.normalize.models import OddsUpdate

__all__ = ["BookParser"]

logger = logging.getLogger(__name__)


class BookParser(ABC):
    """Abstract base class for sportsbook parsers."""

    book_name: str

    @abstractmethod
    def relevant_http_url(self, url: str) -> bool:
        """True if this HTTP response body should be fetched via getResponseBody."""
        pass

    def relevant_ws_url(self, url: str) -> bool:
        """True if this WebSocket connection's frames should be parsed.

        Returns True by default (permissive), allowing frames from any socket the tab opens.
        This is appropriate for most books, but books that open multiple separate websockets
        (e.g., Caesars) should override this to drop frames from unrelated connections.
        """
        return True

    @abstractmethod
    def handle_http_body(self, url: str, body: str) -> list[OddsUpdate]:
        """Parse an HTTP response body — reference dictionaries AND/OR live odds
        depending on the book (see each book's .md for which URLs carry which)."""
        pass

    @abstractmethod
    def handle_ws_frame(self, payload: str) -> list[OddsUpdate]:
        """Parse a raw WebSocket frame payload. Return [] for non-odds frames
        (handshakes, acks, keepalives)."""
        pass

    def reset(self) -> None:
        """Reset parser state (e.g. on socket close or reconnect).

        Default no-op. Override in parsers that maintain session state
        (e.g. Caesars Diffusion alias store).
        """
        pass
