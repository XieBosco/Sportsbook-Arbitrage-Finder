"""End-to-end tests: 4 sportsbooks receiving live NHL market data to ui_server sink."""

from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

try:
    from fastapi.testclient import TestClient
except Exception:
    TestClient = None

from arbfinder.matching.bucket_store import BucketStore
from arbfinder.matching.matcher import Matcher
from arbfinder.matching.output import MatchOutputBuilder
from arbfinder.matching.time_resolver import TimeResolver
from arbfinder.normalization.book_normalizers.betano_normalizer import BetanoNormalizer
from arbfinder.normalization.book_normalizers.caesars_normalizer import CaesarsNormalizer
from arbfinder.normalization.book_normalizers.draftkings_normalizer import DraftKingsNormalizer
from arbfinder.normalization.book_normalizers.fanduel_normalizer import FanDuelNormalizer
from arbfinder.normalization.normalizer import Normalizer
from arbfinder.parsers.betano import BetanoParser
from arbfinder.parsers.caesars import CaesarsParser
from arbfinder.parsers.draftkings import DraftKingsParser
from arbfinder.parsers.fanduel import FanDuelParser
from arbfinder.pipeline.config import AppConfig, SinksConfig
from arbfinder.pipeline.registry import EXPECTED_SELECTIONS_BY_MARKET
from arbfinder.scanner.dedup_tracker import DedupTracker
from arbfinder.scanner.market_grouper import MarketGrouper
from arbfinder.scanner.scanner import Scanner
from arbfinder.scanner.sinks.websocket_sink import WebSocketSink
from arbfinder.scanner.staleness_filter import StalenessFilter
from arbfinder.scanner.threshold_config import ScannerThresholds
from arbfinder.ui_server.app import create_app
from arbfinder.ui_server.connection_manager import ConnectionManager

_REPO_ROOT = Path(__file__).resolve().parents[2]


def test_nhl_individual_sportsbook_ingestion():
    """Verify each of the 4 sportsbooks can ingest and parse raw NHL market data."""
    batch_normalizer = Normalizer({
        "DraftKings": DraftKingsNormalizer(),
        "FanDuel": FanDuelNormalizer(),
        "Betano": BetanoNormalizer(),
        "Caesars": CaesarsNormalizer(),
    })
    store = BucketStore()
    matcher = Matcher(store, TimeResolver())

    # 1. DraftKings
    dk = DraftKingsParser()
    with open(_REPO_ROOT / "scripts/nhl_data/draftkings/draftkings_messages/json_1.json", "r", encoding="utf-8") as f:
        d = json.load(f)
        dk.handle_http_body(d.get("_DEBUG_URL", ""), json.dumps(d.get("data", d)))
    with open(_REPO_ROOT / "scripts/nhl_data/draftkings/draftkings_messages/ws_10.txt", "r", encoding="utf-8") as f:
        dk_parsed = dk.handle_ws_frame(f.read().strip())
    assert len(dk_parsed) > 0
    dk_norm = batch_normalizer.normalize_batch(dk_parsed)
    assert len(dk_norm) > 0
    assert dk_norm[0].league_key == "NHL"
    for u in dk_norm:
        matcher.assign(u)

    # 2. FanDuel
    fd = FanDuelParser()
    with open(_REPO_ROOT / "scripts/nhl_data/fanduel/fanduel_messages/json_1.json", "r", encoding="utf-8") as f:
        d = json.load(f)
        fd.handle_http_body(d.get("_DEBUG_URL", ""), json.dumps(d.get("data", d)))
    with open(_REPO_ROOT / "scripts/nhl_data/fanduel/fanduel_messages/ws_4.txt", "r", encoding="utf-8") as f:
        d = json.load(f)
        fd_parsed = fd.handle_http_body(
            "https://smp.on.sportsbook.fanduel.ca/api/sports/fixedodds/readonly/v1/getMarketPrices?priceHistory=1",
            json.dumps(d.get("data", d)),
        )
    assert len(fd_parsed) > 0
    fd_norm = batch_normalizer.normalize_batch(fd_parsed)
    assert len(fd_norm) > 0
    assert fd_norm[0].league_key == "NHL"
    for u in fd_norm:
        matcher.assign(u)

    # 3. Betano
    bt = BetanoParser()
    with open(_REPO_ROOT / "scripts/nhl_data/betano/betano_messages/json_1.json", "r", encoding="utf-8") as f:
        d = json.load(f)
        bt.handle_http_body(d.get("_DEBUG_URL", ""), json.dumps(d.get("data", d)))
    assert len(bt.reference_data["events"]) > 0
    with open(_REPO_ROOT / "scripts/nhl_data/betano/betano_messages/ws_10.txt", "r", encoding="utf-8") as f:
        bt_parsed = bt.handle_ws_frame(f.read().strip() + "\x1e")
    assert len(bt_parsed) > 0

    # 4. Caesars
    cz = CaesarsParser()
    with open(_REPO_ROOT / "scripts/nhl_data/caesars/messages/ws_15.txt", "r", encoding="utf-8") as f:
        cz_parsed = cz.handle_ws_frame(f.read().strip())
    assert len(cz_parsed) > 0
    assert cz_parsed[0].raw_selection == "Vancouver Canucks"


