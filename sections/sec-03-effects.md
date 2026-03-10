# III. Effects are recipes

In PureScript, an effectful value does not *do* anything. It *describes* something to be done. This distinction — effects as data, not as actions — is the foundation of everything else: composition, concurrency, testing, and reasoning. Once the recipe metaphor clicks, the combinators are plumbing.


---


## 31. An Effect is a recipe, not an action

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


## 32. Use Aff for async, not callbacks [JavaScript]

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


## 33. Use when and unless, not if-then-pure-unit

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

Note that `when` requires only an `Applicative` constraint, not `Monad` — so it works in more contexts than `do` notation does. This applies anywhere you find yourself writing `else pure unit`: `Effect`, `Aff`, `StateT`, Halogen's `HalogenM`, and any other `Applicative`.


---


## 34. Sometimes map will do

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


## 35. Understand Apply vs Bind and choose deliberately

PureScript gives you a choice that most languages do not. `Bind` (and `do` notation) sequences computations where each step may depend on the result of the previous one. `Apply` (and `ado` notation) combines computations that are independent.

Prefer:

```purescript
ado
  user    <- fetchUser uid
  friends <- fetchFriends uid
  in { user, friends }
```

Over:

```purescript
do
  user    <- fetchUser uid
  friends <- fetchFriends uid
  pure { user, friends }
```

The distinction is not merely semantic. In `Aff`, `Apply` can run both fetches concurrently via `parApply`. In `Validation`, `Apply` accumulates errors from both branches. In a free monad, `Apply` enables static analysis of the computation's structure. `Bind` forecloses all of these because it promises the second computation may depend on the first.

Use `do` when there is a genuine dependency -- when the URL you fetch in step two is computed from the result of step one. Use `ado` when you are simply gathering independent results. The types are telling the truth either way; the question is whether you are.


---


## 36. ado notation: powerful but know the sharp edges

The previous entry introduced the Apply/Bind distinction. `ado` (applicative do) is the syntax for the Apply side — it desugars to `Apply` rather than `Bind`, which means the computations are independent. In `Aff`, this enables concurrency. In `Maybe` and `Either`, it documents independence. In `Validation`, it is the only option (there is no `Monad` instance).

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


## 37. Applicative for building, Monad for deciding

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


## 38. Attach a Canceler to every makeAff

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


## 39. Use parallel/sequential for concurrent Aff

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


## 40. parTraverse and parSequence cover 80% of parallel Aff

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


## 41. Use STRef with ST.run for locally-scoped mutation

It might surprise you to learn that PureScript has an escape hatch for mutation — but it should not surprise you to learn that it is a very principled and precise one. When an algorithm needs mutable state for performance — building an array in a loop, accumulating into a hash map, running an in-place sort — `ST` gives you mutation with a pure interface.

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


## 42. Prefer Ref only at application boundaries

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


---


## 43. Use newtypes for monad transformer stacks

A type alias for a transformer stack is transparent — every function that uses it must be compatible with the fully expanded type, and error messages show the expanded form.

Prefer:

```purescript
newtype AppM a = AppM (ReaderT Config (ExceptT AppError Aff) a)

derive newtype instance Functor AppM
derive newtype instance Apply AppM
derive newtype instance Applicative AppM
derive newtype instance Bind AppM
derive newtype instance Monad AppM
derive newtype instance MonadAsk Config AppM
derive newtype instance MonadThrow AppError AppM
derive newtype instance MonadEffect AppM
derive newtype instance MonadAff AppM
```

Over:

```purescript
type AppM = ReaderT Config (ExceptT AppError Aff)
```

The newtype version lets you write `doSomething :: AppM Unit` and see `AppM` in error messages, not `ReaderT Config (ExceptT AppError Aff)`. The derived instances are one-time boilerplate — they delegate to the wrapped stack and cannot be wrong. The type alias version saves five minutes of setup and costs readability for the life of the project.

The newtype also gives you a place to hang custom instances. If `AppM` needs a `MonadLogger` instance that logs to a specific sink, you define it on the newtype. With a type alias, you would need an orphan instance or a workaround.


---


## 44. Prefer polymorphic monad constraints over concrete Effect

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


## 45. A transformer stack is only as stack-safe as its base

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
