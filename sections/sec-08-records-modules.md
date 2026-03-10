# VIII. Records, rows, and modules

Records and modules are the primary tools for organising code. Records give structure to data; modules give structure to namespaces. PureScript's row polymorphism makes records more flexible than in most languages, and its strict module system makes exports and imports more intentional.


---


## 89. Use records with named fields when three or more arguments share a type

When a function takes multiple arguments of the same type, the compiler cannot protect you from transposition. The caller can, if the arguments have names.

Prefer:

```purescript
createUser :: { name :: String, email :: String, role :: String } -> Effect User
```

Over:

```purescript
createUser :: String -> String -> String -> Effect User
```

The positional version permits `createUser "admin" "alice@x.com" "Alice"` and the compiler will not object. The record version makes each field self-documenting at the call site: `createUser { name: "Alice", email: "alice@x.com", role: "admin" }`.

This is not a blanket rule against curried functions. `filter :: (a -> Boolean) -> Array a -> Array a` benefits from currying because the two arguments have different types and partial application is natural. The rule applies when the types alone do not distinguish the arguments and human memory is the only safeguard.

For even stronger protection, combine records with newtypes: `{ name :: Name, email :: Email, role :: Role }`.


---


## 90. Use row polymorphism instead of concrete record types in library APIs

PureScript's row polymorphism lets a function require specific fields without constraining the rest of the record. This is a feature worth using at module boundaries.

Prefer:

```purescript
renderWidget :: forall r. { label :: String, onClick :: Effect Unit | r } -> HTML
```

Over:

```purescript
type WidgetProps = { label :: String, onClick :: Effect Unit }

renderWidget :: WidgetProps -> HTML
```

The closed record forces every caller to construct exactly `{ label, onClick }` and nothing more. The open record accepts any record that has at least those fields -- callers with additional fields do not need to destructure and rebuild.

This matters most in libraries and shared modules where you cannot predict every calling context. Within a single application module, a closed record is often fine -- you control both sides. The principle is: require what you need, accept what you are given.


---


## 91. Use record update syntax, not manual reconstruction

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

For nested records, PureScript supports nested update syntax — no lenses required for simple cases:

```purescript
setPersonPostcode :: PostCode -> Person -> Person
setPersonPostcode pc p = p { address { postCode = pc } }
```

In `do` blocks and Halogen handlers, combine this with the wildcard from entry 76: `H.modify_ _ { loading = true }`. One token for the record, one field updated, nothing else to read.


---


## 92. Use _ for record updates in modify

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


## 93. Use _.field for record access in map

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


## 94. Use an explicit lambda when the body goes beyond field access

Accessor shorthand (`_.field`) is for field extraction. The moment the body involves computation, conditionals, or references to multiple fields, write a named lambda instead.

```purescript
-- Accessor shorthand: clean.
map _.name users

-- Lambda required: the body computes.
map (\item -> item.price * item.quantity) orders

-- Lambda required: multiple fields.
map (\u -> u.firstName <> " " <> u.lastName) users
```

The boundary is usually self-evident. If the body is more than a dotted path, you need a lambda — and the parameter name (`item`, `u`) gives the reader a handle on what is being transformed. Do not contort accessor shorthand to avoid naming a parameter; the name is the point.


---


## 95. Skip the newtype when the record field name already provides context

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

See also entry 140 for the complementary case where the newtype is warranted.


---


## 96. Newtype everything that has different semantics from its base type

This is the affirmative case for newtypes, complementing entry 139's restraint. When a `String` is not just a string — when it is a UUID, an email address, a file path, a CSS class name — wrap it. The newtype costs nothing at runtime and prevents an entire category of mixups at compile time.

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


## 97. Extensible records for function arguments, closed records for domain models

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


## 98. Use explicit export lists

A module without an export list exports everything: public API, internal helpers, partially-applied constructors, and any re-exports you did not intend. This is rarely what you want.

```purescript
-- Exports everything, including helpers the caller should not depend on.
module MyApp.Parser where

-- Exports exactly the public API.
module MyApp.Parser
  ( parse
  , ParseError(..)
  , ParseResult
  ) where
```

An explicit export list serves three purposes. It tells the reader what the module is for, without requiring them to scan the entire file. It lets you refactor internal functions freely, knowing that no downstream code depends on them. And it prevents accidental coupling -- the kind that only surfaces when you try to move a helper function and discover six modules importing it.

Export data constructors with `(..)` when callers need to pattern match. Export only the type name when you want to preserve the ability to change the representation.


---


## 99. Use explicit imports or qualified imports

When you read `head xs` in a module with `import Data.Array` and `import Data.List`, you cannot tell which `head` is being called without checking the types. When you read `Array.head xs`, you can.

Prefer:

```purescript
import Data.Array as Array
import Data.Map (lookup, insert)
import Data.String.CodeUnits (length)
```

Over:

```purescript
import Data.Array
import Data.Map
import Data.String.CodeUnits
```

Open imports make the provenance of every name ambiguous. The compiler resolves it, but the reader must do extra work — or rely on an IDE — to do the same. Explicit imports also make unused dependencies visible: if you remove the last use of `insert`, the import stands out as dead code.

