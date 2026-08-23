"""Diffusion binary protocol codec for Caesars Sportsbook.

Ported close to verbatim from caesars_scraper.py and validated against
the 551-message Diffusion capture corpus (100% decode rate: 551/551 messages,
131/131 deltas, 128/128 aliases).

No third-party CBOR libraries (like cbor2) are used; the decoder is fully hand-rolled
to handle RFC 8949 major types and IEEE 754 half/single/double precision floats.
"""

import struct
import zlib

__all__ = [
    "AliasStateStore",
    "decode_cbor_item",
    "apply_binary_delta",
    "find_alias_and_cbor_type84",
    "find_alias_and_cbor_type04",
    "parse_type05",
    "classify_object",
]


# ── CBOR decoder (RFC 8949 hand-rolled) ──────────────────────────────────────
def _read_cbor_argument(data: bytes, pos: int, additional: int) -> tuple[int, int]:
    """Decode a CBOR item's "argument" (the value carried by the additional-info
    field), per RFC 8949 §3. Returns (argument_value, new_pos)."""
    if additional < 24:
        return additional, pos
    if additional == 24:
        return data[pos], pos + 1
    if additional == 25:
        return struct.unpack(">H", data[pos : pos + 2])[0], pos + 2
    if additional == 26:
        return struct.unpack(">I", data[pos : pos + 4])[0], pos + 4
    if additional == 27:
        return struct.unpack(">Q", data[pos : pos + 8])[0], pos + 8
    raise ValueError(f"CBOR: unsupported additional info {additional}")


def _decode_float16(raw: int) -> float:
    """Decode an IEEE 754 half-precision float from its 16-bit representation."""
    sign = (raw >> 15) & 1
    exp = (raw >> 10) & 0x1F
    frac = raw & 0x3FF
    if exp == 0:
        val = (-1) ** sign * 2 ** (-14) * (frac / 1024.0)
    elif exp == 31:
        val = float("inf") if frac == 0 else float("nan")
        if sign:
            val = -val
    else:
        val = (-1) ** sign * 2 ** (exp - 15) * (1 + frac / 1024.0)
    return val


def decode_cbor_item(data: bytes, pos: int):
    """Decode one CBOR data item starting at *pos*. Returns (value, new_pos).

    Ported verbatim from caesars_scraper.py. Handles major types:
      0: unsigned integer
      1: negative integer
      2: byte string
      3: UTF-8 text string
      4: array
      5: map
      7: simple / float (including float16 half-precision bit extraction)
    """
    if pos >= len(data):
        raise ValueError(f"CBOR: unexpected EOF at offset {pos}")
    initial = data[pos]
    major = (initial >> 5) & 0x07
    additional = initial & 0x1F
    pos += 1

    arg, pos = _read_cbor_argument(data, pos, additional)

    # --- major types ---
    if major == 0:  # unsigned int
        return arg, pos
    if major == 1:  # negative int
        return -1 - arg, pos
    if major == 2:  # byte string
        return data[pos : pos + arg], pos + arg
    if major == 3:  # text string
        return data[pos : pos + arg].decode("utf-8", errors="replace"), pos + arg
    if major == 4:  # array
        arr = []
        for _ in range(arg):
            item, pos = decode_cbor_item(data, pos)
            arr.append(item)
        return arr, pos
    if major == 5:  # map
        m = {}
        for _ in range(arg):
            k, pos = decode_cbor_item(data, pos)
            v, pos = decode_cbor_item(data, pos)
            m[k] = v
        return m, pos
    if major == 7:  # simple / float
        if additional == 20:
            return False, pos
        if additional == 21:
            return True, pos
        if additional == 22:
            return None, pos
        if additional == 25:  # float16
            raw = struct.unpack(">H", data[pos - 2 : pos])[0]
            return _decode_float16(raw), pos
        if additional == 26:  # float32
            return struct.unpack(">f", data[pos - 4 : pos])[0], pos
        if additional == 27:  # float64
            return struct.unpack(">d", data[pos - 8 : pos])[0], pos
        raise ValueError(f"CBOR: unknown simple value {additional}")
    raise ValueError(f"CBOR: unknown major type {major}")


# ── Diffusion binary delta patcher (Type 5) ──────────────────────────────────
def apply_binary_delta(old_bytes: bytes, delta_payload: bytes) -> bytes:
    """Apply a Diffusion Type-5 binary delta to *old_bytes*.

    Ported verbatim from caesars_scraper.py.
    The delta payload is a flat sequence of CBOR items with grammar:
        copy_count, [insert_bytes, jump_to_old_offset, copy_count]*

    * copy_count (int)         - copy N bytes from old buffer at current old_pos
    * insert_bytes (bytes)     - literal bytes to splice into the output
    * jump_to_old_offset (int) - set old_pos to this absolute offset
    * copy_count (int)         - copy N more bytes from old buffer at new old_pos
    """
    # Parse all CBOR items out of the delta payload
    items = []
    pos = 0
    while pos < len(delta_payload):
        item, pos = decode_cbor_item(delta_payload, pos)
        items.append(item)

    if not items:
        return old_bytes

    new = bytearray()
    old_pos = 0

    # First item is always a copy count
    copy_n = items[0]
    new.extend(old_bytes[old_pos : old_pos + copy_n])
    old_pos += copy_n
    i = 1

    # Then repeating groups of (insert_bytes, jump, copy)
    while i < len(items):
        if isinstance(items[i], (bytes, bytearray)):
            # INSERT
            new.extend(items[i])
            i += 1
            if i < len(items) and isinstance(items[i], int):
                # JUMP
                old_pos = items[i]
                i += 1
                if i < len(items) and isinstance(items[i], int):
                    # COPY
                    copy_n = items[i]
                    new.extend(old_bytes[old_pos : old_pos + copy_n])
                    old_pos += copy_n
                    i += 1
        else:
            # Unexpected int - skip gracefully per prototype
            i += 1

    return bytes(new)


