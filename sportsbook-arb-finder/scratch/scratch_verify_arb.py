import json
import os
from datetime import datetime, timezone

# We'll use the normalizers to parse the raw files mentioned in the timeline
from arbfinder.parsers.betmgm import BetMGMParser
from arbfinder.parsers.caesars import CaesarsParser
from arbfinder.normalization.book_normalizers.betmgm_normalizer import BetMGMNormalizer
from arbfinder.normalization.book_normalizers.caesars_normalizer import CaesarsNormalizer

with open('scripts/data2/timeline.jsonl', 'r') as f:
    timeline = [json.loads(line) for line in f]

betmgm_parser = BetMGMParser()
caesars_parser = CaesarsParser()
betmgm_norm = BetMGMNormalizer()
caesars_norm = CaesarsNormalizer()

print("Scanning for BetMGM/Caesars updates on Baltimore @ Oakland total 6.5...")
for event in timeline:
    dt = datetime.fromtimestamp(event['timestamp'], timezone.utc)
    if not (datetime(2026, 8, 30, 3, 13, 0, tzinfo=timezone.utc) <= dt <= datetime(2026, 8, 30, 3, 15, 0, tzinfo=timezone.utc)):
        continue
        
    sb = event["sportsbook"]
    if sb not in ["betmgm", "caesars"]:
        continue
        
    msg_dir = "messages" if sb == "caesars" else f"{sb}_messages"
    fpath = os.path.join('scripts', 'data2', sb, msg_dir, event["file_name"])
    
    parser = betmgm_parser if sb == "betmgm" else caesars_parser
    norm = betmgm_norm if sb == "betmgm" else caesars_norm
    
    updates = []
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            if event["file_type"] == "json":
                d = json.load(f)
                payload = d.get("data", d)
                url = d.get("_DEBUG_URL", "https://api.americanwagering.com/v4/home" if sb == "caesars" else "fixture-view")
                updates = parser.handle_http_body(url, json.dumps(payload) if not isinstance(payload, str) else payload)
            else:
                content = f.read().strip()
                if sb == "betmgm": content += "\x1e"
                updates = parser.handle_ws_frame(content)
    except Exception:
        continue
        
    for u in updates:
        n = norm.normalize(u)
        if n and n.home_team == "Oakland Athletics" and n.market_type == "total" and n.line == 6.5:
            print(f"[{dt.time()}] {sb.upper()} update: {n.selection} {n.line} @ {n.odds_decimal}")