The Prelude is the most common open import, and its contents (`map`, `bind`, `show`, `pure`, `unit`) are ubiquitous enough that qualifying them adds noise. But even Prelude is not sacred — when working heavily with a library whose names clash with Prelude, it can be clearer to import Prelude explicitly and open-import the library instead. Use `hiding` to suppress specific Prelude names that clash rather than qualifying every use. The principle is always the same: make it obvious where each name comes from.


---


## 100. Separate data types from their operations

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


## 101. Distinguish configuration from state

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


## 102. Factor common fields out of ADT variants

If every constructor of a sum type carries the same field, that field belongs outside the sum.

```purescript
-- Repeated: position appears in every constructor.
data Node
  = Element Position Name (Array Node)
  | TextNode Position String
  | Comment Position String

-- Factored: position is structural, content varies.
data NodeContent
  = ElementContent Name (Array Node)
  | TextContent String
  | CommentContent String

type Node = { position :: Position, content :: NodeContent }
```

Every `Node` still has a `Position` — it lives in the record wrapper, not in each constructor. `TextContent` and `CommentContent` carry only the data that varies; the position is always `node.position`, no pattern matching required.

The factored version makes the common structure visible in the type. You can write `node.position` directly, without a helper function that matches on every constructor to extract the same field. When you add a new constructor to `NodeContent`, the `Node` record still requires a `position` — you cannot forget it.


---


## 103. Keep modules under approximately 400 lines

A module that grows past this threshold is likely doing more than one thing. It accumulates responsibilities until no one can hold it in their head, and every change requires scrolling past unrelated code.

Split by responsibility. A data type and its core operations in one module; rendering functions in a sibling; serialisation in a third. PureScript's orphan-instance rule means a type and its instances must live together, but operations that use the type can live anywhere.

The number is not sacred — some modules are naturally larger (a component with many action handlers, a codec module for a complex API). The principle is: when you find yourself navigating within a module rather than reading it, it is time to split.


---


## 104. Write helpers liberally; export sparingly

Break complex functions into small, well-typed, unexported helpers. Each helper with a type signature is a checked assertion about an intermediate step — a waypoint where the compiler verifies your reasoning.

```purescript
-- A single monolithic function: hard to test, hard to debug.
processData :: RawInput -> Effect Output
processData raw = do
  ...  -- 60 lines of interleaved parsing, validation, and transformation

-- Decomposed: each step is named, typed, and independently testable.
processData :: RawInput -> Effect Output
processData raw = do
  let parsed = parseFields raw
  validated <- validateFields parsed
  pure $ transformToOutput validated

-- These are not exported. They exist for clarity, not reuse.
parseFields :: RawInput -> ParsedFields
parseFields = ...

validateFields :: ParsedFields -> Effect ValidatedFields
validateFields = ...

transformToOutput :: ValidatedFields -> Output
transformToOutput = ...
```

The cost of an unexported helper is near zero: a few lines of code that the compiler checks and dead-code elimination removes if unused. The benefit is that when something goes wrong, the type error points to a small, named function rather than line 47 of an anonymous pipeline. Write as many as you need. Export only what the module's consumers require.


---


## 105. Structure modules by capability and domain

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

See also entry 165 for the capability pattern that gives the `Capability/` directory its purpose.


---


## 106. The capability pattern: type classes for effects, newtypes for implementations

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

This is the `ReaderT` pattern from entry 149 taken to its logical conclusion: the monad abstraction separates business logic from effect plumbing entirely.


---


## 107. Follow namespace conventions: Data for data, Control for control, Node for Node.js

PureScript's module namespace conventions carry semantic weight. They tell the reader what category of abstraction a module provides before they open the file.

`Data.*` is for data structures, types, and pure operations on them. `Data.Map`, `Data.Array`, `Data.Maybe`. `Control.*` is for control flow abstractions — monads, applicatives, continuations. `Control.Monad.Reader`, `Control.Alt`. `Effect.*` is for effectful operations. `Node.*` is for Node.js-specific bindings.

The split is not arbitrary. There are genuinely two kinds of functor hiding behind the same type class. A *data functor* is a container — it holds many values, and `map` applies a function to each one. `Data.Array`, `Data.Map`, `Data.List`. A *control functor* wraps a single result with an effect, and `bind` sequences what happens next. `Control.Monad.Reader`, `Control.Monad.State`. In regular Haskell and PureScript the two coincide (every functor is both), but the namespace convention preserves the conceptual distinction. A useful heuristic: if the abstraction answers "what is in here?", it belongs in `Data`. If it answers "what do I do next?", it belongs in `Control`. (Arnaud Spiwack, "A Tale of Two Functors")

Do not put your data structure in `Control.MyThing`. Do not put your effect wrapper in `Data.MyEffect`. The namespace is not a filing system — it is a signal. When a reader sees `import Control.Monad.MyTransformer`, they expect a monad transformer. When they see `import Data.MyCollection`, they expect a data structure with pure operations.

For application code, your top-level namespace is your project name: `MyApp.Data.User`, `MyApp.Api.Client`, `MyApp.Component.Header`. The conventions apply within your namespace just as they do in the ecosystem. (Official Style Guide)


---
