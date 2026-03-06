# The Elements of PureScript Style — Entries 9-32


---

## 9. An Effect is a recipe, not an action

In JavaScript, calling `fetch(url)` sends the request. The function *does* the work. In PureScript, a value of type `Effect Unit` or `Aff String` does nothing at all. It is a description of work — a recipe that says "when executed, do this." The recipe only runs when it is wired into `main` or handed to the Halogen runtime or passed to `launchAff_`.

This distinction is not academic. It is the reason you can pass effects around as values, store them in data structures, compose them with `>>=` and `<*>`, and choose at the last moment whether to run them at all.

```purescript
-- This does not log anything. It produces a value that, if run, would log.
greet :: Effect Unit
greet = log "hello"

-- This logs twice, because the recipe is executed twice.
main :: Effect Unit
main = do
  greet
  greet
```

The confusion usually surfaces when a newcomer writes a function that "should do something" but has no visible effect. The function is constructing a recipe; nothing runs it. If you find yourself asking "why doesn't this do anything?" — check whether the `Effect` or `Aff` value you built is actually composed into something that executes.

Every other rule about effects follows from this one. `traverse_`, `when`, `launchAff_`, `forkAff` — these are all combinators for assembling and running recipes. Once the recipe metaphor clicks, the rest is plumbing.


---

## 10. Use Aff for async, not callbacks [JavaScript]

This is what JavaScript async looks like when it accumulates:

```javascript
fetchUsers(url, (err, users) => {
  if (err) return handleError(err);
  fetchConfig(configUrl, (err, config) => {
    if (err) return handleError(err);
    fetchPermissions(users[0].id, (err, perms) => {
      if (err) return handleError(err);
      render(users, config, perms);
    });
  });
});
```

Three levels of nesting, each with its own error check, and the actual work (`render`) buried at the deepest point. PureScript's `Aff` monad exists to absorb callbacks at the boundary and present sequential, typed code to the rest of your program.

```purescript
-- Wrap a callback-based API once.
fetchText :: String -> Aff String
fetchText url = makeAff \callback -> do
  xhr <- newXHR
  onLoad xhr \_ -> do
    body <- responseText xhr
    callback (Right body)
  open xhr "GET" url
  send xhr
  pure nonCanceler

-- Then use it as plain sequential code.
loadAll :: Aff { users :: String, config :: String, perms :: String }
loadAll = do
  users <- fetchText "/api/users"
  config <- fetchText "/api/config"
  perms <- fetchText "/api/permissions"
  pure { users, config, perms }
```

The `makeAff` wrapper is the last place callbacks should appear. Once wrapped, everything downstream is `do`-notation — no nesting, no `.then` chains, no pyramid of doom. If you find callback-shaped indentation in PureScript, the boundary is in the wrong place.


---

## 11. Attach a Canceler to every makeAff

Every `makeAff` must return a `Canceler`. This is not a suggestion from the type system — it is a requirement. But the compiler only checks that you return *a* `Canceler`, not that it does anything useful. The responsibility for meaningful cancellation is yours.

```purescript
-- Correct: clean up the resource on cancellation.
listenOnce :: EventTarget -> String -> Aff Event
listenOnce target eventName = makeAff \callback -> do
  listener <- eventListener \ev -> callback (Right ev)
  addEventListener (EventType eventName) listener false target
  pure $ Canceler \_ -> liftEffect $
    removeEventListener (EventType eventName) listener false target

-- Acceptable when there is genuinely nothing to cancel.
sleep :: Int -> Aff Unit
sleep ms = makeAff \callback -> do
  _id <- setTimeout ms (callback (Right unit))
  pure nonCanceler
```

Forgetting the canceler — or always returning `nonCanceler` out of habit — means fibers cannot be cleanly killed. Event listeners accumulate, timers fire into dead contexts, and network requests complete for nobody. Even the `sleep` example above would benefit from `clearTimeout` in a production codebase. When in doubt, cancel something. When truly nothing can be cancelled, write `nonCanceler` explicitly so the reader knows you considered it.


---

## 12. Use parallel/sequential for concurrent Aff

When two asynchronous operations do not depend on each other, run them concurrently. PureScript provides two mechanisms: the `parallel`/`sequential` combinators (and their convenience wrappers `parTraverse`, `parSequence`) and manual fiber management (`forkAff`/`joinFiber`). Prefer the first.

