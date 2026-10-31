"""Locally hosted mock server for Caesars Sportsbook HTTP and WebSocket endpoints.

Replays recorded dataset messages (HTTP /v4/home snapshots and Diffusion WebSocket frames)
over real localhost TCP connections using standard library socket & threading.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import socket
import struct
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def make_ws_accept_key(sec_key: str) -> str:
    """Compute Sec-WebSocket-Accept header value per RFC 6455."""
    sha1 = hashlib.sha1((sec_key.strip() + WS_GUID).encode("ascii")).digest()
    return base64.b64encode(sha1).decode("ascii")


def encode_ws_frame(payload_str: str) -> bytes:
    """Encode text payload into an unmasked RFC 6455 WebSocket frame."""
    data = payload_str.encode("utf-8")
    length = len(data)
    header = bytearray([0x81])  # FIN + Text Opcode (0x01)
    if length < 126:
        header.append(length)
    elif length < 65536:
        header.append(126)
        header.extend(struct.pack(">H", length))
    else:
        header.append(127)
        header.extend(struct.pack(">Q", length))
    return bytes(header) + data


class MockCaesarsServer:
    """Local HTTP and WebSocket server replaying Caesars capture datasets."""

    def __init__(
        self,
        dataset_path: str | Path,
        host: str = "127.0.0.1",
        port: int = 0,  # 0 binds to a random available port
        frame_delay: float = 0.001,
    ) -> None:
        self.dataset_path = Path(dataset_path).resolve()
        self.host = host
        self.port = port
        self.frame_delay = frame_delay

        self._server_sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._actual_port = 0

        # Load dataset messages
        self.home_json_body: str = ""
        self.home_url: str = "https://api.americanwagering.com/regions/ca/locations/on/brands/czr/sb/v4/home"
        self.ws_frames: list[str] = []
        self._load_dataset()

    def _load_dataset(self) -> None:
        """Find /v4/home JSON file and load all ws_*.txt frames in chronological order."""
        msg_dir = self.dataset_path / "caesars" / "messages"
        if not msg_dir.exists():
            msg_dir = self.dataset_path / "messages"
        if not msg_dir.exists():
            raise FileNotFoundError(f"Messages directory not found in {self.dataset_path}")

        # Locate /v4/home JSON
        found_home = False
        json_files = sorted(msg_dir.glob("json_*.json"), key=lambda p: int(p.stem[5:]))
        for jf in json_files:
            try:
                with open(jf, "r", encoding="utf-8") as f:
                    content = f.read()
                d = json.loads(content)
                url = d.get("_DEBUG_URL", "")
                if "/v4/home" in url or "eventDisplayGroups" in d.get("data", {}):
                    self.home_json_body = content
                    if url:
                        self.home_url = url
                    found_home = True
                    logger.info("[MockServer] Loaded /v4/home snapshot from %s (%d bytes)", jf.name, len(content))
                    break
            except Exception:
                continue

        if not found_home and json_files:
            # Fallback to largest JSON
            largest = max(json_files, key=lambda p: p.stat().st_size)
            with open(largest, "r", encoding="utf-8") as f:
                self.home_json_body = f.read()
            logger.info("[MockServer] Using fallback JSON %s", largest.name)

        # Locate all ws_*.txt frames
        ws_files = sorted(msg_dir.glob("ws_*.txt"), key=lambda p: int(p.stem[3:]))
        for wf in ws_files:
            try:
                with open(wf, "r", encoding="utf-8") as f:
                    self.ws_frames.append(f.read().strip())
            except Exception as e:
                logger.warning("[MockServer] Failed to read %s: %e", wf.name, e)

        logger.info(
            "[MockServer] Initialized dataset from %s: 1 home JSON, %d WS frames",
            self.dataset_path.name,
            len(self.ws_frames),
        )

    def start(self) -> None:
        """Start the TCP server listening on host:port."""
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self.host, self.port))
        self._actual_port = self._server_sock.getsockname()[1]
        self._server_sock.listen(10)
        self._server_sock.settimeout(0.5)

        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True, name="MockCaesarsServer")
        self._thread.start()
        logger.info("[MockServer] Listening on http://%s:%d", self.host, self._actual_port)

    def stop(self) -> None:
        """Stop server and close listening socket."""
        self._running = False
        if self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("[MockServer] Stopped.")

    @property
    def http_url(self) -> str:
        return f"http://{self.host}:{self._actual_port}/regions/ca/locations/on/brands/czr/sb/v4/home"

    @property
    def ws_url(self) -> str:
        return f"ws://{self.host}:{self._actual_port}/regions/ca/locations/on/brands/czr/diffusion?ty=WB"

    def _listen_loop(self) -> None:
        while self._running:
            try:
                conn, addr = self._server_sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            handler_thread = threading.Thread(
                target=self._handle_client, args=(conn, addr), daemon=True
            )
            handler_thread.start()

    def _handle_client(self, conn: socket.socket, addr: tuple[str, int]) -> None:
        conn.settimeout(10.0)
        try:
            req_data = b""
            while b"\r\n\r\n" not in req_data:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                req_data += chunk

            if not req_data:
                conn.close()
                return

            req_text = req_data.decode("ascii", errors="ignore")
            lines = req_text.split("\r\n")
            if not lines:
                conn.close()
                return

            req_line = lines[0]
            parts = req_line.split()
            if len(parts) < 2:
                conn.close()
                return

            method, path = parts[0].upper(), parts[1]

            # Parse headers
            headers = {}
            for line in lines[1:]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    headers[k.strip().lower()] = v.strip()

            # 1. WebSocket Upgrade Request
            if headers.get("upgrade", "").lower() == "websocket":
                sec_key = headers.get("sec-websocket-key")
                if not sec_key:
                    conn.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
                    conn.close()
                    return

                accept_key = make_ws_accept_key(sec_key)
                response = (
                    "HTTP/1.1 101 Switching Protocols\r\n"
                    "Upgrade: websocket\r\n"
                    "Connection: Upgrade\r\n"
                    f"Sec-WebSocket-Accept: {accept_key}\r\n\r\n"
                )
                conn.sendall(response.encode("ascii"))
                logger.info("[MockServer] WebSocket connected from %s for path: %s", addr, path)
                self._stream_ws_frames(conn)
                return

            # 2. HTTP GET /v4/home Request
            if method == "GET" and ("/v4/home" in path or path == "/"):
                body_bytes = self.home_json_body.encode("utf-8")
                resp = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: application/json; charset=utf-8\r\n"
                    f"Content-Length: {len(body_bytes)}\r\n"
                    "Access-Control-Allow-Origin: *\r\n"
                    "Connection: close\r\n\r\n"
                ).encode("ascii") + body_bytes
                conn.sendall(resp)
                logger.info("[MockServer] Served /v4/home (%d bytes) to %s", len(body_bytes), addr)
                conn.close()
                return

            # 3. Default fallback
            conn.sendall(b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n")
            conn.close()

        except Exception as e:
            logger.debug("[MockServer] Exception handling client %s: %s", addr, e)
            try:
                conn.close()
            except Exception:
                pass

    def _stream_ws_frames(self, conn: socket.socket) -> None:
        """Stream all recorded WebSocket frames sequentially to the connected client."""
        try:
            total = len(self.ws_frames)
            for idx, frame_payload in enumerate(self.ws_frames, 1):
                if not self._running:
                    break
                wire_bytes = encode_ws_frame(frame_payload)
                conn.sendall(wire_bytes)
                if self.frame_delay > 0:
                    time.sleep(self.frame_delay)

            logger.info("[MockServer] Finished streaming all %d WebSocket frames.", total)
            # Give client a brief moment to finish receiving before closing
            time.sleep(0.2)
        except (BrokenPipeError, ConnectionResetError):
            logger.info("[MockServer] Client disconnected during frame stream.")
        except Exception as e:
            logger.warning("[MockServer] WebSocket stream error: %s", e)
        finally:
            try:
                conn.close()
            except Exception:
                pass
