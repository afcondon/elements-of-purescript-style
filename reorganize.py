#!/usr/bin/env python3
"""Reorganize entries into new section-based structure."""

import re
import json
from pathlib import Path

# ── Section definitions ──────────────────────────────────────────────────────

SECTIONS = {
    1:  ("let-the-compiler", "I. Let the compiler do the work",
         "PureScript's compiler is not a gatekeeper — it is a collaborator. Every feature in this section exists to move knowledge out of your head and into the type system, where it can be checked, enforced, and relied upon. The habit to cultivate is simple: when you know something about your program, ask whether the compiler can know it too."),

    2:  ("totality", "II. The rewards of totality",
         "A total function handles every possible input. A partial function handles most of them and hopes for the best. PureScript's exhaustiveness checker, guard analysis, and non-empty types exist to help you write total functions — and to tell you when you have not. The entries in this section are variations on a single theme: leave no case unhandled."),

    3:  ("effects", "III. Effects are recipes",
         "In PureScript, an effectful value does not *do* anything. It *describes* something to be done. This distinction — effects as data, not as actions — is the foundation of everything else: composition, concurrency, testing, and reasoning. Once the recipe metaphor clicks, the combinators are plumbing."),

    4:  ("errors", "IV. Errors and failure",
         "There are two kinds of failure: the kind your program expects and the kind it does not. PureScript gives you different tools for each. Confusing them — catching unexpected errors, ignoring expected ones, or mixing both into one channel — produces code that is hard to reason about and harder to maintain."),

    5:  ("ffi", "V. The FFI boundary",
         "The foreign function interface is where PureScript's guarantees end and the host language's begin. Every entry in this section is about making that boundary as thin, honest, and verifiable as possible. The type checker cannot see across it; your discipline must bridge the gap."),

    6:  ("type-classes", "VI. Type classes",
         "Type classes in PureScript are not interfaces, not abstract classes, not traits. They are a mechanism for principled ad hoc polymorphism — functions that behave differently for different types, but within a framework of laws and guarantees. Understanding what they are (and are not) is essential to using them well."),

    7:  ("containers", "VII. Containers and traversal",
         "PureScript's standard library provides a small, well-designed set of containers and a rich algebra for working with them. The entries here cover the most common operations and the most common mistakes — places where a more direct combinator exists for what you are doing the long way."),

    8:  ("records-modules", "VIII. Records, rows, and modules",
         "Records and modules are the primary tools for organising code. Records give structure to data; modules give structure to namespaces. PureScript's row polymorphism makes records more flexible than in most languages, and its strict module system makes exports and imports more intentional."),

    9:  ("not-haskell", "IX. PureScript is not Haskell",
         "PureScript borrows much from Haskell — syntax, type classes, algebraic data types — but the languages differ in ways that matter daily. This section catalogues the differences that trip up Haskell programmers most often. If you have never written Haskell, you may skip this section without loss."),

    10: ("not-just-js", "X. PureScript compiles to more than JavaScript",
         "The JavaScript backend is the most mature and widely used, but PureScript also targets Erlang, Python, Lua, and other platforms. Advice that assumes JavaScript — 'use Array for performance', 'the FFI is a .js file' — may not transfer. The entries here remind you to think about the language, not just one backend."),

    11: ("codecs", "XI. Parsing, codecs, and round-tripping",
         "Data enters your program as untyped bytes and leaves as untyped bytes. The transformation between external representation and internal types should happen at the boundary, happen once, and be verifiable. Bidirectional codecs, parser combinators, and optics are the tools for this work."),

    12: ("omit-needless", "XII. Omit needless code",
         "Strunk and White's most famous rule is 'Omit needless words.' The same principle applies to code. Every unnecessary binding, redundant pattern, or verbose combinator chain is a distraction from the intent. PureScript's concise syntax rewards brevity — use it."),

    13: ("build", "XIII. The build",
         "Spago is PureScript's build tool and package manager. It is opinionated about project structure and dependency management, and working with those opinions — rather than against them — saves time and frustration."),

    14: ("power-tools", "XIV. Power tools — when to wield, when to sheathe",
         "PureScript offers type-level programming, extensible effects, and generic programming over row types. These are genuine capabilities, not parlour tricks. But they carry costs in compile time, error message clarity, and code legibility. Reach for them when simpler tools fall short, not before."),

    15: ("halogen", "XV. Halogen patterns",
         "Halogen is PureScript's most widely used UI framework. These entries cover patterns specific to Halogen's component model — not general PureScript style, but idioms that make Halogen code cleaner and more maintainable."),

    16: ("tasks", "XVI. Practical tasks",
         "Concrete guidance for common programming tasks. Each entry recommends a specific library or approach for a specific problem, chosen for reliability and ecosystem fit."),

    17: ("naming-style", "XVII. Naming and style",
         "Conventions that have no deep justification beyond consistency. Their value is that the community follows them; deviating without reason creates friction for readers who expect the standard patterns."),

    18: ("testing", "XVIII. Testing",
         "PureScript's type system catches many bugs at compile time, but not all. Property-based testing and law checking fill the gap, especially for the algebraic structures that type classes encode."),
}

