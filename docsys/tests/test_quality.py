"""Quality checks must fail on bad input, not just pass on good input."""

from pathlib import Path

import pytest
from sdkdocsys import api, coderef, generate, loop, quality

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
CFG = quality.load_config(ROOT / "quality.toml")
SNAP = api.snapshot(REPO / "splunklib")
MANIFEST = generate.load_manifest(ROOT / "manifest.toml")
EXAMPLES = {e["id"]: e for e in MANIFEST["example"]}
PAGE = next(p for p in MANIFEST["page"] if p["id"] == "procedure-first-search")
FIXTURES = Path(__file__).parent / "fixtures"
GOOD_PAGE = (FIXTURES / "good_page.md").read_text()


def failed(rep: quality.Report) -> set[str]:
    return {c.name for c in rep.failing}


def page_report(md: str) -> quality.Report:
    return quality.check_page(md, PAGE, CFG, SNAP, ROOT, EXAMPLES)


def example_report(tmp_path: Path, src: str) -> quality.Report:
    f = tmp_path / "ex.py"
    f.write_text(src)
    return quality.check_example(f, CFG, SNAP)


def test_shipped_content_passes_all_gates():
    for p in MANIFEST["page"]:
        md = (ROOT / "content" / p["path"]).read_text()
        rep = quality.check_page(md, p, CFG, SNAP, ROOT, EXAMPLES)
        assert rep.gates_ok, (p["id"], [c.name for c in rep.failing])
    for e in MANIFEST["example"]:
        rep = quality.check_example(ROOT / e["path"], CFG, SNAP)
        assert rep.gates_ok, (e["id"], [c.name for c in rep.failing])


def test_embedded_code_fence_fails():
    assert "no_embedded_code" in failed(page_report(GOOD_PAGE + "\n```python\nx = 1\n```\n"))


def test_text_fence_is_allowed():
    assert "no_embedded_code" not in failed(page_report(GOOD_PAGE + "\n```text\nok\n```\n"))


@pytest.mark.parametrize(
    "bad", ["You can simply run it.", "Use it - and, obviously, wait.", "Wait \u2014 then run."]
)
def test_banned_terms_fail(bad):
    assert "banned_terms" in failed(page_report(GOOD_PAGE + f"\n{bad}\n"))


def test_missing_section_fails():
    assert "required_sections" in failed(page_report(GOOD_PAGE.replace("## Verify", "## Done")))


def test_unresolved_coderef_fails():
    md = GOOD_PAGE.replace(":region: search", ":region: nope")
    assert "coderef_resolves" in failed(page_report(md))


def test_hallucinated_symbol_fails():
    rep = page_report(GOOD_PAGE + "\nSee `splunklib.client.NotARealThing`.\n")
    assert "symbol_refs_exist" in failed(rep)


def test_key_symbol_not_explained_fails():
    rep = page_report(GOOD_PAGE.replace("`Message`", "the message type"))
    assert "key_symbols_explained" in failed(rep)


def test_dense_prose_fails_readability():
    dense = (
        "Notwithstanding interoperability considerations, institutional authentication "
        "infrastructure necessitates comprehensive reconfiguration. "
    ) * 12
    assert "flesch_reading_ease" in failed(page_report(GOOD_PAGE + "\n" + dense + "\n"))


GOOD_EX = (FIXTURES / "good_example.py").read_text()


def test_example_hardcoded_password_fails(tmp_path):
    src = GOOD_EX.replace('os.environ["SPLUNK_PASSWORD"]', '"hunter2"')
    assert "no_hardcoded_secrets" in failed(example_report(tmp_path, src))


def test_example_third_party_import_fails(tmp_path):
    assert "self_contained" in failed(example_report(tmp_path, "import requests\n" + GOOD_EX))


def test_example_hallucinated_api_fails(tmp_path):
    src = GOOD_EX.replace("results.Message", "results.NotAThing")
    assert "splunklib_symbols_exist" in failed(example_report(tmp_path, src))


def test_example_without_guard_fails(tmp_path):
    src = GOOD_EX.replace('if __name__ == "__main__":\n    main()\n', "main()\n")
    assert "entrypoint" in failed(example_report(tmp_path, src))


def test_example_unbalanced_region_fails(tmp_path):
    src = GOOD_EX.replace("# endregion: search", "")
    assert "regions_balanced" in failed(example_report(tmp_path, src))


def test_example_missing_header_fails(tmp_path):
    src = GOOD_EX.replace("Goal:", "Aim:")
    assert "header_docstring" in failed(example_report(tmp_path, src))


def test_example_syntax_error_fails(tmp_path):
    assert "parses" in failed(example_report(tmp_path, "def (:\n"))


