"""What the model reviewer is shown, and how its two kinds of concern are reported."""

import ast
import json
from pathlib import Path

from sdkdocsys import api, cli, loop, quality

PAGE = """# T

Intro with `Jobs.oneshot`, `Message`, and a plain `count` word.

:::{coderef} examples/a.py
:region: one
:::

:::{coderef} examples/a.py
:region: two
:::

:::{coderef} examples/b.py
:::
"""
A = (
    "import helper\n\ndef connect():\n    return 1  # outside every region\n\n"
    "# region: one\nx = 1\n# endregion: one\n# region: two\ny = 2\n# endregion: two\n"
)


def _root(tmp_path: Path) -> Path:
    (tmp_path / "examples").mkdir()
    (tmp_path / "examples" / "a.py").write_text(A)
    (tmp_path / "examples" / "b.py").write_text("z = 3\n")
    (tmp_path / "examples" / "helper.py").write_text("SECRET_HELPER = 1\n")
    return tmp_path


SNAP = {
    "symbols": {
        "pkg.client.Jobs.oneshot": {"kind": "method", "sig": "(q)", "doc": "Runs one search."},
        "pkg.client.Jobs.count": {"kind": "method", "sig": "()", "doc": "UNRELATED"},
        "pkg.results.Message": {"kind": "class", "sig": "(t, m)", "doc": "A message."},
        "pkg.results.Other": {"kind": "class", "sig": "()", "doc": "Not named on the page."},
    }
}


def test_reviewer_sees_each_cited_file_whole_and_once(tmp_path):
    text = quality.reviewer_text(PAGE, _root(tmp_path))
    assert text.count("[FULL EXAMPLE FILE examples/a.py") == 1  # cited twice, shown once
    assert "[FULL EXAMPLE FILE examples/b.py" in text
    assert "return 1  # outside every region" in text  # code outside the cited regions
    assert text.index("[CODE from examples/a.py") < text.index("[FULL EXAMPLE FILE")


def test_imported_files_are_not_followed(tmp_path):
    assert "SECRET_HELPER" not in quality.reviewer_text(PAGE, _root(tmp_path))


def test_missing_cited_file_is_skipped_without_crashing(tmp_path):
    root = _root(tmp_path)
    (root / "examples" / "b.py").unlink()
    text = quality.reviewer_text(PAGE, root)
    assert "FULL EXAMPLE FILE examples/b.py" not in text and "examples/a.py" in text


def test_cited_example_files_keep_page_order():
    assert quality.cited_example_files(PAGE) == ["examples/a.py", "examples/b.py"]


def test_named_symbols_skip_plain_words():
    got = quality.named_symbols(PAGE, SNAP)
    assert "pkg.client.Jobs.oneshot" in got and "pkg.results.Message" in got
    assert "pkg.client.Jobs.count" not in got  # `count` is a plain word


def test_named_symbols_get_docstrings_and_others_do_not():
    focus = quality.named_symbols(PAGE, SNAP)
    facts = quality.api_facts(SNAP, ["pkg"], focus=focus)
    assert "Runs one search." in facts and "A message." in facts
    assert "Not named on the page." not in facts


def test_stored_docstrings_are_not_cut_at_1200_chars():
    node = ast.parse('def f():\n    "' + "x" * 3000 + '"\n').body[0]
    assert len(api._entry("function", node)["doc"]) == 3000


class FakeLLM:
    def __init__(self, reply: dict):
        self.reply, self.prompts = reply, []

    def complete(self, system, prompt, max_tokens=0):
        self.prompts.append((system, prompt))
        return json.dumps(self.reply)


SCORES = {"accuracy": 4, "clarity": 4, "teaching_value": 4, "completeness": 4}
CFG = {"judge": {"min_score": 3.5, "dimensions": list(SCORES)}}


def test_unverifiable_claims_are_notes_not_issues():
    llm = FakeLLM(SCORES | {"issues": ["real problem"], "unverifiable": ["count caps rows"]})
    chk, issues = quality.judge(llm, "page", "facts", CFG)
    assert issues == ["real problem"]  # the reviser is never asked to act on the notes
    assert chk.notes == ["count caps rows"] and chk.passed is True


def test_reply_without_unverifiable_still_works():
    chk, issues = quality.judge(FakeLLM(SCORES | {"issues": []}), "page", "facts", CFG)
    assert chk.notes == [] and issues == []


def test_rubric_tells_the_reviewer_not_to_penalize_unverifiable_claims():
    assert "unverifiable" in quality.JUDGE_SYSTEM
    assert "not how the SDK is implemented" in quality.JUDGE_SYSTEM
    assert "never also under issues" in quality.JUDGE_SYSTEM


def test_loop_report_lists_notes_for_sme_review():
    note = quality.Check("llm_rubric", "judge", True, "gate", SCORES, 3.5, "", ["count caps rows"])
    out = loop.Outcome("t", loop.ACCEPTED, "ok", [], quality.Report("t", [note]), [])
    md = loop.render_markdown(out)
    assert "Needs SME confirmation" in md and "count caps rows" in md


def test_review_command_file_lists_notes(tmp_path):
    chk = quality.Check("llm_rubric", "judge", True, "gate", SCORES, 3.5, "", ["count caps rows"])
    cli._save_review(tmp_path, "p", quality.Report("p", []), chk, ["an issue"])
    body = (tmp_path / "p.md").read_text()
    assert "Needs SME confirmation" in body and "count caps rows" in body
