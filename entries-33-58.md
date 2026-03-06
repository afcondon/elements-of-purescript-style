# The Elements of PureScript Style — Entries 33-58


---

## 33. Model domain errors as ADTs, not strings

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

## 34. Either short-circuits; know when that is what you want

`Either`'s `Bind` instance stops at the first `Left`. Each step sees the result of the previous one, and if any step fails, the rest never runs. This is exactly right for sequencing dependent operations.

```purescript
processOrder :: OrderInput -> Either AppError Receipt
processOrder input = do
  user    <- lookupUser input.userId       -- fails here? stop.
  address <- validateAddress user.address  -- depends on user
  charge  <- billCard user.card address    -- depends on both
  pure (Receipt charge address)
```

Each step genuinely depends on the previous one — you cannot validate the address without the user, and you cannot bill without both. `Either`'s short-circuiting is the correct behaviour here: there is nothing useful to do after a failure.

The mistake is reaching for `Either` when the checks are *independent* — see entry 34a.


---

## 34a. Use V (Validation) to accumulate independent errors

When checks do not depend on each other, `Either`'s short-circuiting is a disservice. A form with five bad fields should report all five, not make the user fix them one at a time.

`V` from `purescript-validation` has an `Apply` instance that accumulates errors using a `Semigroup`:

```purescript
import Data.Validation.Semigroup (V, invalid)

validateUser :: Input -> V (Array String) User
validateUser input = ado
  name  <- validateName input.name
  email <- validateEmail input.email
  age   <- validateAge input.age
  in { name, email, age }
```

With `Either`, this `ado` block would yield only the first failure. With `V`, all three checks run and all failures are collected. The `ado` notation makes the independence visible: each line binds from the input, not from a previous result.

`V` has no `Monad` instance — by design. You cannot write `do` notation with it, because `do` implies sequencing, and sequencing implies short-circuiting. The restriction is the feature.


---

## 35. Use ExceptT for expected failures, Aff's error for unexpected ones

`Aff` has a built-in error channel that carries JavaScript `Error` values. This is the right place for failures that indicate something has gone genuinely wrong -- a network socket closed, a file could not be read, memory was exhausted. These are not part of your domain; they are part of the runtime's.

Domain errors -- a user not found, a validation that failed, a permission denied -- are expected. They are part of the application's normal control flow. Layer `ExceptT` over `Aff` to keep them in the types:

```purescript
type AppM = ExceptT AppError Aff

fetchUser :: UserId -> AppM User
fetchUser uid = do
  response <- lift $ Fetch.get ("/users/" <> show uid)  -- network error stays in Aff
  case decodeUser response.body of
    Left err -> throwError (MalformedResponse err)       -- domain error in ExceptT
    Right user -> pure user
```

The separation pays off at the call site. An `Aff` error means something unexpected happened and you probably need to log it and show a generic message. An `ExceptT` error means something expected happened and you can handle it precisely. Mixing the two channels means every handler must inspect the error to decide which kind it is.


---

## 36. Do not catch exceptions you cannot handle

`try` converts an exception into an `Either`. This is useful when you have a meaningful response to the failure -- a fallback value, an alternative code path, a user-facing message. It is not useful when you intend to re-throw, log and crash, or immediately `fromRight`.

```purescript
-- This catches an exception only to make the failure harder to diagnose.
result <- try (loadConfig path)
config <- case result of
  Left err -> throwError (error $ "Config failed: " <> message err)
  Right c  -> pure c
```

The re-throw discards the original stack trace and replaces a specific exception with a vaguer one. The code would be clearer -- and the error more useful -- if the exception simply propagated.

Catch an exception when you can do something about it: retry, fall back, degrade gracefully. If you cannot, let it pass through. A caught-and-rethrown exception is not handled; it is laundered.


---

## 37. Use purescript-parsing for structured parsing, not regex

A regular expression can validate a pattern. A parser combinator can extract structure, report precise error positions, and compose with other parsers.

