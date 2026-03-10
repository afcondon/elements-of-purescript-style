# I. Let the compiler do the work

PureScript's compiler is not a gatekeeper — it is a collaborator. Every feature in this section exists to move knowledge out of your head and into the type system, where it can be checked, enforced, and relied upon. The habit to cultivate is simple: when you know something about your program, ask whether the compiler can know it too.


---


## 1. Make the compiler's knowledge your own

When your function must handle every case of a sum type, write it as a pattern match — and let the compiler confirm you covered them all.

```purescript
layoutInfo :: LayoutType -> LayoutInfo
layoutInfo = case _ of
  TreeHorizontal -> { name: "Tree", description: "Reingold-Tilford" }
  TreeVertical   -> { name: "Tree (Top-Down)", description: "Vertical layout" }
  Pack           -> { name: "Circle Pack", description: "Nested circles" }
  ...
```

This is clear and the compiler checks exhaustiveness. Now consider the alternative, which appears in many codebases:

```purescript
layoutInfo :: LayoutType -> LayoutInfo
layoutInfo lt = fromMaybe { name: "Unknown", description: "" } $ Map.lookup lt infoMap
  where
  infoMap = Map.fromFoldable
    [ Tuple TreeHorizontal { name: "Tree", description: "Reingold-Tilford" }
    , Tuple TreeVertical { name: "Tree (Top-Down)", description: "Vertical layout" }
    , Tuple Pack { name: "Circle Pack", description: "Nested circles" }
    ...
    ]
```

The Map version looks sophisticated but is worse in every way that matters. The compiler cannot check that every constructor appears in the map. The `fromMaybe` with a dummy value silently handles the missing case — exactly the bug you wanted the type system to prevent. And the function is no longer obviously total; the reader must verify the map's contents against the type to be sure.

Reach for `Map` when the keys are data. Use pattern matching when the cases are the definition.

A corollary: when you match on a closed ADT, spell out every constructor. Do not catch the remaining cases with a wildcard. Today's wildcard is tomorrow's silent bug — when a new constructor is added, the compiler will warn you about the missing case in an explicit match but will say nothing about a wildcard that swallows it. Your language server or LLM will happily generate the boilerplate; there is no excuse for `_ ->` on a type you control.


---


## 2. Avoid boolean blindness with ADTs

When a value can only be one of a known set of alternatives, represent it as a sum type — not as a `String` you validate, and not as a `Boolean` you remember the meaning of.

```purescript
-- Structure-dependent: the type answers the question.
data Element = Sidebar | Toolbar | StatusBar
data Visibility = Visible | Hidden

setVisibility :: Element -> Visibility -> Effect Unit

-- The call site documents itself:
setVisibility Sidebar Visible
```

```purescript
-- Convention-dependent: what does `true` mean?
setVisibility :: String -> Boolean -> Effect Unit

-- The call site is opaque:
setVisibility "sidebar" true
```

The String-and-Boolean version requires the reader to know (or discover) what `"sidebar"` and `true` mean in this context. The ADT version requires them to know nothing beyond the types. And when someone adds a new element or a third visibility state (`Collapsed`), every call site that needs updating will fail to compile.

The same principle applies to intermediate representations. If your program passes around a `String` that can be `"left"`, `"right"`, or `"center"`, and somewhere validates it — that validation is an admission that the type is wrong.

Prefer:

```purescript
data Alignment = Left | Right | Center

align :: Alignment -> HTML -> HTML
align = case _ of
  Left   -> ...
  Right  -> ...
  Center -> ...
```

Over:

```purescript
align :: String -> HTML -> HTML
align s = case s of
  "left"   -> ...
  "right"  -> ...
  "center" -> ...
  _        -> ... -- what goes here?
```


---


## 3. Newtype what you mean

A type alias documents intent for the reader. A newtype enforces it through the compiler.

```purescript
-- Newtypes. The compiler distinguishes them.
newtype NodeID = NodeID Int
newtype LinkID = LinkID Int

derive newtype instance Eq NodeID
derive newtype instance Ord NodeID

derive newtype instance Eq LinkID
derive newtype instance Ord LinkID

addEdge :: NodeID -> NodeID -> LinkID -> Graph -> Graph
-- addEdge linkId nodeId nodeId graph  -- type error
```

