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


def apply_binary_delta(old_bytes, delta_data):
    """Apply Diffusion binary delta to old CBOR bytes.
    
    The delta format consists of alternating CBOR items:
    - int N: copy N bytes from old_bytes starting at old_pos, then advance old_pos by N
    - bytes B: insert B into the output, then advance old_pos by len(B)
    
    BUT: when the delta changes the size of a field, the next int after a bytes insert
    is a JUMP (absolute offset) rather than a copy count. We need to detect this.
    
    Actually - simpler theory: 
    The items ALWAYS alternate int, bytes, int, bytes, ..., int
    The first int = copy_count
    Then for each (bytes, int) pair:
        bytes = insert into output
        int = the new old_pos (absolute jump, NOT a copy)
    And the very last int = copy remaining bytes
    
    Wait, that doesn't work either for ws_508 which has: 59, bytes(13), 79, 11
    That's: copy(59), insert(13), jump(79), copy(11) -> output = 59+13+11=83 ✓
    old was 91, old[0:59] + insert + old[79:90] = 59+13+11=83
    """
    
    # Parse all items
    items = []
    pos = 0
    while pos < len(delta_data):
        item, pos = decode_cbor_item(delta_data, pos)
        items.append(item)
    
    # Theory: copy, [insert, jump]*, copy_final
    # = int, [bytes, int]*, int
    # Items for ws_508: 59, bytes(13), 79, 11
    #   -> copy(59), insert(13), jump_to(79), copy(11)
    # Items for ws_454: 60, bytes(1), 61, 5, bytes(13), 80, 11  
    #   -> copy(60), insert(1), jump_to(61), copy(5), insert(13), jump_to(80), copy(11)
    # So the pattern is: int(copy), [bytes(insert), int(jump), int(copy)]*, OR ends with int(copy)
    
    # Wait ws_454: 60, bytes(1), 61, 5, bytes(13), 80, 11
    # if: copy(60), insert(1), then remaining = 61, 5, bytes(13), 80, 11
    # Then: jump(61), copy(5), insert(13), jump(80), copy(11)
    # = [copy, insert, jump, copy, insert, jump, copy]
    # So: copy | {insert, jump, copy}*
    
    new_bytes = bytearray()
    old_pos = 0
    i = 0
    
    # First item: always a copy count
    if len(items) == 0:
        return old_bytes
    
    assert isinstance(items[0], int), f"First item must be int, got {type(items[0])}"
    copy_count = items[0]
    new_bytes.extend(old_bytes[old_pos:old_pos + copy_count])
    old_pos += copy_count
    i = 1
    
    while i < len(items):
        if isinstance(items[i], bytes):
            # INSERT
            new_bytes.extend(items[i])
            i += 1
            
            if i < len(items) and isinstance(items[i], int):
                # JUMP to old offset
                old_pos = items[i]
                i += 1
                
                if i < len(items) and isinstance(items[i], int):
                    # COPY
                    copy_count = items[i]
                    new_bytes.extend(old_bytes[old_pos:old_pos + copy_count])
                    old_pos += copy_count
                    i += 1
        elif isinstance(items[i], int):
            # This shouldn't happen if we parsed correctly
            print(f"WARNING: unexpected int at position {i}: {items[i]}")
            i += 1
    
    return bytes(new_bytes)

# Test with all examples
orig_12 = read_ws(12)[5:]  # Original CBOR for bd9bf767

# ws_508
delta508 = read_ws(508)
zero_pos = delta508.index(0x00, 2)
delta_data = delta508[zero_pos+1:]
new_value = apply_binary_delta(orig_12, delta_data)
result, _ = decode_cbor_item(new_value, 0)
print(f"ws_508: {json.dumps(result, default=str)}")

# ws_454
delta454 = read_ws(454)
zero_pos = delta454.index(0x00, 2)
delta_data = delta454[zero_pos+1:]
new_value = apply_binary_delta(orig_12, delta_data)
result, _ = decode_cbor_item(new_value, 0)
print(f"ws_454: {json.dumps(result, default=str)}")

# ws_395 - market
for n in range(1, 551):
    fpath = os.path.join(LOG_DIR, f"ws_{n}.txt")
    if not os.path.exists(fpath): continue
    d = read_ws(n)
    if d[0] == 0x84:
        for i in range(2, len(d)):
            if d[i] == 0x78 and i+1 < len(d) and d[i+1] in (0x01,):
                if d[2:i].hex() == 'e5cdb5':
                    orig_market = zlib.decompress(d[i:])
                    break

delta395 = read_ws(395)
zero_pos = delta395.index(0x00, 2)
delta_data = delta395[zero_pos+1:]
new_value = apply_binary_delta(orig_market, delta_data)
result, _ = decode_cbor_item(new_value, 0)
print(f"ws_395: {json.dumps(result, default=str)}")

# ws_398 - event
for n in range(1, 551):
    fpath = os.path.join(LOG_DIR, f"ws_{n}.txt")
    if not os.path.exists(fpath): continue
    d = read_ws(n)
    if d[0] == 0x84:
        for i in range(2, len(d)):
            if d[i] == 0x78 and i+1 < len(d) and d[i+1] in (0x01,):
                if d[2:i].hex() == 'e22a4b':
                    orig_event = zlib.decompress(d[i:])
                    break

delta398 = read_ws(398)
zero_pos = delta398.index(0x00, 2)
delta_data = delta398[zero_pos+1:]
new_value = apply_binary_delta(orig_event, delta_data)
result, _ = decode_cbor_item(new_value, 0)
print(f"ws_398: {json.dumps(result, default=str)}")

# Now test a bunch more deltas
print("\n=== Testing all Type 5 deltas ===")

# Build complete alias map with original CBOR bytes
alias_cbor = {}  # alias_hex -> original cbor bytes

# From Type 0x84 (compressed)
for n in range(1, 551):
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
                except: pass
                break

# From Type 4 (uncompressed)  
for n in range(1, 551):
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
                    break
            except: continue

print(f"Alias CBOR map: {len(alias_cbor)} entries")

# Now apply all Type 5 deltas
success = 0
fail = 0
total = 0
for n in range(1, 551):
    fpath = os.path.join(LOG_DIR, f"ws_{n}.txt")
    if not os.path.exists(fpath): continue
    d = read_ws(n)
    if d[0] != 0x05: continue
    total += 1
    
    zero_pos = d.index(0x00, 2)
    alias_key = d[2:zero_pos].hex()
    delta_data = d[zero_pos+1:]
    
    if alias_key not in alias_cbor:
        fail += 1
        continue
    
    old = alias_cbor[alias_key]
    try:
        new_value = apply_binary_delta(old, delta_data)
        result, end = decode_cbor_item(new_value, 0)
        if isinstance(result, dict) and end == len(new_value):
            success += 1
            # Update the alias_cbor for subsequent deltas
            alias_cbor[alias_key] = new_value
        else:
            fail += 1
            if fail <= 3:
                print(f"  ws_{n}: decoded but end={end} != len={len(new_value)}")
    except Exception as e:
        fail += 1
        if fail <= 3:
            print(f"  ws_{n}: ERROR: {e}")

print(f"\nResults: {success} success, {fail} fail, {total} total")
