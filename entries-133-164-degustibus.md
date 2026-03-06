# The Elements of PureScript Style — Entries 133-164 and De Gustibus


---

## 133. ADTs for variants, type classes for polymorphism — do not conflate them

A sum type models a closed set of alternatives that your program knows about exhaustively. A type class models an open set of types that share a common interface. These solve different problems, and reaching for the wrong one creates code that is both harder to extend and harder to understand.

When you have three kinds of notification — email, SMS, and push — and your application handles all three, that is a sum type. You pattern match, and the compiler ensures you handle every case. When you have a `Renderable` interface that any type in any package might implement, that is a type class.

```purescript
-- Correct: a closed universe of known alternatives.
data Notification = Email EmailAddress Body | SMS PhoneNumber Body | Push DeviceToken Body

deliver :: Notification -> Aff Unit
deliver = case _ of
  Email addr body -> sendEmail addr body
  SMS phone body  -> sendSMS phone body
  Push token body -> sendPush token body
```

```purescript
-- Wrong: a type class for a closed set.
class Deliverable a where
  deliver :: a -> Aff Unit

-- Now you have three orphan-prone instance declarations,
-- no exhaustiveness checking, and no way to write a function
-- that handles "any notification" without existential gymnastics.
```

The temptation to use type classes for variants often comes from object-oriented thinking, where subclassing is the primary extension mechanism. In PureScript, "defining a separate ADT to model your 'universe' and casing on it is really how the language wants you to solve this problem." (Nate Faubion) If you find yourself writing a class with one method and three instances that are all defined in the same module, you almost certainly want a sum type with three constructors.


---

## 134. Existentials are an anti-pattern unless you have measured a performance need

CPS-encoded existential types in PureScript allow you to hide a type parameter behind a universal quantifier. They are occasionally necessary and almost always the wrong tool.

The canonical alternative is a closure. Instead of packaging a value with its operations into an existential wrapper, close over the value and expose only the operations.

```purescript
-- Closure: simple, direct.
type Renderer = { render :: Effect Unit, resize :: Int -> Int -> Effect Unit }

mkCanvasRenderer :: Canvas -> Renderer
mkCanvasRenderer canvas =
  { render: drawCanvas canvas
  , resize: \w h -> resizeCanvas canvas w h
  }
```

```purescript
-- Existential: pays a complexity tax for no benefit here.
data Renderer = forall s. Renderer
  { state :: s
  , render :: s -> Effect Unit
  , resize :: s -> Int -> Int -> Effect Unit
  }
```

Existential types earned their place in Halogen's internal architecture, where they produced roughly 40% memory reduction when processing millions of virtual DOM nodes. That is an exceptional case in a framework's hot path, measured and justified. For application code, the closure version is simpler, carries no encoding overhead, and composes naturally with the rest of PureScript. (Nate Faubion)

Do not optimise for a problem you have not measured. Existentials are a power tool; most joins need wood glue.


---

## 135. Skip the newtype when the record field name already provides context

Entry 5 argues that newtypes are cheap and you should use them liberally. This is the necessary counterweight: not every value with an underlying type of `Boolean` or `String` needs a wrapper.

A `following :: Boolean` field inside a `UserProfile` record is unambiguous. The field name carries the semantic load. Wrapping it in `newtype Following = Following Boolean` adds a constructor and unwrapping ceremony to every access, with no improvement in type safety — there is no second `Boolean` field it could be confused with. (Thomas Honeyman)

```purescript
-- The field name is sufficient.
type UserProfile = { name :: String, following :: Boolean, bio :: String }

-- Contrast: here newtypes earn their keep.
sendMessage :: UserId -> UserId -> MessageBody -> Aff Unit
-- Without newtypes, swapping sender and recipient is a silent bug.
```

The test from entry 5 still applies: "would swapping this value with another value of the same underlying type be a bug?" A single named field in a record fails that test — there is nothing to swap it with. Newtypes solve the positional confusion problem; named fields solve it differently.

See also entry 136 for the complementary case where the newtype is warranted.


---

## 136. Newtype everything that has different semantics from its base type

This is the affirmative case for newtypes, complementing entry 135's restraint. When a `String` is not just a string — when it is a UUID, an email address, a file path, a CSS class name — wrap it. The newtype costs nothing at runtime and prevents an entire category of mixups at compile time.

```purescript
newtype EmailAddress = EmailAddress String
newtype UserId = UserId String

derive newtype instance Eq EmailAddress
derive newtype instance Eq UserId

-- The compiler will not let you send an email to a user ID.
sendVerification :: EmailAddress -> UserId -> Aff Unit
```

In larger applications, newtypes for records also improve the developer experience. Bare record types produce verbose, hard-to-follow type errors — the compiler prints the full row, which in a complex domain can span dozens of lines. A newtype gives the error a name. (Thomas Honeyman, Nate Faubion)

