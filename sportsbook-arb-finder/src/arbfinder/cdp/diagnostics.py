"""CDP Robustness & Diagnostic Test Runner.

Provides standalone live verification and real-time telemetry for the CDP layer
(discovery.py, client.py, session_manager.py) against a real Chrome instance.
Does NOT depend on any downstream parsers or engines.
"""

import sys
import os
import time
import json
import logging
import argparse
import threading
from dataclasses import dataclass, field
from datetime import datetime

# Allow direct execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from arbfinder.cdp.discovery import list_tabs, find_tab
from arbfinder.cdp.client import CDPClient
from arbfinder.cdp.session_manager import SessionManager
from arbfinder.parsers.base import BookParser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("CDPDiagnostic")


@dataclass
class CDPTelemetry:
    start_time: float = field(default_factory=time.time)
    http_responses_seen: int = 0
    http_bodies_fetched: int = 0
    http_bodies_base64: int = 0
    http_errors: int = 0

    ws_created_count: int = 0
    ws_closed_count: int = 0
    ws_frames_received: int = 0
    ws_frames_allowed: int = 0
    ws_frames_dropped: int = 0
    ws_bytes_received: int = 0

    untracked_frames_warned: int = 0
    last_report_time: float = field(default_factory=time.time)

    def print_summary(self, final: bool = False):
        now = time.time()
        elapsed = max(1.0, now - self.start_time)
        fps = self.ws_frames_received / elapsed
        kbps = (self.ws_bytes_received / 1024.0) / elapsed

        header = (
            "=== CDP LIVE TELEMETRY SUMMARY ==="
            if final
            else "--- CDP Live Diagnostics Update ---"
        )
        print(f"\n{header}")
        print(f"Elapsed Time           : {elapsed:.1f}s")
        print(f"HTTP Responses Seen    : {self.http_responses_seen}")
        print(
            f"HTTP Bodies Fetched    : {self.http_bodies_fetched} (Base64: {self.http_bodies_base64}, Errors: {self.http_errors})"
        )
        print(
            f"WebSockets Tracked     : Created: {self.ws_created_count}, Closed: {self.ws_closed_count}"
        )
        print(
            f"WebSocket Frames Total : {self.ws_frames_received} ({fps:.1f} frames/sec, {kbps:.2f} KB/sec)"
        )
        print(f"  └─ Passed URL Filter : {self.ws_frames_allowed}")
        print(f"  └─ Filtered / Dropped: {self.ws_frames_dropped}")
        print(f"{'=' * 35 if final else '-' * 35}\n")


class MockDiagnosticParser(BookParser):
    """Zero-dependency mock parser for multi-tab SessionManager stress testing."""

    def __init__(
        self, book_name: str, http_filter_kw: str = "", ws_filter_kw: str = ""
    ):
        self.book_name = book_name
        self.http_filter_kw = http_filter_kw
        self.ws_filter_kw = ws_filter_kw

    def relevant_http_url(self, url: str) -> bool:
        return (
            self.http_filter_kw.lower() in url.lower() if self.http_filter_kw else True
        )

    def relevant_ws_url(self, url: str) -> bool:
        return self.ws_filter_kw.lower() in url.lower() if self.ws_filter_kw else True

    def handle_http_body(self, url: str, body: str) -> list:
        logger.info(
            f"[{self.book_name}] Captured HTTP body from {url[:80]}... (Length: {len(body)} chars)"
        )
        return []

    def handle_ws_frame(self, payload: str) -> list:
        preview = payload[:100].replace("\n", " ")
        logger.info(
            f"[{self.book_name}] Captured WS frame: {preview}... (Length: {len(payload)} bytes)"
        )
        return []


def test_discovery_and_list_tabs(port: int) -> list[dict]:
    """Test discovery against Chrome port and return list of tabs."""
    print(f"\n[1/4] Probing Chrome Remote Debugging on port {port}...")
    tabs = list_tabs(port=port)

    if not tabs:
        print(f"[!] FAILED: No Chrome tabs found on http://127.0.0.1:{port}/json")
        print("[!] To launch Chrome with remote debugging on Windows, run:")
        print(
            f'    & "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port={port} --user-data-dir="$env:TEMP\\chrome_cdp_profile"\n'
        )
        return []

    print(f"[✔] SUCCESS: Discovered {len(tabs)} target(s) on port {port}:\n")
    page_tabs = []
    for i, tab in enumerate(tabs, 1):
        tab_type = tab.get("type", "unknown")
        title = tab.get("title", "No Title")
        url = tab.get("url", "No URL")
        ws_url = tab.get("webSocketDebuggerUrl", "None")

        is_page = tab_type == "page" and not url.startswith("devtools://")
        marker = "[PAGE]" if is_page else f"[{tab_type.upper()}]"
        print(f'  {i}. {marker} "{title}"')
        print(f"     URL: {url}")
        print(f"     WS : {ws_url[:70]}...")
        if is_page:
            page_tabs.append(tab)

    print(f"\nTotal connectable page tabs: {len(page_tabs)}")
    return page_tabs