```purescript
-- Regex: validates shape but extracts nothing typed
isValidDate :: String -> Boolean
isValidDate = test (unsafeRegex "^\\d{4}-\\d{2}-\\d{2}$" noFlags)

-- Parser: validates, extracts, and composes
dateParser :: Parser String Date
dateParser = do
  year  <- intDigits 4
  _     <- char '-'
  month <- intDigits 2
  _     <- char '-'
  day   <- intDigits 2
  case mkDate year month day of
    Nothing -> fail "Invalid date"
    Just d  -> pure d
```

The parser version is longer but does more: it produces a `Date`, not a `Boolean`. It rejects `2024-13-45` where the regex accepts it. And it composes -- you can embed `dateParser` inside a larger parser for log lines, CSV rows, or configuration files without rewriting anything.

Use regex for quick guards at the boundary -- "does this look like an email?" Use `purescript-parsing` when you need to turn text into data.


---

## 38. Use codec for JSON, not hand-written decoders

A hand-written `EncodeJson` instance and a hand-written `DecodeJson` instance are two independent pieces of code that must agree on field names, nesting structure, and handling of optional values. They will disagree eventually.

`purescript-codec-argonaut` defines a single bidirectional codec that handles both directions:

```purescript
import Data.Codec.Argonaut as CA
import Data.Codec.Argonaut.Record as CAR

userCodec :: JsonCodec User
userCodec = CA.object "User" $ CAR.record
  { name: CA.string
  , email: CA.string
  , role: roleCodec
  }
```

The codec is the single source of truth. If it encodes a field as `"name"`, it decodes from `"name"`. Roundtripping is guaranteed by construction, not by the discipline of two separate authors (or the same author on two different days).

When you need custom handling -- a sum type encoded as a tagged string, a date encoded as ISO 8601 -- you write a codec for that type once, and it composes into every record and array codec that uses it.


---

## 39. Decode at the boundary, work with types internally

JSON, Foreign values, URL query parameters, and localStorage strings are external representations. They belong at the edge of your application -- the point where data enters or leaves. Inside the boundary, everything should be typed.

```purescript
-- At the boundary: decode once
fetchTasks :: Aff (Either JsonDecodeError (Array Task))
fetchTasks = do
  response <- Fetch.get "/api/tasks"
  pure $ decode (CA.array taskCodec) response.body

-- Inside the boundary: work with typed values
filterOverdue :: Array Task -> DateTime -> Array Task
filterOverdue tasks now = filter (\t -> t.due < now) tasks
```

If `filterOverdue` took `Json` and decoded internally, you would be decoding the same payload every time it was called, handling decode errors in a function that has nothing to say about malformed JSON, and hiding the fact that the real dependency is on `Task`, not `Json`.

Push the parse to the outermost layer. If a function three levels deep needs to decode JSON, the boundary is in the wrong place.


---

## 40. Prefer render functions over components

Not every piece of reusable HTML needs to be a Halogen component. A component carries overhead: a `State` type, an `Action` type, an `initialState`, a `handleAction`, lifecycle management, and a slot type at every use site. If the piece in question has no independent state and raises no actions, all of that machinery is waste.

A plain render function is simpler:

```purescript
-- A render function: no state, no lifecycle, no slot type
statusBadge :: forall w i. Status -> HH.HTML w i
statusBadge = case _ of
  Active   -> HH.span [ HP.class_ (ClassName "badge-active") ] [ HH.text "Active" ]
  Inactive -> HH.span [ HP.class_ (ClassName "badge-inactive") ] [ HH.text "Inactive" ]
```

Use a component when you need internal state, subscriptions, or effects in response to user interaction. Use a render function -- a value or function returning `HTML` -- when you are simply translating data into markup. The distinction is not about size; it is about whether the thing has behaviour of its own.


---

## 41. Store minimal canonical state; derive the rest in render