```purescript
-- A type alias. The compiler sees Int everywhere.
type NodeID = Int
type LinkID = Int

addEdge :: NodeID -> NodeID -> LinkID -> Graph -> Graph
-- Nothing prevents: addEdge linkId nodeId nodeId graph
```

The runtime cost is zero — newtypes are erased during compilation. The development cost is small: a declaration, a constructor, and a few derived instances. The return is that an entire class of argument-transposition bugs becomes impossible.

The question to ask is not "do I need a newtype here?" but "would swapping this value with another value of the same underlying type be a bug?" If the answer is yes, the type alias is a comment where you needed a guard rail.

A common situation in a real codebase: `NodeID` appears as a type alias in six modules across two packages. Some modules use `Int` directly, some use the alias, and the compiler treats them identically. A newtype in one shared location would have caught the inconsistency at the point it was introduced.


---


## 4. Constructor order is semantic — put it to work

When you derive `Ord` for a sum type, PureScript orders the constructors from left to right as declared. This is not an implementation detail — it is a design decision.

```purescript
data Severity = Info | Warning | Error

derive instance Eq Severity
derive instance Ord Severity

-- Now: Info < Warning < Error
-- sort [Error, Info, Warning] == [Info, Warning, Error]
```

The ordering is free, correct, and obvious to anyone reading the type declaration. Think of constructor order as a feature, not an accident. When you define a type whose values have a natural ordering — severity levels, lifecycle stages, priority tiers — put the constructors in that order and derive `Ord`. If the ordering you want does not match any natural declaration order, write the instance by hand, but know you are making an affirmative choice.


---


## 5. Let the compiler write the instances

The previous entry showed one derived instance. In practice you will derive many — and this is what makes newtypes and ADTs cheap. You get the behaviour you need without writing or maintaining the code.

For a newtype wrapping a type that already has instances, use `derive newtype instance` to lift them through:

```purescript
newtype Score = Score Int

derive newtype instance Eq Score
derive newtype instance Ord Score
derive newtype instance Semiring Score
```

`Score` now supports `==`, `compare`, `+`, and `*` — all delegating to `Int`'s implementations. No code was written and none can be wrong.

For sum types, the compiler can derive `Eq`, `Ord`, `Functor`, `Foldable`, `Traversable`, and several others directly:

```purescript
data Direction = North | East | South | West

derive instance Eq Direction
derive instance Ord Direction
```

For the full monad transformer pattern, newtype deriving eliminates what would otherwise be five repetitive instance declarations:

```purescript
newtype AppM a = AppM (ReaderT Config (ExceptT AppError Aff) a)

derive newtype instance Functor AppM
derive newtype instance Apply AppM
derive newtype instance Applicative AppM
derive newtype instance Bind AppM
derive newtype instance Monad AppM
```

Each line delegates to the corresponding instance on the wrapped transformer stack. Without newtype deriving, each would be ten lines of manual lifting. With it, the compiler generates correct code that you never read, never test, and never debug.


---


## 6. Records multiply possibilities — use sums to limit them

Records are natural and familiar. You throw together a few fields, and you have a data structure. But every field you add multiplies the space of representable values, and most of those combinations are nonsense. If two fields can combine to represent an impossible state — that is a bug in your types, and you will spend the rest of the codebase defending against it.

```purescript
-- Four states, each carrying exactly the data it needs. Nothing else is representable.
data Connection
  = Disconnected
  | Connecting Url
  | Connected Url Socket
  | Failed Url Error
```

The sum type makes the impossible states *unrepresentable*. You cannot construct a `Disconnected` with a socket because the constructor does not accept one. You cannot construct a `Failed` without an error because the constructor requires one. The defence is structural, not conventional. Compare with:

```purescript
-- Four fields, each independent. How many combinations?
-- String × Maybe Url × Maybe Socket × Maybe Error — far too many.
type Connection =
  { status :: String          -- "disconnected" | "connecting" | "connected" | "failed"
  , url :: Maybe Url
  , socket :: Maybe Socket
  , error :: Maybe Error
  }
```

