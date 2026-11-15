"""Command line entry point: ``sdkdocsys <command>``."""

from __future__ import annotations

import argparse
import difflib
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from . import api, generate, loop, quality
from .llm import USAGE, get_llm, usage_summary

ROOT = Path(os.environ.get("SDKDOCSYS_ROOT", Path(__file__).resolve().parents[2]))
REPO = ROOT.parent
BASELINE = ROOT / "state" / "api_snapshot.json"
MANIFEST = ROOT / "manifest.toml"
QUALITY = ROOT / "quality.toml"
REPORTS = ROOT / "reports"
# Where proposals are written. CI points this at an untracked folder it uploads as an artifact.
PROPOSED = Path(os.environ.get("SDKDOCSYS_PROPOSED", ROOT / "proposed"))
STAGE = ROOT / "state" / ".stage"  # scratch copies for checks that need a file; gitignored
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


def _generate(args: argparse.Namespace, llm) -> dict[str, str]:
    """Draft affected examples and pages with the model. Writes proposals, never originals.

    Returns the generated texts by path relative to ROOT, so ``loop`` can improve them in the
    same run without reading stale files. Examples go first, and pages are drafted against the
    new examples so they cite real regions.
    """
    manifest, snap, base = generate.load_manifest(MANIFEST), _current(), api.load(BASELINE)
    changed = None if (args.all or base is None) else api.changed_symbols(api.diff(base, snap))
    pages, examples = generate.affected(manifest, changed)
    if args.page:
        pages = [p for p in pages if p["id"] == args.page]
        examples = []
    made: dict[str, str] = {}  # every generated text, changed or not
    revised: dict[str, str] = {}  # only texts that differ from the original
    for ex in examples:
        path = ROOT / ex["path"]
        text = generate.generate_example(llm, ex, snap, _read(path))
        made[ex["path"]] = text
        _proposal_writer(path, _read(path), revised)(text)
        print(f"example {'proposed' if ex['path'] in revised else 'unchanged'}: {ex['path']}")
    view = _overlay_root(revised)
    for page in pages:
        path = ROOT / "content" / page["path"]
        text = generate.generate_page(llm, page, manifest, snap, view, _read(path))
        rel = f"content/{page['path']}"
        made[rel] = text
        _proposal_writer(path, _read(path), revised)(text)
        print(f"page {'proposed' if rel in revised else 'unchanged'}: {rel}")
    shutil.rmtree(STAGE, ignore_errors=True)
    if revised:
        print(f"proposals written under {PROPOSED} (originals untouched). See `sdkdocsys adopt`.")
    return made


def cmd_generate(args: argparse.Namespace) -> int:
    """Draft affected pages and examples with the model, as proposals under proposed/."""
    llm = get_llm()
    if llm is None:
        print(
            "generate needs LLM_GATEWAY_TOKEN (extra: bedrock) or ANTHROPIC_API_KEY (extra: llm).",
            file=sys.stderr,
        )
        return 2
    _generate(args, llm)
    return 0


def _read(path: Path) -> str | None:
    """Text of an existing file, or None when it does not exist yet (a planned artifact)."""
    return path.read_text() if path.is_file() else None


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


def _proposal_writer(
    src: Path, original: str | None, sink: dict[str, str] | None = None
) -> Callable[[str], None]:
    """Return a writer that saves text under ``proposed/``, mirroring ``src``'s path in ROOT.

    The source file is never touched. Unchanged text writes nothing, and an existing proposal
    is only replaced when the loop produces a new one. ``sink`` records each changed text by
    its path relative to ROOT, so later artifacts can be checked against it. ``original`` is
    None for an artifact whose file does not exist yet, so any text counts as a change.
    """
    rel = src.relative_to(ROOT)
    dest = PROPOSED / rel

    def write(text: str) -> None:
        if text == original:
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text)
        if sink is not None:
            sink[rel.as_posix()] = text

    return write


def _overlay_root(revised: dict[str, str]) -> Path:
    """Root that pages resolve example code against: originals plus this run's proposals.

    Pages cite examples by path, so a page must be judged against the example code that would
    ship with it. With no revised examples this is just ROOT. Proposals left by earlier runs
    are ignored on purpose, since they may be stale.
    """
    if not revised:
        return ROOT
    view = STAGE / "overlay"
    shutil.rmtree(view, ignore_errors=True)
    shutil.copytree(ROOT / "examples", view / "examples")
    for rel, text in revised.items():
        (view / rel).parent.mkdir(parents=True, exist_ok=True)
        (view / rel).write_text(text)
    return view


