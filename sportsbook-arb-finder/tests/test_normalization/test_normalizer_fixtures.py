"""Integration tests: real fixture data → parser → normalizer.

Each test replays captured sportsbook traffic (the same fixtures used by
``test_parsers.py``) and verifies that the normalizer:
 1. Produces a non-zero number of ``NormalizedOddsUpdate`` objects.
 2. Every output has valid types and non-empty critical fields.
 3. ``odds_decimal`` is positive and finite.
 4. ``start_time`` is timezone-aware UTC.
 5. ``selection`` is one of the allowed canonical values.
 6. No exceptions are raised during the whole pipeline.
"""

from __future__ import annotations

import glob
import json
import os
from datetime import timezone

import pytest

from arbfinder.normalization.book_normalizers.betano_normalizer import BetanoNormalizer
from arbfinder.normalization.book_normalizers.betmgm_normalizer import BetMGMNormalizer
from arbfinder.normalization.book_normalizers.caesars_normalizer import CaesarsNormalizer
from arbfinder.normalization.book_normalizers.draftkings_normalizer import DraftKingsNormalizer
from arbfinder.normalization.book_normalizers.fanduel_normalizer import FanDuelNormalizer
from arbfinder.normalization.normalizer import Normalizer
from arbfinder.normalization.models import NormalizedOddsUpdate
from arbfinder.parsers.betano import BetanoParser
from arbfinder.parsers.betmgm import BetMGMParser
from arbfinder.parsers.caesars import CaesarsParser
from arbfinder.parsers.draftkings import DraftKingsParser
from arbfinder.parsers.fanduel import FanDuelParser

FIXTURES = os.path.join(os.path.dirname(__file__), "../fixtures")

ALLOWED_SELECTIONS = {
    "home", "away", "over", "under", "draw",
    "home_draw", "home_away", "draw_away",
    "yes", "no",
}


def _validate_output(results: list[NormalizedOddsUpdate]) -> None:
    """Shared assertions for all book normalizers."""
    for r in results:
        assert isinstance(r, NormalizedOddsUpdate)
        assert r.book_id
        assert r.book_event_id
        assert r.home_team
        assert r.away_team
        assert r.start_time is not None
        assert r.start_time.tzinfo is not None, "start_time must be tz-aware"
        assert r.start_time.tzinfo == timezone.utc or r.start_time.utcoffset().total_seconds() == 0
        assert r.odds_decimal > 0, f"odds_decimal must be positive, got {r.odds_decimal}"
        assert r.odds_decimal < 10000, f"odds_decimal suspiciously large: {r.odds_decimal}"
        assert r.selection in ALLOWED_SELECTIONS, f"Unexpected selection: {r.selection!r}"
        assert r.market_type, "market_type must be non-empty"


# -----------------------------------------------------------------------
# DraftKings
# -----------------------------------------------------------------------

class TestDraftKingsNormalizerFixtures:
    """Replay DraftKings fixtures → normalizer."""

    @pytest.fixture()
    def dk_updates(self):
        parser = DraftKingsParser()
        ref = os.path.join(FIXTURES, "draftkings", "draftkings_messages", "json_1.json")
        with open(ref, encoding="utf-8") as f:
            d = json.load(f)
            parser.handle_http_body("api/sportscontent/v1/markets", json.dumps(d.get("data", d)))

        updates = []
        for mf in sorted(glob.glob(os.path.join(FIXTURES, "draftkings", "draftkings_messages", "ws_*.txt"))):
            with open(mf, encoding="utf-8") as f:
                updates.extend(parser.handle_ws_frame(f.read().strip()))
        return updates

    def test_normalizer_produces_results(self, dk_updates) -> None:
        normalizer = Normalizer(normalizers={"DraftKings": DraftKingsNormalizer()})
        results = normalizer.normalize_batch(dk_updates)
        assert len(results) > 0, f"Expected normalized results from {len(dk_updates)} updates"

    def test_output_validity(self, dk_updates) -> None:
        normalizer = Normalizer(normalizers={"DraftKings": DraftKingsNormalizer()})
        results = normalizer.normalize_batch(dk_updates)
        _validate_output(results)

    def test_no_exceptions(self, dk_updates) -> None:
        """Normalization must not raise for any real-world update."""
        n = DraftKingsNormalizer()
        for u in dk_updates:
            n.normalize(u)  # should not raise

    def test_yield_rate(self, dk_updates) -> None:
        """At least 50% of fixture updates should normalize successfully."""
        n = DraftKingsNormalizer()
        successes = sum(1 for u in dk_updates if n.normalize(u) is not None)
        rate = successes / max(len(dk_updates), 1)
        assert rate >= 0.5, f"Yield rate too low: {rate:.1%} ({successes}/{len(dk_updates)})"