When uncertain, add the wrapper. The worst case is a few `coerce` or `unwrap` calls. The best case is a bug that never ships.


---

## 137. Extensible records for function arguments, closed records for domain models

PureScript's row polymorphism lets you write functions that accept records with extra fields:

```purescript
fullName :: forall r. { first :: String, last :: String | r } -> String
fullName u = u.first <> " " <> u.last
```

This is excellent for utility functions and component interfaces — callers pass whatever record they have, and the function takes only what it needs. It is the PureScript equivalent of structural subtyping, and it composes well.

But domain models should be concrete. Define `User`, `Order`, `Transaction` as closed records or newtypes around closed records. Do not thread row variables through your entire domain layer.

```purescript
-- Domain model: closed, concrete, documented.
newtype User = User
  { id :: UserId
  , email :: EmailAddress
  , name :: String
  , role :: Role
  }

-- Not this: extensible domain types push complexity to every consumer.
type User r = { id :: UserId, email :: EmailAddress, name :: String, role :: Role | r }
```

The extensible version forces every function that mentions `User` to carry and propagate the row variable. The syntactic duplication of spelling out your fields in a closed record is preferable to the cognitive overhead of tracking extensible type layers through a codebase. (joneshf)


---

## 138. Smart constructors: export the type and an unwrapper, not the constructor

When a type has an invariant — a non-empty string, a positive integer, a validated email — hide the data constructor and export a smart constructor that enforces the invariant.

```purescript
module Data.PositiveInt (PositiveInt, mkPositiveInt, toInt) where

newtype PositiveInt = PositiveInt Int

mkPositiveInt :: Int -> Maybe PositiveInt
mkPositiveInt n
  | n > 0     = Just (PositiveInt n)
  | otherwise = Nothing

toInt :: PositiveInt -> Int
toInt (PositiveInt n) = n
```

The module exports `PositiveInt` (the type), `mkPositiveInt` (the validated constructor), and `toInt` (the unwrapper). It does not export the `PositiveInt` data constructor.

Resist the temptation to create a type class for unwrapping — something like `class Unwrap f where unwrap :: f -> a`. The marginal benefit over a plain function is negative: it harms type inference, adds a class constraint to every use site, and creates an abstraction that does not abstract over anything meaningful. A named function like `toInt` or `toString` is unambiguous and needs no dictionary lookup. (CarstenKoenig, Thomas Honeyman)


---

## 139. JSON codecs should be values, not type class instances

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

See also entry 101 on not using `show` for serialisation — the same principle of making encoding decisions visible and deliberate.


---

## 140. Avoid dual error channels: do not return Effect (Either e a)

When a function returns `Effect (Either AppError a)`, it has two ways to fail: the `Effect` can throw a JavaScript exception, and the `Either` can be `Left`. The caller must handle both, and inevitably one channel is forgotten.

```purescript
-- Two error channels: which one should the caller check?
loadConfig :: FilePath -> Effect (Either ConfigError Config)

-- Caller must handle both:
result <- try (loadConfig path)
case result of
  Left exn          -> -- JavaScript exception
  Right (Left err)  -> -- domain error
  Right (Right cfg) -> -- success
```

This is the wrong shape. If your errors are structured and recovery depends on the error type, use `ExceptT`:

```purescript
loadConfig :: FilePath -> ExceptT ConfigError Effect Config
```

If your errors are simple and you only need to catch them at a boundary, use plain exceptions and `try` at the outer edge:

```purescript
loadConfig :: FilePath -> Effect Config
-- throws on failure; caller uses `try` if recovery is needed
```

Either approach gives you one error channel. The `Effect (Either e a)` pattern gives you two and guarantees that someone, somewhere, will handle the wrong one. (ntwilson, Nate Faubion)


---

## 141. Use unsafeCrashWith for genuinely unreachable code

Sometimes the type system cannot prove that a branch is unreachable, but you know it is. Perhaps you have established the invariant elsewhere, or the surrounding logic excludes the case. Mark these branches explicitly with `unsafeCrashWith`.

```purescript
import Partial.Unsafe (unsafeCrashWith)

lookupOrDie :: forall k v. Ord k => k -> Map k v -> v
lookupOrDie k m = case Map.lookup k m of
  Just v  -> v
  Nothing -> unsafeCrashWith "lookupOrDie: key missing from map assumed to be complete"
```

This is better than an incomplete pattern match, which the compiler may or may not warn about and which produces an unhelpful runtime error. It is better than `unsafePartial $ fromJust`, which hides the crash behind two layers of indirection. And the message string serves as documentation — it explains why the author believed the branch was unreachable, which helps the person debugging when that belief turns out to be wrong. (Gary Burgess)

Use this sparingly. Every `unsafeCrashWith` is a claim that the type system cannot verify. If you find yourself writing many of them, the types are not carrying enough information.


---

## 142. Prefer polymorphic monad constraints over concrete Effect