def run_single_tab_diagnostic(
    tab: dict,
    http_filter_str: str = "",
    ws_filter_str: str = "",
    duration_secs: int = 0,
    dump_file: str | None = None,
) -> CDPTelemetry:
    """Run an in-depth diagnostic session on a single tab using CDPClient."""
    ws_debugger_url = tab.get("webSocketDebuggerUrl")
    if not ws_debugger_url:
        logger.error(f"Tab '{tab.get('title')}' has no webSocketDebuggerUrl!")
        return CDPTelemetry()

    telemetry = CDPTelemetry()
    dump_fp = open(dump_file, "a", encoding="utf-8") if dump_file else None

    print(f'\n[2/4] Attaching CDPClient to tab: "{tab.get("title")}"')
    print(f"      WS Debugger: {ws_debugger_url}")
    print(f"      HTTP Filter: '{http_filter_str or 'ALL'}'")
    print(f"      WS Filter  : '{ws_filter_str or 'ALL'}'")
    if duration_secs > 0:
        print(f"      Duration   : {duration_secs}s")
    else:
        print("      Duration   : Indefinite (Press Ctrl+C to stop)")
    print(
        "\nListening for network events... (Refresh the tab in Chrome to trigger reference loads!)\n"
    )

    def http_filter(url: str) -> bool:
        telemetry.http_responses_seen += 1
        matches = http_filter_str.lower() in url.lower() if http_filter_str else True
        if matches:
            logger.debug(f"[HTTP IN] Intercepting: {url[:90]}")
        return matches

    def on_http_body(url: str, body: str):
        telemetry.http_bodies_fetched += 1
        preview = body[:120].replace("\n", " ")
        logger.info(
            f"[HTTP BODY FETCHED] URL: {url[:80]}... | Size: {len(body):,} bytes | Preview: {preview}..."
        )
        if dump_fp:
            dump_fp.write(
                json.dumps(
                    {
                        "type": "http",
                        "timestamp": datetime.now().isoformat(),
                        "url": url,
                        "body_length": len(body),
                        "body_preview": body[:1000],
                    }
                )
                + "\n"
            )
            dump_fp.flush()

    def ws_filter(url: str) -> bool:
        matches = ws_filter_str.lower() in url.lower() if ws_filter_str else True
        return matches

    def on_ws_frame(payload: str):
        telemetry.ws_frames_allowed += 1
        telemetry.ws_bytes_received += len(payload)
        preview = payload[:100].replace("\n", " ")
        logger.info(
            f"[WS FRAME MATCH] Size: {len(payload):,} bytes | Preview: {preview}..."
        )
        if dump_fp:
            dump_fp.write(
                json.dumps(
                    {
                        "type": "ws_frame",
                        "timestamp": datetime.now().isoformat(),
                        "size": len(payload),
                        "payload_preview": payload[:500],
                    }
                )
                + "\n"
            )
            dump_fp.flush()

    client = CDPClient(
        ws_url=ws_debugger_url,
        url_filter=http_filter,
        on_http_body=on_http_body,
        on_ws_frame=on_ws_frame,
        ws_url_filter=ws_filter,
    )

    # Wrap original _on_message to collect low-level frame metrics
    original_on_message = client._on_message

    def instrumented_on_message(ws, message: str):
        try:
            data = json.loads(message)
            method = data.get("method")
            if method == "Network.webSocketCreated":
                telemetry.ws_created_count += 1
                logger.info(
                    f"[WS CREATED] ID: {data.get('params', {}).get('requestId')} | URL: {data.get('params', {}).get('url')}"
                )
            elif method == "Network.webSocketClosed":
                telemetry.ws_closed_count += 1
                logger.info(
                    f"[WS CLOSED] ID: {data.get('params', {}).get('requestId')}"
                )
            elif method == "Network.webSocketFrameReceived":
                telemetry.ws_frames_received += 1
                req_id = data.get("params", {}).get("requestId")
                if req_id not in client.active_websockets:
                    telemetry.untracked_frames_warned += 1
            elif (
                "id" in data
                and "result" in data
                and data.get("result", {}).get("base64Encoded")
            ):
                telemetry.http_bodies_base64 += 1
        except Exception:
            pass
        original_on_message(ws, message)

    client._on_message = instrumented_on_message

    # Background runner thread
    client_thread = threading.Thread(target=client.run, daemon=True)
    client_thread.start()

    # Telemetry reporter loop
    try:
        start_t = time.time()
        while client_thread.is_alive():
            time.sleep(5)
            telemetry.print_summary(final=False)
            if duration_secs > 0 and (time.time() - start_t) >= duration_secs:
                logger.info(f"Test duration of {duration_secs}s reached.")
                break
    except KeyboardInterrupt:
        print("\nStopping diagnostic session (Ctrl+C caught)...")
    finally:
        client.close()
        client_thread.join(timeout=2)
        if dump_fp:
            dump_fp.close()

    telemetry.print_summary(final=True)
    return telemetry


