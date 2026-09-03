"""ConnectionManager — tracks WebSocket clients and broadcasts messages.

Thread-safety note
------------------
The scanner runs inside asyncio tasks in the *same* event loop as the
FastAPI server.  ``emit()`` in ``WebSocketSink`` calls
``asyncio.create_task(manager.broadcast(...))``, so multiple broadcasts can
overlap if they ``await`` concurrently.  An ``asyncio.Lock`` serialises
mutations of ``_active`` (connect / disconnect / prune-on-failure) against
the snapshot taken at the start of each broadcast, preventing list-corruption
from concurrent adds/removes.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from starlette.websockets import WebSocket

__all__ = ["ConnectionManager"]

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts JSON messages."""

    def __init__(self) -> None:
        self._active: list[WebSocket] = []
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self, websocket: WebSocket) -> None:
        """Accept *websocket* and register it as an active client."""
        await websocket.accept()
        async with self._lock:
            self._active.append(websocket)
        logger.info(
            "WebSocket client connected (%d active)", len(self._active),
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove *websocket* from the active list (no error if absent)."""
        async with self._lock:
            try:
                self._active.remove(websocket)
            except ValueError:
                pass
        logger.info(
            "WebSocket client disconnected (%d active)", len(self._active),
        )

    # ------------------------------------------------------------------
    # Broadcast
    # ------------------------------------------------------------------

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Send *message* as JSON to every active connection.

        A dead/slow client that raises on ``send_json`` is collected and
        pruned *after* the send loop so that one failure never prevents
        delivery to the remaining clients.
        """
        # Snapshot under lock so new connects/disconnects during the
        # send loop don't mutate the list we're iterating.
        async with self._lock:
            snapshot = list(self._active)

        failed: list[WebSocket] = []
        for ws in snapshot:
            try:
                await ws.send_json(message)
            except Exception:
                logger.debug("Send failed for a client — will prune")
                failed.append(ws)

        if failed:
            async with self._lock:
                for ws in failed:
                    try:
                        self._active.remove(ws)
                    except ValueError:
                        pass  # already removed by a concurrent disconnect
            logger.info(
                "Pruned %d dead client(s) (%d remaining)",
                len(failed),
                len(self._active),
            )

    @property
    def active_count(self) -> int:
        """Return the number of currently connected clients."""
        return len(self._active)
