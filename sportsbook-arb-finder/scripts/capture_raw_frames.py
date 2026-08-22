"""Script for capturing raw CDP frames and HTTP bodies for offline debugging and fixture generation."""
import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime

# Allow direct execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from arbfinder.cdp.discovery import find_tab, list_tabs
from arbfinder.cdp.client import CDPClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("RawCapture")

def main() -> None:
    """Parse arguments and start capturing CDP frames."""
    parser = argparse.ArgumentParser(description="Capture raw CDP frames and HTTP responses to JSONL")
    parser.add_argument("--port", type=int, default=19222, help="CDP debug port")
    parser.add_argument("--url-pattern", type=str, required=True, help="URL or title substring to match")
    parser.add_argument("--out", type=str, required=True, help="Output file path (.jsonl)")
    parser.add_argument("--duration", type=int, default=0, help="Capture duration in seconds (0 = until Ctrl+C)")
    args = parser.parse_args()

    tab = find_tab(args.url_pattern, port=args.port)
    if not tab:
        logger.error(f"No tab matching '{args.url_pattern}' found on port {args.port}.")
        tabs = list_tabs(args.port)
        if tabs:
            logger.info("Open tabs:")
            for t in tabs:
                logger.info(f" - {t.get('title')} ({t.get('url')})")
        sys.exit(1)

    ws_url = tab.get("webSocketDebuggerUrl")
    if not ws_url:
        logger.error(f"Tab '{tab.get('title')}' has no webSocketDebuggerUrl.")
        sys.exit(1)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    out_file = open(args.out, "a", encoding="utf-8")
    logger.info(f"Capturing traffic from \"{tab.get('title')}\" to {args.out}...")

    def on_http_body(url: str, body: str):
        record = {
            "type": "http",
            "timestamp": datetime.now().isoformat(),
            "url": url,
            "body": body
        }
        out_file.write(json.dumps(record) + "\n")
        out_file.flush()
        logger.info(f"[HTTP] Saved response from {url[:80]} ({len(body):,} chars)")

    def on_ws_frame(payload: str):
        record = {
            "type": "ws_frame",
            "timestamp": datetime.now().isoformat(),
            "payload": payload
        }
        out_file.write(json.dumps(record) + "\n")
        out_file.flush()
        logger.info(f"[WS] Saved frame ({len(payload):,} bytes)")

    client = CDPClient(
        ws_url=ws_url,
        url_filter=lambda u: True,
        on_http_body=on_http_body,
        on_ws_frame=on_ws_frame,
        ws_url_filter=lambda u: True
    )

    try:
        if args.duration > 0:
            import threading
            t = threading.Thread(target=client.run, daemon=True)
            t.start()
            time.sleep(args.duration)
            client.close()
        else:
            client.run()
    except KeyboardInterrupt:
        logger.info("Capture stopped by user.")
    finally:
        client.close()
        out_file.close()
        logger.info(f"Capture completed. Data written to {args.out}")

if __name__ == "__main__":
    main()
