# The Elements of PureScript Style — Entries 59-94


---

## XIII. Power Tools — when to wield, when to sheathe


---

## 59. Phantom types and smart constructors replace most GADTs [Haskell]

Haskell programmers arriving in PureScript quickly notice the absence of GADTs. The instinct is to reach for elaborate type-class encodings that simulate them. In most cases, a phantom type parameter with smart constructors does the job — compiles faster, produces better error messages, and can be read by a colleague who has not studied the Hasochism paper.

In Haskell you might write `data Expr a where LitInt :: Int -> Expr Int; Add :: Expr Int -> Expr Int -> Expr Int`. In PureScript:

```purescript
data Expr (a :: Type) = LitInt Int | LitBool Boolean | Add (Expr Int) (Expr Int)

litInt :: Int -> Expr Int
litInt = LitInt

litBool :: Boolean -> Expr Boolean
litBool = LitBool

add :: Expr Int -> Expr Int -> Expr Int
add = Add
```

The phantom parameter does not appear in the data constructors, but the smart constructors enforce the relationship. Pattern matching still requires care — you are trading a compiler guarantee for a module-boundary discipline — but for most DSLs this is sufficient.


---

## 59a. Use continuation-passing style to encode existential types [Haskell]

In Haskell, `ExistentialQuantification` or GADTs let you write `data SomeShow = forall a. Show a => SomeShow a` — a type that hides the concrete type while retaining a constraint. PureScript does not have this syntax. The idiomatic alternative is a continuation-passing style (CPS) encoding using rank-2 types.

The idea: instead of storing the hidden value directly, you store a function that *accepts a handler* for any type satisfying the constraint, and applies it to the hidden value.

```purescript
-- "I have a Foldable container of Ints, but I won't tell you which one."
newtype SomeFoldable = SomeFoldable (forall r. (forall f. Foldable f => f Int -> r) -> r)

mkSomeFoldable :: forall f. Foldable f => f Int -> SomeFoldable
mkSomeFoldable fa = SomeFoldable \k -> k fa

-- To use the hidden value, provide a function that works for ANY Foldable:
sumHidden :: SomeFoldable -> Int
sumHidden (SomeFoldable run) = run \fa -> foldl (+) 0 fa
```

The caller of `sumHidden` never learns whether the hidden container was an `Array`, a `List`, or a `Set` — only that it was `Foldable`. No `unsafeCoerce`, no `Foreign`, no runtime tags. The rank-2 type does the work.

When you need a heterogeneous collection — "a list of things that can each be folded, but with different element types" — this is the PureScript answer. The pattern is worth learning once; it appears throughout the ecosystem.


---

## 59b. Use sum types directly for typed command/message patterns [Haskell]

When you want different payload types for different commands — `Command Insert` carrying an `InsertPayload`, `Command Delete` carrying a `DeletePayload` — the Haskell instinct is to index the command type by a phantom and use GADT matching to eliminate it. In PureScript, use a plain sum type:

```purescript
data Command
  = Insert InsertPayload
  | Delete DeletePayload
  | Update UpdatePayload
```

No phantom parameter, no type-level tag, no class instances to recover the payload type. The sum type is total, exhaustive, and obvious. Pattern matching gives you the payload directly, and the compiler ensures you handle every case.

The general principle: when the simpler encoding covers your use case, prefer it. PureScript's sum types are expressive enough for most command and message patterns, and the directness pays off in readability and error messages.


---

## 60. Do not reproduce a lax type system with powerful tools

PureScript's `Variant` (extensible sum types) and heterogeneous record machinery (`Record`, `RowList`, `HMap`) are genuinely powerful. The temptation, especially for programmers arriving from languages with less precise types, is to reach for these tools to build the kind of loose, dynamic-feeling structures they are used to — open unions where a closed sum type would do, generic record traversals where three concrete functions would suffice.

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

The `Variant` version becomes worthwhile when the set of cases is genuinely *open* — when downstream consumers need to add their own cases without modifying the original type, or when you are building a framework where effect rows are composed from independent modules:

```purescript
-- Effect rows in Run: each module contributes its own effects.
type AppEffects = (db :: DB, log :: LOG, auth :: AUTH)

-- Extensible output in a component framework:
type ChildOutput r = Variant (saved :: Entity, deleted :: EntityId | r)
```

