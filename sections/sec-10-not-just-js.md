# X. PureScript compiles to more than JavaScript

The JavaScript backend is the most mature and widely used, but PureScript also targets Erlang, Python, Lua, and other platforms. Advice that assumes JavaScript — 'use Array for performance', 'the FFI is a .js file' — may not transfer. The entries here remind you to think about the language, not just one backend.


---


## 122. Note runtime environment assumptions in your README

A PureScript library that calls `process.argv` will fail silently in the browser. A library that calls `document.querySelector` will crash in Node. These are not type errors — the compiler cannot catch them.

If your library assumes a specific runtime environment, say so in the first paragraph of the README. Not in a "Compatibility" section that the reader scrolls past. Not in a footnote. At the top.

```markdown
# purescript-node-streams

Node.js bindings for readable and writable streams.

**This library requires a Node.js runtime.** It will not work in browsers or other JavaScript environments.
```

A consumer who installs your library for the wrong platform gets cryptic FFI errors — `TypeError: Cannot read property 'createReadStream' of undefined` — not a helpful message. The README is the only firewall you have. (Official Style Guide)


---


## 123. PureScript is industrially focused, not a PL research vehicle

PureScript is a language designed for building software, not for exploring the frontiers of type theory. This is a deliberate choice with practical consequences.

Stability is a high priority. Features that require large-scale breaking changes across the ecosystem are unlikely to be accepted, regardless of their theoretical merit. The language prefers fewer, more powerful features to many special-purpose ones. If a need can be addressed downstream of the compiler — in a library, a code generator, a build tool — it probably should be.

This means some features that PureScript *could* have, it chooses not to. Dependent types, linear types, effect rows — these are active areas of PL research, and PureScript's governance has consistently prioritised the working programmer over the language enthusiast. The language is expressive enough to build complex systems and simple enough to onboard working developers.

For users, the implication is: work with the language as it is. If you find yourself fighting the type system to encode an invariant it was not designed to express, consider whether a simpler encoding — a smart constructor, a runtime check at the boundary, a convention documented in a comment — might serve better. The goal is working software, not a proof of concept. (Gary Burgess, Nate Faubion, Thomas Honeyman)


---


---