When a function performs effects, writing its type with a concrete `Effect` monad locks it into a specific execution context. Writing it with a constraint leaves room for the future.

```purescript
-- Concrete: works, but inflexible.
getUser :: UserId -> Effect User

-- Polymorphic: works in any monad that can perform effects.
getUser :: forall m. MonadEffect m => UserId -> m User
```

The polymorphic version works identically when called in `Effect`. But when you later wrap your application in a `ReaderT Config Aff` stack, the concrete version requires `liftEffect` at every call site. The polymorphic version works unchanged.

Testing benefits are equally significant. You can run the polymorphic version in a test monad that logs calls without performing them. The concrete version can only be tested by running the real effect.

This does not mean every function should carry monad constraints. Pure functions should stay pure. But when a function genuinely needs effects, `MonadEffect m` or `MonadAff m` is almost always preferable to naming the concrete monad. (ntwilson)


---

## 143. A transformer stack is only as stack-safe as its base

If your monad transformer stack bottoms out in `Identity`, your `bind` chains are not stack-safe. Each `>>=` adds a frame, and deep recursion will overflow.

```purescript
-- Stack-unsafe: Identity does not trampoline.
type PureComp = ReaderT Config (StateT AppState Identity)

-- Stack-safe: Trampoline is a free monad with constant stack usage.
type PureComp = ReaderT Config (StateT AppState Trampoline)
```

`Aff` is already stack-safe, so a `ReaderT Config Aff` stack inherits that property. The problem arises specifically with pure transformer stacks over `Identity` and with long `bind` chains — the kind you get from recursive computations or processing large data structures monadically.

A related subtlety: `MonadRec` and `tailRecM` provide explicit stack-safe recursion, but using them with an already stack-safe base monad like `Aff` doubles the number of binds for no benefit. Reach for `tailRecM` at the point of final interpretation, not as a blanket precaution. (Nate Faubion)


---

## 144. parTraverse and parSequence cover 80% of parallel Aff

PureScript's `Aff` monad provides parallel combinators through the `Parallel` type class. For most use cases, two functions are sufficient:

```purescript
-- Fetch three resources in parallel.
results <- parTraverse fetchResource ["users", "posts", "comments"]

-- Or with independently typed actions:
{ users, posts } <- sequential $ { users: _, posts: _ }
  <$> parallel (fetchUsers orgId)
  <*> parallel (fetchPosts orgId)
```

Do not manually compose `parallel` and `sequential` unless you need something that `parTraverse` and `parSequence` cannot express. The manual version is verbose and error-prone — forgetting `sequential` or misplacing `parallel` produces confusing type errors.

For bounded concurrency — running at most N requests simultaneously — use an `AVar` as a semaphore with `bracket` to acquire and release permits. This is a straightforward pattern that composes with the existing parallel combinators rather than replacing them. (Nate Faubion)


---

## 145. Use the ReaderT pattern for non-trivial Halogen apps

As applications grow, components need access to shared resources: API clients, configuration, authentication state. Threading these as props through every layer of the component tree does not scale.

The `ReaderT` pattern, demonstrated extensively in Real World Halogen, provides a principled alternative. Your application monad carries an environment, and any component can read from it.

```purescript
newtype AppM a = AppM (ReaderT Env Aff a)

derive newtype instance Functor AppM
derive newtype instance Apply AppM
derive newtype instance Applicative AppM
derive newtype instance Bind AppM
derive newtype instance Monad AppM
derive newtype instance MonadEffect AppM
derive newtype instance MonadAff AppM

instance MonadAsk Env AppM where
  ask = AppM ask
```

For global mutable state — the current user, a notification queue — prefer `halogen-store` over rolling your own `ReaderT` with a `Ref`. The library handles subscription, notification of changes, and cleanup. Reserve manual `ReaderT` + `Ref` for cases where you need fine-grained control over when subscribers are notified. (Thomas Honeyman)

See also entry 92 on newtypes for transformer stacks, and entry 161 on the capability pattern that builds on this foundation.


---

## 146. Do not use unsafePerformEffect in production code

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

## 147. Do not mutate input records in FFI code

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

## 148. join <$> traverse is idiomatic

There is no standard combinator for "traverse a structure with a function that returns a nested container, then flatten." The idiomatic PureScript for this is `join <$> traverse`.

```purescript
-- Given: lookupUser :: UserId -> Aff (Maybe User)
-- Want:  look up each ID, get Maybe (Array User) where Nothing means any lookup failed.

lookupAll :: Array UserId -> Aff (Maybe (Array User))
lookupAll ids = join <$> traverse lookupUser ids
-- traverse gives: Aff (Array (Maybe User))
-- but we want:   Aff (Maybe (Array User))
```

