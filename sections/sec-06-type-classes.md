# VI. Type classes

Type classes in PureScript are not interfaces, not abstract classes, not traits. They are a mechanism for principled ad hoc polymorphism — functions that behave differently for different types, but within a framework of laws and guarantees. Understanding what they are (and are not) is essential to using them well.


---


## 66. ADTs for variants, type classes for ad hoc polymorphism

Type classes are PureScript's mechanism for *ad hoc polymorphism* — giving the same operation different behaviour for different types, within a framework of laws. `Eq` means "this type supports equality, and it is reflexive, symmetric, and transitive." `Monoid` means "this type has an associative binary operation with an identity element." The laws are the point; convenience is a side effect.

This makes type classes fundamentally different from both OOP interfaces and ADT-based dispatch. An ADT models a *closed* set of alternatives your program handles exhaustively. A type class models an *open* set of types that share a lawful interface — any module can add a new instance without modifying the class.

Use ADTs when you know all the cases. Use type classes when the set of types is open and the shared behaviour follows laws.

```purescript
-- Closed set of known alternatives: ADT + pattern match.
data Notification = Email EmailAddress Body | SMS PhoneNumber Body | Push DeviceToken Body

deliver :: Notification -> Aff Unit
deliver = case _ of
  Email addr body -> sendEmail addr body
  SMS phone body  -> sendSMS phone body
  Push token body -> sendPush token body
```

```purescript
-- A type class for a closed set gains nothing and loses exhaustiveness checking.
class Deliverable a where
  deliver :: a -> Aff Unit
```

A useful heuristic: if you are writing a class with one method and three instances, all defined in the same module, you almost certainly want a sum type with three constructors. (Nate Faubion)


---


## 67. Use newtypes to avoid orphan instance errors

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


## 68. There are no default method implementations

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


## 69. Give instances for containers you define

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

More broadly: you will get terrific return on your investment from using existing container types — `Set`, `Map`, `Graph`, `Tree`, `NonEmptyArray` — rather than rolling your own. Not only do they come with all the instances, but using standard containers structures your thinking. A `Set` communicates "no duplicates, order irrelevant." A `Map` communicates "lookup by key." These are design decisions encoded in the type, and they come with tested, optimised implementations for free.


---


## 70. Write functions over Foldable, not concrete containers

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


## 71. Use Traversable to combine effects over structures

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


## 72. Minimise type class constraints

Do not constrain a function with `Eq a =>` if the implementation never compares values of type `a`. Unnecessary constraints exclude valid call sites and misrepresent the function's actual requirements.

Prefer:

```purescript
reverseList :: forall a. List a -> List a
reverseList = foldl (flip Cons) Nil
```

Over:

```purescript
reverseList :: forall a. Eq a => List a -> List a
reverseList = foldl (flip Cons) Nil
```

Each constraint is a promise that the function uses that capability. An `Eq` constraint says "I compare values for equality somewhere in this implementation." A `Show` constraint says "I convert values to strings." If the promise is false, the function is lying about its requirements — and that lie has practical consequences. Function types, for instance, rarely have `Eq` instances; an unnecessary `Eq a =>` prevents the function from being used with `a ~ (Int -> Int)`.

The compiler does not warn about over-constrained functions. Discipline here is manual but worthwhile.


---


## 73. Do not use Show for serialisation

`Show` is for debugging. Its output format is not stable across compiler versions, not specified by any standard, and not guaranteed to be parseable. A `Show` instance is a convenience for the REPL and for log messages during development. It is not a serialisation format.

Prefer:

```purescript
saveConfig :: Config -> Effect Unit
saveConfig config = writeFile "config.json" (stringify $ encodeConfig config)
```

Over:

```purescript
saveConfig :: Config -> Effect Unit
saveConfig config = writeFile "config.txt" (show config)
```

If you need to serialise a value, write a codec — `purescript-codec-argonaut`, `purescript-yoga-json`, or a hand-rolled encoder. If you need a human-readable label for a UI, write a `display` function with an explicit, documented format. `Show` instances should appear in debug logs and test failure messages; they should never appear in data that crosses a process boundary, a network, or a file system.

The temptation is strongest with simple types — `show myEnum` produces something that looks reasonable today. But "today" is the operative word. When you add a constructor, rename one, or change the `Show` instance for readability, every consumer of that serialised string breaks silently.


---


## 74. Semigroup instances should compose, not silently discard

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


## 75. Avoid stringly-typed Symbol proxies when an ADT exists

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
