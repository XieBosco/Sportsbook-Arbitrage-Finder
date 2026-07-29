# Diffusion Protocol Analysis — Caesars Sportsbook

## 1. Protocol Overview

Caesars Sportsbook uses **DiffusionData's** proprietary binary WebSocket protocol
to stream live odds updates to the browser. The protocol sits on top of a
standard WebSocket connection and uses **CBOR** (Concise Binary Object
Representation, RFC 8949) for structured data serialization within its messages.

**WebSocket endpoint:**
```
wss://api.americanwagering.com/regions/ca/locations/on/brands/czr/diffusion?ty=WB&v=25&ca=10&r=0
```

Each WebSocket frame contains exactly one Diffusion message. The frames arrive
as base64-encoded binary and, once decoded, begin with a **type byte** that
determines the message structure.

---

## 2. Message Types

### 2.1 Handshake (`0x23`)

The very first message in the connection. Contains a session token and protocol
negotiation parameters.

```
Byte layout:  23 [session-token-and-capabilities...]
Example:      23 19 64 2b 9f 00 c4 05 2b 93 c4 00 00 00 01 00 ...
```

- Only one handshake per connection.
- The payload structure is opaque — we treat it as raw bytes.

### 2.2 Subscription (`0x00`)

The client subscribes to a **topic path** containing human-readable UUIDs. These
paths follow the pattern:

| Path pattern | Level | Example |
|---|---|---|
| `BE/wh-ca-on/{eventId}` | Event | `BE/wh-ca-on/f7bdf6e6-fcb0-4184-ab84-99ed2a961826` |
| `BE/wh-ca-on/v2/{eventId}/{marketId}` | Market | `BE/wh-ca-on/v2/f7bdf6e6.../d6938958...` |
| `BE/wh-ca-on/{eventId}/{marketId}/{selectionId}` | Selection | `BE/wh-ca-on/f7bdf6e6.../d6938958.../bd9bf767...` |

**Frame structure:**
```
00 [header bytes] [CBOR-like length prefix] [ASCII topic path] [subscription options]
```

The header between `0x00` and the path string is 8 bytes and contains internal
routing/alias identifiers (NOT the same alias used in Type 4/5 messages — see
Section 4.3). The subscription options trail after the path:
```
0f 02 0a "PERSISTENT" 05 "false" 05 "_VIEW" 03 "all"
```

**Observation in corpus:** 129 subscription messages were captured, establishing:
- 12 event-level subscriptions
- 38 market-level subscriptions (use `/v2/` path variant)
- 78 selection-level subscriptions
- 1 anomalous short message (`ws_519`, 5 bytes — likely a re-subscription ping)

### 2.3 Full State — Type 4 Uncompressed (`0x04`)

Binds a **topic alias** to a full CBOR-serialized object. This is the initial
state payload for a given selection, market, or event.

```
Byte layout:  04 [flags] [3-byte alias] [CBOR map]
Example:      04 10 e1fbbb a4 62 69 64 78 24 ...
              |  |  |       └── CBOR: {id: "bd9bf767-...", active: true, price: {...}, state: "open"}
              |  |  └── alias = e1fbbb
              |  └── flags byte (always 0x10 in corpus)
              └── type byte
```

**Alias boundary detection:** The boundary between the alias bytes and the CBOR
payload is found by brute-force: try decoding CBOR starting at offsets 3, 4,
5, ... and accept the offset where the decoded object is a `dict` that consumes
exactly all remaining bytes. In practice, aliases are always **3 bytes** (offset
5 = 1 type + 1 flags + 3 alias).

**In corpus:** 78 Type 4 messages, all with 3-byte aliases.

### 2.4 Full State — Type 4 Compressed (`0x84`)

Same semantics as `0x04`, but the CBOR payload is **zlib-compressed**.

```
Byte layout:  84 [flags] [3-byte alias] [zlib-compressed CBOR]
Example:      84 10 e1c313 78 01 15 c6 41 0a ...
              |  |  |       └── zlib stream (starts with 0x78 0x01 = zlib magic)
              |  |  └── alias = e1c313
              |  └── flags byte (always 0x10 in corpus)
              └── type byte (0x84 = 0x04 | 0x80 compression flag)
```

**Alias boundary detection:** Scan forward from offset 2 looking for the zlib
magic bytes `0x78 0x01`. The bytes between offset 2 and the magic position are
the alias.

**In corpus:** 50 Type 0x84 messages, all with 3-byte aliases.

### 2.5 Binary Delta — Type 5 (`0x05`)

A compact binary diff against the **current CBOR state** of an alias. Does not
contain a full object — only the changed bytes.

