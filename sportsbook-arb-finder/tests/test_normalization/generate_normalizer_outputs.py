"""Script to run normalizers against fixtures and dump outputs for manual review."""

import glob
import json
import os
from datetime import datetime

from arbfinder.parsers.betano import BetanoParser
from arbfinder.parsers.betmgm import BetMGMParser
from arbfinder.parsers.caesars import CaesarsParser
from arbfinder.parsers.draftkings import DraftKingsParser
from arbfinder.parsers.fanduel import FanDuelParser

from arbfinder.normalization.normalizer import Normalizer
from arbfinder.normalization.book_normalizers.betano_normalizer import BetanoNormalizer
from arbfinder.normalization.book_normalizers.betmgm_normalizer import BetMGMNormalizer
from arbfinder.normalization.book_normalizers.caesars_normalizer import CaesarsNormalizer
from arbfinder.normalization.book_normalizers.draftkings_normalizer import DraftKingsNormalizer
from arbfinder.normalization.book_normalizers.fanduel_normalizer import FanDuelNormalizer

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "../scripts/data2")
# FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")
OUTPUTS_DIR = os.path.dirname(__file__)


def main():
    normalizer = Normalizer(
        normalizers={
            "DraftKings": DraftKingsNormalizer(),
            "FanDuel": FanDuelNormalizer(),
            "BetMGM": BetMGMNormalizer(),
            "Betano": BetanoNormalizer(),
            "Caesars": CaesarsNormalizer(),
        }
    )

    all_normalized_updates = []

    # --- DraftKings ---
    print("Normalizing DraftKings...")
    parser = DraftKingsParser()
    ref_path = os.path.join(FIXTURES_DIR, "draftkings", "draftkings_messages", "json_1.json")
    with open(ref_path, "r", encoding="utf-8") as f:
        d = json.load(f)
        parser.handle_http_body("api/sportscontent/v1/markets", json.dumps(d.get("data", d)))
    
    updates = []
    msg_files = glob.glob(os.path.join(FIXTURES_DIR, "draftkings", "draftkings_messages", "ws_*.txt"))
    msg_files.sort(key=lambda x: int(os.path.basename(x)[3:-4]))
    for mf in msg_files:
        with open(mf, "r", encoding="utf-8") as f:
            b64_payload = f.read().strip()
        updates.extend(parser.handle_ws_frame(b64_payload))
    all_normalized_updates.extend(normalizer.normalize_batch(updates))

    # --- FanDuel ---
    print("Normalizing FanDuel...")
    parser = FanDuelParser()
    ref_path = os.path.join(FIXTURES_DIR, "fanduel", "fanduel_messages", "json_1.json")
    with open(ref_path, "r", encoding="utf-8") as f:
        d = json.load(f)
        parser.handle_http_body("content-managed-page", json.dumps(d.get("data", d)))
        
    updates = []
    msg_dir = os.path.join(FIXTURES_DIR, "fanduel", "fanduel_messages")
    msg_files = glob.glob(os.path.join(msg_dir, "ws_*.txt"))
    msg_files.sort(key=lambda x: int(os.path.basename(x)[3:-4]))
    for mf in msg_files:
        with open(mf, "r", encoding="utf-8") as f:
            d = json.load(f)
            msg_body = json.dumps(d.get("data", d))
        updates.extend(parser.handle_http_body("https://smp.on.sportsbook.fanduel.ca/api/sports/fixedodds/readonly/v1/getMarketPrices?priceHistory=1", msg_body))
    all_normalized_updates.extend(normalizer.normalize_batch(updates))

    # --- BetMGM ---
    print("Normalizing BetMGM...")
    parser = BetMGMParser()
    json_files = glob.glob(os.path.join(FIXTURES_DIR, "betmgm", "betmgm_messages", "json_*.json"))
    for ref_path in json_files:
        with open(ref_path, "r", encoding="utf-8") as f:
            d = json.load(f)
            parser.handle_http_body("fixture-view", json.dumps(d.get("data", d)))
        
    updates = []
    msg_files = glob.glob(os.path.join(FIXTURES_DIR, "betmgm", "betmgm_messages", "ws_*.txt"))
    msg_files.sort(key=lambda x: int(os.path.basename(x)[3:-4]))
    for mf in msg_files:
        with open(mf, "r", encoding="utf-8") as f:
            raw = f.read().strip()
        updates.extend(parser.handle_ws_frame(raw + "\x1e"))
    all_normalized_updates.extend(normalizer.normalize_batch(updates))

    # --- Betano ---
    print("Normalizing Betano...")
    parser = BetanoParser()
    ref_path = os.path.join(FIXTURES_DIR, "betano", "betano_messages", "json_1.json")
    with open(ref_path, "r", encoding="utf-8") as f:
        d = json.load(f)
        parser.handle_http_body("https://www.betano.ca/danae-webapi/api/live/overview/1", json.dumps(d.get("data", d)))
        
    updates = []
    msg_files = glob.glob(os.path.join(FIXTURES_DIR, "betano", "betano_messages", "ws_*.txt"))
    msg_files.sort(key=lambda x: int(os.path.basename(x)[3:-4]))
    for mf in msg_files:
        with open(mf, "r", encoding="utf-8") as f:
            raw = f.read().strip()
        parsed = parser.handle_ws_frame(raw + "\x1e")
        for p in parsed:
            if p.raw_league_name == "1662":
                updates.append(p)
    all_normalized_updates.extend(normalizer.normalize_batch(updates))

    # --- Caesars ---
    print("Normalizing Caesars...")
    parser = CaesarsParser()
    json_files = glob.glob(os.path.join(FIXTURES_DIR, "caesars", "messages", "json_*.json"))
    for jf in json_files:
        with open(jf, "r", encoding="utf-8") as f:
            parser.handle_http_body("https://api.americanwagering.com/v4/home", f.read())
        
    updates = []
    msg_files = glob.glob(os.path.join(FIXTURES_DIR, "caesars", "messages", "ws_*.txt"))
    msg_files.sort(key=lambda x: int(os.path.basename(x)[3:-4]))
    for mf in msg_files:
        with open(mf, "r", encoding="utf-8") as f:
            b64_payload = f.read().strip()
        updates.extend(parser.handle_ws_frame(b64_payload))
    all_normalized_updates.extend(normalizer.normalize_batch(updates))

    # --- Write Outputs ---
    updates_path = os.path.join(OUTPUTS_DIR, "normalized_messages_output.txt")
    
    print("Writing text formatted NormalizedOddsUpdates to:", updates_path)
    with open(updates_path, "w", encoding="utf-8") as f:
        # Header
        f.write(
            f"{'BOOK':<10} | {'SPORT':<10} | {'LEAGUE':<20} | {'START_TIME':<25} | "
            f"{'EVENT_ID':<20} | {'HOME TEAM':<25} | {'AWAY TEAM':<25} | "
            f"{'MARKET':<30} | {'SELECTION':<30} | {'LINE':<6} | "
            f"{'ODDS':<8} | {'CAPTURED_AT'}\n"
        )
        f.write("-" * 250 + "\n")
        for u in all_normalized_updates:
            line_str = str(u.line) if u.line is not None else ""
            if isinstance(u.odds, float):
                price_str = f"{u.odds:.3f}"
            else:
                price_str = str(u.odds)
            
            sport = str(u.sport_key)[:10]
            league = str(u.league_key)[:20]
            start = str(u.start_time)[:25]
            ev_id = str(u.book_event_id)[:20]
            home = str(u.home_team)[:25]
            away = str(u.away_team)[:25]
            market = str(u.market_type)[:30]
            sel = str(u.selection)[:30]
            cap = u.captured_at.isoformat()
            
            f.write(
                f"{u.book_id:<10} | {sport:<10} | {league:<20} | {start:<25} | "
                f"{ev_id:<20} | {home:<25} | {away:<25} | "
                f"{market:<30} | {sel:<30} | {line_str:<6} | "
                f"{price_str:<8} | {cap}\n"
            )

    print(f"\nDone! Generated {len(all_normalized_updates)} total normalized updates.")

if __name__ == "__main__":
    main()
