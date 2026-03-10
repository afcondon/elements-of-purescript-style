#!/usr/bin/env python3
"""
Build a single-page HTML book: The Elements of PureScript Style.

Usage: python3 build-book.py
Output: public/elements.html
"""

import html as html_mod
import re
from pathlib import Path

# Language mapping for Prism.js syntax highlighting
LANG_MAP = {
    'purescript': 'haskell',
    'haskell': 'haskell',
    'yaml': 'yaml',
    'bash': 'bash',
    'javascript': 'javascript',
    'markdown': 'markdown',
}

CODE_LABELS = frozenset([
    'Prefer:', 'Over:', 'Good:', 'Bad:', 'Right:', 'Wrong:',
])


def esc(text):
    return html_mod.escape(text, quote=False)


def inline(text):
    """Convert inline markdown to HTML."""
    parts = re.split(r'(`[^`]+`)', text)
    out = []
    for part in parts:
        if part.startswith('`') and part.endswith('`'):
            out.append(f'<code>{esc(part[1:-1])}</code>')
        else:
            s = esc(part)
            # Bold before italic
            s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
            # Italic
            s = re.sub(r'(?<!\*)\*([^\*\n]+?)\*(?!\*)', r'<em>\1</em>', s)
            # Links
            s = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', s)
            # Auto-link entry references
            s = re.sub(
                r'\b([Ee]ntry) (\d+)',
                lambda m: f'<a href="#entry-{m.group(2)}">{m.group(1)}\u00a0{m.group(2)}</a>',
                s
            )
            # Em-dashes
            s = s.replace(' -- ', ' \u2014 ')
            out.append(s)
    return ''.join(out)


