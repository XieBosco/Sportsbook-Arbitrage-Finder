"""Unit tests for DraftKings parser (draftkings.py)."""

import base64
import json
import msgpack
import pytest

from arbfinder.parsers.draftkings import DraftKingsParser


@pytest.fixture
def sample_dk_ref():
    return {
        "events": [
            {"id": "ev-100", "name": "Los Angeles Dodgers @ San Francisco Giants"}
        ],
        "markets": [
            {"id": "m-200", "eventId": "ev-100", "name": "Moneyline"},
            {"id": "m-201", "eventId": "ev-100", "name": "Total"}
        ],
        "selections": [
            {"id": "0ML12345_1", "marketId": "m-200"},
            {"id": "0OU12345O850_1", "marketId": "m-201"},
        ]
    }


def test_draftkings_url_matching():
    parser = DraftKingsParser()
    assert parser.relevant_http_url("https://sportsbook.draftkings.com/api/sportscontent/v1/markets")
    assert not parser.relevant_http_url("https://sportsbook.draftkings.com/api/other")


def test_draftkings_http_reference_parsing(sample_dk_ref):
    parser = DraftKingsParser()
    parser.handle_http_body("api/sportscontent/v1/markets", json.dumps(sample_dk_ref))

    assert "ev-100" in parser.reference_data["events"]
    assert parser.reference_data["events"]["ev-100"] == "Los Angeles Dodgers @ San Francisco Giants"
    assert "m-200" in parser.reference_data["markets"]
    assert "0ML12345_1" in parser.reference_data["selections"]


def test_draftkings_ws_msgpack_parsing(sample_dk_ref):
    parser = DraftKingsParser()
    parser.handle_http_body("test_url", json.dumps(sample_dk_ref))

    # Standard outcome array shape: [selectionId, selectionName, odds_array, dummy, dummy, tags_array, marketId]
    outcome = [
        "0ML12345_1",
        "Los Angeles Dodgers",
        [-150],
        None,
        None,
        ["Moneyline"],
        "m-200"
    ]
    packed = msgpack.packb([outcome])
    b64_payload = base64.b64encode(packed).decode("ascii")

    updates = parser.handle_ws_frame(b64_payload)
    assert len(updates) == 1
    assert updates[0].book == "DraftKings"
    assert updates[0].home_team == "San Francisco Giants"
    assert updates[0].away_team == "Los Angeles Dodgers"
    assert updates[0].selection == "Los Angeles Dodgers"
    assert updates[0].price_american == -150


def test_draftkings_core_id_fallback(sample_dk_ref):
    """If a new dynamic total arrives (e.g. 0OU12345O950_1 with CoreID 12345), fallback finds ev-100."""
    parser = DraftKingsParser()
    parser.handle_http_body("test_url", json.dumps(sample_dk_ref))

    # Dynamic selection 0OU12345O950_1 is not in dictionary, but shares CoreID 12345 with 0OU12345O850_1
    outcome = [
        "0OU12345O950_1",
        "Over 9.5",
        [110],
        None,
        9.5,
        ["Total"],
        None  # marketId is None
    ]
    packed = msgpack.packb([outcome])
    b64_payload = base64.b64encode(packed).decode("ascii")

    updates = parser.handle_ws_frame(b64_payload)
    assert len(updates) == 1
    assert updates[0].event_id == "ev-100"
    assert updates[0].home_team == "San Francisco Giants"
    assert updates[0].selection == "Over 9.5"
    assert updates[0].line == 9.5
    assert updates[0].price_american == 110


def test_draftkings_unicode_minus_odds(sample_dk_ref):
    """Test that unicode minus signs (U+2212 '−') in odds strings are safely sanitized."""
    parser = DraftKingsParser()
    parser.handle_http_body("test_url", json.dumps(sample_dk_ref))

    # Odds with unicode minus sign U+2212: '−248'
    outcome = [
        "0ML12345_1",
        "Los Angeles Dodgers",
        ["−248", "1.40", "25/62", None, "71%"],
        None,
        None,
        ["Moneyline"],
        "m-200"
    ]
    packed = msgpack.packb([outcome])
    b64_payload = base64.b64encode(packed).decode("ascii")

    updates = parser.handle_ws_frame(b64_payload)
    assert len(updates) == 1
    assert updates[0].price_american == -248
