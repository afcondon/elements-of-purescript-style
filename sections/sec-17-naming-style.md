# XVII. Naming and style

Conventions that have no deep justification beyond consistency. Their value is that the community follows them; deviating without reason creates friction for readers who expect the standard patterns.


---


## 167. Order imports: Prelude, then libraries, then local modules

Three groups, separated by blank lines, alphabetical within each group.

```purescript
import Prelude

import Data.Array (filter, length)
import Data.Map as Map
import Data.Maybe (Maybe(..))
import Effect.Aff (Aff)

import MyApp.Data.User (User)
import MyApp.Util (formatDate)
```

The reader can tell at a glance what comes from the language's Prelude, what comes from the ecosystem, and what is project-local. When a module adds a new dependency, the diff touches only the relevant group. When reviewing unfamiliar code, the import section is a table of contents — keep it organised.

Note: `purs-tidy` does not rearrange imports — it formats code structure but leaves import ordering to you. However, the PureScript language server provides `source.organizeImports` and `source.sortImports` code actions, which VS Code can run on save via `editor.codeActionsOnSave`. This removes unused imports and sorts alphabetically within each group — a useful complement to the grouping convention above.


---


## 168. Qualify container imports

`import Data.Map as Map` and write `Map.lookup`, `Map.insert`, `Map.empty` at every call site. The same for `Set`, `List`, `StrMap`, and any container whose operations have generic names.

```purescript
-- Ambiguous: which lookup? which empty?
import Data.Map (lookup, insert, empty)
import Data.Set (empty, insert)  -- name clash

-- Unambiguous: the container is visible at the point of use.
import Data.Map as Map
import Data.Set as Set

result = Map.lookup key (Map.insert key value Map.empty)
items  = Set.insert item Set.empty
```

`lookup`, `insert`, `empty`, `singleton`, and `fromFoldable` appear in half a dozen modules. Qualifying them avoids name clashes and makes the container type visible without tracing back to the import list. The three extra characters per call site are an investment in readability that compounds over the life of the codebase.


---


## 169. Document every export with a doc comment

PureScript doc comments (`-- |`) appear in generated documentation and in IDE hover popups. Every exported function and type should have one.

```purescript
-- | Partition nodes into layers by their depth from the root.
-- | Nodes unreachable from the root are placed in a separate overflow layer.
layerByDepth :: Graph -> Array (Array Node)
```

The comment describes what the function does and any non-obvious behaviour (the overflow layer). It does not describe the implementation. If a function is not worth documenting, it is probably not worth exporting.

For internal helpers, a brief comment is still welcome but not obligatory — the type signature and a well-chosen name often suffice. For exports, the doc comment is part of the API contract. Write it as if the reader cannot see the source code, because often they cannot.


---


## 170. Documentation describes what, not how

"Returns the first element, or `Nothing` if empty." Not: "Pattern matches on the array, checks if the length is zero, then returns the head."

```purescript
-- | Compute the bounding box that encloses all points.
-- | Returns Nothing if the array is empty.
boundingBox :: Array Point -> Maybe BoundingBox

-- Not:
-- | Folds over the array, tracking the min and max x and y
-- | coordinates, then constructs a BoundingBox from the extremes.
```

If you feel the need to explain the mechanism, that is often a signal that the function is doing too much or that its name does not convey its purpose. A doc comment that restates the implementation in English is pure noise — the reader could have read the code. A doc comment that states the contract gives the reader something the code alone does not: permission to stop reading.


---


## 171. Use mixed case for abbreviations: HttpServer, not HTTPServer

When an abbreviation appears in a CamelCase identifier, treat it as a word: `HttpServer`, `JsonParser`, `XmlNode`. The exception is two-letter abbreviations, which remain uppercase: `IO`, `Id`.

The reason is legibility at word boundaries. `HTTPSConnection` forces the reader to determine where `HTTPS` ends and `Connection` begins. `HttpsConnection` is unambiguous. `HTMLParser` could be `HT` + `MLParser` if you squint; `HtmlParser` cannot be misread.

This convention follows the PureScript ecosystem's prevailing practice and aligns with the Haskell style guides (Tibbe, Kowainik). Consistency within a codebase matters more than the specific choice, but if you are starting fresh, mixed case is the safer default.


---


## 172. Use singular module names

`Data.Map`, not `Data.Maps`. `MyApp.Route`, not `MyApp.Routes`. `Component.Sidebar`, not `Components.Sidebar`.

A module represents a concept — the Map type and its operations, the Route type and its parser, the Sidebar component — not a collection of instances of that concept. The singular name is both more precise and more consistent with the PureScript and Haskell ecosystem conventions.

The plural form tempts when a module contains "many things" — many routes, many components. But the module itself is still one thing: the namespace for those definitions. Name it for what it is, not what it contains.


---


## 173. Do not mix let and where in the same definition

A definition that scatters bindings between `let` (above the main expression) and `where` (below it) forces the reader to look in two places to understand the function's vocabulary.

```purescript
-- Mixed: where is `margin` defined? Where is `scaled`?
render state =
  let scaled = state.value * factor
  in svg [ viewBox 0.0 0.0 width height ]
       [ rect [ x margin, y margin, width (width - 2.0 * margin), height scaled ] ]
  where
  factor = 2.5
  margin = 10.0
```

Pick one style per definition. Use `where` for named helpers that support the main expression. Use `let` for intermediate values that feed into the next step. Do not split the supporting cast between two stages.


---


## 174. Name recursive helpers go or loop

When a function uses an inner recursive helper with an accumulator, the conventional name is `go` (or sometimes `loop`). This is not a PureScript invention — it is established practice across Haskell, Scala, and the broader FP community.

```purescript
findIndex :: forall a. (a -> Boolean) -> Array a -> Maybe Int
findIndex pred arr = go 0
  where
  go i
    | i >= Array.length arr = Nothing
    | pred (unsafePartial $ Array.unsafeIndex arr i) = Just i
    | otherwise = go (i + 1)
```

The name `go` signals "this is the tail-recursive workhorse; the outer function is the public interface." Any FP programmer recognises the pattern instantly. A descriptive name like `findFrom` is also fine, but avoid inventing a new naming convention for each function — consistency across the codebase is more valuable than local precision.


---


## 175. Do not shadow; the compiler warns for a reason

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


## 176. Keep warnings under control

The PureScript compiler's warnings are precise: unused imports, missing type signatures, shadowed names, redundant patterns, incomplete binds. Most identify code that is wrong, dead, or unclear.

In `spago.yaml`, you can enforce this:

```yaml
package:
  build:
    censor_warnings:
      - WildcardInferredType
    strict: true
```

A codebase with a dozen warnings trains its authors to ignore the thirteenth — which might be the one that matters. The goal is that every warning is either fixed or consciously suppressed with a reason.

That said, "zero warnings always" is a guideline, not a law. Shadowed name warnings, for instance, are sometimes a sign of clear code — a `let` rebinding a function parameter with the same name after validation is arguably *more* readable than inventing a new name. The `censor_warnings` mechanism exists precisely so you can make deliberate, documented decisions about which warnings matter in your codebase. The sin is not having warnings; it is having warnings nobody looks at.


---