class BookBuilder:
    def __init__(self):
        self.toc = []
        self.parts = []
        self.in_code = False
        self.code_lang = ''
        self.code_buf = []
        self.para_buf = []
        self.list_buf = []
        self.in_list = False
        self.counts = {'entries': 0, 'sections': 0, 'dg': 0}

    def _flush_para(self):
        if self.para_buf:
            text = ' '.join(self.para_buf)
            if text.strip() in CODE_LABELS:
                self.parts.append(f'<p class="code-label">{inline(text)}</p>')
            else:
                self.parts.append(f'<p>{inline(text)}</p>')
            self.para_buf = []

    def _flush_list(self):
        if self.list_buf:
            items = '\n'.join(f'  <li>{inline(li)}</li>' for li in self.list_buf)
            self.parts.append(f'<ul>\n{items}\n</ul>')
            self.list_buf = []
            self.in_list = False

    def _flush(self):
        self._flush_para()
        self._flush_list()

    def feed_line(self, line, is_dg=False):
        stripped = line.strip()

        # Inside code block
        if self.in_code:
            if stripped.startswith('```'):
                lang = LANG_MAP.get(self.code_lang, '')
                cls = f' class="language-{lang}"' if lang else ''
                code = esc('\n'.join(self.code_buf))
                self.parts.append(f'<pre><code{cls}>{code}</code></pre>')
                self.code_buf = []
                self.in_code = False
            else:
                self.code_buf.append(line)
            return

        # Start code block
        m = re.match(r'^```(\w*)$', stripped)
        if m:
            self._flush()
            self.in_code = True
            self.code_lang = m.group(1)
            return

        # Horizontal rule
        if re.match(r'^-{3,}$', stripped):
            self._flush()
            return

        # Section heading: # Title
        if line.startswith('# ') and not line.startswith('## '):
            self._flush()
            title = line[2:].strip()
            self.counts['sections'] += 1
            sid = 'de-gustibus' if 'De Gustibus' in title else f'sec-{self.counts["sections"]}'
            self.toc.append((sid, title))
            self.parts.append(f'</section>\n<section id="{sid}">')
            self.parts.append(f'<h2><a href="#{sid}">{esc(title)}</a></h2>')
            return

        # Entry heading: ## N. Title
        m = re.match(r'^##\s+(\d+)\.\s+(.+)$', line)
        if m:
            self._flush()
            num, title = m.group(1), m.group(2)
            eid = f'entry-{num}'
            self.counts['entries'] += 1
            self.parts.append(
                f'<h3 id="{eid}"><a href="#{eid}" class="entry-link">'
                f'<span class="entry-num">{num}.</span></a> {inline(title)}</h3>'
            )
            return

        # Mid-file section heading: ## XVI. Title
        m = re.match(r'^##\s+([IVXLCDM]+)\.\s+(.+)$', line)
        if m and not is_dg:
            self._flush()
            full = f'{m.group(1)}. {m.group(2)}'
            self.counts['sections'] += 1
            sid = f'sec-{self.counts["sections"]}'
            self.toc.append((sid, full))
            self.parts.append(f'</section>\n<section id="{sid}">')
            self.parts.append(f'<h2><a href="#{sid}">{esc(full)}</a></h2>')
            return

        # DG entry heading: ## Title
        if line.startswith('## ') and is_dg:
            self._flush()
            title = line[3:].strip()
            self.counts['dg'] += 1
            did = f'dg-{self.counts["dg"]}'
            self.parts.append(
                f'<h3 id="{did}" class="dg-title">'
                f'<a href="#{did}" class="entry-link">{inline(title)}</a></h3>'
            )
            return

        # List item
        m = re.match(r'^[-*]\s+(.+)$', stripped)
        if m:
            self._flush_para()
            self.in_list = True
            self.list_buf.append(m.group(1))
            return

        # List continuation
        if self.in_list and line.startswith('  ') and stripped:
            if self.list_buf:
                self.list_buf[-1] += ' ' + stripped
            return

        # Blank line
        if not stripped:
            self._flush()
            return

        # Regular text
        if self.in_list:
            self._flush_list()
        self.para_buf.append(stripped)

    def process_file(self, path, is_dg=False):
        for line in path.read_text().split('\n'):
            self.feed_line(line, is_dg)
        self._flush()

    def build(self):
        root = Path(__file__).parent / 'sections'
        files = sorted(root.glob('sec-*.md'))
        self.parts.append('<section>')
        for f in files:
            self.process_file(f, is_dg='degustibus' in f.name)
        self.parts.append('</section>')

        body = '\n'.join(self.parts)
        body = body.replace('<section>\n</section>\n', '', 1)

        toc_items = '\n'.join(
            f'    <li><a href="#{sid}">{esc(title)}</a></li>'
            for sid, title in self.toc
        )

        n = self.counts
        return TEMPLATE.format(
            toc_items=toc_items,
            body=body,
            entries=n['entries'],
            sections=n['sections'],
            dg=n['dg'],
        )


# ---------------------------------------------------------------------------

TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Elements of PureScript Style</title>
<style>
/* ── Reset ─────────────────────────────────────────────────────────── */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

/* ── Base ──────────────────────────────────────────────────────────── */
html {{ font-size: 18px; }}
body {{
  font-family: Georgia, "Times New Roman", Times, serif;
  line-height: 1.75;
  color: #222;
  background: #fff;
  max-width: 36em;
  margin: 0 auto;
  padding: 3em 1.5em 4em;
}}

/* ── Title page ────────────────────────────────────────────────────── */
.title-page {{
  text-align: center;
  margin: 5em 0 4em;
}}
.title-page h1 {{
  font-size: 1.8em;
  font-weight: normal;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  line-height: 1.35;
}}
.title-page .rule {{
  display: block;
  width: 4em;
  height: 1px;
  background: #999;
  margin: 1.5em auto;
  border: none;
}}
.epigraph {{
  font-style: italic;
  color: #666;
  font-size: 0.9em;
  margin-top: 0.5em;
}}
.attribution {{
  font-style: normal;
  font-size: 0.85em;
  letter-spacing: 0.03em;
}}

