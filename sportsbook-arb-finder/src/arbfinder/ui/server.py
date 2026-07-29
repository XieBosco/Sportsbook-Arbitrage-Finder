"""Web UI and API server."""
from typing import TYPE_CHECKING
from arbfinder.engine.store import OddsStore

if TYPE_CHECKING:
    from fastapi import FastAPI

__all__ = ["create_app", "ConnectionManager"]

def create_app(store: OddsStore) -> "FastAPI":
    """Create and configure the FastAPI application."""
    pass

class ConnectionManager:
    """Manages WebSocket connections for real-time UI updates."""

    def __init__(self) -> None:
        """Initialize the connection manager."""
        pass

    async def connect(self, websocket) -> None:
        """Accept a new websocket connection."""
        pass

    async def disconnect(self, websocket) -> None:
        """Handle a websocket disconnection."""
        pass

    async def broadcast(self, message: dict) -> None:
        """Broadcast a message to all connected clients."""
        pass