```purescript
-- Prefer: declarative concurrency via parTraverse.
loadAll :: Array String -> Aff (Array String)
loadAll urls = parTraverse fetchText urls

-- Or with applicative combinators:
loadDashboard :: Aff Dashboard
loadDashboard = sequential $
  { users: _, metrics: _, config: _ }
    <$> parallel (fetchText "/users")
    <*> parallel (fetchText "/metrics")
    <*> parallel (fetchText "/config")
```

```purescript
-- Over: manual fiber management for simple concurrency.
loadDashboard :: Aff Dashboard
loadDashboard = do
  fiberU <- forkAff (fetchText "/users")
  fiberM <- forkAff (fetchText "/metrics")
  fiberC <- forkAff (fetchText "/config")
  users   <- joinFiber fiberU
  metrics <- joinFiber fiberM
  config  <- joinFiber fiberC
  pure { users, metrics, config }
```

The parallel combinators express the *structure* of the concurrency — these things are independent — without requiring you to manage the *mechanism* of fibers. Reserve `forkAff` for long-running background work where you genuinely need a handle to the fiber for later supervision or cancellation.


---

## 13. ado notation: powerful but subtle

`ado` (applicative do) desugars to `Apply` rather than `Bind`, which means the computations are independent — none uses the result of another. In `Aff`, this enables concurrency. In `Maybe` and `Either`, it documents independence. In `Validation`, it is the only option (there is no `Monad` instance).

```purescript
renderCard :: Aff HTML
renderCard = ado
  user    <- fetchUser userId
  avatar  <- fetchAvatar userId
  badges  <- fetchBadges userId
  in renderProfile user avatar badges
```

The case for `ado` is real. But the syntax introduces subtleties that trip up newcomers and experienced programmers alike:

- In `do`, each bound variable is in scope for subsequent bindings. In `ado`, it is not — the bindings are independent by definition.
- `let` inside `ado` is evaluated at the end, with all bindings in scope. But `let` in `do` is evaluated in order. The identical syntax does different things.
- The `in` keyword at the end looks like `let ... in` but is not. The scoping rules are different.

Nate Faubion on the PureScript Discord: "ado syntax is well defined and makes sense in the context of applicatives, but in comparison to do, its scoping for each bind and let is different, which can be confusing to newcomers to understand why something that looks so superficially similar actually operates so differently."

His recommendation for beginners: ignore `ado` initially. "Why does this exist when I can just use `do`" is the immediate question, and the answers require understanding Applicative vs Monad — a distinction most newcomers are still building intuition for.

For experienced programmers, `ado` is a precise tool. For codebases with mixed experience levels, `do` with a comment noting independence may be clearer. See also De Gustibus: "`ado` vs `liftN`."


---

## 14. Keep FFI files minimal; put logic in PureScript

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

## 15. Use EffectFn/Fn for uncurried FFI

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

## 16. Use Nullable for values that may be null

JavaScript APIs routinely return `null` or `undefined`. Rather than pretending the value will always be there (and crashing at runtime), use `Nullable` from `Data.Nullable` to make the possibility explicit at the FFI boundary.

```purescript
foreign import getElementByIdImpl :: String -> Effect (Nullable Element)

getElementById :: String -> Effect (Maybe Element)
getElementById id = toMaybe <$> getElementByIdImpl id
```

`Nullable` exists specifically for this: it maps directly to JavaScript's null/undefined semantics and converts cleanly to `Maybe` via `toMaybe`. It is the right tool for single values that might be absent. Do not use `Foreign` decoding when `Nullable` suffices — the lighter tool communicates the simpler situation.

For richer structures coming across the boundary, see entry 16a.


---

## 16a. Parse foreign data at the boundary

JavaScript can return a number where you expected a string, or an object missing half its fields. The PureScript type system has no jurisdiction over foreign land. It is your job to check papers at the border.

```purescript
-- Dangerous: trusting JavaScript to return the right shape.
foreign import getConfigImpl :: Effect { timeout :: Int, retries :: Int }

-- Safe: treating the return as foreign data and decoding it.
foreign import getConfigImpl :: Effect Foreign

getConfig :: Effect (Either String { timeout :: Int, retries :: Int })
getConfig = do
  raw <- getConfigImpl
  pure $ runExcept $ do
    timeout <- readInt =<< readProp "timeout" raw
    retries <- readInt =<< readProp "retries" raw
    pure { timeout, retries }
```

