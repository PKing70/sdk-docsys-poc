# Docsys: a documentation maintenance system for the Splunk Python SDK

`docsys/` has been added next to the SDK. It never edits SDK files. When the SDK's public API
changes, it works out which docs are affected, drafts conceptual and procedural pages plus
runnable examples, measures their quality in a bounded loop, and builds one site that
combines those guides with the existing Sphinx API reference.

## What is and is not changed here

The first commit in this repository is the upstream SDK, unmodified. The second adds
`docsys/` and one workflow. `git diff <first> <second>` shows exactly that. One later commit
removes the SDK's `.github/dependabot.yaml`, because dependency-update pull requests for a
private copy that is not shipped are noise, and merging them would change the SDK's pins.
The SDK's own workflows (lint, test, appinspect, CD) are disabled in the repository settings.

As I refine this proof, we should be able to get all further changes out of PR history.

## Quick start

```bash
cd docsys
uv sync --python 3.13 --extra dev --extra reference     # add --extra llm for model access
uv run sdkdocsys check          # deterministic quality gates, no model, no network
uv run sdkdocsys loop           # gates + justification reports in reports/
uv run sdkdocsys build          # site in _build/html
uv run pytest                   # the system's own tests
```

Model-assisted generation and review need one of:

- `LLM_GATEWAY_TOKEN` and `LLM_GATEWAY_URL` (a Bedrock-compatible gateway that accepts a
  short-lived bearer token) with the `bedrock` extra. Optional: `SDKDOCSYS_MODEL` (default
  `anthropic.claude-sonnet-4-6`). Pass the token like any secret, never in a file.
- `ANTHROPIC_API_KEY` with the `llm` extra.

`SDKDOCSYS_PROVIDER=bedrock_proxy|anthropic` forces one when both are set. Without
credentials everything deterministic still runs, and reports say plainly that the model
review was skipped.

## Credentials

Never put a key in a file, a command line, or this repo (yet). Use the macOS Keychain:

1. One time, in a terminal. You paste the key at the prompt, so it never shows in history:
   `security add-generic-password -a "$USER" -s docsys-anthropic -U -w`
2. Run anything that needs the key through the wrapper, which passes it to that one process:
   `bin/with-key uv run --no-config sdkdocsys review`
3. Rotate by repeating step 1 (`-U` updates the item). Delete it with
   `security delete-generic-password -a "$USER" -s docsys-anthropic`.

For GitHub Actions, set the key as a repository secret from the clipboard, so it never touches
a file: `pbpaste | gh secret set ANTHROPIC_API_KEY --repo <owner>/<repo>`. The workflow reads
`secrets.ANTHROPIC_API_KEY`. `tests/test_no_secrets.py` fails if anything credential-shaped
is in the project, and `.gitignore` excludes `.env` and `*.pem`.

If/when I get ai-devx tokens to use instead, I will change the cred model and perhaps add 
them to github secrets, making the system devops automatable from a workflow. In the meantime,
I am running against my personal credits with my personal key (judiciously) and there's no
way to "run" directly from this repo yet. As designed; so only I burn my credits locally as I 
see fit.

## Commands

| Command | What it does |
|---|---|
| `sdkdocsys snapshot [--update]` | Count public API symbols; `--update` rewrites the baseline |
| `sdkdocsys diff` | API changes since the baseline, and which pages and examples they affect |
| `sdkdocsys generate [--all] [--page ID]` | Model drafts affected examples, then pages |
| `sdkdocsys check` | Deterministic gates only. Exit 1 on any gate failure |
| `sdkdocsys review` | Read-only model review of files as they are; writes `reports/review/`. Never rewrites |
| `sdkdocsys loop` | Measure, revise (bounded), write `reports/<id>.md` and `reports/SUMMARY.md` |
| `sdkdocsys build` | Stage SDK `docs/*.rst` plus guides, run Sphinx |
| `sdkdocsys ci [--update-baseline]` | diff, generate if needed, loop, build |

## Layout

| Path | Role |
|---|---|
| `manifest.toml` | The doc plan: pages, examples, what each covers, key symbols |
| `quality.toml` | Thresholds for every check and for the loop budget |
| `content/` | Markdown pages (no code fences; code is pulled in) |
| `examples/` | The runnable example scripts, the single source of the code |
| `state/api_snapshot.json` | Public API as of the last documented SDK state |
| `reports/` | Per-artifact justification reports and a summary |
| `src/sdkdocsys/` | The tool |
| `sphinx/conf.py` | Sphinx config for the combined site |
| `docs/` | Requirements, architecture, quality loop explainer |

See [docs/requirements.md](docs/requirements.md), [docs/architecture.md](docs/architecture.md),
and [docs/quality-loop.md](docs/quality-loop.md).

## Writing a page that references code

Use a MyST colon fence. The page contains no code:

```text
:::{coderef} examples/oneshot_search.py
:region: search
:::
```

In the example file, wrap the lines you want between `# region: search` and
`# endregion: search`. The build includes those lines and links back to the file.
