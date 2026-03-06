# The Elements of PureScript Style — Entry Ideas

100 candidate entries beyond the 8 already drafted. Grouped by theme, not final chapter order. Each has a working title and a one-line pitch. Marked with origin where relevant: **[JS]** = traps from JavaScript/TypeScript, **[HS]** = traps from Haskell, **[task]** = task-specific, **[lib]** = library/ecosystem, **[style]** = general FP style, **[tooling]** = spago/build/deploy.

### Unmined sources

- PureScript Discord (can't be fetched — paste threads in for distillation)
- PureScript Discourse (public, web-fetchable)
- GitHub issues on purescript/purescript, purescript-contrib, spago (especially "question" labels)
- Real World Halogen (Thomas Honeyman)
- Jordan's Reference (design patterns sections)
- purs-tidy source (formatting decisions encode style opinions)
- Compiler suggestion messages (purs itself recommends alternatives in warnings)
- purescript-cookbook examples
- Strudel/Tidal community (FP newcomers, different background than web devs)


## Already drafted (for reference)

1. Make the compiler's knowledge your own (exhaustive matching over sum types)
2. Do not reach for a default you do not need (fromMaybe reflex)
3. Traverse; do not map and sequence
4. Discard results deliberately (traverse_ over void$traverse)
5. Newtype what you mean (newtype over type alias)
6. Let the compiler write the instances (derive, derive newtype)
7. Impose structure before you impose convention (ADTs over strings/booleans)
8. PureScript is strict; do not import lazy habits

De Gustibus: where/let, point-free/pointed


---

## I. The Effect Boundary — what runs, when, and why

**9. An Effect is a recipe, not an action** [JS]
In JavaScript, calling a function that does IO *does* the IO. In PureScript, `Effect` and `Aff` are values that *describe* work. They do nothing until composed into `main`. This is the single biggest mental-model shift for imperative programmers, and most other rules flow from it.

**10. Use Aff for async, not callbacks** [JS]
`makeAff` wraps callback-based JavaScript. Once wrapped, use `do`-notation, not `.then`-chains or nested callbacks. The whole point of `Aff` is to flatten callback pyramids into sequential-looking code.

**11. Attach a Canceler to every makeAff** [JS/task]
Every `makeAff` must return a `Canceler`. Forgetting this means fibers cannot be cleanly killed, leaking event listeners, timers, or network connections. Even if cancellation is a no-op, return `nonCanceler` explicitly.

**12. Use parallel/sequential for concurrent Aff** [task]
`parTraverse` and applicative combinators over `ParAff` express concurrency declaratively. Reserve `forkAff`/`joinFiber` for long-running background work, not request batching.

**13. Use ado notation for independent computations** [style]
When a result depends on multiple values with no data dependency between them, `ado` lets the compiler use `Apply` instead of `Bind`. In `Aff`, this enables parallelism. Everywhere else, it documents independence.


## II. The FFI Boundary — PureScript meets JavaScript

**14. Keep FFI files minimal; put logic in PureScript** [JS]
Foreign modules should be one-line wrappers. Move all branching, error handling, and data transformation into PureScript where the type checker can see it.

**15. Use EffectFn/Fn for uncurried FFI** [JS]
`Effect.Uncurried` and `Data.Function.Uncurried` let you type JavaScript's calling convention directly, avoiding manual currying wrappers and improving performance for callbacks.

**16. Sanitize all data crossing the FFI boundary** [JS]
JavaScript can return `null`, `undefined`, or values of the wrong shape. Use `Nullable`, `Foreign`, or codec-based decoders. Never give a raw FFI return a bare PureScript type.

**17. Never use unsafeCoerce as a substitute for proper types** [JS]
JavaScript's `any` and TypeScript's `as` have no place here. If you reach for `Unsafe.Coerce.unsafeCoerce`, you almost certainly need a newtype, a type class, or a `Foreign` decoder.


## III. Coming from Haskell — things that aren't the same

**18. Ensure stack safety with tailRecM** [HS]
In a strict language, monadic recursion (`forever`, deeply recursive `>>=` chains) is not automatically stack-safe. Use `MonadRec` / `tailRecM` or rewrite with a loop combinator.

**19. Mutual recursion defeats TCO** [HS]
The compiler only performs tail-call optimisation on self-recursive functions. Fuse mutually recursive functions into a single function with a tag argument if you need stack safety.

**20. Write explicit forall** [HS]
PureScript requires `forall` to introduce every type variable. There is no implicit universal quantification. If you see a "not defined" error for a type variable, you forgot the `forall`.

**21. Use <<< for composition, not .** [HS]
The dot is for record access and module qualification. Right-to-left composition is `<<<`; left-to-right is `>>>`.

**22. Number literals are not overloaded** [HS]
`1` is always `Int`, `1.0` is always `Number`. There is no `Num` class or `fromInteger`. Use `toNumber` for explicit conversion.

**23. Orphan instances are a compiler error** [HS]
The instance must live in the module that defines the class or the type. Plan module structure accordingly, or use newtype wrappers.

**24. There are no default method implementations** [HS]
Every method in every instance must be written. Factor shared logic into helper functions instead.

**25. Use Array as your default sequential collection** [HS]
PureScript's `Array` is a JavaScript array with O(1) index access. `List` has worse constant factors in a strict language. Prefer `Array` unless you need a cons-based structure for pattern matching or incremental construction.

**26. Operator sections use _, not partial application syntax** [HS]
Write `(_ + 2)` and `(2 + _)`, not `(+ 2)`. The underscore placeholder is PureScript's uniform section syntax.


## IV. Containers, Foldable, and Traversable — write it once

**27. Generalise with Foldable/Traversable constraints** [lib]
Writing `sum :: Array Int -> Int` when `sum :: forall f. Foldable f => f Int -> Int` works equally well locks callers into `Array` for no benefit. Generalise at module boundaries; specialise internally if performance requires it.

**28. Use foldMap instead of map followed by fold** [style]
`foldMap f` is one pass. `fold <<< map f` is two. The single-pass version is both clearer and, depending on the container, more efficient.

**29. Require NonEmpty when emptiness is impossible** [task]
If a function logically requires at least one element — `fold1`, choosing from alternatives, rendering a comma-separated list — encode that in the type. `NonEmptyArray` and `NonEmptyList` move the proof from a runtime check to the call site.

**30. Use Data.Map and Data.Set, not hand-rolled lookups** [lib]
Do not reinvent association-list searches or manually deduplicate arrays. `ordered-collections` provides balanced-tree `Map` and `Set` with proper asymptotics.

**31. Give instances for containers you define** [lib]
If you write a new data structure that holds values, give it `Functor`, `Foldable`, and `Traversable` instances (derive them if possible). Without these, every consumer must destructure manually, and your type cannot participate in generic algorithms.

**32. Use coerce for zero-cost newtype conversions** [lib]
Mapping `unwrap` or `un Foo >>> Bar` over a container is O(n). `coerce` from `Safe.Coerce` does the same in O(1) because newtypes have identical runtime representations.


## V. Error Handling — say what went wrong

**33. Model domain errors as ADTs, not strings** [task]
`throwError "invalid input"` discards structure. Define `data AppError = InvalidInput Field | Unauthorized | ...` and pattern match on the result. The caller can decide how to display the message; the thrower should decide what the error *is*.

**34. Use V (Validation) to accumulate errors, Either to short-circuit** [task]
`Either`'s `Apply` stops at the first `Left`. If you want to collect all validation failures — missing form fields, multiple schema violations — use `V` from `purescript-validation` with a `Semigroup` error type.

**35. Use ExceptT for expected failures, Aff's error for unexpected ones** [task]
Aff's built-in error mechanism is for truly exceptional failures (network down, file not found). For expected, recoverable domain errors, layer `ExceptT` on top to keep error handling in the types.

**36. Do not catch exceptions you cannot handle** [style]
`try` converts an exception into an `Either`, but if you then call `unsafePartial $ fromRight` or re-throw with a different message, you have obscured the failure without improving recoverability.


## VI. Parsing, Codecs, and Serialisation — structured I/O

**37. Use purescript-parsing for structured parsing, not regex** [task]
Regular expressions are stringly-typed and compose poorly. `purescript-parsing` gives you typed, composable parser combinators with proper error positions. Regex is fine for quick validation; parsing is for structure.

**38. Use codec for JSON, not hand-written decoders** [task]
`purescript-codec-argonaut` gives you bidirectional codecs that guarantee encode/decode roundtripping by construction. Hand-written `DecodeJson`/`EncodeJson` instances can silently disagree.

**39. Decode at the boundary, work with types internally** [task]
Parse JSON into your domain types at the outermost layer. Internally, pass typed records and ADTs, not `Json` or `Foreign` values. If a function deep in your stack takes `Json`, the boundary is in the wrong place.


## VII. Halogen — components and state

**40. Prefer render functions over components** [lib]
A shared header, footer, or widget with no independent state should be a plain `forall w i. HH.HTML w i` value or a function returning one — not a stateful component with empty `State` and `Action`.

**41. Store minimal canonical state; derive the rest in render** [lib]
Compute view-only data in `render`, do not cache it in `State`. Derived state goes stale; source-of-truth state does not.

**42. Model component actions as what happened, not what to do** [lib]
Name actions after user events (`Clicked`, `InputChanged`, `TimerFired`), not after their effects (`UpdateState`, `FetchData`). The handler decides what to do; the action records what occurred.


## VIII. Type Classes — use the hierarchy

**43. Use when and unless, not if-then-pure-unit** [style]
`when condition (log "done")` is clearer than `if condition then log "done" else pure unit`. The library offers the intent-matching variant; use it.

**44. Use guard and Alternative for conditional failure** [style]
Rather than nesting `if` expressions that return `Nothing` or `Left`, use `guard condition` in a `do` block with an `Alternative` constraint.

**45. Understand Apply vs Bind and choose deliberately** [style]
`Apply` combines independent computations. `Bind` sequences dependent ones. If nothing in line 3 depends on the result of line 2, you are using `Bind` where `Apply` (or `ado`) would be more honest — and in `Aff`, more concurrent.

**46. Use Data.Newtype.un / over / over2, not manual unwrap/rewrap** [lib]
The `Newtype` class provides generic accessors that work with any newtype without importing its constructor. `over Score (_ + 1)` is one expression; unwrapping, modifying, and rewrapping is three.


## IX. Module Hygiene — say what you mean, export what you intend

**47. Use explicit export lists** [style]
A module without an export list exports everything, including internal helpers and partially-applied constructors. List your public API explicitly. Use `module Foo.Internal (everything)` for shared internals.

**48. Use explicit imports or qualified imports for everything except Prelude** [style]
`import Data.Array` without listing what you need makes it impossible to tell where a name comes from when reading the code. Either `import Data.Array (head, tail)` or `import Data.Array as Array`.

**49. Always write type signatures on top-level declarations** [style]
The compiler warns when you don't. Type signatures are documentation, catch errors early, and prevent unintended generalisation or specialisation.

**50. Compile with no warnings** [style]
Treat warnings as errors. The PureScript compiler's warnings — unused imports, missing signatures, shadowed names — are precise and actionable. A clean build is a form of documentation.


## X. Records, Rows, and Data Modelling

**51. Use records with named fields when three or more arguments have the same type** [style]
`createUser "Alice" "alice@x.com" "admin"` is a bug waiting to happen. `createUser { name: "Alice", email: "alice@x.com", role: "admin" }` is self-documenting — and even better with newtyped fields.

**52. Use row polymorphism instead of concrete record types in library APIs** [style]
`renderWidget :: forall r. { label :: String, onClick :: Effect Unit | r } -> HTML` accepts any record with at least those fields. Requiring a specific closed record forces callers to construct throwaway values for fields they do not use.

**53. Prefer case expressions over equational pattern matching** [style]
Multiple equations with different patterns (`f 0 = ... ; f n = ...`) are harder to refactor than a single `f = case _ of`. Adding a parameter to the equational form means rewriting every clause.


## XI. Testing and Verification

**54. Write property-based tests, not just examples** [task]
PureScript's `Arbitrary` and `Coarbitrary` classes make property-based testing natural. Test codec roundtrips, monoid laws, idempotency, commutativity. An example test says "this works"; a property test says "this always works."

**55. Use the type system to make illegal states unrepresentable** [style]
If a `User` can be `LoggedIn` (with a session token) or `Anonymous` (without), do not model this as `{ loggedIn :: Boolean, token :: Maybe Token }`. Model it as `data User = LoggedIn Token | Anonymous`. The Boolean-and-Maybe version permits `{ loggedIn: true, token: Nothing }` — a state that should not exist.

**56. Smart constructors: export the type, not the constructor** [style]
When a value must satisfy an invariant (a positive integer, a non-empty string, a normalised email), export a smart constructor that validates and returns `Maybe MyType`. Do not export the data constructor. The type system then guarantees that every value of `MyType` satisfies the invariant.


## XII. Performance and Pragmatism

**57. Use STRef with ST.run for locally-scoped mutation** [task]
When you need mutation for performance — an in-place sort, building a mutable array — `ST` gives you a pure interface. The rank-2 type guarantees the mutable reference cannot escape.

**58. Prefer Ref only at application boundaries** [JS]
Reaching for `Effect.Ref` everywhere is translating imperative habits. Use `State`, `StateT`, or immutable record updates for most things. Reserve `Ref` for shared mutable state between event handlers or components.


## XIII. Power Tools — when to wield, when to sheathe

**59. You do not need GADTs; here is what you do instead** [HS]
PureScript has no GADTs. Haskell programmers feel this keenly and reach for complex encodings. In most cases the problem has a simpler PureScript solution: existential newtypes (CPS-encoded, as in HATS `SomeFold`), type classes with functional dependencies, or simply a sum type with a phantom parameter. The entry should show three concrete "I wanted a GADT for X" scenarios and the idiomatic PureScript alternative for each.

**60. Variant and heterogeneous records: reach for them last, not first** [style]
`purescript-variant` and `purescript-heterogeneous` are powerful, specialized tools. Programmers arriving from untyped languages — enamored by FP but unbothered by complexity — often reach for them immediately, producing code that is harder to read, harder to maintain, and slower to compile than a plain ADT or record would be. Use `Variant` when you need extensible, open sum types across module boundaries. Use heterogeneous records when row-level computation is genuinely required. For closed, known alternatives — which is most of the time — a sum type is simpler, faster, and the compiler gives you exhaustiveness checking for free.

**61. Do not encode at the type level what works at the value level** [style]
Type-level programming in PureScript (Symbol, RowList, type-class-level computation) is powerful but has real costs: longer compile times, worse error messages, and code that fewer people can read. If the problem can be solved with a plain function over a sum type, do that. Reserve type-level machinery for cases where the guarantee must hold at compile time and cannot be expressed any other way.

**62. Understand what purescript-run gives you before using it** [lib]
`Run` (extensible effects via free monads over variant rows) is an alternative to monad transformer stacks. It is elegant for large applications with many interchangeable effect interpreters. For a Halogen app with two or three effects, `ReaderT` over `Aff` is simpler, faster, and better understood by the community. Match the abstraction to the problem.

**63. Existentials: use the CPS encoding, not unsafeCoerce** [style]
PureScript has no native existential types. The standard encoding is a newtype wrapping a rank-2 continuation: `newtype SomeFold = SomeFold (forall r. (forall a. FoldSpec a -> r) -> r)`. This is safe, composable, and well-understood. Do not simulate existentials with `unsafeCoerce` or `Foreign`.


## XIV. Spago, the Registry, and the Build — getting your project to compile

**64. Understand the package set vs the solver** [tooling]
Spago can resolve dependencies from a fixed *package set* (a known-good snapshot of the registry at a point in time) or via the *solver* (which resolves version ranges like npm/cargo). Package sets give reproducibility; the solver gives flexibility. Most projects should start with a package set and only use the solver when they need packages or versions not in the set. Mixing the two without understanding which is active is the most common source of "package not found" errors.

**65. Use workspace.extraPackages for local and unpublished dependencies** [tooling]
When you depend on a local checkout, a git repo, or an unpublished package, add it under `workspace.extraPackages` in your `spago.yaml` — not by hacking the package set or symlinking into `.spago`. The `path:` form is for local directories; the `git:` form is for remote repos with a specific ref.

**66. Keep spago.yaml minimal and let the lock file do its job** [tooling]
`spago.yaml` declares your intent (which packages, which version ranges). `spago.lock` records what was actually resolved. Check in the lock file. Do not pin exact versions in `spago.yaml` unless you have a specific reason — that is the lock file's job.

**67. One workspace, many packages** [tooling]
Spago supports monorepos: a root `spago.yaml` with `workspace:` and sub-directories each with their own `package:` stanza. This is how `purescript-hylograph-libs` manages 15+ packages. Do not create separate repos (with separate package sets, separate lock files, separate CI) for packages that evolve together.

**68. spago bundle vs spago build: know the difference** [tooling]
`spago build` compiles PureScript to ES modules in `output/`. `spago bundle` additionally runs esbuild to produce a single JS file for browsers or Node. If your HTML loads `bundle.js`, you need `spago bundle`. If you are writing a library or a Node app that can use ES module imports, `spago build` is sufficient. Getting this wrong produces either "module not found" in the browser or an unnecessarily large bundle in Node.

**69. Browser bundles need platform: browser** [tooling]
When bundling for the browser, your `spago.yaml` bundle config must include `platform: browser`. Without it, esbuild may leave in Node-specific imports (`fs`, `path`, `process`) that fail at runtime. The error is often cryptic — a reference error for `process` or `require` — and the fix is one line in the config.

**70. Set bundle.module to your entry point** [tooling]
`spago bundle` needs to know which module contains `main`. Set `bundle.module: Main` (or whatever your entry module is) in `spago.yaml`. If omitted, the bundler may produce an empty or incorrect output without a clear error.

**71. Do not import from output/ in your source** [tooling]
The `output/` directory is a build artifact. Importing from it (`import { foo } from "../output/Module.Name/index.js"`) creates a circular dependency between the build system and your source. Use PureScript imports and let spago/the bundler resolve the paths.

**72. Clear output/ when things make no sense** [tooling]
Incremental compilation occasionally produces stale artifacts, especially after renaming modules, changing the package set, or switching git branches. If you get inexplicable errors (duplicate module, wrong type, module not found), `rm -rf output .spago` and rebuild. It costs 30 seconds and saves 30 minutes.

**73. The registry version must match what the solver sees** [tooling]
If you specify `registry: 63.2.0` in your workspace packageSet, only packages published at or before that registry version are visible. A package that exists on Pursuit but was published after your registry snapshot will not resolve. Either bump the registry version or add the package to `extraPackages`.

**74. Use spago ls packages and spago ls deps to debug resolution** [tooling]
When a package is "not found," `spago ls packages` shows what the current package set contains. `spago ls deps` shows your resolved dependency tree. These two commands answer most "why can't spago find X" questions faster than reading the spago source.


## XV. Omit Needless Names — PureScript's own "omit needless words"

This is a *principle* that unifies several individual rules. PureScript offers syntactic tools that let you avoid naming intermediate values. Each unnecessary name is a small tax on the reader: they must track what it refers to, whether it is used again, and whether its name is meaningful or merely structural. When the value is used once, immediately, and its role is obvious from position, the name is noise.

**75. Use case _ of, not a named parameter you immediately case on** [style]
```purescript
-- The parameter name adds nothing.
colorFor status = case status of ...

-- The underscore says: this function is defined by cases.
colorFor = case _ of ...
```
`case _ of` is a lambda with pattern matching. It signals "the entire function is a dispatch on one argument." The named version says the same thing in more words.

**76. Use _ for record updates in modify** [style]
```purescript
-- Three tokens to say "the state":
H.modify_ \s -> s { loading = true }

-- One token:
H.modify_ _ { loading = true }
```
The record-update wildcard `_` exists precisely for this. The `\s -> s { ... }` form suggests something more complex is happening; the wildcard says "update a field, that's all."

**77. Use _.field for record access in map** [style]
```purescript
map (\item -> item.name) items
map _.name items
```
The accessor shorthand `_.name` is a function from any record with a `name` field to that field's value. When the lambda body is a single field access, the shorthand is strictly clearer.

**78. Do not name a value you immediately pass to one function** [style]
```purescript
-- The binding exists only to be consumed on the next line.
do
  result <- fetchUser id
  let name = result.name
  log name

-- Pass directly.
do
  result <- fetchUser id
  log result.name
```
A `let` binding is documentation: "this value has a role worth naming." If the value is consumed immediately and never referenced again, the name is overhead. (This does not apply when the name genuinely clarifies intent — `let cutoff = 0.5` is fine even if used once.)

**79. The principle, stated** [style]
Naming a value is a promise that the name matters. PureScript's syntax — lambda-case (`case _ of`), record update wildcards, accessor shorthand, point-free composition — lets you write code where the structure speaks. When you reach for a name, ask: does this name tell the reader something they cannot see from position alone? If not, let the syntax carry the meaning.

**80. Use record update syntax, not manual reconstruction** [style]
`state { count = state.count + 1 }` is clearer and safer than `{ count: state.count + 1, name: state.name, items: state.items }`. The update syntax changes only the fields you name; manual reconstruction silently drops fields you forget.
In `do` blocks and handlers, `H.modify_ _ { loading = true }` is idiomatic. The underscore is the record being updated. This is PureScript-specific syntax that newcomers often miss, writing `\s -> s { loading = true }` instead.

**81. Do not shadow; the compiler warns for a reason** [style]
Shadowing a binding with a `let` or `case` is legal but the compiler warns. Heed it. Shadowed names are a rich source of bugs, especially in long `do` blocks where the old binding is still in scope but no longer reachable.

**82. Use typed holes to ask the compiler for help** [style]
Writing `?help` in place of an expression makes the compiler report what type is expected and what bindings are in scope. This is not a workaround — it is a development technique. Use it when you know the shape of the code but not the exact function name.

**83. Read compiler errors bottom-up** [style]
The PureScript compiler reports the most specific error last. The top of a long error message is context ("while checking…", "in the expression…"); the bottom is the actual mismatch. New programmers read top-down and get lost in the framing.

**84. Understand kind errors** [HS/style]
PureScript distinguishes `Type`, `Type -> Type`, `Row Type`, and other kinds. A kind error means you gave a type constructor the wrong number of arguments — `Maybe` where `Maybe Int` was expected, or `Effect` where `Effect Unit` was needed. Read "expected kind X, got kind Y" the same way you read "expected type X, got type Y."

**85. Use purs-tidy and do not fight it** [tooling]
`purs-tidy` is the community formatter. Use it. Do not configure around it or manually reformat its output. Consistent formatting across the ecosystem means you can read anyone's code without adjusting to their whitespace preferences.

**86. Separate data types from their operations** [style]
Define your ADTs and records in a `Types` module. Define operations in sibling modules that import `Types`. This avoids circular dependencies and keeps type definitions — which change less often — stable while operations evolve.

**87. Avoid stringly-typed Symbol proxies when an ADT exists** [style]
Type-level strings (`SProxy`, `Proxy @"foo"`) are powerful for row polymorphism and generic programming, but using them as runtime-level tags or enum-like values bypasses the exhaustiveness checking that ADTs provide.

**88. Monomorphise hot paths** [style]
Polymorphic code goes through type class dictionaries at runtime. In tight loops or performance-critical sections, use type annotations or module-internal monomorphic helpers to eliminate the dictionary overhead. Profile first.

**89. Use intercalate, not manual separator logic** [style]
Building a comma-separated string with `foldl` and a conditional separator is a bug waiting to happen (off-by-one on the first or last element). `intercalate ", " items` does it correctly.

**90. Prefer Maybe over Boolean + separate value** [style]
`{ enabled :: Boolean, value :: Maybe Int }` where `value` is `Nothing` when `enabled` is `false` is the Boolean-and-Maybe anti-pattern from entry 55. Use `Maybe Int` alone — `Just` means enabled, `Nothing` means disabled. One field, no impossible states.

**91. Distinguish configuration from state** [style]
Values that are set once at startup and never change (API URL, feature flags, locale) belong in a `Reader` environment, not in mutable state. Putting configuration in `State` invites accidental modification and complicates reasoning about what can change.

**92. Use newtypes for monad transformer stacks** [style]
Defining `type App = ReaderT Config (ExceptT Error Aff)` as a type alias means every function that uses it must repeat the full stack in its signature. A newtype (`newtype AppM a = AppM (ReaderT ...)`) lets you derive the instances once and write `AppM` everywhere.

**93. Understand the Purescript String** [HS/JS]
PureScript's `String` is a JavaScript string — UTF-16 encoded, not a list of characters, not Haskell's `Text`. `Data.String.CodeUnits` operates on UTF-16 code units; `Data.String.CodePoints` operates on Unicode code points. If you process user text with code-unit functions, you will mangle emoji and CJK characters. Know which module you need.

**94. Use Data.String.Pattern, not raw strings, for search targets** [style]
`contains (Pattern "needle") haystack` is self-documenting. `contains "needle" haystack` (if it compiled) would not distinguish the search term from any other string argument. The `Pattern` newtype exists precisely for this — to mark the role of the argument.


## XVI. Thinking in Types — design before you code

**95. Design the types first, write the functions second** [style]
Before writing any logic, define the data types. If the types are right, the functions are often obvious — sometimes there is only one well-typed implementation. If the types are wrong, no amount of clever logic will save you.

**96. Sum types for "or", product types for "and"** [style]
"A value is either X or Y" → sum type. "A value has both X and Y" → record. This sounds trivial but programmers from OO backgrounds systematically reach for inheritance hierarchies where a sum type is the correct model.

**97. Phantom types: tag without data** [style]
`newtype Id (a :: Type) = Id String` lets you distinguish `Id User` from `Id Order` without storing the `User` or `Order`. The phantom parameter exists only in the type; at runtime, both are `String`. Useful for preventing ID mixups across entity types.

**98. Use the strength of Maybe** [JS]
JavaScript programmers often check `if (x !== null)` and proceed. In PureScript, `Maybe` is a functor, a monad, an alternative. `map`, `bind`, `fromMaybe`, `maybe`, `<|>`, `traverse` — use the structure. Pattern matching on `Just`/`Nothing` in every function is the equivalent of null-checking: correct but missing the point.

**99. Alt and Alternative: first success wins** [style]
`<|>` tries the left side; if it fails, tries the right. This works for `Maybe`, parsers, arrays, and any `Alt` instance. Use it to express fallback chains: `lookupCache key <|> lookupDB key <|> pure defaultValue`.

**100. Applicative for building, Monad for deciding** [style]
If every field of a record can be computed independently, use applicative style or `ado`. If computing field B requires knowing the value of field A, you need `Bind`. The distinction is not merely stylistic — `Validation` has an `Applicative` but no `Monad`, precisely because it needs to evaluate all fields to collect all errors.

**101. Do not use show for serialisation** [style]
`Show` is for debugging. Its output is not stable, not specified, and not guaranteed to be parseable. If you need to serialise a value, write a codec. If you need a human-readable label, write a `display` function. `Show` instances should never appear in production output.

**102. Optics: a lens is a getter and a setter that agree** [lib]
If you find yourself writing `getField` and `setField` pairs, you have half a lens. The `profunctor-lenses` library gives you composable access paths into nested structures. Start with `_Just`, `_Left`, and record lenses; do not start with prisms and isos.

**103. Use Tuple only for ephemeral pairs** [style]
`Tuple String Int` tells the reader nothing about which string or which int. For anything that persists beyond a single `map` or `foldl`, use a record: `{ name :: String, count :: Int }`. Tuples are for intermediate pipeline steps; records are for data with identity.

**104. Write the simplest code that the types permit** [style]
If the compiler accepts it and the meaning is clear, the code is good enough. Do not add type-level machinery to enforce an invariant the code already maintains. Do not abstract over a pattern that occurs once. Do not reach for a monad transformer when a function argument will do. Simplicity is not a concession — it is the goal.


## XVII. Common Pitfalls by Task

**105. Generating random values: use MonadGen or Effect.Random, not unsafePerformEffect** [task]
Random number generation is an effect. Wrapping it in `unsafePerformEffect` to get a "pure" random value is not pure — it is a lie. Use `Effect.Random` for one-off values, `MonadGen` for QuickCheck-style generators, and pass seeds explicitly for reproducible randomness.

**106. CLI argument parsing: use optparse, not hand-rolled case matching on argv** [task]
`purescript-optparse` gives you typed argument parsing with help text, subcommands, and validation. Manually indexing into `process.argv` produces code that is fragile, undocumented, and silently wrong when arguments are reordered.

**107. Date and time: use the types, not epoch integers** [task]
Passing `Int` or `Number` for timestamps invites arithmetic errors (milliseconds vs seconds, timezone-unaware subtraction). Use `DateTime`, `Instant`, or `Duration` from the date/time libraries. The types prevent you from adding a date to a duration in the wrong units.

**108. Regular expressions: compile once, use many** [task]
`Regex.regex` returns `Either` because the pattern might be invalid. Do not call it inside a loop or a `map`. Compile the regex once at the top level or in a `where` clause, handle the `Left`, and reuse the compiled `Regex` value.

**109. HTTP requests: decode the response, do not assume its shape** [task]
An HTTP response body is `String` (or `ArrayBuffer`). It is not your domain type yet. Decode it with a codec or parser and handle the failure case. The server will eventually change its response format; your decoder is the firewall.

**110. File I/O in Node: use the Aff wrappers, not raw FFI** [task]
`purescript-node-fs-aff` wraps Node's `fs` module with `Aff`-based functions. Using the callback-based FFI directly means managing callbacks, errors, and cancellation by hand — all things `Aff` already does.

**111. Logging: use structured logging, not string concatenation** [task]
`log ("User " <> show userId <> " logged in at " <> show timestamp)` is ungreppable and untypeable. Use a logging library that accepts structured data, or at minimum, define a `LogEntry` record and a single function that formats it.

**112. Environment variables: read at startup, not on demand** [task]
Do not sprinkle `lookupEnv` throughout your codebase. Read all environment variables in `main`, validate them, construct a `Config` record, and pass it through `ReaderT`. This makes the configuration surface explicit, testable, and mockable.


## XVIII. Habits of Good Code — from the Haskell style guides, adapted

**113. Order imports: Prelude, then libraries, then local modules** [style]
Three groups separated by blank lines, alphabetical within each. The reader can tell at a glance what comes from the ecosystem and what is project-local.

**114. Qualify container imports** [style]
`import Data.Map as Map` and `Map.lookup` at call sites. This avoids name clashes (`lookup`, `insert`, `empty` appear in many modules) and makes the container type visible at the point of use.

**115. Document every export with a doc comment** [style]
`-- |` comments appear in Pursuit and in IDE hover. Every exported function and type should have one. If a function is not worth documenting, it is not worth exporting.

**116. Documentation describes what, not how** [style]
"Returns the first element, or Nothing if empty" — not "Pattern matches on the array, checks if the length is zero, then..." If you need to explain the mechanism, the function is doing too much.

**117. Use mixed case for abbreviations: HttpServer, not HTTPServer** [style]
The exception is two-letter abbreviations (`IO`). Beyond two letters, camelCase reads better and avoids the awkward `HTTPSConnection` problem (where does `HTTPS` end and `Connection` begin?).

**118. Use singular module names** [style]
`Data.Map`, not `Data.Maps`. `MyApp.Route`, not `MyApp.Routes`. The module represents the concept, not a collection of its instances.

**119. Do not mix let and where in the same definition** [style]
Scattering bindings between `let` (above) and `where` (below) the main expression forces the reader to look in two places. Pick one per definition.

**120. Prefer guards over if-then-else** [style]
Guards align the conditions vertically and make the structure obvious. `if-then-else` nests and obscures. Use `if` only for inline binary choices where a guard would be heavier than the expression it guards.

```purescript
-- Guards: the conditions scan vertically.
classify score
  | score >= 90 = Excellent
  | score >= 70 = Good
  | otherwise   = NeedsWork

-- if-then-else: nests and obscures.
classify score =
  if score >= 90 then Excellent
  else if score >= 70 then Good
  else NeedsWork
```

**121. End every guard chain with otherwise** [style]
An unguarded case with no `otherwise` is a partial function hiding in plain sight. The compiler may not catch it. `otherwise` makes exhaustiveness explicit.

**122. Replace do { x <- m; pure (f x) } with map f m** [style]
A `do` block that binds once and immediately wraps the result in `pure` is a `Functor` operation written in `Monad` clothing. `f <$> m` is shorter, works with `Apply` (not just `Monad`), and documents that the computation is a simple transformation.

```purescript
-- Monadic dress for a functorial body.
do
  response <- fetchUser id
  pure response.name

-- What it actually is.
_.name <$> fetchUser id
```

**123. Avoid explicit recursion; use higher-order functions** [style]
Most recursive patterns are already captured by `map`, `filter`, `foldl`, `foldr`, `traverse`, `unfold`. Explicit recursion is harder to read and — in a strict language — easier to get wrong (stack safety). Use it only when no standard combinator fits.

**124. Use comparing and on for custom sort/comparison** [style]
`sortBy (comparing _.age)` is one expression. `sortBy (\a b -> compare a.age b.age)` is four. `Data.Ord.comparing` exists for this.

**125. Factor common fields out of ADT variants** [style]
If every constructor carries the same field, factor it out.
```purescript
-- Repeated:
data Node = Element Position Name Children | TextNode Position String

-- Factored:
data NodeContent = Element Name Children | TextContent String
type Node = { position :: Position, content :: NodeContent }
```
The common structure is now visible in the type and accessible without pattern matching.

**126. Name recursive helpers go or loop** [style]
The `go` convention (`myFn xs = go 0 xs where go acc ... = ...`) is immediately recognisable to any FP programmer. A descriptive name is fine too, but avoid inventing a new convention per function.

**127. Use let, not x <- pure y, for pure bindings in do blocks** [style]
`x <- pure (f y)` pretends to be effectful. `let x = f y` says what it is: a pure binding. The reader should not have to verify that `pure` is the only effect.

**128. Minimise type class constraints** [style]
Do not constrain a function with `Eq a =>` if the implementation uses only structural operations. Unnecessary constraints exclude valid call sites (function types, for instance, rarely have `Eq` instances) and misrepresent the function's requirements.

**129. Avoid dead code and commented-out blocks** [style]
Delete what you do not use. Version control remembers. Commented-out code is a trap: it rots faster than live code, gives no compiler errors, and misleads readers into thinking it might be restored.

**130. Use $ and # to reduce parentheses, but do not chain excessively** [style]
`f $ g $ h x` is fine. `f $ g $ h $ i $ j $ k x` is a parenthesis problem solved with a readability problem. For long pipelines, use `>>>` composition or intermediate `let` bindings.

**131. Keep modules under ~400 lines** [style]
If a module grows past this, it is likely doing more than one thing. Split by responsibility. PureScript's orphan-instance rule means types and their instances must stay together, but operations, rendering, and serialisation can live in sibling modules.

**132. Write helpers liberally; export sparingly** [style]
Break complex functions into small, well-typed, unexported helpers. Each helper with a type signature is a checked assertion about an intermediate step. The cost is near zero; the debugging benefit is high.


## XIX. From the Discourse — attributed community wisdom

**133. ADTs for variants, type classes for polymorphism — do not conflate them** [style]
"Defining a separate ADT to model your 'universe' and casing on it is really how the language wants you to solve this problem." Type classes are for ad-hoc polymorphism across unrelated types, not for modelling a hierarchy of related things. If you find yourself writing a class with one method and three instances, you probably want a sum type with three constructors. (Nate Faubion, Discourse /t/3053)

**134. Existentials are an anti-pattern unless you have measured a performance need** [style]
Prefer closures. Existential types (CPS-encoded in PS) gave Halogen ~40% memory reduction, but that is a special case in a framework processing millions of virtual DOM nodes. For application code, a closure is simpler, safer, and often faster. (Nate Faubion, Discourse /t/1024)

**135. Skip the newtype when the record field name already provides context** [style]
A `following :: Boolean` inside `UserProfile` does not need a `Following` newtype. Newtypes earn their keep when the same underlying type appears in multiple positions with different meanings — not when a single named field suffices. (Thomas Honeyman, Discourse /t/450)

**136. Newtype everything that has different semantics from its base type** [style]
When uncertain, add the wrapper. Worst case, you add a few `coerce` calls. UUIDs, email addresses, and identifiers are not Strings. In larger applications, newtypes for records also improve error messages — bare records produce verbose, hard-to-follow type errors. (Thomas Honeyman, Nate Faubion, Discourse /t/450, /t/1179)

**137. Extensible records for function arguments, closed records for domain models** [style]
Use row polymorphism in function signatures so callers can pass records with extra fields. But define domain types as concrete, non-extensible records. Syntactic duplication is preferable to the cognitive overhead of tracking extensible type layers. (joneshf, Discourse /t/217)

**138. Smart constructors: export the type and an unwrapper, not the constructor** [style]
Provide explicit conversion functions (`toInt`, `toString`) alongside validators. Do not create custom type classes for unwrapping — "marginal benefit" and it harms type inference. (CarstenKoenig, Thomas Honeyman, Discourse /t/3344)

**139. JSON codecs should be values, not type class instances** [lib]
Implicit encoding via `EncodeJson`/`DecodeJson` instances creates orphan-instance pressure and makes it invisible which encoding is in use. `purescript-codec-argonaut` gives you bidirectional codec *values* that are explicit, composable, and guarantee roundtripping. (Gary Burgess, Discourse /t/2680)

**140. Avoid dual error channels: do not return Effect (Either e a)** [style]
All Effects can already throw, so wrapping in `Either` creates two parallel error channels. Use `ExceptT` when error information is richer than strings and recovery depends on the error's structure. For simple error messages, plain exceptions with `try` at the boundary are fine. (ntwilson, Nate Faubion, Discourse /t/2640)

**141. Use unsafeCrashWith for genuinely unreachable code** [style]
`Partial.Unsafe.unsafeCrashWith "message"` marks dead branches explicitly. It is better than `unsafePartial $ unsafeCrashWith` and infinitely better than an incomplete pattern match that the compiler might not catch. (Gary Burgess, Discourse /t/1785)

**142. Prefer polymorphic monad constraints over concrete Effect** [style]
Write `forall m. MonadEffect m => ...` instead of `Effect`. This eliminates boilerplate lift functions when you later wrap in a transformer, and makes testing easier (swap the monad). (ntwilson, Discourse /t/3990)

**143. A transformer stack is only as stack-safe as its base** [lib]
`ReaderT (StateT Identity)` inherits `Identity`'s stack unsafety. For stack-safe pure code, use `Trampoline` as the base monad. Use `MonadRec` / `tailRecM` only at the point of final interpretation — using it with already stack-safe monads like `Aff` doubles the number of binds for no benefit. (Nate Faubion, Discourse /t/552, /t/4935)

**144. parTraverse and parSequence cover 80% of parallel Aff** [lib]
Do not manually compose `parallel`/`sequential` unless you need something unusual. For bounded concurrency, use `AVar` with `bracket` to implement a semaphore. (Nate Faubion, Discourse /t/3238, /t/1204)

**145. Use the ReaderT pattern for non-trivial Halogen apps** [lib]
As demonstrated in Real World Halogen. Use `halogen-store` for global state rather than rolling your own `ReaderT` + `Ref`. Reserve manual `ReaderT` for cases where you need fine-grained control. (Thomas Honeyman, Discourse /t/547, /t/2162)

**146. Do not use unsafePerformEffect in production code** [style]
It subverts the type system via polymorphism + mutability. Unused `where` bindings could trigger unintended side effects. Future compiler optimisations could cause further breakage. Acceptable only as a transitional prototyping step for FFI; never expose to others. (Nate Faubion, hdgarrood, Thomas Honeyman, Discourse /t/2323)

**147. Do not mutate input records in FFI code** [JS]
JavaScript FFI functions that modify their arguments violate the functional contract. All PureScript callers assume their values are not mutated. Copy before mutating, or — better — return a new value from PureScript. (wclr, Discourse /t/4847)

**148. join <$> traverse is idiomatic** [style]
There is no dedicated combinator for "traverse, then flatten." `join <$> traverse f xs` is the well-known pattern. Recognise it when you see it; use it when you need it. (paf31, Nate Faubion, Discourse /t/144)

**149. Test laws with purescript-quickcheck-laws** [task]
If your type has `Eq`, `Ord`, `Semigroup`, `Monoid`, `Functor`, or `Monad` instances, test that they obey the laws. `purescript-quickcheck-laws` automates this. An instance that violates its laws is worse than no instance at all. (JamieBallingall, Gary Burgess, Discourse /t/1192)

**150. Semigroup instances should compose, not silently discard** [lib]
The `Map` Semigroup debate: community preference is for unbiased instances that merge values via the inner `Semigroup`, not left- or right-biased union. Use `First`/`Last` wrappers when you want biased behaviour — make the choice visible in the type. (kl0tl, monoidmusician, hdgarrood, Discourse /t/1935)


## XX. From GitHub Issues and Official Guides — the authoritative word

**151. Suffix foreign imports with Impl; hide them behind a wrapper** [JS]
`foreign import joinPathImpl :: Fn2 String String String` then `joinPath start end = runFn2 joinPathImpl start end`. Export `joinPath`, not `joinPathImpl`. The module boundary is where PureScript types begin and JavaScript types end. (Official FFI Tips Guide)

**152. Do not go point-free with runFn** [JS]
The compiler inlines `runFn` calls only when fully saturated. `joinPath = runFn2 joinPathImpl` prevents inlining; `joinPath start end = runFn2 joinPathImpl start end` enables it. The point-free version is subtly slower. (Official FFI Tips Guide)

**153. Never call PureScript code from foreign modules** [JS]
Do not import PureScript-generated constructors like `Data_Maybe.Just.create(x)` in FFI. Instead, pass constructors and functions as extra arguments from the PureScript wrapper. Calling generated code directly breaks when codegen changes and defeats dead-code elimination. (Official FFI Tips Guide)

**154. Pass type class methods, not dictionaries, to FFI** [JS]
When an FFI function needs `show`, pass `show` as an argument from the PureScript wrapper where the compiler resolves the correct instance. Do not try to deal with dictionary objects in JavaScript. (Official FFI Tips Guide)

**155. Remember that Effect values are thunks** [JS]
PureScript wraps effects in constant functions: `export function myEffect() { return doSomething(); }`. Writing `export const myEffect = doSomething()` executes the effect at import time, not when the PureScript program runs it. (Official FFI Tips Guide)

**156. Derived Ord for records compares fields in alphabetical label order** [gotcha]
Not declaration order. `{ a :: Int, z :: String }` and `{ z :: String, a :: Int }` have the same derived `Ord` — comparing by `a` first, then `z`. If you need a different comparison order, write the instance by hand. (jpvillaisaza, purescript/purescript#3226)

**157. Boolean operations (||, &&) are non-strict — an exception to PureScript's strict semantics** [gotcha]
`HeytingAlgebra`'s instance for `Boolean` uses short-circuit evaluation, but this is not guaranteed for all `HeytingAlgebra` instances. If you write generic code over `HeytingAlgebra`, the right-hand side may or may not be evaluated. (eric-corumdigital, purescript/purescript#3457)

**158. Use type wildcards for irrelevant type variables** [style]
In signatures with many phantom or constraint-only variables, `_` makes the signal visible: `raise :: forall s f g p o m. o -> HalogenM s f g p o m Unit` can be focused as `raise :: forall _ _ _ _ o _. o -> HalogenM _ _ _ _ o _ Unit`. (Gary Burgess, purescript/purescript#3530)

**159. Declare type roles explicitly for foreign data and mutable newtypes** [style]
The compiler can infer roles, but explicit `type role MyType nominal representational` documents intent and prevents accidental unsafe coercions via `coerce`. Especially important for types wrapping mutable state. (purescript/purescript#4116)

**160. Structure modules by capability and domain** [lib]
Thomas Honeyman's Real World Halogen: `Api/` (HTTP layer), `Capability/` (type class interfaces), `Component/` (UI), `Data/` (domain types), `Page/` (page components), `Store.purs` (global state). This separates what the app *can do* from what it *is*. (thomashoneyman/purescript-halogen-realworld)

**161. The capability pattern: type classes for effects, newtypes for implementations** [lib]
Define `class MonadLogger m`, `class ManageResource m`. Implement in a production `AppM` newtype. Swap in test implementations. This separates business logic from effect plumbing — you test the logic without running the effects. (Thomas Honeyman, purescript-halogen-realworld)

**162. Follow namespace conventions: Data for data, Control for control, Node for Node.js** [style]
Do not put your data structure in `Control.MyThing` or your effect wrapper in `Data.MyEffect`. The namespace signals the category. (Official Style Guide)

**163. Note runtime environment assumptions in your README** [lib]
If your library only works in Node, or only in the browser, say so prominently. A consumer who installs your library for the wrong platform gets cryptic FFI errors, not a helpful message. (Official Style Guide)

**164. PureScript is industrially focused, not a PL research vehicle** [philosophy]
Stability is a high priority. Feature requests with large downstream impact are unlikely to be accepted. Prefer fewer, more powerful features to many special-purpose ones. If a need can be solved downstream of the compiler, it probably should be. (Governance document — Gary Burgess, Nate Faubion, Thomas Honeyman)


---

## Candidates for De Gustibus (taste, not rules)

- **where vs let** (already drafted)
- **Point-free vs pointed** (already drafted)
- **Qualified imports vs explicit imports** — both have defenders; qualified is noisier but grepping-friendly; explicit is concise but requires maintenance.
- **One module per file vs internal sub-modules** — some codebases split aggressively, some keep related types together. PureScript's orphan instance rule pushes toward co-location.
- **do notation vs bind chains** — `do` is overwhelmingly preferred, but some prefer explicit `>>=` for short pipelines to emphasise the data flow.
- **Total record update vs field-by-field** — `state { a = x, b = y }` vs building a new record from scratch. The latter is sometimes clearer when most fields change.
- **Named vs anonymous lambda in traverse/map** — `map (\x -> x.name)` vs `map _.name`. PureScript supports record accessor shorthand; some find it too terse.
- **Applicative do (ado) vs lift2/lift3** — `ado` is sugar over `Apply`; `lift2 f a b` is sometimes more direct for simple binary combinations. Neither is wrong.
- **`~>` (natural transformation) vs explicit forall** — `~>` looks clean in simple cases (`f ~> g`) but its precedence relative to `->` is surprising, it doesn't chain, and it formats poorly in complex signatures. Nate Faubion: "It's the kind of thing that works ok in a very simple case, but scales poorly, and gets confusing quickly." `foo :: forall a. f a -> g a` is always unambiguous. (Source: PureScript Discord)
- **Parentheses vs `$` vs composition** — Neither is canonical. Parentheses give clearer error messages for beginners; `$` reduces stacked closing parens; `<<<` composition is a third option. Pick what reads best. (Discourse /t/2928)
- **Left-to-right (`#`/`>>>`) vs right-to-left (`$`/`<<<`)** — Pick one direction and stay consistent within a codebase. Right-to-left is more traditional; left-to-right emphasises the sequence of transformations. Mixing freely within one file creates confusion. (Discourse /t/2028)
- **Leading-pipe ADT formatting** — `| Foo | Bar` has strong community support for consistency and cleaner diffs, but purs-tidy may have its own opinion. (Discourse /t/3027)
- **Shadowing: warn or allow?** — Entry 81 says "do not shadow." But Gary Burgess: the shadowing warning "has caused me more trouble than it has saved" — there are valid reasons to shadow (hiding old values in scope after transformation). Some deliberately shadow `state` in `do` blocks after modification. (purescript/purescript#3375)
- **Abbreviation casing: HttpServer vs HTTPServer vs Json vs JSON** — The Tibbe/Kowainik rule says mixed case (`HttpServer`). But `Json` vs `JSON` was debated for argonaut-core, with arguments for matching the spec's casing. No consensus. (purescript-contrib/purescript-argonaut-core#59)
