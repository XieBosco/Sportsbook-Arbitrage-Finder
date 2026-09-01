import glob
import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src")))

from arbfinder.parsers.caesars import CaesarsParser

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "tests", "fixtures", "caesars", "messages")

def main():
    parser = CaesarsParser()
    ws_files = sorted(glob.glob(os.path.join(FIXTURES_DIR, "ws_*.txt")))
    
    # We want to intercept the decoded objects.
    # We can patch _process_decoded_object
    original_process = parser._process_decoded_object
    
    def hooked_process(alias_hex, obj, now):
        from arbfinder.parsers.diffusion_codec import classify_object
        obj_type = classify_object(obj) if isinstance(obj, dict) else "unknown"
        if obj_type == "selection":
            print(f"Selection obj: {obj}")
        elif obj_type == "market":
            print(f"Market obj: {obj}")
        return original_process(alias_hex, obj, now)
        
    parser._process_decoded_object = hooked_process
    
    for f in ws_files:
        with open(f, "r", encoding="utf-8") as file:
            payload = file.read().strip()
            parser.handle_ws_frame(payload)

if __name__ == "__main__":
    main()
