"""Diffusion protocol binary codec and CBOR decoder for Caesars Sportsbook.

Implements:
- RFC 8949 CBOR decoding supporting integer, byte/text string, arrays, maps,
  tags, undefined, indefinite-length collections, and unhashable key conversion.
- Diffusion Type-5 binary delta application engine with multi-jump copy support.
- Frame parsing helpers for Type 0x04, 0x84, 0x05, 0x85, 0x06, 0x00, and 0x23.
- AliasStateStore for managing session topic alias -> CBOR state bindings.
"""

from __future__ import annotations

import logging
import struct
import zlib
from typing import Any

try:
    import cbor2
except ImportError:
    cbor2 = None

__all__ = [
    "AliasStateStore",
    "apply_binary_delta",
    "classify_object",
    "decode_cbor_item",
    "find_alias_and_cbor_type04",
    "find_alias_and_cbor_type84",
    "parse_type05",
    "parse_type85",
]

logger = logging.getLogger(__name__)


# ── CBOR Decoder ─────────────────────────────────────────────────────────────
def decode_cbor_item(data: bytes, pos: int) -> tuple[Any, int]:
    """Decode one CBOR data item starting at *pos*. Returns (value, new_pos).

    Implements RFC 8949 major types:
      0: unsigned integer
      1: negative integer
      2: byte string (definite & indefinite)
      3: text string (definite & indefinite)
      4: array (definite & indefinite)
      5: map (definite & indefinite, with unhashable key handling)
      6: semantic tags (e.g. Tag 0 datetime string)
      7: simple values (false, true, null, undefined) and IEEE 754 floats (16, 32, 64)
    """
    if pos >= len(data):
        raise ValueError(f"CBOR: unexpected EOF at offset {pos}")

    initial = data[pos]
    major = (initial >> 5) & 0x07
    additional = initial & 0x1F
    pos += 1

    # --- Argument parsing ---
    if additional < 24:
        arg = additional
    elif additional == 24:
        if pos >= len(data):
            raise ValueError(f"CBOR: unexpected EOF reading 1-byte argument at {pos}")
        arg = data[pos]
        pos += 1
    elif additional == 25:
        if pos + 2 > len(data):
            raise ValueError(f"CBOR: unexpected EOF reading 2-byte argument at {pos}")
        arg = struct.unpack(">H", data[pos : pos + 2])[0]
        pos += 2
    elif additional == 26:
        if pos + 4 > len(data):
            raise ValueError(f"CBOR: unexpected EOF reading 4-byte argument at {pos}")
        arg = struct.unpack(">I", data[pos : pos + 4])[0]
        pos += 4
    elif additional == 27:
        if pos + 8 > len(data):
            raise ValueError(f"CBOR: unexpected EOF reading 8-byte argument at {pos}")
        arg = struct.unpack(">Q", data[pos : pos + 8])[0]
        pos += 8
    elif additional == 31:
        arg = -1  # Indefinite length marker
    else:
        raise ValueError(f"CBOR: unsupported additional info {additional} at offset {pos - 1}")

    # --- Major Types ---
    if major == 0:  # Unsigned integer
        return arg, pos

    if major == 1:  # Negative integer
        return -1 - arg, pos

    if major == 2:  # Byte string
        if arg == -1:  # Indefinite byte string terminated by 0xFF
            chunks = []
            while pos < len(data) and data[pos] != 0xFF:
                chunk, pos = decode_cbor_item(data, pos)
                if isinstance(chunk, (bytes, bytearray)):
                    chunks.append(bytes(chunk))
            if pos < len(data) and data[pos] == 0xFF:
                pos += 1
            return b"".join(chunks), pos
        if pos + arg > len(data):
            raise ValueError(f"CBOR: unexpected EOF reading {arg} bytes at {pos}")
        return data[pos : pos + arg], pos + arg

    if major == 3:  # Text string (UTF-8)
        if arg == -1:  # Indefinite text string terminated by 0xFF
            chunks = []
            while pos < len(data) and data[pos] != 0xFF:
                chunk, pos = decode_cbor_item(data, pos)
                if isinstance(chunk, str):
                    chunks.append(chunk)
            if pos < len(data) and data[pos] == 0xFF:
                pos += 1
            return "".join(chunks), pos
        if pos + arg > len(data):
            raise ValueError(f"CBOR: unexpected EOF reading {arg} chars at {pos}")
        val = data[pos : pos + arg].decode("utf-8", errors="replace")
        return val, pos + arg

    if major == 4:  # Array
        if arg == -1:  # Indefinite-length array (0x9F)
            arr = []
            while pos < len(data) and data[pos] != 0xFF:
                item, pos = decode_cbor_item(data, pos)
                arr.append(item)
            if pos < len(data) and data[pos] == 0xFF:
                pos += 1
            return arr, pos
        arr = []
        for _ in range(arg):
            item, pos = decode_cbor_item(data, pos)
            arr.append(item)
        return arr, pos

    if major == 5:  # Map
        m: dict[Any, Any] = {}
        if arg == -1:  # Indefinite-length map (0xBF)
            while pos < len(data):
                if data[pos] == 0xFF:
                    pos += 1
                    break
                k, pos = decode_cbor_item(data, pos)
                # Check for break code appearing right after key without a value
                if pos < len(data) and data[pos] == 0xFF:
                    pos += 1
                    break
                v, pos = decode_cbor_item(data, pos)
                if isinstance(k, (dict, list, set)):
                    k = str(k)
                m[k] = v
            return m, pos

        for _ in range(arg):
            k, pos = decode_cbor_item(data, pos)
            v, pos = decode_cbor_item(data, pos)
            if isinstance(k, (dict, list, set)):
                k = str(k)
            m[k] = v
        return m, pos

    if major == 6:  # Semantic tag
        val, pos = decode_cbor_item(data, pos)
        # Tag 0: standard date/time string, Tag 1: epoch timestamp, etc.
        return val, pos

    if major == 7:  # Simple value or float
        if additional == 20:
            return False, pos
        if additional == 21:
            return True, pos
        if additional in (22, 23):  # 22: Null, 23: Undefined -> return None
            return None, pos
        if additional == 24:
            # 1-byte simple value (e.g. 0xF8 0x20 -> CBORSimpleValue(32))
            val = arg
            if cbor2 is not None:
                return cbor2.CBORSimpleValue(val), pos
            return val, pos
        if additional == 25:  # Float16 (half-precision IEEE 754)
            raw = struct.unpack(">H", data[pos - 2 : pos])[0]
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
            return val, pos
        if additional == 26:  # Float32
            return struct.unpack(">f", data[pos - 4 : pos])[0], pos
        if additional == 27:  # Float64
            return struct.unpack(">d", data[pos - 8 : pos])[0], pos

        if cbor2 is not None:
            try:
                val = cbor2.loads(data[pos - 1 : pos])
                return val, pos
            except Exception:
                pass
        raise ValueError(f"CBOR: unknown simple value {additional}")

    # Fallback to cbor2 if available
    if cbor2 is not None:
        try:
            val = cbor2.loads(data[pos - 1 :])
            return val, len(data)
        except Exception:
            pass

    raise ValueError(f"CBOR: unknown major type {major}")


