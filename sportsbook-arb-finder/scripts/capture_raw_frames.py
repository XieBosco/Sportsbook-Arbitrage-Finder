"""Script for capturing raw CDP frames for debugging."""
import argparse

def main() -> None:
    """Parse arguments and start capturing CDP frames."""
    parser = argparse.ArgumentParser(description="Capture raw CDP frames")
    parser.add_argument("--port", type=int, default=19222, help="CDP debug port")
    parser.add_argument("--url-pattern", type=str, required=True, help="URL pattern to match")
    parser.add_argument("--out", type=str, required=True, help="Output file path")
    pass

if __name__ == "__main__":
    main()
