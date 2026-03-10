#!/usr/bin/env python3
"""Mark entries as 'edited' in the review app's edit tracker.

Generates a JSON file that can be imported via the review app's
"Import edit markers" button.

Usage:
  python3 mark-edited.py 1 2 4 7 8 9 10 11 13 15 18 22 23
  # Then import public/edit-markers.json in the browser
"""

import json
import sys
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 mark-edited.py <entry-id> [entry-id ...]")
        print("Example: python3 mark-edited.py 1 2 4 7 8")
        sys.exit(1)

    ids = sys.argv[1:]
    edits = {id: "edited" for id in ids}

    out = Path(__file__).parent / "public" / "edit-markers.json"
    out.write_text(json.dumps({"edits": edits}, indent=2))
    print(f"Wrote {len(ids)} edit markers to {out}")
    print("Import this file in the review app via 'Import edit markers'.")

if __name__ == "__main__":
    main()
