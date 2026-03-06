#!/usr/bin/env python3
"""Parse all entry markdown files into a single entries.json for the review app."""

import json
import re
import sys
from pathlib import Path

def parse_entries(text):
    """Split markdown into entries by ## N. Title headings."""
    entries = []
    # Match numbered entries: ## N. Title (including ## 16a. Title)
    entry_pattern = re.compile(r'^## (\d+[a-z]?)\. (.+)$', re.MULTILINE)
    # Match any heading (# or ##) to find section boundaries
    any_heading = re.compile(r'^#{1,2} ', re.MULTILINE)

    matches = list(entry_pattern.finditer(text))
    for i, match in enumerate(matches):
        raw_id = match.group(1)
        entry_id = int(raw_id) if raw_id.isdigit() else raw_id
        title = match.group(2).strip()
        start = match.end()

        # End at the next numbered entry OR any heading that isn't a numbered entry
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            # No more numbered entries — find the next heading of any kind
            later = any_heading.search(text, start)
            end = later.start() if later else len(text)

        body = text[start:end].strip()
        body = re.sub(r'\n---\s*$', '', body).strip()
        entries.append({
            "id": entry_id,
            "title": title,
            "body": body,
            "section": "entry"
        })
    return entries

def parse_degustibus(text):
    """Parse De Gustibus entries (## Title without numbers)."""
    entries = []
    # Find the De Gustibus section
    dg_match = re.search(r'^# De Gustibus', text, re.MULTILINE)
    if not dg_match:
        return entries

    dg_text = text[dg_match.end():]
    # Split on ## headings
    pattern = re.compile(r'^## (.+)$', re.MULTILINE)
    matches = list(pattern.finditer(dg_text))

    for i, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(dg_text)
        body = dg_text[start:end].strip()
        body = re.sub(r'\n---\s*$', '', body).strip()
        entries.append({
            "id": f"dg-{i+1}",
            "title": title,
            "body": body,
            "section": "degustibus"
        })
    return entries

def main():
    root = Path(__file__).parent
    files = [
        "draft-entries.md",
        "entries-09-32.md",
        "entries-33-58.md",
        "entries-59-94.md",
        "entries-95-132.md",
        "entries-133-164-degustibus.md",
    ]

    all_entries = []
    all_dg = []

    for fname in files:
        path = root / fname
        if not path.exists():
            print(f"Warning: {fname} not found", file=sys.stderr)
            continue
        text = path.read_text()
        all_entries.extend(parse_entries(text))
        all_dg.extend(parse_degustibus(text))

    # Deduplicate by id (earlier files take precedence)
    seen = set()
    unique_entries = []
    for e in all_entries:
        if e["id"] not in seen:
            seen.add(e["id"])
            unique_entries.append(e)

    # Sort entries by number
    def sort_key(e):
        eid = e["id"]
        if isinstance(eid, int):
            return (eid, "")
        # Handle "16a" -> (16, "a")
        m = re.match(r'^(\d+)([a-z]*)$', str(eid))
        return (int(m.group(1)), m.group(2)) if m else (999, str(eid))

    unique_entries.sort(key=sort_key)

    # Deduplicate De Gustibus by title
    seen_dg = set()
    unique_dg = []
    for e in all_dg:
        if e["title"] not in seen_dg:
            seen_dg.add(e["title"])
            unique_dg.append(e)

    result = {
        "entries": unique_entries,
        "degustibus": unique_dg
    }

    out = root / "public" / "entries.json"
    out.write_text(json.dumps(result, indent=2))
    print(f"Written {len(unique_entries)} entries + {len(unique_dg)} De Gustibus to {out}")

if __name__ == "__main__":
    main()
