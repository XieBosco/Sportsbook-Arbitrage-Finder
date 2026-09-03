"""UI server package — FastAPI WebSocket server for live opportunity streaming."""

from arbfinder.ui_server.app import create_app
from arbfinder.ui_server.connection_manager import ConnectionManager

__all__ = ["ConnectionManager", "create_app"]