If a value can be computed from other state, compute it in `render`. Do not store it alongside the data it depends on.

```purescript
-- Derived state stored explicitly: can go stale
type State =
  { items :: Array Item
  , selectedItems :: Array Item   -- derived from items + selection
  , totalPrice :: Number          -- derived from selectedItems
  }

-- Minimal canonical state: nothing to synchronise
type State =
  { items :: Array Item
  , selectedIds :: Set ItemId
  }

render :: State -> HTML
render state =
  let
    selectedItems = filter (\i -> Set.member i.id state.selectedIds) state.items
    totalPrice = foldl (\acc i -> acc + i.price) 0.0 selectedItems
  in
    ...
```

Every piece of derived state is a synchronisation obligation. When you update `items`, you must remember to update `selectedItems` and `totalPrice`. Forget one, and the UI shows stale data with no compiler warning.

The canonical state is the smallest set of values from which everything else can be recomputed. Store that, and let `render` do the rest.


---

## 42. Model component actions as what happened, not what to do

Name actions after events, not effects. An action is a record of something that occurred; the handler decides what it means.

Prefer:

```purescript
data Action
  = SearchTermChanged String
  | ResultClicked ResultId
  | FilterToggled FilterType
  | PageLoaded
```

Over:

```purescript
data Action
  = UpdateSearchResults String
  | NavigateToResult ResultId
  | SetFilterAndRefresh FilterType
  | FetchInitialData
```

The first set describes what the user did. The second prescribes what the system should do, embedding implementation decisions in the type. When requirements change -- perhaps `FilterToggled` should now also log an analytics event -- the event-style action accommodates the change in the handler without renaming the action. The imperative-style action, `SetFilterAndRefresh`, must either be renamed (breaking every reference) or become a lie.

Actions named after events also compose better with parent-child communication. A parent receiving `ResultClicked` can decide independently what that means. A parent receiving `NavigateToResult` has already been told what to do.


---

## 43. Use when and unless, not if-then-pure-unit

When the else branch is `pure unit`, you are not making a choice — you are conditionally executing an effect. PureScript has a name for that.

Prefer:

```purescript
when (Array.null items) do
  log "No items found"
  showEmptyState
```

Over:

```purescript
if Array.null items
  then do
    log "No items found"
    showEmptyState
  else pure unit
```

`when` and `unless` (from `Control.Monad`) are not abbreviations; they are the precise statement of intent. The `if`/`else pure unit` version forces the reader to examine the else branch, confirm it does nothing, and then discard it. The `when` version says there is no else branch, and the reader moves on.

This applies in any monadic context — `Effect`, `Aff`, `StateT`, a Halogen `HalogenM` — anywhere you find yourself writing `else pure unit`.


---

## 44. Use guard and Alternative for conditional failure

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

## 45. Understand Apply vs Bind and choose deliberately

`Bind` (and `do` notation) sequences computations where each step may depend on the result of the previous one. `Apply` (and `ado` notation) combines computations that are independent.

```purescript
-- These two fetches do not depend on each other.
-- Bind sequences them needlessly.
do
  user    <- fetchUser uid
  friends <- fetchFriends uid
  pure { user, friends }

-- Apply declares their independence.
ado
  user    <- fetchUser uid
  friends <- fetchFriends uid
  in { user, friends }
```

The distinction is not merely semantic. In `Aff`, `Apply` can run both fetches concurrently via `parApply`. In `Validation`, `Apply` accumulates errors from both branches. In a free monad, `Apply` enables static analysis of the computation's structure. `Bind` forecloses all of these because it promises the second computation may depend on the first.

Use `do` when there is a genuine dependency -- when the URL you fetch in step two is computed from the result of step one. Use `ado` when you are simply gathering independent results. The types are telling the truth either way; the question is whether you are.


---

## 46. Use Data.Newtype.un, over, and over2

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

## 47. Use explicit export lists

A module without an export list exports everything: public API, internal helpers, partially-applied constructors, and any re-exports you did not intend. This is rarely what you want.