The principle is what Alexis King calls "parse, don't validate": do not check that the data looks right and then use it unsafely — transform it into a type that *cannot* be wrong. The `Foreign` decoder is a parser. Once it succeeds, the result is a genuine PureScript value with full type guarantees. If the JavaScript function "always returns a string," it will return `undefined` the week after you ship.

This applies beyond the FFI. Any data arriving from outside your program — JSON from an API, query parameters from a URL, configuration from a file — should be parsed into a typed representation at the boundary and never trusted as raw input beyond that point.


---

## 17. Never use unsafeCoerce as a substitute for proper types

`Unsafe.Coerce.unsafeCoerce` tells the compiler "trust me, this value has this type." The compiler obliges. It has no choice. When you are wrong — and you will eventually be wrong — the error surfaces at runtime, far from the coercion, with no indication of what went awry.

```purescript
-- This compiles. It will fail at runtime in creative ways.
foreign import getMetadata :: Effect Foreign

metadata :: Effect { title :: String }
metadata = unsafeCoerce <$> getMetadata
```

```purescript
-- This also compiles, and fails at compile time when the shape is wrong.
metadata :: Effect (Either String { title :: String })
metadata = do
  raw <- getMetadata
  pure $ decode raw
```

Legitimate uses of `unsafeCoerce` exist — primarily in library internals where the author has proven a type equivalence that PureScript's type system cannot express. Application code should never need it. If you reach for `unsafeCoerce` because a `Foreign` decoder feels like too much ceremony, the ceremony is the point. It is the type system asking you to prove that you know what you have.


---

## 18. Ensure stack safety with tailRecM

In Haskell, monadic recursion is stack-safe by default because laziness defers the frames. PureScript is strict. A recursive monadic computation that recurs a thousand times will build a thousand stack frames and may overflow.

```purescript
-- Unsafe: each iteration adds a stack frame.
countDown :: Int -> Effect Unit
countDown 0 = pure unit
countDown n = do
  log (show n)
  countDown (n - 1)

-- Safe: tailRecM runs in constant stack.
countDown :: Int -> Effect Unit
countDown = tailRecM go
  where
  go 0 = do
    pure (Done unit)
  go n = do
    log (show n)
    pure (Loop (n - 1))
```

The `MonadRec` class and `tailRecM` provide a trampolining mechanism: instead of recursing directly, you return `Loop` to continue or `Done` to finish. The runtime drives the loop without growing the stack.

This matters whenever your recursion depth is proportional to data size rather than code structure. A three-branch case expression is fine. A fold over ten thousand elements needs `tailRecM` or one of the library combinators (`foldRecM`, `whileM`) that use it internally. If you are porting Haskell code that uses `forever` or deep `>>=` chains, this is the first thing to check.


---

## 19. Mutual recursion defeats TCO

The PureScript compiler performs tail-call optimisation on self-recursive functions — a function that calls itself in tail position becomes a JavaScript `while` loop. But if function `A` calls function `B` which calls function `A`, neither is self-recursive, and no optimisation occurs.

```purescript
-- No TCO: mutual recursion builds stack frames.
isEven :: Int -> Boolean
isEven 0 = true
isEven n = isOdd (n - 1)

isOdd :: Int -> Boolean
isOdd 0 = false
isOdd n = isEven (n - 1)

-- TCO-friendly: fuse into a single self-recursive function.
isEven :: Int -> Boolean
isEven = go true
  where
  go acc 0 = acc
  go acc n = go (not acc) (n - 1)
```

The general technique is to merge the mutually recursive functions into one function with a tag parameter (here, the boolean accumulator) that distinguishes what was formerly a call to `isEven` from a call to `isOdd`. The result is a single self-recursive function the compiler can optimise.

For more complex cases where fusion is awkward, `tailRecM` (entry 18) works as well: represent the choice of "which function to call next" as part of the `Loop` value.


---

## 20. Write explicit forall

PureScript does not silently introduce type variables. If a type signature mentions `a`, you must write `forall a.` to bring it into scope. There is no implicit universal quantification.

```purescript
-- Does not compile: `a` is not in scope.
identity :: a -> a
identity x = x

-- Compiles.
identity :: forall a. a -> a
identity x = x
```

This is one of the first surprises for Haskell programmers, where `identity :: a -> a` works without ceremony. In PureScript, the explicitness is deliberate — it makes the binding site of every type variable visible, which matters more as signatures grow complex with constraints, higher-rank types, and visible type applications.

