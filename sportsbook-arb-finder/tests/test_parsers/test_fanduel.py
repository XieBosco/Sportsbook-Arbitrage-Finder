"""Unit tests for FanDuel parser (fanduel.py)."""

import json
import pytest

from arbfinder.parsers.fanduel import FanDuelParser


@pytest.fixture
def sample_fanduel_ref():
    return {
        "attachments": {
            "events": {
                "31234567": {"name": "Baltimore Orioles @ New York Yankees"}
            },
            "markets": {
                "71.123456": {
                    "eventId": "31234567",
                    "marketName": "Moneyline",
                    "marketType": "MONEYLINE",
                    "runners": [
                        {"selectionId": "1001", "runnerName": "Baltimore Orioles", "handicap": 0},
                        {"selectionId": "1002", "runnerName": "New York Yankees", "handicap": 0},
                    ],
                }
            },
        }
    }


def test_fanduel_url_matching():
    parser = FanDuelParser()
    assert parser.relevant_http_url("https://sbapi.on.sportsbook.fanduel.ca/api/content-managed-page?page=CUSTOM")
    assert parser.relevant_http_url("https://sbapi.on.sportsbook.fanduel.ca/api/getMarketPrices?marketIds=71.123456")
    assert not parser.relevant_http_url("https://sbapi.on.sportsbook.fanduel.ca/api/other")


def test_fanduel_http_reference_parsing(sample_fanduel_ref):
    parser = FanDuelParser()
    parser.handle_http_body("content-managed-page", json.dumps(sample_fanduel_ref))

    assert "31234567" in parser.reference_data["events"]
    assert parser.reference_data["events"]["31234567"] == "Baltimore Orioles @ New York Yankees"
    assert "71.123456" in parser.reference_data["markets"]
    assert "71.123456_1001" in parser.reference_data["selections"]


def test_fanduel_live_odds_update(sample_fanduel_ref):
    parser = FanDuelParser()
    parser.handle_http_body("content-managed-page", json.dumps(sample_fanduel_ref))

    odds_payload = {
        "marketPrices": [
            {
                "marketId": "71.123456",
                "runnerDetails": [
                    {
                        "selectionId": "1001",
                        "winRunnerOdds": {
                            "americanDisplayOdds": {"americanOdds": "+130"}
                        },
                    },
                    {
                        "selectionId": "1002",
                        "winRunnerOdds": {
                            "americanDisplayOdds": {"americanOdds": "-155"}
                        },
                    },
                ],
            }
        ]
    }

    updates = parser.handle_http_body("getMarketPrices", json.dumps(odds_payload))
    assert len(updates) == 2
    assert updates[0].book == "FanDuel"
    assert updates[0].home_team == "New York Yankees"
    assert updates[0].away_team == "Baltimore Orioles"
    assert updates[0].market == "MONEYLINE"
    assert updates[0].selection == "Baltimore Orioles"
    assert updates[0].price_american == 130
    assert updates[1].selection == "New York Yankees"
    assert updates[1].price_american == -155
