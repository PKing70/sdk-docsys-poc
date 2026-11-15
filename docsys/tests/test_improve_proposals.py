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