These are real use cases. But they carry real costs: type errors involving `RowList` constraints routinely span twenty lines, compile times grow, editor tooling struggles, and the code resists casual modification. Start with a sum type. Move to `Variant` when you hit a concrete extensibility requirement that the sum type cannot satisfy. Reach for `RowList` traversal when the set of fields is genuinely unknown at definition time — not as a first resort.


---

## 61. Use type-level code for what only type-level code can do

Type-level programming in PureScript — `Symbol`, `RowList`, type-class-level computation with functional dependencies — is a real capability, not a party trick. Libraries like `simple-json` and `routing-duplex` use it to derive codecs and parsers from types alone, eliminating entire categories of boilerplate.

But type-level code has real costs. Compile times increase, sometimes dramatically. Error messages become walls of unsolved constraint text that even experienced programmers must squint at. And the code is legible only to the subset of PureScript programmers who have internalized the type-level idioms — a set that, in a small community, may be a set of one.

```purescript
-- Type-level: enforce at compile time that a config has a "port" field.
serveWithPort :: forall r. { port :: Int | r } -> Effect Unit

-- Value-level: validate at the boundary, use a known type internally.
type ServerConfig = { port :: Int, host :: String }

serve :: ServerConfig -> Effect Unit
```

The first version is more general. The second is more readable, produces better errors, and is sufficient if you control the call sites. The type-level version earns its keep in library APIs consumed by many unknown callers. In application code, where you control both the producer and consumer, the value-level version is almost always the right choice.

Reserve type-level machinery for guarantees that must hold at compile time and cannot be expressed any other way. If a plain function over a sum type solves the problem, it solves the problem.


---

## 62. Match the abstraction to the problem (Run, free monads, extensible effects)

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

## 63. Never use unsafeCoerce to hide types; use the CPS existential pattern

When you need to store values of different types in a collection, or pass a value whose concrete type the consumer need not know, the temptation is to reach for `unsafeCoerce` or `Foreign` to erase the type and cast it back later. This is unsafe in the precise sense that the compiler cannot check it — a refactor that changes the hidden type will compile successfully and crash at runtime.

The safe alternative is the continuation-passing style (CPS) existential encoding described in entry 59a. To recap the pattern briefly:

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

If the rank-2 types feel unfamiliar, invest the time to understand entry 59a's explanation. The pattern appears throughout the ecosystem, and it is the idiomatic way to express existentials in PureScript.


---

## XIV. Spago, the Registry, and the Build


---

## 64. Understand the package set vs the solver

Spago resolves dependencies in one of two ways. A *package set* is a fixed snapshot of the registry — a known-good collection of packages at specific versions, tested together. The *solver* resolves version ranges dynamically, like npm or Cargo, finding versions that satisfy all constraints.

```yaml
# Using a package set (reproducible, recommended for most projects):
workspace:
  packageSet:
    registry: 63.2.0

# Using the solver (flexible, needed for bleeding-edge packages):
workspace:
  packageSet:
    registry: 63.2.0
  extraPackages: {}
```

Package sets give reproducibility: every developer and CI run resolves to the same versions. The solver gives flexibility: you can use packages or versions not in the set. Most projects should start with a package set and reach for the solver only when they need something the set does not contain.

The most common source of "package not found" errors is confusion about which mode is active. If you are on a package set and the package was published after that snapshot, it does not exist as far as Spago is concerned. Either bump the registry version or add the package to `extraPackages`.


---

## 65. Use workspace.extraPackages for local and unpublished dependencies

When you depend on a local checkout, a git repository, or a package not yet in the registry, add it under `workspace.extraPackages` in your root `spago.yaml`. Do not hack the package set, symlink directories into `.spago`, or copy source files into your tree.

```yaml
workspace:
  packageSet:
    registry: 63.2.0
  extraPackages:
    # A local checkout (sibling directory):
    hylograph-canvas:
      path: ../purescript-hylograph-libs/canvas

    # A git dependency at a specific commit:
    some-experimental-lib:
      git: https://github.com/user/some-experimental-lib.git
      ref: a1b2c3d
      subdir: lib
```

The `path:` form is for local directories — monorepo siblings, packages under active development, forks with local patches. The `git:` form is for remote repositories pinned to a ref. Both integrate cleanly with the lock file and dependency resolution. Both are visible in one place, not scattered across shell scripts or build hacks.

When the package is eventually published to the registry and appears in a package set you adopt, remove the `extraPackages` entry. The override has served its purpose.


---

