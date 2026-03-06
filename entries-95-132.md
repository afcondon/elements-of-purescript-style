# The Elements of PureScript Style — Entries 95-132


---

## 95. Design the types first, write the functions second

Before writing any logic, define your data types. Sketch the ADTs, the records, the newtypes. Write the type signatures for the functions you will need. Then — and only then — fill in the implementations.

This is not ceremony. It is discovery. A type signature is a contract between your function and the rest of the program, and writing it first forces you to answer the hard questions early: What does this function need? What does it produce? What can go wrong? If you cannot write the signature, you do not yet understand the problem.

Often, once the types are right, the implementation is obvious — sometimes uniquely determined. A function `Array (Tuple k v) -> Map k v` has essentially one reasonable implementation. A function `forall f a b. Functor f => (a -> b) -> f a -> f b` has exactly one. The types do the thinking; the programmer merely transcribes.

When the types are wrong, no amount of clever logic will save you. You will write validation functions to compensate for missing structure, default values to paper over impossible states, and runtime checks that the compiler should have handled at compile time. Fix the types and the functions simplify themselves.


---

## 96. Sum types for "or", product types for "and"

A value is either one thing or another: sum type. A value has both this and that: product type (typically a record).

```purescript
-- "A request is either pending, succeeded, or failed."
data Request a
  = Pending
  | Succeeded a
  | Failed String

-- "A point has both an x-coordinate and a y-coordinate."
type Point = { x :: Number, y :: Number }
```

This sounds trivial, but programmers arriving from object-oriented languages systematically reach for inheritance hierarchies where a sum type is the correct model. In Java, you might write an abstract `Shape` class with `Circle` and `Rectangle` subclasses, then discover you cannot exhaustively match on them without `instanceof` checks. In PureScript, `data Shape = Circle Number | Rectangle Number Number` gives you exhaustiveness checking for free.

The same principle applies to product types. If you find yourself passing five related arguments to every function, that is a record waiting to be named. And if you find yourself writing a record where half the fields are `Maybe` because they only apply to certain variants — that is a sum type buried inside a product type, struggling to get out.


---

## 97. Phantom types: tag without data

A phantom type parameter appears in a type's signature but not in its runtime representation. It exists solely to let the compiler distinguish values that are identical at runtime but different in meaning.

```purescript
newtype Id (entity :: Type) = Id String

derive newtype instance Eq (Id a)
derive newtype instance Ord (Id a)

lookupUser :: Id User -> UserMap -> Maybe User
lookupOrder :: Id Order -> OrderMap -> Maybe Order

-- This compiles:
lookupUser userId users

-- This does not:
lookupUser orderId users
-- Type error: Id Order does not unify with Id User
```

At runtime, both `Id User` and `Id Order` are plain strings. The `User` and `Order` parameters are erased during compilation; they cost nothing in memory or execution time. But the compiler treats them as distinct types, which means you cannot accidentally pass an order ID where a user ID is expected.

The technique is especially valuable in codebases where multiple entity types share the same underlying identifier format. Without phantom types, you rely on variable naming conventions — `userId`, `orderId` — to keep them straight. Conventions are suggestions; types are walls.


---

## 98. Use the strength of Maybe

Programmers arriving from JavaScript are accustomed to checking `if (x !== null)` and proceeding. The PureScript equivalent — pattern matching on `Just` and `Nothing` in every function — is correct but misses the point. `Maybe` is a functor, a monad, and an alternative. It has structure; use it.

```purescript
-- Pattern matching everywhere: correct, but verbose.
displayName :: Maybe User -> String
displayName user = case user of
  Just u  -> u.firstName <> " " <> u.lastName
  Nothing -> "Anonymous"

-- Using the structure of Maybe.
displayName :: Maybe User -> String
displayName = maybe "Anonymous" \u -> u.firstName <> " " <> u.lastName
```

`map` transforms the value inside without touching the `Nothing` case. `bind` lets you chain operations that might each fail. `<|>` expresses fallback: try this, and if it produces `Nothing`, try that. `traverse` lets you run an effectful function on the value if it exists and skip it if not. `fromMaybe` provides a default at the boundary where you finally need a concrete value.

