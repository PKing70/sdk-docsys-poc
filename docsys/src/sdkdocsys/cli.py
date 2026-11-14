"""Command line entry point: ``sdkdocsys <command>``."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import api, generate, loop, quality
from .llm import USAGE, get_llm, usage_summary

ROOT = Path(os.environ.get("SDKDOCSYS_ROOT", Path(__file__).resolve().parents[2]))
REPO = ROOT.parent
BASELINE = ROOT / "state" / "api_snapshot.json"
MANIFEST = ROOT / "manifest.toml"
QUALITY = ROOT / "quality.toml"
REPORTS = ROOT / "reports"
FAIL_STATUSES = {loop.NEEDS_LLM, loop.PLATEAU, loop.EXHAUSTED}


def _current() -> api.Snapshot:
    return api.snapshot(REPO / "splunklib")


def cmd_snapshot(args: argparse.Namespace) -> int:
    snap = _current()
    print(
        f"{len(snap['symbols'])} public symbols, SDK {snap['meta']['sdk_version']} "
        f"@ {snap['meta']['git_commit']}"
    )
    if args.update:
        api.save(snap, BASELINE)
        print(f"baseline written: {BASELINE.relative_to(REPO)}")
    return 0


def cmd_diff(_: argparse.Namespace) -> int:
    snap, base = _current(), api.load(BASELINE)
    d = api.diff(base, snap)
    if base is None:
        print("no baseline: everything counts as changed")
    for kind, items in d.items():
        print(f"{kind}: {len(items)}")
        for s in items[:15]:
            print(f"  {s}")
        if len(items) > 15:
            print(f"  ... {len(items) - 15} more")
    pages, examples = generate.affected(
        generate.load_manifest(MANIFEST), None if base is None else api.changed_symbols(d)
    )
    print("affected pages:", [p["id"] for p in pages] or "none")
    print("affected examples:", [e["id"] for e in examples] or "none")
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    llm = get_llm()
    if llm is None:
        print(
            "generate needs LLM_GATEWAY_TOKEN (extra: bedrock) or ANTHROPIC_API_KEY (extra: llm).",
            file=sys.stderr,
        )
        return 2
    manifest, snap, base = generate.load_manifest(MANIFEST), _current(), api.load(BASELINE)
    changed = None if (args.all or base is None) else api.changed_symbols(api.diff(base, snap))
    pages, examples = generate.affected(manifest, changed)
    if args.page:
        pages = [p for p in pages if p["id"] == args.page]
        examples = []
    for ex in examples:  # examples first: pages cite their regions
        path = ROOT / ex["path"]
        cur = path.read_text() if path.exists() else None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(generate.generate_example(llm, ex, snap, cur))
        print(f"example written: {ex['path']}")
    for page in pages:
        path = ROOT / "content" / page["path"]
        cur = path.read_text() if path.exists() else None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(generate.generate_page(llm, page, manifest, snap, ROOT, cur))
        print(f"page written: content/{page['path']}")
    return 0


def _artifacts(args: argparse.Namespace):
    manifest = generate.load_manifest(MANIFEST)
    pages = [p for p in manifest["page"] if not getattr(args, "page", None) or p["id"] == args.page]
    exs = [
        e
        for e in manifest["example"]
        if not getattr(args, "example", None) or e["id"] == args.example
    ]
    if getattr(args, "page", None) and not getattr(args, "example", None):
        exs = []
    if getattr(args, "example", None) and not getattr(args, "page", None):
        pages = []
    return manifest, pages, exs


def cmd_check(args: argparse.Namespace) -> int:
    """Deterministic checks only. No model, no network. Exit 1 when any gate fails."""
    cfg, snap = quality.load_config(QUALITY), _current()
    manifest, pages, exs = _artifacts(args)
    by_id = {e["id"]: e for e in manifest["example"]}
    reports = [quality.check_example(ROOT / e["path"], cfg, snap) for e in exs]
    reports += [
        quality.check_page((ROOT / "content" / p["path"]).read_text(), p, cfg, snap, ROOT, by_id)
        for p in pages
    ]
    bad = 0
    for r in reports:
        status = "ok  " if r.gates_ok else "FAIL"
        print(
            f"{status} {r.artifact:<28} score={r.score:.2f}  "
            f"gates_failed={[c.name for c in r.failing if c.severity == 'gate'] or '-'}  "
            f"advisory={[c.name for c in r.failing if c.severity == 'advisory'] or '-'}"
        )
        bad += not r.gates_ok
    print(f"docstring coverage of public API: {api.docstring_coverage(snap):.0%}")
    return 1 if bad else 0


def cmd_loop(args: argparse.Namespace) -> int:
    """Measure, optionally revise (bounded), and write justification reports."""
    cfg, snap, llm = quality.load_config(QUALITY), _current(), get_llm()
    manifest, pages, exs = _artifacts(args)
    by_id = {e["id"]: e for e in manifest["example"]}
    lp = cfg["loop"]
    outcomes: list[loop.Outcome] = []

    for ex in exs:
        path = ROOT / ex["path"]

        def measure(text: str, ex=ex, path=path):
            path.write_text(text)
            rep = quality.check_example(path, cfg, snap)
            chk, issues = quality.judge(
                llm, text, quality.api_facts(snap, ex["covers"], focus=ex.get("uses")), cfg
            )
            rep.checks.append(chk)
            return rep, issues

        revise = (
            None
            if llm is None
            else (lambda t, r, i, ex=ex: generate.revise_example(llm, t, r, i, ex, snap))
        )
        outcomes.append(
            loop.run(
                ex["id"],
                read=path.read_text,
                write=path.write_text,
                measure=measure,
                revise=revise,
                max_iterations=lp["max_iterations"],
                min_improvement=lp["min_improvement"],
            )
        )

    for page in pages:
        path = ROOT / "content" / page["path"]

        def measure(text: str, page=page, path=path):
            path.write_text(text)
            rep = quality.check_page(text, page, cfg, snap, ROOT, by_id)
            chk, issues = quality.judge(
                llm,
                quality.expand_coderefs(text, ROOT),
                quality.api_facts(snap, page["covers"], focus=page.get("key_symbols")),
                cfg,
            )
            rep.checks.append(chk)
            return rep, issues

        revise = (
            None
            if llm is None
            else (
                lambda t, r, i, page=page: generate.revise_page(
                    llm, t, r, i, page, manifest, snap, ROOT
                )
            )
        )
        outcomes.append(
            loop.run(
                page["id"],
                read=path.read_text,
                write=path.write_text,
                measure=measure,
                revise=revise,
                max_iterations=lp["max_iterations"],
                min_improvement=lp["min_improvement"],
            )
        )

    summary = [
        "# Quality summary",
        "",
        f"Model review: {'ran' if llm else 'SKIPPED (no LLM_GATEWAY_TOKEN or ANTHROPIC_API_KEY)'}",
        "",
        "| Artifact | Status | Score | Why it stopped |",
        "|---|---|---|---|",
    ]
    for o in outcomes:
        loop.write_reports(o, REPORTS)
        summary.append(
            f"| [{o.artifact}]({o.artifact}.md) | `{o.status}` | {o.final.score:.2f} | {o.reason} |"
        )
        print(f"{o.status:<22} {o.artifact:<28} score={o.final.score:.2f}  {o.reason}")
    (REPORTS / "SUMMARY.md").write_text("\n".join(summary) + "\n")
    return 1 if any(o.status in FAIL_STATUSES for o in outcomes) else 0


def cmd_review(args: argparse.Namespace) -> int:
    """Read-only model review: judge files exactly as they are. Never rewrites anything."""
    cfg, snap, llm = quality.load_config(QUALITY), _current(), get_llm()
    if llm is None:
        print(
            "review needs LLM_GATEWAY_TOKEN (extra: bedrock) or ANTHROPIC_API_KEY (extra: llm).",
            file=sys.stderr,
        )
        return 2
    manifest, pages, exs = _artifacts(args)
    by_id = {e["id"]: e for e in manifest["example"]}
    out_dir = REPORTS / "review"
    out_dir.mkdir(parents=True, exist_ok=True)
    for ex in exs:
        path = ROOT / ex["path"]
        rep = quality.check_example(path, cfg, snap)
        chk, issues = quality.judge(
            llm, path.read_text(), quality.api_facts(snap, ex["covers"], focus=ex.get("uses")), cfg
        )
        _save_review(out_dir, ex["id"], rep, chk, issues)
    for page in pages:
        text = (ROOT / "content" / page["path"]).read_text()
        rep = quality.check_page(text, page, cfg, snap, ROOT, by_id)
        chk, issues = quality.judge(
            llm,
            quality.expand_coderefs(text, ROOT),
            quality.api_facts(snap, page["covers"], focus=page.get("key_symbols")),
            cfg,
        )
        _save_review(out_dir, page["id"], rep, chk, issues)
    return 0


def _save_review(
    out_dir: Path, name: str, rep: quality.Report, chk: quality.Check, issues: list[str]
) -> None:
    scores = chk.value if isinstance(chk.value, dict) else {}
    print(f"{name:<26} scores={ {k: int(v) for k, v in scores.items()} or chk.detail[:60] }")
    lines = [
        f"# Review (read-only): {name}",
        "",
        f"Deterministic gates: {'pass' if rep.gates_ok else 'FAIL'}  ",
        f"Reviewer scores: {scores or 'not available: ' + chk.detail}",
        "",
        "## Issues",
        "",
    ]
    lines += [f"{n}. {i}" for n, i in enumerate(issues, 1)] or ["(none)"]
    (out_dir / f"{name}.md").write_text("\n".join(lines) + "\n")


def build_site(out: Path) -> int:
    """Stage SDK reference + generated content into a scratch dir and run Sphinx.

    The SDK's own ``docs/`` is copied, never modified.
    """
    manifest = generate.load_manifest(MANIFEST)
    stage = ROOT / "_build" / "src"
    shutil.rmtree(stage, ignore_errors=True)
    (stage / "reference").mkdir(parents=True)
    for f in (REPO / "docs").glob("*.rst"):
        shutil.copy(f, stage / "reference" / f.name)
    shutil.copytree(ROOT / "content", stage, dirs_exist_ok=True)
    titles = {"concept": "Concepts", "procedure": "How-to guides"}
    lines = ["# Splunk SDK for Python", "", "Guides, runnable examples, and the API reference.", ""]
    for kind, heading in titles.items():
        lines += ["```{toctree}", ":maxdepth: 1", f":caption: {heading}", ""]
        lines += [f"{p['path'].removesuffix('.md')}" for p in manifest["page"] if p["kind"] == kind]
        lines += ["```", ""]
    lines += [
        "```{toctree}",
        ":maxdepth: 2",
        ":caption: Reference",
        "",
        "reference/index",
        "```",
        "",
    ]
    (stage / "index.md").write_text("\n".join(lines))
    cmd = [
        sys.executable,
        "-m",
        "sphinx",
        "-b",
        "html",
        "-c",
        str(ROOT / "sphinx"),
        "-d",
        str(ROOT / "_build" / "doctrees"),
        str(stage),
        str(out),
    ]
    return subprocess.run(cmd, cwd=ROOT).returncode


def cmd_build(args: argparse.Namespace) -> int:
    return build_site(Path(args.out))


def cmd_ci(args: argparse.Namespace) -> int:
    """diff -> generate (if a model is available and something changed) -> loop -> build."""
    snap, base = _current(), api.load(BASELINE)
    d = api.diff(base, snap)
    changed = base is None or any(d.values())
    print(
        f"SDK {snap['meta']['sdk_version']} @ {snap['meta']['git_commit']}; "
        f"API changed since baseline: {changed}"
    )
    if changed and get_llm() is not None:
        cmd_generate(argparse.Namespace(all=False, page=None))
    rc = cmd_loop(argparse.Namespace(page=None, example=None))
    rc = max(rc, build_site(Path(args.out)))
    if rc == 0 and changed and args.update_baseline:
        api.save(snap, BASELINE)
        print("baseline updated")
    return rc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="sdkdocsys", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot", help="count public API; --update rewrites the baseline")
    s.add_argument("--update", action="store_true")
    s.set_defaults(fn=cmd_snapshot)
    sub.add_parser("diff", help="API changes since baseline and affected docs").set_defaults(
        fn=cmd_diff
    )
    g = sub.add_parser("generate", help="(re)write affected pages and examples with the model")
    g.add_argument("--all", action="store_true")
    g.add_argument("--page")
    g.set_defaults(fn=cmd_generate)
    for name, fn, helptext in (
        ("check", cmd_check, "deterministic quality gates, no model"),
        ("loop", cmd_loop, "bounded improve loop + justification reports"),
    ):
        c = sub.add_parser(name, help=helptext)
        c.add_argument("--page")
        c.add_argument("--example")
        c.set_defaults(fn=fn)
    r = sub.add_parser("review", help="read-only model review; writes reports/review/")
    r.add_argument("--page")
    r.add_argument("--example")
    r.set_defaults(fn=cmd_review)
    b = sub.add_parser("build", help="build the combined HTML site")
    b.add_argument("--out", default=str(ROOT / "_build" / "html"))
    b.set_defaults(fn=cmd_build)
    c = sub.add_parser("ci", help="the whole pipeline, as CI runs it")
    c.add_argument("--out", default=str(ROOT / "_build" / "html"))
    c.add_argument("--update-baseline", action="store_true")
    c.set_defaults(fn=cmd_ci)
    args = ap.parse_args(argv)
    rc = args.fn(args)
    if USAGE["calls"]:
        print(usage_summary(), file=sys.stderr)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
