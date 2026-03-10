# XVI. Practical tasks

Concrete guidance for common programming tasks. Each entry recommends a specific library or approach for a specific problem, chosen for reliability and ecosystem fit.


---


## 159. Generating random values: use Effect.Random, not unsafePerformEffect

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


## 160. CLI argument parsing: use optparse, not hand-rolled case matching on argv

`purescript-optparse` gives you typed argument parsing with help text generation, subcommands, default values, and validation — all derived from a declarative description of your interface.

```purescript
-- Structured: self-documenting, validated, composable.
opts :: Parser Options
opts = ado
  input <- strOption (long "input" <> metavar "PATH" <> help "Input file")
  verbose <- switch (long "verbose" <> help "Enable verbose output")
  in { input, verbose }

-- Hand-rolled: fragile, undocumented, silently wrong.
main :: Effect Unit
main = do
  args <- Process.argv
  case args !! 2, args !! 3 of
    Just "--input", Just path -> run path
    _, _ -> log "Usage: mytool --input <path>"
```

Manually indexing into `process.argv` produces code that is fragile when arguments are reordered, undocumented when someone passes `--help`, and silently wrong when optional arguments shift the indices. A declarative parser describes the interface once and derives both the parsing logic and the usage message from that single description.

Even for tools with only one or two arguments, the structured approach costs less than the debugging session you will eventually have when someone passes the arguments in the wrong order.


---


## 161. Date and time: use the types, not epoch integers

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


## 162. Regular expressions: compile once, use many

`Regex.regex` returns `Either String Regex` because the pattern string might be syntactically invalid. This is a check that needs to happen once, not on every use.

```purescript
-- Right: compile once, reuse.
numberPattern :: Regex
numberPattern = unsafePartial $ fromRight $ regex "\\d+" noFlags

extractNumbers :: Array String -> Array (Maybe (NonEmptyArray Match))
extractNumbers = map (match numberPattern)

-- Wrong: recompiling inside a map.
extractNumbers :: Array String -> Array (Maybe (NonEmptyArray Match))
extractNumbers = map \s ->
  case regex "\\d+" noFlags of
    Left _  -> Nothing
    Right r -> match r s
```

If the pattern is a literal known at compile time, `unsafePartial $ fromRight` is justified — you are asserting that the string is a valid regex, and if it is not, the crash at startup is the correct behaviour. For patterns constructed from user input, handle the `Left` case properly and compile once at the point of input, passing the compiled `Regex` value to everything downstream.

Compiling a regex is not expensive in absolute terms, but doing it inside a tight loop is the kind of unnecessary work that accumulates quietly until profiling reveals it.


---


## 163. HTTP requests: decode the response, do not assume its shape

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

A pragmatic exception: if you are on a JavaScript backend and receiving very large JSON payloads (megabytes of data), the overhead of a full decode-and-reconstruct pass may matter. In that narrow case, treating the parsed JSON as a trusted JavaScript object — skipping the PureScript codec — is a defensible performance trade-off. Document it explicitly, confine it to one module, and accept the runtime risk. This is a production performance decision, not a default.


---


## 164. File I/O in Node: use the Aff wrappers, not raw FFI

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


## 165. Logging: use structured data, not string concatenation

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


## 166. Environment variables: read at startup, not on demand

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
