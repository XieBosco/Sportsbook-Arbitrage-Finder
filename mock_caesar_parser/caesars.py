"""Caesars Sportsbook live odds parser.

Subclass of BookParser handling:
- Initial state ingestion from /v4/home HTTP response body.
- Live Diffusion protocol WebSocket frames (0x23, 0x00, 0x04, 0x84, 0x05, 0x85, 0x06).
- Topic alias management and binary delta application.
- Normalization into standardized OddsUpdate objects.
"""

from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timezone
from typing import Any

from arbfinder.normalization.models import OddsUpdate
from arbfinder.parsers._helpers import clean_american_odds, split_fixture_name
from arbfinder.parsers.base import BookParser
try:
    from mock_caesar_parser.diffusion_codec import (
        AliasStateStore,
        apply_binary_delta,
        classify_object,
        decode_cbor_item,
        find_alias_and_cbor_type04,
        find_alias_and_cbor_type84,
        parse_type05,
        parse_type85,
    )
except ImportError:
    try:
        from diffusion_codec import (
            AliasStateStore,
            apply_binary_delta,
            classify_object,
            decode_cbor_item,
            find_alias_and_cbor_type04,
            find_alias_and_cbor_type84,
            parse_type05,
            parse_type85,
        )
    except ImportError:
        from arbfinder.parsers.diffusion_codec import (
            AliasStateStore,
            apply_binary_delta,
            classify_object,
            decode_cbor_item,
            find_alias_and_cbor_type04,
            find_alias_and_cbor_type84,
            parse_type05,
            parse_type85,
        )
from arbfinder.parsers.unresolved_log import record_unresolved_parser_id

__all__ = ["CaesarsParser"]

logger = logging.getLogger(__name__)


def _american_to_decimal(am: int | float) -> float:
    """Convert American odds to decimal odds rounded to 4 decimals."""
    if am > 0:
        return round(1.0 + am / 100.0, 4)
    if am < 0:
        return round(1.0 + 100.0 / abs(am), 4)
    return 1.0


