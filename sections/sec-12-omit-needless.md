# XII. Omit needless code

Strunk and White's most famous rule is 'Omit needless words.' The same principle applies to code. Every unnecessary binding, redundant pattern, or verbose combinator chain is a distraction from the intent. PureScript's concise syntax rewards brevity — use it.


---


## 129. Do not name a value you immediately pass to one function

A `let` binding is documentation. It says: "this intermediate value has a role worth naming, or it will be used more than once." When neither is true, the binding is clutter.

Prefer:

```purescript
do
  user <- fetchUser id
  log user.name
```

Over:

```purescript
do
  user <- fetchUser id
  let name = user.name
  log name
```

The binding `name` exists for one line. It is consumed immediately and never referenced again. The reader must track it anyway — scanning ahead to confirm it is not used a second time, checking that it means what they think it means. Passing `user.name` directly eliminates this overhead.

This does not apply when the name genuinely clarifies intent. `let cutoff = 0.5` is fine even if used once, because `cutoff` tells the reader something that `0.5` does not. The test is not "how many times is it used?" but "does the name add information?"


---


## 130. The principle, stated

Naming a value is a promise that the name matters. Every binding asks the reader to remember it, track its scope, and consider whether it will appear again. In a language with good syntax for anonymous operations — lambda-case, record-update wildcards, accessor shorthand, point-free composition — many of these names are unnecessary. They exist not because the author chose them but because the author did not notice they could be omitted. The discipline is not to write the shortest code, but to write code where every name earns its place. When the structure of the expression already tells you what is happening — when position, type, and context are sufficient — let the syntax speak and keep the namespace clean. Omit needless names.


---

## XVI. Miscellany


---


## 131. Sometimes you just need a let

If the compiler is telling you something needs to be `pure` because it is in a `do` block, consider whether it might only need a `let`. Beginners often reach for `x <- pure (f y)` because everything else in the block uses `<-` and a plain declaration seems to require it. It does not — `let` works directly inside `do` blocks for pure bindings.

Prefer:

```purescript
do
  response <- fetchData url
  let parsed = parseResponse response
  saveToCache parsed
```

Over:

```purescript
do
  response <- fetchData url
  parsed <- pure (parseResponse response)
  saveToCache parsed
```

Every `<-` in a `do` block signals "this is where an effect happens." `let` says what it is: a pure binding. The reader does not need to look inside the parentheses to confirm that nothing effectful is going on.


---


## 132. Avoid explicit recursion; use higher-order functions

Most recursive patterns over data structures are already captured by standard combinators: `map`, `filter`, `foldl`, `foldr`, `traverse`, `unfold`, `mapAccumL`. Explicit recursion is harder to read, easier to get wrong, and — in a strict language — liable to blow the stack.

```purescript
-- Higher-order: intent is visible, stack safety is inherited.
sumPositive :: Array Int -> Int
sumPositive = filter (_ > 0) >>> sum

-- Explicit recursion: the reader must verify termination and accumulator handling.
sumPositive :: Array Int -> Int
sumPositive = go 0
  where
  go acc arr = case Array.uncons arr of
    Nothing -> acc
    Just { head, tail } ->
      if head > 0 then go (acc + head) tail
      else go acc tail
```

Reach for explicit recursion only when no standard combinator fits — tree traversals with complex accumulation, interleaved effects with early termination, or algorithms where the recursive structure is the point. When you do write explicit recursion, use `tailRecM` or the `MonadRec` class to guarantee stack safety.


---


## 133. Write the simplest code that the types permit

If the compiler accepts your code and the meaning is clear to a reader, the code is good enough. Do not add type-level machinery to enforce an invariant the code already maintains. Do not abstract over a pattern that occurs once. Do not reach for a monad transformer when a function argument will do.

Simplicity in PureScript is not simplicity in JavaScript. A sum type with four constructors, a `newtype` with a smart constructor, an `ado` block that validates five fields — these are precision, not complexity.

The temptation runs the other direction. PureScript offers enough abstraction machinery to build cathedrals. But generality that serves no current need is speculation, and speculation has a carrying cost: every reader must understand the abstraction to understand the code.

Write a concrete function. When a second use case appears, extract the commonality. When a third appears, consider a type class. The simplest code that the types permit is the least sophisticated code that still captures every distinction the problem demands.


---


## 134. Use $ and # to reduce parentheses, but do not chain excessively

`$` (apply) and `#` (pipe) exist to reduce nested parentheses. One or two applications improve readability. A long chain trades one problem for another.

```purescript
-- Good: one $ eliminates a nesting level.
Map.lookup key $ Map.fromFoldable pairs

-- Good: # for a left-to-right pipeline.
pairs # Map.fromFoldable # Map.lookup key

-- Too much: the reader counts operators instead of parentheses.
f $ g $ h $ i $ j $ k x
```

For pipelines longer than two or three steps, use `>>>` composition with a named function, or break the chain into `let` bindings. The goal is to reduce the reader's working memory, not to demonstrate that parentheses are unnecessary.

`$` reads right to left; `#` reads left to right. Within a codebase, pick a prevailing direction and stay consistent. Mixing the two in a single expression is almost always confusing.


---


## 135. Avoid dead code and commented-out blocks

Delete what you do not use. Version control remembers what you have deleted; your codebase should not.

Commented-out code is a trap. It rots faster than live code because the compiler never checks it. When dependencies change, module names shift, or type signatures evolve, the commented block falls silently out of sync. A reader encountering it cannot know whether it is a plan, a memory, a debugging aid, or an oversight. In every case, it is noise.

The same applies to unused imports, unreachable branches, and functions that nothing calls. Each is a false signal — an assertion that this code matters when it does not. Remove it. If you need it again, `git log` is a better archive than a comment.


---


## 136. Use purs-tidy and do not fight it

`purs-tidy` is the community formatter for PureScript. Run it. Configure your editor to run it on save. Do not manually adjust its output.

Consistent formatting across the ecosystem means you can read anyone's code without adjusting to their whitespace preferences, open a pull request without noise from reformatting, and focus code review on substance rather than style. The specific choices `purs-tidy` makes are less important than the fact that everyone makes the same ones.

If you disagree with a formatting decision, consider whether the disagreement is worth the cost of divergence. It almost never is.


---
