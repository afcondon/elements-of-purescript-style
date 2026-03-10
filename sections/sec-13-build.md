# XIII. The build

Spago is PureScript's build tool and package manager. It is opinionated about project structure and dependency management, and working with those opinions — rather than against them — saves time and frustration.


---


## 137. Use a package set for reproducible builds

A *package set* is a fixed snapshot of the registry — a known-good collection of packages at specific versions, tested together. Most projects should use one.

```yaml
workspace:
  packageSet:
    registry: 63.2.0
```

Every developer and CI run resolves to the same versions. If a package was published after your snapshot, it does not exist as far as Spago is concerned — bump the registry version or add the package to `extraPackages`.


---


## 138. Use the solver when the package set is not enough

The *solver* resolves version ranges dynamically, like npm or Cargo, finding versions that satisfy all constraints. It activates when you add `extraPackages` to your workspace.

```yaml
workspace:
  packageSet:
    registry: 63.2.0
  extraPackages:
    some-new-lib:
      git: https://github.com/user/some-new-lib.git
      ref: main
```

The solver gives flexibility — you can use packages or versions not in the set. The trade-off is that resolution is no longer fully deterministic from the package set alone; the lock file becomes essential for reproducibility.

The most common source of "package not found" errors is confusion about which mode is active. If you are on a package set and a package is missing, either bump the registry version or add the package to `extraPackages`.


---


## 139. Use workspace.extraPackages for local and unpublished dependencies

When you depend on a local checkout, a git repository, or a package not yet in the registry, add it under `workspace.extraPackages` in your root `spago.yaml`. Do not hack the package set, symlink directories into `.spago`, or copy source files into your tree.

```yaml
workspace:
  packageSet:
    registry: 63.2.0
  extraPackages:
    # A local checkout (sibling directory):
    hylograph-canvas:
      path: ../purescript-hylograph-libs/canvas

    # A git dependency at a specific commit:
    some-experimental-lib:
      git: https://github.com/user/some-experimental-lib.git
      ref: a1b2c3d
      subdir: lib
```

The `path:` form is for local directories — monorepo siblings, packages under active development, forks with local patches. The `git:` form is for remote repositories pinned to a ref. Both integrate cleanly with the lock file and dependency resolution. Both are visible in one place, not scattered across shell scripts or build hacks.

When the package is eventually published to the registry and appears in a package set you adopt, remove the `extraPackages` entry. The override has served its purpose.


---


## 140. Keep spago.yaml minimal and let the lock file do its job

`spago.yaml` declares your intent: which packages you depend on, which version ranges you accept, which registry snapshot you use. `spago.lock` records what was actually resolved: exact versions, exact hashes, the full dependency tree.

```yaml
# spago.yaml — declare intent:
package:
  name: my-app
  dependencies:
    - aff
    - halogen
    - argonaut-codecs
```

Check in the lock file. Do not pin exact versions in `spago.yaml` unless you have a specific, documented reason — that is the lock file's job. Pinning versions in `spago.yaml` defeats the flexibility of range resolution and creates two sources of truth about which version is in use.

When you run `spago install`, Spago resolves dependencies and updates the lock file. When a colleague clones the repo and runs `spago build`, the lock file ensures they get the same versions you did. This is the same contract as `package-lock.json` or `Cargo.lock`. Trust it.


---


## 141. Spago supports monorepo workspaces

If you are developing tightly coupled packages — a library and the application that uses it, or a family of related libraries — Spago's workspace feature lets you manage them in a single repository. A root `spago.yaml` defines the workspace — the package set, extra packages, and shared configuration. Sub-directories each have their own `spago.yaml` with a `package:` stanza declaring their name, dependencies, and source globs.

```yaml
# Root spago.yaml
workspace:
  packageSet:
    registry: 63.2.0
  extraPackages: {}

# packages/canvas/spago.yaml
package:
  name: hylograph-canvas
  dependencies:
    - effect
    - web-dom
  publish:
    version: 0.3.0
    license: MIT
```

Each package can depend on its siblings by name, and Spago resolves the internal dependency graph. You get one lock file, one package set, and a single `spago build` that builds everything.

This is one option for organising multi-package projects. Separate repositories with their own package sets and CI pipelines are a reasonable alternative, especially when packages have independent release cycles and maintainers. The workspace approach works well when packages evolve together and you want to test cross-cutting changes in a single commit.


---


## 142. spago bundle vs spago build: know the difference

`spago build` compiles PureScript source to ES modules in the `output/` directory. Each PureScript module becomes a directory with an `index.js` file. This is sufficient for libraries, for Node applications that can consume ES module imports, and for any downstream tool that handles bundling itself.

`spago bundle` does everything `spago build` does and then runs esbuild to produce a single JavaScript file — a bundle suitable for loading in a browser via a `<script>` tag, or for deploying as a single-file Node script.

