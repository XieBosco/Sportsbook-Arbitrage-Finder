"""Tests for odds math utilities."""

import pytest
from arbfinder.normalization.odds_math import (
    american_to_decimal,
    decimal_to_american,
    implied_prob,
)


def test_implied_prob():
    # Negative odds (favorite)
    # -100 -> 100 / 200 = 0.5
    assert pytest.approx(implied_prob(-100)) == 0.5
    # -200 -> 200 / 300 = 0.6666667
    assert pytest.approx(implied_prob(-200)) == 2 / 3
    # -110 -> 110 / 210 = 0.5238095
    assert pytest.approx(implied_prob(-110)) == 110 / 210

    # Positive odds (underdog)
    # +100 -> 100 / 200 = 0.5
    assert pytest.approx(implied_prob(100)) == 0.5
    # +150 -> 100 / 250 = 0.4
    assert pytest.approx(implied_prob(150)) == 0.4
    # +200 -> 100 / 300 = 0.3333333
    assert pytest.approx(implied_prob(200)) == 1 / 3


def test_american_to_decimal():
    # Negative odds
    # -100 -> 1 - (100 / -100) = 2.0
    assert pytest.approx(american_to_decimal(-100)) == 2.0
    # -200 -> 1 - (100 / -200) = 1.5
    assert pytest.approx(american_to_decimal(-200)) == 1.5
    # -110 -> 1 - (100 / -110) = 1.9090909
    assert pytest.approx(american_to_decimal(-110)) == 1 + 100 / 110

    # Positive odds
    # +100 -> 1 + (100 / 100) = 2.0
    assert pytest.approx(american_to_decimal(100)) == 2.0
    # +150 -> 1 + (150 / 100) = 2.5
    assert pytest.approx(american_to_decimal(150)) == 2.5


def test_decimal_to_american():
    # 2.0 -> +100
    assert decimal_to_american(2.0) == 100
    # 2.5 -> +150
    assert decimal_to_american(2.5) == 150
    # 1.5 -> -200
    assert decimal_to_american(1.5) == -200
    # 1.91 -> -110
    assert decimal_to_american(1.91) == -110
    # 1.9090909 -> -110
    assert decimal_to_american(1.9090909) == -110

    # Edge cases (<= 1.0)
    assert decimal_to_american(1.0) == 0
    assert decimal_to_american(0.5) == 0