Can you have a `"disconnected"` connection with a socket? A `"failed"` connection with no error? A `"connecting"` connection with no URL? The type says yes. The domain says no. Every function that touches this record must defend against those impossible combinations — or trust that no code produces them. That trust is the bug.

This is one of the biggest ideas in typed functional programming. Smart constructors (next entry), newtypes, `NonEmpty`, phantom types — many entries in this guide are applications of the same principle. The habit to develop: whenever you define a type, ask what states it allows that should not exist. If the answer is "many," a sum type is waiting to be extracted.


---


## 7. Think about the state space of every type you define

The previous entry showed one specific fix — replacing a record with a sum type. This entry is the general principle behind it.

When you combine types into a record, you are *multiplying* their possibilities. A record with a `Boolean`, a `Maybe String`, and an `Int` can represent `2 × 2 × (all Ints)` combinations. Most of those combinations will be meaningless in your domain, but your code must handle all of them — or hope nobody constructs the bad ones.

Sum types work in the other direction: they *constrain* possibilities. `data Light = Red | Amber | Green` has exactly three values, not the infinity of `String`. When you combine sums and products thoughtfully, you can shrink the representable state space until it closely matches the domain — and no closer.

The question to ask about any entity in your program — whether it is an ADT, a record, or a `Map` — is: *what implicit domain knowledge have I failed to encode?* Every fact about your domain that lives in a comment, a validation function, or a developer's head rather than in the type is a fact that the compiler cannot check. Some of those facts are hard to encode. Many are easy — and the only reason they are not encoded is that nobody stopped to think about the state space.

This is unfamiliar territory for programmers coming from languages without sum types. In those languages, throwing together a record (or object, or dictionary) and then validating and pruning and defending against it is the normal workflow. In PureScript, you have the tools to *not represent those states in the first place*. Use them.


---


## 8. Smart constructors: export the type, not the constructor

When a type has an invariant that the type system cannot express directly, enforce it with a smart constructor. Export the type and the constructor function, but not the data constructor. If you have worked in OO languages, this is the same idea as making a constructor private and exposing a factory method — PureScript enforces it through module exports rather than access modifiers.

```purescript
module App.Types.Email
  ( Email         -- type only, no constructor
  , mkEmail       -- smart constructor
  , unEmail       -- accessor
  ) where

newtype Email = Email String

mkEmail :: String -> Maybe Email
mkEmail s
  | contains (Pattern "@") s && length s > 3 = Just (Email s)
  | otherwise = Nothing

unEmail :: Email -> String
unEmail (Email s) = s
```

Consumers of this module can create an `Email` only through `mkEmail`, which validates the invariant. They cannot write `Email "not-an-email"` because the `Email` constructor is not exported. Every `Email` value in the program is guaranteed to have passed validation.

This pattern composes well with `Newtype` deriving. Inside the module, you have full access to the constructor for implementing functions. Outside, the abstraction is sealed. The cost is one module boundary; the benefit is that the invariant is enforced once and relied upon everywhere.

This is "make illegal states unrepresentable" (entry 6) applied at the boundary: you cannot prevent the outside world from handing you `"not-an-email"`, but you can ensure that if someone has an `Email`, it is a validated thing and not a ghastly string.


---


## 9. Design the types first, write the functions second

Try starting with the types. Before writing any logic, sketch the ADTs, the records, the newtypes. Write the type signatures for the functions you will need. Then fill in the implementations.

This is not "eat your vegetables" advice — it is one of the genuine pleasures of working in PureScript. A type signature is a conversation with the compiler about what your function needs, what it produces, and what can go wrong. If the signature is hard to write, that is useful information: it usually means the problem needs more thought. And once the types are in place, the compiler *helps you write the code*. It narrows the possibilities, flags wrong turns immediately, and often guides you to the implementation more efficiently than staring at a blank function body.

