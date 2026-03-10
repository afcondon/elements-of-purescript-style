# V. The FFI boundary

The foreign function interface is where PureScript's guarantees end and the host language's begin. Every entry in this section is about making that boundary as thin, honest, and verifiable as possible. The type checker cannot see across it; your discipline must bridge the gap.


---


## 53. Keep FFI files minimal; put logic in PureScript

A foreign module should do one thing: expose a host-language function to PureScript with an honest type. All branching, error handling, validation, and data transformation belong on the PureScript side, where the compiler can verify them.

```javascript
// src/FFI/Clipboard.js — good: a single-purpose wrapper.
export const writeTextImpl = (text) => () =>
  navigator.clipboard.writeText(text);
```

```purescript
-- src/FFI/Clipboard.purs — logic lives here.
foreign import writeTextImpl :: String -> Effect (Promise Unit)

writeText :: String -> Aff Unit
writeText s = do
  p <- liftEffect $ writeTextImpl s
  toAff p
```

The temptation is to handle edge cases in the host language — check for `null`, catch exceptions, massage data into shape — because "it's easier over there." Every line of logic in a foreign file is a line the type checker cannot see. Keeping the foreign code thin and the logic in PureScript lets the boundary be a boundary.

That said, this advice assumes a project that has committed to PureScript for its application logic. If you are introducing PureScript into an existing codebase incrementally — wrapping a few critical functions, testing the water — a thicker FFI layer may be a reasonable interim step. The principle still holds: move logic to PureScript as the PureScript surface area grows. The examples here use JavaScript, but the same applies to any backend's FFI (Erlang, Python, Lua).


---


## 54. Use EffectFn/Fn for uncurried FFI

PureScript functions are curried. JavaScript functions are not. When you call a JavaScript function that takes multiple arguments, or pass a PureScript callback to JavaScript, use `Fn` and `EffectFn` from `Data.Function.Uncurried` and `Effect.Uncurried` to match JavaScript's calling convention directly.

```purescript
-- Prefer: uncurried types match the JavaScript signature.
foreign import addEventListenerImpl
  :: EffectFn3 String (EffectFn1 Event Unit) Element Unit

addEventListener :: String -> (Event -> Effect Unit) -> Element -> Effect Unit
addEventListener evt cb el =
  runEffectFn3 addEventListenerImpl evt (mkEffectFn1 cb) el
```

```purescript
-- Over: curried foreign import requires a manual wrapper in JavaScript.
foreign import addEventListenerImpl
  :: String -> (Event -> Effect Unit) -> Element -> Effect Unit
-- The .js file must now manually handle currying:
-- export const addEventListenerImpl = (evt) => (cb) => (el) => () => ...
```

The uncurried variants avoid an intermediate currying wrapper in the JavaScript file and are faster at the call boundary. More importantly, they make the FFI file trivial — often just `export const foo = someBuiltin;` — which is exactly where you want the complexity to be: nowhere.


---


## 55. Use Nullable for values that may be null

JavaScript APIs routinely return `null` or `undefined`. Rather than pretending the value will always be there (and crashing at runtime), use `Nullable` from `Data.Nullable` to make the possibility explicit at the FFI boundary.

```purescript
foreign import getElementByIdImpl :: String -> Effect (Nullable Element)

getElementById :: String -> Effect (Maybe Element)
getElementById id = toMaybe <$> getElementByIdImpl id
```

`Nullable` exists specifically for this: it maps directly to JavaScript's null/undefined semantics and converts cleanly to `Maybe` via `toMaybe`. It is the right tool for single values that might be absent. Do not use `Foreign` decoding when `Nullable` suffices — the lighter tool communicates the simpler situation.

For richer structures coming across the boundary, see entry 56.


---


## 56. Parse, don't validate — especially at the boundary

Any data arriving from outside your program — JSON from an API, query parameters from a URL, configuration from a file, a return value from a JavaScript function — should be *parsed* into a typed representation at the boundary and never trusted as raw input beyond that point. This is what Alexis King calls "parse, don't validate": do not check that the data looks right and then use it unsafely — transform it into a type that *cannot* be wrong.

The FFI is the most common boundary. JavaScript can return a number where you expected a string, or an object missing half its fields. The PureScript type system has no jurisdiction over foreign land. It is your job to check papers at the border.

```purescript
-- Safe: treating the return as foreign data and decoding it.
foreign import getConfigImpl :: Effect Foreign

getConfig :: Effect (Either String { timeout :: Int, retries :: Int })
getConfig = do
  raw <- getConfigImpl
  pure $ runExcept $ do
    timeout <- readInt =<< readProp "timeout" raw
    retries <- readInt =<< readProp "retries" raw
    pure { timeout, retries }

-- Dangerous: trusting JavaScript to return the right shape.
foreign import getConfigImpl :: Effect { timeout :: Int, retries :: Int }
```

The `Foreign` decoder is a parser. Once it succeeds, the result is a genuine PureScript value with full type guarantees. If the JavaScript function "always returns a string," it will return `undefined` the week after you ship.