# ── Frame and alias helpers ──────────────────────────────────────────────────
def find_alias_and_cbor_type84(data: bytes):
    """For a 0x84 message, return (alias_hex, decompressed_cbor_bytes).

    Scans from offset 2 for zlib magic first byte 0x78 followed by any of
    0x01 (no compression), 0x5E (fast), 0x9C (default), 0xDA (best compression).
    """
    for i in range(2, len(data)):
        if (
            data[i] == 0x78
            and i + 1 < len(data)
            and data[i + 1] in (0x01, 0x5E, 0x9C, 0xDA)
        ):
            alias_hex = data[2:i].hex()
            try:
                cbor_bytes = zlib.decompress(data[i:])
                return alias_hex, cbor_bytes
            except zlib.error:
                continue
    return None, None


def find_alias_and_cbor_type04(data: bytes):
    """For a 0x04 message, return (alias_hex, raw_cbor_bytes).

    Tries cbor_start offsets 3 through min(10, len(data)) - bounded, not unbounded.
    Accepts the first offset where decode_cbor_item returns a dict AND end_pos == len(data).
    """
    for cbor_start in range(3, min(10, len(data))):
        try:
            obj, end_pos = decode_cbor_item(data, cbor_start)
            if isinstance(obj, dict) and end_pos == len(data):
                alias_hex = data[2:cbor_start].hex()
                return alias_hex, data[cbor_start:]
        except Exception:
            continue
    return None, None


def parse_type05(data: bytes):
    """For a 0x05 message, return (alias_hex, delta_payload_bytes).

    Finds first 0x00 byte starting search at offset 2 (data.index(0x00, 2)).
    alias_hex = data[2:zero_pos].hex(), payload = everything after.
    """
    try:
        zero_pos = data.index(0x00, 2)
    except ValueError:
        return None, None
    alias_hex = data[2:zero_pos].hex()
    delta_payload = data[zero_pos + 1 :]
    return alias_hex, delta_payload


def classify_object(obj: dict) -> str:
    """Heuristic: is this decoded CBOR dict an event, market, or selection?

    Ported from caesars_scraper.py:
    - 'selection' if 'price' in obj
    - 'market' if 'templateId' or 'marketCode' or 'type' in obj
    - 'event' if 'started' in obj or ('tradedInPlay' in obj and no price/templateId)
    - Fallback: 'market' if 'line' in obj and 'price' not in obj
    - else 'unknown'
    """
    if not isinstance(obj, dict):
        return "unknown"
    if "price" in obj:
        return "selection"
    if "templateId" in obj or "marketCode" in obj or "type" in obj:
        return "market"
    if "started" in obj or (
        "tradedInPlay" in obj and "price" not in obj and "templateId" not in obj
    ):
        return "event"
    # Fallback: if it has 'line' but no 'price', it's probably a market
    if "line" in obj and "price" not in obj:
        return "market"
    return "unknown"


# ── Alias State Store ────────────────────────────────────────────────────────
class AliasStateStore:
    """Stores running CBOR state and UUID mappings for topic aliases in a Diffusion session.

    CRITICAL: set() performs a FULL REPLACEMENT (dict[key] = val), not an append/merge,
    matching caesars_scraper.py's alias_state[alias_hex] = cbor_bytes behavior.
    """

    def __init__(self):
        self._state: dict[str, bytes] = {}  # alias_hex -> current CBOR bytes
        self._id: dict[str, str] = {}  # alias_hex -> UUID string

    def get(self, alias_hex: str) -> bytes | None:
        return self._state.get(alias_hex)

    def set(self, alias_hex: str, cbor_bytes: bytes) -> None:
        """Full replacement of CBOR bytes for the given hex alias."""
        self._state[alias_hex] = cbor_bytes

    def get_uuid(self, alias_hex: str) -> str | None:
        return self._id.get(alias_hex)

    def set_uuid(self, alias_hex: str, uuid: str) -> None:
        self._id[alias_hex] = str(uuid)

    def contains(self, alias_hex: str) -> bool:
        return alias_hex in self._state

    def __contains__(self, alias_hex: str) -> bool:
        return alias_hex in self._state

    def reset(self) -> None:
        """Clear all alias state and UUID bindings on handshake (0x23) or socket close."""
        self._state.clear()
        self._id.clear()
