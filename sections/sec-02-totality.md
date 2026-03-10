# II. The rewards of totality

A total function handles every possible input. A partial function handles most of them and hopes for the best. PureScript's exhaustiveness checker, guard analysis, and non-empty types exist to help you write total functions — and to tell you when you have not. The entries in this section are variations on a single theme: leave no case unhandled.


---


## 20. Prefer case expressions over equational pattern matching

PureScript supports both equational-style pattern matching (multiple function clauses) and `case` expressions. The `case` form is more resilient to change.

Prefer:

```purescript
describe :: Shape -> String
describe = case _ of
  Circle r    -> "Circle with radius " <> show r
  Square s    -> "Square with side " <> show s
  Rect w h    -> show w <> " by " <> show h
```

Over:

```purescript
describe :: Shape -> String
describe (Circle r) = "Circle with radius " <> show r
describe (Square s) = "Square with side " <> show s
describe (Rect w h) = show w <> " by " <> show h
```

The equational form looks clean for simple cases. The trouble appears when you need to add a parameter. Adding a second argument to the equational version means rewriting every clause: `describe lang (Circle r) = ...`. In the `case` version, you add the parameter once: `describe lang = case _ of ...`.

The `case _ of` idiom also composes better with `let` bindings and `where` clauses -- the function body is a single expression, and shared helpers are scoped to it naturally.


---


## 21. Use case _ of, not a named parameter you immediately case on

When a function's entire body is a pattern match on its argument, use `case _ of` — the anonymous lambda-case form.

Prefer:

```purescript
colorFor :: Status -> String
colorFor = case _ of
  Active   -> "#2d5a27"
  Inactive -> "#999"
  Error    -> "#c23b22"
```

Over:

```purescript
colorFor :: Status -> String
colorFor status = case status of
  Active   -> "#2d5a27"
  Inactive -> "#999"
  Error    -> "#c23b22"
```

The name `status` appears twice and communicates nothing the type signature did not already say. The `case _ of` form signals immediately that this function is *defined by cases* — its entire purpose is dispatching on the structure of its argument. The reader need not scan for other uses of `status` in the body, because there is no `status` to scan for.

This applies only when the argument is used once, for pattern matching, and nothing else. If the function also passes the argument to another function or uses it in a guard, name it.


---


## 22. Prefer guards over if-then-else

Guards align conditions vertically, making the decision structure scannable. Nested `if-then-else` indents rightward and buries the structure.

Prefer:

```purescript
severity :: Int -> Severity
severity count
  | count > 100 = Critical
  | count > 10  = Warning
  | count > 0   = Info
  | otherwise   = None
```

Over:

```purescript
severity :: Int -> Severity
severity count =
  if count > 100 then Critical
  else if count > 10 then Warning
  else if count > 0 then Info
  else None
```

Use `if-then-else` for simple binary choices where a guard would be heavier than the expression it protects — a ternary-style inline decision within a larger expression. For anything with more than two branches, guards are clearer.


---


## 23. End every guard chain with otherwise

The compiler will not let you get away with incomplete guards. If you write:

```purescript
label :: Int -> String
label count
  | count > 0 = "positive"
  | count == 0 = "zero"
```

the compiler will insist on a catch-all:

```
A case expression could not be determined to cover all inputs.
The following additional cases are required to cover all inputs:

  _

Alternatively, add a Partial constraint to the type of the enclosing value.
```

This is the compiler doing its job. The fix is not to add a `Partial` constraint — that just pushes the problem to runtime. The fix is `otherwise`:

```purescript
label :: Int -> String
label count
  | count > 0  = "positive"
  | count == 0 = "zero"
  | otherwise  = "negative"
```

`otherwise` is simply `true`, but its presence signals intent: "I have considered all cases." Guards are for predicates on values — comparisons, Boolean tests, numeric ranges. When your branches correspond to constructors of an ADT, use a `case` expression instead (see entry 24).

The same logic applies to `case` expressions on ADTs: do not use a wildcard pattern when you can match every constructor explicitly. A wildcard silently accepts new constructors added later, which is precisely the bug exhaustiveness checking exists to prevent (see entry 1).