def run_session_manager_stress_test(tabs: list[dict], duration_secs: int = 15):
    """Test SessionManager concurrency, reattach loop, and shutdown with mock parsers."""
    print(
        f"\n[3/4] Running SessionManager multi-tab concurrency test ({duration_secs}s)..."
    )

    mock_parsers = []
    for tab in tabs[:3]:
        title = tab.get("title", "tab")
        kw = title.split()[0] if title else "tab"
        mock_parsers.append(MockDiagnosticParser(book_name=kw))

    if not mock_parsers:
        mock_parsers.append(MockDiagnosticParser(book_name="General"))

    updates_received = []
    manager = SessionManager(
        parsers=mock_parsers,
        on_odds_update=lambda updates: updates_received.extend(updates),
    )

    print(f"Starting SessionManager with {len(mock_parsers)} mock parser targets...")
    manager.start()

    try:
        for remaining in range(duration_secs, 0, -1):
            time.sleep(1)
            print(
                f"  SessionManager active clients: {len(manager._clients)} | Active threads: {len(manager._threads)} | Time remaining: {remaining}s",
                end="\r",
            )
        print()
    finally:
        print("\n[4/4] Testing non-blocking SessionManager.stop()...")
        t0 = time.time()
        manager.stop()
        stop_duration = time.time() - t0
        print(
            f"[✔] SessionManager stopped successfully in {stop_duration:.4f}s (Remaining clients: {len(manager._clients)})"
        )


def main():
    parser = argparse.ArgumentParser(
        description="CDP Layer Diagnostic & Robustness Test Runner"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=19222,
        help="Chrome Remote Debugging Port (default: 19222)",
    )
    parser.add_argument(
        "--tab",
        type=str,
        default="",
        help="Tab title or URL substring to match (default: prompts/first)",
    )
    parser.add_argument(
        "--http-filter",
        type=str,
        default="",
        help="Keyword substring to filter HTTP response URLs",
    )
    parser.add_argument(
        "--ws-filter",
        type=str,
        default="",
        help="Keyword substring to filter WebSocket URLs",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=0,
        help="Test duration in seconds (0 = run until Ctrl+C)",
    )
    parser.add_argument(
        "--session-manager-test",
        action="store_true",
        help="Run SessionManager multi-tab test instead of single-tab client",
    )
    parser.add_argument(
        "--dump-file",
        type=str,
        default=None,
        help="Optional path to write raw JSON telemetry log",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("      SPORTSBOOK ARBITRAGE FINDER - CDP DIAGNOSTIC RUNNER")
    print("=" * 60)

    # 1. Test Discovery
    page_tabs = test_discovery_and_list_tabs(port=args.port)
    if not page_tabs:
        sys.exit(1)

    # 2. SessionManager Multi-Tab Test Mode
    if args.session_manager_test:
        run_session_manager_stress_test(page_tabs, duration_secs=args.duration or 15)
        sys.exit(0)

    # 3. Find or Select Tab
    target_tab = None
    if args.tab:
        target_tab = find_tab(args.tab, port=args.port)
        if not target_tab:
            print(f"[!] No tab found matching '--tab {args.tab}'")
            print("Available tabs:")
            for t in page_tabs:
                print(f" - {t.get('title')} ({t.get('url')})")
            sys.exit(1)
    else:
        # Default to first page tab
        target_tab = page_tabs[0]
        print(
            f'\nNo --tab pattern specified. Defaulting to first tab: "{target_tab.get("title")}"'
        )

    # 4. Run Live Diagnostic Session
    run_single_tab_diagnostic(
        tab=target_tab,
        http_filter_str=args.http_filter,
        ws_filter_str=args.ws_filter,
        duration_secs=args.duration,
        dump_file=args.dump_file,
    )


if __name__ == "__main__":
    main()
