"""Quick check: do selection CBOR objects contain marketId or eventId?"""
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

# Check a known selection alias (bd9bf767 from ws_12)
d = read_ws(12)
obj, _ = decode_cbor_item(d, 5)  # skip 5-byte header for type 0x04
print("ws_12 (selection) keys:", sorted(obj.keys()))
print("ws_12 (selection):", json.dumps(obj, default=str))

# Check a known market alias (e5cdb5)
for n in range(1, 552):
    fpath = os.path.join(LOG_DIR, f"ws_{n}.txt")
    if not os.path.exists(fpath): continue
    d = read_ws(n)
    if d[0] == 0x84:
        for i in range(2, len(d)):
            if d[i] == 0x78 and i+1 < len(d) and d[i+1] in (0x01,):
                alias = d[2:i].hex()
                if alias == 'e5cdb5':
                    decompressed = zlib.decompress(d[i:])
                    obj, _ = decode_cbor_item(decompressed, 0)
                    print(f"\nMarket (e5cdb5) keys: {sorted(obj.keys())}")
                    print(f"Market: {json.dumps(obj, default=str)}")
                break

# Check an event alias (e22a4b)
for n in range(1, 552):
    fpath = os.path.join(LOG_DIR, f"ws_{n}.txt")
    if not os.path.exists(fpath): continue
    d = read_ws(n)
    if d[0] == 0x84:
        for i in range(2, len(d)):
            if d[i] == 0x78 and i+1 < len(d) and d[i+1] in (0x01,):
                alias = d[2:i].hex()
                if alias == 'e22a4b':
                    decompressed = zlib.decompress(d[i:])
                    obj, _ = decode_cbor_item(decompressed, 0)
                    print(f"\nEvent (e22a4b) keys: {sorted(obj.keys())}")
                    print(f"Event: {json.dumps(obj, default=str)}")
                break