The goal is to keep values wrapped in `Maybe` as long as possible, operating on them through the interface, and unwrap only at the edge — when you render to the DOM, write to a log, or return a final result. Every early unwrap is a lost opportunity for the type system to track partiality on your behalf.


---

## 99. Alt and Alternative: first success wins

The `<|>` operator tries the left side; if it fails (produces `Nothing`, an empty array, a parse failure), it tries the right. This works for any type with an `Alt` instance, and it is the natural way to express fallback chains.

```purescript
-- A cascade of lookups, most specific to least.
resolveConfig :: String -> Effect String
resolveConfig key =
  lookupEnv key
    <|> lookupFile configPath key
    <|> pure defaultValue
```

For `Maybe`, failure means `Nothing`. For parsers, failure means a failed parse. For arrays, `<|>` is concatenation — all successes, not just the first. The semantics vary by type, but the shape is always the same: try alternatives in order, combine the results according to the type's notion of success and failure.

`<|>` composes. Where an `if-then-else` chain or a nested `case` expression grows linearly and indents rightward, a chain of `<|>` stays flat. And because it is an operator on a type class, you can write functions that are polymorphic in the choice strategy — the same fallback logic works with `Maybe`, with parsers, with validation.


---

## 100. Applicative for building, Monad for deciding

If every part of a computation can proceed independently, use `Applicative` (or `ado` notation). If the next step depends on the result of the previous one, you need `Monad`.

```purescript
-- Applicative: all fields are computed independently.
mkUser :: Validation Errors User
mkUser = ado
  name  <- validateName rawName
  email <- validateEmail rawEmail
  age   <- validateAge rawAge
  in { name, email, age }

-- Monadic: the second query depends on the first result.
fetchProfile :: Aff Profile
fetchProfile = do
  user    <- fetchUser userId
  friends <- fetchFriends user.friendListId  -- needs user first
  pure { user, friends }
```

The distinction is not merely stylistic. `Validation` has an `Applicative` instance but deliberately lacks a `Monad` instance, because it needs to evaluate all fields to collect all errors. If it were monadic, a failure in `validateName` would short-circuit and you would never learn that `validateEmail` also failed. The type class hierarchy encodes a real semantic difference: applicative computations have a static structure; monadic computations have a dynamic one.

When you reach for `do` notation, ask whether each bind genuinely depends on a previous result. If the answer is no — if you are merely building up a record from independent parts — `ado` is both more honest and more powerful.


---

## 101. Do not use Show for serialisation

`Show` is for debugging. Its output format is not stable across compiler versions, not specified by any standard, and not guaranteed to be parseable. A `Show` instance is a convenience for the REPL and for log messages during development. It is not a serialisation format.

```purescript
-- Wrong: Show in production output.
saveConfig :: Config -> Effect Unit
saveConfig config = writeFile "config.txt" (show config)

-- Right: explicit serialisation.
saveConfig :: Config -> Effect Unit
saveConfig config = writeFile "config.json" (stringify $ encodeConfig config)
```

If you need to serialise a value, write a codec — `purescript-codec-argonaut`, `purescript-yoga-json`, or a hand-rolled encoder. If you need a human-readable label for a UI, write a `display` function with an explicit, documented format. `Show` instances should appear in debug logs and test failure messages; they should never appear in data that crosses a process boundary, a network, or a file system.

The temptation is strongest with simple types — `show myEnum` produces something that looks reasonable today. But "today" is the operative word. When you add a constructor, rename one, or change the `Show` instance for readability, every consumer of that serialised string breaks silently.


---

## 102. Optics: a lens is a getter and a setter that agree

If you find yourself writing paired functions — `getField` and `setField`, or `readNested` and `updateNested` — you have half a lens. The `profunctor-lenses` library gives you composable access paths into nested structures, and the two halves are guaranteed to agree because they are one value, not two.

```purescript
-- Without optics: manual nesting.
updateCity :: String -> Company -> Company
updateCity city company =
  company { headquarters = company.headquarters { address = company.headquarters.address { city = city } } }

-- With optics: compose the path.
_city :: Lens' Company String
_city = prop (Proxy :: _ "headquarters") <<< prop (Proxy :: _ "address") <<< prop (Proxy :: _ "city")

updateCity :: String -> Company -> Company
updateCity = set _city
```