/* ── Table of contents ─────────────────────────────────────────────── */
.toc {{
  margin: 0 0 4em;
}}
.toc-heading {{
  font-family: Georgia, "Times New Roman", Times, serif;
  font-size: 0.75em;
  font-weight: normal;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #888;
  margin-bottom: 1.25em;
}}
.toc ol {{
  list-style: none;
  padding: 0;
}}
.toc li {{
  margin: 0.3em 0;
  font-size: 0.9em;
}}
.toc a {{
  color: #333;
  text-decoration: none;
}}
.toc a:hover {{
  border-bottom: 1px solid #aaa;
}}

/* ── Sections ──────────────────────────────────────────────────────── */
section {{
  margin-top: 3.5em;
  padding-top: 2em;
  border-top: 1px solid #ddd;
}}
section:first-of-type {{
  border-top: none;
  padding-top: 0;
}}

h2 {{
  font-size: 0.8em;
  font-weight: normal;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: #555;
  margin-bottom: 1.25em;
}}
h2 a {{
  color: inherit;
  text-decoration: none;
}}
h2 a:hover {{
  color: #333;
}}

/* Section intro — first paragraph after section heading */
section > h2 + p {{
  color: #444;
  margin-bottom: 1.5em;
}}

/* ── Entries ────────────────────────────────────────────────────────── */
h3 {{
  font-size: 1em;
  font-weight: bold;
  margin-top: 2.5em;
  margin-bottom: 0.4em;
  line-height: 1.45;
  position: relative;
}}

.entry-link {{
  text-decoration: none;
  color: inherit;
}}
.entry-link:hover .entry-num {{
  color: #999;
}}

.entry-num {{
  color: #888;
  font-weight: normal;
  transition: color 0.15s;
}}

/* On wide screens, float entry numbers into the margin */
@media (min-width: 54em) {{
  .entry-num {{
    position: absolute;
    right: calc(100% + 0.6em);
    font-size: 0.88em;
    top: 0.08em;
  }}
}}

/* De Gustibus entries */
.dg-title {{
  font-style: italic;
}}
.dg-title a {{
  color: inherit;
  text-decoration: none;
}}
.dg-title a:hover {{
  color: #666;
}}

/* ── Text ──────────────────────────────────────────────────────────── */
p {{
  margin: 0.75em 0;
}}

.code-label {{
  font-size: 0.85em;
  font-style: italic;
  color: #666;
  margin-bottom: 0.15em;
}}
.code-label + pre {{
  margin-top: 0.25em;
}}

/* ── Inline code ───────────────────────────────────────────────────── */
code {{
  font-family: "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
  font-size: 0.82em;
  background: #f4f3f0;
  padding: 0.1em 0.3em;
  border-radius: 2px;
}}

/* ── Code blocks ───────────────────────────────────────────────────── */
pre {{
  background: #f8f7f4;
  padding: 1.2em 1.5em;
  margin: 1em 0;
  overflow-x: auto;
  line-height: 1.55;
  border-left: 2px solid #ddd;
}}
pre code {{
  background: none;
  padding: 0;
  font-size: 0.75em;
  border-radius: 0;
}}
/* On wide screens, let code blocks extend beyond the text column */
@media (min-width: 54em) {{
  pre {{
    width: calc(100% + 8em);
    margin-left: -4em;
    padding-left: calc(4em + 1.5em);
    margin-right: -4em;
    padding-right: 1.5em;
  }}
}}

/* ── Prism.js — minimal syntax highlighting ────────────────────────── */
code[class*="language-"],
pre[class*="language-"] {{
  color: #333;
}}
.token.comment,
.token.prolog,
.token.doctype,
.token.cdata {{
  color: #9a9a9a;
  font-style: italic;
}}
.token.comment.comment-good {{
  color: #4a7c59;
}}
.token.comment.comment-bad {{
  color: #a05050;
}}
.token.keyword {{
  font-weight: 600;
  color: #333;
}}
.token.string,
.token.char,
.token.attr-value {{
  color: #596d49;
}}
.token.number,
.token.boolean {{
  color: #596d49;
}}
.token.operator {{
  color: #666;
}}
.token.punctuation {{
  color: #666;
}}
.token.class-name,
.token.function,
.token.builtin,
.token.tag,
.token.attr-name,
.token.selector {{
  color: #333;
}}

