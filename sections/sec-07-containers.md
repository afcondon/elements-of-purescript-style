# VII. Containers and traversal

PureScript's standard library provides a small, well-designed set of containers and a rich algebra for working with them. The entries here cover the most common operations and the most common mistakes — places where a more direct combinator exists for what you are doing the long way.


---


## 76. Traverse; do not map and sequence

When you need to apply an effectful function to every element of a structure, use `traverse`. Do not `map` the function over the structure and then `sequence` the result.

Prefer:

```purescript
loadAll :: Array FilePath -> Aff (Array String)
loadAll = traverse readTextFile
```

Over:

```purescript
loadAll :: Array FilePath -> Aff (Array String)
loadAll paths = sequence (map readTextFile paths)
```

These are equivalent — `traverse f` is defined as `sequence <<< map f` — but the composed version says two things ("apply this to each element", then "collect the effects") where one will do. Worse, the two-step version invites the reader to wonder whether something happens between the `map` and the `sequence`, and the answer is always no.

Use `for` when the function reads more naturally after the structure:

```purescript
for items \item ->
  H.liftEffect $ log item.name
```


---


## 77. Discard results deliberately

When you traverse for effect alone, use `traverse_` or `for_`.

```purescript
traverse_ removeFile tempFiles
```

Not:

```purescript
void $ traverse (\f -> removeFile f) tempFiles
```

The underscore variants are not merely cosmetic. `traverse` must retain every result to build the output structure; `traverse_` is free to discard each result as it goes. `void $ traverse` builds an `Array Unit` and then throws it away.

The same applies throughout the standard libraries. Prefer `when` over `void $ if`, `for_` over `void $ for`. Where the library offers a variant that matches your intent, use it. The reader should not have to subtract the parts you did not mean.


---


## 78. Use foldMap instead of map followed by fold

When you need to transform each element and then combine the results under a `Monoid`, `foldMap` does both in a single pass.

```purescript
-- Prefer: one pass, clear intent.
renderNames :: forall f. Foldable f => f User -> String
renderNames = foldMap (\u -> u.name <> "\n")

-- Over: two passes, intermediate structure.
renderNames :: forall f. Foldable f => f User -> String
renderNames = fold <<< map (\u -> u.name <> "\n")
```

`foldMap f` is defined as `fold <<< map f`, so the two are semantically equivalent. But the single-pass version avoids constructing an intermediate collection, and more importantly, it says "transform and combine" as one thought rather than two. When you see `foldMap`, you know the shape immediately: a function into a monoid, applied across a structure. When you see `fold <<< map`, you must read both to confirm they are not doing something more complex.


---


## 79. Use Data.Map and Data.Set, not hand-rolled lookups

If you find yourself writing `findFirst (\x -> x.id == target) items` or manually deduplicating with `nub`, step back. The `ordered-collections` package provides `Map` and `Set` with proper logarithmic-time operations.

```purescript
-- Prefer: a Map built once, queried many times.
userMap :: Map UserId User
userMap = Map.fromFoldable $ map (\u -> Tuple u.id u) users

lookupUser :: UserId -> Maybe User
lookupUser = flip Map.lookup userMap

-- Over: linear scan on every lookup.
lookupUser :: UserId -> Array User -> Maybe User
lookupUser uid = find (\u -> u.id == uid)
```

The difference is not only performance. `Map` and `Set` make the intent legible: this is a collection keyed by something, or a collection of unique things. An `Array` that you happen to search linearly communicates nothing about its access pattern.

Build the `Map` at the boundary where the data arrives. Pass it inward. Do not convert back to `Array` for a function that will only look things up.

The same principle applies to other container types. If your data is a tree, use `Data.Tree` (from `rose-trees`). If it has graph structure — nodes with edges, cycles, dependencies — use a graph library rather than an `Array` of records with ID references. The container type documents the structure; the library provides the algorithms.


---


## 80. Use coerce for zero-cost newtype conversions

You may be surprised to learn that PureScript has a `coerce` function (not `unsafeCoerce` — the safe kind). How can that be? Because newtypes are erased at runtime, and `coerce` simply tells the compiler "these two types have the same runtime representation — trust me, and check." The compiler does check, and it is O(1).