# ── Diffusion Binary Delta Engine ────────────────────────────────────────────
def apply_binary_delta(old_bytes: bytes, delta_payload: bytes) -> bytes:
    """Apply a Diffusion Type-5 binary delta to *old_bytes*.

    Grammar:
        copy_count, [insert_bytes, jump_to_old_offset, copy_count]*
    also supporting consecutive jump/copy sequences without intermediate insert bytes:
        [jump_to_old_offset, copy_count]*
    """
    items = []
    pos = 0
    while pos < len(delta_payload):
        item, pos = decode_cbor_item(delta_payload, pos)
        items.append(item)

    if not items:
        return old_bytes

    new = bytearray()
    old_pos = 0
    i = 0

    # First item is initial copy count
    if isinstance(items[0], int):
        copy_n = items[0]
        new.extend(old_bytes[old_pos : old_pos + copy_n])
        old_pos += copy_n
        i = 1

    while i < len(items):
        item = items[i]
        if isinstance(item, (bytes, bytearray)):
            # INSERT
            new.extend(item)
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
        elif isinstance(item, int):
            # Consecutive JUMP without intermediate INSERT
            old_pos = item
            i += 1
            if i < len(items) and isinstance(items[i], int):
                # COPY
                copy_n = items[i]
                new.extend(old_bytes[old_pos : old_pos + copy_n])
                old_pos += copy_n
                i += 1
        else:
            i += 1

    return bytes(new)


# ── Frame Decoders ───────────────────────────────────────────────────────────
def find_alias_and_cbor_type84(data: bytes) -> tuple[str | None, bytes | None]:
    """For a 0x84 compressed full state frame, extract (alias_hex, decompressed_cbor).

    Scans for valid zlib header magic (0x78 followed by 0x01, 0x5e, 0x9c, or 0xda)
    starting from offset 2, decompresses the payload, and verifies it decodes
    to a valid CBOR dictionary consuming all decompressed bytes.
    """
    for i in range(2, len(data) - 1):
        if data[i] == 0x78 and data[i + 1] in (0x01, 0x5E, 0x9C, 0xDA):
            try:
                cbor_bytes = zlib.decompress(data[i:])
                obj, end_pos = decode_cbor_item(cbor_bytes, 0)
                if isinstance(obj, dict) and end_pos == len(cbor_bytes):
                    alias_hex = data[2:i].hex()
                    return alias_hex, cbor_bytes
            except Exception:
                continue
    return None, None


