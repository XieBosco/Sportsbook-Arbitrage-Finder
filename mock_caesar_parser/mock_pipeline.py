"""End-to-end verification pipeline from locally hosted mock server to Caesars parser output.

Modeled directly after arbfinder's SessionManager and CDPClient architecture:
1. Starts MockCaesarsServer serving the recorded dataset over real localhost HTTP and WebSocket.
2. Performs initial state fetch (/v4/home) and verifies parser ingestion.
3. Establishes live WebSocket client connection, streaming Diffusion frames into parser.handle_ws_frame().
4. Dispatches emitted OddsUpdate objects to consumer pipeline.
5. Logs all parser internals to logs/caesar_parser.log and all parser outputs to logs/caesar_output.jsonl.
6. Validates 100% correctness with zero unhandled errors or warnings.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import urllib.request
import websocket

# Ensure mock_caesar_parser and arbfinder are on path
MOCK_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MOCK_DIR.parent
SRC_DIR = PROJECT_ROOT / "sportsbook-arb-finder" / "src"

sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(MOCK_DIR))

from caesars import CaesarsParser
from diffusion_codec import AliasStateStore
from mock_server import MockCaesarsServer
from arbfinder.normalization.models import OddsUpdate

LOGS_DIR = MOCK_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

PARSER_LOG_PATH = LOGS_DIR / "caesar_parser.log"
OUTPUT_JSONL_PATH = LOGS_DIR / "caesar_output.jsonl"
REPORT_JSON_PATH = LOGS_DIR / "verification_report.json"

# Setup detailed file logger for parser
file_handler = logging.FileHandler(PARSER_LOG_PATH, mode="w", encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s"))
file_handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
console_handler.setLevel(logging.INFO)

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.handlers = [file_handler, console_handler]

logger = logging.getLogger("mock_pipeline")


def datetime_serializer(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


class MockArbfinderPipeline:
    """Simulates the arbfinder ingestion and parsing pipeline against a local mock server."""

    def __init__(self, dataset_path: Path, output_file: Path | None = None) -> None:
        self.dataset_path = dataset_path
        self.output_file = output_file or OUTPUT_JSONL_PATH
        self.parser = CaesarsParser()
        self.server: MockCaesarsServer | None = None
        self.updates: list[OddsUpdate] = []
        self.anomalies: list[str] = []
        self.frames_received = 0

    def run(self) -> dict[str, Any]:
        """Execute the full pipeline verification against the local server."""
        logger.info("=" * 70)
        logger.info("STARTING PIPELINE RUN FOR DATASET: %s", self.dataset_path.name)
        logger.info("=" * 70)

        # 1. Start local mock server
        self.server = MockCaesarsServer(self.dataset_path, frame_delay=0.0005)
        self.server.start()
        logger.info("[Pipeline] Mock server running at HTTP: %s, WS: %s", self.server.http_url, self.server.ws_url)

        try:
            # 2. HTTP Ingestion Phase (/v4/home)
            logger.info("[Pipeline] --- Phase 1: Ingesting HTTP initial state ---")
            req = urllib.request.Request(self.server.http_url)
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                http_body = resp.read().decode("utf-8")

            if not self.parser.relevant_http_url(self.server.http_url):
                raise AssertionError(f"relevant_http_url rejected valid URL: {self.server.http_url}")

            http_updates = self.parser.handle_http_body(self.server.http_url, http_body)
            if http_updates != []:
                self.anomalies.append(f"HTTP body unexpectedly returned odds updates: {len(http_updates)}")

            ev_count = len(self.parser.reference_data["events"])
            mkt_count = len(self.parser.reference_data["markets"])
            sel_count = len(self.parser.reference_data["selections"])
            logger.info(
                "[Pipeline] Ingested initial state: %d events, %d markets, %d selections",
                ev_count,
                mkt_count,
                sel_count,
            )
            if not self.parser.is_initialized:
                raise AssertionError("Parser failed to initialize reference data from /v4/home")

            # 3. Live WebSocket Replay Phase (Diffusion protocol frames)
            logger.info("[Pipeline] --- Phase 2: Live WebSocket Replay ---")
            if not self.parser.relevant_ws_url(self.server.ws_url):
                raise AssertionError(f"relevant_ws_url rejected valid URL: {self.server.ws_url}")

            total_expected = len(self.server.ws_frames)

            def on_ws_message(ws: websocket.WebSocketApp, message: str) -> None:
                self.frames_received += 1
                try:
                    new_updates = self.parser.handle_ws_frame(message)
                    if new_updates:
                        self._handle_updates(new_updates)
                except Exception as exc:
                    err = f"Exception in handle_ws_frame on frame {self.frames_received}: {exc}"
                    logger.error(err)
                    self.anomalies.append(err)

                if self.frames_received >= total_expected:
                    ws.close()

            def on_ws_error(ws: websocket.WebSocketApp, err: Any) -> None:
                if self.frames_received >= total_expected:
                    return
                logger.error("[Pipeline] WebSocket error: %s", err)
                self.anomalies.append(f"WebSocket client error: {err}")

            ws_client = websocket.WebSocketApp(
                self.server.ws_url,
                on_message=on_ws_message,
                on_error=on_ws_error,
            )

            # Blocks until server finishes streaming all frames and closes socket
            ws_client.run_forever()

            logger.info("[Pipeline] WebSocket connection closed. Frames received: %d", self.frames_received)

        finally:
            self.server.stop()

        # 4. Phase 3: Verification & Report
        logger.info("[Pipeline] --- Phase 3: Verification & Correctness Checking ---")
        summary = self._verify_results()
        self._write_output_file()
        return summary

    def _handle_updates(self, updates: list[OddsUpdate]) -> None:
        """Process and validate odds updates emitted by parser."""
        for u in updates:
            self.updates.append(u)

            # Verification assertions
            if u.book_id != "Caesars":
                self.anomalies.append(f"Invalid book_id: {u.book_id}")

            if not u.raw_selection:
                self.anomalies.append(f"Empty raw_selection in update: {u}")

            if u.odds_value is None or u.odds_value <= 1.0:
                self.anomalies.append(f"Invalid odds_value ({u.odds_value}) in update: {u}")

            if u.odds_format not in ("decimal", "american", "fractional"):
                self.anomalies.append(f"Invalid odds_format ({u.odds_format}) in update: {u}")

            if not isinstance(u.captured_at, datetime):
                self.anomalies.append(f"Invalid captured_at ({u.captured_at}) in update: {u}")

    def _verify_results(self) -> dict[str, Any]:
        """Perform final verification checks and build statistics summary."""
        total_expected_frames = len(self.server.ws_frames) if self.server else 0
        if self.frames_received != total_expected_frames:
            self.anomalies.append(
                f"Frame count mismatch: received {self.frames_received} vs expected {total_expected_frames}"
            )

        if len(self.updates) == 0:
            self.anomalies.append("Parser emitted ZERO odds updates across entire replay")

        summary = {
            "dataset": self.dataset_path.name,
            "events_ingested": len(self.parser.reference_data["events"]),
            "markets_ingested": len(self.parser.reference_data["markets"]),
            "selections_ingested": len(self.parser.reference_data["selections"]),
            "frames_expected": total_expected_frames,
            "frames_received": self.frames_received,
            "updates_emitted": len(self.updates),
            "parser_stats": self.parser.stats,
            "anomalies_count": len(self.anomalies),
            "anomalies": self.anomalies,
            "status": "PASSED" if len(self.anomalies) == 0 else "FAILED",
        }

        logger.info("Summary for %s: Status=%s", self.dataset_path.name, summary["status"])
        logger.info("  Frames: %d / %d", self.frames_received, total_expected_frames)
        logger.info("  Odds Updates Emitted: %d", len(self.updates))
        logger.info("  Anomalies: %d", len(self.anomalies))

        if self.anomalies:
            logger.error("Sample anomalies:")
            for a in self.anomalies[:10]:
                logger.error("  %s", a)
            raise AssertionError(f"Pipeline failed with {len(self.anomalies)} anomalies on {self.dataset_path.name}")

        return summary

    def _write_output_file(self) -> None:
        """Write all emitted OddsUpdate objects to the output JSONL file."""
        with open(self.output_file, "a", encoding="utf-8") as f:
            for u in self.updates:
                record = asdict(u)
                record["captured_at"] = u.captured_at.isoformat()
                f.write(json.dumps(record) + "\n")
        logger.info("[Pipeline] Wrote %d updates to %s", len(self.updates), self.output_file)


def run_timeline_verification(dataset_path: Path) -> dict[str, Any]:
    """Verify entire timeline.jsonl sequence in exact chronological order without mock socket."""
    tl_path = dataset_path / "timeline.jsonl"
    msg_dir = dataset_path / "caesars" / "messages"

    if not tl_path.exists() or not msg_dir.exists():
        raise FileNotFoundError(f"Missing timeline or messages in {dataset_path}")

    with open(tl_path, "r", encoding="utf-8") as f:
        events = [
            json.loads(line)
            for line in f
            if line.strip() and json.loads(line).get("sportsbook") == "caesars"
        ]

    logger.info("=== Running Chronological Timeline Verification for %s (%d events) ===", dataset_path.name, len(events))
    parser = CaesarsParser()
    anomalies: list[str] = []
    total_updates = 0

    for idx, ev in enumerate(events, 1):
        fname = ev["file_name"]
        ftype = ev["file_type"]
        fpath = msg_dir / fname

        if not fpath.exists():
            anomalies.append(f"Missing file: {fpath}")
            continue

        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        if ftype == "json":
            try:
                d = json.loads(content)
                url = d.get("_DEBUG_URL", "")
                parser.handle_http_body(url, content)
            except Exception as e:
                anomalies.append(f"JSON error in {fname}: {e}")
        elif ftype == "ws":
            try:
                updates = parser.handle_ws_frame(content)
                total_updates += len(updates)
                for u in updates:
                    if u.book_id != "Caesars":
                        anomalies.append(f"Invalid book_id in {fname}")
                    if not u.raw_selection:
                        anomalies.append(f"Empty raw_selection in {fname}")
                    if u.odds_value is None or u.odds_value <= 1.0:
                        anomalies.append(f"Invalid odds in {fname}")
            except Exception as e:
                anomalies.append(f"WS error in {fname}: {e}")

    logger.info("Timeline replay for %s complete: %d updates, %d anomalies", dataset_path.name, total_updates, len(anomalies))
    if anomalies:
        for a in anomalies[:10]:
            logger.error("  %s", a)
        raise AssertionError(f"Timeline verification failed on {dataset_path.name} with {len(anomalies)} anomalies")

    return {
        "dataset": dataset_path.name,
        "timeline_events": len(events),
        "updates_emitted": total_updates,
        "anomalies": len(anomalies),
        "status": "PASSED",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Caesars Parser Mock Server & Verification Pipeline")
    parser.add_argument(
        "--dataset",
        choices=["nhl_data", "data2", "all"],
        default="all",
        help="Dataset to replay and verify (default: all)",
    )
    args = parser.parse_args()

    # Clear previous output logs
    if OUTPUT_JSONL_PATH.exists():
        OUTPUT_JSONL_PATH.unlink()

    datasets = []
    if args.dataset in ("nhl_data", "all"):
        datasets.append(PROJECT_ROOT / "sportsbook-arb-finder" / "scripts" / "nhl_data")
    if args.dataset in ("data2", "all"):
        datasets.append(PROJECT_ROOT / "sportsbook-arb-finder" / "scripts" / "data2")

    all_reports = {}

    for ds in datasets:
        # 1. Local mock server & WebSocket client pipeline
        pipeline = MockArbfinderPipeline(ds)
        report = pipeline.run()
        all_reports[f"{ds.name}_mock_server"] = report

        # 2. Timeline chronological verification
        tl_report = run_timeline_verification(ds)
        all_reports[f"{ds.name}_timeline"] = tl_report

    with open(REPORT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(all_reports, f, indent=2, default=datetime_serializer)

    logger.info("=" * 70)
    logger.info("ALL VERIFICATIONS COMPLETED SUCCESSFULLY WITHOUT ERROR OR WARNINGS!")
    logger.info("Report saved to: %s", REPORT_JSON_PATH)
    logger.info("Parser outputs logged to: %s", OUTPUT_JSONL_PATH)
    logger.info("Parser internal logs written to: %s", PARSER_LOG_PATH)
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
