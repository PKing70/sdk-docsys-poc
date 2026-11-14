# Architecture

## Flow

```text
SDK change (new commit in splunklib/)
   |
   v
api.snapshot()  --diff-->  state/api_snapshot.json   (what changed in the public API)
   |
   v
generate.affected()   uses manifest.toml `covers`     (which pages/examples are affected)
   |
   v
generate (model)      examples first, then pages      (skipped without a key)
   |
   v
loop (per artifact)   measure -> accept | revise -> measure ...   (bounded)
   |                  writes reports/<id>.md and reports/SUMMARY.md
   v
build                 stage SDK docs/*.rst + content/ -> Sphinx -> _build/html
```

## Components

| Module | Responsibility | Generic or SDK-specific |
|---|---|---|
| `api.py` | Static public-API snapshot and diff using `ast` (no SDK import) | Python-specific; the first extractor adapter |
| `generate.py` | Change routing, prompts, revise helpers | Routing generic, prompts SDK-flavored |
| `coderef.py` | Sphinx directive that includes code regions | Generic |
| `quality.py` | Prose, code, coverage checks and the model rubric | Mostly generic; code checks are Python |
| `loop.py` | Bounded loop, stop reasons, reports | Generic |
| `llm.py` | Model access, optional | Generic |
| `cli.py` | Commands and the staged Sphinx build | Generic shape |

## Key decisions

1. **Additive only.** Everything lives in `docsys/`. The staged build copies SDK `docs/*.rst`
   into a scratch directory; it never writes into the SDK tree.
2. **Static API extraction.** `ast` avoids importing the SDK, so no optional dependencies are
   needed and no code runs. The cost: inherited methods appear on their defining class only
   (for example `Collection.create`, not `Indexes.create`), so manifests name the defining class.
3. **Code is referenced, not embedded.** Regions in `.py` files are the unit of reuse. Files
   are the source of truth rather than gists: one place to version, lint, and test. Gist
   mirroring can be added later without changing pages.
4. **Gates versus advisory.** Gates encode correctness and policy (no hallucinated API, no
   embedded code, runnable shape). Advisory checks shape the score without blocking.
5. **Honest skips.** A check that could not run is `skipped`. A skipped model review yields
   `accepted_unreviewed`, never `accepted`.
6. **Explicit coverage.** `key_symbols` in the manifest must be named in prose and exercised
   by an example. Coverage is a concrete, checkable list, not a vague percentage.

## Known limits

- Method calls on instances cannot be checked statically, so a made-up method on a real object
  passes `splunklib_symbols_exist`. Live execution against Splunk is the real test for that.
- Readability uses a built-in Flesch estimate. It is a rough guide, not a style review.
  Vale or a similar linter is a natural addition.
- The model rubric is only as reliable as the model. It is one signal among several.
- The Sphinx reference depends on the SDK's optional AI packages. The `reference` extra in
  `pyproject.toml` mirrors the SDK's `[ai]` extra and must be kept in sync by hand.