Start with record lenses (`prop`), `_Just` for `Maybe`, and `_Left`/`_Right` for `Either`. These cover the majority of real-world nesting. Prisms, isos, and traversals are powerful but rarely needed in application code — reach for them when the simpler tools fall short, not before.

The deeper value of optics is composability. A lens into a record field and a prism into a sum type constructor compose with `<<<` into an optic that focuses through both layers. You build complex access paths from simple, tested pieces, and each piece can be reused independently.


---

## 103. Use Tuple only for ephemeral pairs

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

## 104. Write the simplest code that the types permit

This is the principle that governs all the others. If the compiler accepts your code and the meaning is clear to a reader, the code is good enough. Do not add type-level machinery to enforce an invariant the code already maintains. Do not abstract over a pattern that occurs once. Do not reach for a monad transformer when a function argument will do.

Simplicity in PureScript is not the same as simplicity in JavaScript. A sum type with four constructors is simple. A `newtype` with a smart constructor is simple. An `ado` block that validates five fields independently is simple. These are not complexity — they are precision. The type system lets you say exactly what you mean, and saying exactly what you mean is the simplest thing you can do.

The temptation runs in the other direction. PureScript offers type classes, higher-kinded types, row polymorphism, phantom types, functional dependencies, and enough abstraction machinery to build cathedrals. It is always possible to make code more general, more abstract, more reusable. But generality that serves no current need is not simplicity — it is speculation, and speculation has a carrying cost: every reader must understand the abstraction to understand the code.

Write a concrete function. When a second use case appears, extract the commonality. When a third appears, consider a type class. This is not timidity; it is empiricism. The simplest code that the types permit is not the least sophisticated code you could write — it is the least sophisticated code that still captures every distinction the problem demands. The type system is your ally in this: it will refuse code that conflates things that differ. Trust it, and do not add a second enforcer where one suffices.


---

## 105. Generating random values: use Effect.Random, not unsafePerformEffect

Random number generation is an effect. It reads from a source of entropy, which is external state by definition. Wrapping it in `unsafePerformEffect` to get a "pure" random value is not pure — it is a lie that the compiler cannot detect but your program's behaviour will eventually reveal.

```purescript
-- Wrong: pretending randomness is pure.
randomColor :: String
randomColor = unsafePerformEffect do
  i <- randomInt 0 5
  pure (colors !! i)

-- Right: acknowledging the effect.
randomColor :: Effect String
randomColor = do
  i <- randomInt 0 5
  pure (fromMaybe "#000" (colors !! i))
```

Use `Effect.Random` for one-off random values in effectful code. Use `MonadGen` and `Gen` for property-testing generators, where you need controlled, reproducible randomness from a seed. If you need deterministic "randomness" for a pure function — procedural generation, shuffling with a known seed — pass the seed explicitly and use a pure PRNG. The type signature should always tell the truth about where the entropy comes from.


---

## 106. CLI argument parsing: use optparse, not hand-rolled case matching on argv

`purescript-optparse` gives you typed argument parsing with help text generation, subcommands, default values, and validation — all derived from a declarative description of your interface.

```purescript
-- Hand-rolled: fragile, undocumented, silently wrong.
main :: Effect Unit
main = do
  args <- Process.argv
  case args !! 2, args !! 3 of
    Just "--input", Just path -> run path
    _, _ -> log "Usage: mytool --input <path>"

-- Structured: self-documenting, validated, composable.
opts :: Parser Options
opts = ado
  input <- strOption (long "input" <> metavar "PATH" <> help "Input file")
  verbose <- switch (long "verbose" <> help "Enable verbose output")
  in { input, verbose }
```

Manually indexing into `process.argv` produces code that is fragile when arguments are reordered, undocumented when someone passes `--help`, and silently wrong when optional arguments shift the indices. A declarative parser describes the interface once and derives both the parsing logic and the usage message from that single description.