## 66. Keep spago.yaml minimal and let the lock file do its job

`spago.yaml` declares your intent: which packages you depend on, which version ranges you accept, which registry snapshot you use. `spago.lock` records what was actually resolved: exact versions, exact hashes, the full dependency tree.

```yaml
# spago.yaml — declare intent:
package:
  name: my-app
  dependencies:
    - aff
    - halogen
    - argonaut-codecs
```

Check in the lock file. Do not pin exact versions in `spago.yaml` unless you have a specific, documented reason — that is the lock file's job. Pinning versions in `spago.yaml` defeats the flexibility of range resolution and creates two sources of truth about which version is in use.

When you run `spago install`, Spago resolves dependencies and updates the lock file. When a colleague clones the repo and runs `spago build`, the lock file ensures they get the same versions you did. This is the same contract as `package-lock.json` or `Cargo.lock`. Trust it.


---

## 67. One workspace, many packages

Spago supports monorepos natively. A root `spago.yaml` defines the workspace — the package set, extra packages, and shared configuration. Sub-directories each have their own `spago.yaml` with a `package:` stanza declaring their name, dependencies, and source globs.

```yaml
# Root spago.yaml
workspace:
  packageSet:
    registry: 63.2.0
  extraPackages: {}

# packages/canvas/spago.yaml
package:
  name: hylograph-canvas
  dependencies:
    - effect
    - web-dom
  publish:
    version: 0.3.0
    license: MIT
```

This is how `purescript-hylograph-libs` manages fifteen-plus packages: one lock file, one package set, one CI pipeline. Each package can depend on its siblings by name, and Spago resolves the internal dependency graph.

Do not create separate repositories — with separate package sets, separate lock files, separate CI configurations — for packages that evolve together. The coordination cost of keeping N repositories in sync dwarfs the cost of a monorepo workspace. Separate repositories earn their keep when packages have genuinely independent release cycles and maintainers.


---

## 68. spago bundle vs spago build: know the difference

`spago build` compiles PureScript source to ES modules in the `output/` directory. Each PureScript module becomes a directory with an `index.js` file. This is sufficient for libraries, for Node applications that can consume ES module imports, and for any downstream tool that handles bundling itself.

`spago bundle` does everything `spago build` does and then runs esbuild to produce a single JavaScript file — a bundle suitable for loading in a browser via a `<script>` tag, or for deploying as a single-file Node script.

```yaml
# spago.yaml bundle configuration for a browser app:
package:
  name: my-app
  bundle:
    module: Main
    outfile: dist/bundle.js
    platform: browser
```

If your HTML loads `bundle.js`, you need `spago bundle`. If you are writing a library consumed by other PureScript packages, `spago build` is sufficient and `spago bundle` is unnecessary. Getting this wrong produces either "module not found" errors in the browser (because the browser cannot resolve ES module imports from `output/`) or an unnecessarily large bundle in Node (because esbuild inlined dependencies you did not need to inline).


---

## 69. Browser bundles need platform: browser

When bundling for the browser, your `spago.yaml` bundle configuration must include `platform: browser`. Without it, esbuild defaults to the Node platform and may leave in Node-specific imports — `fs`, `path`, `process`, `buffer` — that do not exist in the browser.

```yaml
# Correct:
package:
  bundle:
    module: Main
    platform: browser
    outfile: dist/app.js

# Missing platform — will default to node:
package:
  bundle:
    module: Main
    outfile: dist/app.js
```

The resulting error is often cryptic: a `ReferenceError: process is not defined` or `require is not a function` at runtime, not at build time. You stare at your PureScript source looking for the Node dependency and find nothing, because the import was introduced by a transitive JavaScript dependency that esbuild chose not to polyfill. The fix is one line in the config.


---

## 70. Set bundle.module to your entry point

`spago bundle` needs to know which module contains your application's `main` function. Set `bundle.module` in your `spago.yaml`:

```yaml
package:
  bundle:
    module: Main
    outfile: dist/bundle.js
    platform: browser
```

If omitted, the bundler may produce an empty file, a file that defines modules but never calls `main`, or an error that does not clearly indicate the problem. The fix is always the same: tell the bundler where to start.

This is especially easy to overlook in monorepo setups where each package has its own entry point. Each package that produces a bundle needs its own `bundle.module` declaration.


---

## 71. Do not import from output/ in your source

The `output/` directory is a build artifact generated by the PureScript compiler. It is not part of your source tree.

