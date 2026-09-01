"""
analyze_caesar.py – Decode Caesars Sportsbook Diffusion protocol WebSocket
captures and produce a single, chronologically-ordered JSON file of enriched
live odds updates.

Input:  caesars_workspace/caesars_full_logs/ws_*.txt   (base64 Diffusion frames)
        caesars_workspace/caesars_full_logs/json_5.json (/v4/home snapshot)
Output: caesars_workspace/decoded_odds.json

Protocol summary
────────────────
Diffusion frames (decoded from base64) carry a type byte at d[0]:
  0x00 – Subscription: human-readable topic path with event/market/selection UUIDs.
  0x04 – Type 4 (uncompressed): binds a 3-byte topic alias to a full CBOR object.
  0x84 – Type 4 (compressed): same, but CBOR payload is zlib-compressed.
  0x05 – Type 5: binary delta against the current CBOR state of an alias.

Aliases are always 3 bytes.  Alias boundaries for 0x84 are found by scanning
for the zlib magic byte (0x78); for 0x04, by brute-force CBOR validation.

The delta grammar (Type 5) is:
    copy_count, [insert_bytes, jump_to_old_offset, copy_count]*
"""

import base64, json, os, struct, sys, zlib

# ── paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# LOG_DIR = os.path.join(SCRIPT_DIR, "caesars_full_logs")
# HOME_JSON = os.path.join(LOG_DIR, "json_5.json")
LOG_DIR = "C:\\Users\\fiona\\Desktop\\arbitrage_tool\\sportsbook-arb-finder\\scripts\\data2\\caesars\\messages"
HOME_JSON = os.path.join(LOG_DIR, "json_8.json")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "decoded_odds.json")


# ── CBOR decoder ─────────────────────────────────────────────────────────────
def decode_cbor_item(data, pos):
    """Decode one CBOR data item starting at *pos*.  Returns (value, new_pos)."""
    if pos >= len(data):
        raise ValueError(f"CBOR: unexpected EOF at offset {pos}")
    initial = data[pos]
    major = (initial >> 5) & 0x07
    additional = initial & 0x1F
    pos += 1

    # --- argument ---
    if additional < 24:
        arg = additional
    elif additional == 24:
        arg = data[pos]; pos += 1
    elif additional == 25:
        arg = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
    elif additional == 26:
        arg = struct.unpack(">I", data[pos:pos + 4])[0]; pos += 4
    elif additional == 27:
        arg = struct.unpack(">Q", data[pos:pos + 8])[0]; pos += 8
    else:
        raise ValueError(f"CBOR: unsupported additional info {additional}")

    # --- major types ---
    if major == 0:                       # unsigned int
        return arg, pos
    if major == 1:                       # negative int
        return -1 - arg, pos
    if major == 2:                       # byte string
        return data[pos:pos + arg], pos + arg
    if major == 3:                       # text string
        return data[pos:pos + arg].decode("utf-8", errors="replace"), pos + arg
    if major == 4:                       # array
        arr = []
        for _ in range(arg):
            item, pos = decode_cbor_item(data, pos)
            arr.append(item)
        return arr, pos
    if major == 5:                       # map
        m = {}
        for _ in range(arg):
            k, pos = decode_cbor_item(data, pos)
            v, pos = decode_cbor_item(data, pos)
            m[k] = v
        return m, pos
    if major == 7:                       # simple / float
        if additional == 20:
            return False, pos
        if additional == 21:
            return True, pos
        if additional == 22:
            return None, pos
        if additional == 25:             # float16
            raw = struct.unpack(">H", data[pos - 2:pos])[0]
            sign = (raw >> 15) & 1
            exp  = (raw >> 10) & 0x1F
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
        if additional == 26:             # float32
            return struct.unpack(">f", data[pos - 4:pos])[0], pos
        if additional == 27:             # float64
            return struct.unpack(">d", data[pos - 8:pos])[0], pos
        raise ValueError(f"CBOR: unknown simple value {additional}")
    raise ValueError(f"CBOR: unknown major type {major}")