Even for tools with only one or two arguments, the structured approach costs less than the debugging session you will eventually have when someone passes the arguments in the wrong order.


---

## 107. Date and time: use the types, not epoch integers

Passing `Int` or `Number` for timestamps invites an entire category of arithmetic errors: milliseconds versus seconds, timezone-unaware subtraction, comparing instants with durations.

```purescript
-- Opaque integers: what unit? what timezone? who knows.
isExpired :: Int -> Int -> Boolean
isExpired expiresAt now = now > expiresAt

-- Typed: the units and semantics are in the types.
isExpired :: Instant -> Instant -> Boolean
isExpired expiresAt now = now > expiresAt

timeUntilExpiry :: Instant -> Instant -> Duration
timeUntilExpiry expiresAt now = diff expiresAt now
```

Use `DateTime` for calendar dates and times, `Instant` for points on the UTC timeline, and `Duration` or `Milliseconds` for differences between them. The date and time libraries (`purescript-datetime`, `purescript-now`) provide these types with the arithmetic you need. The compiler will prevent you from adding an `Instant` to an `Instant` or subtracting a `Duration` from a `Date` — errors that are trivially easy with bare integers and surprisingly common in production code.

Convert to and from epoch integers at the boundary: when reading from a database, an API response, or a JavaScript interop call. Inside your program, let the types carry the meaning.


---

## 108. Regular expressions: compile once, use many

`Regex.regex` returns `Either String Regex` because the pattern string might be syntactically invalid. This is a check that needs to happen once, not on every use.

```purescript
-- Wrong: recompiling inside a map.
extractNumbers :: Array String -> Array (Maybe (NonEmptyArray Match))
extractNumbers = map \s ->
  case regex "\\d+" noFlags of
    Left _  -> Nothing
    Right r -> match r s

-- Right: compile once, reuse.
numberPattern :: Regex
numberPattern = unsafePartial $ fromRight $ regex "\\d+" noFlags

extractNumbers :: Array String -> Array (Maybe (NonEmptyArray Match))
extractNumbers = map (match numberPattern)
```

If the pattern is a literal known at compile time, `unsafePartial $ fromRight` is justified — you are asserting that the string is a valid regex, and if it is not, the crash at startup is the correct behaviour. For patterns constructed from user input, handle the `Left` case properly and compile once at the point of input, passing the compiled `Regex` value to everything downstream.

Compiling a regex is not expensive in absolute terms, but doing it inside a tight loop is the kind of unnecessary work that accumulates quietly until profiling reveals it.


---

## 109. HTTP requests: decode the response, do not assume its shape

An HTTP response body is a `String` or an `ArrayBuffer`. It is not your domain type. The gap between the wire format and your types is where every integration bug lives, and a codec is the firewall.

```purescript
-- Wishful thinking: assuming the response matches.
fetchUser :: Int -> Aff User
fetchUser id = do
  response <- get json ("/api/users/" <> show id)
  pure response.body  -- What if the shape changed?

-- Defensive: decode explicitly, handle failure.
fetchUser :: Int -> Aff (Either JsonDecodeError User)
fetchUser id = do
  response <- get string ("/api/users/" <> show id)
  pure $ decodeUser response.body
```

The server will eventually change its response format — a field will be renamed, a nullable field will appear, an envelope will be added. Your decoder is the single place where that change surfaces as an error rather than propagating silently through your application as a wrong value in the right type.

Write the decoder alongside the request function. Test it against example responses. When the API changes, the decoder fails loudly and locally, not quietly and everywhere.


---

## 110. File I/O in Node: use the Aff wrappers, not raw FFI

`purescript-node-fs-aff` wraps Node's `fs` module with `Aff`-based functions that handle callbacks, errors, and cancellation correctly. Using the callback-based FFI directly means reimplementing all of this by hand.

```purescript
-- Raw FFI: you own the callback, the error handling, and the cancellation.
foreign import readFileImpl :: String -> (String -> Effect Unit) -> (Error -> Effect Unit) -> Effect Unit

-- Aff wrapper: all of that is handled.
import Node.FS.Aff (readTextFile)

contents <- readTextFile UTF8 "/path/to/file"
```

