"""End-to-end integration test for the full pipeline (Stage 3)."""
import json
from datetime import datetime, timezone
import zoneinfo

from arbfinder.matching.bucket_store import BucketStore
from arbfinder.matching.matcher import Matcher
from arbfinder.matching.time_resolver import TimeResolver
from arbfinder.normalization.base_normalizer import BaseNormalizer
from arbfinder.normalization.models import OddsUpdate, NormalizedOddsUpdate
from arbfinder.normalization.normalizer import Normalizer
from arbfinder.parsers.base import BookParser
from arbfinder.pipeline.orchestrator import handle_raw_payload

class _FixtureParser(BookParser):
    book_name: str = "mock_book"

    def relevant_http_url(self, url: str) -> bool:
        return True

    def handle_http_body(self, url: str, body: str) -> list[OddsUpdate]:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return []

        if not isinstance(payload, list):
            payload = [payload]

        now = datetime.now(timezone.utc)
        updates = []
        for ev in payload:
            updates.append(
                OddsUpdate(
                    book_id="mock_book",
                    raw_event_id=ev.get("event_id", ""),
                    raw_sport_code=ev.get("sport", ""),
                    raw_league_name=ev.get("league", ""),
                    raw_home_team=ev.get("home", ""),
                    raw_away_team=ev.get("away", ""),
                    raw_start_time=ev.get("start_time", ""),
                    raw_market_type=ev.get("market", ""),
                    raw_selection=ev.get("selection", ""),
                    raw_line=ev.get("line"),
                    odds_value=ev.get("odds", 0),
                    odds_format=ev.get("odds_format", "american"),
                    captured_at=now,
                )
            )
        return updates

    def handle_ws_frame(self, payload: str) -> list[OddsUpdate]:
        return []

class MockNormalizer(BaseNormalizer):
    def normalize(self, update: OddsUpdate) -> NormalizedOddsUpdate | None:
        if update.raw_home_team == "Nonexistent Team XYZ":
            return None
            
        selection = update.raw_selection.lower()
        if selection == "home":
            selection_canonical = "home"
        elif selection == "away":
            selection_canonical = "away"
        else:
            selection_canonical = "home"
            
        if update.odds_value == -150:
            odds = 1.6667
        elif update.odds_value == -140:
            odds = 1.714
        elif update.odds_value == 130:
            odds = 2.3
        else:
            odds = 2.0
            
        return NormalizedOddsUpdate(
            book_id=update.book_id,
            book_event_id=update.raw_event_id,
            sport_key="basketball",
            league_key="NBA",
            home_team="Los Angeles Lakers",
            away_team="Brooklyn Nets",
            start_time=datetime(2024, 6, 15, 15, 0, tzinfo=zoneinfo.ZoneInfo("America/New_York")),
            market_type="moneyline",
            selection=selection_canonical,
            line=None,
            odds=odds,
            captured_at=datetime(2024, 6, 15, 18, 55, tzinfo=timezone.utc),
        )

class TestPipelineIntegration:
    def _build_infra(self):
        parser_registry = {"mock_book": _FixtureParser()}
        normalizer = Normalizer(normalizers={"mock_book": MockNormalizer()})
        store = BucketStore()
        resolver = TimeResolver()
        matcher = Matcher(store, resolver)
        return parser_registry, normalizer, matcher, store

    def test_single_event_end_to_end(self) -> None:
        parser_registry, normalizer, matcher, store = self._build_infra()
        raw = json.dumps([
            {
                "event_id": "evt-100",
                "sport": "basketball",
                "league": "NBA",
                "home": "LA Lakers",
                "away": "Brooklyn Nets",
                "start_time": "2024-06-15T19:00:00+00:00",
                "market": "Moneyline",
                "selection": "Home",
                "line": None,
                "odds": -150,
                "odds_format": "american",
            }
        ]).encode("utf-8")
        results = handle_raw_payload(
            book_id="mock_book",
            raw_payload=raw,
            parser_registry=parser_registry,
            normalizer=normalizer,
            matcher=matcher,
            bucket_store=store,
        )
        assert len(results) == 1
        ms = results[0]
        assert ms.sport_key == "basketball"
        assert ms.league_key == "NBA"
        assert ms.market_type == "moneyline"
        assert ms.selection == "home"
        assert "mock_book" in ms.book_odds

    def test_multi_book_payload(self) -> None:
        parser_registry, normalizer, matcher, store = self._build_infra()
        payload_a = json.dumps([{
            "event_id": "evt-200",
            "sport": "basketball",
            "league": "NBA",
            "home": "LA Lakers",
            "away": "Brooklyn Nets",
            "start_time": "2024-06-15T19:00:00+00:00",
            "market": "Moneyline",
            "selection": "Home",
            "line": None,
            "odds": -150,
            "odds_format": "american",
        }]).encode()
        payload_b = json.dumps([{
            "event_id": "evt-201",
            "sport": "basketball",
            "league": "NBA",
            "home": "LA Lakers",
            "away": "Brooklyn Nets",
            "start_time": "2024-06-15T19:00:00+00:00",
            "market": "Moneyline",
            "selection": "Home",
            "line": None,
            "odds": -140,
            "odds_format": "american",
        }]).encode()
        handle_raw_payload("mock_book", payload_a, parser_registry, normalizer, matcher, store)
        results = handle_raw_payload("mock_book", payload_b, parser_registry, normalizer, matcher, store)
        assert len(results) == 1
        ms = results[0]
        assert "mock_book" in ms.book_odds

    def test_unknown_parser_returns_empty(self) -> None:
        parser_registry, normalizer, matcher, store = self._build_infra()
        raw = b'{"event_id": "evt-300"}'
        results = handle_raw_payload("unknown_book", raw, parser_registry, normalizer, matcher, store)
        assert results == []

    def test_unresolvable_fields_returns_empty(self) -> None:
        parser_registry, normalizer, matcher, store = self._build_infra()
        raw = json.dumps([{
            "event_id": "evt-400",
            "sport": "basketball",
            "league": "NBA",
            "home": "Nonexistent Team XYZ",
            "away": "Another Fake Team",
            "start_time": "2024-06-15T19:00:00+00:00",
            "market": "Moneyline",
            "selection": "Home",
            "line": None,
            "odds": -110,
            "odds_format": "american",
        }]).encode()
        results = handle_raw_payload("mock_book", raw, parser_registry, normalizer, matcher, store)
        assert results == []

    def test_deduplication_across_multiple_selections(self) -> None:
        parser_registry, normalizer, matcher, store = self._build_infra()
        raw = json.dumps([
            {
                "event_id": "evt-500",
                "sport": "basketball",
                "league": "NBA",
                "home": "LA Lakers",
                "away": "Brooklyn Nets",
                "start_time": "2024-06-15T19:00:00+00:00",
                "market": "Moneyline",
                "selection": "Home",
                "line": None,
                "odds": -150,
                "odds_format": "american",
            },
            {
                "event_id": "evt-500",
                "sport": "basketball",
                "league": "NBA",
                "home": "LA Lakers",
                "away": "Brooklyn Nets",
                "start_time": "2024-06-15T19:00:00+00:00",
                "market": "Moneyline",
                "selection": "Away",
                "line": None,
                "odds": 130,
                "odds_format": "american",
            },
        ]).encode()
        results = handle_raw_payload("mock_book", raw, parser_registry, normalizer, matcher, store)
        assert len(results) == 2
        selections = {r.selection for r in results}
        assert selections == {"home", "away"}