```purescript
-- Do not do this:
foreign import myHelper :: forall a. a -> Effect Unit
-- with an FFI file that says:
-- import { someFunction } from "../../output/Other.Module/index.js"

-- Do this:
import Other.Module (someFunction)
```

Importing from `output/` in your PureScript source or FFI files creates a circular dependency between the build system and your code. The `output/` directory may not exist yet when the compiler first runs. Its internal structure is a compiler implementation detail that may change between PureScript versions. And it defeats incremental compilation, because changes to one module now invalidate another through a path the compiler does not track.

Use PureScript imports for PureScript dependencies. If you need to call JavaScript, use the FFI mechanism — a `.js` file alongside your `.purs` file. Let the compiler and bundler resolve the paths.


---

## 72. Clear output/ when things make no sense

Incremental compilation is a tremendous convenience until it produces a stale artifact. This happens most often after renaming modules, changing the package set, switching git branches that reorganised the source tree, or upgrading the compiler.

The symptoms are distinctive: duplicate module errors for modules that exist only once, type errors that contradict what you can see in the source, "module not found" for a module you just created. The common thread is that the error does not match reality.

```bash
rm -rf output .spago
spago build
```

This costs thirty seconds on a clean build and saves thirty minutes of debugging a phantom. It is not a sign of a broken tool — incremental compilation systems in every language have this failure mode. The important thing is to recognise the symptoms and reach for the fix without guilt.

If you find yourself clearing `output/` routinely (more than once a week), something else is wrong — likely a build script that modifies source files in place, or a symlink that confuses the watcher.


---

## 73. The registry version must match what the solver sees

Your workspace's `packageSet.registry` field specifies a snapshot of the PureScript registry. Only packages published at or before that snapshot are visible to the resolver.

```yaml
workspace:
  packageSet:
    registry: 63.2.0  # Packages published after this snapshot are invisible.
```

A package that appears on Pursuit, that you can browse and read the documentation for, may nonetheless fail to resolve if it was published after your registry snapshot. The error — typically "package not found" or "no version satisfying constraint" — gives no hint that the issue is temporal.

The fix is either to bump the registry version to a snapshot that includes the package, or to add the package to `extraPackages` with an explicit source. When in doubt, check the package's publish date against your registry version.


---

## 74. Use spago ls packages and spago ls deps to debug resolution

When a package is "not found" and you are not sure why, two commands answer most questions:

```bash
# What packages does my current package set contain?
spago ls packages

# What does my resolved dependency tree look like?
spago ls deps
```

`spago ls packages` shows every package visible in your current package set, with its version. If the package you want is not listed, it is not in your snapshot — see entry 73. `spago ls deps` shows the resolved dependency tree for your project, including transitive dependencies. If a package appears in `ls packages` but not in `ls deps`, you have not added it to your `dependencies` list.

These commands are faster and more reliable than reading the Spago source, guessing at resolution logic, or asking in Discord. Use them before you debug.


---

## XV. Omit Needless Names


---

## 75. Use case _ of, not a named parameter you immediately case on

When a function's entire body is a pattern match on its argument, use `case _ of` — the anonymous lambda-case form.

Prefer:

```purescript
colorFor :: Status -> String
colorFor = case _ of
  Active   -> "#2d5a27"
  Inactive -> "#999"
  Error    -> "#c23b22"
```

Over:

```purescript
colorFor :: Status -> String
colorFor status = case status of
  Active   -> "#2d5a27"
  Inactive -> "#999"
  Error    -> "#c23b22"
```

The name `status` appears twice and communicates nothing the type signature did not already say. The `case _ of` form signals immediately that this function is *defined by cases* — its entire purpose is dispatching on the structure of its argument. The reader need not scan for other uses of `status` in the body, because there is no `status` to scan for.

This applies only when the argument is used once, for pattern matching, and nothing else. If the function also passes the argument to another function or uses it in a guard, name it.


---

## 76. Use _ for record updates in modify

When updating state in Halogen or any context that takes a record-update function, use the wildcard `_` instead of naming the record.

Prefer:

```purescript
H.modify_ _ { loading = true }
```

Over:

```purescript
H.modify_ \state -> state { loading = true }
```

The lambda version uses three tokens — `\state -> state` — to say "the record being updated." The wildcard says it in one. More importantly, the wildcard signals that nothing complex is happening: this is a field update, full stop. The lambda form looks identical to code that might do something more involved with `state` before updating it, and the reader must verify that it does not.

