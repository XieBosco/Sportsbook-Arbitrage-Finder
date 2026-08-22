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
    ref_path = os.path.join(FIXTURES_DIR, "fanduel", "example_reference_dictionary_fanduel.json")
    with open(ref_path, "r", encoding="utf-8") as f:
        parser.handle_http_body("content-managed-page", f.read())
        
    all_refs["FanDuel"] = parser.reference_data
    
    msg_path = os.path.join(FIXTURES_DIR, "fanduel", "messages", "fanduel_message1.json")
    with open(msg_path, "r", encoding="utf-8") as f:
        msg_body = f.read()
    all_updates.extend(parser.handle_http_body("https://sbapi.on.sportsbook.fanduel.ca/api/getMarketPrices", msg_body))

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
        f.write(f"{'BOOK':<12} | {'EVENT_ID':<25} | {'HOME TEAM':<30} | {'AWAY TEAM':<30} | {'MARKET':<30} | {'SELECTION':<35} | {'LINE':<6} | {'PRICE':<6}\n")
        f.write("-" * 187 + "\n")
        for u in all_updates:
            line_str = str(u.line) if u.line is not None else ""
            price_str = str(u.price_american) if u.price_american is not None else ""
            
            ev_id = str(u.event_id)[:25]
            home = str(u.home_team)[:30]
            away = str(u.away_team)[:30]
            market = str(u.market)[:30]
            sel = str(u.selection)[:35]
            
            f.write(f"{u.book:<12} | {ev_id:<25} | {home:<30} | {away:<30} | {market:<30} | {sel:<35} | {line_str:<6} | {price_str:<6}\n")

    print("Writing full JSON reference dictionaries to:", refs_path)
    with open(refs_path, "w", encoding="utf-8") as f:
        json.dump(all_refs, f, indent=4, default=datetime_handler)
        
    print(f"\nDone! Generated {len(all_updates)} total updates.")

if __name__ == "__main__":
    main()