`Aff` gives you structured error handling with `try` and `catchError`, automatic resource cleanup with `bracket`, and cancellation propagation through `forkAff`. Writing raw callback-based FFI means giving up all three and rebuilding them ad hoc, or more likely, not rebuilding them and discovering the gap in production.

The same principle applies to any Node API that uses callbacks. If an `Aff` wrapper exists in the ecosystem, use it. If one does not, write a small wrapper using `makeAff` and contain the callback machinery in one place.


---

## 111. Logging: use structured data, not string concatenation

String-concatenated log messages are easy to write and hard to use. They cannot be filtered, queried, or parsed reliably. They embed formatting decisions at every call site, making global changes to log format impossible.

```purescript
-- Unstructured: ungreppable, inconsistent, fragile.
log ("User " <> show userId <> " logged in at " <> show timestamp <> " from " <> ipAddress)

-- Structured: a record you can format, filter, and forward.
type LogEntry =
  { level     :: LogLevel
  , event     :: String
  , userId    :: UserId
  , timestamp :: Instant
  , metadata  :: Map String String
  }

logEvent { level: Info, event: "login", userId, timestamp, metadata: Map.singleton "ip" ipAddress }
```

At minimum, define a `LogEntry` record and a single formatting function. Better, use a logging library that accepts structured data and routes it to the appropriate sink. The point is not sophistication — it is that the log format is defined in one place, not scattered across every `log` call in the codebase.

Structured logging also makes the logging surface greppable in the source code. `logEvent` with a known record type is easy to find; `log ("User " <> ...)` in forty variations is not.


---

## 112. Environment variables: read at startup, not on demand

Do not sprinkle `lookupEnv` calls throughout your codebase. Each one is an implicit dependency on external state — invisible in the type signature, untestable without modifying the environment, and discovered only at the moment of execution.

```purescript
-- Scattered: each module reads what it needs, when it needs it.
connectDb :: Aff Connection
connectDb = do
  host <- liftEffect $ lookupEnv "DB_HOST"
  port <- liftEffect $ lookupEnv "DB_PORT"
  ...

-- Gathered: read once, validate, pass explicitly.
type Config =
  { dbHost :: String
  , dbPort :: Int
  , logLevel :: LogLevel
  }

readConfig :: Effect (Either String Config)
readConfig = do
  dbHost <- lookupEnv "DB_HOST"
  dbPort <- lookupEnv "DB_PORT"
  ...

main :: Effect Unit
main = do
  config <- readConfig >>= either die pure
  runApp config app
```

Read all environment variables in `main`. Validate them — a missing `DB_HOST` should be a startup error, not a runtime surprise ten minutes later. Construct a `Config` record and pass it through `ReaderT` or as an explicit argument. This makes the configuration surface visible in one place, testable by constructing a `Config` value directly, and mockable without touching the process environment.


---

## 113. Order imports: Prelude, then libraries, then local modules

Three groups, separated by blank lines, alphabetical within each group.

```purescript
import Prelude

import Data.Array (filter, length)
import Data.Map as Map
import Data.Maybe (Maybe(..))
import Effect.Aff (Aff)

import MyApp.Data.User (User)
import MyApp.Util (formatDate)
```

The reader can tell at a glance what comes from the language's Prelude, what comes from the ecosystem, and what is project-local. When a module adds a new dependency, the diff touches only the relevant group. When reviewing unfamiliar code, the import section is a table of contents — keep it organised.


---

## 114. Qualify container imports

`import Data.Map as Map` and write `Map.lookup`, `Map.insert`, `Map.empty` at every call site. The same for `Set`, `List`, `StrMap`, and any container whose operations have generic names.

```purescript
-- Ambiguous: which lookup? which empty?
import Data.Map (lookup, insert, empty)
import Data.Set (empty, insert)  -- name clash

-- Unambiguous: the container is visible at the point of use.
import Data.Map as Map
import Data.Set as Set

result = Map.lookup key (Map.insert key value Map.empty)
items  = Set.insert item Set.empty
```