```purescript
-- Exports everything, including helpers the caller should not depend on.
module MyApp.Parser where

-- Exports exactly the public API.
module MyApp.Parser
  ( parse
  , ParseError(..)
  , ParseResult
  ) where
```

An explicit export list serves three purposes. It tells the reader what the module is for, without requiring them to scan the entire file. It lets you refactor internal functions freely, knowing that no downstream code depends on them. And it prevents accidental coupling -- the kind that only surfaces when you try to move a helper function and discover six modules importing it.

Export data constructors with `(..)` when callers need to pattern match. Export only the type name when you want to preserve the ability to change the representation.


---

## 48. Use explicit imports or qualified imports

When you read `head xs` in a module with `import Data.Array` and `import Data.List`, you cannot tell which `head` is being called without checking the types. When you read `Array.head xs`, you can.

Prefer:

```purescript
import Data.Array as Array
import Data.Map (lookup, insert)
import Data.String.CodeUnits (length)
```

Over:

```purescript
import Data.Array
import Data.Map
import Data.String.CodeUnits
```

Open imports make the provenance of every name ambiguous. The compiler resolves it, but the reader must do extra work — or rely on an IDE — to do the same. Explicit imports also make unused dependencies visible: if you remove the last use of `insert`, the import stands out as dead code.

The Prelude is the most common open import, and its contents (`map`, `bind`, `show`, `pure`, `unit`) are ubiquitous enough that qualifying them adds noise. But even Prelude is not sacred — when working heavily with a library whose names clash with Prelude, it can be clearer to import Prelude explicitly and open-import the library instead. Use `hiding` to suppress specific Prelude names that clash rather than qualifying every use. The principle is always the same: make it obvious where each name comes from.


---

## 49. Always write type signatures on top-level declarations

The PureScript compiler infers types, but inference is a convenience for the author, not a service to the reader. A top-level binding without a type signature is a function whose contract must be reverse-engineered from its implementation.

```purescript
-- The reader must trace through the body to learn what this accepts and returns.
buildIndex entries =
  Map.fromFoldable $ map (\e -> Tuple e.id e) entries

-- The contract is stated up front.
buildIndex :: Array Entry -> Map EntryId Entry
buildIndex entries =
  Map.fromFoldable $ map (\e -> Tuple e.id e) entries
```

The compiler warns on missing signatures for good reason. Without one, a small change to the implementation can silently change the inferred type, which in turn changes the type expected by every caller. A signature pins the contract. If the implementation no longer matches, the error appears where the change was made, not somewhere downstream.

Write the signature first. It is the function's spec.

One powerful technique: after writing the implementation, *comment out* the signature and rebuild. The compiler will warn about the missing signature and show you what it inferred. If the inferred type is more general than what you wrote — `Foldable f => f a` where you wrote `Array a`, or `Semiring a =>` where you wrote `Int` — you may be over-constraining your function. The compiler often knows more than you do about what your code actually requires.


---

## 50. Keep warnings under control

The PureScript compiler's warnings are precise: unused imports, missing type signatures, shadowed names, redundant patterns, incomplete binds. Most identify code that is wrong, dead, or unclear.

In `spago.yaml`, you can enforce this:

```yaml
package:
  build:
    censor_warnings:
      - WildcardInferredType
    strict: true
```

A codebase with a dozen warnings trains its authors to ignore the thirteenth — which might be the one that matters. The goal is that every warning is either fixed or consciously suppressed with a reason.

That said, "zero warnings always" is a guideline, not a law. Shadowed name warnings, for instance, are sometimes a sign of clear code — a `let` rebinding a function parameter with the same name after validation is arguably *more* readable than inventing a new name. The `censor_warnings` mechanism exists precisely so you can make deliberate, documented decisions about which warnings matter in your codebase. The sin is not having warnings; it is having warnings nobody looks at.


---

