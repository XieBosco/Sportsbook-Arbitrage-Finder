"""Explore 0x00 subscription messages and their relationship to aliases."""
import base64, os, struct

LOG_DIR = r"c:\Users\fiona\Desktop\arbitrage_tool\caesars_workspace\caesars_full_logs"

def read_ws(n):
    with open(os.path.join(LOG_DIR, f"ws_{n}.txt"), 'r') as f:
        return base64.b64decode(f.read().strip())

# First pass: find all 0x00 (subscription) messages and dump their structure
print("=== All 0x00 subscription messages ===")
sub_messages = []
for n in range(1, 552):
    fpath = os.path.join(LOG_DIR, f"ws_{n}.txt")
    if not os.path.exists(fpath):
        continue
    d = read_ws(n)
    if len(d) == 0:
        continue
    if d[0] == 0x00:
        # The subscription message should contain a human-readable path string
        # Let's see what follows the 0x00 byte
        print(f"\nws_{n}: len={len(d)}, hex={d.hex()}")
        # Try to find ASCII text
        ascii_part = ''
        for b in d[1:]:
            if 32 <= b < 127:
                ascii_part += chr(b)
            else:
                ascii_part += f'[{b:02x}]'
        print(f"  content: {ascii_part}")
        sub_messages.append((n, d))

print(f"\nTotal subscription messages: {len(sub_messages)}")

# Also look at Type 4 (0x04) messages to understand the alias assignment
print("\n=== Type 4 (0x04) messages - alias to full CBOR ===")
type4_count = 0
for n in range(1, 552):
    fpath = os.path.join(LOG_DIR, f"ws_{n}.txt")
    if not os.path.exists(fpath):
        continue
    d = read_ws(n)
    if len(d) == 0:
        continue
    if d[0] == 0x04:
        type4_count += 1
        if type4_count <= 5:
            print(f"\nws_{n}: len={len(d)}, first 20 hex={d[:20].hex()}")
            # Try alias as bytes 1-3 and also 2-4
            print(f"  d[1:4]={d[1:4].hex()}, d[2:5]={d[2:5].hex()}")

print(f"\nTotal Type 4 messages: {type4_count}")

# And Type 0x84 messages  
print("\n=== Type 0x84 (compressed) messages ===")
type84_count = 0
for n in range(1, 552):
    fpath = os.path.join(LOG_DIR, f"ws_{n}.txt")
    if not os.path.exists(fpath):
        continue
    d = read_ws(n)
    if len(d) == 0:
        continue
    if d[0] == 0x84:
        type84_count += 1
        if type84_count <= 5:
            print(f"\nws_{n}: len={len(d)}, first 20 hex={d[:20].hex()}")
            # The alias is at d[2:?] — we need to find the boundary
            # For 0x84, the handoff says alias is 3 bytes starting after some header
            # Let's look at d[1] which might be a length or flags byte
            print(f"  d[1]={d[1]:02x}, d[2:5]={d[2:5].hex()}")

print(f"\nTotal Type 0x84 messages: {type84_count}")

# Now let's look at how aliases in Type 5 messages look
print("\n=== Type 5 delta messages - alias bytes ===")
type5_aliases = set()
for n in range(1, 552):
    fpath = os.path.join(LOG_DIR, f"ws_{n}.txt")
    if not os.path.exists(fpath):
        continue
    d = read_ws(n)
    if len(d) == 0:
        continue
    if d[0] == 0x05:
        # Alias is between d[2] and the 0x00 separator
        zero_pos = d.index(0x00, 2)
        alias = d[2:zero_pos].hex()
        type5_aliases.add(alias)

print(f"Unique aliases in Type 5 messages: {sorted(type5_aliases)}")
print(f"Count: {len(type5_aliases)}")

# Now let's see WHICH aliases appear in Type 4/84 and Type 5  
print("\n=== Cross-referencing aliases ===")
type4_aliases = set()
for n in range(1, 552):
    fpath = os.path.join(LOG_DIR, f"ws_{n}.txt")
    if not os.path.exists(fpath):
        continue
    d = read_ws(n)
    if len(d) == 0:
        continue
    if d[0] == 0x84:
        # From scratch_decode.py: alias is d[2:i] where d[i] starts the zlib data
        # The detection uses: d[i] == 0x78 and d[i+1] in (0x01,)
        for i in range(2, len(d)):
            if d[i] == 0x78 and i+1 < len(d) and d[i+1] in (0x01,):
                alias = d[2:i].hex()
                type4_aliases.add(alias)
                break

print(f"Aliases from Type 4/84: {sorted(type4_aliases)}")
print(f"Count: {len(type4_aliases)}")
print(f"Type 5 aliases not in Type 4/84: {type5_aliases - type4_aliases}")
print(f"Type 4/84 aliases not in Type 5: {type4_aliases - type5_aliases}")
