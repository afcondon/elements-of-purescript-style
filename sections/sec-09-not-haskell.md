# IX. PureScript is not Haskell

PureScript borrows much from Haskell — syntax, type classes, algebraic data types — but the languages differ in ways that matter daily. This section catalogues the differences that trip up Haskell programmers most often. If you have never written Haskell, you may skip this section without loss.


---


## 108. Unused bindings are not free in a strict language

PureScript evaluates strictly, left to right. In Haskell, `let x = expensiveComputation in if flag then x else 0` never evaluates `expensiveComputation` when `flag` is false. In PureScript, it always does.

```purescript
-- In PureScript, both branches of the let are evaluated.
let
  expanded = buildFullTree dataset     -- always runs
  summary  = summarize dataset         -- always runs
in if detailed then expanded else summary

-- Evaluate only what you need.
if detailed
  then buildFullTree dataset
  else summarize dataset
```

Code ported from Haskell or written with Haskell intuitions can silently do more work than intended. Every `let` binding is evaluated at the point of definition, not at the point of use. If only one of several bindings is needed, move the others into the branch that uses them or compute them lazily with an explicit thunk.


---


## 109. Infinite structures do not work

PureScript's strict evaluation means there is no `Data.List.iterate` that produces values on demand. An expression like `iterate (_ + 1) 0` would attempt to build an infinite list immediately and never terminate.

If you want a stream, you need an explicit lazy type (such as `Data.Lazy` or a lazy list library) or a generator pattern that produces values one at a time. Do not port Haskell idioms that rely on lazy spine evaluation — they will hang or exhaust memory.


---


## 110. Choose foldl for strict accumulation

In Haskell, `foldr` is often preferred because laziness lets it short-circuit and work on infinite structures. In PureScript, `foldl` is the natural choice for strict left-to-right accumulation, and `foldr` should be chosen only when the algebra requires right-association (building a list, for instance).

Picking the wrong fold does not produce wrong results — but it can produce unnecessary intermediate allocations. When accumulating a sum, a count, or any strict value, use `foldl`. Reserve `foldr` for cases where the combining function is non-strict in its second argument or where the result must be right-associated.


---


## 111. Write explicit forall

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


## 112. Use <<< for composition, not .

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


## 113. Number literals are not overloaded — and the numeric hierarchy is different

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


## 114. Operator sections use _, not partial application syntax

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


## 115. Ensure stack safety with tailRecM

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


## 116. Mutual recursion defeats TCO

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


## 117. Phantom types and smart constructors replace most GADTs [Haskell]

Haskell programmers arriving in PureScript quickly notice the absence of GADTs. The instinct is to reach for elaborate type-class encodings that simulate them. In most cases, a phantom type parameter with smart constructors does the job — compiles faster, produces better error messages, and can be read by a colleague who has not studied the Hasochism paper.

In Haskell you might write:

```haskell
data Expr a where
  LitInt :: Int -> Expr Int
  Add    :: Expr Int -> Expr Int -> Expr Int
```

In PureScript:

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


## 118. Use continuation-passing style to encode existential types [Haskell]

If you hit a wall trying to express existential types in PureScript, this is the entry to bookmark. The technique is worth learning once — but you may not need it on day one.

The problem: Haskell's `ExistentialQuantification` or GADTs let you write `data SomeShow = forall a. Show a => SomeShow a` — a type that hides the concrete type while retaining a constraint. PureScript does not have this syntax. If you need a heterogeneous collection or a type that erases its concrete representation while preserving a constraint, the idiomatic alternative uses rank-2 types in an encoding known as continuation-passing style (CPS).

**The technique in detail.** In continuation-passing style, instead of returning a result directly, a function takes an extra argument — a *continuation* — that says what to do with the result. The function calls the continuation instead of returning. This indirection is the key to the encoding: you never store the hidden value directly. Instead, you store a function that accepts a handler (the continuation) and applies it to the hidden value internally.

The handler must be polymorphic — it must work for *any* type satisfying the constraint — so the concrete type never escapes. The rank-2 quantification (`forall` inside the argument) is what enforces this.

Here is the pattern applied to a `Foldable` container whose concrete type is hidden:

```purescript
-- "I have a Foldable container of Ints, but I won't tell you which one."
newtype SomeFoldable = SomeFoldable (forall r. (forall f. Foldable f => f Int -> r) -> r)
```