`lookup`, `insert`, `empty`, `singleton`, and `fromFoldable` appear in half a dozen modules. Qualifying them avoids name clashes and makes the container type visible without tracing back to the import list. The three extra characters per call site are an investment in readability that compounds over the life of the codebase.


---

## 115. Document every export with a doc comment

PureScript doc comments (`-- |`) appear in generated documentation and in IDE hover popups. Every exported function and type should have one.

```purescript
-- | Partition nodes into layers by their depth from the root.
-- | Nodes unreachable from the root are placed in a separate overflow layer.
layerByDepth :: Graph -> Array (Array Node)
```

The comment describes what the function does and any non-obvious behaviour (the overflow layer). It does not describe the implementation. If a function is not worth documenting, it is probably not worth exporting.

For internal helpers, a brief comment is still welcome but not obligatory — the type signature and a well-chosen name often suffice. For exports, the doc comment is part of the API contract. Write it as if the reader cannot see the source code, because often they cannot.


---

## 116. Documentation describes what, not how

"Returns the first element, or `Nothing` if empty." Not: "Pattern matches on the array, checks if the length is zero, then returns the head."

```purescript
-- | Compute the bounding box that encloses all points.
-- | Returns Nothing if the array is empty.
boundingBox :: Array Point -> Maybe BoundingBox

-- Not:
-- | Folds over the array, tracking the min and max x and y
-- | coordinates, then constructs a BoundingBox from the extremes.
```

If you feel the need to explain the mechanism, that is often a signal that the function is doing too much or that its name does not convey its purpose. A doc comment that restates the implementation in English is pure noise — the reader could have read the code. A doc comment that states the contract gives the reader something the code alone does not: permission to stop reading.


---

## 117. Use mixed case for abbreviations: HttpServer, not HTTPServer

When an abbreviation appears in a CamelCase identifier, treat it as a word: `HttpServer`, `JsonParser`, `XmlNode`. The exception is two-letter abbreviations, which remain uppercase: `IO`, `Id`.

The reason is legibility at word boundaries. `HTTPSConnection` forces the reader to determine where `HTTPS` ends and `Connection` begins. `HttpsConnection` is unambiguous. `HTMLParser` could be `HT` + `MLParser` if you squint; `HtmlParser` cannot be misread.

This convention follows the PureScript ecosystem's prevailing practice and aligns with the Haskell style guides (Tibbe, Kowainik). Consistency within a codebase matters more than the specific choice, but if you are starting fresh, mixed case is the safer default.


---

## 118. Use singular module names

`Data.Map`, not `Data.Maps`. `MyApp.Route`, not `MyApp.Routes`. `Component.Sidebar`, not `Components.Sidebar`.

A module represents a concept — the Map type and its operations, the Route type and its parser, the Sidebar component — not a collection of instances of that concept. The singular name is both more precise and more consistent with the PureScript and Haskell ecosystem conventions.

The plural form tempts when a module contains "many things" — many routes, many components. But the module itself is still one thing: the namespace for those definitions. Name it for what it is, not what it contains.


---

## 119. Do not mix let and where in the same definition

A definition that scatters bindings between `let` (above the main expression) and `where` (below it) forces the reader to look in two places to understand the function's vocabulary.

```purescript
-- Mixed: where is `margin` defined? Where is `scaled`?
render state =
  let scaled = state.value * factor
  in svg [ viewBox 0.0 0.0 width height ]
       [ rect [ x margin, y margin, width (width - 2.0 * margin), height scaled ] ]
  where
  factor = 2.5
  margin = 10.0
```

Pick one style per definition. Use `where` for named helpers that support the main expression. Use `let` for intermediate values that feed into the next step. Do not split the supporting cast between two stages.


---

## 120. Prefer guards over if-then-else

Guards align conditions vertically, making the decision structure scannable. Nested `if-then-else` indents rightward and buries the structure.

```purescript
-- Guards: the conditions scan as a table.
severity :: Int -> Severity
severity count
  | count > 100 = Critical
  | count > 10  = Warning
  | count > 0   = Info
  | otherwise   = None

-- if-then-else: nests and obscures.
severity :: Int -> Severity
severity count =
  if count > 100 then Critical
  else if count > 10 then Warning
  else if count > 0 then Info
  else None
```