/* ── Lists ─────────────────────────────────────────────────────────── */
ul, ol {{
  padding-left: 1.5em;
  margin: 0.5em 0;
}}
li {{
  margin: 0.25em 0;
}}

/* ── Links ─────────────────────────────────────────────────────────── */
a {{
  color: #333;
}}
p a, li a {{
  text-decoration-color: #ccc;
  text-underline-offset: 0.15em;
}}
p a:hover, li a:hover {{
  text-decoration-color: #666;
}}

/* ── Footer ────────────────────────────────────────────────────────── */
footer {{
  margin-top: 5em;
  padding-top: 1.5em;
  border-top: 1px solid #ddd;
  text-align: center;
  font-size: 0.78em;
  color: #aaa;
  letter-spacing: 0.04em;
}}
footer p {{
  margin: 0.3em 0;
}}
footer a {{
  color: #999;
}}

/* ── Responsive ────────────────────────────────────────────────────── */
@media (max-width: 600px) {{
  html {{ font-size: 16px; }}
  body {{ padding: 1.5em 1em; }}
  pre {{ padding: 1em; font-size: 0.9em; }}
  .title-page {{ margin: 3em 0 2.5em; }}
}}

/* ── Print ─────────────────────────────────────────────────────────── */
@media print {{
  body {{ max-width: none; font-size: 11pt; color: #000; }}
  section {{ page-break-inside: avoid; }}
  pre {{ border-left-color: #999; white-space: pre-wrap; word-wrap: break-word; }}
  a {{ color: #000; text-decoration: none; }}
  .toc {{ page-break-after: always; }}
  footer {{ display: none; }}
  .entry-num {{ color: #000; font-weight: bold; position: static; }}
}}
</style>
</head>
<body>

<header class="title-page">
  <h1>The Elements of<br>PureScript Style</h1>
  <hr class="rule">
  <p class="epigraph">\u201cOmit needless words.\u201d<br>
  <span class="attribution">\u2014 William Strunk Jr.</span></p>
</header>

<nav class="toc">
  <h2 class="toc-heading">Contents</h2>
  <ol>
{toc_items}
  </ol>
</nav>

<main>
{body}
</main>

<footer>
  <p>{entries} entries \u00b7 {sections} sections \u00b7 {dg} De Gustibus</p>
  <p>Draft \u2014 March 2026</p>
</footer>

<script>window.Prism = window.Prism || {{}};Prism.manual = true;</script>
<script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/prism.min.js" defer></script>
<script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-haskell.min.js" defer></script>
<script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-yaml.min.js" defer></script>
<script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-javascript.min.js" defer></script>
<script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-bash.min.js" defer></script>
<script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-markdown.min.js" defer></script>
<script>
document.addEventListener('DOMContentLoaded', function() {{
  Prism.highlightAll();
  var GOOD = /\\b(Prefer|Correct|Better|Idiomatic|CORRECT|Safe)\\b|\\bRight:/;
  var BAD  = /\\b(Avoid|Don't|Dangerous|WRONG|Anti-pattern|Verbose)\\b|\\b(Over-|Bad:|Wrong:)/;
  document.querySelectorAll('.token.comment').forEach(function(el) {{
    var t = el.textContent;
    if (GOOD.test(t)) el.classList.add('comment-good');
    else if (BAD.test(t)) el.classList.add('comment-bad');
  }});
}});
</script>
</body>
</html>'''


def main():
    builder = BookBuilder()
    page = builder.build()
    out = Path(__file__).parent / 'public' / 'elements.html'
    out.write_text(page)
    n = builder.counts
    print(f'Written {n["entries"]} entries + {n["dg"]} De Gustibus ({n["sections"]} sections) to {out}')


if __name__ == '__main__':
    main()