Reading this type from the outside in: `SomeFoldable` wraps a function. That function takes a continuation `k` of type `forall f. Foldable f => f Int -> r` — meaning `k` must work for *any* `Foldable`, not a specific one — and produces an `r`. Inside, the function applies `k` to the concrete container it is hiding.

The smart constructor captures a concrete container and seals it behind the rank-2 boundary:

```purescript
mkSomeFoldable :: forall f. Foldable f => f Int -> SomeFoldable
mkSomeFoldable fa = SomeFoldable \k -> k fa
-- `fa` is concrete here (Array, List, Set, etc.), but `k` cannot inspect which.
```

To use the hidden value, you provide a function that works for any `Foldable`. The continuation you pass in is applied to the hidden container — you get to operate on it, but you never learn its concrete type:

```purescript
sumHidden :: SomeFoldable -> Int
sumHidden (SomeFoldable run) = run \fa -> foldl (+) 0 fa
-- `fa` could be an Array, a List, or a Set — the caller never finds out.
```

No `unsafeCoerce`, no `Foreign`, no runtime tags. The rank-2 type does the work. The compiler guarantees that the concrete type cannot leak.

When you need a heterogeneous collection — "a list of things that can each be folded, but with different concrete container types" — this is the PureScript answer. The pattern is worth learning once; it appears throughout the ecosystem.


---


## 119. Use sum types directly for typed command/message patterns [Haskell]

When you want different payload types for different commands — `Command Insert` carrying an `InsertPayload`, `Command Delete` carrying a `DeletePayload` — the Haskell instinct is to index the command type by a phantom and use GADT matching to eliminate it. In PureScript, use a plain sum type:

```purescript
data Command
  = Insert InsertPayload
  | Delete DeletePayload
  | Update UpdatePayload
```

No phantom parameter, no type-level tag, no class instances to recover the payload type. The sum type is total, exhaustive, and obvious. Pattern matching gives you the payload directly, and the compiler ensures you handle every case.

The general principle: when the simpler encoding covers your use case, prefer it. PureScript's sum types are expressive enough for most command and message patterns, and the directness pays off in readability and error messages. If you have used GADTs for this in Haskell, the plain sum type may feel like a step down — but the loss is smaller than it appears, and the gain in simplicity is immediate.


---


## 120. Derived Ord for records compares fields in alphabetical label order

When the compiler derives an `Ord` instance for a record type, it compares fields in alphabetical order by label name — not in the order they appear in the declaration.

```purescript
type Person = { zipCode :: String, age :: Int, name :: String }

derive instance Ord Person
-- Compares by: age, then name, then zipCode.
-- NOT by: zipCode, then age, then name.
```

This is consistent with PureScript's treatment of records as row types, where label order is semantic, not syntactic. But it surprises programmers who expect declaration order to matter, particularly those coming from Haskell where field order in a `data` declaration determines derived comparison order.

If you need a specific comparison order — compare by age first, then by name — write the instance by hand. Do not rely on renaming fields to sort alphabetically into your preferred order; that is a maintenance trap waiting for the next person who adds a field. (jpvillaisaza)


---


## 121. Boolean operations (||, &&) are non-strict — an exception to PureScript's strict semantics

Entry 8 establishes that PureScript is strict. Boolean `||` and `&&` are the exception: the compiler implements short-circuit evaluation for `Boolean`'s `HeytingAlgebra` instance. `false && expensiveCheck` does not evaluate `expensiveCheck`.

```purescript
-- Short-circuits: the second condition is not evaluated.
isValid :: User -> Boolean
isValid user = isActive user && hasPermission user
```

But this guarantee applies only to `Boolean`. The `HeytingAlgebra` type class is more general, and other instances are not required to short-circuit:

```purescript
-- Generic code: no short-circuit guarantee.
bothTrue :: forall a. HeytingAlgebra a => a -> a -> a
bothTrue x y = x && y
-- If `a` is not Boolean, `y` may be evaluated even if `x` is "false-like."
```

If you write generic code over `HeytingAlgebra`, do not assume the right-hand side is unevaluated when the left-hand side determines the result. The short-circuit behaviour is a special case of the `Boolean` instance, not a law of the class. (eric-corumdigital)


---
