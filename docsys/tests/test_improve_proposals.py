"""The improve loop must never edit content/ or examples/; revisions go to proposed/."""

import argparse
import shutil
from pathlib import Path

from sdkdocsys import cli, generate, quality

ROOT = Path(__file__).resolve().parents[1]
MARK = "\n# revised\n"


def _sandbox(tmp_path: Path, monkeypatch) -> Path:
    for name in ("manifest.toml", "quality.toml"):
        shutil.copy(ROOT / name, tmp_path / name)
    shutil.copytree(ROOT / "examples", tmp_path / "examples")
    shutil.copytree(ROOT / "content", tmp_path / "content")
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "MANIFEST", tmp_path / "manifest.toml")
    monkeypatch.setattr(cli, "QUALITY", tmp_path / "quality.toml")
    monkeypatch.setattr(cli, "REPORTS", tmp_path / "reports")
    monkeypatch.setattr(cli, "PROPOSED", tmp_path / "proposed")
    monkeypatch.setattr(cli, "STAGE", tmp_path / "state" / ".stage")
    (tmp_path / "reports").mkdir()
    return tmp_path


def _fake_model(monkeypatch) -> None:
    """Score a candidate higher only when it carries the revision marker."""
    monkeypatch.setattr(cli, "get_llm", lambda: object())
    monkeypatch.setattr(
        generate, "revise_example", lambda llm, text, rep, issues, ex, snap: text + MARK
    )
    monkeypatch.setattr(
        generate, "revise_page", lambda llm, text, rep, issues, page, m, snap, root: text + MARK
    )

    def check_example(path, cfg, snap):
        ok = MARK in path.read_text()
        return quality.Report(path.stem, [quality.Check("revised", "code", ok, "gate")])

    def check_page(text, page, cfg, snap, root, by_id):
        return quality.Report(page["id"], [quality.Check("revised", "prose", MARK in text, "gate")])

    monkeypatch.setattr(quality, "check_example", check_example)
    monkeypatch.setattr(quality, "check_page", check_page)
    monkeypatch.setattr(quality, "judge", lambda *a, **k: (quality.Check("j", "judge", True), []))


def test_example_revision_goes_to_proposed_not_in_place(tmp_path, monkeypatch):
    root = _sandbox(tmp_path, monkeypatch)
    _fake_model(monkeypatch)
    ex = generate.load_manifest(root / "manifest.toml")["example"][0]
    original = (root / ex["path"]).read_text()

    cli.cmd_loop(argparse.Namespace(page=None, example=ex["id"]))

    assert (root / ex["path"]).read_text() == original
    assert (root / "proposed" / ex["path"]).read_text() == original + MARK
    assert not (root / "state" / ".stage").exists()


def test_page_revision_goes_to_proposed_not_in_place(tmp_path, monkeypatch):
    root = _sandbox(tmp_path, monkeypatch)
    _fake_model(monkeypatch)
    page = generate.load_manifest(root / "manifest.toml")["page"][0]
    src = root / "content" / page["path"]
    original = src.read_text()

    cli.cmd_loop(argparse.Namespace(page=page["id"], example=None))

    assert src.read_text() == original
    assert (root / "proposed" / "content" / page["path"]).read_text() == original + MARK


def test_no_model_writes_no_proposals(tmp_path, monkeypatch):
    root = _sandbox(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "get_llm", lambda: None)
    ex = generate.load_manifest(root / "manifest.toml")["example"][0]

    cli.cmd_loop(argparse.Namespace(page=None, example=ex["id"]))

    assert not (root / "proposed").exists()


