"""
caesars_scraper.py – Live Caesars Sportsbook odds scraper via CDP.

Passively intercepts Diffusion WebSocket traffic from an already-running
Chrome instance using Chrome DevTools Protocol (CDP).  Decodes binary
Diffusion frames (CBOR, zlib, binary deltas) in real time and streams
enriched odds updates to both the terminal and a JSONL log file.

Usage
─────
1. Launch Chrome with a remote debugging port:
       chrome.exe --remote-debugging-port=19222
2. Navigate to the Caesars Sportsbook MLB page in that Chrome.
3. Run this script:
       python caesars_scraper.py [--port 19222]

The script will automatically:
 • Attach to the Caesars tab via CDP
 • Intercept the /v4/home REST response for enrichment data
 • Identify the primary Diffusion odds WebSocket
 • Decode and display every odds update as it arrives

Dependencies:  pip install websocket-client requests
"""

import argparse, base64, json, os, struct, sys, time, zlib
from datetime import datetime

try:
    import websocket
except ImportError:
    print("ERROR: 'websocket-client' is required.")
    print("Install it with:  pip install websocket-client")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("ERROR: 'requests' is required.")
    print("Install it with:  pip install requests")
    sys.exit(1)


# ─── paths ───────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, "caesars_live_odds.jsonl")


# ═══════════════════════════════════════════════════════════════════════════════
# REUSED DECODER FUNCTIONS — copied verbatim from analyze_caesar.py
# (validated at 100%: 551/551 messages, 131/131 deltas, 128/128 aliases)
# ═══════════════════════════════════════════════════════════════════════════════

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


# ── alias / frame helpers ────────────────────────────────────────────────────
def find_alias_and_cbor_type84(data):
    """For a 0x84 message, return (alias_hex, decompressed_cbor_bytes).

    Widened zlib magic check: 0x01 (no compression), 0x5E (fast),
    0x9C (default), 0xDA (best compression).
    """
    for i in range(2, len(data)):
        if data[i] == 0x78 and i + 1 < len(data) and data[i + 1] in (0x01, 0x5E, 0x9C, 0xDA):
            alias_hex = data[2:i].hex()
            try:
                cbor_bytes = zlib.decompress(data[i:])
                return alias_hex, cbor_bytes
            except zlib.error:
                continue
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


def parse_subscription_path(data):
    """Extract the topic path string from a 0x00 subscription message."""
    be_idx = data.find(b"BE/")
    if be_idx == -1:
        return None
    path_end = be_idx
    while path_end < len(data) and 32 <= data[path_end] < 127:
        path_end += 1
    return data[be_idx:path_end].decode("ascii")


# ═══════════════════════════════════════════════════════════════════════════════
# NEW CODE — CDP session, live interception, formatting, logging
# ═══════════════════════════════════════════════════════════════════════════════

# ── enrichment lookup (adapted for live JSON instead of file path) ────────────
def build_enrichment_lookup_from_json(json_data):
    """Build selectionId/marketId/eventId → enrichment info from /v4/home JSON.

    Accepts a parsed JSON dict (the response body), not a file path.
    Returns (selection_lookup, market_lookup, event_lookup).
    """
    home = json_data.get("data", json_data)
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


# ── live enrichment updater ──────────────────────────────────────────────────
def update_enrichment_line(market_uuid, new_line, market_lookup, selection_lookup):
    """Propagate a market's new handicap line into the enrichment lookups.

    When a market delta carries a changed 'line' value (e.g. Run Line moves
    from 1.5 to -5.5), this updates:
      1. market_lookup[market_uuid]['line']
      2. selection_lookup[sel_id]['market_line'] for every selection that
         belongs to this market

    This ensures subsequent selection price deltas display the current
    handicap, not the stale /v4/home value.
    """
    if market_uuid in market_lookup:
        old_line = market_lookup[market_uuid].get("line")
        market_lookup[market_uuid]["line"] = new_line
        # Update all child selections
        for sel_id, sel_enr in selection_lookup.items():
            if sel_enr.get("market_id") == market_uuid:
                sel_enr["market_line"] = new_line
        if old_line != new_line:
            market_name = market_lookup[market_uuid].get("name", "")
            event_name = market_lookup[market_uuid].get("event_name", "")
            print(f"{_ts()} LINE CHANGE: {event_name}")
            print(f"           {market_name}  {old_line} -> {new_line}")