Often, once the types are right, the implementation is obvious — sometimes uniquely determined. A function `Array (Tuple k v) -> Map k v` has essentially one reasonable implementation. A function `forall f a b. Functor f => (a -> b) -> f a -> f b` has exactly one. The types do the thinking; the programmer merely transcribes.

Most experienced PureScript and Haskell programmers report that writing types first is the opposite of a chore — it is the moment where the design becomes clear. When the types are wrong, no amount of clever logic will save you. Fix the types and the functions simplify themselves.


---


## 10. Sum types for "or", product types for "and"

An algebraic data type is built from two operations: *sum* (a value is one of several alternatives) and *product* (a value has several fields together).

```purescript
-- Sum: "A request is either pending, succeeded, or failed."
data Request a
  = Pending
  | Succeeded a
  | Failed String

-- Product: "A point has both an x-coordinate and a y-coordinate."
type Point = { x :: Number, y :: Number }
```

This sounds trivial, but programmers arriving from object-oriented languages systematically reach for inheritance hierarchies where a sum type is the correct model. In Java, you might write an abstract `Shape` class with `Circle` and `Rectangle` subclasses, then discover you cannot exhaustively match on them without `instanceof` checks. In PureScript, `data Shape = Circle Number | Rectangle Number Number` gives you exhaustiveness checking for free.


---


## 11. Records are PureScript's predominant product type

Haskell programmers may be surprised: in PureScript, records are the everyday product type. They are anonymous, structurally typed, and support row polymorphism — features that make them far more versatile than Haskell's named record fields.

```purescript
-- A record type. No declaration needed — just use it.
type Point = { x :: Number, y :: Number }

-- Row polymorphism: works with any record that has a `name` field.
greet :: forall r. { name :: String | r } -> String
greet person = "Hello, " <> person.name
```

If you find yourself passing five related arguments to every function, that is a record waiting to be named. And if you find yourself writing a record where half the fields are `Maybe` because they only apply to certain variants — that is a sum type buried inside a product type, struggling to get out (see entry 6).

Records are fantastic as products but they have no notion of "or" — every field is always present. This means they can silently smuggle illegal states into your program. A record with a `status :: String` and a `socket :: Maybe Socket` and an `error :: Maybe Error` has multiplied together a vast space of combinations, most of which are nonsense. Always ask whether your record's fields can combine to represent something that should not exist (see entry 7).


---


## 12. Phantom types: unify through parameterisation

A phantom type parameter appears in a type's signature but not in its runtime representation. Its power is not merely to distinguish values — it is to *unify* disparate parts of a codebase through a shared, parameterised type.

```purescript
newtype Id (entity :: Type) = Id String

derive newtype instance Eq (Id a)
derive newtype instance Ord (Id a)

lookupUser :: Id User -> UserMap -> Maybe User
lookupOrder :: Id Order -> OrderMap -> Maybe Order

-- This compiles:
lookupUser userId users

-- This does not:
lookupUser orderId users
-- Type error: Id Order does not unify with Id User
```

At runtime, both `Id User` and `Id Order` are plain strings. The `User` and `Order` parameters are erased during compilation; they cost nothing in memory or execution time. But the compiler treats them as distinct types, which means you cannot accidentally pass an order ID where a user ID is expected.

The deeper value of phantom types is unification. Every entity in your system — users, orders, invoices, sessions — shares a single `Id` type. Functions that work for any identified entity (`fetchById :: forall e. Id e -> Aff (Maybe e)`) are written once and apply everywhere. Lookup tables, caches, and logging infrastructure all parameterise over the same phantom, giving you a consistent vocabulary across modules that otherwise know nothing about each other. The phantom parameter is the thread that ties them together while the type checker keeps them apart where they need to be.

Without phantom types, you rely on variable naming conventions — `userId`, `orderId` — to keep identifiers straight, and you write separate id types or aliases for each entity. Conventions are suggestions; a shared parameterised type is architecture.

Phantom types have other uses beyond identifiers — tagged state machines, unit-safe quantities, and capability tokens among them. See the power tools section for more.


---


## 13. Use typed holes to ask the compiler for help

A typed hole — any identifier beginning with `?` — tells the compiler: "I do not know what goes here; tell me what you expect."