# -----------------------------------------------------------------------
# FanDuel
# -----------------------------------------------------------------------

class TestFanDuelNormalizerFixtures:
    """Replay FanDuel fixtures → normalizer."""

    @pytest.fixture()
    def fd_updates(self):
        parser = FanDuelParser()
        ref = os.path.join(FIXTURES, "fanduel", "fanduel_messages", "json_1.json")
        with open(ref, encoding="utf-8") as f:
            d = json.load(f)
            parser.handle_http_body("content-managed-page", json.dumps(d.get("data", d)))

        updates = []
        msg_dir = os.path.join(FIXTURES, "fanduel", "fanduel_messages")
        for mf in sorted(glob.glob(os.path.join(msg_dir, "ws_*.txt"))):
            with open(mf, encoding="utf-8") as f:
                d = json.load(f)
                updates.extend(parser.handle_http_body("getMarketPrices", json.dumps(d.get("data", d))))
        return updates

    def test_normalizer_produces_results(self, fd_updates) -> None:
        normalizer = Normalizer(normalizers={"FanDuel": FanDuelNormalizer()})
        results = normalizer.normalize_batch(fd_updates)
        assert len(results) > 0, f"Expected normalized results from {len(fd_updates)} updates"

    def test_output_validity(self, fd_updates) -> None:
        normalizer = Normalizer(normalizers={"FanDuel": FanDuelNormalizer()})
        results = normalizer.normalize_batch(fd_updates)
        _validate_output(results)

    def test_no_exceptions(self, fd_updates) -> None:
        n = FanDuelNormalizer()
        for u in fd_updates:
            n.normalize(u)

    def test_yield_rate(self, fd_updates) -> None:
        n = FanDuelNormalizer()
        successes = sum(1 for u in fd_updates if n.normalize(u) is not None)
        rate = successes / max(len(fd_updates), 1)
        assert rate >= 0.5, f"Yield rate too low: {rate:.1%} ({successes}/{len(fd_updates)})"


# -----------------------------------------------------------------------
# BetMGM
# -----------------------------------------------------------------------

class TestBetMGMNormalizerFixtures:
    """Replay BetMGM fixtures → normalizer."""

    @pytest.fixture()
    def mgm_updates(self):
        parser = BetMGMParser()
        ref = os.path.join(FIXTURES, "betmgm", "betmgm_messages", "json_1.json")
        with open(ref, encoding="utf-8") as f:
            d = json.load(f)
            parser.handle_http_body("fixture-view", json.dumps(d.get("data", d)))

        updates = []
        for mf in sorted(glob.glob(os.path.join(FIXTURES, "betmgm", "betmgm_messages", "ws_*.txt"))):
            with open(mf, encoding="utf-8") as f:
                raw = f.read().strip()
            updates.extend(parser.handle_ws_frame(raw + "\x1e"))
        return updates

    def test_normalizer_produces_results(self, mgm_updates) -> None:
        normalizer = Normalizer(normalizers={"BetMGM": BetMGMNormalizer()})
        results = normalizer.normalize_batch(mgm_updates)
        assert len(results) > 0, f"Expected normalized results from {len(mgm_updates)} updates"

    def test_output_validity(self, mgm_updates) -> None:
        normalizer = Normalizer(normalizers={"BetMGM": BetMGMNormalizer()})
        results = normalizer.normalize_batch(mgm_updates)
        _validate_output(results)

    def test_no_exceptions(self, mgm_updates) -> None:
        n = BetMGMNormalizer()
        for u in mgm_updates:
            n.normalize(u)

    def test_yield_rate(self, mgm_updates) -> None:
        n = BetMGMNormalizer()
        successes = sum(1 for u in mgm_updates if n.normalize(u) is not None)
        rate = successes / max(len(mgm_updates), 1)
        assert rate >= 0.5, f"Yield rate too low: {rate:.1%} ({successes}/{len(mgm_updates)})"