When you see a compiler error about an undefined type, and the name in question is a lowercase single letter, you almost certainly forgot a `forall`.


---

## 21. Use <<< for composition, not .

In Haskell, `(.)` is function composition. In PureScript, the dot is reserved for record access and module-qualified names. Composition uses `<<<` (right-to-left) and `>>>` (left-to-right).

```purescript
-- PureScript composition.
normalise :: String -> String
normalise = trim <<< toLower

-- Or, reading left-to-right:
normalise = toLower >>> trim
```

There is nothing more to say. The syntax is different; the concept is identical. If you find yourself writing `f . g` and getting a confusing parse error about records, this is why.


---

## 22. Number literals are not overloaded — and the numeric hierarchy is different

In Haskell, `1` has type `Num a => a` — it can be an `Int`, an `Integer`, a `Double`, or any other numeric type. In PureScript, `1` is an `Int` and `1.0` is a `Number`. There is no `Num` class and no `fromInteger`.

```purescript
-- Does not compile: 1.0 is Number, not Int.
addOne :: Int -> Int
addOne x = x + 1.0

-- Explicit conversion when needed.
scale :: Int -> Number
scale n = toNumber n * 2.5
```

This rigidity avoids an entire class of ambiguity errors that Haskell programmers know well (`"Ambiguous type variable 'a' arising from the literal '1'"`). The trade-off is that you must convert explicitly between `Int` and `Number` with `toNumber` and `round`/`floor`/`ceil`.

The differences go deeper than literals. PureScript's numeric type class hierarchy — `Semiring`, `Ring`, `CommutativeRing`, `EuclideanRing`, `Field` — is more algebraically principled than Haskell's `Num`. Each class corresponds to a genuine algebraic structure with laws. `Semiring` gives you `(+)` and `(*)` with identity elements. `Ring` adds negation. `EuclideanRing` adds integer division and `mod`. `Field` adds real division. There is no grab-bag class that bundles unrelated operations together.

In practice, this means: `(+)` requires `Semiring`, `(-)` requires `Ring`, `div` and `mod` require `EuclideanRing`, and `(/)` requires `Field`. When you see a constraint like `EuclideanRing a =>`, you know exactly which operations are available and which algebraic laws they satisfy. The hierarchy is more to learn upfront, but it eliminates the "why does `Num` require `abs` and `signum`?" puzzlement that Haskell programmers accept as normal.


---

## 23. Use newtypes to avoid orphan instance errors

PureScript enforces a strict rule: a type class instance must be defined in the module that defines the class or in the module that defines the type. Defining it anywhere else is an orphan instance, and the compiler rejects it outright.

```purescript
-- In module MyApp.Display:
-- Does not compile: neither Show nor ThirdPartyType is defined here.
instance Show ThirdPartyType where
  show _ = "ThirdPartyType"
```

The solution is a newtype wrapper. The newtype is defined in your module, so you are free to give it any instance you like.

```purescript
newtype Displayable = Displayable ThirdPartyType

instance Show Displayable where
  show (Displayable t) = "ThirdPartyType(...)"
```

This comes up constantly when integrating third-party libraries. You want `Encode` for a type from one package and `Decode` for a type from another, and the compiler refuses both. The newtype is not boilerplate — it is the module system telling you to be explicit about which behaviour you intend. If you control the type, put the instance with the type. If you control the class, put the instance with the class. If you control neither, newtype.

The restriction exists to prevent incoherence — the situation where two modules define different instances for the same class-type pair, and the one you get depends on which module was imported. Haskell allows orphans with a warning; PureScript closes the door entirely.


---

## 24. There are no default method implementations

In Haskell, a type class can provide default implementations for some methods in terms of others. You might define only `fmap` and get `<$` for free. PureScript does not have this feature. Every method in every instance must be written.

```purescript
-- You must provide both, even if one is trivially derived from the other.
instance Eq MyType where
  eq a b = ...

instance Ord MyType where
  compare a b = ...
```

This is a deliberate design choice — it keeps the instance resolution machinery simpler and the instance declarations explicit. The practical consequence is that shared logic should live in named helper functions, not in default methods. If five instances share the same implementation of a method, extract that implementation and call it from each instance. The repetition is real but small, and the explicitness prevents surprises when the "default" is not what you expected.


---

## 25. Write functions over Foldable, not concrete containers

When a function folds, traverses, or checks membership, constrain it with `Foldable` or `Traversable` rather than naming a specific container. The function works the same; the caller is free to supply whichever collection they have.

