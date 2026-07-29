# Handoff: Caesars Sportsbook Diffusion Decoder (`analyze_caesar.py`)

## Objective
Build `analyze_caesar.py`: a script that reads raw WebSocket captures (`ws_*.txt`,
base64-encoded Diffusion protocol frames) and HTTP snapshot files (`json_*.json`,
including the `/v4/home` blob) from `caesars_workspace/caesars_full_logs`, decodes
the binary CBOR-based Diffusion messages byte-by-byte (no regex), resolves topic
aliases back to true Selection UUIDs, enriches each decoded odds update with
`name`, `market_name`, and handicap/line from the JSON snapshots, and writes a
single chronologically-ordered JSON file of enriched odds updates (ordered by
`ws_N` file index).

## Protocol background (see `caesars.md`)
- Caesars streams live odds over a proprietary binary WebSocket protocol called
  Diffusion (from DiffusionData).
- `/v4/home` is a REST snapshot (huge JSON) giving the initial state of every
  event/market/selection and is the source of truth for names, market names,
  and lines — but selection IDs. Live updates only carry selection IDs, not names.
- Diffusion message types observed in captures (first byte of decoded frame):
  - `0x00` — subscription message. Carries a human-readable **topic path
    string**, e.g.:
    - `BE/wh-ca-on/{eventId}` (event-level)
    - `BE/wh-ca-on/v2/{eventId}/{marketId}` (market-level)
    - `BE/wh-ca-on/v2/{eventId}/{marketId}/{selectionId}` (selection-level)
    This is a **major shortcut**: the real UUIDs are visible directly in these
    subscription paths, without needing to decode any CBOR at all.
  - `0x04` — Type 4: binds a short **topic alias** to a full CBOR object
    (uncompressed). This is the initial/full state payload for that alias.
  - `0x84` — Type 4, compressed variant: same as above but the CBOR payload is
    zlib-compressed after the alias header.
  - `0x05` — Type 5: a **binary delta** update against a previously-bound alias.
    Carries only the changed bytes (e.g. new `price.a`, `price.d`, `state`,
    handicap `line`), not a full object.
- Aliases are confirmed to always be **3 bytes**. The correct alias/CBOR boundary
  in Type 4/0x84 messages was determined by brute-force CBOR validation: try
  decoding starting at each candidate offset, and the correct one is the one
  where decoding consumes bytes exactly to end-of-message. This method was
  validated at **100% (130/130)** match against known aliases.

## Progress so far
1. **Alias → CBOR object map: SOLVED.**
   `scratch_decode.py` builds `alias_cbor[alias_hex] = decompressed_or_raw_cbor_bytes`
   by scanning all `ws_*.txt` files for `0x84` (zlib-decompress after alias) and
   `0x04` (validate CBOR decode boundary) messages. Confirmed 100% match rate
   against known test aliases.

2. **Binary delta (Type 5) format: partially reverse-engineered, NOT fully
   validated.**
   Current theory (implemented as `apply_binary_delta()` in `scratch_decode.py`):
   the delta payload is a flat sequence of CBOR items with this grammar:
   ```
   copy_count(int), [ insert_bytes(bytes), jump_to_old_offset(int), copy_count(int) ]*
   ```
   i.e. first copy N bytes from the old object's serialized CBOR bytes starting
   at old_pos=0, then repeatedly: insert a literal byte string into the output,
   jump the "old" cursor to an absolute offset, and copy N more bytes from the
   old buffer at that offset. This was verified **by hand** against two examples:
   - `ws_508`: items `[59, bytes(13), 79, 11]` → copy(59) + insert(13) + jump(79)
     + copy(11) = 83 output bytes. Confirmed correct.
   - `ws_454`: items `[60, bytes(1), 61, 5, bytes(13), 80, 11]` → copy(60) +
     insert(1) + jump(61) + copy(5) + insert(13) + jump(80) + copy(11) = 90
     output bytes. Confirmed correct (price `130→137` and `state` field decoded
     correctly).

   `scratch_decode.py` ends with a loop that runs this `apply_binary_delta`
   against **every** `0x05` message found in the whole log directory (up to
   `ws_550`), counting successes (result decodes as a valid dict consuming all
   bytes) vs failures. **This loop has not been run / its output was not
   captured in this session** — that's the first thing to do next.