# ── Entry mapping: old_id → (section_num, position_in_section) ───────────────
# Position determines order within section. Gaps are fine.

MAPPING = {
    # I. Let the compiler do the work
    1:    (1, 1),
    7:    (1, 2),
    5:    (1, 3),
    6:    (1, 4),
    55:   (1, 5),
    56:   (1, 6),
    95:   (1, 7),
    96:   (1, 8),
    97:   (1, 9),
    82:   (1, 10),
    49:   (1, 11),
    83:   (1, 12),
    84:   (1, 13),
    158:  (1, 14),   # type wildcards

    # II. Totality
    53:   (2, 1),
    75:   (2, 2),
    120:  (2, 3),
    121:  (2, 4),
    29:   (2, 5),
    44:   (2, 6),
    90:   (2, 7),
    98:   (2, 8),
    2:    (2, 9),
    33:   (2, 10),

    # III. Effects
    9:    (3, 1),
    10:   (3, 2),
    43:   (3, 3),
    122:  (3, 4),
    45:   (3, 5),
    13:   (3, 6),
    100:  (3, 7),
    11:   (3, 8),
    12:   (3, 9),
    144:  (3, 10),
    57:   (3, 11),
    58:   (3, 12),
    92:   (3, 13),   # newtypes for transformer stacks
    142:  (3, 14),   # polymorphic monad constraints
    143:  (3, 15),   # transformer stack safety

    # IV. Errors
    34:   (4, 1),
    '34a':(4, 2),
    35:   (4, 3),
    36:   (4, 4),
    140:  (4, 5),
    141:  (4, 6),
    99:   (4, 7),

    # V. FFI
    14:   (5, 1),
    15:   (5, 2),
    16:   (5, 3),
    '16a':(5, 4),
    17:   (5, 5),
    151:  (5, 6),
    152:  (5, 7),
    147:  (5, 8),
    153:  (5, 9),
    154:  (5, 10),
    155:  (5, 11),
    146:  (5, 12),   # unsafePerformEffect
    159:  (5, 13),   # type roles

    # VI. Type classes
    133:  (6, 1),
    23:   (6, 2),
    24:   (6, 3),
    31:   (6, 4),
    25:   (6, 5),
    27:   (6, 6),
    128:  (6, 7),
    101:  (6, 8),    # Don't use Show for serialisation
    150:  (6, 9),    # Semigroup instances should compose
    87:   (6, 10),   # avoid stringly-typed Symbol proxies
    149:  (6, 11),

    # VII. Containers
    3:    (7, 1),
    4:    (7, 2),
    28:   (7, 3),
    30:   (7, 4),
    32:   (7, 5),
    46:   (7, 6),
    89:   (7, 7),
    103:  (7, 8),
    124:  (7, 9),
    148:  (7, 10),   # join <$> traverse
    93:   (7, 11),   # PureScript String
    94:   (7, 12),   # Data.String.Pattern

    # VIII. Records, rows, modules
    51:   (8, 1),
    52:   (8, 2),
    80:   (8, 3),
    76:   (8, 4),
    77:   (8, 5),
    135:  (8, 6),    # skip newtype when field provides context
    136:  (8, 7),    # newtype everything with different semantics
    137:  (8, 8),    # extensible for args, closed for domain
    47:   (8, 9),
    48:   (8, 10),
    86:   (8, 11),   # separate data from operations
    91:   (8, 12),   # distinguish config from state
    125:  (8, 13),   # factor common fields
    131:  (8, 14),
    132:  (8, 15),
    160:  (8, 16),
    161:  (8, 17),   # capability pattern
    162:  (8, 18),   # namespace conventions

    # IX. Not Haskell
    8:    (9, 1),
    20:   (9, 2),
    21:   (9, 3),
    22:   (9, 4),
    26:   (9, 5),
    18:   (9, 6),
    19:   (9, 7),
    59:   (9, 8),
    '59a':(9, 9),
    '59b':(9, 10),
    156:  (9, 11),   # derived Ord for records
    157:  (9, 12),   # boolean ops non-strict

    # X. Not just JS
    163:  (10, 1),
    164:  (10, 2),

    # XI. Codecs
    37:   (11, 1),
    38:   (11, 2),
    39:   (11, 3),
    139:  (11, 4),   # JSON codecs as values
    102:  (11, 5),

    # XII. Omit needless code
    78:   (12, 1),
    79:   (12, 2),    # the principle stated
    127:  (12, 3),
    123:  (12, 4),    # avoid explicit recursion
    104:  (12, 5),
    130:  (12, 6),
    129:  (12, 7),
    85:   (12, 8),

    # XIII. Build
    64:   (13, 1),
    65:   (13, 2),
    66:   (13, 3),
    67:   (13, 4),
    68:   (13, 5),
    69:   (13, 6),
    70:   (13, 7),
    71:   (13, 8),
    72:   (13, 9),
    73:   (13, 10),
    74:   (13, 11),

    # XIV. Power tools
    60:   (14, 1),
    61:   (14, 2),
    62:   (14, 3),
    63:   (14, 4),
    134:  (14, 5),
    88:   (14, 6),   # monomorphise hot paths

    # XV. Halogen
    40:   (15, 1),
    41:   (15, 2),
    42:   (15, 3),
    145:  (15, 4),

    # XVI. Tasks
    105:  (16, 1),
    106:  (16, 2),
    107:  (16, 3),
    108:  (16, 4),
    109:  (16, 5),
    110:  (16, 6),
    111:  (16, 7),
    112:  (16, 8),

    # XVII. Naming
    113:  (17, 1),
    114:  (17, 2),
    115:  (17, 3),
    116:  (17, 4),
    117:  (17, 5),
    118:  (17, 6),
    119:  (17, 7),
    126:  (17, 8),
    81:   (17, 9),
    50:   (17, 10),

    # XVIII. Testing
    54:   (18, 1),
    149:  (18, 2),   # wait, 149 is already in VI.11 - skip duplicate
}

