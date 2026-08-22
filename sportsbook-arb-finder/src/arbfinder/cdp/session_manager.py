"""Manager for CDP sessions."""

import logging
import threading
import time
from collections.abc import Callable
from typing import Any

from arbfinder.cdp.discovery import find_tab
from arbfinder.cdp.client import CDPClient
from arbfinder.parsers.base import BookParser

__all__ = ["SessionManager"]

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages multiple CDP client sessions for different sportsbooks."""

    def __init__(
        self, parsers: list[BookParser], on_odds_update: Callable[[list[Any]], None]
    ) -> None:
        """Initialize the session manager with sportsbook parsers."""
        self.parsers = parsers
        self.on_odds_update = on_odds_update
        self._running = False
        self._threads: list[threading.Thread] = []
        self._clients: list[CDPClient] = []
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start managing CDP sessions."""
        self._running = True
        for parser in self.parsers:
            t = threading.Thread(
                target=self._reattach_loop, args=(parser,), daemon=True
            )
            self._threads.append(t)
            t.start()

    def stop(self) -> None:
        """Stop managing CDP sessions."""
        self._running = False

        with self._lock:
            clients = list(self._clients)

        for client in clients:
            client.close()

    def _handle_updates(self, updates: list[Any] | None) -> None:
        if updates:
            self.on_odds_update(updates)

    def _reattach_loop(self, parser: BookParser) -> None:
        """Background loop to reconnect or poll for tabs."""
        url_pattern = parser.book_name.lower()

        while self._running:
            logger.info(f"Looking for {parser.book_name} tab...")
            tab = find_tab(url_pattern)

            if not tab:
                logger.warning(f"No {parser.book_name} tab found. Retrying in 3s...")
                time.sleep(3)
                continue

            ws_url = tab.get("webSocketDebuggerUrl")
            if not ws_url:
                logger.warning(
                    f"Tab found for {parser.book_name} but no ws url. Retrying in 3s..."
                )
                time.sleep(3)
                continue

            logger.info(f"Connecting to {parser.book_name} via CDP...")

            client = CDPClient(
                ws_url=ws_url,
                url_filter=parser.relevant_http_url,
                on_http_body=lambda url, body: self._handle_updates(
                    parser.handle_http_body(url, body)
                ),
                on_ws_frame=lambda frame: self._handle_updates(
                    parser.handle_ws_frame(frame)
                ),
                ws_url_filter=parser.relevant_ws_url,
            )

            with self._lock:
                self._clients.append(client)

            # Blocks until connection closes
            client.run()

            with self._lock:
                if client in self._clients:
                    self._clients.remove(client)

            if self._running:
                logger.info(
                    f"Connection for {parser.book_name} closed. Re-running discovery in 3s..."
                )
                time.sleep(3)
