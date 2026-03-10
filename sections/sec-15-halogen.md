# XV. Halogen patterns

Halogen is PureScript's most widely used UI framework. These entries cover patterns specific to Halogen's component model — not general PureScript style, but idioms that make Halogen code cleaner and more maintainable.


---


## 155. Prefer render functions over components

Not every piece of reusable HTML needs to be a Halogen component. A component carries overhead: a `State` type, an `Action` type, an `initialState`, a `handleAction`, lifecycle management, and a slot type at every use site. If the piece in question has no independent state and raises no actions, all of that machinery is waste.

A plain render function is simpler:

```purescript
-- A render function: no state, no lifecycle, no slot type
statusBadge :: forall w i. Status -> HH.HTML w i
statusBadge = case _ of
  Active   -> HH.span [ HP.class_ (ClassName "badge-active") ] [ HH.text "Active" ]
  Inactive -> HH.span [ HP.class_ (ClassName "badge-inactive") ] [ HH.text "Inactive" ]
```

Use a component when you need internal state, subscriptions, or effects in response to user interaction. Use a render function -- a value or function returning `HTML` -- when you are simply translating data into markup. The distinction is not about size; it is about whether the thing has behaviour of its own.


---


## 156. Store minimal canonical state; derive the rest in render

If a value can be computed from other state, compute it in `render`. Do not store it alongside the data it depends on.

```purescript
-- Derived state stored explicitly: can go stale
type State =
  { items :: Array Item
  , selectedItems :: Array Item   -- derived from items + selection
  , totalPrice :: Number          -- derived from selectedItems
  }

-- Minimal canonical state: nothing to synchronise
type State =
  { items :: Array Item
  , selectedIds :: Set ItemId
  }

render :: State -> HTML
render state =
  let
    selectedItems = filter (\i -> Set.member i.id state.selectedIds) state.items
    totalPrice = foldl (\acc i -> acc + i.price) 0.0 selectedItems
  in
    ...
```

Every piece of derived state is a synchronisation obligation. When you update `items`, you must remember to update `selectedItems` and `totalPrice`. Forget one, and the UI shows stale data with no compiler warning.

The canonical state is the smallest set of values from which everything else can be recomputed. Store that, and let `render` do the rest.


---


## 157. Model component actions as what happened, not what to do

Name actions after events, not effects. An action is a record of something that occurred; the handler decides what it means.

Prefer:

```purescript
data Action
  = SearchTermChanged String
  | ResultClicked ResultId
  | FilterToggled FilterType
  | PageLoaded
```

Over:

```purescript
data Action
  = UpdateSearchResults String
  | NavigateToResult ResultId
  | SetFilterAndRefresh FilterType
  | FetchInitialData
```

The first set describes what the user did. The second prescribes what the system should do, embedding implementation decisions in the type. When requirements change -- perhaps `FilterToggled` should now also log an analytics event -- the event-style action accommodates the change in the handler without renaming the action. The imperative-style action, `SetFilterAndRefresh`, must either be renamed (breaking every reference) or become a lie.

Actions named after events also compose better with parent-child communication. A parent receiving `ResultClicked` can decide independently what that means. A parent receiving `NavigateToResult` has already been told what to do.


---


## 158. Use the ReaderT pattern for non-trivial Halogen apps

As applications grow, components need access to shared resources: API clients, configuration, authentication state. Threading these as props through every layer of the component tree does not scale.

The `ReaderT` pattern, demonstrated extensively in Real World Halogen, provides a principled alternative. Your application monad carries an environment, and any component can read from it.

```purescript
newtype AppM a = AppM (ReaderT Env Aff a)

derive newtype instance Functor AppM
derive newtype instance Apply AppM
derive newtype instance Applicative AppM
derive newtype instance Bind AppM
derive newtype instance Monad AppM
derive newtype instance MonadEffect AppM
derive newtype instance MonadAff AppM

instance MonadAsk Env AppM where
  ask = AppM ask
```

For global mutable state — the current user, a notification queue — prefer `halogen-store` over rolling your own `ReaderT` with a `Ref`. The library handles subscription, notification of changes, and cleanup. Reserve manual `ReaderT` + `Ref` for cases where you need fine-grained control over when subscribers are notified. (Thomas Honeyman)

See also entry 92 on newtypes for transformer stacks, and entry 165 on the capability pattern that builds on this foundation.


---