# Remove the duplicate — 149 goes in VI (type classes) only
# Actually let me keep it in XVIII and remove from VI
# Let me handle this by putting it in XVIII only
MAPPING[149] = (18, 2)
# And remove from VI — we'll add a cross-ref there instead
# Actually for simplicity, just keep it in one place. Testing is a better fit.

# ── Parse entries from existing files ────────────────────────────────────────

def parse_all_entries():
    """Parse all numbered entries from source markdown files."""
    root = Path(__file__).parent
    files = [
        "draft-entries.md",
        "entries-09-32.md",
        "entries-33-58.md",
        "entries-59-94.md",
        "entries-95-132.md",
        "entries-133-164-degustibus.md",
    ]

    pattern = re.compile(r'^## (\d+[a-z]?)\. (.+)$', re.MULTILINE)
    any_heading = re.compile(r'^#{1,2} ', re.MULTILINE)

    entries = {}  # id → (title, body)

    for fname in files:
        path = root / fname
        if not path.exists():
            continue
        text = path.read_text()

        matches = list(pattern.finditer(text))
        for i, match in enumerate(matches):
            raw_id = match.group(1)
            eid = int(raw_id) if raw_id.isdigit() else raw_id
            title = match.group(2).strip()
            start = match.end()

            if i + 1 < len(matches):
                end = matches[i + 1].start()
            else:
                later = any_heading.search(text, start)
                end = later.start() if later else len(text)

            body = text[start:end].strip()
            body = re.sub(r'\n---\s*$', '', body).strip()

            if eid not in entries:
                entries[eid] = (title, body)

    return entries


