#!/usr/bin/env python3
"""Renumber all entries sequentially across section files.

Handles entries like 107a, 107b by giving them proper sequential numbers.
Produces a mapping of old -> new numbers for cross-reference fixing.
"""

import re
import sys
from pathlib import Path

def main():
    root = Path(__file__).parent
    sections_dir = root / "sections"
    files = sorted(sections_dir.glob("sec-*.md"))

    # First pass: collect all entry IDs in order
    entry_pattern = re.compile(r'^## (\d+[a-z]?)\. (.+)$', re.MULTILINE)
    all_entries = []  # (file, raw_id, title, match_obj)

    for f in files:
        text = f.read_text()
        for m in entry_pattern.finditer(text):
            all_entries.append((f, m.group(1), m.group(2)))

    # Build mapping: old_id -> new_id
    mapping = {}
    for i, (f, old_id, title) in enumerate(all_entries, start=1):
        new_id = str(i)
        if old_id != new_id:
            mapping[old_id] = new_id

    if not mapping:
        print("All entries are already sequentially numbered.")
        return

    print(f"Renumbering {len(mapping)} entries:")
    for old, new in sorted(mapping.items(), key=lambda x: int(re.match(r'(\d+)', x[0]).group(1))):
        print(f"  {old} -> {new}")

    # Second pass: apply renumbering to files
    for f in files:
        text = f.read_text()
        original = text

        # Replace entry headings: ## 107a. Title -> ## 108. Title
        def replace_heading(m):
            old_id = m.group(1)
            title = m.group(2)
            new_id = mapping.get(old_id, old_id)
            return f"## {new_id}. {title}"

        text = entry_pattern.sub(replace_heading, text)

        if text != original:
            f.write_text(text)
            print(f"  Updated {f.name}")

    # Print total count
    total = len(all_entries)
    print(f"\nTotal entries: {total}")

    # Warn about cross-references that may need updating
    xref_pattern = re.compile(r'entry (\d+[a-z]?)')
    for f in files:
        text = f.read_text()
        for m in xref_pattern.finditer(text):
            ref = m.group(1)
            if ref in mapping:
                print(f"  WARNING: {f.name} references old entry {ref} (now {mapping[ref]})")

if __name__ == "__main__":
    main()
