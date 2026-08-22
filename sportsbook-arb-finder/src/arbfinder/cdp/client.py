"""CDP websocket client."""

import base64
import json
import logging
import time
from collections.abc import Callable
from typing import Any

import websocket

__all__ = ["CDPClient"]

logger = logging.getLogger(__name__)


class CDPClient:
    """Client for interacting with Chrome DevTools Protocol."""

    def __init__(
        self,
        ws_url: str,
        url_filter: Callable[[str], bool],
        on_http_body: Callable[[str, str], Any],
        on_ws_frame: Callable[[str], Any],
        ws_url_filter: Callable[[str], bool] | None = None,
    ) -> None:
        """Initialize the CDP client."""
        self.ws_url = ws_url
        self.url_filter = url_filter
        self.on_http_body = on_http_body
        self.on_ws_frame = on_ws_frame
        self.ws_url_filter = ws_url_filter or (lambda url: True)

        self.cmd_id = 0
        self.pending_requests: dict[
            int, tuple[str, float]
        ] = {}  # cmd_id -> (url, timestamp)
        self.active_websockets: dict[str, str] = {}  # requestId -> url
        self._untracked_warned_sockets: set[str] = set()
        self._last_sweep = time.time()
        self.ws: websocket.WebSocketApp | None = None
        self._running = False

    def send(self, method: str, params: dict | None = None) -> int:
        """Send a CDP method with optional parameters and return the request ID."""
        if not self.ws:
            return -1

        self.cmd_id += 1
        msg = {"id": self.cmd_id, "method": method}
        if params:
            msg["params"] = params

        self.ws.send(json.dumps(msg))
        return self.cmd_id

    def run(self) -> None:
        """Start the CDP client blocking event loop."""
        self._running = True
        try:
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_close=self._on_close,
                on_error=self._on_error,
            )
            self.ws.run_forever()
        except Exception as e:
            logger.error(f"CDP websocket exception: {e}")

    def close(self) -> None:
        """Close the CDP client connection."""
        self._running = False
        if self.ws:
            self.ws.close()
        self.pending_requests.clear()
        self.active_websockets.clear()
        self._untracked_warned_sockets.clear()

    def _on_open(self, ws: websocket.WebSocketApp) -> None:
        """Handle websocket open event."""
        logger.info(f"Connected to CDP websocket: {self.ws_url}")
        self.send(
            "Network.enable",
            {
                "maxResourceBufferSize": 100 * 1024 * 1024,
                "maxTotalBufferSize": 100 * 1024 * 1024,
            },
        )

    def _on_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        """Handle incoming websocket message."""
        try:
            data = json.loads(message)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to decode CDP message as JSON: {e}")
            return

        # Evict old pending requests periodically (time-gated)
        now = time.time()
        if now - self._last_sweep > 10.0:
            self._last_sweep = now
            expired_cmds = [
                cmd
                for cmd, (url, ts) in self.pending_requests.items()
                if now - ts > 30.0
            ]
            for cmd in expired_cmds:
                del self.pending_requests[cmd]

        method = data.get("method")

        # 1. Handle HTTP response received
        if method == "Network.responseReceived":
            response = data.get("params", {}).get("response", {})
            url = response.get("url", "")
            if url and self.url_filter(url):
                request_id = data.get("params", {}).get("requestId")
                if request_id:
                    cmd_id = self.send(
                        "Network.getResponseBody", {"requestId": request_id}
                    )
                    self.pending_requests[cmd_id] = (url, time.time())

        # 2. Handle getResponseBody result
        elif "id" in data and "result" in data and "body" in data.get("result", {}):
            cmd_id = data["id"]
            if cmd_id in self.pending_requests:
                url, _ = self.pending_requests.pop(cmd_id)
                body = data["result"]["body"]
                if data["result"].get("base64Encoded"):
                    try:
                        body = base64.b64decode(body).decode("utf-8", errors="ignore")
                    except Exception as e:
                        logger.error(
                            f"Failed to base64 decode HTTP body for {url}: {e}"
                        )
                self.on_http_body(url, body)

        # 3. Handle WebSocket creation
        elif method == "Network.webSocketCreated":
            params = data.get("params", {})
            request_id = params.get("requestId")
            url = params.get("url")
            if request_id and url:
                self.active_websockets[request_id] = url

        # 4. Handle WebSocket close
        elif method == "Network.webSocketClosed":
            request_id = data.get("params", {}).get("requestId")
            if request_id in self.active_websockets:
                del self.active_websockets[request_id]
            if request_id in self._untracked_warned_sockets:
                self._untracked_warned_sockets.remove(request_id)

        # 5. Handle WebSocket frame received
        elif method == "Network.webSocketFrameReceived":
            params = data.get("params", {})
            request_id = params.get("requestId")

            if request_id in self.active_websockets:
                url = self.active_websockets[request_id]
                if self.ws_url_filter(url):
                    payload_data = params.get("response", {}).get("payloadData")
                    if payload_data is not None:
                        self.on_ws_frame(payload_data)
            else:
                if request_id and request_id not in self._untracked_warned_sockets:
                    self._untracked_warned_sockets.add(request_id)
                    logger.warning(
                        f"Received frame for untracked WebSocket requestId '{request_id}' "
                        f"(socket connection predates CDP attachment). "
                        f"Frames will be dropped until the page is refreshed."
                    )

    def _on_error(self, ws: websocket.WebSocketApp, error: Any) -> None:
        """Handle websocket error."""
        logger.error(f"CDP Websocket error: {error}")

    def _on_close(
        self, ws: websocket.WebSocketApp, close_status_code: int, close_msg: str
    ) -> None:
        """Handle websocket close event."""
        logger.info(f"CDP Websocket closed (code {close_status_code}): {close_msg}")
        self.pending_requests.clear()
        self.active_websockets.clear()
        self._untracked_warned_sockets.clear()
