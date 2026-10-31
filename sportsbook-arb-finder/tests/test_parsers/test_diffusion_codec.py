"""Unit tests for Caesars Diffusion binary codec (diffusion_codec.py)."""

import base64
import struct
import zlib
import pytest

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


# ── CBOR Decoder Tests ───────────────────────────────────────────────────────
def test_cbor_unsigned_int():
    # Additional info < 24
    assert decode_cbor_item(bytes([0x00]), 0) == (0, 1)
    assert decode_cbor_item(bytes([0x17]), 0) == (23, 1)
    # Additional info 24 (1 byte uint)
    assert decode_cbor_item(bytes([0x18, 0x64]), 0) == (100, 2)
    # Additional info 25 (2 byte uint)
    assert decode_cbor_item(bytes([0x19, 0x01, 0x00]), 0) == (256, 3)
    # Additional info 26 (4 byte uint)
    assert decode_cbor_item(bytes([0x1A, 0x00, 0x01, 0x00, 0x00]), 0) == (65536, 5)
    # Additional info 27 (8 byte uint)
    assert decode_cbor_item(bytes([0x1B, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00]), 0) == (4294967296, 9)


def test_cbor_negative_int():
    # -1 is 0x20
    assert decode_cbor_item(bytes([0x20]), 0) == (-1, 1)
    # -100 is major 1 with arg 99 -> 0x38, 0x63
    assert decode_cbor_item(bytes([0x38, 0x63]), 0) == (-100, 2)


def test_cbor_byte_string():
    # Major 2, 4 bytes
    data = bytes([0x44, 0xDE, 0xAD, 0xBE, 0xEF])
    assert decode_cbor_item(data, 0) == (b"\xde\xad\xbe\xef", 5)


def test_cbor_text_string():
    # Major 3, "hello" (len 5) -> 0x65, "hello"
    raw = bytes([0x65]) + b"hello"
    assert decode_cbor_item(raw, 0) == ("hello", 6)


def test_cbor_array():
    # Major 4, length 2: [1, 2] -> 0x82, 0x01, 0x02
    raw = bytes([0x82, 0x01, 0x02])
    assert decode_cbor_item(raw, 0) == ([1, 2], 3)


def test_cbor_map():
    # Major 5, length 1: {"k": 10} -> 0xA1, 0x61, 0x6B, 0x0A
    raw = bytes([0xA1, 0x61, 0x6B, 0x0A])
    assert decode_cbor_item(raw, 0) == ({"k": 10}, 4)


def test_cbor_simple_and_floats():
    # False (20), True (21), None (22)
    assert decode_cbor_item(bytes([0xF4]), 0) == (False, 1)
    assert decode_cbor_item(bytes([0xF5]), 0) == (True, 1)
    assert decode_cbor_item(bytes([0xF6]), 0) == (None, 1)

    # float16 (half-precision) 1.5 -> 0xF9, 0x3E, 0x00
    assert decode_cbor_item(bytes([0xF9, 0x3E, 0x00]), 0) == (1.5, 3)

    # float32 1.5 -> 0xFA, 0x3F, 0xC0, 0x00, 0x00
    val, pos = decode_cbor_item(bytes([0xFA, 0x3F, 0xC0, 0x00, 0x00]), 0)
    assert pytest.approx(val) == 1.5
    assert pos == 5

    # float64 1.5 -> 0xFB, 0x3F, 0xF8, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
    val, pos = decode_cbor_item(bytes([0xFB, 0x3F, 0xF8, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]), 0)
    assert pytest.approx(val) == 1.5
    assert pos == 9