## 51. Use records with named fields when three or more arguments share a type

When a function takes multiple arguments of the same type, the compiler cannot protect you from transposition. The caller can, if the arguments have names.

Prefer:

```purescript
createUser :: { name :: String, email :: String, role :: String } -> Effect User
```

Over:

```purescript
createUser :: String -> String -> String -> Effect User
```

The positional version permits `createUser "admin" "alice@x.com" "Alice"` and the compiler will not object. The record version makes each field self-documenting at the call site: `createUser { name: "Alice", email: "alice@x.com", role: "admin" }`.

This is not a blanket rule against curried functions. `filter :: (a -> Boolean) -> Array a -> Array a` benefits from currying because the two arguments have different types and partial application is natural. The rule applies when the types alone do not distinguish the arguments and human memory is the only safeguard.

For even stronger protection, combine records with newtypes: `{ name :: Name, email :: Email, role :: Role }`.


---

## 52. Use row polymorphism instead of concrete record types in library APIs

PureScript's row polymorphism lets a function require specific fields without constraining the rest of the record. This is a feature worth using at module boundaries.

Prefer:

```purescript
renderWidget :: forall r. { label :: String, onClick :: Effect Unit | r } -> HTML
```

Over:

```purescript
type WidgetProps = { label :: String, onClick :: Effect Unit }

renderWidget :: WidgetProps -> HTML
```

The closed record forces every caller to construct exactly `{ label, onClick }` and nothing more. The open record accepts any record that has at least those fields -- callers with additional fields do not need to destructure and rebuild.

This matters most in libraries and shared modules where you cannot predict every calling context. Within a single application module, a closed record is often fine -- you control both sides. The principle is: require what you need, accept what you are given.


---

## 53. Prefer case expressions over equational pattern matching

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

## 54. Write property-based tests, not just examples

An example test says "this input produces this output." A property test says "for all inputs satisfying these constraints, this relationship holds." The second finds bugs the first never will, because it explores inputs the author did not think to try.

```purescript
-- Example: tests one case
it "decodes what it encodes" do
  let user = { name: "Alice", role: Admin }
  decode userCodec (encode userCodec user) `shouldEqual` Right user

-- Property: tests the relationship for all generated users
quickCheck \(user :: User) ->
  decode userCodec (encode userCodec user) === Right user
```

The property version requires an `Arbitrary User` instance, which forces you to think about the space of valid inputs -- itself a useful exercise. It then generates hundreds of random users, including edge cases (empty strings, boundary values, unusual characters) that a hand-written example would never include.

Good candidates for property tests: codec roundtrips, monoid laws (`mempty <> x === x`), idempotency (`f (f x) === f x`), commutativity, and ordering consistency. These are universal relationships, and testing them universally is what property-based testing is for.


---

## 55. Use the type system to make illegal states unrepresentable

If two fields in a record are correlated -- one is meaningful only when the other has a certain value -- they should not be independent fields. They should be a sum type.

Prefer:

```purescript
data Connection
  = Disconnected
  | Connecting Url
  | Connected Url Socket
  | Failed Url Error
```

Over:

```purescript
type Connection =
  { status :: String          -- "disconnected" | "connecting" | "connected" | "failed"
  , url :: Maybe Url
  , socket :: Maybe Socket
  , error :: Maybe Error
  }
```

The record version permits states that should not exist: a `"disconnected"` connection with a socket, a `"failed"` connection with no error, a `"connecting"` connection with no URL. Every function that consumes a `Connection` must defend against these impossible combinations, or trust that no code produces them. The sum type eliminates the combinations at the type level. Each constructor carries exactly the data that is meaningful in that state, no more.

This is entry 7 taken to its conclusion. It is not enough to use ADTs for enumerated values; use them for correlated state. Wherever you find a `Boolean` or `String` flag accompanied by `Maybe` fields that are "only valid when the flag is true," a sum type is waiting to be extracted.


---

