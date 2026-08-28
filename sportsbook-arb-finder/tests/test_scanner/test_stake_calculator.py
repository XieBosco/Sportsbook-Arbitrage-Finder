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
        stakes = compute_stakes(odds, total)
        assert math.isclose(sum(stakes.values()), total, rel_tol=1e-9)
