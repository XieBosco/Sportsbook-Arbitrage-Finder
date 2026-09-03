import json
import os
from datetime import datetime, timezone
from arbfinder.parsers.betmgm import BetMGMParser
from arbfinder.normalization.book_normalizers.betmgm_normalizer import BetMGMNormalizer
from arbfinder.parsers.caesars import CaesarsParser
from arbfinder.normalization.book_normalizers.caesars_normalizer import CaesarsNormalizer
import sys
sys.path.insert(0, os.path.abspath('src'))

with open('scripts/data2/timeline.jsonl', 'r') as f:
    events = [json.loads(line) for line in f]

betmgm_parser = BetMGMParser()
caesars_parser = CaesarsParser()
betmgm_norm = BetMGMNormalizer()
caesars_norm = CaesarsNormalizer()

for e in events:
    dt = datetime.fromtimestamp(e['timestamp'], timezone.utc)
    if not (datetime(2026, 8, 30, 4, 8, 50, tzinfo=timezone.utc) <= dt <= datetime(2026, 8, 30, 4, 10, 10, tzinfo=timezone.utc)):
        continue
    sb = e['sportsbook']
    if sb not in ['caesars', 'betmgm']:
        continue
    
    msg_dir = 'messages' if sb == 'caesars' else f'{sb}_messages'
    fpath = os.path.join('scripts', 'data2', sb, msg_dir, e['file_name'])
    
    parser = betmgm_parser if sb == 'betmgm' else caesars_parser
    norm = betmgm_norm if sb == 'betmgm' else caesars_norm
    
    updates = []
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            if e['file_type'] == 'json':
                d = json.load(f)
                payload = d.get('data', d)
                url = d.get('_DEBUG_URL', 'https://api.americanwagering.com/v4/home' if sb == 'caesars' else 'fixture-view')
                updates = parser.handle_http_body(url, json.dumps(payload) if not isinstance(payload, str) else payload)
            else:
                content = f.read().strip()
                if sb == 'betmgm': content += '\x1e'
                updates = parser.handle_ws_frame(content)
    except Exception:
        continue
        
    for u in updates:
        n = norm.normalize(u)
        if n and n.market_type == 'run_line' and ('Phillies' in n.home_team or 'Angels' in n.home_team or 'Philadelphia' in n.away_team):
            print(f"[{dt.time()}] {sb.upper()} update: {n.home_team} vs {n.away_team} | {n.selection} {n.line} @ {n.odds_decimal}")