# -----------------------------------------------------------------------
# Betano
# -----------------------------------------------------------------------

class TestBetanoNormalizerFixtures:
    """Replay Betano fixtures → normalizer."""

    @pytest.fixture()
    def betano_updates(self):
        parser = BetanoParser()
        ref = os.path.join(FIXTURES, "betano", "betano_messages", "json_1.json")
        with open(ref, encoding="utf-8") as f:
            d = json.load(f)
            parser.handle_http_body(
                "https://www.betano.ca/danae-webapi/api/live/overview/1?isInit=false&includeVirtuals=true",
                json.dumps(d.get("data", d)),
            )

        updates = []
        for mf in sorted(glob.glob(os.path.join(FIXTURES, "betano", "betano_messages", "ws_*.txt"))):
            with open(mf, encoding="utf-8") as f:
                raw = f.read().strip()
            updates.extend(parser.handle_ws_frame(raw + "\x1e"))
        return updates

    def test_normalizer_produces_results(self, betano_updates) -> None:
        normalizer = Normalizer(normalizers={"Betano": BetanoNormalizer()})
        results = normalizer.normalize_batch(betano_updates)
        assert len(results) > 0, f"Expected normalized results from {len(betano_updates)} updates"

    def test_output_validity(self, betano_updates) -> None:
        normalizer = Normalizer(normalizers={"Betano": BetanoNormalizer()})
        results = normalizer.normalize_batch(betano_updates)
        _validate_output(results)

    def test_no_exceptions(self, betano_updates) -> None:
        n = BetanoNormalizer()
        for u in betano_updates:
            n.normalize(u)

    def test_yield_rate(self, betano_updates) -> None:
        n = BetanoNormalizer()
        successes = sum(1 for u in betano_updates if n.normalize(u) is not None)
        rate = successes / max(len(betano_updates), 1)
        assert rate >= 0.3, f"Yield rate too low: {rate:.1%} ({successes}/{len(betano_updates)})"


# -----------------------------------------------------------------------
# Caesars
# -----------------------------------------------------------------------

class TestCaesarsNormalizerFixtures:
    """Replay Caesars fixtures → normalizer."""

    @pytest.fixture()
    def cae_updates(self):
        parser = CaesarsParser()
        ref = os.path.join(FIXTURES, "caesars", "messages", "json_5.json")
        with open(ref, encoding="utf-8") as f:
            parser.handle_http_body("https://api.americanwagering.com/v4/home", f.read())

        updates = []
        for mf in sorted(glob.glob(os.path.join(FIXTURES, "caesars", "messages", "ws_*.txt"))):
            with open(mf, encoding="utf-8") as f:
                updates.extend(parser.handle_ws_frame(f.read().strip()))
        return updates

    def test_normalizer_produces_results(self, cae_updates) -> None:
        normalizer = Normalizer(normalizers={"Caesars": CaesarsNormalizer()})
        results = normalizer.normalize_batch(cae_updates)
        assert len(results) > 0, f"Expected normalized results from {len(cae_updates)} updates"

    def test_output_validity(self, cae_updates) -> None:
        normalizer = Normalizer(normalizers={"Caesars": CaesarsNormalizer()})
        results = normalizer.normalize_batch(cae_updates)
        _validate_output(results)

    def test_no_exceptions(self, cae_updates) -> None:
        n = CaesarsNormalizer()
        for u in cae_updates:
            n.normalize(u)

    def test_yield_rate(self, cae_updates) -> None:
        n = CaesarsNormalizer()
        successes = sum(1 for u in cae_updates if n.normalize(u) is not None)
        rate = successes / max(len(cae_updates), 1)
        assert rate >= 0.5, f"Yield rate too low: {rate:.1%} ({successes}/{len(cae_updates)})"