---


## 24. Do not write guards when you should case on an ADT

Guards are for predicates — conditions on values. When you find yourself writing guards that test equality against constructors, you are doing the pattern matcher's job by hand, and losing exhaustiveness checking in the process.

Prefer:

```purescript
describe :: Shape -> String
describe = case _ of
  Circle _ -> "round"
  Square _ -> "boxy"
  Rect _ _ -> "rectangular"
```

Over:

```purescript
describe :: Shape -> String
describe s
  | isCircle s = "round"
  | isSquare s = "boxy"
  | otherwise  = "unknown"  -- what is this hiding?
```

Notice that every branch in the guards entry above (entry 21) uses predicates on `Int` — comparisons, not constructors. That is the right use of guards. When your branches correspond to constructors of an ADT, use a `case` expression and spell them all out.


---


## 25. Require NonEmpty when emptiness is impossible

If a function only makes sense with at least one element, say so in the type. Do not accept a possibly-empty collection and then scramble to handle the empty case with a default value or a partial function.

```purescript
-- Prefer: the type guarantees at least one element.
chooseBest :: NonEmptyArray Candidate -> Candidate
chooseBest = maximumBy (comparing _.score)

-- Over: the Maybe infects every call site.
chooseBest :: Array Candidate -> Maybe Candidate
chooseBest = maximumBy (comparing _.score)
```

When you accept `Array` and return `Maybe`, you push the burden to the caller, who must handle `Nothing` even when they know the array is non-empty. When you accept `NonEmptyArray`, the caller must prove non-emptiness at the point of call — via `fromArray`, `cons'`, or construction — and thereafter the proof is carried in the type.

The same logic applies to `NonEmptyList`, `NonEmptyString`, and `NonEmpty f`. Wherever "this cannot be empty" is an invariant, encode it. Invariants maintained by convention are invariants waiting to be broken.


---


## 26. Use guard and Alternative for conditional failure

When a computation should fail if a condition is not met, `guard` expresses this directly in any `Alternative` context. The pattern is the same whether the context is `Maybe`, `List`, `Array`, or a parser.

Start with the simplest case — `Maybe`:

```purescript
lookupAdult :: Map Name Int -> Name -> Maybe Int
lookupAdult ages name = do
  age <- Map.lookup name ages
  guard (age >= 18)
  pure age
```

If the lookup fails, `Nothing`. If the guard fails, `Nothing`. No `if`/`else`, no explicit `Nothing` — each line is a precondition that must hold for the computation to continue.

The same idiom scales to richer contexts. In `Array`, `guard` filters:

```purescript
eligiblePairs :: Array User -> Array (Tuple User User)
eligiblePairs users = do
  u1 <- users
  u2 <- users
  guard (u1.id /= u2.id)
  guard (u1.role == Admin || u2.role == Admin)
  pure (Tuple u1 u2)
```

And in a parser, `guard` rejects input that is syntactically valid but semantically wrong:

```purescript
parsePort :: Parser String Int
parsePort = do
  n <- intDecimal
  guard (n > 0 && n <= 65535) <?> "port out of range"
  pure n
```

The underlying mechanism is `Alternative` — the type class that gives a computation a notion of failure (`empty`) and choice (`<|>`). `guard` is defined as `guard true = pure unit; guard false = empty`. Once you see it this way, the idiom transfers to any `Alternative` context you encounter.


---


## 27. Prefer Maybe over Boolean + separate value

When a value is meaningful only when some condition holds, represent it as `Maybe` — not as a `Boolean` flag with a separate field.

Prefer:

```purescript
type Selection = Maybe SelectionInfo
```

Over:

```purescript
type State =
  { hasSelection :: Boolean
  , selection :: Maybe SelectionInfo  -- NB: in a real codebase these fields may be far apart!
  }
```