Wait — that is not quite right. Let us be precise. `traverse` here gives `Aff (Array (Maybe User))`. To turn `Array (Maybe User)` into `Maybe (Array User)`, you need `sequence`, not `join`. The actual `join <$> traverse` pattern applies when the traversal function returns a value in the same monad:

```purescript
-- lookupChildren :: NodeId -> Aff (Array NodeId)
-- Traverse a list of nodes, get each node's children, flatten into one list.
allChildren :: Array NodeId -> Aff (Array NodeId)
allChildren ids = join <$> traverse lookupChildren ids
-- traverse gives: Aff (Array (Array NodeId))
-- join flattens:  Aff (Array NodeId)
```

Recognise this pattern when you see it. It is the monadic generalisation of `concatMap`, lifted into an effectful context. (paf31, Nate Faubion)


---

## 149. Test laws with purescript-quickcheck-laws

If your type has instances for `Eq`, `Ord`, `Semigroup`, `Monoid`, `Functor`, or `Monad`, those instances carry algebraic laws. `Eq` must be reflexive, symmetric, and transitive. `Semigroup`'s `append` must be associative. `Monad` must satisfy left identity, right identity, and associativity.

An instance that violates its laws is worse than no instance at all. Code that uses your type through the class interface assumes the laws hold. When they do not, the bugs are subtle, non-local, and maddening to track down.

```purescript
import Test.QuickCheck.Laws.Data.Eq (checkEq)
import Test.QuickCheck.Laws.Data.Ord (checkOrd)
import Test.QuickCheck.Laws.Data.Monoid (checkMonoid)

main :: Effect Unit
main = do
  checkEq (Proxy :: Proxy MyType)
  checkOrd (Proxy :: Proxy MyType)
  checkMonoid (Proxy :: Proxy MyType)
```

`purescript-quickcheck-laws` generates random instances of your type and verifies each law with property-based tests. This requires an `Arbitrary` instance, which is itself a useful exercise — if you cannot generate random values of your type, your type may be too constrained to test effectively.

Write these tests when you define the instances, not after a bug report. (JamieBallingall, Gary Burgess)


---

## 150. Semigroup instances should compose, not silently discard

The `Semigroup` instance for `Map` was the subject of considerable community debate. The question: when two maps share a key, should `append` keep the left value, the right value, or merge the values using the inner type's `Semigroup`?

The community preference, and the current implementation, is unbiased: values at duplicate keys are merged via `append` on the value type. This is the principled choice — a `Semigroup` should compose, not silently discard information.

```purescript
import Data.Map as Map

-- Inner Semigroup merges values.
Map.singleton "a" [1, 2] <> Map.singleton "a" [3, 4]
-- Result: Map.singleton "a" [1, 2, 3, 4]
```

When you want biased behaviour — keeping the first or last value — make the choice visible in the type:

```purescript
import Data.Semigroup.First (First(..))
import Data.Semigroup.Last (Last(..))

-- Left-biased: wrap values in First.
map1 :: Map String (First Int)
map1 = Map.singleton "a" (First 1) <> Map.singleton "a" (First 2)
-- Result: Map.singleton "a" (First 1)
```

The `First` and `Last` newtypes document the bias at the type level. A reader encountering `Map String (First Config)` knows immediately that duplicate keys keep the first value. A bare `Map String Config` with a biased instance would require reading the instance definition — or discovering the behaviour through a bug. (kl0tl, monoidmusician, hdgarrood)


---

## 151. Suffix foreign imports with Impl; hide them behind a wrapper

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

## 152. Do not go point-free with runFn

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

## 153. Never call PureScript code from foreign modules

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


---

## 154. Pass type class methods, not dictionaries, to FFI

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

## 155. Remember that Effect values are thunks

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

## 156. Derived Ord for records compares fields in alphabetical label order

When the compiler derives an `Ord` instance for a record type, it compares fields in alphabetical order by label name — not in the order they appear in the declaration.

```purescript
type Person = { zipCode :: String, age :: Int, name :: String }

derive instance Ord Person
-- Compares by: age, then name, then zipCode.
-- NOT by: zipCode, then age, then name.
```

This is consistent with PureScript's treatment of records as row types, where label order is semantic, not syntactic. But it surprises programmers who expect declaration order to matter, particularly those coming from Haskell where field order in a `data` declaration determines derived comparison order.

If you need a specific comparison order — compare by age first, then by name — write the instance by hand. Do not rely on renaming fields to sort alphabetically into your preferred order; that is a maintenance trap waiting for the next person who adds a field. (jpvillaisaza)


---

## 157. Boolean operations (||, &&) are non-strict — an exception to PureScript's strict semantics

Entry 8 establishes that PureScript is strict. Boolean `||` and `&&` are the exception: the compiler implements short-circuit evaluation for `Boolean`'s `HeytingAlgebra` instance. `false && expensiveCheck` does not evaluate `expensiveCheck`.

```purescript
-- Short-circuits: the second condition is not evaluated.
isValid :: User -> Boolean
isValid user = isActive user && hasPermission user
```