```yaml
# spago.yaml bundle configuration for a browser app:
package:
  name: my-app
  bundle:
    module: Main
    outfile: dist/bundle.js
    platform: browser
```

If your HTML loads `bundle.js`, you need `spago bundle`. If you are writing a library consumed by other PureScript packages, `spago build` is sufficient and `spago bundle` is unnecessary. Getting this wrong produces either "module not found" errors in the browser (because the browser cannot resolve ES module imports from `output/`) or an unnecessarily large bundle in Node (because esbuild inlined dependencies you did not need to inline).


---


## 143. Browser bundles need platform: browser

When bundling for the browser, your `spago.yaml` bundle configuration must include `platform: browser`. Without it, esbuild defaults to the Node platform and may leave in Node-specific imports — `fs`, `path`, `process`, `buffer` — that do not exist in the browser.

```yaml
# Correct:
package:
  bundle:
    module: Main
    platform: browser
    outfile: dist/app.js

# Missing platform — will default to node:
package:
  bundle:
    module: Main
    outfile: dist/app.js
```

The resulting error is often cryptic: a `ReferenceError: process is not defined` or `require is not a function` at runtime, not at build time. You stare at your PureScript source looking for the Node dependency and find nothing, because the import was introduced by a transitive JavaScript dependency that esbuild chose not to polyfill. The fix is one line in the config.


---


## 144. Set bundle.module to your entry point

`spago bundle` needs to know which module contains your application's `main` function. Set `bundle.module` in your `spago.yaml`:

```yaml
package:
  bundle:
    module: Main
    outfile: dist/bundle.js
    platform: browser
```

If omitted, the bundler may produce an empty file, a file that defines modules but never calls `main`, or an error that does not clearly indicate the problem. The fix is always the same: tell the bundler where to start.

This is especially easy to overlook in monorepo setups where each package has its own entry point. Each package that produces a bundle needs its own `bundle.module` declaration.


---


## 145. Do not import from output/ in your source

The `output/` directory is a build artifact generated by the PureScript compiler. It is not part of your source tree.

```purescript
-- Do not do this:
foreign import myHelper :: forall a. a -> Effect Unit
-- with an FFI file that says:
-- import { someFunction } from "../../output/Other.Module/index.js"

-- Do this:
import Other.Module (someFunction)
```

Importing from `output/` in your PureScript source or FFI files creates a circular dependency between the build system and your code. The `output/` directory may not exist yet when the compiler first runs. Its internal structure is a compiler implementation detail that may change between PureScript versions. And it defeats incremental compilation, because changes to one module now invalidate another through a path the compiler does not track.

Use PureScript imports for PureScript dependencies. If you need to call JavaScript, use the FFI mechanism — a `.js` file alongside your `.purs` file. Let the compiler and bundler resolve the paths.


---


## 146. Clear output/ when things make no sense

Incremental compilation is a tremendous convenience until it produces a stale artifact. This happens most often after renaming modules, changing the package set, switching git branches that reorganised the source tree, or upgrading the compiler.

The symptoms are distinctive: duplicate module errors for modules that exist only once, type errors that contradict what you can see in the source, "module not found" for a module you just created. The common thread is that the error does not match reality.

```bash
rm -rf output .spago
spago build
```

This costs thirty seconds on a clean build and saves thirty minutes of debugging a phantom. It is not a sign of a broken tool — incremental compilation systems in every language have this failure mode. The important thing is to recognise the symptoms and reach for the fix without guilt.

If you find yourself clearing `output/` routinely (more than once a week), something else is wrong — likely a build script that modifies source files in place, or a symlink that confuses the watcher.


---


## 147. The registry version must match what the solver sees

Your workspace's `packageSet.registry` field specifies a snapshot of the PureScript registry. Only packages published at or before that snapshot are visible to the resolver.

```yaml
workspace:
  packageSet:
    registry: 63.2.0  # Packages published after this snapshot are invisible.
```

A package that appears on Pursuit, that you can browse and read the documentation for, may nonetheless fail to resolve if it was published after your registry snapshot. The error — typically "package not found" or "no version satisfying constraint" — gives no hint that the issue is temporal.

The fix is either to bump the registry version to a snapshot that includes the package, or to add the package to `extraPackages` with an explicit source. When in doubt, check the package's publish date against your registry version.


---


## 148. Use spago ls packages and spago ls deps to debug resolution

When a package is "not found" and you are not sure why, two commands answer most questions:

```bash
# What packages does my current package set contain?
spago ls packages

# What does my resolved dependency tree look like?
spago ls deps
```

`spago ls packages` shows every package visible in your current package set, with its version. If the package you want is not listed, it is not in your snapshot — see entry 73. `spago ls deps` shows the resolved dependency tree for your project, including transitive dependencies. If a package appears in `ls packages` but not in `ls deps`, you have not added it to your `dependencies` list.

These commands are faster and more reliable than reading the Spago source, guessing at resolution logic, or asking in Discord. Use them before you debug.


---
