"""Map aliases to UUIDs by extracting 'id' from the decoded CBOR objects, 
then cross-ref with subscription paths."""
import base64, os, struct, json, zlib

LOG_DIR = r"c:\Users\fiona\Desktop\arbitrage_tool\caesars_workspace\caesars_full_logs"

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

# Build alias -> CBOR object map (same as scratch_decode.py)
alias_cbor = {}  # alias_hex -> raw cbor bytes
alias_obj = {}   # alias_hex -> decoded dict
alias_source = {} # alias_hex -> ws_N where it was defined

# From Type 0x84 (compressed)
for n in range(1, 552):
    fpath = os.path.join(LOG_DIR, f"ws_{n}.txt")
    if not os.path.exists(fpath): continue
    d = read_ws(n)
    if d[0] == 0x84:
        for i in range(2, len(d)):
            if d[i] == 0x78 and i+1 < len(d) and d[i+1] in (0x01,):
                alias_key = d[2:i].hex()
                try:
                    decompressed = zlib.decompress(d[i:])
                    alias_cbor[alias_key] = decompressed
                    obj, _ = decode_cbor_item(decompressed, 0)
                    alias_obj[alias_key] = obj
                    alias_source[alias_key] = n
                except: pass
                break

# From Type 4 (uncompressed)
for n in range(1, 552):
    fpath = os.path.join(LOG_DIR, f"ws_{n}.txt")
    if not os.path.exists(fpath): continue
    d = read_ws(n)
    if d[0] == 0x04:
        for cbor_start in range(3, min(10, len(d))):
            try:
                obj, end_pos = decode_cbor_item(d, cbor_start)
                if isinstance(obj, dict) and end_pos == len(d):
                    alias_key = d[2:cbor_start].hex()
                    alias_cbor[alias_key] = d[cbor_start:]
                    alias_obj[alias_key] = obj
                    alias_source[alias_key] = n
                    break
            except: continue

print(f"Total aliases with decoded objects: {len(alias_obj)}")

# Now extract 'id' field from each decoded object
print("\n=== Alias -> ID mapping from CBOR objects ===")
alias_to_id = {}
for alias_key, obj in sorted(alias_obj.items()):
    obj_id = obj.get('id', None)
    if obj_id:
        alias_to_id[alias_key] = obj_id
        print(f"  alias={alias_key} (ws_{alias_source[alias_key]}): id={obj_id}")
    else:
        print(f"  alias={alias_key} (ws_{alias_source[alias_key]}): NO 'id' field. Keys: {list(obj.keys())[:10]}")

print(f"\nAliases with 'id': {len(alias_to_id)} / {len(alias_obj)}")

# Now parse subscription paths to get the UUIDs
sub_paths = {}  # n -> path
for n in range(1, 552):
    fpath = os.path.join(LOG_DIR, f"ws_{n}.txt")
    if not os.path.exists(fpath): continue
    d = read_ws(n)
    if len(d) == 0 or d[0] != 0x00: continue
    be_idx = d.find(b'BE/')
    if be_idx == -1: continue
    path_start = be_idx
    path_end = path_start
    while path_end < len(d) and 32 <= d[path_end] < 127:
        path_end += 1
    path = d[path_start:path_end].decode('ascii')
    sub_paths[n] = path

# Parse paths into components
print("\n=== Subscription paths with UUIDs ===")
selection_paths = {}  # selectionId -> {eventId, marketId}
market_paths = {}     # marketId -> eventId
event_paths = {}      # eventId -> path

for n, path in sorted(sub_paths.items()):
    parts = path.split('/')
    # BE/wh-ca-on/{eventId} -> depth 3
    # BE/wh-ca-on/v2/{eventId}/{marketId} -> depth 5
    # BE/wh-ca-on/{eventId}/{marketId}/{selectionId} -> depth 5 (no v2)
    if len(parts) == 3:
        event_id = parts[2]
        event_paths[event_id] = path
    elif len(parts) == 5 and parts[2] == 'v2':
        # market-level: BE/wh-ca-on/v2/{eventId}/{marketId}
        event_id = parts[3]
        market_id = parts[4]
        market_paths[market_id] = event_id
    elif len(parts) == 5 and parts[2] != 'v2':
        # selection-level: BE/wh-ca-on/{eventId}/{marketId}/{selectionId}
        event_id = parts[2]
        market_id = parts[3]
        selection_id = parts[4]
        selection_paths[selection_id] = {'eventId': event_id, 'marketId': market_id}

print(f"Events: {len(event_paths)}")
print(f"Markets: {len(market_paths)}")
print(f"Selections: {len(selection_paths)}")

# Now cross-reference: for each alias with an 'id', check if that id appears in the paths
print("\n=== Cross-referencing alias IDs with subscription paths ===")
alias_to_uuid_info = {}
for alias_key, obj_id in alias_to_id.items():
    if obj_id in selection_paths:
        info = selection_paths[obj_id]
        alias_to_uuid_info[alias_key] = {
            'type': 'selection',
            'selectionId': obj_id,
            'marketId': info['marketId'],
            'eventId': info['eventId']
        }
        print(f"  alias={alias_key}: SELECTION {obj_id}")
    elif obj_id in market_paths:
        alias_to_uuid_info[alias_key] = {
            'type': 'market',
            'marketId': obj_id,
            'eventId': market_paths[obj_id]
        }
        print(f"  alias={alias_key}: MARKET {obj_id}")
    elif obj_id in event_paths:
        alias_to_uuid_info[alias_key] = {
            'type': 'event',
            'eventId': obj_id
        }
        print(f"  alias={alias_key}: EVENT {obj_id}")
    else:
        print(f"  alias={alias_key}: id={obj_id} NOT FOUND in any subscription path")

print(f"\nMapped: {len(alias_to_uuid_info)} / {len(alias_to_id)}")

# Also check: do we have alias objects WITHOUT an 'id' field?
no_id = [k for k in alias_obj if k not in alias_to_id]
if no_id:
    print(f"\nAliases without 'id' field: {no_id}")
    for k in no_id[:3]:
        print(f"  {k}: keys={list(alias_obj[k].keys())[:15]}")
        print(f"  {k}: values sample={json.dumps(alias_obj[k], default=str)[:200]}")