But this guarantee applies only to `Boolean`. The `HeytingAlgebra` type class is more general, and other instances are not required to short-circuit:

```purescript
-- Generic code: no short-circuit guarantee.
bothTrue :: forall a. HeytingAlgebra a => a -> a -> a
bothTrue x y = x && y
-- If `a` is not Boolean, `y` may be evaluated even if `x` is "false-like."
```

If you write generic code over `HeytingAlgebra`, do not assume the right-hand side is unevaluated when the left-hand side determines the result. The short-circuit behaviour is a special case of the `Boolean` instance, not a law of the class. (eric-corumdigital)


---

## 158. Use type wildcards for irrelevant type variables

Some PureScript signatures carry type variables that the reader does not need to think about. Halogen component signatures are the canonical example, where `State`, `Action`, `ChildSlots`, `Input`, `Output`, and `Monad` all appear as type parameters, but a given function may only care about one or two of them.

Type wildcards let you focus the reader's attention:

```purescript
-- Every variable named, most irrelevant to understanding this function.
raise :: forall state action slots input output monad.
  output -> HalogenM state action slots input output monad Unit

-- Wildcards for the irrelevant variables.
raise :: forall output. output -> HalogenM _ _ _ _ output _ Unit
```

The wildcard version says: this function takes an output value and raises it. The fully spelled-out version says the same thing, buried under six type variables that contribute nothing to the reader's understanding.

Use this judiciously. In library code and exported functions, explicit type variables serve as documentation. In application code, where the concrete types are known from context, wildcards reduce noise without losing information. (Gary Burgess)


---

## 159. Declare type roles explicitly for foreign data and mutable newtypes

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

## 160. Structure modules by capability and domain

As a PureScript application grows beyond a handful of modules, directory structure becomes load-bearing. The Real World Halogen project demonstrates a structure that has aged well:

```
src/
  Api/           -- HTTP layer: request functions, response decoders
  Capability/    -- Type class interfaces: MonadLogger, ManageUser
  Component/     -- Reusable UI components
  Data/          -- Domain types, codecs, pure logic
  Page/          -- Page-level components (each route maps to a page)
  Store.purs     -- Global application state
  Main.purs      -- Entry point, wiring
```

This separates what the application *can do* (capabilities) from what it *is* (domain types) from how it *looks* (components and pages) from how it *talks to the outside world* (API). Each layer depends only on the layers below it.

The structure is not prescriptive for all applications. A compiler pass has different concerns than a web application. But the principle holds: group by responsibility, not by file type. Do not put all your types in `Types.purs` and all your functions in `Utils.purs`. (Thomas Honeyman)

See also entry 161 for the capability pattern that gives the `Capability/` directory its purpose.


---

## 161. The capability pattern: type classes for effects, newtypes for implementations

Define your application's side effects as type class methods. Implement them in a production newtype. Swap in test implementations.

```purescript
-- Capability: what the application can do.
class Monad m <= ManageUser m where
  getUser :: UserId -> m (Maybe User)
  saveUser :: User -> m Unit

class Monad m <= LogMessage m where
  logMsg :: LogLevel -> String -> m Unit

-- Production implementation.
instance ManageUser AppM where
  getUser uid = liftAff $ Api.fetchUser uid
  saveUser u  = liftAff $ Api.putUser u

instance LogMessage AppM where
  logMsg lvl msg = liftEffect $ Console.log (show lvl <> ": " <> msg)
```

Business logic is written against the type class constraints, not against `AppM`:

```purescript
deactivateUser :: forall m. ManageUser m => LogMessage m => UserId -> m Unit
deactivateUser uid = do
  mUser <- getUser uid
  for_ mUser \user -> do
    saveUser (user { active = false })
    logMsg Info ("Deactivated user " <> show uid)
```

In tests, provide a mock implementation that records calls without performing them. The business logic is tested without HTTP requests, database connections, or console output. (Thomas Honeyman)

This is the `ReaderT` pattern from entry 145 taken to its logical conclusion: the monad abstraction separates business logic from effect plumbing entirely.


---

## 162. Follow namespace conventions: Data for data, Control for control, Node for Node.js

PureScript's module namespace conventions carry semantic weight. They tell the reader what category of abstraction a module provides before they open the file.

`Data.*` is for data structures, types, and pure operations on them. `Data.Map`, `Data.Array`, `Data.Maybe`. `Control.*` is for control flow abstractions — monads, applicatives, continuations. `Control.Monad.Reader`, `Control.Alt`. `Effect.*` is for effectful operations. `Node.*` is for Node.js-specific bindings.

Do not put your data structure in `Control.MyThing`. Do not put your effect wrapper in `Data.MyEffect`. The namespace is not a filing system — it is a signal. When a reader sees `import Control.Monad.MyTransformer`, they expect a monad transformer. When they see `import Data.MyCollection`, they expect a data structure with pure operations.