```purescript
newtype Score = Score Int
derive instance Newtype Score _

rankings :: Array Score
rankings = [Score 42, Score 98, Score 71]

-- Prefer: O(1), the array is not traversed.
scores :: Array Int
scores = coerce (rankings :: Array Score)
-- scores == [42, 98, 71]

-- Over: O(n), mapping a function that does nothing at runtime.
scores :: Array Int
scores = map unwrap rankings
```

`coerce` works not only on arrays but on any type whose structure the compiler can verify as representationally identical: `Map k (Additive Int)` to `Map k Int`, `Maybe Score` to `Maybe Int`, nested combinations thereof.

The constraint is that the newtype constructor must be in scope — if a module exports the type but not its constructor, `coerce` correctly refuses to bypass the abstraction. This is the right behaviour: a newtype with a hidden constructor is enforcing an invariant, and stripping it silently would defeat the purpose.


---


## 81. But what if you don't want two newtypes to be coercible?

The previous entry explains how `coerce` works. But sometimes you want to *prevent* coercion — for example, when a newtype wraps mutable state and converting between them would be unsound.

This is what type roles are for. See entry 65 in the FFI section for the full treatment. The short version: if you declare `type role MutableRef nominal`, then `coerce :: MutableRef Int -> MutableRef String` becomes a type error. The `nominal` role says "these type parameters are significant, not just representational wrappers."

If you write a newtype that enforces an invariant via a smart constructor (entry 8), you probably want its role to be `nominal` too — otherwise `coerce` can bypass your smart constructor from any module that has the newtype constructor in scope.


---


## 82. Use Data.Newtype.un, over, and over2

The `Newtype` class provides generic functions for working with newtypes without importing or mentioning the constructor. This keeps code resilient to refactoring and avoids unnecessary coupling to a type's internal structure.

Prefer:

```purescript
adjustScore :: Score -> Score
adjustScore = over Score (_ * 2 + 1)

combineScores :: Score -> Score -> Score
combineScores = over2 Score (+)

readScore :: Score -> Int
readScore = un Score
```

Over:

```purescript
adjustScore :: Score -> Score
adjustScore (Score n) = Score (n * 2 + 1)

combineScores :: Score -> Score -> Score
combineScores (Score a) (Score b) = Score (a + b)

readScore :: Score -> Int
readScore (Score n) = n
```

The manual version is not wrong, but it repeats the constructor name at every use site. If `Score` is renamed or restructured, every pattern match must be updated. The `Newtype` functions work with any newtype -- they are parameterised by the class, not the constructor name.

For collections, this matters more: `map (over Score (_ + 1)) scores` reads as a single transformation, while `map (\(Score n) -> Score (n + 1)) scores` buries the intent in wrapping and unwrapping.


---


## 83. Use intercalate, not manual separator logic

Building a delimited string by folding with a conditional separator is a recurring source of off-by-one errors: an extra comma at the end, a missing comma at the start, special-casing the first or last element.

Prefer:

```purescript
intercalate "; " ["alpha", "beta", "gamma"]
-- "alpha; beta; gamma"
```

Over:

```purescript
foldlWithIndex
  (\i acc s -> if i == 0 then s else acc <> "; " <> s)
  ""
  ["alpha", "beta", "gamma"]
```

`intercalate` from `Data.Foldable` (for strings) or `Data.Array` (for arrays) handles the separator logic correctly and communicates intent in a single word. The fold version is four lines of control flow to achieve what a standard library function already does. This generalises: before writing separator logic, check whether `intercalate` or `joinWith` already exists for your type.


---


## 84. Use Tuple only for ephemeral pairs

`Tuple String Int` tells the reader nothing about which string or which int. It is a pair without identity — suitable for the intermediate steps of a pipeline, but not for data that persists, crosses a function boundary, or appears in a type signature that others must read.

```purescript
-- Ephemeral: fine for a fold accumulator.
wordCounts :: String -> Array (Tuple String Int)
wordCounts = words >>> map (\w -> Tuple w 1) >>> ...

-- Persistent: use a record.
type WordCount = { word :: String, count :: Int }

wordCounts :: String -> Array WordCount
```

