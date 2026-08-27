"""Script to run parsers against fixtures and dump outputs for manual review."""

import base64
import glob
import json
import os
import msgpack
from dataclasses import asdict
from datetime import datetime

from arbfinder.parsers.betano import BetanoParser
from arbfinder.parsers.betmgm import BetMGMParser
from arbfinder.parsers.caesars import CaesarsParser
from arbfinder.parsers.draftkings import DraftKingsParser
from arbfinder.parsers.fanduel import FanDuelParser

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")
OUTPUTS_DIR = os.path.dirname(__file__)


def datetime_handler(x):
    if isinstance(x, datetime):
        return x.isoformat()
    raise TypeError("Unknown type")


def main():
    all_updates = []
    all_refs = {}

    # --- DraftKings ---
    print("Parsing DraftKings...")
    parser = DraftKingsParser()
    ref_path = os.path.join(FIXTURES_DIR, "draftkings", "draftkings_messages", "json_1.json")
    with open(ref_path, "r", encoding="utf-8") as f:
        d = json.load(f)
        parser.handle_http_body("api/sportscontent/v1/markets", json.dumps(d.get("data", d)))
    
    all_refs["DraftKings"] = parser.reference_data
    
    msg_files = sorted(glob.glob(os.path.join(FIXTURES_DIR, "draftkings", "draftkings_messages", "ws_*.txt")))
    for mf in msg_files:
        with open(mf, "r", encoding="utf-8") as f:
            b64_payload = f.read().strip()
        all_updates.extend(parser.handle_ws_frame(b64_payload))

    # --- FanDuel ---
    print("Parsing FanDuel...")
    parser = FanDuelParser()
    ref_path = os.path.join(FIXTURES_DIR, "fanduel", "fanduel_messages", "json_1.json")
    with open(ref_path, "r", encoding="utf-8") as f:
        d = json.load(f)
        parser.handle_http_body("content-managed-page", json.dumps(d.get("data", d)))
        
    all_refs["FanDuel"] = parser.reference_data
    
    msg_dir = os.path.join(FIXTURES_DIR, "fanduel", "fanduel_messages")
    msg_files = sorted(glob.glob(os.path.join(msg_dir, "ws_*.txt")))
    for mf in msg_files:
        with open(mf, "r", encoding="utf-8") as f:
            d = json.load(f)
            msg_body = json.dumps(d.get("data", d))
        all_updates.extend(parser.handle_http_body("https://smp.on.sportsbook.fanduel.ca/api/sports/fixedodds/readonly/v1/getMarketPrices?priceHistory=1", msg_body))

    # --- BetMGM ---
    print("Parsing BetMGM...")
    parser = BetMGMParser()
    ref_path = os.path.join(FIXTURES_DIR, "betmgm", "betmgm_messages", "json_1.json")
    with open(ref_path, "r", encoding="utf-8") as f:
        d = json.load(f)
        parser.handle_http_body("fixture-view", json.dumps(d.get("data", d)))
        
    all_refs["BetMGM"] = parser.reference_data
    
    msg_files = sorted(glob.glob(os.path.join(FIXTURES_DIR, "betmgm", "betmgm_messages", "ws_*.txt")))
    for mf in msg_files:
        with open(mf, "r", encoding="utf-8") as f:
            raw = f.read().strip()
        all_updates.extend(parser.handle_ws_frame(raw + "\x1e"))

    # --- Betano ---
    print("Parsing Betano...")
    parser = BetanoParser()
    ref_path = os.path.join(FIXTURES_DIR, "betano", "betano_messages", "json_1.json")
    with open(ref_path, "r", encoding="utf-8") as f:
        d = json.load(f)
        parser.handle_http_body("https://www.betano.ca/danae-webapi/api/live/overview/1", json.dumps(d.get("data", d)))
        
    all_refs["Betano"] = parser.reference_data
    
    msg_files = sorted(glob.glob(os.path.join(FIXTURES_DIR, "betano", "betano_messages", "ws_*.txt")))
    for mf in msg_files:
        with open(mf, "r", encoding="utf-8") as f:
            raw = f.read().strip()
        all_updates.extend(parser.handle_ws_frame(raw + "\x1e"))

    # --- Caesars ---
    print("Parsing Caesars...")
    parser = CaesarsParser()
    ref_path = os.path.join(FIXTURES_DIR, "caesars", "messages", "json_5.json")
    with open(ref_path, "r", encoding="utf-8") as f:
        parser.handle_http_body("https://api.americanwagering.com/v4/home", f.read())
        
    all_refs["Caesars"] = {
        "events": parser.reference_data["events"],
        "markets": parser.reference_data["markets"],
        "selections": parser.reference_data["selections"],
        "alias_uuid": dict(parser.store._id)
    }
    
    msg_files = sorted(glob.glob(os.path.join(FIXTURES_DIR, "caesars", "messages", "ws_*.txt")))
    for mf in msg_files:
        with open(mf, "r", encoding="utf-8") as f:
            b64_payload = f.read().strip()
        all_updates.extend(parser.handle_ws_frame(b64_payload))

    # --- Write Outputs ---
    updates_path = os.path.join(OUTPUTS_DIR, "parsed_messages_output.txt")
    refs_path = os.path.join(OUTPUTS_DIR, "parsed_reference_dicts.json")
    
    print("Writing text formatted OddsUpdates to:", updates_path)
    with open(updates_path, "w", encoding="utf-8") as f:
        # Header
        f.write(
            f"{'BOOK':<10} | {'SPORT':<10} | {'LEAGUE':<20} | {'START_TIME':<25} | "
            f"{'EVENT_ID':<20} | {'HOME TEAM':<25} | {'AWAY TEAM':<25} | "
            f"{'MARKET':<30} | {'SELECTION':<30} | {'LINE':<6} | "
            f"{'ODDS':<8} | {'FMT':<6} | {'CAPTURED_AT'}\n"
        )
        f.write("-" * 250 + "\n")
        for u in all_updates:
            line_str = str(u.raw_line) if u.raw_line is not None else ""
            price_str = str(u.odds_value) if u.odds_value is not None else ""
            
            sport = str(u.raw_sport_code)[:10]
            league = str(u.raw_league_name)[:20]
            start = str(u.raw_start_time)[:25]
            ev_id = str(u.raw_event_id)[:20]
            home = str(u.raw_home_team)[:25]
            away = str(u.raw_away_team)[:25]
            market = str(u.raw_market_type)[:30]
            sel = str(u.raw_selection)[:30]
            fmt = str(u.odds_format)[:8]
            cap = u.captured_at.isoformat()
            
            f.write(
                f"{u.book_id:<10} | {sport:<10} | {league:<20} | {start:<25} | "
                f"{ev_id:<20} | {home:<25} | {away:<25} | "
                f"{market:<30} | {sel:<30} | {line_str:<6} | "
                f"{price_str:<8} | {fmt:<6} | {cap}\n"
            )

    print("Writing full JSON reference dictionaries to:", refs_path)
    with open(refs_path, "w", encoding="utf-8") as f:
        json.dump(all_refs, f, indent=4, default=datetime_handler)
        
    print(f"\nDone! Generated {len(all_updates)} total updates.")

if __name__ == "__main__":
    main()