```
Byte layout:  05 [flags] [3-byte alias] 00 [delta payload (CBOR items)]
Example:      05 10 e263a1 00 18 3b 55 38 ...
              |  |  |       |  └── delta payload: CBOR sequence
              |  |  |       └── 0x00 separator
              |  |  └── alias = e263a1
              |  └── flags byte
              └── type byte
```

The `0x00` byte acts as a separator between the alias and the delta payload.
The alias bytes are extracted as `data[2:zero_pos]`.

**Delta grammar** (see Section 3 for full specification):
```
copy_count, [insert_bytes, jump_to_old_offset, copy_count]*
```

**In corpus:** 131 Type 5 messages, all successfully decoded (0 failures).

### 2.6 Acknowledgement (`0x06`)

The client acknowledges receipt of topic alias bindings. Two forms observed:

```
2-byte:  06 XX          (114 messages)
3-byte:  06 XX XX 01    (48 messages)
```

Where `XX` bytes are references to the aliases being acknowledged. These are
flow-control messages and do not carry odds data.

**In corpus:** 162 acknowledgement messages total.

---

## 3. Binary Delta Specification

### 3.1 Overview

Type 5 deltas operate on the **raw serialized CBOR bytes** of the object, not on
the decoded structure. They describe a sequence of copy/insert operations that
produce a new byte buffer from the old one.

### 3.2 Grammar

The delta payload is a flat sequence of CBOR-encoded items:

```
initial_copy_count:int, [insert:bytes, jump:int, copy:int]*
```

| Item | Type | Semantics |
|------|------|-----------|
| `initial_copy_count` | unsigned int | Copy this many bytes from old buffer starting at offset 0 |
| `insert` | byte string | Literal bytes to write into the new buffer |
| `jump` | unsigned int | Set the old-buffer cursor to this absolute offset |
| `copy` | unsigned int | Copy this many bytes from old buffer at the current cursor |

The triplet `(insert, jump, copy)` repeats zero or more times.

### 3.3 Worked Examples

**Example 1: `ws_508`** — single replacement (price change)
```
Old buffer: 91 bytes (selection bd9bf767, price.a=130)
Delta items: [59, bytes(13), 79, 11]

Operations:
  1. copy(59)  → output[0:59]  = old[0:59]    (header + id + part of price)
  2. insert(13) → output[59:72] = literal bytes (new price.a, price.d, price.f)
  3. jump(79)   → old_pos = 79
  4. copy(11)   → output[72:83] = old[79:90]   (state field)

Result: 83 bytes → decoded as price.a=-200, price.d=1.5, price.f="1/2"
```

**Example 2: `ws_454`** — two replacements (price + state change)
```
Old buffer: 91 bytes (same selection)
Delta items: [60, bytes(1), 61, 5, bytes(13), 80, 11]

Operations:
  1. copy(60)   → old[0:60]       (header through price.a prefix)
  2. insert(1)  → literal byte    (new price.a value byte)
  3. jump(61)   → old_pos = 61
  4. copy(5)    → old[61:66]      (price.d prefix)
  5. insert(13) → literal bytes   (new price.d, price.f, state)
  6. jump(80)   → old_pos = 80
  7. copy(11)   → old[80:91]      (trailing fields)

Result: 90 bytes → decoded as price.a=137, price.d=2.37, price.f="11/8", state="open"
```

### 3.4 Validation

The grammar was validated against **131/131 (100%)** Type 5 messages in the
corpus. Each delta result was verified to:
1. Decode as a valid CBOR map (`dict`)
2. Consume exactly all output bytes (no trailing garbage)

The alias state is **chained**: after applying a delta, the resulting bytes
become the new "old buffer" for subsequent deltas on the same alias.

---

## 4. Topic Aliases

### 4.1 Structure

Aliases are always **3 bytes** in this corpus (confirmed 128/128 for Type 4/0x84
messages and 78/78 unique aliases in Type 5 messages). They act as compact
references to avoid retransmitting full topic paths on every update.

### 4.2 Alias ↔ UUID Resolution

Each decoded CBOR object contains an `id` field with its UUID as a string. This
is the same UUID found in the subscription topic paths and in the `/v4/home` REST
snapshot. Resolution is therefore trivial:

```
alias_hex → decode CBOR → obj["id"] → UUID string
```

All 128 unique aliases in the corpus mapped successfully to UUIDs in
`json_5.json` (0 unmapped).

### 4.3 Subscription Aliases vs. Data Aliases

The `0x00` subscription messages contain their own internal alias-like bytes in
the header (bytes 2–4 after the type byte). These are **NOT** the same as the
data aliases used in Type 4/5 messages. The subscription aliases appear to be
routing identifiers within the Diffusion server and are not needed for decoding.

---

## 5. CBOR Object Schemas

