"""Validate decoded_odds.json against the hand-verified examples from handoff.md."""
import json

with open(r"c:\Users\fiona\Desktop\arbitrage_tool\caesars_workspace\decoded_odds.json") as f:
    records = json.load(f)

# Build lookup by ws_file number
by_ws = {r['ws_file']: r for r in records}

print("=== Validation against hand-verified examples ===\n")

# ws_508: selection bd9bf767, price should change to {a: -200, d: 1.5, f: "1/2"}
print("--- ws_508 ---")
r = by_ws.get(508)
if r:
    print(f"  type: {r['type']}")
    print(f"  id: {r['id']}")
    print(f"  name: {r.get('name', 'N/A')}")
    print(f"  market_name: {r.get('market_name', 'N/A')}")
    print(f"  event_name: {r.get('event_name', 'N/A')}")
    print(f"  decoded price: {r['decoded'].get('price', 'N/A')}")
    assert r['id'] == 'bd9bf767-a588-31d9-b297-215f9ff45921', "Wrong ID!"
    assert r['decoded']['price']['a'] == -200, f"Wrong price.a: {r['decoded']['price']['a']}"
    assert r['decoded']['price']['f'] == '1/2', f"Wrong price.f: {r['decoded']['price']['f']}"
    print("  [OK] PASS")
else:
    print("  [FAIL] MISSING")

# ws_454: selection bd9bf767, price should be {a: 137, d: 2.37, f: "11/8"}, state: "open"
print("\n--- ws_454 ---")
r = by_ws.get(454)
if r:
    print(f"  type: {r['type']}")
    print(f"  id: {r['id']}")
    print(f"  name: {r.get('name', 'N/A')}")
    print(f"  decoded price: {r['decoded'].get('price', 'N/A')}")
    print(f"  decoded state: {r['decoded'].get('state', 'N/A')}")
    assert r['id'] == 'bd9bf767-a588-31d9-b297-215f9ff45921', "Wrong ID!"
    assert r['decoded']['price']['a'] == 137, f"Wrong price.a: {r['decoded']['price']['a']}"
    assert r['decoded']['state'] == 'open', f"Wrong state: {r['decoded']['state']}"
    print("  [OK] PASS")
else:
    print("  [FAIL] MISSING")

# ws_395: market fa50d853, should have line field that changed (originally 5.5 → 6.5)
print("\n--- ws_395 ---")
r = by_ws.get(395)
if r:
    print(f"  type: {r['type']}")
    print(f"  id: {r['id']}")
    print(f"  event_name: {r.get('event_name', 'N/A')}")
    print(f"  decoded line: {r['decoded'].get('line', 'N/A')}")
    print(f"  decoded name: {r['decoded'].get('name', 'N/A')}")
    assert r['id'] == 'fa50d853-b0a2-3f96-945f-23768eaedfec', "Wrong ID!"
    assert r['decoded']['line'] == 6.5, f"Wrong line: {r['decoded']['line']}"
    print("  [OK] PASS")
else:
    print("  [FAIL] MISSING")

# ws_398: event 8e767a58, should have active=false
print("\n--- ws_398 ---")
r = by_ws.get(398)
if r:
    print(f"  type: {r['type']}")
    print(f"  id: {r['id']}")
    print(f"  event_name: {r.get('event_name', 'N/A')}")
    print(f"  decoded active: {r['decoded'].get('active', 'N/A')}")
    assert r['id'] == '8e767a58-7f55-4521-9e53-92b01a3add69', "Wrong ID!"
    assert r['decoded']['active'] == False, f"Wrong active: {r['decoded']['active']}"
    print("  [OK] PASS")
else:
    print("  [FAIL] MISSING")

print("\n=== Summary statistics ===")
type_counts = {}
for r in records:
    t = r['type']
    type_counts[t] = type_counts.get(t, 0) + 1
print(f"  Records by type: {type_counts}")

enriched = sum(1 for r in records if 'name' in r or 'event_name' in r)
print(f"  Enriched records: {enriched} / {len(records)}")

# Check chronological ordering
ws_numbers = [r['ws_file'] for r in records]
assert ws_numbers == sorted(ws_numbers), "Records are NOT in chronological order!"
print(f"  Chronological order: OK")
print(f"  First: ws_{ws_numbers[0]}, Last: ws_{ws_numbers[-1]}")