# ── Binary Delta Engine Tests (ws_12 -> ws_454 -> ws_508) ───────────────────
def test_apply_binary_delta_sequence():
    """Test sequential binary delta application matching exact protocol trace for alias e1fbbb.

    1. ws_12: Type 0x04 full CBOR buffer
    2. ws_454: Type 0x05 dual replacement delta applied onto ws_12 buffer -> price moves to +137 (11/8)
    3. ws_508: Type 0x05 delta applied onto ws_454 buffer -> price moves to -200 (1/2)
    """
    # 1. ws_12: Type 0x04 initial full state
    ws_12_b64 = "BBDh+7ukYmlkeCRiZDliZjc2Ny1hNTg4LTMxZDktYjI5Ny0yMTVmOWZmNDU5MjFmYWN0aXZl9WVwcmljZaNhYRiCYWT7QAJmZmZmZmZhZmUxMy8xMGVzdGF0ZWRvcGVu"
    ws_12_bytes = base64.b64decode(ws_12_b64)
    alias_hex, cbor_v1 = find_alias_and_cbor_type04(ws_12_bytes)
    assert alias_hex == "e1fbbb"

    obj_v1, end_pos_v1 = decode_cbor_item(cbor_v1, 0)
    assert end_pos_v1 == len(cbor_v1)
    assert obj_v1["id"] == "bd9bf767-a588-31d9-b297-215f9ff45921"
    assert obj_v1["price"]["a"] == 130
    assert obj_v1["price"]["f"] == "13/10"
    assert obj_v1["state"] == "open"

    # 2. ws_454: Type 0x05 delta applied onto cbor_v1
    ws_454_b64 = "BRDh+7sAGDxBiRg9BU31wo9cKPZhZmQxMS84GFAL"
    ws_454_bytes = base64.b64decode(ws_454_b64)
    delta_alias_454, delta_payload_454 = parse_type05(ws_454_bytes)
    assert delta_alias_454 == "e1fbbb"

    cbor_v2 = apply_binary_delta(cbor_v1, delta_payload_454)
    obj_v2, end_pos_v2 = decode_cbor_item(cbor_v2, 0)
    assert end_pos_v2 == len(cbor_v2)
    assert isinstance(obj_v2, dict)
    assert obj_v2["id"] == "bd9bf767-a588-31d9-b297-215f9ff45921"
    assert obj_v2["price"]["a"] == 137
    assert obj_v2["price"]["f"] == "11/8"
    assert pytest.approx(obj_v2["price"]["d"]) == 2.37
    assert obj_v2["state"] == "open"

    # 3. ws_508: Type 0x05 delta applied onto cbor_v2
    ws_508_b64 = "BRDh+7sAGDtNOMdhZPk+AGFmYzEvMhhPCw=="
    ws_508_bytes = base64.b64decode(ws_508_b64)
    delta_alias_508, delta_payload_508 = parse_type05(ws_508_bytes)
    assert delta_alias_508 == "e1fbbb"

    cbor_v3 = apply_binary_delta(cbor_v2, delta_payload_508)
    obj_v3, end_pos_v3 = decode_cbor_item(cbor_v3, 0)
    assert end_pos_v3 == len(cbor_v3)
    assert isinstance(obj_v3, dict)
    assert obj_v3["id"] == "bd9bf767-a588-31d9-b297-215f9ff45921"
    assert obj_v3["price"]["a"] == -200
    assert obj_v3["price"]["f"] == "1/2"
    assert pytest.approx(obj_v3["price"]["d"]) == 1.5
    assert obj_v3["state"] == "open"


# ── Frame Helper Tests ───────────────────────────────────────────────────────
def test_find_alias_and_cbor_type84_all_zlib_headers():
    """Test find_alias_and_cbor_type84 recognizes all 4 zlib compression headers (0x01, 0x5E, 0x9C, 0xDA)."""
    # Sample CBOR payload: {"id": "test"} -> 0xA1, 0x62, 0x69, 0x64, 0x64, 0x74, 0x65, 0x73, 0x74
    raw_cbor = bytes([0xA1, 0x62, 0x69, 0x64, 0x64, 0x74, 0x65, 0x73, 0x74])

    for level in [1, 6, 9]:
        compressed = zlib.compress(raw_cbor, level=level)
        # Header byte 0x84, sequence 0x10, alias 0xAA 0xBB 0xCC, then compressed bytes
        msg = bytes([0x84, 0x10, 0xAA, 0xBB, 0xCC]) + compressed
        alias_hex, decompressed = find_alias_and_cbor_type84(msg)
        assert alias_hex == "aabbcc"
        assert decompressed == raw_cbor


def test_find_alias_and_cbor_type04_bounded_range():
    """Hard requirement: find_alias_and_cbor_type04 MUST use bounded range 3..min(10, len(data))."""
    # Create a message where CBOR starts at offset 5 (alias is 3 bytes: indices 2, 3, 4)
    raw_cbor = bytes([0xA1, 0x62, 0x69, 0x64, 0x64, 0x74, 0x65, 0x73, 0x74])
    msg = bytes([0x04, 0x10, 0x11, 0x22, 0x33]) + raw_cbor
    alias_hex, cbor_bytes = find_alias_and_cbor_type04(msg)
    assert alias_hex == "112233"
    assert cbor_bytes == raw_cbor

    # If the CBOR start is at offset 12 (beyond min(10, len)), it must return (None, None)
    dummy_prefix = bytes([0x04, 0x10] + [0xFF] * 10)
    msg_out_of_bounds = dummy_prefix + raw_cbor
    alias_hex, cbor_bytes = find_alias_and_cbor_type04(msg_out_of_bounds)
    assert alias_hex is None
    assert cbor_bytes is None