```purescript
render state =
  HH.div []
    [ HH.text ?help ]
```

The compiler responds with the expected type (`String`), the bindings in scope, and their types. This is not a workaround for incomplete code — it is a development technique. Use it when you know the shape of the expression but not the exact function name, when you are exploring an unfamiliar API, or when a type error is confusing and you want to see what the compiler actually expects at a specific position.

Typed holes are especially valuable in pipelines. Placing `?here` in the middle of a composition chain tells you exactly what type flows through that point, without reading the signatures of every function in the chain.


---


## 14. Take the type the compiler gives you and search Pursuit

A typed hole tells you what the compiler expects. The next step: paste that type signature into Pursuit (PureScript's package search engine) and discover the function that already exists.

You place `?help` in a pipeline and the compiler says it needs `forall a. Maybe a -> a -> a`. You paste that into Pursuit's type search and find `fromMaybe`. You are looking for something that does `forall a. (a -> Boolean) -> Array a -> Array a` — and Pursuit shows you `filter`. Often the function you are about to write is one Pursuit search away.

This technique is especially powerful for discovering `traverse`, `foldMap`, `sequence`, and other workhorse functions whose names are hard to guess but whose types are unambiguous. Let the type lead you to the function, not the other way around.


---


## 15. Always write type signatures on top-level declarations

The PureScript compiler infers types, but inference is a convenience for the author, not a service to the reader. A top-level binding without a type signature is a function whose contract must be reverse-engineered from its implementation.

Prefer:

```purescript
buildIndex :: Array Entry -> Map EntryId Entry
buildIndex entries =
  Map.fromFoldable $ map (\e -> Tuple e.id e) entries
```

Over:

```purescript
buildIndex entries =
  Map.fromFoldable $ map (\e -> Tuple e.id e) entries
```

The compiler warns on missing signatures for good reason. Without one, a small change to the implementation can silently change the inferred type, which in turn changes the type expected by every caller. A signature pins the contract. If the implementation no longer matches, the error appears where the change was made, not somewhere downstream.

Write the signature first. It is the function's spec.


---


## 16. Comment out your type signature and learn if it could be better

After writing a function, try this: comment out the type signature and rebuild. The compiler will warn about the missing signature and show you what it inferred. If the inferred type is more general than what you wrote — `Foldable f => f a` where you wrote `Array a`, or `Semiring a =>` where you wrote `Int` — you may be over-constraining your function.

This is a conversation with the compiler, not a test. Sometimes the more general type is what you want — a function that works on any `Foldable` is more reusable than one locked to `Array`. Sometimes the specific type is better — it documents intent and gives better error messages. Either way, you are making the choice consciously, because the compiler told you what was possible.


---


## 17. Read compiler errors bottom-up

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


## 18. Understand kind errors

PureScript distinguishes types by their *kind* — the "type of a type." `Int` has kind `Type`. `Maybe` has kind `Type -> Type` (it takes a type and returns a type). `Effect` has kind `Type -> Type`. A row of types has kind `Row Type`.

A kind error means you supplied a type constructor with the wrong number of arguments:

```purescript
-- Correct: Maybe is applied to a type.
foo :: Maybe String -> String

-- Kind error: Maybe has kind Type -> Type, but Type was expected.
foo :: Maybe -> String
```

Read "expected kind `Type`, got kind `Type -> Type`" the same way you would read "expected type `Int`, got type `String`." The fix is the same in spirit: you gave the compiler the wrong thing. Usually you forgot to apply a type constructor to its argument, or applied it to too many.

Kind errors are more common when working with type classes (`class Functor f` requires `f` of kind `Type -> Type`) and when defining instances. If the error mentions `Row Type`, you likely wrote a record type where a row was expected, or vice versa.


---


## 19. Use type wildcards for irrelevant type variables

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

In library code and exported functions, explicit type variables serve as documentation — name them all. But in application code, those same type variables are often noise. Wildcards reduce that noise without losing information; in fact, they *increase* information by telling the reader "this type does not matter in this context." (Gary Burgess)


---
