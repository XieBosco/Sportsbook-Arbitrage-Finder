"""Unit tests for Caesars parser (caesars.py)."""

import base64
import json
import os
import zlib
import pytest

from arbfinder.parsers.caesars import CaesarsParser
from arbfinder.parsers.diffusion_codec import decode_cbor_item

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")


@pytest.fixture
def sample_home_json():
    """Simulate a /v4/home REST response."""
    return {
        "data": {
            "eventDisplayGroups": [
                {
                    "events": [
                        {
                            "id": "event-100",
                            "name": "Boston Red Sox at New York Yankees",
                            "keyMarketGroups": [
                                {
                                    "markets": [
                                        {
                                            "id": "market-200",
                                            "name": "Moneyline",
                                            "line": None,
                                            "selections": [
                                                {
                                                    "id": "sel-301",
                                                    "name": "Boston Red Sox",
                                                },
                                                {
                                                    "id": "sel-302",
                                                    "name": "New York Yankees",
                                                },
                                            ],
                                        },
                                        {
                                            "id": "market-201",
                                            "name": "Run Line",
                                            "line": 1.5,
                                            "selections": [
                                                {
                                                    "id": "sel-303",
                                                    "name": "Boston Red Sox +1.5",
                                                },
                                            ],
                                        },
                                    ]
                                }
                            ],
                        }
                    ]
                }
            ]
        }
    }


def test_caesars_url_matching():
    parser = CaesarsParser()
    assert parser.relevant_http_url("https://api.americanwagering.com/v4/home")
    assert not parser.relevant_http_url("https://api.americanwagering.com/v1/other")

    assert parser.relevant_ws_url("wss://api.americanwagering.com/diffusion?ty=WB")
    assert not parser.relevant_ws_url("wss://otherbook.com/ws")


def test_caesars_http_reference_parsing(sample_home_json):
    parser = CaesarsParser()
    parser.handle_http_body("https://api.americanwagering.com/v4/home", json.dumps(sample_home_json))

    assert "event-100" in parser.reference_data["events"]
    assert parser.reference_data["events"]["event-100"]["name"] == "Boston Red Sox at New York Yankees"

    assert "market-200" in parser.reference_data["markets"]
    assert parser.reference_data["markets"]["market-200"]["name"] == "Moneyline"

    assert "sel-301" in parser.reference_data["selections"]
    assert parser.reference_data["selections"]["sel-301"]["name"] == "Boston Red Sox"
    assert parser.reference_data["selections"]["sel-301"]["market_id"] == "market-200"


def test_caesars_handshake_preserves_alias_state():
    """Handshake 0x23 frame acknowledges connection without clearing active alias state."""
    parser = CaesarsParser()
    parser.store.set("aabbcc", b"\x01\x02\x03")
    parser.store.set_uuid("aabbcc", "some-uuid")
    assert parser.store.contains("aabbcc")

    # Send 0x23 handshake frame
    handshake_payload = base64.b64encode(bytes([0x23])).decode("ascii")
    updates = parser.handle_ws_frame(handshake_payload)

    assert updates == []
    assert parser.stats["handshakes"] == 1
    assert parser.store.contains("aabbcc")
    assert parser.store.get_uuid("aabbcc") == "some-uuid"


def test_caesars_socket_close_reset():
    """parser.reset() explicitly clears alias state if invoked.

    Note: This tests the reset() method directly. In production, CDP socket-close events
    are not yet wired to this method in session_manager.py; instead, the 0x23 session handshake
    resets alias state on each new connection.
    """
    parser = CaesarsParser()
    parser.store.set("112233", b"\xAA\xBB")
    parser.store.set_uuid("112233", "uuid-close-test")
    assert parser.store.contains("112233")

    # Trigger explicit reset
    parser.reset()

    assert not parser.store.contains("112233")
    assert parser.store.get_uuid("112233") is None


