# Sportsbook Arbitrage Finder — Latency Performance Metrics

**Generated:** 2026-09-16 03:19:31 UTC  
**Environment:** Windows 10 (AMD64) | Python CPython 3.13.7  
**Timer:** `time.perf_counter_ns` (Nanosecond resolution)

---

## 1. Executive Summary

This report measures the operational latency of the Sportsbook Arbitrage Finder pipeline across two primary dimensions:
1. **Odds Update Latency**: Time required to ingest, normalize, bucket-match, and evaluate live odds ticks.
2. **Arbitrage Opportunity Detection Latency**: Time required from when a market-completing odds tick arrives until an arbitrage opportunity is mathematically verified, checked for staleness and book conflicts, hedged with optimal stakes, and emitted to sinks.

### Key Highlights
- **Arbitrage Detection Latency (Median P50)**: **41.90 µs** (0.0419 ms)
- **Arbitrage Detection Latency (P95)**: **80.20 µs** (0.0802 ms)
- **End-to-End Arb Detection Latency (P50)**: **112.00 µs** (0.1120 ms)
- **Routine Odds Update Throughput**: **225,501 updates/sec** (isolated scanner) and **14,898 updates/sec** (full E2E pipeline).

---

## 2. Latency Breakdown by Component

The table below details the latency distribution for each layer in microseconds (µs):

| Pipeline Stage | Samples | Median (P50) | P90 | P95 | P99 | Mean ± Std | Min / Max | Throughput (ops/s) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Normalization Layer** | 1000 | 22.0 µs | 132.8 µs | 167.4 µs | 233.1 µs | 48.8 ± 55.2 µs | 14.8 / 313.4 µs | 20,503 |
| **2. Matching Layer** | 1000 | 7.8 µs | 20.9 µs | 24.2 µs | 33.5 µs | 10.0 ± 6.6 µs | 7.3 / 97.9 µs | 99,793 |
| **3. Scanner: Routine Update** | 1950 | 4.2 µs | 4.3 µs | 4.4 µs | 9.6 µs | 4.4 ± 2.4 µs | 4.0 / 56.6 µs | 225,501 |
| **4. Arbitrage Detection** | 500 | 41.9 µs | 68.4 µs | 80.2 µs | 115.6 µs | 47.9 ± 16.2 µs | 39.5 / 160.7 µs | 20,885 |

---

## 3. End-to-End Pipeline Latency

End-to-end latency tracks a raw `OddsUpdate` entering the pipeline through all intermediate representations (`NormalizedOddsUpdate` $\rightarrow$ `Bucket` $\rightarrow$ `MatchedSelection`) to final `Scanner` output:

| Scenario | Samples | Median (P50) | P95 | P99 | Mean | Max |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Routine Odds Update (No Arb)** | 500 | **57.3 µs** (0.057 ms) | **119.4 µs** (0.119 ms) | 180.8 µs | 67.1 µs | 201.6 µs |
| **Arbitrage Opportunity Detection** | 500 | **112.0 µs** (0.112 ms) | **205.5 µs** (0.205 ms) | 254.2 µs | 128.9 µs | 878.8 µs |

---

## 4. Technical Analysis & Findings

### Why Arbitrage Detection is Sub-Millisecond
1. **In-Memory Hash Bucketing**: `BucketStore` and `MarketGrouper` operate entirely with $O(1)$ dictionary lookups keyed on pre-computed composite keys (`BucketKey`, `MarketGroupKey`).
2. **Short-Circuit Filtering**: If a market is not complete (e.g. only 1 side received so far), `MarketGrouper.is_complete` immediately exits before running floating-point arbitrage calculations.
3. **Pure Stake Calculation**: Once an opportunity is verified, `compute_stakes` solves the hedging equations using direct linear proportional weighting with zero matrix overhead.

### Latency Budget Comparison
- **Internal Pipeline Processing**: **~0.03 ms to 0.15 ms**.
- **External Network / CDP Transport**: Typically **5 ms to 50 ms** depending on WebSocket ping and browser rendering loop.
- **Conclusion**: The Python processing pipeline accounts for **< 1%** of overall system latency, ensuring that price changes are acted upon immediately without internal bottlenecks.