The record-update wildcard is PureScript-specific syntax. Newcomers often miss it because it does not exist in Haskell or most other ML-family languages. Once learned, it becomes second nature.


---

## 77. Use _.field for record access in map

When the body of a lambda is a single field access, use the accessor shorthand.

Prefer:

```purescript
map _.name items
```

Over:

```purescript
map (\item -> item.name) items
```

The shorthand `_.name` is a function from any record with a `name` field to that field's value. It is shorter, yes, but the real benefit is semantic: it says "extract this field" with no surrounding ceremony. The lambda version introduces a binding (`item`) that exists only to be immediately projected — the definition of a needless name.

The shorthand composes:

```purescript
map _.address.city users
```

This would be `map (\user -> user.address.city) users` in the explicit form — four tokens of binding for zero information. Let the syntax carry the meaning.


---

## 78. Do not name a value you immediately pass to one function

A `let` binding is documentation. It says: "this intermediate value has a role worth naming, or it will be used more than once." When neither is true, the binding is clutter.

Prefer:

```purescript
do
  user <- fetchUser id
  log user.name
```

Over:

```purescript
do
  user <- fetchUser id
  let name = user.name
  log name
```

The binding `name` exists for one line. It is consumed immediately and never referenced again. The reader must track it anyway — scanning ahead to confirm it is not used a second time, checking that it means what they think it means. Passing `user.name` directly eliminates this overhead.

This does not apply when the name genuinely clarifies intent. `let cutoff = 0.5` is fine even if used once, because `cutoff` tells the reader something that `0.5` does not. The test is not "how many times is it used?" but "does the name add information?"


---

## 79. The principle, stated

Naming a value is a promise that the name matters. Every binding asks the reader to remember it, track its scope, and consider whether it will appear again. In a language with good syntax for anonymous operations — lambda-case, record-update wildcards, accessor shorthand, point-free composition — many of these names are unnecessary. They exist not because the author chose them but because the author did not notice they could be omitted. The discipline is not to write the shortest code, but to write code where every name earns its place. When the structure of the expression already tells you what is happening — when position, type, and context are sufficient — let the syntax speak and keep the namespace clean. Omit needless names.


---

## XVI. Miscellany


---

## 80. Use record update syntax, not manual reconstruction

When you need to change one or two fields of a record, use update syntax. Do not rebuild the entire record by hand.

Prefer:

```purescript
state { count = state.count + 1 }
```

Over:

```purescript
{ count: state.count + 1
, name: state.name
, items: state.items
, loading: state.loading
}
```

The update syntax changes only the fields you name and preserves everything else. The manual reconstruction must list every field, and if you add a field to the record type later, the manual version silently fails to compile — or worse, if you are constructing a new record rather than updating, it compiles with the old default. Either way, you are doing bookkeeping the compiler should do for you.

In `do` blocks and Halogen handlers, combine this with the wildcard from entry 76: `H.modify_ _ { loading = true }`. One token for the record, one field updated, nothing else to read.


---

## 81. Do not shadow; the compiler warns for a reason

Shadowing — binding a new value with the same name as an existing binding in scope — is legal PureScript. The compiler warns about it. Heed the warning.

```purescript
-- The second `result` shadows the first.
do
  result <- fetchUser id
  let result = formatUser result  -- Warning: shadowed binding
  log result                      -- Which result? The formatted one.
```

In short functions, shadowing is merely confusing. In long `do` blocks — the kind that appear in Halogen `handleAction` functions — it is a reliable source of bugs. The old binding is still in scope but unreachable by name. A later refactor that reorders lines may silently change which `result` is referenced.

The fix is usually a better name: `formatted`, `userStr`, or whatever describes the new value's role. If you cannot think of a distinct name, that is often a sign the two values should not coexist in the same scope.


---

## 82. Use typed holes to ask the compiler for help

A typed hole — any identifier beginning with `?` — tells the compiler: "I do not know what goes here; tell me what you expect."

```purescript
render state =
  HH.div []
    [ HH.text ?help ]
```

The compiler responds with the expected type (`String`), the bindings in scope, and their types. This is not a workaround for incomplete code — it is a development technique. Use it when you know the shape of the expression but not the exact function name, when you are exploring an unfamiliar API, or when a type error is confusing and you want to see what the compiler actually expects at a specific position.

