# Decoder Handoff: `analyze_caesar.py`

## What it does

`analyze_caesar.py` is a batch decoder for captured Caesars Sportsbook Diffusion
WebSocket traffic. It reads static log files from disk, decodes every message,
and writes a single JSON file.

### Inputs
- **`caesars_full_logs/ws_*.txt`** — One file per WebSocket frame, base64-encoded.
  Files are numbered `ws_1.txt` through `ws_551.txt`; the numeric suffix is the
  chronological ordering key.
- **`caesars_full_logs/json_5.json`** — The `/v4/home` REST snapshot containing
  event names, market names, selection names, handicap lines, and initial prices
  for all active selections.

### Output
- **`decoded_odds.json`** — A JSON array of 551 records (one per `ws_*.txt`
  file), sorted by `ws_file` number. Every record has a `message_type` field
  (`handshake`, `subscription`, `full_state`, `delta`, `ack`).

### Decoding pipeline

1. **Read & classify** — Decode base64, inspect `data[0]` (type byte):
   - `0x23` → handshake (raw hex preserved)
   - `0x00` → subscription (ASCII topic path parsed into event/market/selection UUIDs)
   - `0x04` → Type 4 uncompressed full state (alias + raw CBOR)
   - `0x84` → Type 4 compressed full state (alias + zlib → CBOR)
   - `0x05` → Type 5 binary delta (alias + delta payload applied to current state)
   - `0x06` → acknowledgement (alias reference extracted)

2. **Alias state tracking** — A dict `alias_state[alias_hex] → current_cbor_bytes`
   is updated on every Type 4 (reset) and Type 5 (delta applied). Deltas are
   chained: each delta's output becomes the base for the next delta on that alias.

3. **Alias → UUID resolution** — Each CBOR object contains an `id` field with
   its UUID string. No external mapping is needed. The script reads the `id`
   directly from the decoded CBOR dict.

4. **Object classification** — Heuristic based on field presence:
   - Has `price` → selection
   - Has `templateId` / `marketCode` / `type` → market
   - Has `started`, or has `tradedInPlay` without selection/market indicators → event

5. **Enrichment** — The UUID is looked up in a dict built from `json_5.json`:
   - Selections get `name`, `market_name`, `event_name`, `line` (if applicable)
   - Markets get `event_name`, `line`
   - Events get `event_name`
   - Subscriptions are also enriched with the same lookups using the UUIDs
     parsed from their topic paths.

### CBOR decoder
A from-scratch CBOR decoder (`decode_cbor_item`) handles major types 0–5 and 7,
including float16/32/64. It does NOT handle indefinite-length items, tags
(major 6), or break codes — none were observed in the corpus.

### Binary delta applicator
`apply_binary_delta(old_bytes, delta_payload)` parses the delta payload as a
flat sequence of CBOR items with grammar:
```
copy_count:int, [insert:bytes, jump_to_offset:int, copy_count:int]*
```
Copy/insert operates on raw serialized CBOR bytes. The jump value is an
absolute offset into the old buffer (not relative).

---

## Validated accuracy

| Metric | Result |
|--------|--------|
| Total messages decoded | 551 / 551 (100%) |
| Type 5 deltas applied successfully | 131 / 131 (100%, 0 failures) |
| Alias → UUID resolution | 128 / 128 (100%, 0 unmapped) |
| UUID → `/v4/home` enrichment | 128 / 128 (100%, 0 unmapped) |
| Unknown/unclassified message types | 0 |

### Hand-verified examples
| ws_file | Type | ID | Verified field | Expected | Actual |
|---------|------|----|---------------|----------|--------|
| ws_508 | selection | bd9bf767 | price.a | -200 | -200 ✓ |
| ws_454 | selection | bd9bf767 | price.a, state | 137, "open" | 137, "open" ✓ |
| ws_395 | market | fa50d853 | line | 6.5 | 6.5 ✓ |
| ws_398 | event | 8e767a58 | active | false | false ✓ |

### Special cases / edge behaviors
- **Alias boundary detection for `0x04`**: brute-force CBOR-validation scan at
  offsets 3–9. Works for all 78 uncompressed Type 4 messages in the corpus
  (alias always landed at 3 bytes = offset 5), but this is a search, not a
  hardcoded offset.
