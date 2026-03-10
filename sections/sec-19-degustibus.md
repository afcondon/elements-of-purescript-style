# De Gustibus

These are matters where reasonable PureScript programmers differ. We present the cases without ruling.


---


## `where` or `let`

Some prefer `where` for named helpers, reserving `let` for intermediate values within `do` blocks. The argument: `where` puts the main expression first, so the function reads top-down — topic sentence, then supporting detail.

```purescript
handleAction = case _ of
  Initialize -> generateLayout
  SetGridSize size -> do
    H.modify_ _ { gridSize = size }
    generateLayout
  where
  generateLayout = do
    state <- H.get
    let cells = waffle state.gridSize state.gridSize vp sampleCounts
    H.modify_ _ { cells = cells }

  vp = viewport 400.0 400.0
```

Others prefer `let` throughout, on the grounds that definitions should appear before their use — as they do in most languages — and that `where` scattering definitions below the expression makes them harder to locate in a long module.

```purescript
handleAction action = do
  let vp = viewport 400.0 400.0
  let generateLayout = do
        state <- H.get
        let cells = waffle state.gridSize state.gridSize vp sampleCounts
        H.modify_ _ { cells = cells }
  case action of
    Initialize -> generateLayout
    SetGridSize size -> do
      H.modify_ _ { gridSize = size }
      generateLayout
```

Both positions have merit. The compiler does not prefer one to the other.


---


## Point-free or pointed

Point-free style — defining functions without naming their arguments — can clarify or obscure depending on context.

When the pipeline is a clean chain of transformations, point-free is natural:

```purescript
normalise :: String -> String
normalise = toLower >>> trim >>> replaceAll (Pattern "  ") (Replacement " ")
```

When the logic involves branching or multiple uses of the same argument, naming it is clearer:

```purescript
classify :: Score -> Rating
classify score
  | unwrap score >= 90 = Excellent
  | unwrap score >= 70 = Good
  | otherwise = NeedsWork
```

The forced point-free version of the second would require gymnastics that help no one. Conversely, writing `normalise s = replaceAll ... (trim (toLower s))` nests where it could flow.

The test: if removing the argument name makes the function harder to read aloud, keep the name.


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

For types with more than two constructors, leading pipe has near-consensus, and `purs-tidy` formats accordingly. For single-line, two-constructor types, both are common and both are fine.


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

A practical heuristic from entry 134: keep modules under roughly 400 lines. This is loose enough to accommodate types with their instances and tight enough to prevent modules from becoming grab-bags. Split when a module has two unrelated responsibilities, not when it reaches an arbitrary line count.


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


---
