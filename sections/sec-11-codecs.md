# XI. Parsing, codecs, and round-tripping

Data enters your program as untyped bytes and leaves as untyped bytes. The transformation between external representation and internal types should happen at the boundary, happen once, and be verifiable. Bidirectional codecs, parser combinators, and optics are the tools for this work.


---


## 124. Use purescript-parsing for structured parsing, not regex

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


## 125. Use codec for JSON, not hand-written decoders

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


## 126. Decode at the boundary, work with types internally

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

**A pragmatic exception.** For very large JSON payloads on JavaScript backends, full decoding into PureScript types can carry a real performance cost. In these cases, you might pragmatically skip full parsing — accessing fields directly from the raw JSON via FFI or `Foreign` — and accept the runtime risk. If you do this, treat it as a conscious, documented decision: comment why you are bypassing the codec, which fields you are accessing unsafely, and what breaks if the shape changes. This is a performance escape hatch, not a default.


---


## 127. JSON codecs should be values, not type class instances

The `EncodeJson` and `DecodeJson` type classes from `argonaut` are convenient — `encodeJson myValue` picks up the instance automatically. But this convenience has costs that grow with your codebase.

First, orphan-instance pressure. If your type is defined in one package and your encoding strategy in another, you either create orphan instances or couple your domain types to a serialisation library. Second, invisibility. When encoding is implicit, the reader cannot tell which encoding is in use without chasing the instance chain. Third, inflexibility. A type can have only one instance, but real systems often need multiple encodings — one for the API, one for the database, one for logging.

```purescript
-- Codec value: explicit, composable, bidirectional.
import Data.Codec.Argonaut as CA

userCodec :: JsonCodec User
userCodec = CA.object "User" $ CA.recordProp (Proxy :: _ "name") CA.string
  <<< CA.recordProp (Proxy :: _ "email") CA.string
  <<< CA.recordProp (Proxy :: _ "role") roleCodec

-- The codec is a value. You can have as many as you need.
userApiCodec :: JsonCodec User    -- for the REST API
userLogCodec :: JsonCodec User    -- for structured logs, omitting PII
```

`purescript-codec-argonaut` gives you bidirectional codec values that are explicit at every call site, composable via ordinary function composition, and guarantee that encode and decode agree by construction. (Gary Burgess)

See also entry 102 on not using `show` for serialisation — the same principle of making encoding decisions visible and deliberate.


---


## 128. Optics: a lens is a getter and a setter that agree

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