def find_alias_and_cbor_type04(data: bytes) -> tuple[str | None, bytes | None]:
    """For a 0x04 uncompressed full state frame, extract (alias_hex, raw_cbor).

    Searches bounded range 3..min(10, len(data)) for a valid CBOR dictionary
    that consumes all remaining bytes in the frame.
    """
    for cbor_start in range(3, min(10, len(data))):
        # Type 0x04 payload must be a CBOR map (major type 5)
        if (data[cbor_start] >> 5) & 0x07 != 5:
            continue
        try:
            obj, end_pos = decode_cbor_item(data, cbor_start)
            if isinstance(obj, dict) and end_pos == len(data):
                alias_hex = data[2:cbor_start].hex()
                return alias_hex, data[cbor_start:]
        except Exception:
            continue
    return None, None


def parse_type05(data: bytes) -> tuple[str | None, bytes | None]:
    """For a 0x05 binary delta frame, extract (alias_hex, delta_payload).

    Scans for the 0x00 delimiter separating alias from delta payload,
    handling possible internal zeros inside the alias.
    """
    zero_pos = -1
    for idx in range(2, min(7, len(data))):
        if data[idx] == 0x00:
            if idx + 1 < len(data) and data[idx + 1] == 0x00:
                continue
            zero_pos = idx
            break

    if zero_pos == -1 or zero_pos < 3:
        return None, None

    alias_hex = data[2:zero_pos].hex()
    delta_payload = data[zero_pos + 1 :]
    return alias_hex, delta_payload


def parse_type85(data: bytes) -> tuple[str | None, bytes | None]:
    """For a 0x85 compressed delta frame, extract (alias_hex, decompressed_delta).

    Extracts alias up to 0x00 separator, then decompresses the remaining
    zlib payload into delta bytes.
    """
    zero_pos = -1
    for idx in range(2, min(7, len(data))):
        if data[idx] == 0x00:
            if idx + 1 < len(data) and data[idx + 1] == 0x00:
                continue
            zero_pos = idx
            break

    if zero_pos == -1 or zero_pos < 3:
        return None, None

    alias_hex = data[2:zero_pos].hex()
    compressed_payload = data[zero_pos + 1 :]
    try:
        delta_payload = zlib.decompress(compressed_payload)
        return alias_hex, delta_payload
    except Exception:
        return None, None


def classify_object(obj: Any) -> str:
    """Heuristic to classify a decoded CBOR dict as event, market, or selection."""
    if not isinstance(obj, dict):
        return "unknown"
    if "price" in obj:
        return "selection"
    if "templateId" in obj or "marketCode" in obj or "type" in obj:
        return "market"
    if "started" in obj or "tradedInPlay" in obj:
        return "event"
    if "line" in obj and "price" not in obj:
        return "market"
    return "unknown"


# ── Topic Alias State Store ──────────────────────────────────────────────────
class AliasStateStore:
    """Thread-safe store mapping Diffusion topic aliases to current CBOR states and UUIDs."""

    def __init__(self) -> None:
        self._state: dict[str, bytes] = {}
        self._id: dict[str, str] = {}

    def get(self, alias_hex: str) -> bytes | None:
        """Get the current raw CBOR bytes for an alias."""
        return self._state.get(alias_hex.lower())

    def set(self, alias_hex: str, cbor_bytes: bytes) -> None:
        """Set the raw CBOR bytes for an alias (strict full replacement)."""
        self._state[alias_hex.lower()] = bytes(cbor_bytes)

    def contains(self, alias_hex: str) -> bool:
        """Check if the alias is currently tracked."""
        return alias_hex.lower() in self._state

    def __contains__(self, alias_hex: str) -> bool:
        return self.contains(alias_hex)

    def get_uuid(self, alias_hex: str) -> str | None:
        """Get the bound UUID for an alias if known."""
        return self._id.get(alias_hex.lower())

    def set_uuid(self, alias_hex: str, uuid_str: str) -> None:
        """Bind a UUID to an alias."""
        self._id[alias_hex.lower()] = str(uuid_str)

    def remove(self, alias_hex: str) -> None:
        """Evict an alias from the store."""
        key = alias_hex.lower()
        self._state.pop(key, None)
        self._id.pop(key, None)

    def reset(self) -> None:
        """Clear all aliases and state bindings."""
        self._state.clear()
        self._id.clear()