```purescript
-- Prefer: works with Array, List, NonEmptyArray, Set, or any Foldable.
total :: forall f. Foldable f => f Int -> Int
total = foldl (+) 0

-- Over: needlessly locked to Array.
total :: Array Int -> Int
total = foldl (+) 0
```

The generalised version costs nothing at the call site — an `Array Int` is still a valid argument — and gains flexibility at every future call site that happens to have a `List` or `NonEmptyArray`.

**A note on performance**: on the JavaScript backend, `Array` is a JavaScript array with O(1) indexed access and good cache locality, making it the pragmatic choice when you need speed. But PureScript targets multiple backends — Erlang, Python, Lua — where the performance story is different. Writing to `Foldable` keeps your code portable. Specialise to a concrete type in the inner loop where profiling tells you to, not as a default across your API.

The Haskell habit of defaulting to `[]` (a cons list) and optimising later does not transfer directly. But the fix is not "always use Array" — it is "always abstract over the container, and choose the concrete type where it matters."


---

## 26. Operator sections use _, not partial application syntax

Haskell's operator sections let you write `(+ 2)` to mean "a function that adds 2 to its argument." PureScript uses an underscore placeholder instead.

```purescript
-- PureScript operator sections.
addTwo    = (_ + 2)
divideBy  = (10 / _)
wrapInDiv = HH.div_ <<< pure

-- This does NOT work:
addTwo = (+ 2)  -- parse error
```

The underscore syntax is more general than Haskell's: it works uniformly for both left and right sections and extends to record access (`_.name`) and function application (`f _ 3`). The price is two extra characters. The benefit is that the section is never ambiguous — you can always see which argument is missing.


---

## 27. Use Traversable to combine effects over structures

`Traversable` generalises "do something effectful to each element and collect the results." If you find yourself pattern-matching on a container just to map an effectful function and reassemble, you are re-implementing `traverse`.

```purescript
-- Prefer: traverse handles the structure.
validateAll :: forall f. Traversable f => f Input -> Either Error (f Validated)
validateAll = traverse validate

-- Over: manually destructuring and reassembling.
validateBoth :: Tuple Input Input -> Either Error (Tuple Validated Validated)
validateBoth (Tuple a b) = Tuple <$> validate a <*> validate b
```

`traverse` works with any `Traversable` container and any `Applicative` effect. This means the same function validates an `Array`, a `List`, a `Maybe`, or a `Pair` — and the effect can be `Either`, `Aff`, `V`, or anything else with an `Applicative` instance.

The key insight: `Traversable` is to effectful operations what `Functor` is to pure ones. Just as you would never manually unpack a container to apply a pure function (you use `map`), you should not manually unpack a container to apply an effectful one.


---

## 28. Use foldMap instead of map followed by fold

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

## 29. Require NonEmpty when emptiness is impossible

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

## 30. Use Data.Map and Data.Set, not hand-rolled lookups

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


---

## 31. Give instances for containers you define

If you define a data structure that holds values, give it `Functor`, `Foldable`, and `Traversable` instances. Without them, every consumer must destructure your type manually, and it cannot participate in generic algorithms.

```purescript
data Pair a = Pair a a

derive instance Functor Pair

instance Foldable Pair where
  foldl f z (Pair a b) = f (f z a) b
  foldr f z (Pair a b) = f a (f b z)
  foldMap f (Pair a b) = f a <> f b

instance Traversable Pair where
  traverse f (Pair a b) = Pair <$> f a <*> f b
  sequence (Pair fa fb) = Pair <$> fa <*> fb
```

With these three instances, `Pair` immediately works with `traverse`, `for_`, `foldMap`, `sum`, `length`, `toArray`, and every other function polymorphic over `Foldable` or `Traversable`. Without them, it is an island — usable only through its own API. The instances are small, often derivable, and they pay for themselves the first time someone writes `traverse_ validate (Pair left right)` instead of unpacking the pair by hand. In the age of AI-assisted coding, the cost of writing these instances — and the law-checking property tests to go with them — is negligible. There is no excuse for leaving them out.


---

## 32. Use coerce for zero-cost newtype conversions

Mapping `unwrap` or a constructor over a container converts each element, doing O(n) work for what is a no-op at runtime — newtypes are erased to their underlying type. `Safe.Coerce.coerce` performs the conversion in O(1) because it recognises the identical runtime representation.

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