def test_caesars_ws_type04_and_type05_flow(sample_home_json):
    """Test full cycle: load HTTP enrichment, receive Type 0x04 full state, then Type 0x05 delta."""
    parser = CaesarsParser()
    parser.handle_http_body("https://api.americanwagering.com/v4/home", json.dumps(sample_home_json))

    # ws_12 raw base64 provides initial selection state for bd9bf767
    ws_12_b64 = "BBDh+7ukYmlkeCRiZDliZjc2Ny1hNTg4LTMxZDktYjI5Ny0yMTVmOWZmNDU5MjFmYWN0aXZl9WVwcmljZaNhYRiCYWT7QAJmZmZmZmZhZmUxMy8xMGVzdGF0ZWRvcGVu"

    # Map the UUID to our enrichment dictionary
    parser.reference_data["selections"]["bd9bf767-a588-31d9-b297-215f9ff45921"] = {
        "name": "Boston Red Sox",
        "market_name": "Moneyline",
        "market_line": None,
        "event_name": "Boston Red Sox at New York Yankees",
        "event_id": "event-100",
        "market_id": "market-200",
    }

    # Process Type 0x04 frame (ws_12)
    updates_t4 = parser.handle_ws_frame(ws_12_b64)
    assert len(updates_t4) == 1
    assert updates_t4[0].raw_selection == "Boston Red Sox"
    assert updates_t4[0].raw_home_team == "New York Yankees"
    assert updates_t4[0].raw_away_team == "Boston Red Sox"
    assert updates_t4[0].odds_value == 2.3

    # Process Type 0x05 delta frame (ws_454) -> moves to +137
    ws_454_b64 = "BRDh+7sAGDxBiRg9BU31wo9cKPZhZmQxMS84GFAL"
    updates_t5_454 = parser.handle_ws_frame(ws_454_b64)
    assert len(updates_t5_454) == 1
    assert updates_t5_454[0].raw_selection == "Boston Red Sox"
    assert updates_t5_454[0].odds_value == 2.37

    # Process Type 0x05 delta frame (ws_508) -> moves to -200
    ws_508_b64 = "BRDh+7sAGDtNOMdhZPk+AGFmYzEvMhhPCw=="
    updates_t5_508 = parser.handle_ws_frame(ws_508_b64)
    assert len(updates_t5_508) == 1
    assert updates_t5_508[0].raw_selection == "Boston Red Sox"
    assert updates_t5_508[0].odds_value == 1.5


def test_caesars_replay_full_fixture_stream():
    """Integration test: replay all 551 fixture messages against CaesarsParser."""
    json_path = os.path.join(FIXTURES_DIR, "caesars", "messages", "json_5.json")
    assert os.path.exists(json_path), f"Caesars fixture missing: {json_path}"

    parser = CaesarsParser()
    with open(json_path, "r", encoding="utf-8") as f:
        body = f.read()
    parser.handle_http_body("https://api.americanwagering.com/v4/home", body)
    assert len(parser.reference_data["events"]) > 0

    total_updates = 0
    messages_found = 0
    for i in range(552):
        ws_file = os.path.join(FIXTURES_DIR, "caesars", "messages", f"ws_{i}.txt")
        if not os.path.exists(ws_file):
            continue
        messages_found += 1
        with open(ws_file, "r") as f:
            b64_line = f.read().strip()
        updates = parser.handle_ws_frame(b64_line)
        total_updates += len(updates)

    assert messages_found >= 550, f"Expected ~551 messages, found {messages_found}"
    # Replaying full fixture stream should yield hundreds of valid updates
    assert total_updates > 100, f"Expected >100 updates, got {total_updates}"


def test_caesars_unknown_alias_skip():
    """Mid-session delta for unknown alias must be skipped without error."""
    parser = CaesarsParser()
    ws_508_b64 = "BRDh+7sAGDtNOMdhZPk+AGFmYzEvMhhPCw=="
    # Alias e1fbbb is not in parser.store
    updates = parser.handle_ws_frame(ws_508_b64)
    assert updates == []


def test_caesars_market_line_propagation(sample_home_json):
    """When a market delta updates the line, it must propagate to child selections."""
    parser = CaesarsParser()
    parser.handle_http_body("https://api.americanwagering.com/v4/home", json.dumps(sample_home_json))

    market_id = "market-201"
    assert parser.reference_data["markets"][market_id]["handicap"] == 1.5

    # Propagate line update to market-201 -> 2.5
    parser.update_enrichment_line(market_id, 2.5)

    assert parser.reference_data["markets"][market_id]["handicap"] == 2.5


def test_caesars_odds_fallback():
    """Test American odds fallback when only decimal odds ('d') are present."""
    parser = CaesarsParser()
    parser.reference_data["selections"]["sel-dec"] = {
        "name": "Draw",
        "market_name": "3-Way",
        "market_line": None,
        "event_name": "Arsenal vs Chelsea",
        "event_id": "ev-1",
        "market_id": "m-1",
    }

    # Build dummy selection with decimal price d=2.5 (+150)
    obj = {
        "id": "sel-dec",
        "price": {"d": 2.5}
    }
    updates = parser._build_odds_update(obj, "sel-dec", None)
    assert len(updates) == 1
    assert updates[0].odds_value == 2.5