---


## 57. Never use unsafeCoerce as a substitute for proper types

`Unsafe.Coerce.unsafeCoerce` tells the compiler "trust me, this value has this type." The compiler obliges. It has no choice. When you are wrong — and you will eventually be wrong — the error surfaces at runtime, far from the coercion, with no indication of what went awry.

```purescript
-- This also compiles, and fails at compile time when the shape is wrong.
metadata :: Effect (Either String { title :: String })
metadata = do
  raw <- getMetadata
  pure $ decode raw
```

```purescript
-- This compiles. It will fail at runtime in creative ways.
foreign import getMetadata :: Effect Foreign

metadata :: Effect { title :: String }
metadata = unsafeCoerce <$> getMetadata
```

Legitimate uses of `unsafeCoerce` exist — primarily in library internals where the author has proven a type equivalence that PureScript's type system cannot express. Application code should never need it. If you reach for `unsafeCoerce` because a `Foreign` decoder feels like too much ceremony, the ceremony is the point. It is the type system asking you to prove that you know what you have.

In a production codebase, consider adding a pre-commit check or CI step that flags any use of `unsafeCoerce`. The function has legitimate uses in library internals, but its presence in application code is almost always a sign that something should be decoded or typed properly.


---


## 58. Suffix foreign imports with Impl; hide them behind a wrapper

The boundary between JavaScript and PureScript is the most dangerous line in your codebase. Mark it clearly.

```purescript
-- Foreign import: uncurried, suffixed with Impl.
foreign import joinPathImpl :: Fn2 String String String

-- PureScript wrapper: curried, exported.
joinPath :: String -> String -> String
joinPath start end = runFn2 joinPathImpl start end
```

```javascript
// Foreign module: pure JavaScript, no PureScript knowledge required.
export function joinPathImpl(start, end) {
  return start + "/" + end;
}
```

The `Impl` suffix signals that this function is an implementation detail — not for direct consumption. The wrapper function is where PureScript types begin and JavaScript types end. Validation, `Maybe` wrapping, and `Effect` thunking all belong in the wrapper, not in the foreign module.

Export `joinPath`. Do not export `joinPathImpl`. The module boundary is your firewall. (Official FFI Tips Guide)

See also entries 153 and 154 for related FFI discipline.


---


## 59. Do not go point-free with runFn

The PureScript compiler inlines `runFn2`, `runFn3`, and their siblings only when they are fully saturated — applied to all their arguments. A point-free definition defeats this optimisation.

```purescript
-- Inlined: the compiler sees all arguments and generates a direct call.
joinPath :: String -> String -> String
joinPath start end = runFn2 joinPathImpl start end

-- NOT inlined: the compiler sees a partial application and generates a closure.
joinPath :: String -> String -> String
joinPath = runFn2 joinPathImpl
```

The two definitions are semantically identical, but the point-free version produces a closure that wraps the foreign function call. In a hot path — an inner loop, a rendering function called thousands of times — this overhead is measurable.

This is one of the few places where the general De Gustibus tolerance for point-free style does not apply. The `runFn` family has specific compiler support that depends on syntactic saturation. Name the arguments. (Official FFI Tips Guide)


---


## 60. Do not mutate input records in FFI code

JavaScript FFI functions receive PureScript values directly. If a foreign function modifies its arguments in place, it violates the fundamental contract of a pure language: that values do not change after construction.

```javascript
// WRONG: mutates the input.
export function addTimestamp(record) {
  record.timestamp = Date.now();
  return record;
}
```

```javascript
// RIGHT: returns a new object.
export function addTimestamp(record) {
  return { ...record, timestamp: Date.now() };
}
```

The first version looks correct from the JavaScript side but causes silent corruption in PureScript. Any other reference to the original record now sees the mutated version. If the record was shared — passed to multiple functions, stored in state — the mutation propagates unpredictably.

This applies to arrays, typed arrays, and any mutable JavaScript object. If your FFI function needs to modify data, copy first. Or better, structure your FFI so that the PureScript wrapper constructs the new value and the foreign function only performs the operation that requires JavaScript. (wclr)


---


## 61. Never call PureScript code from foreign modules

Do not import PureScript-generated modules in your JavaScript FFI files. Do not reference constructors like `Data_Maybe.Just.create(x)` or call functions from the `output/` directory.

```javascript
// WRONG: reaches into PureScript's generated code.
import * as Maybe from "../output/Data.Maybe/index.js";

export function safeDivide(a, b) {
  if (b === 0) return Maybe.Nothing.value;
  return Maybe.Just.create(a / b);
}
```

```purescript
-- RIGHT: pass constructors from PureScript.
foreign import safeDivideImpl :: Fn3 (forall a. a -> Maybe a) (forall a. Maybe a) Number Number (Maybe Number)

safeDivide :: Number -> Number -> Maybe Number
safeDivide = runFn3 safeDivideImpl Just Nothing
```

```javascript
export function safeDivideImpl(just, nothing, a, b) {
  if (b === 0) return nothing;
  return just(a / b);
}
```

