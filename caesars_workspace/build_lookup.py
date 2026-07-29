"""Build the selectionId -> {name, market_name, line, event_name} lookup from json_5.json."""
import json, os

LOG_DIR = r"c:\Users\fiona\Desktop\arbitrage_tool\caesars_workspace\caesars_full_logs"
data = json.load(open(os.path.join(LOG_DIR, "json_5.json")))
home = data['data']

# Build lookup: selectionId -> enrichment info
selection_lookup = {}
market_lookup = {}
event_lookup = {}

for edg in home.get('eventDisplayGroups', []):
    for event in edg.get('events', []):
        event_id = event.get('id')
        event_name = event.get('name', '')
        event_lookup[event_id] = {'name': event_name}
        
        # keyMarketGroups is a list
        for group in event.get('keyMarketGroups', []):
            if not isinstance(group, dict):
                continue
            for market in group.get('markets', []):
                market_id = market.get('id')
                market_name = market.get('name', '')
                market_line = market.get('line', None)
                market_lookup[market_id] = {
                    'name': market_name,
                    'line': market_line,
                    'eventId': event_id,
                    'event_name': event_name
                }
                
                for sel in market.get('selections', []):
                    sel_id = sel.get('id')
                    sel_name = sel.get('name', '')
                    sel_price = sel.get('price', {})
                    selection_lookup[sel_id] = {
                        'name': sel_name,
                        'market_name': market_name,
                        'market_line': market_line,
                        'event_name': event_name,
                        'eventId': event_id,
                        'marketId': market_id,
                        'initial_price': sel_price
                    }

print(f"Events: {len(event_lookup)}")
print(f"Markets: {len(market_lookup)}")
print(f"Selections: {len(selection_lookup)}")

# Show a few examples
print("\n=== Sample selection entries ===")
for sel_id, info in list(selection_lookup.items())[:5]:
    print(f"\n  selectionId: {sel_id}")
    print(f"    name: {info['name']}")
    print(f"    market_name: {info['market_name']}")
    print(f"    market_line: {info['market_line']}")
    print(f"    event_name: {info['event_name']}")
    print(f"    initial_price: {info['initial_price']}")

# Check: how many of our decoded aliases have matching selections in json_5?
# Load the alias->id map from previous script
import base64, struct, zlib

def read_ws(n):
    with open(os.path.join(LOG_DIR, f"ws_{n}.txt"), 'r') as f:
        return base64.b64decode(f.read().strip())

def decode_cbor_item(data, pos):
    if pos >= len(data):
        raise ValueError(f"EOF at {pos}")
    initial = data[pos]
    major = (initial >> 5) & 0x07
    additional = initial & 0x1f
    pos += 1
    if additional < 24: arg = additional
    elif additional == 24: arg = data[pos]; pos += 1
    elif additional == 25: arg = struct.unpack('>H', data[pos:pos+2])[0]; pos += 2
    elif additional == 26: arg = struct.unpack('>I', data[pos:pos+4])[0]; pos += 4
    elif additional == 27: arg = struct.unpack('>Q', data[pos:pos+8])[0]; pos += 8
    else: raise ValueError(f"Unsupported additional={additional}")
    if major == 0: return arg, pos
    elif major == 1: return -1 - arg, pos
    elif major == 2: return data[pos:pos+arg], pos + arg
    elif major == 3: return data[pos:pos+arg].decode('utf-8', errors='replace'), pos + arg
    elif major == 4:
        arr = []
        for _ in range(arg): item, pos = decode_cbor_item(data, pos); arr.append(item)
        return arr, pos
    elif major == 5:
        m = {}
        for _ in range(arg): k, pos = decode_cbor_item(data, pos); v, pos = decode_cbor_item(data, pos); m[k] = v
        return m, pos
    elif major == 7:
        if additional == 20: return False, pos
        elif additional == 21: return True, pos
        elif additional == 22: return None, pos
        elif additional == 25:
            raw = struct.unpack('>H', data[pos-2:pos])[0]
            sign = (raw >> 15) & 1; exp = (raw >> 10) & 0x1f; frac = raw & 0x3ff
            if exp == 0: val = (-1)**sign * 2**(-14) * (frac / 1024.0)
            elif exp == 31: val = float('inf') if frac == 0 else float('nan'); val = -val if sign else val
            else: val = (-1)**sign * 2**(exp-15) * (1 + frac/1024.0)
            return val, pos
        elif additional == 26: return struct.unpack('>f', data[pos-4:pos])[0], pos
        elif additional == 27: return struct.unpack('>d', data[pos-8:pos])[0], pos
        else: raise ValueError(f"Unknown simple {additional}")
    raise ValueError(f"Unknown major {major}")

# Get all alias IDs
alias_ids = set()
# From Type 0x84
for n in range(1, 552):
    fpath = os.path.join(LOG_DIR, f"ws_{n}.txt")
    if not os.path.exists(fpath): continue
    d = read_ws(n)
    if d[0] == 0x84:
        for i in range(2, len(d)):
            if d[i] == 0x78 and i+1 < len(d) and d[i+1] in (0x01,):
                try:
                    decompressed = zlib.decompress(d[i:])
                    obj, _ = decode_cbor_item(decompressed, 0)
                    if isinstance(obj, dict) and 'id' in obj:
                        alias_ids.add(obj['id'])
                except: pass
                break
# From Type 0x04
for n in range(1, 552):
    fpath = os.path.join(LOG_DIR, f"ws_{n}.txt")
    if not os.path.exists(fpath): continue
    d = read_ws(n)
    if d[0] == 0x04:
        for cbor_start in range(3, min(10, len(d))):
            try:
                obj, end_pos = decode_cbor_item(d, cbor_start)
                if isinstance(obj, dict) and end_pos == len(d) and 'id' in obj:
                    alias_ids.add(obj['id'])
                    break
            except: continue

# Check overlap
sel_ids_in_aliases = alias_ids & set(selection_lookup.keys())
market_ids_in_aliases = alias_ids & set(market_lookup.keys())
event_ids_in_aliases = alias_ids & set(event_lookup.keys())
unmapped = alias_ids - set(selection_lookup.keys()) - set(market_lookup.keys()) - set(event_lookup.keys())

print(f"\n=== Alias IDs found in json_5.json ===")
print(f"  Selection matches: {len(sel_ids_in_aliases)}")
print(f"  Market matches: {len(market_ids_in_aliases)}")
print(f"  Event matches: {len(event_ids_in_aliases)}")
print(f"  Unmapped: {len(unmapped)}")
if unmapped:
    print(f"  Unmapped IDs: {sorted(unmapped)[:10]}")