# ── terminal formatter (no ANSI colors) ──────────────────────────────────────
def _ts():
    """Current local time as [HH:MM:SS]."""
    return datetime.now().strftime("[%H:%M:%S]")


def format_selection(obj, enrichment):
    """Format a selection update for terminal output."""
    event_name = enrichment.get("event_name", "")
    market_name = enrichment.get("market_name", "")
    sel_name = enrichment.get("name", obj.get("id", "?"))
    line = enrichment.get("market_line")
    price = obj.get("price", {})
    state = obj.get("state", "?")

    lines = [f"{_ts()} {event_name}"]
    line_str = f" (line: {line})" if line is not None else ""
    lines.append(f"           {market_name}{line_str}")
    price_parts = []
    if "a" in price:
        price_parts.append(f"a: {price['a']}")
    if "d" in price:
        d = price["d"]
        price_parts.append(f"d: {d:.2f}" if isinstance(d, float) else f"d: {d}")
    if "f" in price:
        price_parts.append(f"f: {price['f']}")
    price_str = "  ".join(price_parts)
    lines.append(f"           {sel_name}  {price_str}  [{state}]")
    return "\n".join(lines)


def format_market(obj, enrichment):
    """Format a market update for terminal output."""
    event_name = enrichment.get("event_name", "")
    market_name = enrichment.get("name", obj.get("id", "?"))
    line = obj.get("line", enrichment.get("line"))
    state = obj.get("state", "?")
    active = obj.get("active")

    parts = [f"{_ts()} {event_name}"]
    detail = f"           {market_name}"
    if line is not None:
        detail += f"  line: {line}"
    if active is not None:
        detail += f"  active={active}"
    detail += f"  [{state}]"
    parts.append(detail)
    return "\n".join(parts)


def format_event(obj, enrichment):
    """Format an event update for terminal output."""
    event_name = enrichment.get("name", obj.get("id", "?"))
    state = obj.get("state", "?")
    active = obj.get("active")
    started = obj.get("started")

    detail_parts = []
    if active is not None:
        detail_parts.append(f"active={active}")
    if started is not None:
        detail_parts.append(f"started={started}")
    detail_str = ", ".join(detail_parts)

    lines = [f"{_ts()} {event_name}"]
    lines.append(f"           Event state: {detail_str}  [{state}]")
    return "\n".join(lines)


# ── JSONL logger ─────────────────────────────────────────────────────────────
class JSONLLogger:
    """Append-mode JSON Lines logger."""

    def __init__(self, filepath):
        self.filepath = filepath
        self.fh = open(filepath, "a", encoding="utf-8")
        self.count = 0

    def log(self, record):
        """Write one JSON record as a single line."""
        record["ts"] = datetime.now().isoformat(timespec="milliseconds")
        self.fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        self.fh.flush()
        self.count += 1

    def close(self):
        self.fh.close()


# ── CDP session ──────────────────────────────────────────────────────────────
class CDPSession:
    """Manages the CDP WebSocket connection to a Chrome page."""

    def __init__(self, port):
        self.port = port
        self.ws = None
        self.cmd_id = 0
        self.pending = {}  # cmd_id → callback function

    def connect(self):
        """Enumerate CDP targets, find the Caesars page, connect."""
        # 1. Enumerate targets
        url = f"http://localhost:{self.port}/json"
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
        except requests.ConnectionError:
            print(f"\nERROR: Cannot connect to Chrome DevTools at {url}")
            print("Make sure Chrome is running with the remote debugging port:\n")
            print(f"    chrome.exe --remote-debugging-port={self.port}\n")
            sys.exit(1)
        except Exception as e:
            print(f"\nERROR: Failed to enumerate CDP targets: {e}")
            sys.exit(1)

        targets = resp.json()

        # 2. Find Caesars page
        page = None
        for t in targets:
            t_url = t.get("url", "").lower()
            if "caesars" in t_url and t.get("type") == "page":
                page = t
                break

        if not page:
            # Also try without type restriction
            for t in targets:
                t_url = t.get("url", "").lower()
                if "caesars" in t_url:
                    page = t
                    break

        if not page:
            print("\nERROR: No Caesars Sportsbook tab found in Chrome.")
            print("Please navigate to the Caesars MLB page, e.g.:")
            print("    https://sportsbook.caesars.com/us/az/bet/baseball/mlb\n")
            print("Available targets:")
            for t in targets:
                print(f"  [{t.get('type', '?')}] {t.get('title', '(no title)')[:60]}")
                print(f"       {t.get('url', '(no url)')[:80]}")
            sys.exit(1)

        ws_url = page.get("webSocketDebuggerUrl")
        if not ws_url:
            print("\nERROR: Target found but no webSocketDebuggerUrl available.")
            print("Another DevTools client may already be attached to this page.")
            sys.exit(1)

        print(f"Attaching to: {page.get('title', '(untitled)')}")
        print(f"  URL: {page.get('url', '?')[:100]}")
        print(f"  CDP: {ws_url}")

        # 3. Connect
        self.ws = websocket.create_connection(ws_url, timeout=None)
        print("CDP WebSocket connected.\n")

    def send_command(self, method, params=None, callback=None):
        """Send a CDP command.  If callback is provided, it will be called
        with the result when the response arrives."""
        self.cmd_id += 1
        msg = {"id": self.cmd_id, "method": method}
        if params:
            msg["params"] = params
        if callback:
            self.pending[self.cmd_id] = callback
        self.ws.send(json.dumps(msg))
        return self.cmd_id

    def recv(self):
        """Receive one CDP message (blocks)."""
        raw = self.ws.recv()
        return json.loads(raw)

    def close(self):
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass


