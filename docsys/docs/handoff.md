# Handoff: read this first in a new chat

Last updated: 2026-11-14. Repository: the private GitHub repo `PKing70/sdk-docsys-poc`, branch `main`.

## What this is

`docsys/` is a documentation system added next to an unmodified copy of the Splunk Python SDK. When the
SDK's public API changes, it works out which docs are affected, drafts concept and how-to pages and
runnable examples with a model, keeps the example code in separate, automatically checked files that pages pull in at
build time, and runs a bounded quality loop that produces a justification report for each page. It
builds one site that combines those guides with the existing Sphinx API reference.

## Start here

Keep one permanent local clone of the repository (suggested: `~/sdk-docsys-poc`) and start every
chat from its `docsys/` folder, so no chat needs to re-clone or paste files. Before each chat, switch
to `main` and run `git pull`. Make changes on a branch.

Also read `docs/handoff-addendum.md`. It records design decisions made after this file was written.
`docsys/CLAUDE.md` tells a new chat to read both files, so a chat started in `docsys/` picks them up
without a starter prompt.

Two kinds of chats can follow this one:

- **A pitch or understanding chat** (explaining the project, drill-down questions, slides). Start it
  in the clone and read this file and `docs/overview/one-pager.md`. Nothing needs to run.
- **A build chat** (changing code, running tests, finishing v0.1). Same clone. If it does not exist
  yet, create it once:

```bash
git clone git@github.com:PKing70/sdk-docsys-poc.git ~/sdk-docsys-poc
cd ~/sdk-docsys-poc/docsys
uv sync --python 3.13 --extra dev --extra reference --extra llm
uv run pytest -q          # expect 43 passed
uv run sdkdocsys check    # deterministic gates, no model needed
```

## Where things are

| Need | File |
|---|---|
| Requirements, architecture, quality loop | `docsys/docs/requirements.md`, `architecture.md`, `quality-loop.md` |
| Roadmap and v0.2 ideas | `docsys/docs/roadmap.md` |
| What we reuse, adapt, or build, and why | `docsys/docs/reuse-decisions.md` |
| Non-technical briefs for pitches | `docsys/docs/overview/` |
| SDK documentation errors we found | `docsys/reports/sdk-doc-findings.md` |
| The doc plan | `docsys/manifest.toml` |
| Quality thresholds | `docsys/quality.toml` |

## Credentials and model access

- Never put a key in a file, a command line, or the repo. A secret-scan test enforces this.
- The personal Anthropic key lives in the macOS Keychain item `docsys-anthropic`. Run anything that
  needs it through `docsys/bin/with-key`, for example `bin/with-key uv run sdkdocsys review`.
- Do not read the user's clipboard or load a secret for them unless they ask for that exact thing.
  Give setup steps and let them run the commands. This is a standing preference.
- The personal key is funded with $20 and auto-reload is off. About $1.3 had been used at this point.
  Every model-using command prints a usage line, so spend is visible.
- The corporate route for model access is pending an access-group approval. Until then, use the
  personal key. The provider interface is swappable (`llm.py`), and the corporate route needs only a
  token and a gateway URL.
- Do not add the key to GitHub secrets yet. The workflow would run the model on every push.

## Decisions already made

- The SDK stays unmodified. All additions live in `docsys/` and one workflow file. The first two
  commits show this: the unmodified SDK, then our additions.
- Code examples are separate `.py` files with named regions, pulled into pages by the `coderef`
  directive. Pages contain no embedded code.
- Quality has gates (block acceptance) and advisory checks (lower the score). A skipped check is
  reported as skipped, never as passed.
- Output goes to two destinations later: reference to GitHub Pages, guides to the developer site,
  which is Markdown-sourced. See the roadmap.
- Commits use the GitHub noreply address, not a work email. Push only when the user says so.

## State of v0.1

Done: API snapshot and diff, change routing, `coderef`, deterministic checks, the reviewer, the bounded
loop with reports, five examples and five guides, the read-only `review` command, a non-destructive loop and `generate` that write proposals to
`proposed/` (pages scored against the same run's example proposals) plus `adopt` to apply them with
rollback on any new gate failure, the usage meter, tests,
a secret scan, and the private repo.

Not done:
- No from-scratch generation run has been done with a real model.
- Examples have never run against a live Splunk. The SDK's compose file auto-accepts a license, so the
  user must decide first.
- The last small edits to three files were not re-reviewed by the model.
- CI cost controls, partly done: with a key, `sdkdocsys ci --changed-from REF` limits model review to
  artifacts affected by the API diff or edited since REF (page, example, or a page citing an edited
  example), and the workflow uploads proposals (`SDKDOCSYS_PROPOSED`) so model output is kept. Not
  done: cancel superseded runs, cache reviews of unchanged artifacts, a per-run spend cap, and a
  spend limit in the Anthropic Console (the user sets that one). No key is in GitHub secrets yet.
- The corporate model provider has only run against a fake client.

## Gotchas learned

- Pushing from a shallow clone failed. The history was rebuilt as an unmodified baseline commit plus ours.
- The SDK's own workflows are disabled in the repo settings, and its Dependabot config was removed.
- The reviewer only sees what we give it: signatures, docstrings for the symbols a page names (stored
  up to 4,000 characters, was 1,200), and each cited example file whole. Never SDK function bodies, by
  design. Claims it cannot verify go to a "needs SME confirmation" list, not the score.
- Some SDK docstrings are wrong, which can make accurate content score low on accuracy.

## How the user likes to work

Plain explanations first, with short answers. Ask before publishing or pushing anything. Prefer
checking claims against the source over trusting a score. The user is cost-conscious about long chats,
so prefer fresh, short sessions and use background agents for large reads.

## Next steps, in order

1. Pitch briefs: manager and writer briefs are written (`docs/overview/manager-brief.md`,
   `writer-brief.md`). Review them with their audiences and revise.
2. Finish v0.1: non-destructive loop, first generation run with the usage meter, CI cost controls.
3. Decide on live example validation and the license question.
4. Fold in the user's feature list from the roadmap parking lot, then plan v0.2.

## Starter prompts for the new chat

For a pitch or understanding chat, started in the clone:

> I'm continuing the docsys project. Read `docsys/docs/handoff.md`, `docsys/docs/handoff-addendum.md`,
> and `docsys/docs/overview/one-pager.md`. Use only those unless I name more. Today I want to
> <say what you want to do>.

For a build chat, from the cloned folder:

> I'm continuing the docsys project. Read `docsys/docs/handoff.md` first, then
> `docsys/docs/overview/one-pager.md`. Don't read other files unless needed. Today I want to
> <say what you want to do>.
