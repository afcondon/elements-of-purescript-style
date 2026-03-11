# PureScript Style Guide

Load idiomatic PureScript rules into context. These rules shape code generation — apply them to all PureScript code you write this session.

## Arguments

$ARGUMENTS

## Instructions

When invoked without arguments, confirm the rules are loaded and apply them to all PureScript code going forward. When invoked with a file path, review that file against the rules and suggest improvements.

## Rules

### Data modeling

**Use ADTs, not strings or booleans, for closed alternatives.**
`data Visibility = Visible | Hidden` not `Boolean`. `data Severity = Info | Warning | Error` not `String`.

**Use newtypes, not type aliases, for domain concepts.**
`newtype UserId = UserId Int` not `type UserId = Int`. Zero runtime cost; prevents argument transposition bugs. Derive instances with `derive newtype instance`.

**Use sum types to make illegal states unrepresentable.**
If a record has fields that can combine into nonsensical states (e.g. `status :: String` + `socket :: Maybe Socket`), replace it with a sum type where each constructor carries exactly the data it needs.

**Require `NonEmpty` when emptiness is impossible.**
`chooseBest :: NonEmptyArray Candidate -> Candidate` not `Array Candidate -> Maybe Candidate`.

**Use a function with pattern match, not a Map, for closed key sets.**
If every key is a constructor of a known ADT, pattern match. Reserve `Map` for open/dynamic keys.

**Constructor order is semantic.** When you derive `Ord`, constructors compare left-to-right as declared. Declare them in natural order.

### Pattern matching & control flow

**Use `case _ of`, not equational pattern matching.**
Prefer: `describe = case _ of Circle r -> ... ; Square s -> ...`
Over: `describe (Circle r) = ... ; describe (Square s) = ...`

**Use `case _ of`, not a named parameter you immediately case on.**
Prefer: `colorFor = case _ of Active -> ...`
Over: `colorFor status = case status of Active -> ...`

**Never use a wildcard `_ ->` on a closed ADT.** Spell out every constructor.

**Use guards for predicates, case for constructors.** Don't write `| isCircle s = ...` when you can pattern match on `Circle _`.

**End every guard chain with `otherwise`.**

**Prefer guards over nested if-then-else** for multi-branch conditions.

### Effects

**Use `when`/`unless`, not `if-then-pure unit`.**
Prefer: `when (Array.null items) do log "empty"`
Over: `if Array.null items then log "empty" else pure unit`

**Use `<$>` when you only transform the result.**
Prefer: `_.name <$> fetchUser id`
Over: `do { u <- fetchUser id; pure u.name }`

**Use `ado` for independent computations, `do` for dependent ones.**
If step 2 doesn't use the result of step 1, use `ado`. This enables concurrency in `Aff` and error accumulation in `Validation`.

**Use `parTraverse` for concurrent Aff.** Not manual `forkAff`/`joinFiber`.

**Use polymorphic monad constraints, not concrete Effect.**
Prefer: `getUser :: forall m. MonadEffect m => UserId -> m User`
Over: `getUser :: UserId -> Effect User`

**Use `Ref` only at application boundaries.** For local accumulation, use `StateT`, `foldl`, or `ST`.

**Newtype your transformer stacks.** `newtype AppM a = AppM (ReaderT Config Aff a)` with derived instances, not a type alias.

### FFI (JavaScript backend)

**Keep FFI files minimal.** One thin wrapper per foreign function. All logic in PureScript.

**Use `EffectFn`/`Fn` for uncurried FFI.** Don't curry foreign imports manually.

**Do not go point-free with `runFn`.** Write `joinPath a b = runFn2 impl a b`, not `joinPath = runFn2 impl`. Full saturation is required for inlining.

**Suffix foreign imports with `Impl`; do not export them.**

**Effect values are thunks.** In JS: `export function foo() { return () => sideEffect(); }` — the outer function takes args, the inner `() =>` is the Effect thunk.

**Parse, don't validate.** At the FFI boundary, import as `Effect Foreign` and decode. Never trust a foreign return type.

### Type classes

**ADTs for closed variants, type classes for open ad hoc polymorphism.** If you have one class, three instances, all in one module — that's a sum type.

**Minimize constraints.** Don't add `Eq a =>` unless the implementation actually compares `a` values.

**`Show` is for debugging, never serialization.** Use a codec for any data that crosses a boundary.

**Write functions over `Foldable`/`Traversable`, not concrete containers.** `total :: forall f. Foldable f => f Int -> Int` not `total :: Array Int -> Int`.

**Use `traverse`, not map-then-sequence.** Use `foldMap`, not map-then-fold.

**Give your containers `Functor`, `Foldable`, `Traversable` instances.**

### Codecs & serialization

**Use bidirectional codec values for JSON, not separate encode/decode instances.** `purescript-codec-argonaut` guarantees round-trip by construction. Codec values, not type class instances.

**Decode at the boundary, work with types internally.**

### Halogen

**Prefer render functions over components** when there's no internal state or lifecycle.

**Store minimal canonical state; derive the rest in `render`.**

**Name actions as events, not commands.** `SearchTermChanged String`, not `UpdateSearchResults String`.

### PureScript is not Haskell

**Use `<<<` for composition**, not `.` (which is record access).

**Write `derive instance`**, not `deriving`.

**Write explicit `forall`** on every polymorphic signature.

**Use `foldl` for strict accumulation.** PureScript is strict; `foldr` builds thunks.

**Use records, not tuples, for named data.** `{ x: 1, y: 2 }` not `Tuple 1 2`.

**Operator sections use `_`**: `(_ + 1)` not `(+ 1)`.

**No list literal syntax.** `[1, 2, 3]` is an `Array`, not a `List`.

### Style

**Always write type signatures on top-level declarations.**

**Use `$` and `#` to reduce parentheses, but don't chain excessively.**

**Avoid explicit recursion; use `foldl`, `traverse`, `foldMap`, etc.**

**Qualify container imports:** `import Data.Map as Map`, `import Data.Set as Set`.