For application code, your top-level namespace is your project name: `MyApp.Data.User`, `MyApp.Api.Client`, `MyApp.Component.Header`. The conventions apply within your namespace just as they do in the ecosystem. (Official Style Guide)


---

## 163. Note runtime environment assumptions in your README

A PureScript library that calls `process.argv` will fail silently in the browser. A library that calls `document.querySelector` will crash in Node. These are not type errors — the compiler cannot catch them.

If your library assumes a specific runtime environment, say so in the first paragraph of the README. Not in a "Compatibility" section that the reader scrolls past. Not in a footnote. At the top.

```markdown
# purescript-node-streams

Node.js bindings for readable and writable streams.

**This library requires a Node.js runtime.** It will not work in browsers or other JavaScript environments.
```

A consumer who installs your library for the wrong platform gets cryptic FFI errors — `TypeError: Cannot read property 'createReadStream' of undefined` — not a helpful message. The README is the only firewall you have. (Official Style Guide)


---

## 164. PureScript is industrially focused, not a PL research vehicle

PureScript is a language designed for building software, not for exploring the frontiers of type theory. This is a deliberate choice with practical consequences.

Stability is a high priority. Features that require large-scale breaking changes across the ecosystem are unlikely to be accepted, regardless of their theoretical merit. The language prefers fewer, more powerful features to many special-purpose ones. If a need can be addressed downstream of the compiler — in a library, a code generator, a build tool — it probably should be.

This means some features that PureScript *could* have, it chooses not to. Dependent types, linear types, effect rows — these are active areas of PL research, and PureScript's governance has consistently prioritised the working programmer over the language enthusiast. The language is expressive enough to build complex systems and simple enough to onboard working developers.

For users, the implication is: work with the language as it is. If you find yourself fighting the type system to encode an invariant it was not designed to express, consider whether a simpler encoding — a smart constructor, a runtime check at the boundary, a convention documented in a comment — might serve better. The goal is working software, not a proof of concept. (Gary Burgess, Nate Faubion, Thomas Honeyman)


---

---

# De Gustibus

These are matters where reasonable PureScript programmers differ. We present the cases without ruling.


---

## Natural transformations: `~>` or explicit `forall`

The natural transformation operator `~>` provides terse syntax for functions that are polymorphic in their argument's type parameter.

The case for `~>`:

```purescript
interpret :: MyFreeF ~> Aff
```

One line, immediately recognisable to anyone who has worked with free monads or Halogen. The notation comes from category theory and carries the right connotation: a structure-preserving map between functors. For simple signatures, it is difficult to beat.

The case for explicit `forall`:

```purescript
interpret :: forall a. MyFreeF a -> Aff a
```

`~>` has surprising precedence relative to `->`, does not chain well in multi-argument signatures, and formats poorly when the types are complex. Nate Faubion: "It's the kind of thing that works ok in a very simple case, but scales poorly, and gets confusing quickly." The explicit version is always unambiguous, always composes with other type operators, and never surprises the reader who is less familiar with the notation.

In practice, `~>` appears most often in Halogen component signatures and free monad interpreters. Outside those contexts, the explicit form is more common.


---

## Parentheses, `$`, or composition

Three ways to apply `f` to the result of `g x`:

```purescript
-- Parentheses
f (g (h x))

-- Dollar sign
f $ g $ h x

-- Composition
(f <<< g <<< h) x
```

Parentheses give the clearest error messages, especially for beginners — the compiler points to the exact subexpression. They require no knowledge of operator precedence. They are also visually noisy when nested more than two deep.

`$` eliminates trailing parentheses and is the most common idiom in practice. `f $ g $ h x` reads as "apply f to the result of applying g to the result of h x." Two or three `$` signs are comfortable; a chain of six suggests the expression wants to be broken into named subexpressions.

Composition (`<<<` or `>>>`) is a third option that eliminates the argument entirely when you are building a pipeline. It is most natural when the result will be passed to `map` or stored as a value.

None of these is canonical. Pick what reads best at the point of use, and do not mix all three styles in a single expression.


---

## Left-to-right (`#`/`>>>`) or right-to-left (`$`/`<<<`)

PureScript offers operators in both directions:

```purescript
-- Right-to-left: traditional function application order.
result = render $ transform $ parse input

-- Left-to-right: data-flow order.
result = input # parse >>> transform >>> render
```

Right-to-left (`$`, `<<<`) follows mathematical convention and is more common in the PureScript and Haskell ecosystems. The function that runs last appears first, which mirrors how you would read `f(g(x))`.

