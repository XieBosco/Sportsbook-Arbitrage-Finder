## High-Level Design Prompt

How would you design a sportsbook arbitrage finder with the following constraints:

* Data extraction relies on the user opening a specific page,  connecting to an existing browser opened with remote port 19222 through CDP, and eavesdropping on the WebSocket or long-polling messages sent from the sportsbook's web servers.
* Uses websocket-client to connect to CDP.
* Python is the main language.


Answer with a complete directory structure and explanation.

## Implement WireFrame Prompt

You are scaffolding a Python project called "sportsbook-arb-finder". Create the exact directory
structure and files below. This is a WIREFRAME pass only: every class and function must be fully
defined with proper signatures, type hints, and docstrings, but every function/method body must
contain only `pass` (or a `...` for abstract methods) — no implementation logic, no business logic,
no actual CDP/websocket code execution. The goal is a structurally complete, importable skeleton
that a human will fill in afterward.

Follow these rules for every file:
- Add type hints on all parameters and return values.
- Add a one-to-three line docstring on every class and function describing its contract/responsibility.
- Use dataclasses where indicated.
- Where a class extends an ABC, use `abc.ABC` and `@abstractmethod`.
- Do not add extra helper functions beyond what's specified — keep it minimal and exact.
- Every .py file should be valid Python that imports cleanly (add `__all__` where sensible).
- Non-.py files (yaml, md, sh, jsonl fixtures) should contain minimal placeholder content, not empty files.

Create this structure:

sportsbook-arb-finder/
├── README.md                         # short project description + how to run
├── pyproject.toml                    # standard project metadata, deps: websocket-client, requests, pyyaml, fastapi, uvicorn, pytest
├── requirements.txt                  # websocket-client, requests, pyyaml, fastapi, uvicorn, pytest
│
├── config/
│   ├── config.yaml                   # placeholder keys: min_margin_pct, cdp_port, poll_interval_ms
│   └── sportsbooks.yaml              # placeholder list of books with name + url_pattern
│
├── src/arbfinder/
│   ├── __init__.py
│   ├── main.py
│   │
│   ├── cdp/
│   │   ├── __init__.py
│   │   ├── discovery.py
│   │   ├── client.py
│   │   └── session_manager.py
│   │
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── draftkings.py
│   │   ├── fanduel.py
│   │   └── betmgm.py
│   │
│   ├── normalize/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── odds_math.py
│   │   └── team_aliases.py
│   │
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── store.py
│   │   ├── matcher.py
│   │   └── arbitrage.py
│   │
│   ├── alerts/
│   │   ├── __init__.py
│   │   ├── console.py
│   │   └── notifier.py
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── server.py
│   │   └── static/index.html         # minimal placeholder HTML shell
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logging.py
│       └── config.py
│
├── scripts/
│   ├── launch_chrome_debug.sh        # placeholder chrome launch command with --remote-debugging-port=19222
│   └── capture_raw_frames.py         # stub script with argparse skeleton only
│
├── tests/
│   ├── __init__.py
│   ├── test_odds_math.py
│   ├── test_arbitrage.py
│   ├── test_matcher.py
│   ├── test_parsers/
│   │   ├── __init__.py
│   │   ├── test_draftkings.py
│   │   └── test_fanduel.py
│   └── fixtures/
│       ├── draftkings_ws_sample.jsonl   # placeholder with one example JSON line
│       └── fanduel_longpoll_sample.json # placeholder with one example JSON object
│
└── logs/
    └── .gitkeep

