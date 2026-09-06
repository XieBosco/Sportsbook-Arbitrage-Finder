"""WebSocket sink — bridges Scanner output into the UI server's ConnectionManager.

Threading / async analysis
--------------------------
The Scanner's ``process()`` method calls ``sink.emit()`` synchronously
(see ``scanner.py`` L151-153).  ``process()`` is invoked from within
``run_book_pipeline()``, which is an ``asyncio.Task`` in the **same**
event loop that hosts the FastAPI/uvicorn server.

Because we are already inside a running asyncio loop when ``emit()`` is
called, we use ``asyncio.get_running_loop().create_task()`` to schedule
the async ``broadcast()`` without blocking the scanner.  No thread-
crossing (``run_coroutine_threadsafe``) is needed.
"""

from __future__ import annotations

import asyncio
import logging

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from arbfinder.pipeline.config import SinksConfig

from arbfinder.scanner.schema import Opportunity
from arbfinder.scanner.sinks.base_sink import OpportunitySink
from arbfinder.ui_server.connection_manager import ConnectionManager
from arbfinder.ui_server.serializers import serialize_opportunity

__all__ = ["WebSocketSink"]

logger = logging.getLogger(__name__)


class WebSocketSink(OpportunitySink):
    """Serialises each :class:`Opportunity` and broadcasts it to all
    connected WebSocket clients via the shared :class:`ConnectionManager`.
    """

    def __init__(self, connection_manager: ConnectionManager, sinks_config: SinksConfig) -> None:
        self._manager = connection_manager
        self._sinks_config = sinks_config
        self._tasks: set[asyncio.Task] = set()

    def _schedule_broadcast(self, loop: asyncio.AbstractEventLoop, message: dict) -> None:
        task = loop.create_task(self._manager.broadcast(message))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def emit(self, opportunity: Opportunity) -> None:
        """Serialise *opportunity* and schedule an async broadcast.

        This method is synchronous (matching the ``OpportunitySink`` ABC)
        but schedules the actual I/O as a fire-and-forget task on the
        running event loop.
        """
        payload = serialize_opportunity(opportunity, self._sinks_config.odds_format)
        message = {"type": "opportunity", "data": payload}

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop — should not happen in production but log
            # defensively rather than crashing the scanner.
            logger.warning(
                "WebSocketSink.emit() called outside an asyncio event loop; "
                "dropping opportunity %s",
                opportunity.opportunity_id,
            )
            return

        self._schedule_broadcast(loop, message)

    def emit_close(
        self, canonical_game_id: str, market_type: str, line: float | None
    ) -> None:
        """Broadcast a message that an opportunity has closed."""
        message = {
            "type": "opportunity_closed",
            "data": {
                "canonical_game_id": canonical_game_id,
                "market_type": market_type,
                "line": line,
            },
        }

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        self._schedule_broadcast(loop, message)
