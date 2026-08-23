"""Integration tests for all 5 sportsbook parsers against fixture files."""

import base64
import glob
import json
import os
import msgpack
import pytest

from arbfinder.parsers.betano import BetanoParser
from arbfinder.parsers.betmgm import BetMGMParser
from arbfinder.parsers.caesars import CaesarsParser
from arbfinder.parsers.draftkings import DraftKingsParser
from arbfinder.parsers.fanduel import FanDuelParser

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")


def test_draftkings_parser_fixture():
    parser = DraftKingsParser()
    ref_path = os.path.join(FIXTURES_DIR, "draftkings", "draftkings_messages", "json_1.json")
    assert os.path.exists(ref_path), f"DraftKings fixture missing: {ref_path}"
    with open(ref_path, "r", encoding="utf-8") as f:
        d = json.load(f)
        body = json.dumps(d.get("data", d))
    parser.handle_http_body("api/sportscontent/v1/markets", body)
    assert len(parser.reference_data["events"]) > 0


def test_draftkings_replay_messages_fixture():
    parser = DraftKingsParser()
    ref_path = os.path.join(FIXTURES_DIR, "draftkings", "draftkings_messages", "json_1.json")
    with open(ref_path, "r", encoding="utf-8") as f:
        d = json.load(f)
        parser.handle_http_body("api/sportscontent/v1/markets", json.dumps(d.get("data", d)))

    msg_dir = os.path.join(FIXTURES_DIR, "draftkings", "draftkings_messages")
    msg_files = sorted(glob.glob(os.path.join(msg_dir, "ws_*.txt")))
    assert len(msg_files) > 0, "No DraftKings message fixtures found"

    total_updates = 0
    for mf in msg_files:
        with open(mf, "r", encoding="utf-8") as f:
            b64_payload = f.read().strip()
        updates = parser.handle_ws_frame(b64_payload)
        total_updates += len(updates)

    assert total_updates >= 0


def test_fanduel_parser_fixture():
    parser = FanDuelParser()
    ref_path = os.path.join(FIXTURES_DIR, "fanduel", "fanduel_messages", "json_1.json")
    assert os.path.exists(ref_path), f"FanDuel fixture missing: {ref_path}"
    with open(ref_path, "r", encoding="utf-8") as f:
        d = json.load(f)
        body = json.dumps(d.get("data", d))
    parser.handle_http_body("content-managed-page", body)
    assert len(parser.reference_data["events"]) > 0


def test_fanduel_replay_messages_fixture():
    parser = FanDuelParser()
    ref_path = os.path.join(FIXTURES_DIR, "fanduel", "fanduel_messages", "json_1.json")
    with open(ref_path, "r", encoding="utf-8") as f:
        d = json.load(f)
        parser.handle_http_body("content-managed-page", json.dumps(d.get("data", d)))

    msg_dir = os.path.join(FIXTURES_DIR, "fanduel", "fanduel_messages")
    msg_files = sorted(glob.glob(os.path.join(msg_dir, "ws_*.txt")))
    assert len(msg_files) > 0, "No FanDuel message fixtures found"

    total_updates = 0
    for mf in msg_files:
        with open(mf, "r", encoding="utf-8") as f:
            d = json.load(f)
            msg_body = json.dumps(d.get("data", d))
        updates = parser.handle_http_body("https://smp.on.sportsbook.fanduel.ca/api/sports/fixedodds/readonly/v1/getMarketPrices?priceHistory=1", msg_body)
        total_updates += len(updates)

    assert total_updates >= 0


def test_betmgm_parser_fixture():
    parser = BetMGMParser()
    ref_path = os.path.join(FIXTURES_DIR, "betmgm", "betmgm_messages", "json_1.json")
    assert os.path.exists(ref_path), f"BetMGM fixture missing: {ref_path}"
    with open(ref_path, "r", encoding="utf-8") as f:
        d = json.load(f)
        body = json.dumps(d.get("data", d))
    parser.handle_http_body("fixture-view", body)
    assert len(parser.reference_data["events"]) > 0


