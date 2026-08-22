"""Unit tests for BetMGM parser (betmgm.py)."""

import json
import pytest

from arbfinder.parsers._helpers import split_fixture_name
from arbfinder.parsers.betmgm import BetMGMParser


@pytest.fixture
def sample_betmgm_ref():
    return {
        "fixture": {
            "id": 987654,
            "name": {"value": "Chicago Cubs @ St. Louis Cardinals"}
        }
    }


@pytest.fixture
def sample_betmgm_ref_at_delimiter():
    return {
        "fixture": {
            "id": 19766272,
            "name": {"value": "Indiana Fever at Las Vegas Aces"}
        }
    }


def test_betmgm_url_matching():
    parser = BetMGMParser()
    assert parser.relevant_http_url("https://sports.on.betmgm.ca/en/sports/api/fixture-view?fixtureIds=987654")
    assert not parser.relevant_http_url("https://sports.on.betmgm.ca/en/sports/api/other")


def test_betmgm_http_reference_parsing(sample_betmgm_ref):
    parser = BetMGMParser()
    parser.handle_http_body("fixture-view", json.dumps(sample_betmgm_ref))

    assert "987654" in parser.reference_data["events"]
    assert parser.reference_data["events"]["987654"] == "Chicago Cubs @ St. Louis Cardinals"


def test_betmgm_ws_game_update(sample_betmgm_ref):
    parser = BetMGMParser()
    parser.handle_http_body("fixture-view", json.dumps(sample_betmgm_ref))

    signalr_payload = json.dumps({
        "arguments": [
            {
                "messageType": "GameUpdate",
                "payload": {
                    "fixtureId": 987654,
                    "game": {
                        "id": 1122,
                        "name": {"value": "Run Line"},
                        "results": [
                            {
                                "id": 5566,
                                "name": {"value": "Chicago Cubs"},
                                "americanOdds": 140,
                                "attr": "1.5"
                            }
                        ]
                    }
                }
            }
        ]
    }) + "\x1e"

    updates = parser.handle_ws_frame(signalr_payload)
    assert len(updates) == 1
    assert updates[0].book == "BetMGM"
    assert updates[0].event_id == "987654"
    assert updates[0].away_team == "Chicago Cubs"
    assert updates[0].home_team == "St. Louis Cardinals"
    assert updates[0].market == "Run Line"
    assert updates[0].selection == "Chicago Cubs"
    assert updates[0].line == 1.5
    assert updates[0].price_american == 140


def test_betmgm_ws_game_update_at_delimiter(sample_betmgm_ref_at_delimiter):
    """Test ' at ' delimiter (as seen in production fixture: 'Indiana Fever at Las Vegas Aces')."""
    parser = BetMGMParser()
    parser.handle_http_body("fixture-view", json.dumps(sample_betmgm_ref_at_delimiter))

    signalr_payload = json.dumps({
        "arguments": [
            {
                "messageType": "GameUpdate",
                "payload": {
                    "fixtureId": 19766272,
                    "game": {
                        "id": 1539548941,
                        "name": {"value": "Moneyline"},
                        "results": [
                            {
                                "id": 2243734650,
                                "name": {"value": "Fever"},
                                "americanOdds": -220,
                            }
                        ]
                    }
                }
            }
        ]
    }) + "\x1e"

    updates = parser.handle_ws_frame(signalr_payload)
    assert len(updates) == 1
    assert updates[0].book == "BetMGM"
    assert updates[0].event_id == "19766272"
    assert updates[0].away_team == "Indiana Fever"
    assert updates[0].home_team == "Las Vegas Aces"
    assert updates[0].market == "Moneyline"
    assert updates[0].selection == "Fever"
    assert updates[0].price_american == -220


def test_betmgm_ws_option_market_update(sample_betmgm_ref):
    parser = BetMGMParser()
    parser.handle_http_body("fixture-view", json.dumps(sample_betmgm_ref))

    signalr_payload = json.dumps({
        "arguments": [
            {
                "messageType": "OptionMarketUpdate",
                "payload": {
                    "fixtureId": 987654,
                    "optionMarket": {
                        "id": 3344,
                        "name": {"value": "Moneyline"},
                        "options": [
                            {
                                "id": 7788,
                                "name": {"value": "St. Louis Cardinals"},
                                "price": {"americanOdds": -165}
                            }
                        ]
                    }
                }
            }
        ]
    }) + "\x1e"

    updates = parser.handle_ws_frame(signalr_payload)
    assert len(updates) == 1
    assert updates[0].book == "BetMGM"
    assert updates[0].away_team == "Chicago Cubs"
    assert updates[0].home_team == "St. Louis Cardinals"
    assert updates[0].market == "Moneyline"
    assert updates[0].selection == "St. Louis Cardinals"
    assert updates[0].price_american == -165


def test_betmgm_fixture_name_splitting_delimiters():
    """Verify split_fixture_name handles ' at ', ' @ ', ' vs ', ' vs. ', and ' - '."""
    assert split_fixture_name("Indiana Fever at Las Vegas Aces") == ("Las Vegas Aces", "Indiana Fever")
    assert split_fixture_name("Chicago Cubs @ St. Louis Cardinals") == ("St. Louis Cardinals", "Chicago Cubs")
    assert split_fixture_name("Arsenal vs Chelsea") == ("Arsenal", "Chelsea")
    assert split_fixture_name("Arsenal vs. Chelsea") == ("Arsenal", "Chelsea")
    assert split_fixture_name("Boston - NY Yankees") == ("Boston", "NY Yankees")
    assert split_fixture_name("SingleTeam") == ("SingleTeam", "SingleTeam")


def test_betmgm_game_level_attr_fallback(sample_betmgm_ref_at_delimiter):
    """Verify that when result has no 'attr', the parser falls back to game['attr'] (e.g. betmgm_message14.json)."""
    parser = BetMGMParser()
    parser.handle_http_body("fixture-view", json.dumps(sample_betmgm_ref_at_delimiter))

    signalr_payload = json.dumps({
        "type": 1,
        "target": "Receive",
        "arguments": [
            {
                "messageType": "GameUpdate",
                "payload": {
                    "fixtureId": "19766272",
                    "game": {
                        "id": 1543507316,
                        "name": {"value": "3rd quarter totals"},
                        "attr": "45.5",
                        "results": [
                            {"id": 2255353711, "name": {"value": "Over 45.5"}, "americanOdds": -118},
                            {"id": 2255353712, "name": {"value": "Under 45.5"}, "americanOdds": -115}
                        ]
                    }
                }
            }
        ]
    }) + "\x1e"

    updates = parser.handle_ws_frame(signalr_payload)
    assert len(updates) == 2
    assert updates[0].market == "3rd quarter totals"
    assert updates[0].selection == "Over 45.5"
    assert updates[0].line == 45.5
    assert updates[0].price_american == -118
    assert updates[1].selection == "Under 45.5"
    assert updates[1].line == 45.5
    assert updates[1].price_american == -115
