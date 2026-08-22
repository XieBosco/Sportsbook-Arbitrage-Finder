"""Unit tests for Betano parser (betano.py)."""

import base64
import json
import lz4.frame
import pytest

from arbfinder.parsers.betano import BetanoParser


@pytest.fixture
def sample_betano_ref():
    """Simulate a Betano live overview HTTP reference payload."""
    return {
        "data": {
            "events": {
                "88845314": {
                    "id": 88845314,
                    "name": "Partizan vs Zalgiris Kaunas",
                    "participants": [
                        {"id": 1, "name": "Partizan", "isHome": True},
                        {"id": 2, "name": "Zalgiris Kaunas", "isHome": False},
                    ],
                }
            },
            "markets": {
                "2853192981": {
                    "id": 2853192981,
                    "name": "Spread",
                    "eventId": 88845314,
                }
            },
            "selections": {
                "9983218593": {
                    "id": 9983218593,
                    "name": "Partizan +2.5",
                    "fullName": "Partizan +2.5",
                    "handicap": 2.5,
                }
            },
        }
    }


def test_betano_url_matching():
    parser = BetanoParser()
    # Exact regex match with required query params
    assert parser.relevant_http_url(
        "https://www.betano.ca/danae-webapi/api/live/overview/12345?isInit=false&includeVirtuals=true"
    )
    # Loose or different params should not match
    assert not parser.relevant_http_url(
        "https://www.betano.ca/danae-webapi/api/live/overview/12345?isInit=true"
    )
    assert not parser.relevant_http_url("https://www.betano.ca/api/other")

    # Confirmed WebSocket endpoint
    assert parser.relevant_ws_url("wss://www.betano.ca/contenthub?platformType=1")
    assert not parser.relevant_ws_url("wss://www.betano.ca/other-socket")


def test_betano_http_reference_parsing(sample_betano_ref):
    parser = BetanoParser()
    parser.handle_http_body(
        "https://www.betano.ca/danae-webapi/api/live/overview/1?isInit=false&includeVirtuals=true",
        json.dumps(sample_betano_ref),
    )

    assert "88845314" in parser.reference_data["events"]
    assert parser.reference_data["events"]["88845314"]["name"] == "Partizan vs Zalgiris Kaunas"

    assert "2853192981" in parser.reference_data["markets"]
    assert parser.reference_data["markets"]["2853192981"]["name"] == "Spread"

    assert "9983218593" in parser.reference_data["selections"]
    assert parser.reference_data["selections"]["9983218593"]["name"] == "Partizan +2.5"


def test_betano_ws_scenario1_selection_changes(sample_betano_ref):
    """Test Scenario 1: selectionChanges under existing market."""
    parser = BetanoParser()
    parser.handle_http_body("test_url", json.dumps(sample_betano_ref))

    # Construct a diff payload
    diff_payload = [
        {
            "eventId": 88845314,
            "payload": {
                "selectionChanges": {
                    "2853192981": [
                        {
                            "id": 9983218593,
                            "price": 1.91,
                            "handicap": 2.5,
                        }
                    ]
                }
            },
        }
    ]

    compressed = lz4.frame.compress(json.dumps(diff_payload).encode("utf-8"))
    b64_data = base64.b64encode(compressed).decode("ascii")

    # SignalR frame with NewLiveOverviewDiffs in payload
    signalr_frame = json.dumps({
        "type": 1,
        "target": "NewLiveOverviewDiffs",
        "arguments": [b64_data],
    }) + "\x1e"

    updates = parser.handle_ws_frame(signalr_frame)
    assert len(updates) == 1
    assert updates[0].book == "Betano"
    assert updates[0].home_team == "Partizan"
    assert updates[0].away_team == "Zalgiris Kaunas"
    assert updates[0].market == "Spread"
    assert updates[0].selection == "Partizan +2.5"
    assert updates[0].line == 2.5
    assert updates[0].price_american == -110