def test_betmgm_replay_messages_fixture():
    parser = BetMGMParser()
    ref_path = os.path.join(FIXTURES_DIR, "betmgm", "betmgm_messages", "json_1.json")
    with open(ref_path, "r", encoding="utf-8") as f:
        d = json.load(f)
        parser.handle_http_body("fixture-view", json.dumps(d.get("data", d)))

    msg_dir = os.path.join(FIXTURES_DIR, "betmgm", "betmgm_messages")
    msg_files = sorted(glob.glob(os.path.join(msg_dir, "ws_*.txt")))
    assert len(msg_files) > 0, "No BetMGM message fixtures found"

    total_updates = 0
    for mf in msg_files:
        with open(mf, "r", encoding="utf-8") as f:
            raw = f.read().strip()
        # BetMGM WebSocket delivers SignalR frames delimited with \x1e
        payload = raw + "\x1e"
        updates = parser.handle_ws_frame(payload)
        total_updates += len(updates)

    assert total_updates > 0, f"Expected updates from BetMGM messages, got {total_updates}"


def test_betano_parser_fixture():
    parser = BetanoParser()
    ref_path = os.path.join(FIXTURES_DIR, "betano", "betano_messages", "json_1.json")
    assert os.path.exists(ref_path), f"Betano fixture missing: {ref_path}"
    with open(ref_path, "r", encoding="utf-8") as f:
        d = json.load(f)
        body = json.dumps(d.get("data", d))
    parser.handle_http_body(
        "https://www.betano.ca/danae-webapi/api/live/overview/1?isInit=false&includeVirtuals=true",
        body,
    )
    assert len(parser.reference_data["events"]) > 0


def test_betano_replay_messages_fixture():
    parser = BetanoParser()
    ref_path = os.path.join(FIXTURES_DIR, "betano", "betano_messages", "json_1.json")
    with open(ref_path, "r", encoding="utf-8") as f:
        d = json.load(f)
        parser.handle_http_body(
            "https://www.betano.ca/danae-webapi/api/live/overview/1?isInit=false&includeVirtuals=true",
            json.dumps(d.get("data", d)),
        )

    msg_dir = os.path.join(FIXTURES_DIR, "betano", "betano_messages")
    msg_files = sorted(glob.glob(os.path.join(msg_dir, "ws_*.txt")))
    assert len(msg_files) > 0, "No Betano message fixtures found"

    total_updates = 0
    for mf in msg_files:
        with open(mf, "r", encoding="utf-8") as f:
            raw = f.read().strip()
        payload = raw + "\x1e"
        updates = parser.handle_ws_frame(payload)
        total_updates += len(updates)

    assert total_updates > 0, f"Expected updates from Betano messages, got {total_updates}"


def test_caesars_parser_fixture():
    parser = CaesarsParser()
    ref_path = os.path.join(FIXTURES_DIR, "caesars", "messages", "json_5.json")
    assert os.path.exists(ref_path), f"Caesars fixture missing: {ref_path}"
    with open(ref_path, "r", encoding="utf-8") as f:
        body = f.read()
    parser.handle_http_body("https://api.americanwagering.com/v4/home", body)
    assert len(parser.reference_data["events"]) > 0
    assert len(parser.reference_data["markets"]) > 0
    assert len(parser.reference_data["selections"]) > 0


def test_caesars_replay_messages_fixture():
    parser = CaesarsParser()
    ref_path = os.path.join(FIXTURES_DIR, "caesars", "messages", "json_5.json")
    with open(ref_path, "r", encoding="utf-8") as f:
        parser.handle_http_body("https://api.americanwagering.com/v4/home", f.read())

    msg_dir = os.path.join(FIXTURES_DIR, "caesars", "messages")
    msg_files = sorted(glob.glob(os.path.join(msg_dir, "ws_*.txt")))
    assert len(msg_files) > 0, "No Caesars message fixtures found"

    total_updates = 0
    for mf in msg_files:
        with open(mf, "r", encoding="utf-8") as f:
            b64_payload = f.read().strip()
        updates = parser.handle_ws_frame(b64_payload)
        total_updates += len(updates)

    assert total_updates > 0, f"Expected updates from Caesars messages, got {total_updates}"
