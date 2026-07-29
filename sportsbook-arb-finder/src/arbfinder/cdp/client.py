"""CDP websocket client."""
from typing import Callable

__all__ = ["CDPClient"]

class CDPClient:
    """Client for interacting with Chrome DevTools Protocol."""

    def __init__(self, ws_url: str, on_event: Callable[[dict], None]) -> None:
        """Initialize the CDP client."""
        pass

    def send(self, method: str, params: dict | None = None) -> int:
        """Send a CDP method with optional parameters and return the request ID."""
        pass

    def run(self) -> None:
        """Run the CDP client blocking loop."""
        pass

    def close(self) -> None:
        """Close the CDP client connection."""
        pass

    def _on_open(self, ws) -> None:
        """Handle websocket open event."""
        pass

    def _on_message(self, ws, message: str) -> None:
        """Handle incoming websocket message."""
        pass

    def _on_close(self, ws, *args) -> None:
        """Handle websocket close event."""
        pass
