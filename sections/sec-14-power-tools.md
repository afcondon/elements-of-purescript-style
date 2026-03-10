# XIV. Power tools — when to wield, when to sheathe

PureScript offers type-level programming, extensible effects, and generic programming over row types. These are genuine capabilities, not parlour tricks. But they carry costs in compile time, error message clarity, and code legibility. Reach for them when simpler tools fall short, not before.


---


## 149. Do not reproduce a lax type system with powerful tools

Do not be seduced into reproducing a more lax type system with PureScript's powerful tools. `Variant`, `RowList`, and heterogeneous record machinery are genuine capabilities, but the temptation is to reach for them to build the kind of loose, dynamic-feeling structures familiar from less precise languages — open unions where a closed sum type would do, generic record traversals where three concrete functions would suffice.

```purescript
-- If your sum type has four constructors, this is the right tool:
data Output = Clicked | Hovered | Selected String | Dismissed

-- This is not an improvement:
type Output = Variant
  ( clicked :: Unit
  , hovered :: Unit
  , selected :: String
  , dismissed :: Unit
  )
```

**When Variant and heterogeneous types earn their keep.** These tools have legitimate uses — the key is that they solve *extensibility* problems that closed types cannot.

Effect rows in `Run` are the clearest example. Each module contributes its own effects, and the application composes them without a central sum type that every module must import:

```purescript
-- Each module defines its own effect; the application never enumerates them all.
type AppEffects = (db :: DB, log :: LOG, auth :: AUTH)

app :: forall r. Run (AppEffects + r) Unit
```

Extensible component outputs are another. A reusable component that emits outputs should let its parent extend the output row without forking the component:

```purescript
-- The parent can add its own cases without modifying the child.
type ChildOutput r = Variant (saved :: Entity, deleted :: EntityId | r)
```

In both cases, the defining characteristic is that the set of cases is genuinely *open* — downstream code must add its own cases without modifying the original type.

**The costs are real.** Type errors involving `RowList` constraints routinely span twenty lines. Compile times grow. Editor tooling struggles. The code resists casual modification. Start with a sum type. Move to `Variant` when you hit a concrete extensibility requirement that the sum type cannot satisfy. Reach for `RowList` traversal when the set of fields is genuinely unknown at definition time — not as a first resort.


---


## 150. Use type-level code for what only type-level code can do

Type-level programming in PureScript — `Symbol`, `RowList`, type-class-level computation with functional dependencies — is a real capability, not a party trick. Libraries like `simple-json` and `routing-duplex` use it to derive codecs and parsers from types alone, eliminating entire categories of boilerplate.

But type-level code has real costs. Compile times increase, sometimes dramatically. Error messages become walls of unsolved constraint text that even experienced programmers must squint at. And the code is legible only to the subset of PureScript programmers who have internalized the type-level idioms — a set that, in a small community, may be a set of one.

```purescript
-- Type-level: generic JSON codec derived by walking the RowList.
-- Powerful, but error messages are walls of unsolved constraints.
encodeRecord :: forall r rl
   . RowToList r rl
  => EncodeJsonRL rl r
  => Record r -> Json

-- Value-level: explicit codec, readable errors, sufficient for one type.
encodeUser :: User -> Json
encodeUser u = encodeJson { name: u.name, email: u.email }
```

The first version eliminates boilerplate across many record types — it earns its keep in a library like `simple-json`. The second is more readable, produces better errors, and is sufficient when you control the types. Note that row polymorphism (`forall r. { port :: Int | r } -> Effect Unit`) is *not* what this entry is about — open records are basic PureScript and should be used freely. The warning applies to `RowList` iteration, `Symbol` manipulation, type-class-level computation with functional dependencies, and `Proxy`-heavy APIs.

Reserve type-level machinery for guarantees that must hold at compile time and cannot be expressed any other way. If a plain function over a sum type solves the problem, it solves the problem.


---


## 151. Match the abstraction to the problem (Run, free monads, extensible effects)

