# DraftKings Sportsbook Odds Scraper

## Overview
DraftKings streams live odds over a persistent WebSocket connection utilizing binary payloads serialized with MessagePack and encoded in Base64. 

## Deeplink Schema
To construct a URL that automatically adds a bet to the user's betslip, use the `outcomes` parameter.
**Preferred Schemas:**
```
https://sportsbook.draftkings.com/?outcomes={selectionId}
https://sportsbook.draftkings.com/event/{eventId}?outcomes={selectionId}
```
**Full Schema:**
```
https://sportsbook.draftkings.com/event/{seoIdentifier}/{eventId}?outcomes={selectionId}
```

### Variables
- `eventId`: A unique identifier for the match/event.
- `seoIdentifier`: The SEO-friendly URL slug (e.g., `spain-vs-austria`).
- `selectionId` (or `outcomeId`): A unique identifier for a specific bet selection.

## Data Architecture & Flow

### 1. The Reference Dictionary (State Initialization)
DraftKings makes an initial HTTP `GET` request to fetch a reference dictionary containing static metadata for markets, events, and selections.
**Example Endpoint:**
```
https://sportsbook-nash.draftkings.com/sites/CA-ON-SB/api/sportscontent/controldata/...
```
This data is crucial for resolving dynamically created markets (like moving handicap lines) that are sent in the WebSocket stream.

### 2. Live Odds Updates (WebSocket)
DraftKings establishes a WebSocket connection to:
```
wss://sportsbook-ws-ca-on.draftkings.com/websocket?format=msgpack&locale=en
```
The server pushes live odds updates as Base64-encoded strings, which actually contain MessagePack-serialized binary data.

---

## Implementation Guide (Building the Scraper)

DraftKings actively flags and blocks heavily automated headless browsers. To securely extract the WebSocket data without triggering detection, a passive CDP listening approach is strictly required.

### 1. Passive CDP Interception
1. Launch a standard (non-headless) Chrome instance with a remote debugging port (e.g., `--remote-debugging-port=19222`). 
2. Use `websocket-client` to fetch `http://127.0.0.1:19222/json` and attach to the active tab's CDP websocket.
3. Send the `Network.enable` CDP command to begin intercepting all network traffic.
4. Listen for `Network.webSocketFrameReceived` events originating from `wss://sportsbook-ws...draftkings.com`.

### 2. Decoding Base64 and MessagePack (CRITICAL)
The `response.payloadData` from the WebSocket frame contains a Base64-encoded string, which wraps a MessagePack binary payload. 

**Decoding Gotchas:**
- DraftKings' Base64 strings can sometimes lack proper padding (`=`). You must sanitize the string (stripping out illegal characters) and dynamically add padding before decoding.
- The resulting binary includes raw bytes and proprietary `Timestamp` objects that will cause standard JSON encoders to crash.
- Unpack using `msgpack.unpackb(raw_bytes, strict_map_key=False)` and use a custom JSON encoder to safely convert timestamps and raw bytes to UTF-8 strings.

### 3. Payload Structure & Mapping
Once decoded into JSON, the payload is an array of arrays. The odds array typically looks like `["+106", "2.06", "53/50", 49]`.

| Array Index | Frontend Variable | Data Type | Value from Payload |
| :--- | :--- | :--- | :--- |
| **0** | `selectionId` | String | `"0HC85399015P250_1"` |
| **1** | `selectionName` | String | `"WAS Nationals"` |
| **2** | `odds` | Array | `["+106", "2.06", "53/50", 49]` |
| **3** | `binaryOddsData` | Binary block| `[Raw Float/Binary Data]` |
| **4** | `marketType` | String | `"MainPointLine"` |
| **5** | `tags` | Array of Strings | `["SGP", "OSB"]` |
| **6** | `marketId` | String | `"0HC85399015P350_1"` |

| Odds Sub-Array Index | Frontend Variable | Data Type | Value from Payload |
| :--- | :--- | :--- | :--- |
| **0** | `american` | String | `"+106"` |
| **1** | `decimal` | String | `"2.06"` |
| **2** | `fractional` | String | `"53/50"` |
| **3** | `impliedProbability` | Integer | `49` |

### 4. Handling Dynamic Handicaps (Bug-Fix)
When a handicap changes (e.g., Over 8.5 to Over 8.0), DraftKings dynamically generates a brand new market and selection ID in the live odds payload. This new ID will **not** exist in your initial Reference Dictionary!
- Fortunately, DraftKings selection IDs follow a strict format: `PREFIX` + `CORE_ID` + `HANDICAP` (e.g., `0OU85458301O850_1`).
- The `CORE_ID` (e.g., `85458301`) remains constant across all handicap changes for a specific market grouping.
- **The Fix:** To resolve a new, unknown market, extract the core ID using a regex like `^0[A-Z]{2}(\d+)`. Search your original Reference Dictionary for any old selection ID that shares this exact core ID. Since they share the core ID, they point to the exact same game/event!

### 5. Handling Static Handicaps (Moneyline)
To save bandwidth, if a market's odds change but its handicap does not (which is always true for Moneyline), DraftKings sends `null` for the `marketId` at the end of the odds array instead of repeating the string.
- Ensure your array-parsing logic explicitly tolerates `null` (or `None` in Python) in the final index of the array (`marketId`), otherwise you will silently drop all Moneyline updates!