def test_caesars_cbor_name_fallback():
    """When selection is not in selection_lookup, fallback to CBOR's embedded name (stripped of pipes)."""
    parser = CaesarsParser()
    # No enrichment in selection_lookup
    obj = {
        "id": "112dc0d1-d0a4-3798-a2a6-0593336d80f1",
        "name": "|Baltimore Orioles|",
        "price": {"a": 300, "d": 4.0, "f": "3/1"}
    }
    updates = parser._build_odds_update(obj, "112dc0d1-d0a4-3798-a2a6-0593336d80f1", None)
    assert len(updates) == 1
    assert updates[0].raw_selection == "Baltimore Orioles"
    assert updates[0].odds_value == 4.0


def test_caesars_handle_full_state_invalid_cbor_does_not_poison_store():
    """Verify that if a full-state frame fails to decode, the corrupt bytes are NOT stored."""
    from datetime import datetime, timezone
    parser = CaesarsParser()
    alias = "8d7cf9"
    # Pass undecodable garbage bytes
    bad_bytes = b"\xff\xff\xff\xff"
    res = parser._handle_full_state(alias, bad_bytes, datetime.now(timezone.utc))
    assert res == []
    # CRITICAL: alias MUST NOT be stored in store!
    assert not parser.store.contains(alias)


def test_caesars_dynamic_market_line_update_reflects_in_selection():
    """Verify that a market line update (e.g. Total 5.5 -> 6.5) updates enrichment
    and that selection odds updates reflect the updated line (preventing phantom arbs)."""
    from datetime import datetime, timezone
    import cbor2
    parser = CaesarsParser()

    # Pre-game: Devils vs Flyers Total Goals 5.5
    parser.reference_data["events"]["ev-devils"] = {
        "name": "Philadelphia Flyers at New Jersey Devils",
        "sport_code": "Hockey",
        "league_name": "NHL",
        "start_time": "2026-10-01T23:00:00Z",
    }
    parser.reference_data["markets"]["mkt-total"] = {
        "name": "Total Goals",
        "handicap": 5.5,
        "event_id": "ev-devils",
    }
    parser.reference_data["selections"]["sel-under"] = {
        "name": "Under",
        "market_id": "mkt-total",
        "type": "under",
    }

    # Market moves to 6.5 in live play via WebSocket
    mkt_cbor = cbor2.dumps({
        "id": "mkt-total",
        "name": "|Total Goals Live|",
        "line": 6.5,
        "templateId": 1234,
        "marketCode": "TOTAL_GOALS",
    })
    parser._handle_full_state("alias_mkt", mkt_cbor, datetime.now(timezone.utc))

    # Reference data line must now be 6.5
    assert parser.reference_data["markets"]["mkt-total"]["handicap"] == 6.5

    # Selection price update arrives for Under @ +127 (decimal 2.27)
    sel_cbor = cbor2.dumps({
        "id": "sel-under",
        "name": "|Under|",
        "price": {"a": 127, "d": 2.27},
    })
    updates = parser._handle_full_state("alias_sel", sel_cbor, datetime.now(timezone.utc))

    assert len(updates) == 1
    # Line MUST be 6.5, NOT the stale 5.5!
    assert updates[0].raw_line == 6.5
    assert updates[0].odds_value == 2.27


def test_caesars_delta_failure_preserves_alias_in_store():
    """Verify that if a delta fails to apply, the alias is NOT evicted from store
    because Caesars only establishes topic aliases once per session."""
    from datetime import datetime, timezone
    parser = CaesarsParser()
    alias = "8ea710"
    original_cbor = b"\xa1\x62id\x01"
    parser.store.set(alias, original_cbor)  # {"id": 1}
    assert parser.store.contains(alias)

    # Pass corrupt delta payload that causes apply_binary_delta or decode to fail
    corrupt_delta = b"\xff\xff\xff\xff"
    res = parser._handle_binary_delta(alias, corrupt_delta, datetime.now(timezone.utc))
    assert res == []
    # Alias must be preserved in store so subsequent deltas can still be received
    assert parser.store.contains(alias)
    assert parser.store.get(alias) == original_cbor


def test_caesars_american_odds_fallback():
    """Verify that if decimal odds 'd' is missing, American odds 'a' is converted."""
    from datetime import datetime, timezone
    parser = CaesarsParser()
    parser.reference_data["events"]["ev-1"] = {
        "name": "Boston Bruins at New York Rangers",
        "sport_code": "Ice Hockey",
        "league_name": "NHL",
        "start_time": "2026-10-02T00:00:00Z",
    }
    parser.reference_data["markets"]["mkt-1"] = {
        "name": "Money Line",
        "event_id": "ev-1",
        "handicap": None,
    }
    parser.reference_data["selections"]["sel-1"] = {
        "name": "Boston Bruins",
        "market_id": "mkt-1",
        "type": "away",
    }

    # Selection with only American odds "a": +150 (decimal 2.5)
    obj = {
        "id": "sel-1",
        "name": "|Boston Bruins|",
        "price": {"a": 150},
    }
    updates = parser._build_odds_update(obj, "sel-1", datetime.now(timezone.utc))
    assert len(updates) == 1
    assert updates[0].odds_value == 2.5
    assert updates[0].odds_format == "decimal"


