# IV. Errors and failure

There are two kinds of failure: the kind your program expects and the kind it does not. PureScript gives you different tools for each. Confusing them — catching unexpected errors, ignoring expected ones, or mixing both into one channel — produces code that is hard to reason about and harder to maintain.


---


## 46. Either short-circuits; know when that is what you want

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

The mistake is reaching for `Either` when the checks are *independent* — see entry 47.


---


## 47. Use V (Validation) to accumulate independent errors

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


## 48. Use ExceptT for expected failures, Aff's error for unexpected ones

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


## 49. Do not catch exceptions you cannot handle

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


## 50. Avoid dual error channels: do not return Effect (Either e a)

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


## 51. Use unsafeCrashWith for genuinely unreachable code

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


## 52. Alt and Alternative: first success wins

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