def test_parse_type05_separator():
    """Test parse_type05 extracts alias up to first 0x00 starting at offset 2."""
    # Type 0x05, sequence 0x10, alias 0x01 0x02 0x03, separator 0x00, payload 0xAA 0xBB
    msg = bytes([0x05, 0x10, 0x01, 0x02, 0x03, 0x00, 0xAA, 0xBB])
    alias_hex, payload = parse_type05(msg)
    assert alias_hex == "010203"
    assert payload == b"\xaa\xbb"

    # Message with no 0x00 separator after offset 2 returns (None, None)
    no_sep = bytes([0x05, 0x10, 0x01, 0x02, 0x03])
    alias_hex, payload = parse_type05(no_sep)
    assert alias_hex is None
    assert payload is None


def test_classify_object():
    # Selection: has 'price'
    assert classify_object({"price": {"a": -110}}) == "selection"
    # Market: has 'templateId' or 'marketCode' or 'type'
    assert classify_object({"templateId": 123}) == "market"
    assert classify_object({"marketCode": "ML"}) == "market"
    assert classify_object({"type": "moneyline"}) == "market"
    # Event: has 'started' or 'tradedInPlay'
    assert classify_object({"started": True}) == "event"
    assert classify_object({"tradedInPlay": True}) == "event"
    # Market fallback: has 'line' without 'price'
    assert classify_object({"line": 5.5}) == "market"
    # Unknown
    assert classify_object({"foo": "bar"}) == "unknown"
    assert classify_object("not_a_dict") == "unknown"


# ── AliasStateStore Tests ────────────────────────────────────────────────────
def test_alias_state_store_replacement_semantics():
    """CRITICAL: Calling set() twice on the same alias MUST replace rather than merge or extend."""
    store = AliasStateStore()
    alias = "aabbcc"

    initial_bytes = b"\x01\x02\x03"
    store.set(alias, initial_bytes)
    assert store.get(alias) == initial_bytes
    assert store.contains(alias)
    assert alias in store

    # Second call replaces completely
    updated_bytes = b"\x04\x05"
    store.set(alias, updated_bytes)
    assert store.get(alias) == updated_bytes
    assert store.get(alias) != initial_bytes + updated_bytes


def test_alias_state_store_uuid_and_reset():
    store = AliasStateStore()
    alias = "112233"
    uuid_val = "uuid-1234-abcd"

    store.set(alias, b"\x00")
    store.set_uuid(alias, uuid_val)
    assert store.get_uuid(alias) == uuid_val

    # Reset clears everything
    store.reset()
    assert store.get(alias) is None
    assert store.get_uuid(alias) is None
    assert not store.contains(alias)


def test_apply_binary_delta_multi_jump_copy():
    """Verify deltas containing consecutive jump/copy operations without intermediate bytes (e.g. deletions)."""
    # Base buffer: 20 bytes
    old_buf = b"0123456789ABCDEFGHIJ"
    # Delta: copy 5, insert b'XYZ', jump to 8, copy 2, jump to 15, copy 3
    # items: [5, b'XYZ', 8, 2, 15, 3]
    # Expected result: old[0:5] ('01234') + b'XYZ' + old[8:10] ('89') + old[15:18] ('FGH')
    # = b'01234XYZ89FGH'
    from arbfinder.parsers.diffusion_codec import apply_binary_delta
    import cbor2
    # Encode items as CBOR stream
    payload = bytearray()
    for it in [5, b"XYZ", 8, 2, 15, 3]:
        payload.extend(cbor2.dumps(it))

    new_buf = apply_binary_delta(old_buf, bytes(payload))
    assert new_buf == b"01234XYZ89FGH"


def test_cbor_semantic_tag_and_undefined():
    # Major type 6: Tag 0 (standard datetime string) wrapping text string "2026-10-01T00:00:00Z"
    # Tag 0 is 0xC0
    import cbor2
    tagged_bytes = cbor2.dumps(cbor2.CBORTag(0, "2026-10-01T00:00:00Z"))
    val, pos = decode_cbor_item(tagged_bytes, 0)
    assert val == "2026-10-01T00:00:00Z"
    assert pos == len(tagged_bytes)

    # Major type 7: simple value 23 (undefined) -> returns None
    assert decode_cbor_item(bytes([0xF7]), 0) == (None, 1)


def test_find_alias_and_cbor_type84_validation():
    # Valid compressed CBOR dict
    import cbor2
    cbor_data = cbor2.dumps({"id": "market-1", "line": 6.5})
    compressed = zlib.compress(cbor_data)
    # 0x84 frame with 2-byte alias b'\x8d\x7c'
    frame = b"\x84\x00\x8d\x7c" + compressed
    alias, decoded = find_alias_and_cbor_type84(frame)
    assert alias == "8d7c"
    assert decoded == cbor_data

    # Frame with zlib header that decompresses into non-CBOR garbage
    bad_compressed = zlib.compress(b"not valid cbor at all!")
    bad_frame = b"\x84\x00\x8d\x7c" + bad_compressed
    bad_alias, bad_decoded = find_alias_and_cbor_type84(bad_frame)
    assert bad_alias is None
    assert bad_decoded is None


