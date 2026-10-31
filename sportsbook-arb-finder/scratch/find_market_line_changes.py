import json, os, sys
sys.path.insert(0, os.path.abspath('src'))
sys.path.insert(0, os.path.abspath('tests/test_scanner'))
from test_replay import get_parser
cz = get_parser('caesars')

with open('scripts/nhl_data/timeline.jsonl', 'r') as f:
    for i, line in enumerate(f):
        ev = json.loads(line)
        if ev['sportsbook'] != 'caesars': continue
        fn = ev['file_name']
        ft = ev['file_type']
        fpath = f'scripts/nhl_data/caesars/messages/{fn}'
        with open(fpath, 'r', encoding='utf-8') as mf: raw = mf.read().strip()
        if ft == 'json':
            d = json.loads(raw)
            payload = d.get('data', d) if isinstance(d, dict) else d
            url = d.get('_DEBUG_URL', '') if isinstance(d, dict) else ''
            cz.handle_http_body(url, json.dumps(payload) if not isinstance(payload, str) else payload)
        else:
            old_lines = {m: cz.reference_data['markets'][m].get('handicap') for m in cz.reference_data['markets']}
            cz.handle_ws_frame(raw)
            new_lines = {m: cz.reference_data['markets'][m].get('handicap') for m in cz.reference_data['markets']}
            for m in old_lines:
                if old_lines[m] != new_lines[m]:
                    m_name = cz.reference_data['markets'][m]['name']
                    print(f'{fn} changed market {m} ({m_name}) line from {old_lines[m]} to {new_lines[m]}')
