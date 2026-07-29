import json, os

LOG_DIR = r"c:\Users\fiona\Desktop\arbitrage_tool\caesars_workspace\caesars_full_logs"

data = json.load(open(os.path.join(LOG_DIR, "json_5.json")))
home = data['data']

edg = home['eventDisplayGroups']
ev = edg[0]['events'][0]
print(f"Event: {ev['name']} (id={ev['id']})")

kmg = ev.get('keyMarketGroups', [])
print(f"keyMarketGroups type: {type(kmg).__name__}, len={len(kmg)}")

if isinstance(kmg, list) and len(kmg) > 0:
    for gi, group in enumerate(kmg[:3]):
        print(f"\n--- Group {gi} ---")
        print(f"  Type: {type(group).__name__}")
        if isinstance(group, dict):
            print(f"  Keys: {list(group.keys())[:20]}")
            print(f"  name: {group.get('name','?')}")
            if 'markets' in group:
                markets = group['markets']
                print(f"  markets count: {len(markets)}")
                for mi, m in enumerate(markets[:2]):
                    print(f"\n    Market {mi}: name={m.get('name','?')}, id={m.get('id','?')}")
                    print(f"    keys: {list(m.keys())[:20]}")
                    if 'line' in m:
                        print(f"    line: {m.get('line')}")
                    if 'selections' in m:
                        for s in m['selections'][:4]:
                            print(f"      Sel: id={s.get('id','?')}, name={s.get('name','?')}, price={s.get('price','?')}")
                            print(f"        keys: {list(s.keys())[:15]}")