def test_parse_type85():
    # 0x85 compressed delta
    delta_bytes = b"\x18\x64\x43XYZ"
    compressed_delta = zlib.compress(delta_bytes)
    frame = b"\x85\x00\x8d\x7c\x00" + compressed_delta
    alias, payload = parse_type85(frame)
    assert alias == "8d7c"
    assert payload == delta_bytes


def test_cbor_indefinite_length_handling():
    # 0xBF is indefinite-length map, terminated by 0xFF
    # e.g., 0xBF, 0x62, 'i', 'd', 0x01, 0xFF -> {"id": 1}
    indef_map = bytes([0xBF, 0x62, ord('i'), ord('d'), 0x01, 0xFF])
    obj, pos = decode_cbor_item(indef_map, 0)
    assert obj == {"id": 1}
    assert pos == len(indef_map)

    # 0x9F is indefinite-length array: 0x9F, 0x01, 0x02, 0xFF -> [1, 2]
    indef_arr = bytes([0x9F, 0x01, 0x02, 0xFF])
    arr, pos = decode_cbor_item(indef_arr, 0)
    assert arr == [1, 2]
    assert pos == len(indef_arr)


def test_cbor_unhashable_map_key_handled():
    # Construct a CBOR map where key is a dict: 0xA1, 0xA1, 0x61, 'a', 0x01, 0x02
    # which is {{"a": 1}: 2}
    map_with_dict_key = bytes([0xA1, 0xA1, 0x61, ord('a'), 0x01, 0x02])
    obj, pos = decode_cbor_item(map_with_dict_key, 0)
    assert isinstance(obj, dict)
    assert "{'a': 1}" in obj
    assert obj["{'a': 1}"] == 2


def test_find_alias_and_cbor_type04_requires_map():
    # Create a message where byte 4 looks like a tag (0xdf) or int, but the actual map starts at offset 5
    raw_cbor = bytes([0xA1, 0x62, 0x69, 0x64, 0x01])  # {"id": 1}
    # Alias is 3 bytes: fa 70 df
    msg = bytes([0x04, 0x00, 0xFA, 0x70, 0xDF]) + raw_cbor
    alias, cbor_bytes = find_alias_and_cbor_type04(msg)
    assert alias == "fa70df"
    assert cbor_bytes == raw_cbor


def test_parse_type05_with_internal_zero():
    # Alias with internal zero: 8e a7 00, delimiter at index 5: 00
    msg = bytes([0x05, 0x00, 0x8E, 0xA7, 0x00, 0x00, 0x18, 0x2A])
    alias, payload = parse_type05(msg)
    assert alias == "8ea700"
    assert payload == bytes([0x18, 0x2A])


def test_alias_state_store_remove():
    store = AliasStateStore()
    store.set("8ea710", b"test")
    store.set_uuid("8ea710", "uuid-123")
    assert store.contains("8ea710")
    assert store.get_uuid("8ea710") == "uuid-123"

    store.remove("8ea710")
    assert not store.contains("8ea710")
    assert store.get("8ea710") is None
    assert store.get_uuid("8ea710") is None


def test_cbor_indefinite_map_break_code_before_value():
    """Verify indefinite-length map terminates cleanly when 0xFF break code follows key without value."""
    # 0xBF, text 'a', int 1, text 'b', 0xFF -> {'a': 1}
    raw = bytes([0xBF, 0x61, ord('a'), 0x01, 0x61, ord('b'), 0xFF])
    obj, pos = decode_cbor_item(raw, 0)
    assert obj == {"a": 1}
    assert pos == len(raw)


def test_cbor_nested_indefinite_map_with_break_code():
    """Exact reproduction test for live Caesars alias crash: nested indefinite map with trailing 0xFF."""
    # Outer indef map (0xBF), key "foo", inner indef map (0xBF), key "bar", break (0xFF), outer break (0xFF)
    payload = b"\xbf\x63foo\xbf\x63bar\xff\xff"
    obj, pos = decode_cbor_item(payload, 0)
    assert obj == {"foo": {}}
    assert pos == len(payload)


def test_cbor_fallback_to_cbor2_complex_structure():
    """Verify cbor2 fallback handles complex CBOR types (e.g. 1-byte simple values) transparently."""
    import cbor2
    # Simple value 32 (major 7, additional 24, next byte 32): 0xF8, 0x20
    cbor_bytes = bytes([0xF8, 0x20])
    decoded, pos = decode_cbor_item(cbor_bytes, 0)
    assert decoded == cbor2.CBORSimpleValue(32)
    assert pos == len(cbor_bytes)



