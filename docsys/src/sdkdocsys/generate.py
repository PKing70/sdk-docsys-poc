"""Content generation: choose what to (re)write from an API diff, then prompt the model.

The model writes Markdown prose that references code through ``coderef`` and writes
example scripts as separate ``.py`` files. It never writes code fences into pages.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from . import api, coderef
from .llm import LLM, strip_wrapping_fence
from .quality import Report, api_facts


def load_manifest(path: Path) -> dict:
    data = tomllib.loads(path.read_text())
    data.setdefault("page", [])
    data.setdefault("example", [])
    return data


def affected(manifest: dict, changed: set[str] | None) -> tuple[list[dict], list[dict]]:
    """Pages and examples whose ``covers`` intersect the changed symbols.

    ``changed=None`` means "everything" (no baseline yet, or ``--all``).
    """

    def hit(entry: dict) -> bool:
        return changed is None or any(api.covers(entry["covers"], s) for s in changed)

    return [p for p in manifest["page"] if hit(p)], [e for e in manifest["example"] if hit(e)]


STYLE = """\
Voice and style: second person, active voice, present tense, short sentences. Use hyphens,
never em-dashes. Do not use the words simply, just, easily, obviously, clearly. Explain why,
not only how. Name SDK symbols in backticks using forms like `Jobs.oneshot` or
`splunklib.client.connect`; only name symbols that appear in the API FACTS."""

PAGE_SYSTEM = f"""You write documentation pages for the Splunk Python SDK as MyST Markdown.
{STYLE}
Hard rules:
- No fenced code blocks of any kind for code. Code lives in example files and is pulled in with
  a colon-fence directive, exactly:
:::{{coderef}} examples/<file>.py
:region: <region>
:::
- Only reference example files and regions listed in EXAMPLES.
- Exactly one H1. concept pages need sections titled "How it works" and "When to use".
  procedure pages need "Prerequisites", "Steps" (numbered), and "Verify".
- Name every key symbol in backticks. Do not invent APIs. Output only the page."""

EXAMPLE_SYSTEM = f"""You write short runnable example scripts for the Splunk Python SDK.
{STYLE}
Hard rules:
- One focused scenario that teaches something real, at most 80 lines, standard library plus
  splunklib only, copy/paste runnable.
- Module docstring with lines starting "Goal:", "Prerequisites:" and "Run:".
- Connection settings from environment variables (SPLUNK_HOST, SPLUNK_PORT, SPLUNK_USERNAME,
  SPLUNK_PASSWORD). Never hard-code credentials.
- def main() plus an if __name__ == "__main__" guard; nothing runs at import.
- Mark the teachable parts with "# region: name" and "# endregion: name" comment pairs.
- Only call API that appears in API FACTS or that you are certain exists. Clean up anything the
  script creates. Output only the Python file."""


def _example_listing(page: dict, manifest: dict, root: Path) -> str:
    rows = []
    by_id = {e["id"]: e for e in manifest["example"]}
    for ex_id in page.get("examples", []):
        ex = by_id.get(ex_id)
        if not ex:
            continue
        f = root / ex["path"]
        regions = coderef.list_regions(f.read_text()) if f.is_file() else []
        rows.append(f"- {ex['path']} regions={regions} goal={ex.get('goal', '')}")
    return "\n".join(rows) or "(none)"


def generate_page(
    llm: LLM, page: dict, manifest: dict, snap: api.Snapshot, root: Path, current: str | None
) -> str:
    prompt = (
        f"PAGE id={page['id']} kind={page['kind']} title={page['title']!r}\n"
        f"BRIEF: {page.get('brief', '')}\n"
        f"KEY SYMBOLS: {page.get('key_symbols', [])}\n\n"
        f"API FACTS:\n{api_facts(snap, page['covers'])}\n\n"
        f"EXAMPLES:\n{_example_listing(page, manifest, root)}\n\n"
        + (f"CURRENT PAGE (update it, keep what is still correct):\n{current}\n" if current else "")
    )
    return strip_wrapping_fence(llm.complete(PAGE_SYSTEM, prompt, max_tokens=3500))


def generate_example(llm: LLM, ex: dict, snap: api.Snapshot, current: str | None) -> str:
    prompt = (
        f"EXAMPLE id={ex['id']} file={ex['path']}\nGOAL: {ex.get('goal', '')}\n"
        f"SYMBOLS TO EXERCISE: {ex.get('uses', [])}\n\n"
        f"API FACTS:\n{api_facts(snap, ex['covers'])}\n\n"
        + (f"CURRENT FILE (update it, keep region names stable):\n{current}\n" if current else "")
    )
    return strip_wrapping_fence(llm.complete(EXAMPLE_SYSTEM, prompt, max_tokens=2500))


def _feedback(report: Report, issues: list[str]) -> str:
    rows = [
        f"- [{c.severity}] {c.name}: value={c.value} threshold={c.threshold} {c.detail}"
        for c in report.failing
    ]
    rows += [f"- [reviewer] {i}" for i in issues]
    return "\n".join(rows) or "- (no specific failures; tighten clarity)"


def revise_page(
    llm: LLM,
    text: str,
    report: Report,
    issues: list[str],
    page: dict,
    manifest: dict,
    snap: api.Snapshot,
    root: Path,
) -> str:
    prompt = (
        "Revise this page to fix every problem listed. Keep correct content. "
        "Output the full page.\n\n"
        f"PROBLEMS:\n{_feedback(report, issues)}\n\n"
        f"API FACTS:\n{api_facts(snap, page['covers'])}\n\n"
        f"EXAMPLES:\n{_example_listing(page, manifest, root)}\n\nPAGE:\n{text}"
    )
    return strip_wrapping_fence(llm.complete(PAGE_SYSTEM, prompt, max_tokens=3500))


def revise_example(
    llm: LLM, text: str, report: Report, issues: list[str], ex: dict, snap: api.Snapshot
) -> str:
    prompt = (
        "Revise this script to fix every problem listed. Keep region names. "
        "Output the full file.\n\n"
        f"PROBLEMS:\n{_feedback(report, issues)}\n\n"
        f"API FACTS:\n{api_facts(snap, ex['covers'])}\n\n"
        f"FILE:\n{text}"
    )
    return strip_wrapping_fence(llm.complete(EXAMPLE_SYSTEM, prompt, max_tokens=2500))