# ── main scraper ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Caesars Sportsbook live odds scraper via CDP")
    parser.add_argument(
        "--port", type=int, default=19222,
        help="Chrome remote debugging port (default: 19222)")
    args = parser.parse_args()

    # Prevent UnicodeEncodeError on Windows cp1252 terminals when printing
    # CBOR strings that contain replacement characters (\ufffd) or other
    # unencodable Unicode.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(errors="replace")

    print("=" * 65)
    print("  Caesars Sportsbook — Live Odds Scraper (CDP)")
    print("=" * 65)
    print()

    # ── connect CDP ──────────────────────────────────────────────────────
    cdp = CDPSession(args.port)
    cdp.connect()

    # ── enable network domain ────────────────────────────────────────────
    cdp.send_command("Network.enable")
    print("Network.enable sent — intercepting traffic.\n")

    # ── open JSONL log ───────────────────────────────────────────────────
    logger = JSONLLogger(LOG_FILE)
    print(f"Logging to: {LOG_FILE}\n")

    # ── live state ───────────────────────────────────────────────────────
    alias_state = {}       # alias_hex → current CBOR bytes
    alias_id = {}          # alias_hex → UUID string
    ws_connections = {}    # CDP requestId → URL string
    odds_request_ids = set()  # requestIds of the primary Diffusion socket(s)

    selection_lookup = {}  # selectionId → enrichment dict
    market_lookup = {}     # marketId → enrichment dict
    event_lookup = {}      # eventId → enrichment dict
    enrichment_ready = False

    # counters for summary
    counts = {
        "handshake": 0, "subscription": 0, "full_state": 0,
        "delta": 0, "delta_skip": 0, "delta_fail": 0,
        "ack": 0, "sent_frames": 0, "v4home_loads": 0,
    }

    def enrich(obj_type, uuid):
        """Return enrichment dict for a given object type and UUID."""
        if obj_type == "selection" and uuid in selection_lookup:
            return selection_lookup[uuid]
        if obj_type == "market" and uuid in market_lookup:
            return market_lookup[uuid]
        if obj_type == "event" and uuid in event_lookup:
            return {"name": event_lookup[uuid]["name"]}
        return {}

    def process_frame(raw_bytes, direction="recv"):
        """Decode a single Diffusion frame and output results."""
        if len(raw_bytes) == 0:
            return

        msg_type = raw_bytes[0]
        ts_iso = datetime.now().isoformat(timespec="milliseconds")

        # ── 0x23  Handshake ──────────────────────────────────────────
        if msg_type == 0x23:
            counts["handshake"] += 1
            # New handshake = new session → clear all alias state
            alias_state.clear()
            alias_id.clear()
            print(f"{_ts()} === HANDSHAKE (new Diffusion session) ===")
            logger.log({
                "type": "handshake", "direction": direction,
                "raw_hex": raw_bytes[:32].hex() + ("..." if len(raw_bytes) > 32 else ""),
            })

        # ── 0x00  Subscription ───────────────────────────────────────
        elif msg_type == 0x00:
            counts["subscription"] += 1
            path = parse_subscription_path(raw_bytes)
            if path:
                # Determine level from path
                parts = path.split("/")
                level = "unknown"
                uuid = None
                if len(parts) == 3:
                    level = "event"
                    uuid = parts[2]
                elif len(parts) == 5 and parts[2] == "v2":
                    level = "market"
                    uuid = parts[4]
                elif len(parts) == 5:
                    level = "selection"
                    uuid = parts[4]

                # Enrich the subscription itself
                enr = {}
                if level == "selection" and uuid and uuid in selection_lookup:
                    enr = selection_lookup[uuid]
                elif level == "market" and uuid and uuid in market_lookup:
                    enr = market_lookup[uuid]
                elif level == "event" and uuid and uuid in event_lookup:
                    enr = event_lookup[uuid]

                name_hint = enr.get("event_name", enr.get("name", ""))
                print(f"{_ts()} SUB [{level}] {path}")
                if name_hint:
                    print(f"           -> {name_hint}")

                logger.log({
                    "type": "subscription", "direction": direction,
                    "level": level, "topic_path": path,
                    "enrichment": name_hint or None,
                })

        # ── 0x84  Type 4 compressed ──────────────────────────────────
        elif msg_type == 0x84:
            counts["full_state"] += 1
            alias_hex, cbor_bytes = find_alias_and_cbor_type84(raw_bytes)
            if alias_hex and cbor_bytes:
                alias_state[alias_hex] = cbor_bytes
                try:
                    obj, _ = decode_cbor_item(cbor_bytes, 0)
                except Exception:
                    obj = None

                if isinstance(obj, dict) and "id" in obj:
                    alias_id[alias_hex] = obj["id"]

                obj_type = classify_object(obj) if isinstance(obj, dict) else "unknown"
                uuid = alias_id.get(alias_hex, alias_hex)
                enrichment = enrich(obj_type, uuid)

                # Update enrichment if market has a line
                if obj_type == "market" and isinstance(obj, dict) and "line" in obj:
                    update_enrichment_line(uuid, obj["line"],
                                          market_lookup, selection_lookup)

                # Print
                if obj_type == "selection":
                    print(format_selection(obj, enrichment))
                elif obj_type == "market":
                    print(format_market(obj, enrichment))
                elif obj_type == "event":
                    print(format_event(obj, enrichment))
                else:
                    print(f"{_ts()} BIND [{obj_type}] alias={alias_hex} id={uuid}")

                logger.log({
                    "type": "full_state", "compressed": True,
                    "obj_type": obj_type, "id": uuid,
                    "alias": alias_hex, "direction": direction,
                    "decoded": make_serializable(obj) if obj else None,
                    **{k: v for k, v in enrichment.items()
                       if k in ("event_name", "market_name", "name", "market_line")},
                })

        # ── 0x04  Type 4 uncompressed ────────────────────────────────
        elif msg_type == 0x04:
            counts["full_state"] += 1
            alias_hex, cbor_bytes = find_alias_and_cbor_type04(raw_bytes)
            if alias_hex and cbor_bytes:
                alias_state[alias_hex] = cbor_bytes
                try:
                    obj, _ = decode_cbor_item(cbor_bytes, 0)
                except Exception:
                    obj = None

                if isinstance(obj, dict) and "id" in obj:
                    alias_id[alias_hex] = obj["id"]

                obj_type = classify_object(obj) if isinstance(obj, dict) else "unknown"
                uuid = alias_id.get(alias_hex, alias_hex)
                enrichment = enrich(obj_type, uuid)

                # Update enrichment if market has a line
                if obj_type == "market" and isinstance(obj, dict) and "line" in obj:
                    update_enrichment_line(uuid, obj["line"],
                                          market_lookup, selection_lookup)

                # Print
                if obj_type == "selection":
                    print(format_selection(obj, enrichment))
                elif obj_type == "market":
                    print(format_market(obj, enrichment))
                elif obj_type == "event":
                    print(format_event(obj, enrichment))
                else:
                    print(f"{_ts()} BIND [{obj_type}] alias={alias_hex} id={uuid}")

                logger.log({
                    "type": "full_state", "compressed": False,
                    "obj_type": obj_type, "id": uuid,
                    "alias": alias_hex, "direction": direction,
                    "decoded": make_serializable(obj) if obj else None,
                    **{k: v for k, v in enrichment.items()
                       if k in ("event_name", "market_name", "name", "market_line")},
                })

        # ── 0x05  Type 5 delta ───────────────────────────────────────
        elif msg_type == 0x05:
            alias_hex, delta_payload = parse_type05(raw_bytes)
            if alias_hex is None:
                counts["delta_fail"] += 1
                return

            if alias_hex not in alias_state:
                counts["delta_skip"] += 1
                print(f"{_ts()} WARN: delta for unknown alias {alias_hex} (mid-session attach — skipping)")
                logger.log({
                    "type": "delta_skipped", "alias": alias_hex,
                    "reason": "unknown_alias", "direction": direction,
                })
                return

            old_cbor = alias_state[alias_hex]
            try:
                new_cbor = apply_binary_delta(old_cbor, delta_payload)
                obj, end = decode_cbor_item(new_cbor, 0)
                if not (isinstance(obj, dict) and end == len(new_cbor)):
                    counts["delta_fail"] += 1
                    logger.log({
                        "type": "delta_failed", "alias": alias_hex,
                        "reason": "cbor_validation", "direction": direction,
                    })
                    return
            except Exception as e:
                counts["delta_fail"] += 1
                logger.log({
                    "type": "delta_failed", "alias": alias_hex,
                    "reason": str(e), "direction": direction,
                })
                return

            counts["delta"] += 1
            alias_state[alias_hex] = new_cbor  # chained state

            obj_type = classify_object(obj)
            uuid = alias_id.get(alias_hex, alias_hex)
            enrichment = enrich(obj_type, uuid)

            # Update enrichment if market has a line
            if obj_type == "market" and isinstance(obj, dict) and "line" in obj:
                update_enrichment_line(uuid, obj["line"],
                                      market_lookup, selection_lookup)

            # Print
            if obj_type == "selection":
                print(format_selection(obj, enrichment))
            elif obj_type == "market":
                print(format_market(obj, enrichment))
            elif obj_type == "event":
                print(format_event(obj, enrichment))
            else:
                print(f"{_ts()} DELTA [{obj_type}] alias={alias_hex} id={uuid}")

            logger.log({
                "type": "delta", "obj_type": obj_type, "id": uuid,
                "alias": alias_hex, "direction": direction,
                "decoded": make_serializable(obj),
                **{k: v for k, v in enrichment.items()
                   if k in ("event_name", "market_name", "name", "market_line")},
            })

        # ── 0x06  Acknowledgement (silent) ───────────────────────────
        elif msg_type == 0x06:
            counts["ack"] += 1
            # No terminal output for acks

        # ── anything else ────────────────────────────────────────────
        else:
            logger.log({
                "type": "unknown", "type_byte": f"0x{msg_type:02x}",
                "direction": direction,
                "raw_hex": raw_bytes[:64].hex(),
            })

    def handle_v4_home_body(result):
        """Callback for Network.getResponseBody — parse /v4/home JSON."""
        nonlocal selection_lookup, market_lookup, event_lookup, enrichment_ready
        body = result.get("result", {}).get("body", "")
        if not body:
            print(f"{_ts()} WARN: /v4/home response body was empty")
            return
        try:
            json_data = json.loads(body)
        except json.JSONDecodeError as e:
            print(f"{_ts()} WARN: /v4/home JSON parse failed: {e}")
            return

        selection_lookup, market_lookup, event_lookup = \
            build_enrichment_lookup_from_json(json_data)
        enrichment_ready = True
        counts["v4home_loads"] += 1
        print(f"{_ts()} === /v4/home loaded: {len(selection_lookup)} selections, "
              f"{len(market_lookup)} markets, {len(event_lookup)} events ===\n")
        logger.log({
            "type": "v4home_loaded",
            "selections": len(selection_lookup),
            "markets": len(market_lookup),
            "events": len(event_lookup),
        })

    # ── CDP event loop ───────────────────────────────────────────────────
    print("Listening for Diffusion WebSocket traffic...")
    print("(Waiting for page to load — /v4/home + WebSocket connections)\n")
    print("-" * 65)

    try:
        while True:
            try:
                msg = cdp.recv()
            except websocket.WebSocketConnectionClosedException:
                print(f"\n{_ts()} CDP connection closed (Chrome tab closed or navigated away).")
                break
            except Exception as e:
                print(f"\n{_ts()} CDP receive error: {e}")
                break

            # ── handle command responses ─────────────────────────────
            if "id" in msg and msg["id"] in cdp.pending:
                callback = cdp.pending.pop(msg["id"])
                callback(msg)
                continue

            method = msg.get("method", "")

            # ── Network.webSocketCreated ─────────────────────────────
            if method == "Network.webSocketCreated":
                params = msg.get("params", {})
                req_id = params.get("requestId", "")
                ws_url = params.get("url", "")
                ws_connections[req_id] = ws_url

                if "americanwagering.com" in ws_url and "diffusion" in ws_url:
                    odds_request_ids.add(req_id)
                    print(f"{_ts()} === Diffusion WebSocket OPENED ===")
                    print(f"           URL: {ws_url[:100]}")
                    print(f"           requestId: {req_id}\n")
                    logger.log({
                        "type": "ws_opened", "requestId": req_id,
                        "url": ws_url, "is_odds": True,
                    })
                else:
                    logger.log({
                        "type": "ws_opened", "requestId": req_id,
                        "url": ws_url, "is_odds": False,
                    })

            # ── Network.webSocketClosed ──────────────────────────────
            elif method == "Network.webSocketClosed":
                params = msg.get("params", {})
                req_id = params.get("requestId", "")
                was_odds = req_id in odds_request_ids

                if was_odds:
                    odds_request_ids.discard(req_id)
                    # Clear alias state — new connection will re-establish
                    alias_state.clear()
                    alias_id.clear()
                    print(f"\n{_ts()} === Diffusion WebSocket CLOSED (requestId: {req_id}) ===")
                    print(f"           Alias state cleared. Waiting for reconnect...\n")
                    logger.log({
                        "type": "ws_closed", "requestId": req_id,
                        "is_odds": True, "aliases_cleared": True,
                    })

                ws_connections.pop(req_id, None)

            # ── Network.webSocketFrameReceived ───────────────────────
            elif method == "Network.webSocketFrameReceived":
                params = msg.get("params", {})
                req_id = params.get("requestId", "")

                if req_id not in odds_request_ids:
                    continue  # Not the odds WebSocket — ignore

                payload_data = params.get("response", {}).get("payloadData", "")
                if not payload_data:
                    continue

                try:
                    raw = base64.b64decode(payload_data)
                except Exception:
                    # payloadData might be raw text, not base64
                    try:
                        raw = payload_data.encode("utf-8")
                    except Exception:
                        continue

                process_frame(raw, direction="recv")

            # ── Network.webSocketFrameSent ────────────────────────────
            elif method == "Network.webSocketFrameSent":
                params = msg.get("params", {})
                req_id = params.get("requestId", "")

                if req_id not in odds_request_ids:
                    continue

                counts["sent_frames"] += 1
                payload_data = params.get("response", {}).get("payloadData", "")

                # Log sent frames silently (no terminal output)
                if payload_data:
                    try:
                        raw = base64.b64decode(payload_data)
                        process_frame(raw, direction="sent")
                    except Exception:
                        logger.log({
                            "type": "sent_frame_raw", "requestId": req_id,
                            "direction": "sent",
                        })

            # ── Network.responseReceived (intercept /v4/home) ────────
            elif method == "Network.responseReceived":
                params = msg.get("params", {})
                resp_url = params.get("response", {}).get("url", "")

                if "/v4/home" in resp_url:
                    req_id = params.get("requestId", "")
                    print(f"{_ts()} Intercepted /v4/home response — fetching body...")
                    cdp.send_command(
                        "Network.getResponseBody",
                        {"requestId": req_id},
                        callback=handle_v4_home_body,
                    )

    except KeyboardInterrupt:
        print("\n")

    # ── shutdown ─────────────────────────────────────────────────────────
    print("=" * 65)
    print("  Session Summary")
    print("=" * 65)
    print(f"  Handshakes:        {counts['handshake']}")
    print(f"  Subscriptions:     {counts['subscription']}")
    print(f"  Full state:        {counts['full_state']}")
    print(f"  Deltas applied:    {counts['delta']}")
    print(f"  Deltas skipped:    {counts['delta_skip']} (unknown alias)")
    print(f"  Delta failures:    {counts['delta_fail']}")
    print(f"  Acks:              {counts['ack']}")
    print(f"  Sent frames:       {counts['sent_frames']}")
    print(f"  /v4/home loads:    {counts['v4home_loads']}")
    print(f"  Aliases tracked:   {len(alias_id)}")
    print(f"  JSONL records:     {logger.count}")
    print(f"  Log file:          {LOG_FILE}")
    print("=" * 65)

    logger.close()
    cdp.close()


if __name__ == "__main__":
    main()
