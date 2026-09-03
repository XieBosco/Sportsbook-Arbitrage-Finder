"""FastAPI application — WebSocket endpoint, static file serving, health check.

Usage
-----
The orchestrator creates the app via the factory function::

    connection_manager = ConnectionManager()
    app = create_app(connection_manager)
    # then passes ``app`` to ``uvicorn.Server``
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from arbfinder.pipeline.config import AppConfig

from pydantic import BaseModel
from arbfinder.ui_server.connection_manager import ConnectionManager

__all__ = ["create_app"]

logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).resolve().parent / "static"


class SettingsUpdate(BaseModel):
    arbitrage: dict
    scanner: dict
    odds_format: str
    ui_sort_by: str


def create_app(connection_manager: ConnectionManager, config: AppConfig) -> FastAPI:
    """Build and return a configured :class:`FastAPI` instance.

    Parameters
    ----------
    connection_manager:
        The shared :class:`ConnectionManager` that bridges scanner output
        (via ``WebSocketSink``) to connected browser clients.
    """
    app = FastAPI(title="Arbitrage Finder UI", docs_url=None, redoc_url=None)

    # Store on app.state so route handlers can access it.
    app.state.manager = connection_manager

    # ---- Static files ----
    app.mount(
        "/static",
        StaticFiles(directory=str(_STATIC_DIR)),
        name="static",
    )

    # ---- Routes ----

    @app.get("/")
    async def index():
        """Serve the main UI page."""
        return FileResponse(str(_STATIC_DIR / "index.html"))

    @app.get("/health")
    async def health():
        """Simple liveness / readiness check."""
        return {
            "status": "ok",
            "connected_clients": connection_manager.active_count,
        }

    @app.get("/api/config")
    async def get_config():
        """Expose UI-specific configuration."""
        return {"ui_sort_by": config.server.ui_sort_by}

    @app.get("/api/settings")
    async def get_settings():
        """Return the current dynamic settings."""
        return {
            "arbitrage": config.arbitrage.model_dump(),
            "scanner": config.scanner.model_dump(),
            "sinks": {"odds_format": config.sinks.odds_format},
            "ui_sort_by": config.server.ui_sort_by,
        }

    @app.post("/api/settings")
    async def update_settings(payload: SettingsUpdate):
        """Update dynamic settings in-place."""
        for k, v in payload.arbitrage.items():
            if hasattr(config.arbitrage, k):
                setattr(config.arbitrage, k, v)
                
        for k, v in payload.scanner.items():
            if hasattr(config.scanner, k):
                setattr(config.scanner, k, v)
                
        config.sinks.odds_format = payload.odds_format
        config.server.ui_sort_by = payload.ui_sort_by
        return {"status": "ok"}

    @app.websocket("/ws/opportunities")
    async def ws_opportunities(websocket: WebSocket):
        """Push-only WebSocket endpoint for live opportunity streaming.

        The server never reads meaningful data from the client — the
        ``receive_text()`` loop exists solely to detect disconnects.
        """
        await connection_manager.connect(websocket)
        try:
            while True:
                # Block until the client sends *something* or disconnects.
                data = await websocket.receive_text()
                # Ignore content — this endpoint is server-push only.
                logger.debug("Ignored client message on WS: %s", data[:120])
        except WebSocketDisconnect:
            await connection_manager.disconnect(websocket)

    return app