### 5.1 Selection Object
```json
{
  "id": "bd9bf767-a588-31d9-b297-215f9ff45921",
  "active": true,
  "price": {
    "a": 130,       // American odds
    "d": 2.3,       // Decimal odds
    "f": "13/10"    // Fractional odds
  },
  "state": "open"   // or "suspended"
}
```

### 5.2 Market Object
```json
{
  "id": "fa50d853-b0a2-3f96-945f-23768eaedfec",
  "name": "|Total Runs Live|",
  "templateId": "_7cTotal_20Runs_20Live_7c",
  "type": "over-under",
  "templateName": "|Total Runs Live|",
  "tradedInPlay": true,
  "display": true,
  "active": true,
  "line": 5.5,
  "state": "open",
  "byoEligible": true,
  "marketCode": "964d2a7b-69c7-3c11-bf09-fbf7df335815"
}
```

### 5.3 Event Object
```json
{
  "id": "8e767a58-7f55-4521-9e53-92b01a3add69",
  "tradedInPlay": true,
  "display": true,
  "active": true,
  "state": "open",
  "started": true,
  "byoEligible": true
}
```

### 5.4 Object Type Classification

CBOR objects do not carry an explicit "type" field. Classification uses a
heuristic based on field presence:

| Condition | Classified as |
|-----------|--------------|
| Has `price` key | Selection |
| Has `templateId` or `marketCode` or `type` key | Market |
| Has `started` key, or has `tradedInPlay` without `price`/`templateId` | Event |

This heuristic correctly classified all 128 objects in the corpus.

---

## 6. `/v4/home` JSON Snapshot Structure

The REST snapshot (`json_5.json`) provides the enrichment data — names, market
names, and handicap lines — that the WebSocket objects do not carry.

```
data
 └── eventDisplayGroups[]
       └── events[]
             ├── id: "f7bdf6e6-..."
             ├── name: "Toronto Blue Jays at Boston Red Sox"
             └── keyMarketGroups[]    ← LIST, not dict
                   └── markets[]
                         ├── id: "d6938958-..."
                         ├── name: "|Run Line Live|"
                         ├── line: 1.5         (optional — only on spread/total)
                         └── selections[]
                               ├── id: "bd9bf767-..."
                               ├── name: "|Toronto Blue Jays|"
                               └── price: {a, d, f}
```

**Coverage in corpus:**
- 25 events, 73 markets, 267 selections in snapshot
- 12 events, 38 markets, 78 selections subscribed via WebSocket
- **0 unmapped** alias IDs (100% coverage)

---

## 7. Complete Message Flow

The observed message sequence in `caesars_full_logs` (551 messages):

```
ws_1:     0x23  Handshake
ws_2–4:   0x06  Acks (initial)
ws_5:     0x00  Subscribe to event (Toronto Blue Jays at Boston Red Sox)
ws_6:     0x84  Full state → event object (compressed)
ws_7:     0x06  Ack
ws_8:     0x00  Subscribe to market (Run Line Live)
ws_9:     0x84  Full state → market object (compressed)
ws_10:    0x06  Ack
ws_11:    0x00  Subscribe to selection (bd9bf767)
ws_12:    0x04  Full state → selection object (uncompressed)
ws_13:    0x06  Ack
  ...
  [pattern repeats: subscribe → full state → ack, for all events/markets/selections]
  ...
ws_304+:  0x05  Delta updates begin (odds changes, state changes, line moves)
  ...
ws_551:   0x05  Last delta in capture
```

**Key observation:** The protocol strictly follows a
subscribe→bind→ack→delta lifecycle. Deltas only appear after all
subscriptions and initial state bindings are complete (starting at ws_304 in
this capture).

---

## 8. Implementation Notes

### 8.1 Alias Boundary Detection

**For `0x84` (compressed):** Scan from offset 2 for zlib magic `0x78 0x01`.
Bytes `data[2:magic_pos]` are the alias; `data[magic_pos:]` is the zlib stream.

**For `0x04` (uncompressed):** Try CBOR decoding starting at offsets 3, 4, 5, ...
The correct offset is where the decoded value is a `dict` and the decoder
consumes exactly all remaining bytes. The alias is `data[2:cbor_start]`.

### 8.2 Delta State Management

Deltas are **chained**: after applying delta D1 to original state S0, the result
S1 becomes the base for subsequent delta D2. The decoder must maintain a running
`alias → current_cbor_bytes` map and update it on every Type 4 (reset) and
Type 5 (delta) message.

### 8.3 Float16 in CBOR

Some CBOR values use IEEE 754 half-precision (float16). The decoder must handle
CBOR additional info 25 (2-byte float) in addition to the standard float32 (26)
and float64 (27). This appears in price fields like `price.d`.