Use `if-then-else` for simple binary choices where a guard would be heavier than the expression it protects — a ternary-style inline decision within a larger expression. For anything with more than two branches, guards are clearer.


---

## 121. End every guard chain with otherwise

An unguarded case with no `otherwise` is a partial function hiding in plain sight. The compiler may not catch it, depending on context, and the reader certainly cannot verify totality at a glance.

```purescript
-- Partial: what happens when count is negative?
label :: Int -> String
label count
  | count > 0 = "positive"
  | count == 0 = "zero"
  -- count < 0 falls through silently

-- Total: the exhaustive case is explicit.
label :: Int -> String
label count
  | count > 0  = "positive"
  | count == 0 = "zero"
  | otherwise  = "negative"
```

`otherwise` is simply `true`, but its presence signals intent: "I have considered all cases." Its absence signals either an oversight or a function that should not be called with certain inputs — and if the latter, a type that prevents those inputs would be better than a missing branch.


---

## 122. Replace do { x <- m; pure (f x) } with map f m

A `do` block that binds a value and immediately wraps a transformation of it in `pure` is a `Functor` operation wearing `Monad` clothing.

Prefer:

```purescript
_.name <$> fetchUser id
```

Over:

```purescript
do
  response <- fetchUser id
  pure response.name
```

The `<$>` version is shorter, communicates that no effects happen between the fetch and the transformation, and works with any `Functor` — not just `Monad`. The `do` version implies that something monadic is happening between the bind and the `pure`, and the reader must verify that nothing is.

The same principle extends to longer chains. If you find yourself writing `do { x <- a; y <- pure (f x); z <- pure (g y); pure z }`, you have `g <<< f <$> a`. Each unnecessary bind is a false signal of sequential dependence.


---

## 123. Avoid explicit recursion; use higher-order functions

Most recursive patterns over data structures are already captured by standard combinators: `map`, `filter`, `foldl`, `foldr`, `traverse`, `unfold`, `mapAccumL`. Explicit recursion is harder to read, easier to get wrong, and — in a strict language — liable to blow the stack.

```purescript
-- Explicit recursion: the reader must verify termination and accumulator handling.
sumPositive :: Array Int -> Int
sumPositive = go 0
  where
  go acc arr = case Array.uncons arr of
    Nothing -> acc
    Just { head, tail } ->
      if head > 0 then go (acc + head) tail
      else go acc tail

-- Higher-order: intent is visible, stack safety is inherited.
sumPositive :: Array Int -> Int
sumPositive = filter (_ > 0) >>> sum
```

Reach for explicit recursion only when no standard combinator fits — tree traversals with complex accumulation, interleaved effects with early termination, or algorithms where the recursive structure is the point. When you do write explicit recursion, use `tailRecM` or the `MonadRec` class to guarantee stack safety.


---

## 124. Use comparing for custom sort and comparison

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

## 125. Factor common fields out of ADT variants

If every constructor of a sum type carries the same field, that field belongs outside the sum.

```purescript
-- Repeated: position appears in every constructor.
data Node
  = Element Position Name (Array Node)
  | TextNode Position String
  | Comment Position String

-- Factored: position is structural, content varies.
data NodeContent
  = Element Name (Array Node)
  | TextContent String
  | CommentContent String

type Node = { position :: Position, content :: NodeContent }
```

The factored version makes the common structure visible in the type and accessible without pattern matching. You can write `node.position` directly, without a helper function that matches on every constructor to extract the same field. When you add a new constructor, you cannot forget the common field — the record requires it.


---

## 126. Name recursive helpers go or loop

When a function uses an inner recursive helper with an accumulator, the conventional name is `go` (or sometimes `loop`). This is not a PureScript invention — it is established practice across Haskell, Scala, and the broader FP community.

```purescript
findIndex :: forall a. (a -> Boolean) -> Array a -> Maybe Int
findIndex pred arr = go 0
  where
  go i
    | i >= Array.length arr = Nothing
    | pred (unsafePartial $ Array.unsafeIndex arr i) = Just i
    | otherwise = go (i + 1)
```

