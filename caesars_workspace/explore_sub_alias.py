"""Deep-dive into how aliases are assigned and how to link 0x00 subscriptions to Type 4/84 objects."""
import base64, os, struct, json, zlib

LOG_DIR = r"c:\Users\fiona\Desktop\arbitrage_tool\caesars_workspace\caesars_full_logs"

def read_ws(n):
    with open(os.path.join(LOG_DIR, f"ws_{n}.txt"), 'r') as f:
        return base64.b64decode(f.read().strip())

# Let's look at the raw bytes of 0x00 subscription messages more carefully
# Focus on identifying the alias bytes and the path string
print("=== Parsing 0x00 subscription messages ===")

def parse_sub_message(d):
    """Parse a 0x00 subscription message to extract alias and path."""
    # d[0] = 0x00 (type byte)
    # Then some structured data follows...
    # From the hex dumps:
    # 00 57 00 b3bea4 87 01 7a 42452f...
    # 00 is type, 57 is ???, 00 is separator, b3bea4 is alias candidate
    # But wait - maybe 57 is a length? 0x57 = 87 decimal
    # ws_5 hex: 005700b3bea487017a42452f...
    # Total len = 160, minus 2 header bytes = 158
    # 0x57 = 87 doesn't match 158
    
    # Let's look at what's between the type byte and the path
    # Find "BE/" in the bytes
    be_idx = d.find(b'BE/')
    if be_idx == -1:
        return None
    
    # Back up from BE/ to find the CBOR text header
    # CBOR text: 0x78 XX = text with 1-byte length, 0x79 XXXX = 2-byte length
    # 0x7a XXXXXXXX = 4-byte length
    # Path like "BE/wh-ca-on/..." is ~122 chars for selection, ~88 for market
    text_header = be_idx - 1  # simple case: text8 (0x78 + 1 byte len)
    if d[be_idx-1] == ord('z'):  # 0x7a = 4-byte length, but 'z'=0x7a hmm
        text_header = be_idx - 5  # 0x7a + 4 bytes length
    elif d[be_idx-1] == ord('X'):  # 0x58 = bytes with 1-byte length... no
        text_header = be_idx - 2  # 0x78 + 1 byte length
    
    # Actually let me just look at what 0x7a and 0x78 mean
    # In the hex: 7a42452f = 0x7a then "BE/" 
    # 0x7a is CBOR text with 4-byte length... but "BE" starts right after
    # Wait: 0x7a = major type 3 (text), additional info 26 = 4-byte length
    # So 0x7a XX XX XX XX then XX bytes of text
    # But "BE/" appears right at be_idx = d.find(b'BE/')
    # 7a 42 45 2f... = 0x7a then 0x42='B', 0x45='E', 0x2f='/'
    # That can't be right - 4-byte length would be 0x42452f?? = 1,111,687,935 chars
    # So it's NOT 0x7a
    
    # Let me just look at the byte before BE/
    # In ws_5: 7a42452f -> the byte before 'B' (0x42) is 0x7a
    # 0x7a as CBOR: major 3 (text), additional 26 -> 4-byte uint follows as length
    # But then length bytes are 42 45 2f XX which is huge
    
    # Wait, let me look at this differently. 
    # ws_5 content: W[00][b3][be][a4][87][01]zBE/wh-ca-on/...
    # The 'z' here is ASCII 0x7a. But is this really CBOR?
    # Actually, looking at it: after 0x00 type, the content might NOT be CBOR
    # It might be a custom Diffusion binary format
    
    # Let me try: the path is just a plain string in the message
    # Find the end of the path (look for non-printable or control chars)
    path_start = be_idx
    path_end = path_start
    while path_end < len(d) and 32 <= d[path_end] < 127:
        path_end += 1
    path = d[path_start:path_end].decode('ascii')
    
    return {
        'header_before_path': d[1:be_idx].hex(),
        'path': path,
        'after_path': d[path_end:].hex()
    }

# Parse all subscription messages
sub_data = []
for n in range(1, 552):
    fpath = os.path.join(LOG_DIR, f"ws_{n}.txt")
    if not os.path.exists(fpath): continue
    d = read_ws(n)
    if len(d) == 0 or d[0] != 0x00: continue
    
    result = parse_sub_message(d)
    if result:
        sub_data.append((n, result))
        if len(sub_data) <= 10:
            print(f"ws_{n}: header={result['header_before_path']}, path={result['path']}")

print(f"\nTotal parsed: {len(sub_data)}")

# Now let's look at the header bytes before the path to find alias bytes
# Focus on the 3 bytes that should be the alias
print("\n=== Analyzing header bytes ===")
for n, result in sub_data[:20]:
    header = bytes.fromhex(result['header_before_path'])
    print(f"ws_{n}: header_hex={result['header_before_path']}, header_len={len(header)}")
    # Path segments
    parts = result['path'].split('/')
    print(f"  path parts: {parts}")
    print(f"  path len: {len(result['path'])}")
    
print("\n=== Group by path depth ===")
for n, result in sub_data:
    parts = result['path'].split('/')
    depth = len(parts)
    header = bytes.fromhex(result['header_before_path'])
    if depth in (3, 4, 5):
        print(f"ws_{n}: depth={depth}, header_len={len(header)}, header={result['header_before_path'][:40]}")

# Now let's figure out which 3 bytes in the header are the alias
# The alias appears in Type 4/84 at d[2:5] (bytes 2,3,4)
# In the 0x00 subscription, the header starts at d[1]
# Let's see if bytes 2,3,4 of the 0x00 message (d[2:5]) match any known Type 4 alias
print("\n=== Matching 0x00 header bytes to known Type 4/84 aliases ===")

# Build set of all known aliases from Type 4/84
known_aliases = set()
alias_ws_map = {}
for n in range(1, 552):
    fpath = os.path.join(LOG_DIR, f"ws_{n}.txt")
    if not os.path.exists(fpath): continue
    d = read_ws(n)
    if len(d) == 0: continue
    if d[0] == 0x84:
        for i in range(2, len(d)):
            if d[i] == 0x78 and i+1 < len(d) and d[i+1] in (0x01,):
                alias = d[2:i].hex()
                known_aliases.add(alias)
                alias_ws_map[alias] = ('0x84', n)
                break
    elif d[0] == 0x04:
        # Alias starts at d[2] - from the handoff, alias boundary detection
        # uses CBOR validation to find where CBOR starts
        # d[1] might be a flags/length byte
        # Let's check d[2:5] as 3-byte alias
        alias = d[2:5].hex()
        alias_ws_map.setdefault(alias, ('0x04', n))

# Also add aliases from Type 5 (these are the ones that matter)
for n in range(1, 552):
    fpath = os.path.join(LOG_DIR, f"ws_{n}.txt")
    if not os.path.exists(fpath): continue
    d = read_ws(n)
    if len(d) == 0: continue
    if d[0] == 0x05:
        zero_pos = d.index(0x00, 2)
        alias = d[2:zero_pos].hex()
        known_aliases.add(alias)

# For each 0x00 message, try different byte offsets for alias
for n, result in sub_data[:15]:
    d = read_ws(n)
    header = result['header_before_path']
    # Try d[2:5], d[3:6], d[4:7], etc as potential alias
    candidates = []
    for start in range(1, min(10, len(d)-2)):
        candidate = d[start:start+3].hex()
        if candidate in known_aliases:
            candidates.append((start, candidate))
    print(f"ws_{n}: path={result['path'][:60]}...")
    print(f"  header={header}")
    if candidates:
        print(f"  MATCH at offsets: {candidates}")
    else:
        print(f"  No alias match found")