The second version introduces an impossible state: `hasSelection` is `true` but `selection` is `Nothing`, or vice versa. Every function that touches this state must maintain the invariant that the two fields agree. `Maybe` encodes the invariant directly: `Just` means present, `Nothing` means absent. One field, no coordination, no impossible states.

This is a specific instance of the general principle from entry 6: if two fields must vary in lockstep, they are one field in disguise.


---


## 28. Use the strength of Maybe

Programmers arriving from JavaScript are accustomed to checking `if (x !== null)` and proceeding. The PureScript equivalent — pattern matching on `Just` and `Nothing` in every function — is correct but misses the point. `Maybe` has structure; use it.

Prefer:

```purescript
displayName :: Maybe User -> String
displayName = maybe "Anonymous" \u -> u.firstName <> " " <> u.lastName
```

Over:

```purescript
displayName :: Maybe User -> String
displayName user = case user of
  Just u  -> u.firstName <> " " <> u.lastName
  Nothing -> "Anonymous"
```

The goal is to keep values wrapped in `Maybe` as long as possible, operating on them through the interface, and unwrap only at the edge — when you render to the DOM, write to a log, or return a final result. `fromMaybe` provides a default at the boundary where you finally need a concrete value. Every early unwrap is a lost opportunity for the type system to track partiality on your behalf.

**For the curious.** `Maybe` is a functor, a monad, and an alternative — and knowing this unlocks more concise code. `map` transforms the value inside without touching `Nothing`. `bind` chains operations that might each fail. `<|>` expresses fallback: try this, and if it produces `Nothing`, try that. `traverse` runs an effectful function on the value if it exists and skips it if not. These are the same abstractions you will meet in `Either`, `Array`, and every other container in PureScript — learning them on `Maybe` pays compound interest.


---


## 29. Sometimes an ADT is a fixed map

Creating a `Maybe` and then immediately removing it is a smell. If you write `fromMaybe` right after `Map.lookup`, ask whether the lookup was necessary at all.

Here is the key insight: a function from an ADT is the same thing as a map with a fixed, known set of keys — except the compiler can verify that every key is handled. Pattern matching *is* the lookup. The compiler *is* the totality checker.

Prefer:

```purescript
colorFor :: Status -> String
colorFor = case _ of
  Active   -> "#2d5a27"
  Inactive -> "#999"
  Error    -> "#c23b22"
```

Over:

```purescript
colorFor :: Status -> String
colorFor s = fromMaybe "#000" $ Map.lookup s colors
  where
  colors = Map.fromFoldable
    [ Tuple Active "#2d5a27", Tuple Inactive "#999", Tuple Error "#c23b22" ]
```

Both versions map a `Status` to a `String`. But when you add a fourth constructor to `Status`, the pattern match will produce a compiler warning. The map will produce the wrong color, silently.

Reach for `Map` when the key set is open or dynamic (user IDs, file paths, configuration keys). Use a function with pattern matching when the key set is closed and known at compile time. The function version is simpler, faster, and checked.


---


## 30. Model domain errors as ADTs, not strings

When something goes wrong, the code that detects the failure knows what happened. A string error message flattens that knowledge into prose the caller cannot act on without parsing.

Prefer:

```purescript
data AppError
  = InvalidInput Field String
  | Unauthorized
  | ResourceNotFound ResourceId
  | RateLimited Instant

handleError :: AppError -> Effect Unit
handleError = case _ of
  InvalidInput field reason -> highlightField field *> showToast reason
  Unauthorized              -> redirectToLogin
  ResourceNotFound id       -> show404 id
  RateLimited retryAt       -> showRetryTimer retryAt
```

Over:

```purescript
handleError :: String -> Effect Unit
handleError msg
  | contains (Pattern "invalid") msg = showToast msg
  | contains (Pattern "unauthorized") msg = redirectToLogin
  | otherwise = showGenericError msg
```

The string version forces every consumer to reverse-engineer the producer's format. The ADT version lets the caller pattern-match on structure. Adding a new error case produces a compiler warning at every handler that has not been updated.

The thrower's job is to say what went wrong. The caller's job is to decide what to do about it. A string conflates both.


---
