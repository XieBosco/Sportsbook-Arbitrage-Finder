"""Caesars Sportsbook parser.

Ported from caesars_scraper.py. Decodes binary Diffusion WebSocket frames
(Type 4 full state, Type 5 binary deltas) and combines them with /v4/home REST
enrichment dictionaries to emit standardized OddsUpdate instances.
"""

import base64
import json
import logging
from datetime import datetime

from arbfinder.normalization.models import OddsUpdate
from arbfinder.normalization.odds_math import decimal_to_american
from arbfinder.parsers._helpers import split_fixture_name
from arbfinder.parsers.base import BookParser
from arbfinder.parsers.diffusion_codec import (
    AliasStateStore,
    apply_binary_delta,
    classify_object,
    decode_cbor_item,
    find_alias_and_cbor_type04,
    find_alias_and_cbor_type84,
    parse_type05,
)

__all__ = ["CaesarsParser"]

logger = logging.getLogger(__name__)


def _extract_american_odds(price: dict) -> int | None:
    """Extract American odds from a decoded selection's price dict.

    Prefers the direct American odds field ("a"), falling back to converting
    the decimal field ("d"). Returns None if neither is usable.
    """
    if "a" in price and price["a"] is not None:
        try:
            return int(price["a"])
        except (ValueError, TypeError):
            return None
    if "d" in price and price["d"] is not None:
        try:
            return decimal_to_american(float(price["d"]))
        except (ValueError, TypeError):
            return None
    return None


