# Caesars Sportsbook Odds Scraper

## Overview
Caesars establishes a WebSocket connection using DiffusionData's servers to send delta messages containing live odds data to the frontend. The data uses a proprietary, binary-compressed WebSocket protocol called **Diffusion**.

## Deeplink Schema
To construct a URL that automatically adds a bet to the user's betslip, use the `selectionIds` parameter.
```
https://sportsbook.caesars.com/ca/on/bet/betslip?selectionIds={selectionId}
```
*Example:*
`https://sportsbook.caesars.com/ca/on/bet/betslip?selectionIds=9dc72c90-b2e2-3194-8265-8a9f65905e09`

### Variables
- `selectionId`: A UUID string identifier for every unique selection.

## Data Architecture & Flow

### 1. State Initialization (`/v4/home`)
When the page first loads, Caesars makes a GET request to fetch a JSON file containing the initial state of each market and important metadata for each event:
```
https://api.americanwagering.com/regions/ca/locations/on/brands/czr/sb/v4/home
```
- This massive JSON blob contains the current state of all live matches, markets, and selections.
- The scraper intercepts this `responseReceived` event, issues a `getResponseBody`.
- This hashmap links every Selection ID to its parent Market and Event, which is required because live odds updates only contain the Selection ID.

**JSON structure** (see `json_5.json` for full snapshot):
```
data.eventDisplayGroups[].events[]
  ├── id          (event UUID)
  ├── name        (e.g. "Toronto Blue Jays at Boston Red Sox")
  └── keyMarketGroups[]     ← NOTE: this is a list, not a dict
        └── markets[]
              ├── id        (market UUID)
              ├── name      (e.g. "|Run Line Live|")
              ├── line      (handicap, e.g. 1.5 — only on spread/total markets)
              └── selections[]
                    ├── id    (selection UUID)
                    ├── name  (e.g. "|Toronto Blue Jays|")
                    └── price {a: american, d: decimal, f: fractional}
```

### 2. Live Odds Updates (Diffusion WebSocket)
Caesars establishes connection to 4 separate Diffusion websockets. The primary one that sends live odds changes is:
```
wss://api.americanwagering.com/regions/ca/locations/on/brands/czr/diffusion?ty=WB&v=25&ca=10&r=0
```
*(We can ignore the `livescores`, `cashout`, and `microbetting` websockets for standard odds scraping).*

The connection lifecycle follows this sequence:
1. **Handshake** (`0x23`) — Connection establishment with session token.
2. **Subscriptions** (`0x00`) — Client subscribes to topic paths containing UUIDs:
   - `BE/wh-ca-on/{eventId}` — event-level state
   - `BE/wh-ca-on/v2/{eventId}/{marketId}` — market-level state
   - `BE/wh-ca-on/{eventId}/{marketId}/{selectionId}` — selection-level state (odds)
3. **Full State Binding** (`0x04`/`0x84`) — Server binds a short **topic alias** (3 bytes) to a full CBOR object. `0x84` payloads are zlib-compressed.
4. **Acknowledgements** (`0x06`) — Client acknowledges receipt of alias bindings.
5. **Delta Updates** (`0x05`) — Server pushes compact binary diffs against the alias's current CBOR state (e.g. changed `price.a`, `price.d`, `state`, or `line`).

### 3. Alias Resolution
Each CBOR object (event, market, or selection) carries its own `id` field as a UUID string. This is the same UUID that appears in the subscription topic paths and in the `/v4/home` snapshot, providing a direct link for enrichment without needing to decode the subscription messages for alias mapping.

**Object classification heuristic** (CBOR objects don't carry an explicit type field):
| Has field | Object type |
|-----------|-------------|
| `price` | Selection |
| `templateId` or `marketCode` | Market |
| `started` | Event |

### 4. Binary Delta Format (Type 5)
Delta payloads are flat sequences of CBOR items with grammar:
```
copy_count, [insert_bytes, jump_to_old_offset, copy_count]*
```
- `copy_count` (int): copy N bytes from old CBOR buffer at current position
- `insert_bytes` (bytes): literal bytes to splice into the output
- `jump_to_old_offset` (int): absolute offset to resume copying from the old buffer
- `copy_count` (int): copy N more bytes from old buffer at new position

This format was validated at **131/131 (100%)** across the full capture corpus with zero failures.

## Decoding Pipeline (`analyze_caesar.py`)
The decode pipeline processes all `ws_*.txt` files in numeric order:
```
ws_*.txt (base64 Diffusion) ──► decode type byte
  ├── 0x23 → handshake record
  ├── 0x00 → subscription (parse topic path, extract UUIDs)
  ├── 0x04 → full CBOR state (alias boundary via CBOR validation)
  ├── 0x84 → full CBOR state (zlib-decompress after alias)
  ├── 0x05 → apply binary delta to alias state, re-decode CBOR
  └── 0x06 → alias acknowledgement

json_5.json (/v4/home) ──► selectionId → {name, market_name, line, event_name}

Output: decoded_odds.json (551 records, chronologically ordered by ws_N)
```

### Output Statistics (from `caesars_full_logs`)
| Message Type | Count |
|-------------|-------|
| Handshake (`0x23`) | 1 |
| Subscriptions (`0x00`) | 129 |
| Full State (`0x04`/`0x84`) | 128 |
| Deltas (`0x05`) | 131 |
| Acknowledgements (`0x06`) | 162 |
| **Total** | **551** |