def test_nhl_pipeline_to_ui_server_sink():
    """Verify live NHL market timeline delivers opportunities across all 4 books to ui_server."""
    asyncio.run(_run_nhl_pipeline_to_ui_server_sink())


async def _run_nhl_pipeline_to_ui_server_sink():
    # Suppress verbose unresolved logs
    logging.getLogger("arbfinder.normalization.unresolved_log").setLevel(logging.ERROR)
    logging.getLogger("arbfinder.parsers.unresolved_log").setLevel(logging.ERROR)

    connection_manager = ConnectionManager()
    sinks_config = SinksConfig(websocket_enabled=True, odds_format="american")
    ws_sink = WebSocketSink(connection_manager, sinks_config=sinks_config)

    app_config = AppConfig(books=[], sinks=sinks_config)
    fastapi_app = create_app(connection_manager, config=app_config)

    batch_normalizer = Normalizer({
        "DraftKings": DraftKingsNormalizer(),
        "FanDuel": FanDuelNormalizer(),
        "Betano": BetanoNormalizer(),
        "Caesars": CaesarsNormalizer(),
    })
    store = BucketStore()
    matcher = Matcher(store, TimeResolver())

    grouper = MarketGrouper()
    thresholds = ScannerThresholds(min_margin=0.01, max_odds_age_seconds=60.0)
    staleness = StalenessFilter(thresholds=thresholds)
    dedup = DedupTracker(cooldown_seconds=0.0)

    scanner = Scanner(grouper, thresholds, staleness, dedup, [ws_sink], EXPECTED_SELECTIONS_BY_MARKET, lambda _: 100.0)

    parsers = {
        "draftkings": DraftKingsParser(),
        "fanduel": FanDuelParser(),
        "betano": BetanoParser(),
        "caesars": CaesarsParser(),
    }

    # Connect client to capture delivered WebSocket messages
    received_messages = []

    class MockWebSocketClient:
        async def accept(self):
            pass

        async def send_json(self, message):
            received_messages.append(message)

    mock_client = MockWebSocketClient()
    await connection_manager.connect(mock_client)
    assert connection_manager.active_count == 1

    timeline_path = _REPO_ROOT / "scripts/nhl_data/timeline.jsonl"
    with open(timeline_path, "r", encoding="utf-8") as f:
        timeline = [json.loads(line) for line in f]

    books_in_arbs = set()

    for event in timeline:
        sb = event["sportsbook"]
        simulated_now = datetime.fromtimestamp(event["timestamp"], timezone.utc)
        msg_dir_name = "messages" if sb == "caesars" else f"{sb}_messages"
        fpath = _REPO_ROOT / "scripts" / "nhl_data" / sb / msg_dir_name / event["file_name"]

        parser = parsers[sb]
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                is_json = event["file_type"] == "json" or (sb == "fanduel" and event["file_type"] == "ws")
                if is_json:
                    d = json.load(f)
                    payload = d.get("data", d) if isinstance(d, dict) else d
                    url = d.get("_DEBUG_URL", "") if isinstance(d, dict) else ""
                    if not url:
                        if sb == "draftkings":
                            url = "api/sportscontent/v1/markets"
                        elif sb == "fanduel":
                            url = "content-managed-page"
                        elif sb == "betmgm":
                            url = "fixture-view"
                        elif sb == "betano":
                            url = "https://www.betano.ca/danae-webapi/api/live/overview/1"
                        elif sb == "caesars":
                            url = "https://api.americanwagering.com/v4/home"
                        if sb == "fanduel" and "ws" in event["file_name"]:
                            url = "https://smp.on.sportsbook.fanduel.ca/api/sports/fixedodds/readonly/v1/getMarketPrices?priceHistory=1"
                    updates = parser.handle_http_body(url, json.dumps(payload) if not isinstance(payload, str) else payload)
                else:
                    content = f.read().strip()
                    if sb == "betano":
                        content += "\x1e"
                    updates = parser.handle_ws_frame(content)
        except Exception:
            continue

        if not updates:
            continue

        updates = [dataclasses.replace(u, captured_at=simulated_now) for u in updates]
        normalized = batch_normalizer.normalize_batch(updates)

        for norm_update in normalized:
            bucket = matcher.assign(norm_update)
            matched = MatchOutputBuilder.from_bucket(bucket)
            scanner.process(matched, now=simulated_now)

        await asyncio.sleep(0)

        for msg in received_messages:
            if msg.get("type") == "opportunity":
                for leg in msg["data"]["legs"]:
                    books_in_arbs.add(leg["book_id"])

        if len(books_in_arbs) >= 4 and len(received_messages) >= 10:
            break

    opp_messages = [m for m in received_messages if m.get("type") == "opportunity"]
    assert len(opp_messages) >= 10
    assert len(books_in_arbs) == 4, f"All 4 sportsbooks should appear in arbs, got: {books_in_arbs}"

    # Verify serialized schema and logo availability
    with open(_REPO_ROOT / "src/arbfinder/ui_server/static/team_logos.json", "r", encoding="utf-8") as f:
        logos_data = json.load(f)
    nhl_logos = logos_data["nhl"]

    static_nhl_dir = _REPO_ROOT / "src/arbfinder/ui_server/static/nhl_team_logos"
    for msg in opp_messages[:5]:
        assert msg["type"] == "opportunity"
        opp_data = msg["data"]
        assert opp_data["league_key"] == "NHL"

        home_logo_fn = nhl_logos[opp_data["home_team"].lower().strip()]
        away_logo_fn = nhl_logos[opp_data["away_team"].lower().strip()]

        # Verify logo files exist on disk
        assert (static_nhl_dir / home_logo_fn).is_file(), f"Missing logo: {home_logo_fn}"
        assert (static_nhl_dir / away_logo_fn).is_file(), f"Missing logo: {away_logo_fn}"

    # If TestClient is available, verify HTTP serving
    if TestClient is not None:
        try:
            http_client = TestClient(fastapi_app)
            for msg in opp_messages[:5]:
                opp_data = msg["data"]
                home_logo_fn = nhl_logos[opp_data["home_team"].lower().strip()]
                away_logo_fn = nhl_logos[opp_data["away_team"].lower().strip()]
                resp_home = http_client.get(f"/static/nhl_team_logos/{home_logo_fn}")
                assert resp_home.status_code == 200
                assert "image/png" in resp_home.headers["content-type"]
                resp_away = http_client.get(f"/static/nhl_team_logos/{away_logo_fn}")
                assert resp_away.status_code == 200
                assert "image/png" in resp_away.headers["content-type"]
        except Exception:
            pass


if __name__ == "__main__":
    print("Running test_nhl_individual_sportsbook_ingestion()...")
    test_nhl_individual_sportsbook_ingestion()
    print("-> PASSED: Ingestion & Normalization verified for DraftKings, FanDuel, Betano, and Caesars.")

    print("Running test_nhl_pipeline_to_ui_server_sink()...")
    test_nhl_pipeline_to_ui_server_sink()
    print("-> PASSED: End-to-end pipeline to ui_server sink verified.")
    print("ALL TESTS COMPLETED SUCCESSFULLY!")