class CaesarsParser(BookParser):
    """Parser for Caesars Sportsbook."""

    book_name: str = "Caesars"

    def __init__(self):
        # Global state to store reference data
        self.reference_data: dict[str, dict] = {
            "events": {},
            "markets": {},
            "selections": {},
        }

        # Running Diffusion session alias state store
        self.store = AliasStateStore()

    def relevant_http_url(self, url: str) -> bool:
        """True if this HTTP response body should be fetched via getResponseBody."""
        # /v4/home carries the complete event/market/selection reference tree
        return "/v4/home" in url

    def relevant_ws_url(self, url: str) -> bool:
        """True if this WebSocket connection's frames should be parsed."""
        # Caesars Diffusion odds WebSocket endpoint
        return "/diffusion?ty=WB" in url

    def reset(self) -> None:
        """Reset internal Diffusion alias state.

        NOTE: This is NOT currently wired to CDP socket-close events (e.g. via session_manager.py).
        In production, reliance is on the 0x23 handshake resetting alias state on any new
        Diffusion session instead. This method is provided as an explicit hook/utility
        for manual state clearing or future socket-close event wiring.
        """
        self.store.reset()

    def handle_http_body(self, url: str, body: str) -> list[OddsUpdate]:
        """Parse /v4/home REST JSON enrichment dictionary.

        Ported from caesars_scraper.py build_enrichment_lookup_from_json.
        Traverses eventDisplayGroups[].events[].keyMarketGroups[].markets[].selections[]
        (note: keyMarketGroups is a list, not a dict).
        """
        try:
            json_data = json.loads(body)
        except (json.JSONDecodeError, TypeError):
            return []

        home = json_data.get("data", json_data)
        if not isinstance(home, dict):
            return []

        for edg in home.get("eventDisplayGroups", []):
            if not isinstance(edg, dict):
                continue
            sport_code = str(edg.get("sportName") or edg.get("sportId", ""))
            league_name = str(edg.get("competitionName") or edg.get("competitionId", ""))
            
            for event in edg.get("events", []):
                if not isinstance(event, dict):
                    continue
                self._register_event(event, sport_code, league_name)

        return []

    def _register_event(self, event: dict, sport_code: str, league_name: str) -> None:
        event_id = str(event.get("id", ""))
        event_name = event.get("name", "").replace("|", "").strip()
        start_time = event.get("startTime", "")
        self.reference_data["events"][event_id] = {
            "name": event_name,
            "sport_code": sport_code,
            "league_name": league_name,
            "start_time": start_time,
        }

        for group in event.get("keyMarketGroups", []):
            if not isinstance(group, dict):
                continue
            for market in group.get("markets", []):
                if not isinstance(market, dict):
                    continue
                self._register_market(market, event_id)

    def _register_market(self, market: dict, event_id: str) -> None:
        market_id = str(market.get("id", ""))
        market_name = market.get("name", "").replace("|", "").strip()
        market_line = market.get("line", None)
        self.reference_data["markets"][market_id] = {
            "name": market_name,
            "handicap": market_line,
            "event_id": event_id,
        }

        for sel in market.get("selections", []):
            if not isinstance(sel, dict):
                continue
            sel_id = str(sel.get("id", ""))
            sel_name = sel.get("name", "").replace("|", "").strip()
            self.reference_data["selections"][sel_id] = {
                "name": sel_name,
                "market_id": market_id,
                "type": sel.get("type", ""),
            }

    def update_enrichment_line(
        self, market_uuid: str, new_line: float | int | None
    ) -> None:
        """Propagate a market's new handicap line into enrichment lookups.

        Ported from caesars_scraper.py update_enrichment_line.
        When a market delta carries a changed line, updates market_lookup.
        Selections now dynamically fetch their parent market's line.
        """
        if market_uuid in self.reference_data["markets"]:
            self.reference_data["markets"][market_uuid]["handicap"] = new_line

    def _build_odds_update(
        self, obj: dict, uuid: str, now: datetime
    ) -> list[OddsUpdate]:
        """Convert a decoded selection CBOR dict into an OddsUpdate."""
        price = obj.get("price")
        if not isinstance(price, dict):
            return []

        # Get decimal odds directly
        if "d" not in price:
            return []

        enr = self.reference_data["selections"].get(uuid)
        if not enr:
            from arbfinder.parsers.unresolved_log import record_unresolved_parser_id
            record_unresolved_parser_id(self.book_name, "selection_id", uuid)
            enr = {}
            
        market_id = enr.get("market_id", "")
        market_enr = self.reference_data["markets"].get(market_id)
        if market_id and not market_enr:
            from arbfinder.parsers.unresolved_log import record_unresolved_parser_id
            record_unresolved_parser_id(self.book_name, "market_id", market_id)
            market_enr = {}
        elif not market_enr:
            market_enr = {}
            
        event_id = market_enr.get("event_id", "")
        event_enr = self.reference_data["events"].get(event_id)
        if event_id and not event_enr:
            from arbfinder.parsers.unresolved_log import record_unresolved_parser_id
            record_unresolved_parser_id(self.book_name, "event_id", event_id)
            event_enr = {}
        elif not event_enr:
            event_enr = {}

        # Caesars CBOR selection objects carry their own name (e.g. '|Baltimore Orioles|').
        # If REST /v4/home enrichment lookup misses (e.g. mid-session new selection),
        # fallback to the CBOR object's own name (stripped of pipes) before raw UUID.
        cbor_name = obj.get("name")
        if cbor_name and isinstance(cbor_name, str):
            cbor_name = cbor_name.replace("|", "").strip()
        sel_name = enr.get("name") or cbor_name or obj.get("id", uuid)

        m_name = market_enr.get("name", "UNKNOWN_MARKET")
        ev_name = event_enr.get("name", "")
        ev_id = event_id

        # Heuristic assumption (not sourced from prototype — prototype prints full event_name):
        # Caesars fixture names typically follow "Away Team at Home Team"
        home_team, away_team = split_fixture_name(ev_name)
        # split_fixture_name returns (home, away) for ' at '/' @ ' delimiters,
        # which matches the Caesars convention.

        market_line = market_enr.get("handicap")
        handicap_val = None
        if market_line is not None:
            try:
                handicap_val = float(market_line)
                sel_type = enr.get("type", "")
                # By cross-referencing with Moneyline odds, Caesars' market line 
                # ALWAYS represents the Home team's handicap.
                # We must invert it for the Away team.
                if sel_type == "away" or (not sel_type and sel_name == away_team):
                    handicap_val = -handicap_val
            except (ValueError, TypeError):
                pass

        try:
            price_val = float(price.get("d"))
        except (ValueError, TypeError):
            return []

        return [
            OddsUpdate(
                book_id=self.book_name,
                raw_event_id=ev_id,
                raw_sport_code=event_enr.get("sport_code", ""),
                raw_league_name=event_enr.get("league_name", ""),
                raw_home_team=home_team,
                raw_away_team=away_team,
                raw_start_time=event_enr.get("start_time", ""),
                raw_market_type=m_name,
                raw_selection=sel_name,
                raw_line=handicap_val,
                odds_value=price_val,
                odds_format="decimal",
                captured_at=now,
            )
        ]

    def _process_decoded_object(
        self, alias_hex: str, obj: object, now: datetime
    ) -> list[OddsUpdate]:
        """Update alias/enrichment state from a freshly decoded CBOR object and,
        if it's a selection, emit the corresponding OddsUpdate.

        Shared by full-state frames (Type 4/0x84) and post-delta state (Type 5).
        """
        if isinstance(obj, dict) and "id" in obj:
            self.store.set_uuid(alias_hex, obj["id"])

        uuid = self.store.get_uuid(alias_hex) or alias_hex
        obj_type = classify_object(obj) if isinstance(obj, dict) else "unknown"

        if obj_type == "market" and isinstance(obj, dict) and "line" in obj:
            self.update_enrichment_line(uuid, obj["line"])

        if obj_type == "selection" and isinstance(obj, dict):
            return self._build_odds_update(obj, uuid, now)
        return []

    def _handle_full_state(
        self, alias_hex: str, cbor_bytes: bytes, now: datetime
    ) -> list[OddsUpdate]:
        """Shared logic for Type 0x04 and 0x84 full-state frames.

        Stores the CBOR bytes in the alias state store, decodes the CBOR object,
        updates UUID bindings, propagates market line changes, and emits
        OddsUpdate for selection objects.
        """
        self.store.set(alias_hex, cbor_bytes)
        try:
            obj, _ = decode_cbor_item(cbor_bytes, 0)
        except Exception:
            logger.debug("Caesars: failed to decode CBOR for alias %s", alias_hex)
            return []

        return self._process_decoded_object(alias_hex, obj, now)

    def _handle_binary_delta(
        self, alias_hex: str, delta_payload: bytes, now: datetime
    ) -> list[OddsUpdate]:
        """Handle a Type 0x05 binary delta frame: patch the stored CBOR state,
        decode the result, and process it like a full-state update."""
        if not self.store.contains(alias_hex):
            # Mid-session attach: skip gracefully per prototype
            return []

        old_cbor = self.store.get(alias_hex)
        try:
            new_cbor = apply_binary_delta(old_cbor, delta_payload)
            obj, end = decode_cbor_item(new_cbor, 0)
            if not (isinstance(obj, dict) and end == len(new_cbor)):
                return []
        except Exception:
            logger.debug("Caesars: failed to apply delta for alias %s", alias_hex)
            return []

        # Chained state replacement
        self.store.set(alias_hex, new_cbor)
        return self._process_decoded_object(alias_hex, obj, now)

    def handle_ws_frame(self, payload: str) -> list[OddsUpdate]:
        """Parse a raw Diffusion WebSocket frame payload."""
        if not payload:
            return []

        try:
            raw_bytes = base64.b64decode(payload)
        except Exception:
            raw_bytes = payload.encode("utf-8")

        if len(raw_bytes) == 0:
            return []

        msg_type = raw_bytes[0]
        now = datetime.now()

        # ── 0x23 Handshake ──────────────────────────────────────────
        if msg_type == 0x23:
            # New Diffusion session handshake resets all alias state
            self.store.reset()
            return []

        # ── 0x00 Subscription / 0x06 Ack ────────────────────────────
        if msg_type in (0x00, 0x06):
            return []

        # ── 0x84 Type 4 Compressed Full State ───────────────────────
        if msg_type == 0x84:
            alias_hex, cbor_bytes = find_alias_and_cbor_type84(raw_bytes)
            if not alias_hex or not cbor_bytes:
                return []
            return self._handle_full_state(alias_hex, cbor_bytes, now)

        # ── 0x04 Type 4 Uncompressed Full State ─────────────────────
        if msg_type == 0x04:
            alias_hex, cbor_bytes = find_alias_and_cbor_type04(raw_bytes)
            if not alias_hex or not cbor_bytes:
                return []
            return self._handle_full_state(alias_hex, cbor_bytes, now)

        # ── 0x05 Type 5 Binary Delta ────────────────────────────────
        if msg_type == 0x05:
            alias_hex, delta_payload = parse_type05(raw_bytes)
            if not alias_hex:
                return []
            return self._handle_binary_delta(alias_hex, delta_payload, now)

        logger.debug("Caesars: unknown message type 0x%02x, skipping", msg_type)
        return []