def parse_degustibus():
    """Parse De Gustibus entries."""
    root = Path(__file__).parent
    dg_entries = []

    for fname in ["draft-entries.md", "entries-133-164-degustibus.md"]:
        path = root / fname
        if not path.exists():
            continue
        text = path.read_text()

        dg_match = re.search(r'^# De Gustibus', text, re.MULTILINE)
        if not dg_match:
            continue

        dg_text = text[dg_match.end():]
        pattern = re.compile(r'^## (.+)$', re.MULTILINE)
        matches = list(pattern.finditer(dg_text))

        for i, match in enumerate(matches):
            title = match.group(1).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(dg_text)
            body = dg_text[start:end].strip()
            body = re.sub(r'\n---\s*$', '', body).strip()
            dg_entries.append((title, body))

    # Deduplicate by title
    seen = set()
    unique = []
    for title, body in dg_entries:
        if title not in seen:
            seen.add(title)
            unique.append((title, body))

    return unique


# ── Write new section files ──────────────────────────────────────────────────

def main():
    root = Path(__file__).parent
    entries = parse_all_entries()

    # Build section → entries mapping
    section_entries = {}  # section_num → [(position, old_id, title, body)]
    unmapped = []

    for old_id, (sec, pos) in MAPPING.items():
        if old_id in entries:
            title, body = entries[old_id]
            section_entries.setdefault(sec, []).append((pos, old_id, title, body))
        else:
            unmapped.append(old_id)

    if unmapped:
        print(f"Warning: unmapped entries (not found in source): {unmapped}")

    # Check for entries not in any section
    mapped_ids = set(MAPPING.keys())
    all_ids = set(entries.keys())
    orphans = all_ids - mapped_ids
    if orphans:
        print(f"Warning: entries not assigned to any section: {sorted(orphans, key=lambda x: (isinstance(x, str), x))}")

    # Write section files
    global_num = 0
    new_dir = root / "sections"
    new_dir.mkdir(exist_ok=True)

    for sec_num in sorted(SECTIONS.keys()):
        slug, heading, intro = SECTIONS[sec_num]
        fname = f"sec-{sec_num:02d}-{slug}.md"

        sec_list = section_entries.get(sec_num, [])
        sec_list.sort(key=lambda x: x[0])  # sort by position

        lines = [f"# {heading}\n"]
        lines.append(f"{intro}\n")
        lines.append("\n---\n")

        for pos, old_id, title, body in sec_list:
            global_num += 1
            lines.append(f"\n## {global_num}. {title}\n")
            lines.append(f"{body}\n")
            lines.append("\n---\n")

        (new_dir / fname).write_text("\n".join(lines))
        print(f"  {fname}: {len(sec_list)} entries (#{global_num - len(sec_list) + 1}-{global_num})")

    # Write De Gustibus file
    dg = parse_degustibus()
    lines = ["# De Gustibus\n"]
    lines.append("These are matters where reasonable PureScript programmers differ. We present the cases without ruling.\n")
    lines.append("\n---\n")
    for title, body in dg:
        lines.append(f"\n## {title}\n")
        lines.append(f"{body}\n")
        lines.append("\n---\n")

    (new_dir / "sec-19-degustibus.md").write_text("\n".join(lines))
    print(f"  sec-19-degustibus.md: {len(dg)} De Gustibus entries")

    print(f"\nTotal: {global_num} numbered entries + {len(dg)} De Gustibus")
    print(f"Written to {new_dir}/")


if __name__ == "__main__":
    main()