Now fill in each source file with the following specific contracts (use these exactly as the
basis for your signatures — add nothing beyond what's implied):

--- src/arbfinder/normalize/models.py ---
- `@dataclass(frozen=True) class OddsUpdate`: fields `book: str`, `event_id: str`,
  `home_team: str`, `away_team: str`, `market: str`, `selection: str`,
  `line: float | None`, `price_american: int`, `timestamp: datetime`.
- `@dataclass(frozen=True) class Event`: fields `canonical_key: str`, `sport: str`,
  `home_team: str`, `away_team: str`, `start_time: datetime`.
- `@dataclass(frozen=True) class Market`: fields `canonical_key: str`, `event_key: str`,
  `market_type: str`, `line: float | None`.

--- src/arbfinder/normalize/odds_math.py ---
- `def implied_prob(american_odds: int) -> float`
- `def american_to_decimal(american_odds: int) -> float`
- `def decimal_to_american(decimal_odds: float) -> int`

--- src/arbfinder/normalize/team_aliases.py ---
- `def normalize_team_name(raw_name: str, sport: str) -> str`
- `def load_alias_table(path: str) -> dict[str, str]`

--- src/arbfinder/cdp/discovery.py ---
- `def list_tabs(port: int = 19222) -> list[dict]`
- `def find_tab(url_pattern: str, port: int = 19222) -> dict | None`

--- src/arbfinder/cdp/client.py ---
- `class CDPClient`:
  - `def __init__(self, ws_url: str, on_event: Callable[[dict], None]) -> None`
  - `def send(self, method: str, params: dict | None = None) -> int` (returns request id used)
  - `def run(self) -> None`
  - `def close(self) -> None`
  - private hooks: `def _on_open(self, ws) -> None`, `def _on_message(self, ws, message: str) -> None`,
    `def _on_close(self, ws, *args) -> None`

--- src/arbfinder/cdp/session_manager.py ---
- `class SessionManager`:
  - `def __init__(self, books_config: list[dict], on_event: Callable[[str, dict], None]) -> None`
  - `def start(self) -> None`
  - `def stop(self) -> None`
  - `def _reattach_loop(self) -> None` (background thread target for reconnect/poll logic)

--- src/arbfinder/parsers/base.py ---
- `class BookParser(ABC)`:
  - class attribute `book_name: str`
  - `@abstractmethod def can_handle(self, raw: str) -> bool`
  - `@abstractmethod def parse(self, raw: str) -> list[OddsUpdate]`

--- src/arbfinder/parsers/draftkings.py, fanduel.py, betmgm.py ---
- Each defines `class DraftKingsParser(BookParser)` / `FanDuelParser(BookParser)` / `BetMGMParser(BookParser)`
  implementing `can_handle` and `parse` per the base contract (bodies are `pass`).

--- src/arbfinder/engine/store.py ---
- `class OddsStore`:
  - `def __init__(self) -> None`
  - `def update(self, key: str, book: str, update: OddsUpdate) -> None`
  - `def get_market(self, key: str) -> dict[str, OddsUpdate]`
  - `def all_keys(self) -> list[str]`

--- src/arbfinder/engine/matcher.py ---
- `class MarketMatcher`:
  - `def __init__(self, alias_table: dict[str, str]) -> None`
  - `def canonical_key_for(self, update: OddsUpdate) -> str`
  - `def match(self, update: OddsUpdate) -> str` (resolves/caches canonical key)

--- src/arbfinder/engine/arbitrage.py ---
- `def find_arb(prices: dict[str, int]) -> dict | None`
- `class ArbitrageEngine`:
  - `def __init__(self, store: OddsStore, threshold_pct: float) -> None`
  - `def scan_once(self) -> list[dict]`
  - `def run_forever(self, alert_fn: Callable[[dict], None], interval_ms: int = 250) -> None`

--- src/arbfinder/alerts/console.py ---
- `def alert(opportunity: dict) -> None`

--- src/arbfinder/alerts/notifier.py ---
- `class Notifier(ABC)`:
  - `@abstractmethod def send(self, opportunity: dict) -> None`
- `class WebhookNotifier(Notifier)`:
  - `def __init__(self, webhook_url: str) -> None`
  - `def send(self, opportunity: dict) -> None`
- `class TelegramNotifier(Notifier)`:
  - `def __init__(self, bot_token: str, chat_id: str) -> None`
  - `def send(self, opportunity: dict) -> None`

--- src/arbfinder/ui/server.py ---
- `def create_app(store: OddsStore) -> "FastAPI"`
- `class ConnectionManager`:
  - `def __init__(self) -> None`
  - `async def connect(self, websocket) -> None`
  - `async def disconnect(self, websocket) -> None`
  - `async def broadcast(self, message: dict) -> None`

--- src/arbfinder/utils/logging.py ---
- `def get_logger(name: str) -> "logging.Logger"`

--- src/arbfinder/utils/config.py ---
- `def load_config(path: str) -> dict`

--- src/arbfinder/main.py ---
- `def build_parser_registry() -> dict[str, type[BookParser]]`
- `def make_dispatcher(parser: BookParser, store: OddsStore) -> Callable[[dict], None]`
- `def main() -> None`

--- scripts/capture_raw_frames.py ---
- `def main() -> None` with an argparse skeleton (`--port`, `--url-pattern`, `--out`) but no
  implementation, body `pass`.

--- tests/* ---
- For each test file, create empty test function stubs named after the contracts above
  (e.g. `def test_implied_prob() -> None: pass`, `def test_find_arb_detects_positive_margin() -> None: pass`),
  at least 2-3 per file, no assertions or logic yet.

After creating all files, print a tree of the final directory structure to confirm it matches
the spec above.


## Implement CDP, Parsers, and Normalize Prompt

You are implementing real logic into an existing wireframed Python project called
"sportsbook-arb-finder" (already scaffolded under src/arbfinder/ with empty `pass` bodies).
I've attached 5 working single-file prototype scrapers (caesars_scraper.py, betano_scraper.py,
betmgm_scraper.py, draftkings_scraper.py, fanduel_scraper.py) and 6 markdown docs describing
each book's protocol (caesars.md, diffusion_protocol_analysis.md, betano.md, betmgm.md,
draftkings.md, fanduel.md). These prototypes are proven, working code — do not "clean up" their
core decoding logic, only restructure it into the target files below. Read every doc fully before
writing code; several of the gotchas they describe (null-tolerant parsing, SignalR delimiters,
alias boundary detection) are easy to silently regress if you skip them.

Only touch these directories: src/arbfinder/cdp/, src/arbfinder/parsers/, src/arbfinder/normalize/.
Do not touch engine/, alerts/, ui/, or main.py yet.

============================================================
PART 1 — cdp/ (shared transport layer, book-agnostic)
============================================================

cdp/discovery.py
- Implement list_tabs() and find_tab() using `requests` against http://127.0.0.1:{port}/json,
  matching the polling pattern from the prototypes (loop with a short sleep until a `type=="page"`
  tab is found, ignoring `devtools://` urls).

cdp/client.py — CDPClient
- All 5 prototypes independently reinvent the same pattern: send `Network.enable` on open,
  listen for `Network.responseReceived` to trigger `Network.getResponseBody`, and listen for
  `Network.webSocketFrameReceived` for live pushes. Consolidate this into one reusable client:
  - Maintain an incrementing `id` counter for outgoing CDP commands via `send()`.
  - Maintain a `dict[int, str]` mapping outgoing `getResponseBody` command ids -> the original
    `requestId`, so that when the reply arrives (as `{"id":.., "result":{"body":...}}`) you know
    which HTTP response it belongs to. (The prototypes use `hash(request_id) % 100000` as a
    throwaway id and never map it back cleanly — fix this properly with a real dict instead.)
  - On `Network.responseReceived`, do NOT filter by URL here — that's book-specific. Instead,
    expose a constructor param `url_filter: Callable[[str], bool]` so each parser tells the client
    which URLs are worth fetching bodies for. Only call `getResponseBody` when `url_filter` matches,
    to avoid needlessly pulling every response body.
  - On `Network.webSocketFrameReceived`, always forward `params.response.payloadData` to a
    registered `on_ws_frame` callback — don't filter by socket URL at the CDP layer; let the
    parser's `can_handle` decide.
  - Preserve the reconnect-tolerant `run_forever()` behavior from the prototypes.

cdp/session_manager.py
- Port the "loop discovery.list_tabs() until match found, sleep N seconds between attempts"
  logic seen identically in all 5 `main()` functions.
- One CDPClient per configured book (from config/sportsbooks.yaml), each on its own thread.
- Add reattachment: if a tab's socket closes (browser refresh/navigation — this is EXPLICITLY
  the reason the docs tell users to "refresh the page to reload the reference dictionary"),
  re-run discovery and re-attach rather than dying. This is new behavior not in the prototypes —
  the prototypes only handle a clean startup, not a live reconnect. Add it.

============================================================
PART 2 — parsers/ (per-book, stateful)
============================================================

IMPORTANT CONTRACT CHANGE FROM THE WIREFRAME:
The original wireframe's `BookParser.parse(raw: str) -> list[OddsUpdate]` is too narrow —
every real book needs to (a) hold in-memory reference-dictionary state across calls, and
(b) distinguish HTTP response bodies from WS frames, since some books (FanDuel) get
their odds via HTTP, not WS. Update parsers/base.py to:

    class BookParser(ABC):
        book_name: str

        @abstractmethod
        def relevant_http_url(self, url: str) -> bool:
            """True if this HTTP response body should be fetched via getResponseBody."""

        @abstractmethod
        def handle_http_body(self, url: str, body: str) -> list[OddsUpdate]:
            """Parse an HTTP response body — reference dictionaries AND/OR live odds
            depending on the book (see each book's .md for which URLs carry which)."""

        @abstractmethod
        def handle_ws_frame(self, payload: str) -> list[OddsUpdate]:
            """Parse a raw WebSocket frame payload. Return [] for non-odds frames
            (handshakes, acks, keepalives)."""

Each parser keeps its own reference-dictionary state as instance attributes (mirroring each
prototype's global `reference_data` dict, but scoped to the instance, not module-global).

--- parsers/draftkings.py ---
Port from draftkings_scraper.py + draftkings.md:
- `relevant_http_url`: match `/v1/markets` + `api/sportscontent` (the control-data endpoint).
- `handle_http_body`: parse `events`/`markets`/`selections` arrays into the reference dict
  exactly as the prototype does (id-keyed dicts).
- `handle_ws_frame`:
  - Sanitize the base64 string (strip illegal chars, re-pad to a multiple of 4) before decoding
    — DraftKings' base64 is sometimes unpadded, this is NOT optional.
  - Unpack with `msgpack.Unpacker(strict_map_key=False)`.
  - Recursively walk the unpacked structure with the exact `find_outcomes` shape-matching
    heuristic from the prototype (len>=7, string/string/list/...list/str-or-None signature) —
    do not replace this with a schema assumption, DraftKings does not tag message types.
  - Preserve the two critical bugs-avoided-by-design from the doc:
    1. `marketId` (last array element) can legitimately be `None` for Moneyline — must not be
       treated as a missing/invalid field.
    2. When a selection ID isn't in the reference dict (dynamic handicap), extract the CORE_ID
       via `^0[A-Z]{2}(\d+)` and find a sibling selection sharing that core id to resolve the
       event — implement this exact fallback chain, including the final string-matching fallback
       against known event names.

--- parsers/fanduel.py ---
Port from fanduel_scraper.py + fanduel.md:
- `relevant_http_url`: match `content-managed-page` (reference dict) OR `getMarketPrices`
  (live odds) — both are HTTP, there is no WS parsing needed for this book at all.
- `handle_http_body`:
  - If body has `attachments.markets` → this is the reference dictionary; parse
    `attachments.events`, `attachments.markets` (with nested `runners`), same shape as prototype.
  - Otherwise, recursively search the body for any dict containing BOTH `marketId` and
    `runnerDetails` keys (do not hardcode a path — the doc explicitly warns FanDuel's JSON
    hierarchy shifts). Reuse the exact recursive `find_markets` approach from the prototype.
  - Odds extraction must try `winRunnerOdds.americanDisplayOdds.americanOdds` first, then fall
    back to `winRunnerOdds.trueOdds.americanOdds` — keep both branches, do not simplify to one.
- `handle_ws_frame`: not used for this book — return `[]` unconditionally (document why in a
  docstring: FanDuel is long-polling only, per fanduel.md).

--- parsers/betmgm.py ---
Port from betmgm_scraper.py + betmgm.md:
- `relevant_http_url`: match `fixture-view` — this is the only reference-dict source; the doc
  is explicit that the WS stream never carries human-readable names.
- `handle_http_body`: extract `fixture.id` / `fixture.name.value` into the reference dict.
- `handle_ws_frame`:
  - Split on `\x1e` (SignalR record separator) BEFORE calling `json.loads` on each fragment —
    this is called out as CRITICAL in the doc, don't skip it.
  - Each parsed fragment's `arguments` list may contain dicts with `messageType` of either
    `"GameUpdate"` or `"OptionMarketUpdate"` — implement both branches (primary markets vs.
    prop markets), each with its own field paths as in the prototype
    (`payload.game.results[].americanOdds` vs `payload.optionMarket.options[].price.americanOdds`).

--- parsers/betano.py ---
Port from betano_scraper.py + betano.md:
- `relevant_http_url`: match the regex
  `^https://www\.betano\.ca/danae-webapi/api/live/overview/\d+\?isInit=false&includeVirtuals=true$`.
- `handle_http_body`: populate `events`/`markets`/`selections` reference dict as in the prototype.
- `handle_ws_frame`:
  - Split on `\x1e` first (same SignalR pattern as BetMGM).
  - Skip any fragment that doesn't contain the substring `"NewLiveOverviewDiffs"` (keepalive
    filter — do this as a pre-check before attempting JSON parse, exactly as the prototype does).
  - `arguments[0]` is base64 → LZ4 frame decompress → utf-8 → json.loads. Implement exactly this
    chain (`base64.b64decode` → `lz4.frame.decompress` → `json.loads`); add `lz4` to requirements.
  - Two update scenarios must both be handled: `payload.selectionChanges` (odds-only changes,
    resolved via the reference dict) AND `payload.market` (a full new market block sent inline
    when a handicap line moves — this must be merged directly into the instance's reference
    dict as a side effect of parsing, not just returned as an OddsUpdate).

--- parsers/caesars.py + parsers/diffusion_codec.py (NEW FILE, not in original wireframe) ---
Caesars' protocol is materially more complex than the other four (binary CBOR + delta
patching, per diffusion_protocol_analysis.md and caesars.md) and deserves a dedicated codec
module separate from the parser itself, so the byte-level decoding is independently testable.

Create `parsers/diffusion_codec.py` with:
- `def decode_frame_type(raw: bytes) -> int` — returns the leading type byte.
- `def find_alias_boundary_uncompressed(data: bytes) -> int` — brute-force CBOR decode starting
  at offsets 3, 4, 5... and return the first offset where decoding succeeds AND consumes exactly
  the remaining bytes (per section 8.1 of the analysis doc).
- `def find_alias_boundary_compressed(data: bytes) -> int` — scan forward from offset 2 for the
  zlib magic bytes `0x78 0x01`.
- `def decode_full_state(raw: bytes, compressed: bool) -> tuple[bytes, dict]` — returns
  `(alias_bytes, decoded_cbor_dict)`, zlib-decompressing first if `compressed`.
- `def apply_delta(old_bytes: bytes, delta_items: list) -> bytes` — implement the exact
  copy/insert/jump grammar from section 3.2: `initial_copy_count, [insert, jump, copy]*`.
- `class AliasStateStore`:
  - `def __init__(self) -> None` — holds `dict[bytes, bytes]` (alias -> current raw CBOR bytes).
  - `def bind_full_state(self, alias: bytes, raw_cbor: bytes) -> dict` — store + decode.
  - `def apply_delta(self, alias: bytes, delta_items: list) -> dict` — apply grammar, store
    result as new "old buffer" for this alias (deltas are chained per section 3.2/8.2 — this
    is stateful and must persist across calls), decode + return.
  - `def classify(self, obj: dict) -> str` — returns "selection"/"market"/"event" using the
    field-presence heuristic in section 5.4 (`price` → selection, `templateId`/`marketCode`/`type`
    → market, `started` → event).

Then `parsers/caesars.py`:
- `relevant_http_url`: match `/v4/home`.
- `handle_http_body`: walk `data.eventDisplayGroups[].events[].keyMarketGroups[].markets[]`
  (note `keyMarketGroups` is a LIST not a dict, per the doc) to build a
  `selectionId -> {name, market_name, line, event_name}` lookup.
- `handle_ws_frame`: dispatch on the type byte via `diffusion_codec.decode_frame_type`:
  - `0x23` handshake, `0x00` subscription, `0x06` ack → return `[]`, no odds data.
  - `0x04` / `0x84` → decode full state via the codec, classify it, and if it's a selection,
    resolve via the `/v4/home` lookup and emit an `OddsUpdate`.
  - `0x05` → parse the CBOR item sequence after the alias + `0x00` separator into
    `initial_copy_count, [insert, jump, copy]*` and call `AliasStateStore.apply_delta`.
- Add `cbor2` to requirements.txt for CBOR decoding.

============================================================
PART 3 — normalize/
============================================================

normalize/odds_math.py
- Implement `implied_prob`, `american_to_decimal`, `decimal_to_american` using standard formulas.
  (None of the prototypes needed decimal/fractional conversion since books already provide
  american odds directly — but the arb engine downstream needs implied probability, so keep
  this file focused on that, don't over-build fractional-odds support nobody asked for.)

normalize/team_aliases.py
- None of the 5 prototypes needed cross-book name normalization (each just displays whatever
  name string its own reference dict provides). This is new, needed only for the arb-matching
  step downstream. Implement a simple normalizer: lowercase, strip common suffixes/punctuation,
  and a small manually-maintained alias table loaded from a JSON/YAML file via `load_alias_table`.

normalize/models.py
- Keep `OddsUpdate` as already stubbed, but note: each parser's `handle_http_body` and
  `handle_ws_frame` above should construct these directly rather than returning raw dicts —
  make sure the `line` field is populated from the handicap-formatting logic each prototype
  has inline (e.g. DraftKings/Betano's `handicap_str` sign logic) as a numeric field instead
  of a formatted string, since that logic currently exists only for display purposes.

============================================================
GENERAL RULES
============================================================
- Do not deduplicate the per-book SignalR/base64/CBOR logic into a shared abstraction — each
  book's binary format is different enough that a shared "decoder" would just be an if/elif
  in disguise. Keep per-book logic in its own parser file.
- Preserve every explicit gotcha called out in the .md docs as a code comment at the point where
  it's handled, referencing the doc section (e.g. `# see draftkings.md §4 — core-ID fallback`).
- Add unit tests under tests/test_parsers/ using short synthetic fixtures for the trickiest
  logic specifically: DraftKings core-ID fallback, Betano's dual selectionChanges/market
  scenarios, and Caesars' delta apply_delta grammar (use the worked examples in section 3.3
  of diffusion_protocol_analysis.md as literal test cases — they include expected input/output).
- Leave engine/, alerts/, ui/, and main.py untouched — I'll wire those in a follow-up pass.

I've also populated raw captured frame data and reference dictionaries for their respective sportsbooks in tests/fixtures.

Use these to:
1. Write parser unit tests against these real frames rather than synthetic ones wherever possible.
   Synthetic fixtures are fine only where a real example isn't available for a given branch
   (e.g. FanDuel's fallback americanOdds path).
2. If you find any frame that doesn't decode cleanly with the logic described in the .md docs,
   flag it explicitly in your response rather than silently swallowing the error — that's a sign
   the doc's spec has an edge case it didn't capture.


## Claude Continuation Prompt Response

CONTEXT: sportsbook-arb-finder project — continuing work on parsers/ and normalize/ only

## Project summary
Python arbitrage finder that connects to Chrome via CDP (remote debugging port 19222) using
websocket-client, passively eavesdrops on WebSocket frames and long-poll HTTP responses from
5 sportsbooks (DraftKings, FanDuel, BetMGM, Betano, Caesars), and normalizes odds into a common
format for cross-book arbitrage detection. The cdp/ folder (discovery.py, client.py,
session_manager.py) is COMPLETE and verified — do not touch it. This pass is scoped strictly to
parsers/ and normalize/.

I've attached: (1) the 5 original working prototype scripts and 6 markdown protocol docs that are
the ground-truth source of behavior, and (2) the current state of every file in parsers/ and
normalize/. Read every doc fully before writing code — they contain hard-won gotchas that are
easy to silently regress.

## BookParser contract (already finalized in base.py — do not change)
    class BookParser(ABC):
        book_name: str
        @abstractmethod def relevant_http_url(self, url: str) -> bool
        def relevant_ws_url(self, url: str) -> bool  # default True, override only if multi-socket
        @abstractmethod def handle_http_body(self, url: str, body: str) -> list[OddsUpdate]
        @abstractmethod def handle_ws_frame(self, payload: str) -> list[OddsUpdate]

## STATUS BY FILE — read this before touching anything

### ✅ Correct, don't rewrite (light polish only if you spot something)
- parsers/draftkings.py — base64 sanitize/repad, msgpack unpack, shape-matching heuristic,
  None-tolerant marketId, full core-ID regex fallback chain — all correctly ported.
- parsers/fanduel.py — correct branch between reference-dict body vs. live-odds body, recursive
  marketId+runnerDetails search (no hardcoded paths, as the doc requires), correct odds fallback
  chain (americanDisplayOdds → trueOdds). handle_ws_frame correctly returns [] (long-poll only book).
- parsers/betmgm.py — correct \x1e SignalR split BEFORE json.loads, both GameUpdate and
  OptionMarketUpdate branches implemented correctly. NOTE: silently drops updates when
  fixture_name == "Unknown Game" instead of emitting — a deliberate-looking deviation from the
  prototype worth a second look, not necessarily wrong.
- normalize/odds_math.py — implied_prob, american_to_decimal, decimal_to_american all verified
  correct against known odds pairs.
- normalize/models.py, normalize/team_aliases.py — fine as-is, no changes needed.

### ❌ BROKEN — needs full rewrite from prototype + doc

**parsers/betano.py** — does not implement the real protocol at all:
- relevant_http_url checks wrong/fabricated URL substrings ("api/rs/sport", "api/rs/events").
  Real endpoint (see betano.md): regex-matched
  `https://www.betano.ca/danae-webapi/api/live/overview/{id}?isInit=false&includeVirtuals=true`
- handle_http_body assumes wrong reference-dict schema (hunts for id/shortName/markets keys via
  recursion). Real schema is 3 flat dicts (events/markets/selections) keyed by ID — see
  betano_scraper.py's on_message handler for the exact parse.
- handle_ws_frame is missing the ENTIRE base64 → LZ4 frame decompress → UTF-8 → JSON pipeline
  that betano.md marks CRITICAL (with working example code in the doc, section "Decoding the
  Compressed Payload"). No lz4 import exists in the file. Currently just splits on \x1e and looks
  for a fictional "UpdateSelectionOdds" message type that appears nowhere in the doc or prototype.
- Missing the dual-scenario handling from betano.md §4: `selectionChanges` (odds-only changes,
  resolve via reference dict) vs. `market` (a full new market block sent inline on handicap
  moves — must be merged into the parser's reference_data as a side effect of parsing).
- Add `lz4` to requirements.txt.

**parsers/caesars.py + parsers/diffusion_codec.py** — most damaged module, needs rebuild against
diffusion_protocol_analysis.md sections 3 (delta grammar), 5 (CBOR schemas), 6 (/v4/home structure):
- relevant_http_url checks fabricated endpoint ("api/v1/events"/"api/v1/markets"). Real endpoint
  is `/v4/home` (see caesars.md).
- handle_http_body assumes wrong reference-dict schema (flat payload["events"]/["markets"]).
  Real structure: data.eventDisplayGroups[].events[].keyMarketGroups[].markets[].selections[] —
  note keyMarketGroups is explicitly a LIST not a dict, per the doc's repeated warning (this
  warning exists because it's a documented trap).
- diffusion_codec.py's decode_diffusion_message only branches on 0x84/0x04 (full state) — NO
  0x05 (delta) handling exists anywhere. Per the doc, live odds flow almost entirely through
  Type 5 deltas after initial subscribe/bind (131/131 in the corpus, starting mid-capture at
  ws_304) — without this, odds go silent after each selection's first snapshot.
- diffusion_codec.py never extracts/uses the 3-byte topic alias at all — the entire alias-boundary
  detection algorithm from doc §8.1 (brute-force CBOR offset search for 0x04 uncompressed, zlib
  magic-byte scan for 0x84 compressed) is unimplemented. AliasStateStore is instantiated and
  passed around but its methods are never called from decode_diffusion_message — dead code.
- AliasStateStore.update_cbor_bytes APPENDS new bytes instead of REPLACING the buffer. Per doc
  §8.2, delta application must produce a new buffer that becomes the new stored state — append-
  only accumulation is wrong even once wired up.
- _extract_cbor_from_payload accepts the first CBOR-decodable offset without verifying it
  consumes ALL remaining bytes — doc §8.1/§3.4 are explicit that "consumes exactly all remaining
  bytes" is the correctness check that makes offset brute-forcing reliable.
- caesars.py's _find_odds matches on invented field names ("odds", "p", "o") that appear nowhere
  in the doc's CBOR schemas (§5.1-5.3 only define price: {a, d, f}). Also: `odds = item.get("price", ...)`
  assigns the ENTIRE {a,d,f} dict to odds instead of price["a"] — float(odds) on a dict raises
  TypeError, silently caught, so every record is currently dropped even if everything above were
  fixed. This is the most severe individual bug — fix it even if you fix nothing else here.
- relevant_ws_url is already correct (`"/diffusion?ty=WB" in url`) — don't touch, it was verified
  in a prior review pass against caesars.md's socket URL.

### ⚠️ Cross-cutting concern, all 5 parsers
None of the prototypes split event names into home_team/away_team (they only ever printed the
full name string). Every parser's home/away split logic (" @ ", " vs ", " - ", " | " heuristics)
was invented by the prior implementation pass to satisfy the OddsUpdate dataclass shape — it is
NOT verified against real name strings from any book, especially Caesars/Betano where no example
name format appears in the docs at all. If real raw frame/reference-dict samples are available,
validate against them. Otherwise, at minimum flag this as an assumption in a code comment
per-parser rather than presenting it as settled.

## Priority order for this pass
1. diffusion_codec.py + caesars.py — non-functional end to end, highest-value fix
2. betano.py — non-functional, LZ4 pipeline and correct URL/schema entirely missing
3. Verify/tighten the home/away name-splitting heuristics across all 5 parsers
4. Add missing unit test coverage: tests/test_parsers/ has none of the tricky logic tested yet —
   specifically the Caesars delta apply_delta grammar (use the WORKED EXAMPLES in
   diffusion_protocol_analysis.md §3.3 as literal test cases — they give exact byte-level
   input/output you can assert against), DraftKings core-ID fallback (already correct, but
   untested), and Betano's dual selectionChanges/market scenarios.

## Ground rules (carried over from earlier scoping)
- Do not deduplicate per-book binary/decode logic into a shared abstraction — each book's format
  is different enough that a shared decoder becomes an if/elif in disguise.
- Preserve every explicit gotcha from the .md docs as an inline comment citing the doc section
  where it's handled (e.g. `# see draftkings.md §4 — core-ID fallback`) — this convention is
  already used correctly in draftkings.py, match it elsewhere.
- Do not touch cdp/, engine/, alerts/, ui/, or main.py in this pass.