def test_caesars_event_object_ignored_for_odds_and_tracks_uuid():
    """Verify that event objects received via WS return [] for odds and map alias to UUID."""
    from datetime import datetime, timezone
    import cbor2
    parser = CaesarsParser()
    ev_cbor = cbor2.dumps({
        "id": "ev-live-1",
        "started": True,
        "tradedInPlay": True,
        "state": "open",
    })
    updates = parser._handle_full_state("alias_ev", ev_cbor, datetime.now(timezone.utc))
    assert updates == []
    assert parser.store.get_uuid("alias_ev") == "ev-live-1"


def test_caesars_handicap_inversion_for_away_team():
    """Verify that Caesars spread/puck line handicaps are inverted for away selections,
    while home selections and totals markets remain unchanged."""
    from datetime import datetime, timezone
    parser = CaesarsParser()

    # Setup fixture: Edmonton Oilers (Home) vs Vancouver Canucks (Away)
    parser.reference_data["events"]["ev-puck"] = {
        "name": "Vancouver Canucks at Edmonton Oilers",
        "sport_code": "Ice Hockey",
        "league_name": "NHL",
        "start_time": "2026-10-02T02:15:00Z",
    }
    # Market line -1.5: Edmonton Oilers is favored by 1.5 goals
    parser.reference_data["markets"]["mkt-puck"] = {
        "name": "Puck Line Live",
        "handicap": -1.5,
        "event_id": "ev-puck",
    }
    parser.reference_data["selections"]["sel-edm"] = {
        "name": "Edmonton Oilers",
        "market_id": "mkt-puck",
        "type": "home",
    }
    parser.reference_data["selections"]["sel-van"] = {
        "name": "Vancouver Canucks",
        "market_id": "mkt-puck",
        "type": "away",
    }

    # 1. Home selection: Edmonton Oilers -> -1.5
    edm_update = parser._build_odds_update(
        {"id": "sel-edm", "name": "|Edmonton Oilers|", "price": {"d": 2.95}},
        "sel-edm",
        datetime.now(timezone.utc),
    )
    assert len(edm_update) == 1
    assert edm_update[0].raw_line == -1.5
    assert edm_update[0].raw_selection == "Edmonton Oilers"

    # 2. Away selection: Vancouver Canucks -> +1.5 (inverted)
    van_update = parser._build_odds_update(
        {"id": "sel-van", "name": "|Vancouver Canucks|", "price": {"d": 1.40}},
        "sel-van",
        datetime.now(timezone.utc),
    )
    assert len(van_update) == 1
    assert van_update[0].raw_line == 1.5
    assert van_update[0].raw_selection == "Vancouver Canucks"

    # 3. Fallback when type is missing: name matches away_team
    parser.reference_data["selections"]["sel-van-notype"] = {
        "name": "Vancouver Canucks",
        "market_id": "mkt-puck",
    }
    van_notype_update = parser._build_odds_update(
        {"id": "sel-van-notype", "name": "|Vancouver Canucks|", "price": {"d": 1.40}},
        "sel-van-notype",
        datetime.now(timezone.utc),
    )
    assert len(van_notype_update) == 1
    assert van_notype_update[0].raw_line == 1.5

    # 4. Totals market: line must NOT be inverted for Over or Under
    parser.reference_data["markets"]["mkt-tot"] = {
        "name": "Total Goals Live",
        "handicap": 6.5,
        "event_id": "ev-puck",
    }
    parser.reference_data["selections"]["sel-over"] = {
        "name": "Over",
        "market_id": "mkt-tot",
        "type": "over",
    }
    parser.reference_data["selections"]["sel-under"] = {
        "name": "Under",
        "market_id": "mkt-tot",
        "type": "under",
    }
    over_update = parser._build_odds_update(
        {"id": "sel-over", "name": "|Over|", "price": {"d": 1.85}},
        "sel-over",
        datetime.now(timezone.utc),
    )
    under_update = parser._build_odds_update(
        {"id": "sel-under", "name": "|Under|", "price": {"d": 1.95}},
        "sel-under",
        datetime.now(timezone.utc),
    )
    assert over_update[0].raw_line == 6.5
    assert under_update[0].raw_line == 6.5
