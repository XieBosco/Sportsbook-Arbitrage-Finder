"""Pytest test suite asserting latency metrics and correctness on artificial data."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from tests.metrics.benchmark_runner import (
    benchmark_normalization,
    benchmark_matching,
    benchmark_odds_update_scanner_no_arb,
    benchmark_arbitrage_detection,
    benchmark_end_to_end_pipeline,
    _build_test_scanner,
)
from tests.metrics.artificial_data import (
    generate_arb_triggering_pairs,
    generate_non_arb_stream,
)


class TestLatencyMetrics:
    """Latency performance invariants and correctness tests using synthetic workloads."""

    def test_normalization_latency(self) -> None:
        """Assert normalization latency remains sub-millisecond."""
        metric = benchmark_normalization(sample_count=200)
        assert metric.sample_count == 200
        # Normalization (JSON dict lookup + string parsing) should be well under 1000 µs (1 ms) P95
        assert metric.p95_us < 1000.0, f"Normalization P95 too high: {metric.p95_us:.2f} µs"
        assert metric.throughput_ops_sec > 1000.0

    def test_matching_latency(self) -> None:
        """Assert bucket matching latency remains sub-millisecond."""
        metric = benchmark_matching(sample_count=300)
        assert metric.sample_count == 300
        # Bucket assignment + output build should be well under 500 µs P95
        assert metric.p95_us < 500.0, f"Matching P95 too high: {metric.p95_us:.2f} µs"
        assert metric.throughput_ops_sec > 2000.0

    def test_scanner_routine_odds_update_latency(self) -> None:
        """Assert processing a routine non-arb odds update is sub-millisecond."""
        metric = benchmark_odds_update_scanner_no_arb(sample_count=500)
        assert metric.sample_count > 0
        # Scanner routine check should be well under 500 µs P95
        assert metric.p95_us < 500.0, f"Scanner routine update P95 too high: {metric.p95_us:.2f} µs"

    def test_arbitrage_detection_latency(self) -> None:
        """Assert detecting an arbitrage opportunity is sub-millisecond."""
        metric = benchmark_arbitrage_detection(sample_count=100)
        assert metric.sample_count == 100
        # Full arb detection + stake calculation should be well under 1000 µs (1 ms) P95
        assert metric.p95_us < 1000.0, f"Arb detection P95 too high: {metric.p95_us:.2f} µs"

    def test_arbitrage_detection_correctness(self) -> None:
        """Verify that synthetic arbitrage pairs reliably emit opportunities with valid stakes."""
        pairs = generate_arb_triggering_pairs(count=10, target_margin=0.04)
        for pair in pairs:
            scanner, sink = _build_test_scanner()

            # Process setup selection (first leg)
            res1 = scanner.process(pair.setup_selection)
            assert res1 is None, "Setup leg alone should not emit an arb"
            assert len(sink.emitted) == 0

            # Process trigger selection (completes market)
            opp = scanner.process(pair.arb_trigger_selection)
            assert opp is not None, "Arb pair must trigger an Opportunity"
            assert len(sink.emitted) == 1
            assert opp.margin > 0.02
            assert len(opp.legs) == 2

            # Stakes must sum to total budget ($100.0)
            total_stake = sum(leg.stake for leg in opp.legs)
            assert pytest.approx(total_stake, rel=1e-2) == 100.0

    def test_end_to_end_latency(self) -> None:
        """Assert end-to-end pipeline latency from raw update to opportunity emission."""
        routine, arb = benchmark_end_to_end_pipeline(sample_count=100)
        assert routine.p95_us < 3000.0, f"E2E Routine P95 too high: {routine.p95_us:.2f} µs"
        assert arb.p95_us < 3000.0, f"E2E Arb detection P95 too high: {arb.p95_us:.2f} µs"