def test_pages_are_scored_against_this_runs_example_proposals(tmp_path, monkeypatch):
    root = _sandbox(tmp_path, monkeypatch)
    _fake_model(monkeypatch)
    seen: list[Path] = []
    example_text: list[str] = []
    fake_check_page = quality.check_page

    def spy(text, page, cfg, snap, view, by_id):
        seen.append(view)
        example_text.append((view / ex["path"]).read_text())  # overlay is deleted after the run
        return fake_check_page(text, page, cfg, snap, view, by_id)

    monkeypatch.setattr(quality, "check_page", spy)
    man = generate.load_manifest(root / "manifest.toml")
    ex, page = man["example"][0], man["page"][0]
    original = (root / ex["path"]).read_text()

    # Examples and pages in one run: pages see the proposed example, originals stay put.
    cli.cmd_loop(argparse.Namespace(page=None, example=None))
    assert seen and all(v != root for v in seen)
    assert example_text and all(t == original + MARK for t in example_text)
    assert (root / ex["path"]).read_text() == original

    # Page-only run: no example was revised this run, so a stale proposal is not overlaid.
    seen.clear()
    example_text.clear()
    cli.cmd_loop(argparse.Namespace(page=page["id"], example=None))
    assert seen and all(v == root for v in seen)


# --- adopt -----------------------------------------------------------------------------


def _propose(root: Path, rel: str, text: str) -> Path:
    dest = root / "proposed" / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text)
    return dest


def _adopt(**kw) -> int:
    args = dict(page=None, example=None, all=False, dry_run=False) | kw
    return cli.cmd_adopt(argparse.Namespace(**args))


def _example(root: Path) -> tuple[dict, str]:
    ex = generate.load_manifest(root / "manifest.toml")["example"][0]
    return ex, (root / ex["path"]).read_text()


def test_adopt_requires_a_selection(tmp_path, monkeypatch, capsys):
    root = _sandbox(tmp_path, monkeypatch)
    ex, original = _example(root)
    _propose(root, ex["path"], original + "\n# edit\n")
    assert _adopt() == 2
    assert (root / ex["path"]).read_text() == original
    assert ex["id"] in capsys.readouterr().err


def test_adopt_dry_run_changes_nothing(tmp_path, monkeypatch, capsys):
    root = _sandbox(tmp_path, monkeypatch)
    ex, original = _example(root)
    prop = _propose(root, ex["path"], original + "\n# edit\n")
    assert _adopt(example=ex["id"], dry_run=True) == 0
    assert "+# edit" in capsys.readouterr().out
    assert (root / ex["path"]).read_text() == original and prop.exists()


def test_adopt_copies_proposal_and_removes_it(tmp_path, monkeypatch):
    root = _sandbox(tmp_path, monkeypatch)
    ex, original = _example(root)
    new = original + "\n# edit\n"
    prop = _propose(root, ex["path"], new)
    assert _adopt(example=ex["id"]) == 0
    assert (root / ex["path"]).read_text() == new
    assert not prop.exists()


def test_adopt_rolls_back_on_new_gate_failure(tmp_path, monkeypatch, capsys):
    root = _sandbox(tmp_path, monkeypatch)
    ex, original = _example(root)
    prop = _propose(root, ex["path"], "def broken(:\n")  # does not parse
    assert _adopt(example=ex["id"]) == 1
    assert (root / ex["path"]).read_text() == original
    assert prop.exists()
    assert "nothing adopted" in capsys.readouterr().err


def test_adopt_ignores_identical_proposals(tmp_path, monkeypatch):
    root = _sandbox(tmp_path, monkeypatch)
    ex, original = _example(root)
    _propose(root, ex["path"], original)
    assert _adopt(all=True) == 2


# --- generate --------------------------------------------------------------------------


def _generate_args(**kw) -> argparse.Namespace:
    return argparse.Namespace(**({"all": True, "page": None} | kw))


def _fake_generate(monkeypatch, suffix: str = "\n# generated\n") -> list[Path]:
    """Model that appends a marker. Records the root each page was drafted against."""
    roots: list[Path] = []
    monkeypatch.setattr(cli, "get_llm", lambda: object())
    monkeypatch.setattr(
        generate, "generate_example", lambda llm, ex, snap, cur: (cur or "") + suffix
    )

    def gen_page(llm, page, manifest, snap, root, cur):
        roots.append(root)
        return (cur or "") + suffix

    monkeypatch.setattr(generate, "generate_page", gen_page)
    return roots


