"""Tests for core/stake_calculator.py."""

import math

from arbfinder.core.stake_calculator import compute_stakes


class TestComputeStakes:
    """Verify stake distribution is inversely proportional to odds."""

    def test_stakes_sum_to_total(self) -> None:
        odds = {"home": 3.5, "away": 1.5}
        total = 100.0
        stakes = compute_stakes(odds, total)
        assert math.isclose(sum(stakes.values()), total, rel_tol=1e-9)

    def test_inversely_proportional(self) -> None:
        """Lower odds → higher stake (more likely outcome gets more money)."""
        odds = {"home": 4.0, "away": 2.0}
        total = 100.0
        stakes = compute_stakes(odds, total)

        # away (2.0) should get double the stake of home (4.0)
        # 1/2.0 = 0.5, 1/4.0 = 0.25, sum = 0.75
        # away = 100 * 0.5/0.75 = 66.67
        # home = 100 * 0.25/0.75 = 33.33
        assert math.isclose(stakes["away"], 100.0 * (1 / 2.0) / (1 / 2.0 + 1 / 4.0))
        assert math.isclose(stakes["home"], 100.0 * (1 / 4.0) / (1 / 2.0 + 1 / 4.0))
        assert stakes["away"] > stakes["home"]

    def test_equal_odds(self) -> None:
        """Equal odds → equal stakes."""
        odds = {"home": 2.0, "away": 2.0}
        total = 100.0
        stakes = compute_stakes(odds, total)
        assert math.isclose(stakes["home"], 50.0)
        assert math.isclose(stakes["away"], 50.0)

    def test_three_way(self) -> None:
        """Three-way split sums correctly."""
        odds = {"home": 3.0, "draw": 4.0, "away": 5.0}
        total = 1000.0
        stakes = compute_stakes(odds, total)
        assert math.isclose(sum(stakes.values()), total, rel_tol=1e-9)
        # Verify ordering: lower odds → higher stake
        assert stakes["home"] > stakes["draw"] > stakes["away"]

    def test_custom_total(self) -> None:
        """Non-default total stake."""
        odds = {"over": 1.8, "under": 2.1}
        total = 500.0
        stakes = compute_stakes(odds, total, method=1)
        assert math.isclose(sum(stakes.values()), total, rel_tol=1e-9)

    def test_unit_size_method(self) -> None:
        """Method 2: underdog gets unit size, favorite gets target_payout/odds."""
        odds = {"home": 1.5, "away": 4.0}
        unit_size = 100.0
        stakes = compute_stakes(odds, unit_size, method=2)
        
        # Underdog is 'away' with 4.0 odds.
        # It should get exactly the unit_size.
        assert math.isclose(stakes["away"], 100.0)
        
        # Payout should be 400.
        # Favorite 'home' with 1.5 odds needs stake = 400 / 1.5 = 266.666...
        assert math.isclose(stakes["home"], 400.0 / 1.5)
        
        # Both legs should yield the same payout
        assert math.isclose(stakes["away"] * odds["away"], stakes["home"] * odds["home"])

    def test_unit_size_three_way(self) -> None:
        """Method 2 applies correctly to 3-way markets."""
        odds = {"home": 2.0, "draw": 3.0, "away": 7.0}
        unit_size = 50.0
        stakes = compute_stakes(odds, unit_size, method=2)
        
        # Underdog is 'away' with 7.0 odds.
        assert math.isclose(stakes["away"], 50.0)
        
        target_payout = 50.0 * 7.0 # 350.0
        assert math.isclose(stakes["home"], 350.0 / 2.0)
        assert math.isclose(stakes["draw"], 350.0 / 3.0)
        
        assert math.isclose(stakes["home"] * odds["home"], target_payout)
        assert math.isclose(stakes["draw"] * odds["draw"], target_payout)

    def test_empty_odds_dict(self) -> None:
        """Empty odds dict should return empty dict without raising."""
        assert compute_stakes({}, 100.0) == {}

    def test_invalid_odds_raises(self) -> None:
        """Odds <= 1.0 must raise ValueError."""
        import pytest
        with pytest.raises(ValueError, match="Odds must be greater than 1.0"):
            compute_stakes({"home": 1.0, "away": 2.0}, 100.0)
        with pytest.raises(ValueError, match="Odds must be greater than 1.0"):
            compute_stakes({"home": -1.5, "away": 2.0}, 100.0)

    def test_negative_amount_raises(self) -> None:
        """Negative stake amount must raise ValueError."""
        import pytest
        with pytest.raises(ValueError, match="Stake amount must be non-negative"):
            compute_stakes({"home": 2.0, "away": 2.0}, -50.0)

    def test_enum_method(self) -> None:
        """StakeCalculationMethod enum works identically to int."""
        from arbfinder.core.stake_calculator import StakeCalculationMethod
        odds = {"home": 2.0, "away": 2.0}
        s1 = compute_stakes(odds, 100.0, method=StakeCalculationMethod.TOTAL_BET_AMOUNT)
        assert math.isclose(s1["home"], 50.0)
        s2 = compute_stakes(odds, 100.0, method=StakeCalculationMethod.UNIT_SIZE)
        assert math.isclose(s2["home"], 100.0)