`Run` is an extensible effects system built on free monads over variant rows. It lets you define effects as data types, compose them as row-polymorphic unions, and swap interpreters without changing business logic. If you have read the literature on algebraic effects or used `Eff` in Haskell's `freer-simple` or `polysemy`, the idea is familiar.

For a large application with many interchangeable effect interpreters — say, a production interpreter that hits a database and a test interpreter that uses an in-memory map — `Run` is a legitimate architectural choice. The effect rows document exactly which capabilities a function requires, and the interpreters are first-class values you can compose and test independently.

For a Halogen app with two or three effects — reading config, making HTTP requests, logging — `ReaderT Config Aff` is simpler, faster, and understood by every PureScript programmer who has read the Halogen guide. The overhead of defining effect types, writing interpreters, and resolving the row-polymorphic constraints is not justified by the flexibility you gain when there is only one interpreter you will ever use.

```purescript
-- For most Halogen apps, this is enough:
newtype AppM a = AppM (ReaderT Env Aff a)

-- Run earns its keep when you need this:
type AppEffects = (db :: DB, log :: LOG, auth :: AUTH, cache :: CACHE)

app :: forall r. Run (AppEffects + r) Unit
```

Match the abstraction to the problem. If you are not swapping interpreters, you are paying for extensibility you do not use.


---


## 152. Never use unsafeCoerce to hide types; use the CPS existential pattern

When you need to store values of different types in a collection, or pass a value whose concrete type the consumer need not know, the temptation is to reach for `unsafeCoerce` or `Foreign` to erase the type and cast it back later. This is unsafe in the precise sense that the compiler cannot check it — a refactor that changes the hidden type will compile successfully and crash at runtime.

The safe alternative is the continuation-passing style (CPS) existential encoding described in entry 118. To recap the pattern briefly:

```purescript
-- Hide a concrete type behind a constraint.
newtype SomeShowable = SomeShowable (forall r. (forall a. Show a => a -> r) -> r)

mkSomeShowable :: forall a. Show a => a -> SomeShowable
mkSomeShowable a = SomeShowable \k -> k a

-- Use it: the consumer never learns the concrete type.
showHidden :: SomeShowable -> String
showHidden (SomeShowable run) = run show
```

The consumer provides a function that works for *any* type satisfying `Show`, and the hidden value is applied to it. No casts, no runtime tags, no possibility of mismatch.

The alternative — `unsafeCoerce`-ing to `Foreign` and casting back — is the kind of code that works until someone changes the hidden type. The CPS encoding makes that same change a compile error, which is where you want to discover it.

If the rank-2 types feel unfamiliar, invest the time to understand entry 118's explanation. The pattern appears throughout the ecosystem, and it is the idiomatic way to express existentials in PureScript.


---


## 153. Existentials are an anti-pattern unless you have measured a performance need

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


## 154. Monomorphise hot paths

Polymorphic functions in PureScript are compiled to JavaScript functions that receive type class dictionaries as extra arguments. At each call site, the compiler passes the appropriate dictionary. This is the mechanism behind ad-hoc polymorphism, and for most code the overhead is negligible.

In tight loops or performance-critical sections, the dictionary lookup and indirect call can matter. If profiling reveals a polymorphic function as a bottleneck, write a monomorphic wrapper:

```purescript
-- Polymorphic:
sumWith :: forall a. Semiring a => Array a -> a
sumWith = foldl add zero

-- Monomorphic, for a hot path:
sumNumbers :: Array Number -> Number
sumNumbers = foldl add zero
```

The monomorphic version allows the compiler (and the JavaScript engine's JIT) to eliminate the dictionary indirection. But profile first. The overwhelming majority of PureScript code is not in a hot loop, and premature monomorphisation sacrifices generality for speed you may not need.

This is the complement to entry 64 on writing functions over `Foldable` (section VI). Both are right — generalise by default, specialise where profiling tells you to. The generic form is for API design; monomorphisation is for inner loops.


---