Typed holes are especially valuable in pipelines. Placing `?here` in the middle of a composition chain tells you exactly what type flows through that point, without reading the signatures of every function in the chain.


---

## 83. Read compiler errors bottom-up

The PureScript compiler reports errors with context at the top and the specific mismatch at the bottom. A typical error reads:

```
  while checking that expression ...
    has type ...
  in value declaration myFunction
  where ...

  Could not match type
    String
  with type
    Int
```

New programmers read top-down, get lost in the framing ("while checking that expression..."), and give up before reaching the payload. The payload is at the bottom: "Could not match type String with type Int." Start there. The context above it tells you *where* the mismatch occurred, which you need only after you understand *what* the mismatch is.

This is the opposite of most programming language error conventions, where the first line is the important one. Adjust your reading order and the errors become significantly more useful.


---

## 84. Understand kind errors

PureScript distinguishes types by their *kind* — the "type of a type." `Int` has kind `Type`. `Maybe` has kind `Type -> Type` (it takes a type and returns a type). `Effect` has kind `Type -> Type`. A row of types has kind `Row Type`.

A kind error means you supplied a type constructor with the wrong number of arguments:

```purescript
-- Kind error: Maybe has kind Type -> Type, but Type was expected.
foo :: Maybe -> String

-- Correct: Maybe is applied to a type.
foo :: Maybe String -> String
```

Read "expected kind `Type`, got kind `Type -> Type`" the same way you would read "expected type `Int`, got type `String`." The fix is the same in spirit: you gave the compiler the wrong thing. Usually you forgot to apply a type constructor to its argument, or applied it to too many.

Kind errors are more common when working with type classes (`class Functor f` requires `f` of kind `Type -> Type`) and when defining instances. If the error mentions `Row Type`, you likely wrote a record type where a row was expected, or vice versa.


---

## 85. Use purs-tidy and do not fight it

`purs-tidy` is the community formatter for PureScript. Run it. Configure your editor to run it on save. Do not manually adjust its output.

Consistent formatting across the ecosystem means you can read anyone's code without adjusting to their whitespace preferences, open a pull request without noise from reformatting, and focus code review on substance rather than style. The specific choices `purs-tidy` makes are less important than the fact that everyone makes the same ones.

If you disagree with a formatting decision, consider whether the disagreement is worth the cost of divergence. It almost never is.


---

## 86. Separate data types from their operations

Define your ADTs and records in a `Types` module. Define operations in sibling modules that import `Types`.

```
src/
  MyApp/Types.purs       -- data types, newtypes, type aliases
  MyApp/Render.purs      -- imports Types, defines rendering functions
  MyApp/Validation.purs  -- imports Types, defines validation functions
```

This avoids circular dependencies — the most common module-structure headache in PureScript. `Render` and `Validation` can both depend on `Types` without depending on each other. If `Render` needs a validation helper, you can factor it out into a shared module that depends only on `Types`, rather than creating a cycle.

Type definitions change less often than the functions that operate on them. Separating them means that adding a new rendering function does not trigger recompilation of validation code, and vice versa. The initial overhead — one extra module, one extra import — is trivial. The structural benefit compounds as the codebase grows.


---

## 87. Avoid stringly-typed Symbol proxies when an ADT exists

Type-level strings (`Proxy @"foo"`, `SProxy "bar"`) are the foundation of PureScript's row polymorphism and generic programming. They are the right tool when you are writing generic code that operates over arbitrary record fields or variant labels.

They are the wrong tool when you are using them as runtime-level tags or enum-like values:

```purescript
-- The Symbol buys you nothing here. It is a String with more steps.
handleEvent :: forall s. IsSymbol s => Proxy s -> Event -> Effect Unit

-- An ADT gives you exhaustiveness checking.
data EventKind = Click | Hover | Focus

handleEvent :: EventKind -> Event -> Effect Unit
```

The ADT version is checked for exhaustiveness. The `Symbol` version is checked for... existence. If you typo `"clck"`, the compiler will happily create a new symbol and proceed. The error surfaces at runtime, or not at all.

Use `Symbol` for generic programming. Use ADTs for domain modeling.


---

## 88. Monomorphise hot paths

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


---

## 89. Use intercalate, not manual separator logic

Building a delimited string by folding with a conditional separator is a recurring source of off-by-one errors: an extra comma at the end, a missing comma at the start, special-casing the first or last element.