def test_generate_writes_proposals_not_originals(tmp_path, monkeypatch):
    root = _sandbox(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "BASELINE", root / "state" / "none.json")  # no baseline: all
    _fake_generate(monkeypatch)
    man = generate.load_manifest(root / "manifest.toml")
    ex, page = man["example"][0], man["page"][0]
    ex_orig = (root / ex["path"]).read_text()
    page_src = root / "content" / page["path"]
    page_orig = page_src.read_text()

    assert cli.cmd_generate(_generate_args()) == 0

    assert (root / ex["path"]).read_text() == ex_orig
    assert page_src.read_text() == page_orig
    assert (root / "proposed" / ex["path"]).read_text() == ex_orig + "\n# generated\n"
    assert (root / "proposed" / "content" / page["path"]).read_text().endswith("# generated\n")
    assert not (root / "state" / ".stage").exists()


def test_generate_drafts_pages_against_new_examples(tmp_path, monkeypatch):
    root = _sandbox(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "BASELINE", root / "state" / "none.json")
    roots = _fake_generate(monkeypatch)
    ex = generate.load_manifest(root / "manifest.toml")["example"][0]
    seen: list[str] = []
    real = generate.generate_page
    monkeypatch.setattr(
        generate,
        "generate_page",
        lambda llm, page, m, snap, view, cur: (
            seen.append((view / ex["path"]).read_text()),
            real(llm, page, m, snap, view, cur),
        )[1],
    )
    cli.cmd_generate(_generate_args())
    assert roots and all(r != root for r in roots)
    assert seen and all(t.endswith("# generated\n") for t in seen)


def test_generate_creates_planned_artifact_as_proposal(tmp_path, monkeypatch):
    root = _sandbox(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "BASELINE", root / "state" / "none.json")
    _fake_generate(monkeypatch, suffix="NEW\n")
    ex = generate.load_manifest(root / "manifest.toml")["example"][0]
    (root / ex["path"]).unlink()  # planned but unwritten

    cli.cmd_generate(_generate_args(page="no-such-page"))  # pages only: no example generated
    assert not (root / "proposed" / ex["path"]).exists()

    cli.cmd_generate(_generate_args(page=None))
    assert not (root / ex["path"]).exists()
    assert (root / "proposed" / ex["path"]).read_text() == "NEW\n"


def test_adopt_can_adopt_a_new_artifact_and_rolls_it_back(tmp_path, monkeypatch):
    root = _sandbox(tmp_path, monkeypatch)
    ex, original = _example(root)
    (root / ex["path"]).unlink()
    prop = _propose(root, ex["path"], "def broken(:\n")
    assert _adopt(example=ex["id"]) == 1  # new file fails its gates: removed again
    assert not (root / ex["path"]).exists() and prop.exists()

    prop.write_text(original)
    assert _adopt(example=ex["id"]) == 0
    assert (root / ex["path"]).read_text() == original and not prop.exists()


def test_loop_improves_this_runs_generated_draft(tmp_path, monkeypatch):
    root = _sandbox(tmp_path, monkeypatch)
    _fake_model(monkeypatch)
    ex, original = _example(root)
    draft = original + "\n# draft\n"

    cli.cmd_loop(argparse.Namespace(page=None, example=ex["id"], seeds={ex["path"]: draft}))

    assert (root / ex["path"]).read_text() == original
    assert (root / "proposed" / ex["path"]).read_text() == draft + MARK


def test_loop_skips_artifact_with_no_file_and_no_draft(tmp_path, monkeypatch, capsys):
    root = _sandbox(tmp_path, monkeypatch)
    _fake_model(monkeypatch)
    ex, _ = _example(root)
    (root / ex["path"]).unlink()
    cli.cmd_loop(argparse.Namespace(page=None, example=ex["id"]))
    assert "does not exist yet" in capsys.readouterr().out


# --- scoped model review (CI cost control) ---------------------------------------------


def _manifest() -> dict:
    return generate.load_manifest(ROOT / "manifest.toml")


