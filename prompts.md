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