The cost of a record over a `Tuple` is one type declaration and named fields instead of `fst`/`snd`. The return is that every access site documents itself — `entry.word` versus `fst entry` — and that adding a third field later is a refactor, not a rewrite. `Tuple` scales to pairs; records scale to whatever the domain requires.

A useful heuristic: if you would name the components when explaining the code aloud, name them in the code.


---


## 85. Use comparing for custom sort and comparison

`Data.Ord.comparing` exists to eliminate the boilerplate of writing comparison lambdas.

Prefer:

```purescript
sortBy (comparing _.age) users
```

Over:

```purescript
sortBy (\a b -> compare a.age b.age) users
```

The `comparing` version is one expression instead of four, and it reads as English: "sort by comparing age." For compound sort keys, compose with `<>` on the `Ordering` monoid:

```purescript
sortBy (comparing _.lastName <> comparing _.firstName) users
```

This sorts by last name first, breaking ties with first name — expressed as a single declarative statement rather than a nested comparison with fallback logic.


---


## 86. join <$> traverse is idiomatic

You have a function that returns a nested container — say, each node's children as an array — and you want to traverse a structure with it and flatten the result into a single container. There is no standard combinator for "traverse then flatten," but the idiom `join <$> traverse` does exactly this.

The naive approach builds a nested structure and then flattens it in a separate step:

```purescript
-- lookupChildren :: NodeId -> Aff (Array NodeId)

-- Naive: traverse, then flatten.
allChildren :: Array NodeId -> Aff (Array NodeId)
allChildren ids = do
  nested <- traverse lookupChildren ids
  -- nested :: Array (Array NodeId)
  pure (join nested)
```

The idiomatic version fuses the two steps:

```purescript
-- Idiomatic: join <$> traverse.
allChildren :: Array NodeId -> Aff (Array NodeId)
allChildren ids = join <$> traverse lookupChildren ids
-- traverse gives: Aff (Array (Array NodeId))
-- join flattens:  Aff (Array NodeId)
```

Recognise this pattern when you see it. It is the monadic generalisation of `concatMap`, lifted into an effectful context. (paf31, Nate Faubion)


---


## 87. Understand the PureScript String

PureScript's `String` is a JavaScript string. It is UTF-16 encoded, not a linked list of characters (Haskell's `String`), not a byte array (Rust's `&str`), and not a sequence of Unicode code points (Python 3's `str`).

This matters when you process text character by character. PureScript provides two modules:

- `Data.String.CodeUnits` operates on UTF-16 code units. A code unit is 16 bits. Characters outside the Basic Multilingual Plane — emoji, many CJK characters, mathematical symbols — occupy *two* code units (a surrogate pair).
- `Data.String.CodePoints` operates on Unicode code points. Each code point is one logical character, regardless of its UTF-16 encoding.

```purescript
import Data.String.CodeUnits as CU
import Data.String.CodePoints as CP

CU.length "hello" -- 5
CP.length "hello" -- 5

CU.length "\x1F600" -- 2 (surrogate pair)
CP.length "\x1F600" -- 1 (one code point)
```

If you use `CodeUnits.take 1` on a string that starts with an emoji, you get half a surrogate pair — a meaningless fragment. Use `CodePoints` when correctness over the full Unicode range matters. Use `CodeUnits` when you are interoperating with JavaScript APIs that expect UTF-16 indices (such as DOM selection ranges).

Know which module you are importing. The functions have the same names.


---


## 88. Why does Data.String.contains need Pattern?

If you are new to PureScript, you may wonder why `contains` does not just take two strings:

```purescript
-- This does not compile:
contains "needle" haystack

-- This does:
contains (Pattern "needle") haystack
```

The compiler will catch the mistake — `Pattern` is a newtype, not a type alias, so you cannot forget it. But the design choice is worth understanding. `Pattern` and `Replacement` exist so that `replaceAll (Pattern "old") (Replacement "new") source` cannot have its arguments silently swapped. Without the newtypes, both arguments would be `String`, and the transposition would compile happily.

This is entry 3 (Newtype what you mean) applied to the standard library. The library authors already made the decision for you — and you will see the same pattern in your own code once you start using newtypes for domain values.


---