The generated code is an implementation detail of the compiler. Its structure can change between compiler versions, its module paths can change with build tool updates, and referencing it directly defeats dead-code elimination — the bundler cannot tree-shake a constructor that JavaScript imports directly.

Pass what the foreign function needs from the PureScript side. The wrapper function is the place to supply constructors, type class methods, and callbacks. (Official FFI Tips Guide)

You can also pass PureScript functions as callbacks to JavaScript. An `EffectFn1 a b` on the PureScript side is a plain `function(a) { return b }` on the JavaScript side — no thunking, no currying. This is the right way to wire up event handlers, lifecycle hooks, and any JavaScript API that expects a callback.


---


## 62. Pass type class methods, not dictionaries, to FFI

When a foreign function needs to use a type class method — `show`, `compare`, `encode` — pass the resolved method as a function argument. Do not attempt to work with dictionary objects in JavaScript.

```purescript
foreign import logWithLabelImpl :: Fn2 (forall a. a -> String) String (Effect Unit)

logWithLabel :: forall a. Show a => a -> String -> Effect Unit
logWithLabel value label = runFn2 logWithLabelImpl show label
```

```javascript
export function logWithLabelImpl(showFn, label) {
  return function() {
    console.log(label + ": " + showFn(label));
  };
}
```

The PureScript compiler resolves type class instances to dictionary objects with a specific internal structure. That structure is not part of any public API — it can and does change between compiler versions. By passing the resolved method from the PureScript wrapper, the foreign module receives a plain function and needs no knowledge of the type class machinery. (Official FFI Tips Guide)


---


## 63. Remember that Effect values are thunks

In PureScript, an `Effect` value is a function of zero arguments — a thunk. The foreign module must wrap side effects in a function to defer their execution until PureScript's runtime invokes them.

```javascript
// CORRECT: returns a thunk.
export function getCurrentTime() {
  return Date.now();
}

// WRONG: executes at import time.
export const getCurrentTime = Date.now();
```

The second version calls `Date.now()` when the module is loaded, not when the PureScript program calls `getCurrentTime`. The value is captured once and never updated. This is not a subtle difference — it is the difference between a program that reads the current time and a program that reads the time the module was loaded.

For effectful functions with arguments, each argument adds a layer of currying, and the final layer returns the thunk:

```javascript
// writeFile :: String -> String -> Effect Unit
export function writeFile(path) {
  return function(content) {
    return function() {
      fs.writeFileSync(path, content);
    };
  };
}
```

The outermost functions receive the curried arguments. The innermost `function()` is the `Effect` thunk. Forgetting that final layer means the effect runs during argument application, not when the `Effect` is executed. (Official FFI Tips Guide)


---


## 64. Do not use unsafePerformEffect in production code

`unsafePerformEffect` executes an `Effect` and returns a "pure" value. It is the most dangerous function in the PureScript ecosystem, and its dangers are not obvious.

The compiler assumes pure values are referentially transparent — it may inline them, share them, reorder them, or evaluate them at unexpected times. An `unsafePerformEffect` value that mutates a `Ref` can be called zero times, once, or many times depending on compiler optimisations. Unused `where` bindings might still trigger side effects if the compiler does not eliminate them (or might not trigger them if it does).

```purescript
-- This is a time bomb.
counter :: Ref Int
counter = unsafePerformEffect (Ref.new 0)

-- When does this execute? Before main? During module initialisation?
-- Is it shared across all call sites? The answer depends on the compiler version.
```

The only defensible use is as a transitional step during FFI prototyping — and even then, it should never be exported from a module. If you need a global mutable reference, initialise it in `main` and pass it through `ReaderT`. If you need a module-level constant, make it a pure value. (Nate Faubion, hdgarrood, Thomas Honeyman)


---


## 65. Declare type roles explicitly for foreign data and mutable newtypes

PureScript's `coerce` function can convert between types that differ only in newtype wrappers — but only when the type roles permit it. The compiler infers roles, but inference can be too permissive for types that wrap mutable state or foreign data.

```purescript
-- Without explicit roles, the compiler infers `representational` for the parameter.
newtype MutableRef a = MutableRef (Effect.Ref a)

-- This allows:  coerce :: MutableRef Int -> MutableRef String
-- Which is unsound: the underlying Ref still holds an Int.
```

Declare roles explicitly to prevent unsafe coercions:

```purescript
type role MutableRef nominal

newtype MutableRef a = MutableRef (Effect.Ref a)
-- Now: coerce :: MutableRef Int -> MutableRef String  -- type error
```

A `nominal` role means the type parameter is significant — `MutableRef Int` and `MutableRef String` are distinct types that cannot be coerced between. A `representational` role permits coercion when the inner types are themselves coercible (as with pure newtypes). A `phantom` role ignores the parameter entirely.

For foreign data declarations, the compiler cannot inspect the JavaScript implementation, so it defaults to conservative roles. Explicit annotations document your intent and protect against future changes. (purescript/purescript#4116)


---