Left-to-right (`#`, `>>>`) follows the data. The reader traces the value from source to destination in reading order. This is natural for pipelines and method-chain-like transformations, and it is often preferred by programmers coming from languages with pipe operators (Elixir, F#, shell scripting).

The important thing is consistency within a codebase. Mixing `$` and `#` in the same function — or worse, the same expression — creates a reader who must constantly switch mental models. Pick a direction and stay with it.


---

## ADT formatting: leading pipe or not

Two styles for formatting sum type constructors:

```purescript
-- Leading pipe (sometimes called "bar-led").
data Severity
  = Info
  | Warning
  | Error
  | Critical
```

```purescript
-- First constructor unadorned.
data Severity = Info
              | Warning
              | Error
              | Critical
```

The leading-pipe style produces cleaner diffs — adding or removing a constructor changes exactly one line. It also aligns the constructors vertically, making it easy to scan. The community has largely converged on this style, and `purs-tidy` formats accordingly.

The unadorned-first style is more compact for two-constructor types (`data Toggle = On | Off`) and mirrors the BNF grammar notation that some find natural.

For types with more than two constructors, leading pipe has near-consensus. For single-line, two-constructor types, both are common and both are fine.


---

## Shadowing: warn or allow

Entry 81 in the main text advises against shadowing — rebinding a name that is already in scope. The argument: shadowed names create confusion about which binding is in play, and the reader must track scope carefully.

The counterargument, from Gary Burgess among others: the shadowing warning "has caused me more trouble than it has saved." There are legitimate reasons to shadow a variable, particularly in `do` blocks where a value is transformed in stages:

```purescript
-- Intentional shadowing: state is refined step by step.
do
  state <- getState
  let state = applyDefaults state
  let state = validateFields state
  saveState state
```

The shadowing communicates that the old value is superseded — you should not use the pre-defaults `state` after defaults have been applied. A non-shadowing version would require inventing names (`state'`, `state''`, `validatedState`) that carry no additional meaning.

Others find that precisely this invention of names clarifies the transformation: `rawState`, `defaultedState`, `validatedState` tells the reader what each stage has accomplished.

Both positions reflect genuine experience. The compiler's `-W shadow` warning is optional for a reason.


---

## Abbreviation casing: HttpServer or HTTPServer, Json or JSON

The general convention in PureScript follows the Haskell/Tibbe style: treat abbreviations longer than two letters as words, capitalising only the first letter.

```purescript
-- Mixed case: abbreviations as words.
data HttpMethod = Get | Post | Put | Delete
type JsonCodec a = ...
newtype HtmlElement = ...
```

```purescript
-- All-caps: abbreviation preserves its identity.
data HTTPMethod = GET | POST | PUT | DELETE
type JSONCodec a = ...
newtype HTMLElement = ...
```

The mixed-case argument: `HttpsConnection` is immediately parseable. `HTTPSConnection` requires the reader to decide where `HTTPS` ends and `Connection` begins. Camel case applies uniformly, and the abbreviation boundary is always clear.

The all-caps argument: `JSON` is a proper noun (JavaScript Object Notation), and rendering it as `Json` is like writing `Nasa`. The abbreviation has an accepted casing in every other context; PureScript should not override it. This argument was made forcefully in the `argonaut-core` naming debate.

Two-letter abbreviations (`IO`, `UI`, `DB`) are conventionally all-caps everywhere. Beyond two letters, the community is split, though mixed case is more common in the ecosystem's published packages.


---

## Qualified imports or explicit imports

Two strategies for managing what comes into scope:

```purescript
-- Qualified: everything under a prefix.
import Data.Map as Map
import Data.Set as Set

fn = Map.lookup key (Map.singleton "a" 1)
```

```purescript
-- Explicit: name each import.
import Data.Map (Map, lookup, singleton)
import Data.Set (Set, member)

fn = lookup key (singleton "a" 1)
```

Qualified imports are noisier at call sites but self-documenting: `Map.lookup` tells the reader exactly where `lookup` comes from. They require no maintenance when you use a new function from the module. And they prevent name clashes without thought — `Map.empty`, `Set.empty`, and `Array.empty` coexist without conflict.

Explicit imports are concise at call sites and serve as documentation of what the module actually uses. They make unused imports visible (a linter can catch them). But they require maintenance — every time you use a new function, you must add it to the import list, and name clashes between modules require either qualification or renaming.

Many codebases use both: qualified imports for container-like modules (`Map`, `Set`, `Array`, `String`) and explicit imports for everything else. This is a reasonable middle ground, but it is a convention, not a rule.


---

## Module splitting: aggressive or conservative

Some codebases put each type, each component, each function group in its own module. Others keep related definitions together in larger files.

The case for aggressive splitting: small modules are easy to navigate, easy to test in isolation, and produce clear dependency graphs. When a module has one responsibility, its imports and exports tell you everything about its relationships.

The case for conservative splitting: PureScript's orphan-instance rule requires that type class instances live in the module that defines either the class or the type. Splitting a type and its instances across modules is either impossible or requires restructuring. Aggressive splitting also produces deep import chains and can make it harder to understand a feature's full implementation.

A practical heuristic from entry 131: keep modules under roughly 400 lines. This is loose enough to accommodate types with their instances and tight enough to prevent modules from becoming grab-bags. Split when a module has two unrelated responsibilities, not when it reaches an arbitrary line count.


---

## `do` notation or bind chains

`do` notation is overwhelmingly preferred in PureScript for monadic sequencing. But explicit `>>=` has its defenders for short pipelines.

```purescript
-- do notation: the standard.
do
  user <- getUser uid
  posts <- getUserPosts user.id
  pure { user, posts }
```

```purescript
-- Bind chain: emphasises the data flow.
getUser uid >>= \user ->
  getUserPosts user.id >>= \posts ->
    pure { user, posts }
```

`do` is more readable for sequences longer than two steps, for blocks that mix effectful and pure bindings, and for code that non-Haskell-background developers will read. `>>=` can be more natural for a single transformation — `getUser uid >>= fetchProfile` reads as a direct pipeline without the ceremony of `do` and `<-`.

In practice, `>>=` appears most often in point-free combinations (`>>= traverse processItem`) rather than in explicit lambda chains. The lambda-heavy bind chain above is harder to read than the `do` version and offers no compensating benefit.


---

## Record updates: functional update or reconstruct

PureScript provides record update syntax for changing specific fields:

```purescript
-- Functional update: change what differs.
newState = state { count = state.count + 1, loading = true }
```

```purescript
-- Reconstruction: spell out every field.
newState =
  { count: state.count + 1
  , loading: true
  , user: state.user
  , items: state.items
  , error: state.error
  }
```

Functional update is concise, focuses the reader's attention on what changed, and is resilient to new fields — adding a field to the record type does not require updating every functional update site.

Reconstruction makes every field visible, which some find clearer when most fields are changing. It also avoids the subtlety that record update syntax uses `=` (update) rather than `:` (construction), which trips up newcomers.

For updates that change one or two fields out of many, functional update is the clear choice. For transformations that touch most fields, reconstruction can be clearer. The judgment is contextual.


---

## Named lambdas or accessor shorthand in map/traverse

PureScript supports record accessor shorthand, turning `_.fieldName` into a function:

```purescript
-- Accessor shorthand.
names = map _.name users

-- Explicit lambda.
names = map (\user -> user.name) users
```

The shorthand is terse and idiomatic for simple field access. It extends to nested access (`_.address.city`) and works anywhere a function is expected.

The explicit lambda is clearer when the body involves more than field access — computation, conditionals, or multiple field references. It also gives the parameter a name, which can aid readability when the context does not make the type obvious.

```purescript
-- Shorthand strains here.
results = map (\item -> item.price * item.quantity) orders

-- This does not work with accessor shorthand; a lambda is required.
```

For single-field access, accessor shorthand is widely used and uncontroversial. For anything more complex, a named lambda is necessary anyway. The boundary is usually self-evident.


---

## Applicative do (`ado`) or `liftN`

For combining independent applicative computations, PureScript offers both `ado` notation and the `liftN` family:

```purescript
-- ado: mirrors do notation, works for any number of fields.
mkUser :: F User
mkUser = ado
  name  <- validateName input.name
  email <- validateEmail input.email
  age   <- validateAge input.age
  in { name, email, age }
```

```purescript
-- lift3: direct, concise for small arities.
mkUser :: F User
mkUser = lift3 (\name email age -> { name, email, age })
  (validateName input.name)
  (validateEmail input.email)
  (validateAge input.age)
```

`ado` scales to any number of fields, reads like `do` notation (which aids onboarding), and makes the binding names visible next to their sources. It is syntactic sugar over `Apply`, not `Monad`, so it works with `Validation` and other non-monadic applicatives.

`liftN` is more direct for two or three arguments and makes the applicative structure explicit. It does not scale past `lift5` (and past `lift3` it becomes hard to track which argument corresponds to which parameter). For binary combinations — `lift2 Tuple a b`, `lift2 append x y` — it is often more natural than an `ado` block.

Neither is wrong. `ado` is the more general tool; `liftN` is the sharper one for small cases.


---

## Leading pipe in case expressions

Related to ADT formatting, the same question arises in `case` expressions:

```purescript
-- Leading pipe: each branch starts with the same visual marker.
render = case _ of
  Loading -> HH.text "Loading..."
  Error msg -> HH.div_ [ HH.text msg ]
  Ready content -> viewContent content
```

```purescript
-- This is the only style PureScript supports for case expressions.
-- Unlike Haskell, there is no layout-based alternative with leading pipes.
```

For `case` expressions, PureScript's syntax settles the question: each branch is an arrow (`->`), and the visual structure is determined by indentation. The "leading pipe" debate applies to data declarations and top-level pattern matches, not to `case` expressions. Where it does apply — in `data` declarations — see the ADT formatting entry above.
