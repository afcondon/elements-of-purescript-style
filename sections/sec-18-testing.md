# XVIII. Testing

PureScript's type system catches many bugs at compile time, but not all. Property-based testing and law checking fill the gap, especially for the algebraic structures that type classes encode.


---


## 177. Write property-based tests, not just examples

An example test says "this input produces this output." A property test says "for all inputs satisfying these constraints, this relationship holds." The second finds bugs the first never will, because it explores inputs the author did not think to try.

```purescript
-- Property: tests the relationship for all generated users
quickCheck \(user :: User) ->
  decode userCodec (encode userCodec user) === Right user

-- Example: tests one case
it "decodes what it encodes" do
  let user = { name: "Alice", role: Admin }
  decode userCodec (encode userCodec user) `shouldEqual` Right user
```

The property version requires an `Arbitrary User` instance, which forces you to think about the space of valid inputs -- itself a useful exercise. It then generates hundreds of random users, including edge cases (empty strings, boundary values, unusual characters) that a hand-written example would never include.

Good candidates for property tests: codec roundtrips, monoid laws (`mempty <> x === x`), idempotency (`f (f x) === f x`), commutativity, and ordering consistency. These are universal relationships, and testing them universally is what property-based testing is for.


---


## 178. Test laws with purescript-quickcheck-laws

If your type has instances for `Eq`, `Ord`, `Semigroup`, `Monoid`, `Functor`, or `Monad`, those instances carry algebraic laws. `Eq` must be reflexive, symmetric, and transitive. `Semigroup`'s `append` must be associative. `Monad` must satisfy left identity, right identity, and associativity.

An instance that violates its laws is worse than no instance at all. Code that uses your type through the class interface assumes the laws hold. When they do not, the bugs are subtle, non-local, and maddening to track down.

```purescript
import Test.QuickCheck.Laws.Data.Eq (checkEq)
import Test.QuickCheck.Laws.Data.Ord (checkOrd)
import Test.QuickCheck.Laws.Data.Monoid (checkMonoid)

main :: Effect Unit
main = do
  checkEq (Proxy :: Proxy MyType)
  checkOrd (Proxy :: Proxy MyType)
  checkMonoid (Proxy :: Proxy MyType)
```

`purescript-quickcheck-laws` generates random instances of your type and verifies each law with property-based tests. This requires an `Arbitrary` instance, which is itself a useful exercise — if you cannot generate random values of your type, your type may be too constrained to test effectively.

Write these tests when you define the instances, not after a bug report. (JamieBallingall, Gary Burgess)


---
