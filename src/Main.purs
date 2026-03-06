-- | Ecosystem Guide — sigil rendering entry point.
-- |
-- | Detects which containers exist on the current page and
-- | renders the appropriate type signatures into them.
module Main where

import Prelude

import Data.Array (foldM)
import Data.Maybe (Maybe(..))
import Effect (Effect)
import Effect.Console (log)

import Sigil.Html as Sigil
import Sigil.Parse (parseToRenderType)
import Sigil.Types (RenderType)

main :: Effect Unit
main = do
  log "[Ecosystem] Rendering sigil content"
  foldM (\_ r -> r) unit renders
  log "[Ecosystem] Done"

-- | All renders: each tries its selector, silently skips if absent.
renders :: Array (Effect Unit)
renders =
  -- Landing page hero
  [ renderSig "#sigil-hero-bind" "bind" "m a -> (a -> m b) -> m b"

  -- Type classes page: Functor tower
  , renderClass "#sigil-class-functor" "Functor" ["f"]
      [ m "map" "(a -> b) -> f a -> f b" ]
  , renderClass "#sigil-class-apply" "Apply" ["f"]
      [ m "apply" "f (a -> b) -> f a -> f b" ]
  , renderClass "#sigil-class-applicative" "Applicative" ["f"]
      [ m "pure" "a -> f a" ]
  , renderClass "#sigil-class-bind" "Bind" ["m"]
      [ m "bind" "m a -> (a -> m b) -> m b" ]
  , renderClass "#sigil-class-monad" "Monad" ["m"] []

  -- Algebraic tower
  , renderClass "#sigil-class-semiring" "Semiring" ["a"]
      [ m "add" "a -> a -> a", m "mul" "a -> a -> a", mn "zero", mn "one" ]
  , renderClass "#sigil-class-ring" "Ring" ["a"]
      [ m "sub" "a -> a -> a" ]
  , renderClass "#sigil-class-euclideanring" "EuclideanRing" ["a"]
      [ m "div" "a -> a -> a", m "mod" "a -> a -> a" ]

  -- Eq & Ord
  , renderClass "#sigil-class-eq" "Eq" ["a"]
      [ m "eq" "a -> a -> Boolean" ]
  , renderClass "#sigil-class-ord" "Ord" ["a"]
      [ m "compare" "a -> a -> Ordering" ]

  -- Semigroup & Monoid
  , renderClass "#sigil-class-semigroup" "Semigroup" ["a"]
      [ m "append" "a -> a -> a" ]
  , renderClass "#sigil-class-monoid" "Monoid" ["a"]
      [ mn "mempty" ]

  -- Foldable & Traversable
  , renderClass "#sigil-class-foldable" "Foldable" ["f"]
      [ m "foldr" "(a -> b -> b) -> b -> f a -> b"
      , m "foldl" "(b -> a -> b) -> b -> f a -> b"
      , m "foldMap" "(a -> m) -> f a -> m"
      ]
  , renderClass "#sigil-class-traversable" "Traversable" ["t"]
      [ m "traverse" "(a -> m b) -> t a -> m (t b)"
      , m "sequence" "t (m a) -> m (t a)"
      ]
  ]

-- | Render a standalone signature into a selector.
renderSig :: String -> String -> String -> Effect Unit
renderSig sel name sig =
  case parseToRenderType sig of
    Just ast -> Sigil.renderSignatureInto sel { name, ast, typeParams: [], className: Nothing }
    Nothing -> log $ "[Ecosystem] Parse failed: " <> name

-- | Render a class declaration into a selector.
renderClass :: String -> String -> Array String -> Array { name :: String, ast :: Maybe RenderType } -> Effect Unit
renderClass sel name typeParams methods =
  Sigil.renderClassDeclInto sel { name, typeParams, superclasses: [], methods }

-- | Method with a parseable signature.
m :: String -> String -> { name :: String, ast :: Maybe RenderType }
m name sig = { name, ast: parseToRenderType sig }

-- | Method with name only (no signature).
mn :: String -> { name :: String, ast :: Maybe RenderType }
mn name = { name, ast: Nothing }