Prefer:

```purescript
intercalate ", " ["alpha", "beta", "gamma"]
-- "alpha, beta, gamma"
```

Over:

```purescript
foldlWithIndex
  (\i acc s -> if i == 0 then s else acc <> ", " <> s)
  ""
  ["alpha", "beta", "gamma"]
```

`intercalate` from `Data.Foldable` (for strings) or `Data.Array` (for arrays) handles the separator logic correctly and communicates intent in a single word. The fold version is four lines of control flow to achieve what a standard library function already does. This generalises: before writing separator logic, check whether `intercalate` or `joinWith` already exists for your type.


---

## 90. Prefer Maybe over Boolean + separate value

When a value is meaningful only when some condition holds, represent it as `Maybe` — not as a `Boolean` flag with a separate field.

Prefer:

```purescript
type Selection = Maybe SelectionInfo
```

Over:

```purescript
type State =
  { hasSelection :: Boolean
  , selection :: Maybe SelectionInfo
  }
```

The second version introduces an impossible state: `hasSelection` is `true` but `selection` is `Nothing`, or vice versa. Every function that touches this state must maintain the invariant that the two fields agree. `Maybe` encodes the invariant directly: `Just` means present, `Nothing` means absent. One field, no coordination, no impossible states.

This is a specific instance of the general principle from entry 55: if two fields must vary in lockstep, they are one field in disguise.


---

## 91. Distinguish configuration from state

Values that are set once at startup and never change — API base URLs, feature flags, locale, authentication tokens — belong in a `Reader` environment, not in mutable state.

```purescript
-- Configuration: read-only, set at startup.
type Env = { apiBase :: String, locale :: String, features :: Features }

newtype AppM a = AppM (ReaderT Env Aff a)

-- Not this: mutable state that happens to never mutate.
type AppState = { apiBase :: String, locale :: String, ... , count :: Int }
```

Putting configuration in `State` invites accidental modification — a `modify_` that changes `apiBase` compiles without complaint. It also complicates reasoning: when debugging unexpected behaviour, you must verify that the "configuration" fields have not been mutated, which should not be a question you need to ask.

`ReaderT` makes the guarantee structural. The environment is available everywhere via `ask` and `asks`, but no function can modify it. The distinction between "things that change" and "things that are fixed" is visible in the types.


---

## 92. Use newtypes for monad transformer stacks

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

## 93. Understand the PureScript String

PureScript's `String` is a JavaScript string. It is UTF-16 encoded, not a linked list of characters (Haskell's `String`), not a byte array (Rust's `&str`), and not a sequence of Unicode code points (Python 3's `str`).

This matters when you process text character by character. PureScript provides two modules:

- `Data.String.CodeUnits` operates on UTF-16 code units. A code unit is 16 bits. Characters outside the Basic Multilingual Plane — emoji, many CJK characters, mathematical symbols — occupy *two* code units (a surrogate pair).
- `Data.String.CodePoints` operates on Unicode code points. Each code point is one logical character, regardless of its UTF-16 encoding.

```purescript
import Data.String.CodeUnits as CU
import Data.String.CodePoints as CP

CU.length "hello" -- 5
CP.length "hello" -- 5

CU.length "\x1F600" -- 2 (surrogate pair)
CP.length "\x1F600" -- 1 (one code point)
```

If you use `CodeUnits.take 1` on a string that starts with an emoji, you get half a surrogate pair — a meaningless fragment. Use `CodePoints` when correctness over the full Unicode range matters. Use `CodeUnits` when you are interoperating with JavaScript APIs that expect UTF-16 indices (such as DOM selection ranges).

Know which module you are importing. The functions have the same names.


---

## 94. Use Data.String.Pattern, not raw strings, for search targets

When calling string functions that take a search term, use the `Pattern` newtype to mark the role of the argument.

Prefer:

```purescript
contains (Pattern "needle") haystack
replaceAll (Pattern "old") (Replacement "new") source
```

Over:

```purescript
-- If this compiled without newtypes, which argument is the needle?
contains "needle" haystack
```

The `Pattern` and `Replacement` newtypes exist precisely to prevent argument transposition. Without them, `contains haystack "needle"` would also type-check (both are `String`), and the bug would surface only at runtime — or not at all, if the test happened to pass by coincidence.

This is entry 5 (Newtype what you mean) applied to the standard library. The library authors already made the decision for you. Use the types they provided.