## 56. Smart constructors: export the type, not the constructor

When a type has an invariant that the type system cannot express directly, enforce it with a smart constructor. Export the type and the constructor function, but not the data constructor.

```purescript
module App.Types.Email
  ( Email         -- type only, no constructor
  , mkEmail       -- smart constructor
  , unEmail       -- accessor
  ) where

newtype Email = Email String

mkEmail :: String -> Maybe Email
mkEmail s
  | contains (Pattern "@") s && length s > 3 = Just (Email s)
  | otherwise = Nothing

unEmail :: Email -> String
unEmail (Email s) = s
```

Consumers of this module can create an `Email` only through `mkEmail`, which validates the invariant. They cannot write `Email "not-an-email"` because the `Email` constructor is not exported. Every `Email` value in the program is guaranteed to have passed validation.

This pattern composes well with `Newtype` deriving. Inside the module, you have full access to the constructor for implementing functions. Outside, the abstraction is sealed. The cost is one module boundary; the benefit is that the invariant is enforced once and relied upon everywhere.

This is "make illegal states unrepresentable" (entry 55) applied at the boundary: you cannot prevent the outside world from handing you `"not-an-email"`, but you can ensure that if someone has an `Email`, it is a validated thing and not a ghastly string.


---

## 57. Use STRef with ST.run for locally-scoped mutation

When an algorithm needs mutable state for performance -- building an array in a loop, accumulating into a hash map, running an in-place sort -- `ST` gives you mutation with a pure interface.

```purescript
import Control.Monad.ST as ST
import Control.Monad.ST.Ref as STRef

histogram :: Array Int -> Array Int
histogram values = ST.run do
  counts <- STRef.new (Array.replicate 256 0)
  for_ values \v -> do
    STRef.modify (\arr -> Array.modifyAt v (_ + 1) arr # fromMaybe arr) counts
  STRef.read counts
```

The rank-2 type of `ST.run` -- `(forall h. ST h a) -> a` -- guarantees that the mutable reference cannot escape the block. The result is a pure value. Callers see `histogram :: Array Int -> Array Int`; they cannot tell that mutation was used internally, and they do not need to.

This is the right tool when you need imperative performance characteristics inside a pure function. It is not a license to write imperative PureScript everywhere — most code does not need mutable state. But when the alternative is threading an accumulator through a hundred recursive calls, `ST` is both faster and clearer.

There is a larger lesson here. It is not the case that a purely functional language *cannot* handle mutation — it handles it with explicit, scoped, type-checked tools like `ST`. The discipline is not avoidance; it is acknowledgement. When you use `ST`, you are forced to think about the scope and lifetime of your mutation, and the type system ensures the answer is sound. Contrast this with a language where every variable is mutable by default and the discipline is "just be careful."


---

## 58. Prefer Ref only at application boundaries

`Effect.Ref` is mutable state in `Effect`. It is the right tool for state shared between independent event handlers -- a WebSocket connection pool, a cache that outlives a single request, a counter incremented by callbacks from different sources.

It is not the right tool for state within a single computation.

Prefer:

```purescript
-- State threaded through a computation: use StateT or a fold
processItems :: Array Item -> State Summary Unit
processItems = traverse_ \item ->
  modify_ (addToSummary item)
```

Over:

```purescript
-- Mutable ref where none is needed
processItems :: Array Item -> Effect Summary
processItems items = do
  ref <- Ref.new emptySummary
  for_ items \item ->
    Ref.modify_ (addToSummary item) ref
  Ref.read ref
```

The `Ref` version works, but it is Effect-bound for no reason. The computation has a single thread of control and produces a single result -- exactly the scenario where `State`, `foldl`, or `ST` serves better. The `Ref` version forces every caller into `Effect`, prevents the logic from being tested purely, and hides the fact that the mutation is strictly local.

Reserve `Ref` for genuinely shared, long-lived mutable state at the edges of your application. For everything else, PureScript offers better tools.