- **Alias boundary detection for `0x84`**: scans for zlib magic `0x78 0x01`.
  Works for all 50 compressed Type 4 messages. If Diffusion ever uses a
  different zlib compression level, the magic byte would be `0x78 0x9C` or
  `0x78 0x5E` instead of `0x78 0x01` — the current code only checks for `0x01`.
- **No failures or unhandled patterns** in the captured corpus.

---

## Key assumptions baked into the code

These are things that work for batch replay of static logs but may not hold live:

1. **Single pass, pre-ordered input.** The script sorts `ws_*.txt` by numeric
   suffix and processes them once. It assumes the file numbering faithfully
   represents chronological order. A live scraper receives frames in real time
   and doesn't need sorting, but must handle out-of-order or dropped frames.

2. **All aliases are established before deltas arrive.** In the captured logs,
   every Type 5 delta references an alias that was already bound by a Type 4
   message earlier in the sequence. The code skips (and counts as failure) any
   delta whose alias isn't yet in `alias_state`. A live scraper could see a
   delta before its alias binding if it attaches to the WebSocket mid-session.

3. **Aliases are 3 bytes.** Confirmed at 128/128 in this corpus. The code does
   not hardcode this — it searches for the boundary — but the boundary detection
   heuristics (zlib magic scan, CBOR validation from offset 3) effectively
   assume aliases are small (< 8 bytes).

4. **Only one Diffusion WebSocket matters.** The code processes frames from a
   single WebSocket connection (the primary odds stream). Caesars opens 4
   WebSocket connections (odds, livescores, cashout, microbetting); the captured
   logs only contain traffic from the odds socket.

5. **`/v4/home` is loaded once, statically.** The enrichment lookup is built
   from `json_5.json` at startup and never refreshed. In a live session,
   `/v4/home` changes as markets open/close and new events start.

6. **Handles multiple events concurrently.** The code is NOT single-event — it
   successfully tracks aliases for 12 events, 38 markets, and 78 selections
   simultaneously. The alias state map is keyed by alias hex, not by event.

7. **Zlib magic check only looks for `0x01`.** The `find_alias_and_cbor_type84`
   function checks `data[i+1] in (0x01,)`. Other valid zlib header bytes
   (`0x9C`, `0x5E`, `0xDA`) are not checked, which could cause missed
   decompression on different Diffusion server configurations.

8. **Object classification is heuristic.** There is no explicit type field in
   the CBOR objects. The classifier checks for `price` (selection), `templateId`
   (market), `started` (event). If Caesars adds new fields or restructures
   objects, the heuristic could misclassify.

---

## Explicitly out of scope

These were not part of the original task (decoding captured logs) and do not
exist in the current codebase:

- **Live WebSocket connection handling** — no socket management, no reconnects.
- **CDP / browser integration** — no Chrome DevTools Protocol interaction.
- **Real-time output** — writes one batch JSON file at the end, not streaming.
- **Mid-session attach** — assumes the capture starts from the handshake; no
  recovery if aliases were established before capture began.
- **Multiple concurrent WebSocket connections** — processes one stream only.
- **`/v4/home` refresh** — snapshot is loaded once at startup.
- **Error recovery** — delta failures are silently skipped and counted.
- **Odds comparison / alerting / arbitrage detection** — decodes only.

---

## Suggestions for the live scraper phase

> These are recommendations, not confirmed implementation details.

1. **Intercept `/v4/home` via CDP** rather than a separate HTTP call. The
   browser already fetches it; capture it from `Network.responseReceived` to
   stay fully passive.

2. **Handle mid-session attach** by treating the first Type 4 message for each
   alias as the initial state, even if the subscription was missed. The CBOR
   object is self-contained.

3. **Widen the zlib magic check** to include `0x9C` (default compression) and
   `0x5E` (fast compression) in addition to `0x01` (no compression).

4. **Consider reconnect scenarios.** If the Diffusion WebSocket disconnects and
   reconnects, alias assignments may reset. The scraper should detect the new
   handshake (`0x23`) and clear the alias state map.

5. **Print enriched updates immediately** rather than buffering. Each Type 5
   delta should produce a terminal line as soon as it's decoded. Full-state
   Type 4 messages could also be printed (they represent the initial odds for a
   newly subscribed selection).

6. **The `websocket-client` library** (`pip install websocket-client`) is
   sufficient for connecting to the CDP debugger WebSocket. No browser
   automation framework (Selenium, Playwright) is needed since the script only
   listens, never controls.