# ── Diffusion binary delta ───────────────────────────────────────────────────
def apply_binary_delta(old_bytes, delta_payload):
    """Apply a Diffusion Type-5 binary delta to *old_bytes*.

    The delta payload is a flat sequence of CBOR items with grammar:
        copy_count, [insert_bytes, jump_to_old_offset, copy_count]*

    * copy_count (int)     – copy N bytes from old buffer at current old_pos
    * insert_bytes (bytes) – literal bytes to splice into the output
    * jump_to_old_offset (int) – set old_pos to this absolute offset
    * copy_count (int)     – copy N more bytes from old buffer at new old_pos
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
    i = 0

    # First item is always a copy count
    copy_n = items[0]
    new.extend(old_bytes[old_pos:old_pos + copy_n])
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
                    new.extend(old_bytes[old_pos:old_pos + copy_n])
                    old_pos += copy_n
                    i += 1
        else:
            # Unexpected int – skip gracefully
            i += 1

    return bytes(new)


# ── helpers ──────────────────────────────────────────────────────────────────
def read_ws(filepath):
    """Read a ws_*.txt file and return the raw decoded bytes."""
    with open(filepath, "r") as f:
        return base64.b64decode(f.read().strip())


def find_alias_and_cbor_type84(data):
    """For a 0x84 message, return (alias_hex, decompressed_cbor_bytes)."""
    for i in range(2, len(data)):
        if data[i] == 0x78 and i + 1 < len(data) and data[i + 1] in (0x01,):
            alias_hex = data[2:i].hex()
            cbor_bytes = zlib.decompress(data[i:])
            return alias_hex, cbor_bytes
    return None, None


def find_alias_and_cbor_type04(data):
    """For a 0x04 message, return (alias_hex, raw_cbor_bytes)."""
    for cbor_start in range(3, min(10, len(data))):
        try:
            obj, end_pos = decode_cbor_item(data, cbor_start)
            if isinstance(obj, dict) and end_pos == len(data):
                alias_hex = data[2:cbor_start].hex()
                return alias_hex, data[cbor_start:]
        except Exception:
            continue
    return None, None


def parse_type05(data):
    """For a 0x05 message, return (alias_hex, delta_payload_bytes)."""
    try:
        zero_pos = data.index(0x00, 2)
    except ValueError:
        return None, None
    alias_hex = data[2:zero_pos].hex()
    delta_payload = data[zero_pos + 1:]
    return alias_hex, delta_payload


def classify_object(obj):
    """Heuristic: is this decoded CBOR dict an event, market, or selection?"""
    if "price" in obj:
        return "selection"
    if "templateId" in obj or "marketCode" in obj or "type" in obj:
        return "market"
    if "started" in obj or ("tradedInPlay" in obj and "price" not in obj and "templateId" not in obj):
        return "event"
    # Fallback: if it has 'line' but no 'price', it's probably a market
    if "line" in obj and "price" not in obj:
        return "market"
    return "unknown"


def make_serializable(obj):
    """Recursively convert bytes to hex strings for JSON serialization."""
    if isinstance(obj, bytes):
        return obj.hex()
    if isinstance(obj, dict):
        return {make_serializable(k): make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [make_serializable(v) for v in obj]
    return obj


# ── build /v4/home enrichment lookup ─────────────────────────────────────────
def build_enrichment_lookup(home_json_path):
    """Build selectionId/marketId/eventId → enrichment info from json_5.json."""
    with open(home_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    home = data["data"]
    selection_lookup = {}
    market_lookup = {}
    event_lookup = {}

    for edg in home.get("eventDisplayGroups", []):
        for event in edg.get("events", []):
            event_id = event.get("id")
            event_name = event.get("name", "")
            event_lookup[event_id] = {"name": event_name}

            for group in event.get("keyMarketGroups", []):
                if not isinstance(group, dict):
                    continue
                for market in group.get("markets", []):
                    market_id = market.get("id")
                    market_name = market.get("name", "")
                    market_line = market.get("line", None)
                    market_lookup[market_id] = {
                        "name": market_name,
                        "line": market_line,
                        "event_id": event_id,
                        "event_name": event_name,
                    }

                    for sel in market.get("selections", []):
                        sel_id = sel.get("id")
                        sel_name = sel.get("name", "")
                        selection_lookup[sel_id] = {
                            "name": sel_name,
                            "market_name": market_name,
                            "market_line": market_line,
                            "event_name": event_name,
                            "event_id": event_id,
                            "market_id": market_id,
                        }

    return selection_lookup, market_lookup, event_lookup


# ── build alias → UUID hierarchy from subscription paths ─────────────────────
def parse_subscription_path(data):
    """Extract the topic path string from a 0x00 subscription message."""
    be_idx = data.find(b"BE/")
    if be_idx == -1:
        return None
    path_end = be_idx
    while path_end < len(data) and 32 <= data[path_end] < 127:
        path_end += 1
    return data[be_idx:path_end].decode("ascii")


# ── parse 0x06 ack messages ──────────────────────────────────────────────────
def parse_type06(data):
    """Parse a 0x06 topic-alias acknowledgement message.

    2-byte form: 06 XX        – acknowledge alias XX (single-byte alias ref)
    3-byte form: 06 XX XX 01  – acknowledge alias XXXX with confirmation flag
    """
    if len(data) == 2:
        return {"alias_ref": f"0x{data[1]:02x}"}
    if len(data) == 3:
        return {"alias_ref": f"0x{data[1]:02x}{data[2]:02x}"}
    return {"raw": data[1:].hex()}


def parse_subscription_message(data):
    """Parse a 0x00 subscription message into structured fields."""
    path = parse_subscription_path(data)
    if not path:
        return {"raw": data[1:].hex()}

    parts = path.split("/")
    info = {"topic_path": path}

    if len(parts) == 3:
        # BE/wh-ca-on/{eventId}
        info["level"] = "event"
        info["event_id"] = parts[2]
    elif len(parts) == 5 and parts[2] == "v2":
        # BE/wh-ca-on/v2/{eventId}/{marketId}
        info["level"] = "market"
        info["event_id"] = parts[3]
        info["market_id"] = parts[4]
    elif len(parts) == 5 and parts[2] != "v2":
        # BE/wh-ca-on/{eventId}/{marketId}/{selectionId}
        info["level"] = "selection"
        info["event_id"] = parts[2]
        info["market_id"] = parts[3]
        info["selection_id"] = parts[4]
    else:
        info["level"] = "unknown"

    return info


def enrich_record(record, obj_type, uuid,
                  selection_lookup, market_lookup, event_lookup):
    """Add enrichment fields from /v4/home to a record in-place."""
    if obj_type == "selection" and uuid in selection_lookup:
        enrich = selection_lookup[uuid]
        record["name"] = enrich["name"]
        record["market_name"] = enrich["market_name"]
        record["event_name"] = enrich["event_name"]
        if enrich["market_line"] is not None:
            record["line"] = enrich["market_line"]
    elif obj_type == "market" and uuid in market_lookup:
        enrich = market_lookup[uuid]
        record["event_name"] = enrich["event_name"]
        if enrich["line"] is not None:
            record["line"] = enrich["line"]
    elif obj_type == "event" and uuid in event_lookup:
        record["event_name"] = event_lookup[uuid]["name"]


# ── main pipeline ────────────────────────────────────────────────────────────
def main():
    print("Loading /v4/home enrichment data from json_5.json ...")
    selection_lookup, market_lookup, event_lookup = build_enrichment_lookup(HOME_JSON)
    print(f"  {len(selection_lookup)} selections, {len(market_lookup)} markets, "
          f"{len(event_lookup)} events")

    # Discover all ws_N.txt files and sort by N
    ws_files = []
    for fname in os.listdir(LOG_DIR):
        if fname.startswith("ws_") and fname.endswith(".txt"):
            n = int(fname[3:-4])
            ws_files.append((n, os.path.join(LOG_DIR, fname)))
    ws_files.sort()
    print(f"Found {len(ws_files)} WebSocket capture files.")

    # Process every message in chronological order
    alias_state = {}   # alias_hex -> current CBOR bytes (updated by Type 4 & 5)
    alias_id = {}      # alias_hex -> UUID string (from CBOR 'id' field)
    output_records = []
    counts = {"handshake": 0, "subscription": 0, "full_state": 0,
              "delta": 0, "ack": 0, "other": 0, "delta_fail": 0}

    for n, fpath in ws_files:
        data = read_ws(fpath)
        if len(data) == 0:
            continue

        msg_type = data[0]

        # ── 0x23  Connection handshake ───────────────────────────────────
        if msg_type == 0x23:
            counts["handshake"] += 1
            output_records.append({
                "ws_file": n,
                "message_type": "handshake",
                "message_type_byte": "0x23",
                "raw_hex": data.hex(),
            })

        # ── 0x00  Subscription ───────────────────────────────────────────
        elif msg_type == 0x00:
            counts["subscription"] += 1
            sub_info = parse_subscription_message(data)
            record = {
                "ws_file": n,
                "message_type": "subscription",
                "message_type_byte": "0x00",
                "decoded": sub_info,
            }
            # Enrich subscription records with names from /v4/home
            level = sub_info.get("level")
            if level == "selection" and sub_info.get("selection_id") in selection_lookup:
                sel = selection_lookup[sub_info["selection_id"]]
                record["name"] = sel["name"]
                record["market_name"] = sel["market_name"]
                record["event_name"] = sel["event_name"]
            elif level == "market" and sub_info.get("market_id") in market_lookup:
                mkt = market_lookup[sub_info["market_id"]]
                record["event_name"] = mkt["event_name"]
                record["market_name"] = mkt["name"]
            elif level == "event" and sub_info.get("event_id") in event_lookup:
                record["event_name"] = event_lookup[sub_info["event_id"]]["name"]
            output_records.append(record)

        # ── 0x84  Type 4 compressed (full state) ─────────────────────────
        elif msg_type == 0x84:
            counts["full_state"] += 1
            alias_hex, cbor_bytes = find_alias_and_cbor_type84(data)
            if alias_hex and cbor_bytes:
                alias_state[alias_hex] = cbor_bytes
                obj = None
                try:
                    obj, _ = decode_cbor_item(cbor_bytes, 0)
                    if isinstance(obj, dict) and "id" in obj:
                        alias_id[alias_hex] = obj["id"]
                except Exception:
                    pass

                obj_type = classify_object(obj) if isinstance(obj, dict) else "unknown"
                uuid = alias_id.get(alias_hex, alias_hex)
                record = {
                    "ws_file": n,
                    "message_type": "full_state",
                    "message_type_byte": "0x84",
                    "alias": alias_hex,
                    "type": obj_type,
                    "id": uuid,
                    "decoded": make_serializable(obj) if obj else None,
                    "compressed": True,
                }
                enrich_record(record, obj_type, uuid,
                              selection_lookup, market_lookup, event_lookup)
                output_records.append(record)

        # ── 0x04  Type 4 uncompressed (full state) ───────────────────────
        elif msg_type == 0x04:
            counts["full_state"] += 1
            alias_hex, cbor_bytes = find_alias_and_cbor_type04(data)
            if alias_hex and cbor_bytes:
                alias_state[alias_hex] = cbor_bytes
                obj = None
                try:
                    obj, _ = decode_cbor_item(cbor_bytes, 0)
                    if isinstance(obj, dict) and "id" in obj:
                        alias_id[alias_hex] = obj["id"]
                except Exception:
                    pass

                obj_type = classify_object(obj) if isinstance(obj, dict) else "unknown"
                uuid = alias_id.get(alias_hex, alias_hex)
                record = {
                    "ws_file": n,
                    "message_type": "full_state",
                    "message_type_byte": "0x04",
                    "alias": alias_hex,
                    "type": obj_type,
                    "id": uuid,
                    "decoded": make_serializable(obj) if obj else None,
                    "compressed": False,
                }
                enrich_record(record, obj_type, uuid,
                              selection_lookup, market_lookup, event_lookup)
                output_records.append(record)

        # ── 0x05  Type 5 delta ───────────────────────────────────────────
        elif msg_type == 0x05:
            alias_hex, delta_payload = parse_type05(data)
            if alias_hex is None or alias_hex not in alias_state:
                counts["delta_fail"] += 1
                continue

            old_cbor = alias_state[alias_hex]
            try:
                new_cbor = apply_binary_delta(old_cbor, delta_payload)
                obj, end = decode_cbor_item(new_cbor, 0)
                if not (isinstance(obj, dict) and end == len(new_cbor)):
                    counts["delta_fail"] += 1
                    continue
            except Exception:
                counts["delta_fail"] += 1
                continue

            counts["delta"] += 1
            alias_state[alias_hex] = new_cbor  # update state for chained deltas

            obj_type = classify_object(obj)
            uuid = alias_id.get(alias_hex, alias_hex)
            record = {
                "ws_file": n,
                "message_type": "delta",
                "message_type_byte": "0x05",
                "alias": alias_hex,
                "type": obj_type,
                "id": uuid,
                "decoded": make_serializable(obj),
            }
            enrich_record(record, obj_type, uuid,
                          selection_lookup, market_lookup, event_lookup)
            output_records.append(record)

        # ── 0x06  Topic alias acknowledgement ────────────────────────────
        elif msg_type == 0x06:
            counts["ack"] += 1
            output_records.append({
                "ws_file": n,
                "message_type": "ack",
                "message_type_byte": "0x06",
                "decoded": parse_type06(data),
            })

        # ── anything else ────────────────────────────────────────────────
        else:
            counts["other"] += 1
            output_records.append({
                "ws_file": n,
                "message_type": "unknown",
                "message_type_byte": f"0x{msg_type:02x}",
                "raw_hex": data.hex(),
            })

    # Records are already in chronological order (ws_files sorted by N)
    print(f"\nMessage counts:")
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")
    print(f"Total decoded records: {len(output_records)}")

    # Write output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_records, f, indent=2, ensure_ascii=False)
    print(f"Output written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