def test_judge_skipped_is_not_a_pass():
    chk, _ = quality.judge(None, "x", "", CFG)
    assert chk.passed is None


class FakeLLM:
    def __init__(self, reply):
        self.reply = reply

    def complete(self, system, prompt, max_tokens=4000):
        return self.reply


def test_judge_scores_and_threshold():
    ok = '{"accuracy":5,"clarity":4,"teaching_value":4,"completeness":4,"issues":[]}'
    low = '{"accuracy":2,"clarity":4,"teaching_value":4,"completeness":4,"issues":["wrong call"]}'
    assert quality.judge(FakeLLM(ok), "x", "", CFG)[0].passed is True
    chk, issues = quality.judge(FakeLLM(low), "x", "", CFG)
    assert chk.passed is False and issues == ["wrong call"]
    assert quality.judge(FakeLLM("not json"), "x", "", CFG)[0].passed is None


# --- coderef -------------------------------------------------------------------------


def test_coderef_extracts_and_dedents_region():
    text = "def f():\n    # region: a\n    x = 1\n    if x:\n        y = 2\n    # endregion: a\n"
    assert coderef.extract(text, "a") == "x = 1\nif x:\n    y = 2\n"


def test_coderef_whole_file_strips_markers():
    text = "# region: a\nx = 1\n# endregion: a\n"
    assert coderef.extract(text, None) == "x = 1\n"


def test_coderef_missing_region_raises():
    with pytest.raises(coderef.RegionError):
        coderef.extract("x = 1\n", "nope")


# --- api diff and change routing ------------------------------------------------------


def test_diff_detects_each_kind():
    old = {
        "symbols": {
            "m.f": {"sig": "(a)", "doc_hash": "1"},
            "m.g": {"sig": "()", "doc_hash": "1"},
            "m.h": {"sig": "()", "doc_hash": "1"},
        }
    }
    new = {
        "symbols": {
            "m.f": {"sig": "(a, b)", "doc_hash": "1"},
            "m.h": {"sig": "()", "doc_hash": "2"},
            "m.i": {"sig": "()", "doc_hash": "1"},
        }
    }
    d = api.diff(old, new)
    assert d == {
        "added": ["m.i"],
        "removed": ["m.g"],
        "signature_changed": ["m.f"],
        "docs_changed": ["m.h"],
    }


def test_change_routes_to_only_covering_pages():
    changed = {"splunklib.client.KVStoreCollectionData.insert"}
    pages, examples = generate.affected(MANIFEST, changed)
    assert [p["id"] for p in pages] == ["procedure-kvstore"]
    assert [e["id"] for e in examples] == ["kvstore_notes"]


def test_no_change_affects_nothing():
    assert generate.affected(MANIFEST, set()) == ([], [])


def test_snapshot_ignores_private_names():
    assert not any("._" in k for k in SNAP["symbols"])


# --- loop ------------------------------------------------------------------------------


def _loop(initial, measure, revise, max_iter=3, min_gain=0.02):
    store = {"text": initial}
    out = loop.run(
        "t",
        read=lambda: store["text"],
        write=lambda t: store.update(text=t),
        measure=measure,
        revise=revise,
        max_iterations=max_iter,
        min_improvement=min_gain,
    )
    return out, store["text"]


def _measure(text):
    """Score rises with the number of 'x' characters; gate passes at 3 or more."""
    n = text.count("x")
    rep = quality.Report(
        "t",
        [
            quality.Check("enough_x", "prose", n >= 3, "gate"),
            quality.Check("more_x", "prose", n >= 5, "advisory"),
        ],
    )
    return rep, []


def test_loop_accepts_without_revising_when_clean():
    out, _ = _loop("xxxxx", _measure, lambda *_: "never")
    assert out.status == loop.ACCEPTED_UNREVIEWED and len(out.iterations) == 1


def test_loop_without_model_reports_needs_llm():
    out, _ = _loop("x", _measure, None)
    assert out.status == loop.NEEDS_LLM


def test_loop_revises_then_accepts():
    out, text = _loop("x", _measure, lambda t, r, i: t + "xxxx")
    assert out.status == loop.ACCEPTED_UNREVIEWED and text == "xxxxx"


def test_loop_is_bounded_and_keeps_best():
    calls = []

    def revise(t, r, i):
        calls.append(1)
        return t + "x"  # improves by too little to reach the gate quickly

    out, _ = _loop("", _measure, revise, max_iter=2, min_gain=0.0)
    assert len(calls) <= 2
    assert out.status in {loop.EXHAUSTED, loop.PLATEAU}


