# Betano Sportsbook Odds Scraper

## Overview
Betano utilizes a SignalR WebSocket connection to send live odds data to the frontend. The data is heavily obfuscated: it is sent as a Base64-encoded string that encapsulates a compressed LZ4 binary block.

## Deeplink Schema
Betano does not have a strict parameterized API deeplink schema for the betslip. However, the preferred URL to redirect a user to the appropriate market is:
```
https://www.betano.ca/live/{eventName}/{eventId}/
```
*Example:* `https://www.betano.ca/live/mexico-england/88363620/`

## Data Architecture & Flow

### 1. The Reference Dictionary
Through the mechanism of short-polling, Betano sends a `GET` request to a generic endpoint to fetch the reference dictionary, which maps decoded IDs to human-readable strings:
```
https://www.betano.ca/danae-webapi/api/live/overview/{DictionaryId}?isInit=false&includeVirtuals=true
```
**Variables:**
- `DictionaryId`: An integer identifier for every unique request to fetch a new reference dictionary.
- `eventId`: An identifier for a unique event.

To fetch the URL needed to redirect a user, get the `eventId` of an outcome which maps to an object containing a pre-built URL inside the reference dictionary.

### 2. Live Odds Updates (WebSocket)
Betano establishes a WebSocket connection to:
```
wss://www.betano.ca/contenthub?platformType=1
```
It pushes data as Base64-encoded, LZ4-compressed JSON payloads.

---

## Implementation Guide (Building the Scraper)

Developing a robust live-odds scraper for Betano involves dealing with a compressed data pipeline wrapped inside a SignalR WebSocket connection, alongside aggressive anti-bot protections.

### 1. Passive CDP Interception & Port Scanning (CRITICAL)
To avoid Betano's active bot detection, you must intercept data through Chrome's remote debugging protocol (CDP). Target the `Network.webSocketFrameReceived` events.

> **WARNING: Anti-Bot Port Scanning:** 
> Betano's frontend JavaScript actively attempts to open WebSocket connections to `ws://127.0.0.1` on common debugging and automation ports (like `9222`). If your scraper exposes its CDP port locally and Betano scans it successfully, your session will be instantly flagged as a bot. 
> **The Fix:** You must block these local requests. Install an ad-blocker extension (like AdGuard AdBlocker MV3) and add `||127.0.0.1^` and `||localhost^` to your **User rules** list. This intercepts and blocks the port scan locally.

### 2. SignalR and the `\x1e` Terminator
Betano's WebSocket data runs on SignalR. 
- SignalR frames are appended with the ASCII Record Separator character `\x1e` (e.g. `{"type":1,...}\x1e`).
- Running a raw `json.loads()` on this string will throw an `Extra data` JSONDecodeError. 
- **The Fix:** You must split the payload string by `\x1e` and iterate over the fragments before parsing them into JSON.
- **Filtering:** SignalR will also send random keep-alive handshake packets (like `{"type":3,"invocationId":"29","result":null}`). Safely ignore these by ensuring the string contains `"NewLiveOverviewDiffs"` before attempting to parse it.

### 3. Decoding the Compressed Payload
Once you isolate a `NewLiveOverviewDiffs` message and parse it into a JSON object, the actual odds payload is buried inside the `arguments` array.
- Extract the string from `arguments[0]`.
- Decode it from **Base64** into raw bytes.
- Decompress the bytes using the **LZ4** frame compression algorithm.
- Decode the resulting bytes back into a UTF-8 string and parse it as JSON. 

*Example Python Decoder:*
```python
import base64
import lz4.frame
import json

def decode_danae_message(b64_payload):
    compressed_bytes = base64.b64decode(b64_payload)
    decompressed_bytes = lz4.frame.decompress(compressed_bytes)
    json_string = decompressed_bytes.decode('utf-8')
    return json.loads(json_string)
```

### 4. The Live Odds Data Model
The uncompressed Betano payload gracefully handles both standard price changes and handicap line movements without requiring heuristic matching:
- **Static Handicaps (`selectionChanges`):** When only the odds change, the payload provides a `selectionChanges` map (`marketId -> [selection objects]`). Use your Reference Dictionary to resolve these IDs to human-readable names.
- **Dynamic Handicaps (`market`):** When a handicap line moves, Betano creates a brand new market and sends the *entire* market block (including all names, shortnames, new selection IDs, and prices) directly in the `payload['market']` field. You simply parse this block and immediately inject the new market and its selections into your local Reference Dictionary state so future price changes can be resolved.