The name `go` signals "this is the tail-recursive workhorse; the outer function is the public interface." Any FP programmer recognises the pattern instantly. A descriptive name like `findFrom` is also fine, but avoid inventing a new naming convention for each function — consistency across the codebase is more valuable than local precision.


---

## 127. Use let, not x <- pure y, for pure bindings in do blocks

Within a `do` block, `let` introduces a pure binding. `x <- pure (f y)` introduces the same binding while pretending it involves an effect.

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

The `<- pure` version is not wrong, but it is misleading. Every `<-` in a `do` block signals "this is where an effect happens." When the reader sees `parsed <- pure (...)`, they must look inside the parentheses to confirm that nothing effectful is going on. `let` says what it is: a pure binding. The reader does not need to verify.


---

## 128. Minimise type class constraints

Do not constrain a function with `Eq a =>` if the implementation never compares values of type `a`. Unnecessary constraints exclude valid call sites and misrepresent the function's actual requirements.

```purescript
-- Over-constrained: why does reversing require Eq?
reverseList :: forall a. Eq a => List a -> List a
reverseList = foldl (flip Cons) Nil

-- Correct: no constraint needed.
reverseList :: forall a. List a -> List a
reverseList = foldl (flip Cons) Nil
```

Each constraint is a promise that the function uses that capability. An `Eq` constraint says "I compare values for equality somewhere in this implementation." A `Show` constraint says "I convert values to strings." If the promise is false, the function is lying about its requirements — and that lie has practical consequences. Function types, for instance, rarely have `Eq` instances; an unnecessary `Eq a =>` prevents the function from being used with `a ~ (Int -> Int)`.

The compiler does not warn about over-constrained functions. Discipline here is manual but worthwhile.


---

## 129. Avoid dead code and commented-out blocks

Delete what you do not use. Version control remembers what you have deleted; your codebase should not.

Commented-out code is a trap. It rots faster than live code because the compiler never checks it. When dependencies change, module names shift, or type signatures evolve, the commented block falls silently out of sync. A reader encountering it cannot know whether it is a plan, a memory, a debugging aid, or an oversight. In every case, it is noise.

The same applies to unused imports, unreachable branches, and functions that nothing calls. Each is a false signal — an assertion that this code matters when it does not. Remove it. If you need it again, `git log` is a better archive than a comment.


---

## 130. Use $ and # to reduce parentheses, but do not chain excessively

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

## 131. Keep modules under approximately 400 lines

A module that grows past this threshold is likely doing more than one thing. It accumulates responsibilities until no one can hold it in their head, and every change requires scrolling past unrelated code.

Split by responsibility. A data type and its core operations in one module; rendering functions in a sibling; serialisation in a third. PureScript's orphan-instance rule means a type and its instances must live together, but operations that use the type can live anywhere.

The number is not sacred — some modules are naturally larger (a component with many action handlers, a codec module for a complex API). The principle is: when you find yourself navigating within a module rather than reading it, it is time to split.


---

## 132. Write helpers liberally; export sparingly

Break complex functions into small, well-typed, unexported helpers. Each helper with a type signature is a checked assertion about an intermediate step — a waypoint where the compiler verifies your reasoning.

```purescript
-- A single monolithic function: hard to test, hard to debug.
processData :: RawInput -> Effect Output
processData raw = do
  ...  -- 60 lines of interleaved parsing, validation, and transformation

-- Decomposed: each step is named, typed, and independently testable.
processData :: RawInput -> Effect Output
processData raw = do
  let parsed = parseFields raw
  validated <- validateFields parsed
  pure $ transformToOutput validated

-- These are not exported. They exist for clarity, not reuse.
parseFields :: RawInput -> ParsedFields
parseFields = ...

validateFields :: ParsedFields -> Effect ValidatedFields
validateFields = ...

transformToOutput :: ValidatedFields -> Output
transformToOutput = ...
```

The cost of an unexported helper is near zero: a few lines of code that the compiler checks and dead-code elimination removes if unused. The benefit is that when something goes wrong, the type error points to a small, named function rather than line 47 of an anonymous pipeline. Write as many as you need. Export only what the module's consumers require.