def test_loop_discards_regressions():
    out, text = _loop("xx", _measure, lambda t, r, i: "")
    assert text == "xx"  # the worse revision was thrown away
    assert out.status == loop.PLATEAU


def test_report_says_what_was_not_evaluated():
    rep, _ = _measure("xxxxx")
    rep.checks.append(quality.Check("llm_rubric", "judge", None, "gate", detail="skipped"))
    out = loop.Outcome("t", loop.ACCEPTED_UNREVIEWED, "ok", [], rep, [])
    assert "Not evaluated" in loop.render_markdown(out)


def test_loop_repairs_a_broken_page_with_a_model():
    """End to end: bad page in, model revision out, gates re-measured, accepted."""
    broken = GOOD_PAGE + "\n```python\nx = 1\n```\nYou can simply run it.\n"

    def measure(text):
        return page_report(text), []

    llm = FakeLLM(GOOD_PAGE)
    store = {"t": broken}
    out = loop.run(
        "p",
        read=lambda: store["t"],
        write=lambda t: store.update(t=t),
        measure=measure,
        revise=lambda t, r, i: generate.revise_page(llm, t, r, i, PAGE, MANIFEST, SNAP, ROOT),
        max_iterations=3,
        min_improvement=0.02,
    )
    assert out.status == loop.ACCEPTED_UNREVIEWED
    assert out.iterations[0].gate_failures  # the draft really was bad
    assert store["t"] == GOOD_PAGE


# --- model providers --------------------------------------------------------------------


class FakeBedrockClient:
    def __init__(self):
        self.calls = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        return {"output": {"message": {"content": [{"text": "hello "}, {"text": "world"}]}}}


def test_bedrock_proxy_uses_converse_and_joins_text():
    from sdkdocsys.llm import BedrockProxyLLM

    fake = FakeBedrockClient()
    llm = BedrockProxyLLM(model="m", client=fake)
    assert llm.complete("sys", "hi", max_tokens=50) == "hello world"
    call = fake.calls[0]
    assert call["modelId"] == "m" and call["system"] == [{"text": "sys"}]
    assert call["inferenceConfig"] == {"maxTokens": 50}


def test_get_llm_selection(monkeypatch):
    from sdkdocsys import llm as llm_mod

    for var in ("LLM_GATEWAY_TOKEN", "LLM_GATEWAY_URL", "ANTHROPIC_API_KEY", "SDKDOCSYS_PROVIDER"):
        monkeypatch.delenv(var, raising=False)
    assert llm_mod.get_llm() is None
    monkeypatch.setenv("LLM_GATEWAY_TOKEN", "t")
    monkeypatch.setenv("LLM_GATEWAY_URL", "https://gateway.example.test/v1")
    monkeypatch.setattr(llm_mod, "BedrockProxyLLM", lambda: "bedrock")
    assert llm_mod.get_llm() == "bedrock"


# --- reviewer inputs and score ------------------------------------------------------


def test_expand_coderefs_inlines_code_for_the_reviewer():
    out = quality.expand_coderefs(GOOD_PAGE, ROOT)
    assert ":::{coderef}" not in out
    assert "[CODE from examples/oneshot_search.py, region search]" in out
    assert "service.jobs.oneshot" in out


def test_properties_are_marked_in_api_facts_and_setters_skipped():
    assert SNAP["symbols"]["splunklib.client.Service.info"]["kind"] == "property"
    facts = quality.api_facts(SNAP, ["splunklib.client.Service"])
    assert "Service.info (property" in facts
    assert "Service.kvstore_owner (property" in facts  # one entry despite a setter


def test_reviewer_scores_count_continuously():
    def rep(scores):
        return quality.Report("t", [quality.Check("llm_rubric", "judge", False, "gate", scores)])

    assert rep({"a": 3.0, "b": 3.0}).score > rep({"a": 2.0, "b": 2.0}).score
    assert rep({"a": 5.0}).score == 1.0 and rep({"a": 1.0}).score == 0.0


def test_usage_meter_counts_calls_and_tokens():
    from sdkdocsys import llm as llm_mod
    from sdkdocsys.llm import BedrockProxyLLM

    before = dict(llm_mod.USAGE)

    class Client:
        def converse(self, **kwargs):
            return {
                "output": {"message": {"content": [{"text": "x"}]}},
                "usage": {"inputTokens": 120, "outputTokens": 30},
            }

    BedrockProxyLLM(model="m", client=Client()).complete("s", "p")
    assert llm_mod.USAGE["calls"] == before["calls"] + 1
    assert llm_mod.USAGE["input"] == before["input"] + 120
    assert llm_mod.USAGE["output"] == before["output"] + 30
    assert "calls" in llm_mod.usage_summary()