class CaesarsParser(BookParser):
    """Parser for Caesars Sportsbook."""

    book_name: str = "Caesars"

    def __init__(self) -> None:
        self.store = AliasStateStore()
        self.reference_data: dict[str, dict[str, Any]] = {
            "events": {},      # event_id -> {name, sport_code, league_name, start_time}
            "markets": {},     # market_id -> {name, handicap, event_id}
            "selections": {},  # sel_id -> {name, market_id, type}
        }
        self.stats: dict[str, Any] = {
            "http_processed": 0,
            "ws_frames": 0,
            "handshakes": 0,
            "full_states": 0,
            "deltas": 0,
            "updates_emitted": 0,
            "delta_failures": 0,
            "errors": [],
        }

    def relevant_http_url(self, url: str) -> bool:
        """True if this HTTP response body should be fetched via getResponseBody."""
        return "/v4/home" in url

    def relevant_ws_url(self, url: str) -> bool:
        """True if this WebSocket connection's frames should be parsed.

        Only attaches to the Diffusion live odds socket (ty=WB).
        Ignores livescores, cashout, and microbetting sockets.
        """
        return "diffusion" in url and "ty=WB" in url

    def reset(self) -> None:
        """Reset parser state and clear topic alias store."""
        logger.info("[Caesars] Resetting parser state and alias store.")
        self.store.reset()

    @property
    def is_initialized(self) -> bool:
        """True if reference events have been populated from /v4/home."""
        return bool(self.reference_data["events"])

    def handle_http_body(self, url: str, body: str) -> list[OddsUpdate]:
        """Parse initial /v4/home state snapshot into reference_data."""
        if not self.relevant_http_url(url):
            return []

        try:
            payload = json.loads(body)
        except Exception as e:
            logger.warning("[Caesars] Failed to parse JSON from %s: %s", url, e)
            return []

        data = payload.get("data", payload)
        event_groups = data.get("eventDisplayGroups", [])
        if not isinstance(event_groups, list):
            return []

        events_count = 0
        markets_count = 0
        selections_count = 0

        for edg in event_groups:
            if not isinstance(edg, dict):
                continue
            for ev in edg.get("events", []):
                if not isinstance(ev, dict):
                    continue
                ev_id = ev.get("id")
                if not ev_id:
                    continue
                ev_id_str = str(ev_id)
                ev_name = ev.get("name", "")
                sport_code = str(
                    ev.get("sportName")
                    or edg.get("sportName")
                    or ev.get("sportId")
                    or ev.get("sport_code")
                    or ""
                )
                league_name = str(ev.get("competitionName") or ev.get("league_name") or "")
                start_time = str(ev.get("startTime") or ev.get("start_time") or "")

                self.reference_data["events"][ev_id_str] = {
                    "name": ev_name,
                    "sport_code": sport_code,
                    "league_name": league_name,
                    "start_time": start_time,
                }
                events_count += 1

                for kmg in ev.get("keyMarketGroups", []):
                    if not isinstance(kmg, dict):
                        continue
                    for mkt in kmg.get("markets", []):
                        if not isinstance(mkt, dict):
                            continue
                        mkt_id = mkt.get("id")
                        if not mkt_id:
                            continue
                        mkt_id_str = str(mkt_id)
                        raw_name = mkt.get("name", "")
                        mkt_name = raw_name.replace("|", "").strip()

                        raw_line = mkt.get("line")
                        handicap_val: float | None = None
                        if raw_line is not None:
                            try:
                                handicap_val = float(raw_line)
                            except (ValueError, TypeError):
                                handicap_val = None

                        self.reference_data["markets"][mkt_id_str] = {
                            "name": mkt_name,
                            "handicap": handicap_val,
                            "event_id": ev_id_str,
                        }
                        markets_count += 1

                        for sel in mkt.get("selections", []):
                            if not isinstance(sel, dict):
                                continue
                            sel_id = sel.get("id")
                            if not sel_id:
                                continue
                            sel_id_str = str(sel_id)
                            raw_sel_name = sel.get("name", "")
                            sel_name = raw_sel_name.replace("|", "").strip()
                            sel_type = str(sel.get("type", ""))

                            self.reference_data["selections"][sel_id_str] = {
                                "name": sel_name,
                                "market_id": mkt_id_str,
                                "type": sel_type,
                            }
                            selections_count += 1

        self.stats["http_processed"] += 1
        logger.info(
            "[Caesars] Ingested /v4/home: %d events, %d markets, %d selections",
            events_count,
            markets_count,
            selections_count,
        )
        return []

    def update_enrichment_line(self, market_id: str, new_line: float | None) -> None:
        """Update market handicap in reference_data so child selections use the fresh line."""
        mkt_id_str = str(market_id)
        if mkt_id_str in self.reference_data["markets"]:
            val = float(new_line) if new_line is not None else None
            self.reference_data["markets"][mkt_id_str]["handicap"] = val
            logger.debug("[Caesars] Updated line for market %s -> %s", mkt_id_str, val)

    def handle_ws_frame(self, payload: str) -> list[OddsUpdate]:
        """Parse raw WebSocket frame payload (base64 Diffusion format)."""
        cleaned = payload.strip()
        if not cleaned:
            return []

        try:
            data = base64.b64decode(cleaned)
        except Exception as e:
            logger.warning("[Caesars] Base64 decode failed for frame: %s", e)
            return []

        if len(data) == 0:
            return []

        self.stats["ws_frames"] += 1
        msg_type = data[0]
        now = datetime.now(timezone.utc)

        # 0x23: Connection Handshake
        if msg_type == 0x23:
            self.stats["handshakes"] += 1
            logger.info("[Caesars] Handshake (0x23) received")
            return []

        # 0x00: Subscription path (keepalive / topic subscribe)
        if msg_type == 0x00:
            return []

        # 0x06: Topic alias acknowledgement
        if msg_type == 0x06:
            return []

        # 0x84: Compressed Full State Binding
        if msg_type == 0x84:
            alias_hex, cbor_bytes = find_alias_and_cbor_type84(data)
            if alias_hex and cbor_bytes:
                return self._handle_full_state(alias_hex, cbor_bytes, now)
            return []

        # 0x04: Uncompressed Full State Binding
        if msg_type == 0x04:
            alias_hex, cbor_bytes = find_alias_and_cbor_type04(data)
            if alias_hex and cbor_bytes:
                return self._handle_full_state(alias_hex, cbor_bytes, now)
            return []

        # 0x05: Uncompressed Binary Delta
        if msg_type == 0x05:
            alias_hex, delta_payload = parse_type05(data)
            if alias_hex and delta_payload:
                return self._handle_binary_delta(alias_hex, delta_payload, now)
            return []

        # 0x85: Compressed Binary Delta
        if msg_type == 0x85:
            alias_hex, delta_payload = parse_type85(data)
            if alias_hex and delta_payload:
                return self._handle_binary_delta(alias_hex, delta_payload, now)
            return []

        return []

    def _handle_full_state(
        self, alias_hex: str, cbor_bytes: bytes, captured_at: datetime | None
    ) -> list[OddsUpdate]:
        """Process full state binding (0x04 / 0x84)."""
        try:
            obj, end_pos = decode_cbor_item(cbor_bytes, 0)
            if not isinstance(obj, dict) or end_pos != len(cbor_bytes):
                return []
        except Exception as e:
            # Corrupt frame must NOT be stored into store
            logger.debug("[Caesars] CBOR decode failed for alias %s: %s", alias_hex, e)
            return []

        self.stats["full_states"] += 1
        # Only store once decoded successfully
        self.store.set(alias_hex, cbor_bytes)

        obj_id = str(obj["id"]) if "id" in obj else None
        if obj_id:
            self.store.set_uuid(alias_hex, obj_id)

        obj_type = classify_object(obj)

        if obj_type == "event":
            return []

        if obj_type == "market":
            if obj_id and "line" in obj:
                self.update_enrichment_line(obj_id, obj["line"])
            return []

        if obj_type == "selection" or "price" in obj:
            uuid = obj_id or self.store.get_uuid(alias_hex) or alias_hex
            updates = self._build_odds_update(obj, uuid, captured_at)
            self.stats["updates_emitted"] += len(updates)
            return updates

        return []

    def _handle_binary_delta(
        self, alias_hex: str, delta_payload: bytes, captured_at: datetime | None
    ) -> list[OddsUpdate]:
        """Apply a binary delta onto the alias's current CBOR state."""
        if not self.store.contains(alias_hex):
            logger.debug("[Caesars] Skipping delta for untracked alias %s", alias_hex)
            return []

        old_cbor = self.store.get(alias_hex)
        if not old_cbor:
            return []

        try:
            new_cbor = apply_binary_delta(old_cbor, delta_payload)
            obj, end_pos = decode_cbor_item(new_cbor, 0)
            if not isinstance(obj, dict) or end_pos != len(new_cbor):
                self.stats["delta_failures"] += 1
                return []
        except Exception as e:
            # Delta application failure preserves alias in store for subsequent updates
            self.stats["delta_failures"] += 1
            logger.debug("[Caesars] Delta application failed for alias %s: %s", alias_hex, e)
            return []

        self.stats["deltas"] += 1
        self.store.set(alias_hex, new_cbor)

        obj_id = str(obj["id"]) if "id" in obj else None
        if obj_id:
            self.store.set_uuid(alias_hex, obj_id)

        obj_type = classify_object(obj)

        if obj_type == "event":
            return []

        if obj_type == "market":
            target_id = obj_id or self.store.get_uuid(alias_hex)
            if target_id and "line" in obj:
                self.update_enrichment_line(target_id, obj["line"])
            return []

        if obj_type == "selection" or "price" in obj:
            uuid = obj_id or self.store.get_uuid(alias_hex) or alias_hex
            updates = self._build_odds_update(obj, uuid, captured_at)
            self.stats["updates_emitted"] += len(updates)
            return updates

        return []

    def _build_odds_update(
        self, obj: dict[str, Any], sel_id: str, captured_at: datetime | None
    ) -> list[OddsUpdate]:
        """Construct OddsUpdate from a decoded selection dict and reference metadata."""
        price = obj.get("price")
        if not isinstance(price, dict):
            return []

        odds_val: float | None = None
        if "d" in price and price["d"] is not None:
            try:
                odds_val = float(price["d"])
            except (ValueError, TypeError):
                pass

        if odds_val is None and "a" in price and price["a"] is not None:
            am_clean = clean_american_odds(price["a"])
            if am_clean is not None:
                odds_val = _american_to_decimal(am_clean)

        if odds_val is None or odds_val <= 1.0:
            return []

        sel_id_str = str(sel_id)
        sel_meta = self.reference_data["selections"].get(sel_id_str, {})

        market_id = sel_meta.get("market_id", "")
        mkt_meta = self.reference_data["markets"].get(market_id, {}) if market_id else {}

        event_id = mkt_meta.get("event_id") or sel_meta.get("event_id", "")
        event_meta = self.reference_data["events"].get(event_id, {}) if event_id else {}

        # Selection outcome label
        raw_name = sel_meta.get("name") or obj.get("name", "")
        sel_name = str(raw_name).replace("|", "").strip()
        if not sel_name:
            record_unresolved_parser_id(self.book_name, "selection_name", sel_id_str)
            return []

        # Market type and line
        raw_mkt_name = (
            mkt_meta.get("name")
            or sel_meta.get("market_name")
            or obj.get("market_name", "")
        )
        mkt_name = str(raw_mkt_name).replace("|", "").strip()

        raw_line_val: float | None = None
        if "handicap" in mkt_meta and mkt_meta["handicap"] is not None:
            raw_line_val = float(mkt_meta["handicap"])
        elif "market_line" in sel_meta and sel_meta["market_line"] is not None:
            raw_line_val = float(sel_meta["market_line"])
        elif "line" in obj and obj["line"] is not None:
            try:
                raw_line_val = float(obj["line"])
            except (ValueError, TypeError):
                raw_line_val = None

        # Event attributes
        event_name = event_meta.get("name") or sel_meta.get("event_name", "")
        sport_code = event_meta.get("sport_code") or sel_meta.get("sport_code", "")
        league_name = event_meta.get("league_name") or sel_meta.get("league_name", "")
        start_time = event_meta.get("start_time") or sel_meta.get("start_time", "")

        home_team, away_team = split_fixture_name(event_name) if event_name else ("", "")

        if raw_line_val is not None:
            sel_type = str(sel_meta.get("type") or obj.get("type", "")).lower()
            # Caesars' market line always represents the Home team's handicap.
            # Invert line for the Away team.
            is_away = (sel_type == "away") or (
                not sel_type
                and bool(away_team)
                and (
                    sel_name == away_team
                    or sel_name.startswith(away_team + " ")
                    or sel_name.startswith(away_team + "+")
                    or sel_name.startswith(away_team + "-")
                )
            )
            if is_away:
                raw_line_val = -raw_line_val
                if raw_line_val == 0.0:
                    raw_line_val = 0.0

        if not event_id:
            record_unresolved_parser_id(self.book_name, "selection_id", sel_id_str)

        cap_time = captured_at or datetime.now(timezone.utc)

        update = OddsUpdate(
            book_id=self.book_name,
            raw_event_id=event_id,
            raw_sport_code=sport_code,
            raw_league_name=league_name,
            raw_home_team=home_team,
            raw_away_team=away_team,
            raw_start_time=start_time,
            raw_market_type=mkt_name,
            raw_selection=sel_name,
            raw_line=raw_line_val,
            odds_value=odds_val,
            odds_format="decimal",
            captured_at=cap_time,
            raw_selection_id=sel_id_str,
            raw_market_id=market_id,
        )
        return [update]