def test_betano_ws_scenario2_inline_market_injection(sample_betano_ref):
    """Test Scenario 2: inline market object injected in payload."""
    parser = BetanoParser()
    parser.handle_http_body("test_url", json.dumps(sample_betano_ref))

    diff_payload = [
        {
            "eventId": 88845314,
            "payload": {
                "market": {
                    "id": 999999,
                    "name": "Total Points",
                    "selections": [
                        {
                            "id": 111111,
                            "name": "Over 160.5",
                            "fullName": "Over 160.5",
                            "price": 2.05,
                            "handicap": 160.5,
                        },
                        {
                            "id": 222222,
                            "name": "Under 160.5",
                            "fullName": "Under 160.5",
                            "price": 1.78,
                            "handicap": 160.5,
                        },
                    ],
                }
            },
        }
    ]

    compressed = lz4.frame.compress(json.dumps(diff_payload).encode("utf-8"))
    b64_data = base64.b64encode(compressed).decode("ascii")

    signalr_frame = json.dumps({
        "type": 1,
        "target": "NewLiveOverviewDiffs",
        "arguments": [b64_data],
    }) + "\x1e"

    updates = parser.handle_ws_frame(signalr_frame)
    assert len(updates) == 2
    assert updates[0].market == "Total Points"
    assert updates[0].selection == "Over 160.5"
    assert updates[0].price_american == 105
    assert updates[0].line == 160.5
    assert updates[1].selection == "Under 160.5"
    assert updates[1].price_american == -128
    assert updates[1].line == 160.5

    # Verify market was saved into reference data
    assert "999999" in parser.reference_data["markets"]
    assert "111111" in parser.reference_data["selections"]


def test_betano_shortname_handicap_fallback(sample_betano_ref):
    """Test shortName fallback when explicit handicap field is absent."""
    parser = BetanoParser()
    parser.handle_http_body("test_url", json.dumps(sample_betano_ref))

    # Selection with shortName="+3.5" but no handicap field
    parser.reference_data["selections"]["55555"] = {
        "id": 55555,
        "name": "Partizan",
        "fullName": "Partizan +3.5",
        "shortName": "+3.5",
    }

    diff_payload = [
        {
            "eventId": 88845314,
            "payload": {
                "selectionChanges": {
                    "2853192981": [
                        {
                            "id": 55555,
                            "price": 1.95,
                            # No handicap in change dict
                        }
                    ]
                }
            },
        }
    ]

    compressed = lz4.frame.compress(json.dumps(diff_payload).encode("utf-8"))
    b64_data = base64.b64encode(compressed).decode("ascii")

    signalr_frame = json.dumps({
        "type": 1,
        "target": "NewLiveOverviewDiffs",
        "arguments": [b64_data],
    }) + "\x1e"

    updates = parser.handle_ws_frame(signalr_frame)
    assert len(updates) == 1
    assert updates[0].line == 3.5
    assert updates[0].price_american == -105


def test_betano_team_resolution_fallback():
    """If participants are missing, fallback parser splits event name."""
    parser = BetanoParser()
    parser.reference_data["events"]["1001"] = {
        "id": 1001,
        "name": "Toronto Maple Leafs @ Montreal Canadiens",
    }
    parser.reference_data["markets"]["2001"] = {"id": 2001, "name": "Moneyline"}
    parser.reference_data["selections"]["3001"] = {"id": 3001, "fullName": "Toronto Maple Leafs"}

    diff_payload = [
        {
            "eventId": 1001,
            "payload": {
                "selectionChanges": {
                    "2001": [{"id": 3001, "price": 1.65}]
                }
            },
        }
    ]
    compressed = lz4.frame.compress(json.dumps(diff_payload).encode("utf-8"))
    b64_data = base64.b64encode(compressed).decode("ascii")

    signalr_frame = json.dumps({
        "type": 1,
        "target": "NewLiveOverviewDiffs",
        "arguments": [b64_data],
    }) + "\x1e"

    updates = parser.handle_ws_frame(signalr_frame)
    assert len(updates) == 1
    assert updates[0].away_team == "Toronto Maple Leafs"
    assert updates[0].home_team == "Montreal Canadiens"


def test_betano_live_event_registration():
    """Live full event registration pushes (e.g. type 1 with participants) register in reference_data['events']."""
    parser = BetanoParser()
    diff_payload = [
        {
            "version": 85,
            "eventId": 88883006,
            "type": 1,
            "payload": {
                "participants": [
                    {"name": "Germany (RIFT) (Esports)", "isHome": True, "teamId": 107826},
                    {"name": "England (GHOST) (Esports)", "isHome": False, "teamId": 1077634}
                ],
                "url": "/live/germany-rift-esports-england-ghost-esports/88883006/",
            }
        }
    ]
    compressed = lz4.frame.compress(json.dumps(diff_payload).encode("utf-8"))
    b64_data = base64.b64encode(compressed).decode("ascii")

    signalr_frame = json.dumps({
        "type": 1,
        "target": "NewLiveOverviewDiffs",
        "arguments": [b64_data],
    }) + "\x1e"

    updates = parser.handle_ws_frame(signalr_frame)
    assert updates == []
    # Verify the event is now registered with home/away teams in reference_data
    assert "88883006" in parser.reference_data["events"]
    assert parser.reference_data["events"]["88883006"]["home_team"] == "Germany (RIFT) (Esports)"
    assert parser.reference_data["events"]["88883006"]["away_team"] == "England (GHOST) (Esports)"
