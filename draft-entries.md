# The Elements of PureScript Style — Draft Entries

Working draft. Entries are numbered for reference, not final ordering.


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


---

## 2. Do not reach for a default you do not need

This is a companion to rule 1. Programmers arriving from JavaScript, Python, or even Haskell are accustomed to partial lookups — `obj[key]`, `dict.get(key, default)`, `Map.lookup k m` returning `Maybe` and then immediately `fromMaybe`-ing it away. In those languages, the container is the only way to associate keys with values, so the lookup-with-default is a load-bearing idiom.

In PureScript, if your keys are a closed set — an ADT — you do not need a container at all. Pattern matching is the lookup, and the compiler is the totality checker. The `fromMaybe` reflex comes from languages where the compiler cannot help.

The telltale sign: a `fromMaybe` or `fromJust` immediately after a `Map.lookup` where the map was built from a known, fixed set of keys. If you find yourself writing a default value that should never be reached, that is a signal the type system could prevent the situation entirely.

```purescript
-- The default is a lie. It says "this can fail" when it cannot.
colorFor :: Status -> String
colorFor s = fromMaybe "#000" $ Map.lookup s colors
  where
  colors = Map.fromFoldable
    [ Tuple Active "#2d5a27", Tuple Inactive "#999", Tuple Error "#c23b22" ]

-- The truth: Status has three constructors and you know all of them.
colorFor :: Status -> String
colorFor = case _ of
  Active   -> "#2d5a27"
  Inactive -> "#999"
  Error    -> "#c23b22"
```

When you add a fourth constructor to `Status`, the pattern match will produce a compiler warning. The map will produce the wrong color, silently.


---

## 3. Traverse; do not map and sequence

When you need to apply an effectful function to every element of a structure, use `traverse`. Do not `map` the function over the structure and then `sequence` the result.

Prefer:

```purescript
loadAll :: Array FilePath -> Aff (Array String)
loadAll = traverse readTextFile
```

Over:

```purescript
loadAll :: Array FilePath -> Aff (Array String)
loadAll paths = sequence (map readTextFile paths)
```

These are equivalent — `traverse f` is defined as `sequence <<< map f` — but the composed version says two things ("apply this to each element", then "collect the effects") where one will do. Worse, the two-step version invites the reader to wonder whether something happens between the `map` and the `sequence`, and the answer is always no.

Use `for` when the function reads more naturally after the structure:

```purescript
for items \item ->
  H.liftEffect $ log item.name
```


---

## 4. Discard results deliberately

When you traverse for effect alone, use `traverse_` or `for_`.

```purescript
traverse_ removeFile tempFiles
```

Not:

```purescript
void $ traverse (\f -> removeFile f) tempFiles
```

The underscore variants are not merely cosmetic. `traverse` must retain every result to build the output structure; `traverse_` is free to discard each result as it goes. `void $ traverse` builds an `Array Unit` and then throws it away.

The same applies throughout the standard libraries. Prefer `when` over `void $ if`, `for_` over `void $ for`. Where the library offers a variant that matches your intent, use it. The reader should not have to subtract the parts you did not mean.


---

## 5. Newtype what you mean

A type alias documents intent for the reader. A newtype enforces it through the compiler.

```purescript
-- A type alias. The compiler sees Int everywhere.
type NodeID = Int
type LinkID = Int

addEdge :: NodeID -> NodeID -> LinkID -> Graph -> Graph
-- Nothing prevents: addEdge linkId nodeId nodeId graph
```

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

The runtime cost is zero — newtypes are erased during compilation. The development cost is small: a declaration, a constructor, and a few derived instances. The return is that an entire class of argument-transposition bugs becomes impossible.

The question to ask is not "do I need a newtype here?" but "would swapping this value with another value of the same underlying type be a bug?" If the answer is yes, the type alias is a comment where you needed a guard rail.

A common situation in a real codebase: `NodeID` appears as a type alias in six modules across two packages. Some modules use `Int` directly, some use the alias, and the compiler treats them identically. A newtype in one shared location would have caught the inconsistency at the point it was introduced.


---

## 6. Let the compiler write the instances

PureScript can derive many common instances for you. This is one of the things that makes newtypes cheap in practice — you get the behaviour you need without writing or maintaining the code.

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
data Severity = Info | Warning | Error

derive instance Eq Severity
derive instance Ord Severity
```

The derived `Ord` follows constructor order — `Info < Warning < Error` — which is why thoughtful constructor ordering matters. If you want a different ordering, write the instance by hand, but know that you are making an affirmative choice.

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

## 7. Impose structure before you impose convention

When a value can only be one of a known set of alternatives, represent it as a sum type — not as a `String` you validate, and not as a `Boolean` you remember the meaning of.

```purescript
-- Convention-dependent: what does `true` mean?
setVisibility :: String -> Boolean -> Effect Unit

-- The call site is opaque:
setVisibility "sidebar" true
```

```purescript
-- Structure-dependent: the type answers the question.
data Element = Sidebar | Toolbar | StatusBar
data Visibility = Visible | Hidden

setVisibility :: Element -> Visibility -> Effect Unit

-- The call site documents itself:
setVisibility Sidebar Visible
```

The String-and-Boolean version requires the reader to know (or discover) what `"sidebar"` and `true` mean in this context. The ADT version requires them to know nothing beyond the types. And when someone adds a new element or a third visibility state (`Collapsed`), every call site that needs updating will fail to compile.

The same principle applies to intermediate representations. If your program passes around a `String` that can be `"left"`, `"right"`, or `"center"`, and somewhere validates it — that validation is an admission that the type is wrong.

```purescript
-- The validation is doing the type system's job.
align :: String -> HTML -> HTML
align s = case s of
  "left"   -> ...
  "right"  -> ...
  "center" -> ...
  _        -> ... -- what goes here?

-- Let the type system do its own job.
data Alignment = Left | Right | Center

align :: Alignment -> HTML -> HTML
align = case _ of
  Left   -> ...
  Right  -> ...
  Center -> ...
```


---

## 8. PureScript is strict; do not import lazy habits

PureScript evaluates strictly, left to right. Code ported from Haskell or written with Haskell intuitions can silently do more work than intended.

**Unused bindings are not free.** In Haskell, `let x = expensiveComputation in if flag then x else 0` never evaluates `expensiveComputation` when `flag` is false. In PureScript, it always does.

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

**Infinite structures do not work.** There is no `Data.List.iterate` that produces values on demand. If you want a stream, you need an explicit lazy type or a generator pattern.

**`foldl` vs `foldr`.** In Haskell, `foldr` is often preferred because laziness lets it short-circuit. In PureScript, `foldl` is the natural choice for strict left-to-right accumulation, and `foldr` should be chosen only when the algebra requires right-association (building a list, for instance). Picking the wrong fold does not produce wrong results — but it can produce unnecessary intermediate allocations.


---

# De Gustibus

These are matters where reasonable PureScript programmers differ. We present the cases without ruling.


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
