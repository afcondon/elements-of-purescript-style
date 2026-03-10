# The Elements of PureScript Style

**[Read the guide](https://afcondon.github.io/elements-of-purescript-style/)**

178 entries in 18 sections + 14 De Gustibus.

---

This is a first cut at a particular type of document — a guide to writing idiomatic PureScript, aimed at both robots and humans. The inspiration for the approach is the classic, small style guide to English by William Strunk and E.B. White, and the sources are the public Discourse, blogs, PureScript language guide, a lot of things that I've noted myself over time.

I fed all this information into Claude and had it generate the entries with some UI chrome to rate and comment on them, then I read it, rated them, split some, deleted others, queried dubious ones and so on for a number of iterations.

I'm sure there's a lot still to fix but I thought I'd throw it out there to see if there's interest — I'd be happy to host the edit-and-comment version somewhere if anyone felt like contributing and also I'm open to PRs and issues too.

The tone is somewhat AI-ish, I know, but it can be re-written if that's overwhelmingly offputting. Claude doesn't have quite the delicate touch of the original in prose but, in fairness, neither do I.

## Structure

The source lives in `sections/` as markdown files — one per section. The build script (`build-book.py`) assembles them into a single self-contained HTML page published via GitHub Pages from `docs/`.

## Building

```bash
python3 build-book.py
cp public/elements.html docs/index.html
```