def _focus(page: dict, text: str, snap: api.Snapshot) -> list[str]:
    """Symbols whose docstrings the reviewer gets: the key symbols plus any the page names."""
    return list(dict.fromkeys([*page.get("key_symbols", []), *quality.named_symbols(text, snap)]))


def _scope_line(llm, scope: set[str] | None, exs: list[dict], pages: list[dict]) -> str:
    if llm is None:
        return "SKIPPED (no LLM_GATEWAY_TOKEN or ANTHROPIC_API_KEY)"
    if scope is None:
        return "ran for every artifact"
    ids = [a["id"] for a in (*exs, *pages)]
    hit = [i for i in ids if i in scope]
    return (
        f"ran for {len(hit)} of {len(ids)} artifacts ({', '.join(hit) or 'none'}); "
        "the rest had deterministic checks only"
    )


def _changed_paths(ref: str | None) -> set[str] | None:
    """Files under docsys/ that changed between ``ref`` and HEAD, relative to ROOT.

    None when it cannot be determined (no ref, or git does not know it).
    """
    if not ref:
        return None
    proc = subprocess.run(
        ["git", "-C", str(REPO), "diff", "--name-only", ref, "HEAD", "--", ROOT.name],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    prefix = f"{ROOT.name}/"
    return {ln[len(prefix) :] for ln in proc.stdout.splitlines() if ln.startswith(prefix)}


def _review_scope(
    manifest: dict, changed_symbols: set[str] | None, changed_paths: set[str] | None
) -> set[str]:
    """Ids of the artifacts the model should review for this change.

    Affected by the API diff, edited themselves, or a page that cites an edited example.
    """
    pages, examples = generate.affected(manifest, changed_symbols)
    ids = {p["id"] for p in pages} | {e["id"] for e in examples}
    if changed_paths:
        edited = {e["id"] for e in manifest["example"] if e["path"] in changed_paths}
        ids |= edited
        for p in manifest["page"]:
            if f"content/{p['path']}" in changed_paths or edited & set(p.get("examples", [])):
                ids.add(p["id"])
    return ids


def cmd_loop(args: argparse.Namespace) -> int:
    """Measure, optionally revise (bounded), and write justification reports.

    Non-destructive: files in content/ and examples/ are never edited. A revised version is
    written to proposed/<same relative path> for a person to diff and adopt.
    """
    cfg, snap, llm = quality.load_config(QUALITY), _current(), get_llm()
    manifest, pages, exs = _artifacts(args)
    by_id = {e["id"]: e for e in manifest["example"]}
    lp = cfg["loop"]
    outcomes: list[loop.Outcome] = []
    revised: dict[str, str] = {}
    seeds: dict[str, str] = getattr(args, "seeds", None) or {}  # drafts from this run's generate
    # Artifact ids the model may review and revise. None means all. Everything else still gets
    # the deterministic checks, and its model review is reported as skipped.
    scope: set[str] | None = getattr(args, "model_scope", None)

    def model_for(artifact_id: str):
        return llm if scope is None or artifact_id in scope else None

    skip_reason = None if llm is None else "skipped: not affected by this change"

    def start_of(rel: str, path: Path) -> str | None:
        return seeds.get(rel, _read(path))

    for ex in exs:
        path = ROOT / ex["path"]
        first = start_of(ex["path"], path)
        if first is None:
            print(f"skipped {ex['id']}: {ex['path']} does not exist yet (run generate)")
            continue
        write = _proposal_writer(path, _read(path), revised)
        stage = STAGE / ex["path"]

        use = model_for(ex["id"])

        def measure(text: str, ex=ex, stage=stage, use=use):
            # check_example reads a file (and runs ruff on it), so stage the candidate in a
            # scratch dir inside docsys/ (ruff sees the project config). Never the original.
            stage.parent.mkdir(parents=True, exist_ok=True)
            stage.write_text(text)
            rep = quality.check_example(stage, cfg, snap)
            chk, issues = quality.judge(
                use,
                text,
                quality.api_facts(snap, ex["covers"], focus=ex.get("uses")),
                cfg,
                skip_reason=skip_reason,
            )
            rep.checks.append(chk)
            return rep, issues

        revise = (
            None
            if use is None
            else (lambda t, r, i, ex=ex, use=use: generate.revise_example(use, t, r, i, ex, snap))
        )
        outcomes.append(
            loop.run(
                ex["id"],
                read=lambda first=first: first,
                write=write,
                measure=measure,
                revise=revise,
                max_iterations=lp["max_iterations"],
                min_improvement=lp["min_improvement"],
            )
        )

    view = _overlay_root(revised)
    for page in pages:
        path = ROOT / "content" / page["path"]
        rel = f"content/{page['path']}"
        first = start_of(rel, path)
        if first is None:
            print(f"skipped {page['id']}: {rel} does not exist yet (run generate)")
            continue
        write = _proposal_writer(path, _read(path))

        use = model_for(page["id"])

        def measure(text: str, page=page, use=use):
            rep = quality.check_page(text, page, cfg, snap, view, by_id)
            chk, issues = quality.judge(
                use,
                quality.reviewer_text(text, view),
                quality.api_facts(snap, page["covers"], focus=_focus(page, text, snap)),
                cfg,
                skip_reason=skip_reason,
            )
            rep.checks.append(chk)
            return rep, issues

        revise = (
            None
            if use is None
            else (
                lambda t, r, i, page=page, use=use: generate.revise_page(
                    use, t, r, i, page, manifest, snap, view
                )
            )
        )
        outcomes.append(
            loop.run(
                page["id"],
                read=lambda first=first: first,
                write=write,
                measure=measure,
                revise=revise,
                max_iterations=lp["max_iterations"],
                min_improvement=lp["min_improvement"],
            )
        )

    summary = [
        "# Quality summary",
        "",
        f"Model review: {_scope_line(llm, scope, exs, pages)}",
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
    shutil.rmtree(STAGE, ignore_errors=True)
    changed = [p for p in PROPOSED.rglob("*") if p.is_file() and p.name != "README.md"]
    if changed:
        print(f"proposals (diff against the originals, nothing was edited): {PROPOSED}")
    return 1 if any(o.status in FAIL_STATUSES for o in outcomes) else 0


def _gate_failures() -> dict[str, set[str]]:
    """Failing gate names per artifact id, over every example and page. Deterministic, no model."""
    cfg, snap = quality.load_config(QUALITY), _current()
    manifest = generate.load_manifest(MANIFEST)
    by_id = {e["id"]: e for e in manifest["example"]}
    out: dict[str, set[str]] = {}
    for e in manifest["example"]:
        if not (ROOT / e["path"]).is_file():
            continue  # planned, not written yet: it has no gates to fail until it is adopted
        rep = quality.check_example(ROOT / e["path"], cfg, snap)
        out[e["id"]] = {c.name for c in rep.failing if c.severity == "gate"}
    for p in manifest["page"]:
        if not (ROOT / "content" / p["path"]).is_file():
            continue
        text = (ROOT / "content" / p["path"]).read_text()
        rep = quality.check_page(text, p, cfg, snap, ROOT, by_id)
        out[p["id"]] = {c.name for c in rep.failing if c.severity == "gate"}
    return out


def _pending() -> dict[str, tuple[Path, Path]]:
    """Artifact id -> (original, proposal) for every proposal that is new or differs.

    The original path may not exist yet (a newly generated artifact).
    """
    manifest = generate.load_manifest(MANIFEST)
    found: dict[str, tuple[Path, Path]] = {}
    for kind, base in (("example", ROOT), ("page", ROOT / "content")):
        for item in manifest[kind]:
            src = base / item["path"]
            prop = PROPOSED / src.relative_to(ROOT)
            if prop.is_file() and (_read(src) != prop.read_text()):
                found[item["id"]] = (src, prop)
    return found


def cmd_adopt(args: argparse.Namespace) -> int:
    """Copy chosen proposals from proposed/ over the originals, then re-run the gates.

    Nothing is adopted unless named (--page, --example, or --all). If adopting introduces a
    gate failure anywhere (including a page that cites an adopted example), every file is
    restored and the proposals are kept. --dry-run shows diffs and changes nothing.
    """
    pending = _pending()
    wanted = {args.page, args.example} - {None}
    if not (args.all or wanted):
        print("name what to adopt: --page ID, --example ID, or --all.", file=sys.stderr)
        for aid, (src, _) in sorted(pending.items()):
            print(f"  pending: {aid}  ({src.relative_to(ROOT)})", file=sys.stderr)
        if not pending:
            print("  no pending proposals.", file=sys.stderr)
        return 2
    chosen = pending if args.all else {k: v for k, v in pending.items() if k in wanted}
    for missing in sorted(wanted - set(chosen)):
        print(f"no pending proposal for {missing}", file=sys.stderr)
    if not chosen:
        return 2
    if args.dry_run:
        for _aid, (src, prop) in sorted(chosen.items()):
            rel = src.relative_to(ROOT)
            sys.stdout.writelines(
                difflib.unified_diff(
                    (_read(src) or "").splitlines(keepends=True),
                    prop.read_text().splitlines(keepends=True),
                    f"a/{rel}" if src.is_file() else "/dev/null",
                    f"b/{rel}",
                )
            )
        print(f"dry run: {len(chosen)} proposal(s) would be adopted; nothing changed.")
        return 0

    before = _gate_failures()
    backup = {aid: _read(src) for aid, (src, _) in chosen.items()}

    def restore() -> None:
        for aid, (src, _) in chosen.items():
            if backup[aid] is None:
                src.unlink(missing_ok=True)  # it was a new file
            else:
                src.write_text(backup[aid])

    try:
        for src, prop in chosen.values():
            src.parent.mkdir(parents=True, exist_ok=True)
            src.write_text(prop.read_text())
        after = _gate_failures()
    except BaseException:
        restore()
        raise
    broken = {
        a: sorted(after[a] - before.get(a, set())) for a in after if after[a] - before.get(a, set())
    }
    if broken:
        restore()
        for aid, names in sorted(broken.items()):
            print(f"FAIL {aid}: new gate failure(s) {names}", file=sys.stderr)
        print("nothing adopted: originals restored, proposals kept.", file=sys.stderr)
        return 1
    for _, prop in chosen.values():
        prop.unlink()
    for aid, (src, _) in sorted(chosen.items()):
        print(f"adopted {aid}: {src.relative_to(ROOT)}")
    print("gates re-run: no new gate failures. Review with `git diff`; nothing is committed.")
    return 0


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
            quality.reviewer_text(text, ROOT),
            quality.api_facts(snap, page["covers"], focus=_focus(page, text, snap)),
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
    if chk.notes:
        lines += ["", "## Needs SME confirmation (not scored as errors)", ""]
        lines += [f"- {n}" for n in chk.notes]
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
    llm, seeds, scope = get_llm(), {}, None
    if llm is not None and not args.review_all:
        manifest = generate.load_manifest(MANIFEST)
        paths = _changed_paths(args.changed_from)
        if paths is None:
            print("no usable --changed-from: model review follows the API diff only")
        scope = _review_scope(manifest, None if base is None else api.changed_symbols(d), paths)
        print(f"model review scope: {sorted(scope) or 'nothing'}")
    if changed and llm is not None:
        seeds = _generate(argparse.Namespace(all=False, page=None), llm)
    rc = cmd_loop(argparse.Namespace(page=None, example=None, seeds=seeds, model_scope=scope))
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
    a = sub.add_parser(
        "adopt", help="copy proposals from proposed/ over the originals, then re-check"
    )
    a.add_argument("--page")
    a.add_argument("--example")
    a.add_argument("--all", action="store_true")
    a.add_argument("--dry-run", action="store_true")
    a.set_defaults(fn=cmd_adopt)
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
    c.add_argument(
        "--changed-from",
        metavar="REF",
        help="git ref to diff against; the model reviews only artifacts affected since then",
    )
    c.add_argument(
        "--review-all", action="store_true", help="model-review every artifact (can be costly)"
    )
    c.set_defaults(fn=cmd_ci)
    args = ap.parse_args(argv)
    rc = args.fn(args)
    if USAGE["calls"]:
        print(usage_summary(), file=sys.stderr)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