def test_scope_is_empty_when_nothing_changed():
    assert cli._review_scope(_manifest(), set(), None) == set()
    assert cli._review_scope(_manifest(), set(), set()) == set()


def test_scope_covers_an_edited_page():
    page = _manifest()["page"][0]
    got = cli._review_scope(_manifest(), set(), {f"content/{page['path']}"})
    assert got == {page["id"]}


def test_scope_includes_pages_that_cite_an_edited_example():
    man = _manifest()
    ex = next(
        e for e in man["example"] if any(e["id"] in p.get("examples", []) for p in man["page"])
    )
    citing = {p["id"] for p in man["page"] if ex["id"] in p.get("examples", [])}
    got = cli._review_scope(man, set(), {ex["path"]})
    assert got == {ex["id"]} | citing


def test_scope_follows_the_api_diff_and_none_means_everything():
    man = _manifest()
    everything = {a["id"] for a in (*man["page"], *man["example"])}
    assert cli._review_scope(man, None, None) == everything


def test_changed_paths_reads_git_and_returns_none_when_unknown(tmp_path, monkeypatch):
    import subprocess

    repo = tmp_path / "repo"
    (repo / "docsys" / "content").mkdir(parents=True)

    def git(*a):
        subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)

    git("init", "-q")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    (repo / "docsys" / "content" / "a.md").write_text("one")
    (repo / "other.txt").write_text("x")
    git("add", ".")
    git("commit", "-qm", "base")
    (repo / "docsys" / "content" / "a.md").write_text("two")
    (repo / "other.txt").write_text("y")
    git("commit", "-qam", "change")
    monkeypatch.setattr(cli, "REPO", repo)
    monkeypatch.setattr(cli, "ROOT", repo / "docsys")

    assert cli._changed_paths("HEAD~1") == {"content/a.md"}  # outside docsys/ is ignored
    assert cli._changed_paths(None) is None
    assert cli._changed_paths("0" * 40) is None  # a new-branch push has an all-zero "before"


def test_loop_uses_the_model_only_inside_the_scope(tmp_path, monkeypatch):
    root = _sandbox(tmp_path, monkeypatch)
    _fake_model(monkeypatch)
    man = generate.load_manifest(root / "manifest.toml")
    inside, outside = man["example"][0], man["example"][1]
    judged: list[bool] = []
    revised_ids: list[str] = []

    def judge(llm, text, facts, cfg, *, skip_reason=None):
        judged.append(llm is not None)
        return quality.Check("llm_rubric", "judge", True if llm else None), []

    monkeypatch.setattr(quality, "judge", judge)
    monkeypatch.setattr(
        generate,
        "revise_example",
        lambda llm, text, rep, issues, ex, snap: revised_ids.append(ex["id"]) or text + MARK,
    )
    # the fake scorer fails everything until revised, so the model must be asked to revise
    cli.cmd_loop(argparse.Namespace(page=None, example=None, model_scope={inside["id"]}))

    assert inside["id"] in revised_ids and outside["id"] not in revised_ids
    assert (root / "proposed" / inside["path"]).exists()
    assert not (root / "proposed" / outside["path"]).exists()
    summary = (root / "reports" / "SUMMARY.md").read_text()
    assert f"ran for 1 of {len(man['example']) + len(man['page'])} artifacts" in summary


def test_ci_passes_a_model_scope_to_the_loop(tmp_path, monkeypatch):
    seen: list = []
    monkeypatch.setattr(cli, "get_llm", lambda: object())
    monkeypatch.setattr(cli, "cmd_loop", lambda a: seen.append(a.model_scope) or 0)
    monkeypatch.setattr(cli, "build_site", lambda out: 0)
    monkeypatch.setattr(cli, "_generate", lambda a, llm: {})
    base = dict(out=str(tmp_path), update_baseline=False, changed_from=None, review_all=False)

    cli.cmd_ci(argparse.Namespace(**base))
    cli.cmd_ci(argparse.Namespace(**(base | {"review_all": True})))

    assert seen[0] is not None and seen[1] is None  # --review-all lifts the limit
