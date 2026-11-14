# Requirements

Status: v0.1, derived from the project brief. Each requirement has an ID so tests, checks,
and the architecture can point at it.

## Goal

Attach a doc system to the Splunk Python SDK, unchanged, so that SDK changes produce reference
docs (existing Sphinx), plus conceptual and procedural content and runnable scenario examples,
with a bounded quality process that explains why each result is a final draft.

## Functional requirements

| ID | Requirement | Where it lives |
|---|---|---|
| R1 | The SDK source is never modified. The doc system is additive. | `docsys/` only; `git diff upstream/...` over SDK paths stays empty |
| R2 | An SDK change is detected as a diff of its public API. | `api.py`, `sdkdocsys diff` |
| R3 | A change maps to the pages and examples it affects, and only those. | `manifest.toml` `covers`, `generate.affected` |
| R4 | Existing Sphinx reference docs keep working and are published with the guides. | `cli.build_site`, `sphinx/conf.py` |
| R5 | Conceptual pages explain what and why. Procedural pages give goal, prerequisites, numbered steps, verification. | `quality.toml` required sections |
| R6 | Examples are short, scenario-based, copy/paste runnable, and teach more than syntax. | `examples/`, example gates |
| R7 | Code is stored outside page source and pulled in at build time. Pages contain no code fences. | `coderef.py`, `no_embedded_code` gate |
| R8 | Examples are maintained and tested separately from prose. | `check_example`, `tests/` |
| R9 | Quality is measured for prose, code, and coverage. | `quality.py` |
| R10 | Improvement is a bounded loop with a budget and an explicit stop reason. | `loop.py`, `quality.toml [loop]` |
| R11 | Each artifact gets a justification report: what was measured, what changed, why it stopped, what remains and what was not evaluated. | `loop.render_markdown` |
| R12 | The pipeline runs without a model key. Skipped model checks are reported as skipped, never as passed. | `quality.judge` |

## Non-functional requirements

| ID | Requirement |
|---|---|
| N1 | Output stays private. The repository is private; nothing is published without an explicit decision. |
| N2 | Secrets never appear in code or content. Credentials come from the environment. |
| N3 | The generic parts (coderef, quality checks, loop, reports, change routing) stay free of SDK-specific assumptions where that is cheap. |
| N4 | Deterministic checks are fast and need no network. |

## Direction, not yet built: portability

The longer-term goal is a doc generator that applies to other SDKs and to non-SDK products.
That follows the first project working end to end. Planned seams:

- An **extractor adapter** that turns a project into "symbols with signatures". This repository
  has a Python one. Others (OpenAPI, CLI help, other languages) would reuse everything downstream.
- A **project config** carrying voice, name, thresholds, and the manifest location.
- Generic prompts parameterized by that config instead of mentioning one product.

We will extract after a second target shows which parts really vary.

## Out of scope for v0.1

- Changing SDK behavior or its existing reference docs.
- Live execution of examples in CI (needs a Splunk instance and acceptance of Splunk's license).
- Auto-merging generated content without human review.

## Acceptance for v0.1

1. `sdkdocsys check` and `pytest` pass with no network.
2. `sdkdocsys build` produces the combined site without new warnings.
3. Each quality check demonstrably fails on bad input (negative tests).
4. With a model key, `sdkdocsys ci` regenerates only affected artifacts and writes reports.