3. **JSON snapshot structure explored** (`explore_json.py`, `list_json.py`):
   - `list_json.py` confirms `json_5.json` is the `/v4/home` snapshot.
   - Structure: `data['eventDisplayGroups'][i]['events'][j]` → event object
     with `id`, `name`, and `keyMarketGroups` (a **list**, not a dict — this
     tripped up an earlier version of the script).
   - `keyMarketGroups[i]['markets'][k]` → market object with `id`, `name`,
     optionally `line` (handicap), and `selections`.
   - `selections[m]` → `id`, `name`, `price` (this is the object whose `price`
     field gets live-updated via Diffusion deltas).

## Known issues / open questions (pick up here)
1. **Run the full-corpus delta validation loop** in `scratch_decode.py` (the
   "=== Testing all Type 5 deltas ===" section) and record the success/fail
   counts. Investigate any failures — in particular, check whether the delta
   grammar generalizes past exactly one or two `[insert, jump, copy]` groups
   (there was an earlier, now possibly-fixed, bug where variable-length
   replacements left "garbage" trailing bytes in the output for `ws_454`-style
   messages — the current code should fix this via the jump-then-copy model,
   but this is **unconfirmed at full scale**).
2. **No code yet ties the delta-decoded selection objects back to alias →
   Selection UUID → enrichment data.** The alias map currently only stores raw
   CBOR bytes; it does not yet carry the associated real UUID. The most robust
   path is likely to parse the `0x00` subscription messages for their path
   strings (see protocol background above) since these directly contain
   `{eventId}/{marketId}/{selectionId}` — much more reliable than trying to
   pull an ID out of decoded CBOR fields, which appear to be abbreviated
   (e.g. short single-letter keys like `a`/`d`/`f`/`price`).
3. **`analyze_caesar.py` itself has not been started.** Everything so far is
   scratch/exploration in `scratch_decode.py`, `explore_json.py`, `list_json.py`.
4. Need to double check the CBOR decoder in `scratch_decode.py` handles all
   major types seen in the actual data (it currently supports major types
   0,1,2,3,4,5,7 including float16/32/64 — should be sufficient for CBOR but
   confirm no float16 edge cases hang, per an earlier debugging note about a
   possible infinite loop / long-running script).

## Next steps (suggested order)
1. Re-run the full validation loop in `scratch_decode.py` against
   `caesars_workspace/caesars_full_logs` and capture actual success/fail counts.
2. Debug any failing deltas; extend `apply_binary_delta` grammar if a >2-group
   or edge-case pattern turns up.
3. Parse all `0x00` subscription messages; build
   `alias_hex -> {eventId, marketId, selectionId}` using the path strings
   (this sidesteps needing to extract IDs from CBOR content at all).
4. Load `json_5.json` (`/v4/home`) into `selectionId -> {name, market_name,
   line, eventId, marketId}` lookup (remember `keyMarketGroups` is a list).
5. Write `analyze_caesar.py`:
   - Walk `ws_*.txt` in numeric order.
   - Decode each frame's type byte; track alias→CBOR state as messages stream
     (Type 4/0x84 = full state, Type 5 = delta against current state).
   - On each Type 5 update, decode the new selection/market/event object,
     extract the changed price/line/state.
   - Resolve alias → UUIDs via the subscription-path map from step 3.
   - Enrich via the `/v4/home` lookup from step 4.
   - Append an ordered record (keyed by `ws_N` index) to the output list.
   - Dump the full list to a single clean JSON file, sorted by `ws_N`.
6. Sanity-check output against a handful of manually-verified examples
   (ws_508, ws_454, ws_395, ws_398 — these are already hand-verified above).

## Key reference IDs used in scratch testing
- Selection alias/original CBOR test case: `bd9bf767` (path:
  `.../d6938958-9ded-3c02-9dea-4d7b7ea04095/bd9bf767-a588-31d9-b297-215f9ff45921`,
  established in `ws_11`).
- Market alias test case: `e5cdb5`.
- Event alias test case: `e22a4b`.