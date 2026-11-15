"""Quality measurement: deterministic checks plus an optional LLM rubric.

Every check is a ``Check`` with a severity. ``gate`` checks decide acceptance;
``advisory`` checks only lower the score. A check that could not run (no model key,
ruff missing) is recorded as skipped, never as passed, so reports stay honest.
"""

from __future__ import annotations

import ast
import contextlib
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import api, coderef
from .llm import LLM, extract_json

GATE_WEIGHT, ADVISORY_WEIGHT = 1.0, 0.25


@dataclass
class Check:
    name: str
    category: str  # prose | code | coverage | judge
    passed: bool | None  # None = skipped
    severity: str = "gate"  # gate | advisory
    value: Any = None
    threshold: Any = None
    detail: str = ""


@dataclass
class Report:
    artifact: str
    checks: list[Check] = field(default_factory=list)

    @property
    def gates_ok(self) -> bool:
        return all(c.passed for c in self.checks if c.severity == "gate" and c.passed is not None)

    @property
    def failing(self) -> list[Check]:
        return [c for c in self.checks if c.passed is False]

    @property
    def skipped(self) -> list[Check]:
        return [c for c in self.checks if c.passed is None]

    @property
    def score(self) -> float:
        """Weighted pass fraction over checks that actually ran (0..1)."""
        total = earned = 0.0
        for c in self.checks:
            if c.passed is None:
                continue
            w = GATE_WEIGHT if c.severity == "gate" else ADVISORY_WEIGHT
            total += w
            if c.category == "judge" and isinstance(c.value, dict) and c.value:
                # Reviewer scores count continuously, so 2 -> 3 out of 5 registers as progress.
                mean = sum(c.value.values()) / len(c.value)
                earned += w * min(1.0, max(0.0, (mean - 1) / 4))
            else:
                earned += w if c.passed else 0.0
        return earned / total if total else 0.0


def load_config(path: Path) -> dict:
    return tomllib.loads(path.read_text())


# --------------------------------------------------------------------------- prose

_OPEN = re.compile(r"^\s*:{3,}\{(?P<name>[\w-]+)\}\s*(?P<arg>.*)$")
_CLOSE = re.compile(r"^\s*:{3,}\s*$")
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})\s*(?P<lang>[\w+-]*)")


def parse_markdown(md: str) -> dict:
    """Split a MyST page into prose, headings, coderef calls and fenced blocks."""
    lines = md.splitlines()
    if lines and lines[0].strip() == "---":  # front matter
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), 0)
        lines = lines[end + 1 :]
    prose: list[str] = []
    headings: list[str] = []
    refs: list[tuple[str, str | None]] = []
    fences: list[str] = []
    in_fence = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if in_fence:
            in_fence = not _FENCE.match(line)
            i += 1
            continue
        if m := _FENCE.match(line):
            in_fence = True
            fences.append(m["lang"])
            i += 1
            continue
        if (m := _OPEN.match(line)) and m["name"] == "coderef":
            region = None
            i += 1
            while i < len(lines) and not _CLOSE.match(lines[i]):
                if rm := re.match(r"^\s*:region:\s*(\S+)", lines[i]):
                    region = rm.group(1)
                i += 1
            refs.append((m["arg"].strip(), region))
            i += 1
            continue
        if _OPEN.match(line) or _CLOSE.match(line):
            i += 1
            continue
        if hm := re.match(r"^(#{1,6})\s+(.*)$", line):
            headings.append(f"{len(hm.group(1))}|{hm.group(2).strip()}")
            i += 1
            continue
        prose.append(line)
        i += 1
    text = "\n".join(prose)
    return {"prose": text, "headings": headings, "refs": refs, "fences": fences}


def _clean_for_reading(prose: str) -> str:
    text = re.sub(r"`[^`]*`", "code", prose)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^\s*(?:[-*]|\d+[.)])\s+", "", text, flags=re.MULTILINE)
    return text


def _sentences(text: str) -> list[str]:
    out: list[str] = []
    for para in re.split(r"\n\s*\n|\n", text):
        para = para.strip()
        if not para:
            continue
        parts = re.split(r"(?<=[.!?])\s+", para)
        out.extend(p for p in parts if re.search(r"[A-Za-z]", p))
    return out


def _syllables(word: str) -> int:
    word = word.lower()
    count = len(re.findall(r"[aeiouy]+", word))
    if word.endswith("e") and not word.endswith("le") and count > 1:
        count -= 1
    return max(count, 1)


def readability(prose: str) -> dict[str, float]:
    text = _clean_for_reading(prose)
    sents = _sentences(text)
    words = re.findall(r"[A-Za-z']+", text)
    if not sents or not words:
        return {"flesch": 0.0, "fk_grade": 0.0, "avg_sentence": 0.0, "max_sentence": 0.0}
    syl = sum(_syllables(w) for w in words)
    wps, spw = len(words) / len(sents), syl / len(words)
    lengths = [len(re.findall(r"[A-Za-z']+", s)) for s in sents]
    return {
        "flesch": 206.835 - 1.015 * wps - 84.6 * spw,
        "fk_grade": 0.39 * wps + 11.8 * spw - 15.59,
        "avg_sentence": wps,
        "max_sentence": float(max(lengths)),
    }


def check_page(
    md: str,
    page: dict,
    cfg: dict,
    snap: api.Snapshot,
    docsys_root: Path,
    examples: dict[str, dict],
) -> Report:
    """Deterministic checks for one page. ``page`` is its manifest entry."""
    p = cfg["prose"]
    parsed = parse_markdown(md)
    rep = Report(artifact=page["id"])
    add = rep.checks.append

    bad_fences = [lang for lang in parsed["fences"] if lang not in p["allowed_fence_langs"]]
    add(
        Check(
            "no_embedded_code",
            "prose",
            not bad_fences,
            "gate",
            len(bad_fences),
            p["max_fenced_blocks"],
            "code must live in examples/ and be pulled in with coderef",
        )
    )

    found = [
        t
        for t in p["banned_terms"]
        if re.search(rf"(?<!\w){re.escape(t)}(?!\w)", parsed["prose"], re.IGNORECASE)
    ]
    add(
        Check(
            "banned_terms",
            "prose",
            not found,
            "gate",
            ", ".join(found) or 0,
            0,
            "weasel words and em-dashes are not allowed",
        )
    )

    h1 = [h for h in parsed["headings"] if h.startswith("1|")]
    add(Check("single_h1", "prose", len(h1) == 1, "gate", len(h1), 1))
    titles = " ".join(h.split("|", 1)[1].lower() for h in parsed["headings"])
    required = p["required_sections"].get(page["kind"], [])
    missing = [s for s in required if s not in titles]
    add(
        Check(
            "required_sections",
            "prose",
            not missing,
            "gate",
            ", ".join(missing) or "ok",
            ", ".join(required),
            f"{page['kind']} pages need these sections",
        )
    )

    r = readability(parsed["prose"])
    add(
        Check(
            "flesch_reading_ease",
            "prose",
            r["flesch"] >= p["min_flesch"],
            "gate",
            round(r["flesch"], 1),
            p["min_flesch"],
        )
    )
    add(
        Check(
            "fk_grade",
            "prose",
            r["fk_grade"] <= p["max_fk_grade"],
            "advisory",
            round(r["fk_grade"], 1),
            p["max_fk_grade"],
        )
    )
    add(
        Check(
            "avg_sentence_words",
            "prose",
            r["avg_sentence"] <= p["max_avg_sentence_words"],
            "advisory",
            round(r["avg_sentence"], 1),
            p["max_avg_sentence_words"],
        )
    )
    add(
        Check(
            "max_sentence_words",
            "prose",
            r["max_sentence"] <= p["max_sentence_words"],
            "advisory",
            int(r["max_sentence"]),
            p["max_sentence_words"],
        )
    )

    unresolved = []
    for rel, region in parsed["refs"]:
        f = docsys_root / rel
        if not f.is_file():
            unresolved.append(f"{rel} (missing)")
        elif region and region not in coderef.list_regions(f.read_text()):
            unresolved.append(f"{rel}#{region} (no such region)")
    add(Check("coderef_resolves", "prose", not unresolved, "gate", "; ".join(unresolved) or "ok"))

    min_refs = 1
    add(
        Check(
            "has_code_examples",
            "prose",
            len(parsed["refs"]) >= min_refs,
            "gate" if page["kind"] == "procedure" else "advisory",
            len(parsed["refs"]),
            min_refs,
        )
    )

    tokens = set(re.findall(r"`([^`\n]+)`", md))
    bogus = sorted(
        t for t in tokens if re.fullmatch(r"splunklib(\.\w+)+", t) and t not in snap["symbols"]
    )
    add(
        Check(
            "symbol_refs_exist",
            "coverage",
            not bogus,
            "gate",
            ", ".join(bogus) or "ok",
            detail="every `splunklib.x.y` in the text must exist in the API snapshot",
        )
    )

    cleaned = {re.sub(r"\(.*\)$", "", t) for t in tokens}
    used: set[str] = set()
    for ex_id in page.get("examples", []):
        ex = examples.get(ex_id)
        if ex and (docsys_root / ex["path"]).is_file():
            used |= names_used(docsys_root / ex["path"])
    unmentioned, unexercised = [], []
    for sym in page.get("key_symbols", []):
        parts = sym.split(".")
        kind = snap["symbols"].get(sym, {}).get("kind", "function")
        accepted = {sym, ".".join(parts[-2:])}
        if kind in ("class", "function", "module"):
            accepted.add(parts[-1])
        if not accepted & cleaned:
            unmentioned.append(sym)
        if parts[-1] not in used:
            unexercised.append(sym)
    add(
        Check(
            "key_symbols_explained",
            "coverage",
            not unmentioned,
            "gate",
            ", ".join(unmentioned) or "ok",
            detail="manifest key_symbols named in the prose",
        )
    )
    add(
        Check(
            "key_symbols_exercised",
            "coverage",
            not unexercised,
            "gate",
            ", ".join(unexercised) or "ok",
            detail="manifest key_symbols used by an example",
        )
    )
    return rep


# --------------------------------------------------------------------------- code


def names_used(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return set()  # the example's own "parses" gate reports it; a page must not crash on it
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.Name):
            names.add(node.id)
    return names


def _module_aliases(tree: ast.AST) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.startswith("splunklib"):
                    aliases[a.asname or a.name] = a.name
        elif (
            isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("splunklib")
        ):
            for a in node.names:
                aliases[a.asname or a.name] = f"{node.module}.{a.name}"
    return aliases


def _ruff(args: list[str], path: Path) -> tuple[bool | None, str]:
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "ruff", *args, str(path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"ruff unavailable: {exc}"
    if "No module named ruff" in proc.stderr:
        return None, "ruff not installed"
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()[-400:]


def check_example(path: Path, cfg: dict, snap: api.Snapshot) -> Report:
    c = cfg["code"]
    text = path.read_text()
    rep = Report(artifact=path.stem)
    add = rep.checks.append
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        add(Check("parses", "code", False, "gate", detail=str(exc)))
        return rep
    add(Check("parses", "code", True, "gate"))

    doc = ast.get_docstring(tree) or ""
    need = [k for k in ("Goal:", "Prerequisites:", "Run:") if k not in doc]
    add(
        Check(
            "header_docstring",
            "code",
            not need,
            "gate",
            ", ".join(need) or "ok",
            detail="module docstring needs Goal:, Prerequisites:, Run:",
        )
    )

    has_main = any(isinstance(n, ast.FunctionDef) and n.name == "main" for n in tree.body)
    has_guard = '__name__ == "__main__"' in text or "__name__ == '__main__'" in text
    add(
        Check(
            "entrypoint",
            "code",
            has_main and has_guard,
            "gate",
            detail="needs main() and an if __name__ == '__main__' guard (no work at import)",
        )
    )

    regions = coderef.list_regions(text)
    ends = re.findall(r"^\s*#\s*endregion:\s*([\w.-]+)", text, re.MULTILINE)
    add(
        Check(
            "regions_balanced",
            "code",
            bool(regions) and sorted(regions) == sorted(ends),
            "gate",
            len(regions),
            ">=1",
            "regions mark the lines docs pull in",
        )
    )

    imported = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imported |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            imported.add(n.module.split(".")[0])
    foreign = sorted(imported - set(sys.stdlib_module_names) - {"splunklib"})
    add(
        Check(
            "self_contained",
            "code",
            not foreign,
            "gate",
            ", ".join(foreign) or "ok",
            detail="copy/paste runnable: stdlib and splunklib only",
        )
    )

    missing = []
    for alias, target in _module_aliases(tree).items():
        for n in ast.walk(tree):
            if (
                isinstance(n, ast.Attribute)
                and isinstance(n.value, ast.Name)
                and n.value.id == alias
            ):
                sym = f"{target}.{n.attr}"
                if (
                    target in snap["symbols"]
                    and snap["symbols"][target]["kind"] == "module"
                    and sym not in snap["symbols"]
                ):
                    missing.append(sym)
    add(
        Check(
            "splunklib_symbols_exist",
            "code",
            not missing,
            "gate",
            ", ".join(sorted(set(missing))) or "ok",
            detail="module-level API used must exist",
        )
    )

    secrets = [
        n.lineno
        for n in ast.walk(tree)
        if isinstance(n, ast.keyword)
        and n.arg in ("password", "token", "bearer_token", "sessionKey")
        and isinstance(n.value, ast.Constant)
        and isinstance(n.value.value, str)
    ]
    add(Check("no_hardcoded_secrets", "code", not secrets, "gate", secrets or "ok"))

    ok, detail = _ruff(["check", "--no-cache"], path)
    add(Check("ruff_lint", "code", ok, "gate", detail=detail if ok is not True else ""))
    ok, detail = _ruff(["format", "--check", "--no-cache"], path)
    add(Check("ruff_format", "code", ok, "advisory", detail=detail if ok is not True else ""))

    n_lines = len(text.splitlines())
    add(Check("length", "code", n_lines <= c["max_lines"], "gate", n_lines, c["max_lines"]))
    sizes = []
    for r in regions:
        # An unbalanced region is reported by regions_balanced; do not crash the measurement.
        with contextlib.suppress(coderef.RegionError):
            sizes.append(len(coderef.extract(text, r).splitlines()))
    longest = max(sizes, default=0)
    add(
        Check(
            "region_length",
            "code",
            longest <= c["max_region_lines"],
            "advisory",
            longest,
            c["max_region_lines"],
        )
    )
    branches = sum(
        isinstance(n, ast.If | ast.For | ast.While | ast.Try | ast.BoolOp) for n in ast.walk(tree)
    )
    add(
        Check(
            "complexity",
            "code",
            branches <= c["max_branches"],
            "advisory",
            branches,
            c["max_branches"],
        )
    )
    add(
        Check(
            "env_config",
            "code",
            "os.environ" in text or "getenv" in text,
            "advisory",
            detail="connection settings should come from the environment",
        )
    )
    return rep


# --------------------------------------------------------------------------- judge

JUDGE_SYSTEM = (
    "You are a strict technical-documentation reviewer for the Splunk Python SDK. "
    "Score the artifact against the API facts supplied. Reply with one JSON object only: "
    '{"accuracy": 1-5, "clarity": 1-5, "teaching_value": 1-5, "completeness": 1-5, '
    '"issues": ["short, specific, fixable problems"]}. '
    "accuracy: every claim and call matches the API facts. teaching_value: the reader learns "
    "a realistic scenario, not just syntax. Do not praise; list at most 5 concrete problems, "
    "each under 30 words, most important first. Output the JSON object and nothing else."
)


def judge(
    llm: LLM | None, artifact_text: str, api_facts: str, cfg: dict
) -> tuple[Check, list[str]]:
    if llm is None:
        return Check(
            "llm_rubric",
            "judge",
            None,
            "gate",
            detail="skipped: no LLM_GATEWAY_TOKEN or ANTHROPIC_API_KEY, so no model review ran",
        ), []
    try:
        raw = llm.complete(
            JUDGE_SYSTEM, f"API FACTS:\n{api_facts}\n\nARTIFACT:\n{artifact_text}", max_tokens=2500
        )
        data = extract_json(raw)
        scores = {d: float(data[d]) for d in cfg["judge"]["dimensions"]}
    except Exception as exc:  # noqa: BLE001 - a flaky judge must not crash the pipeline
        return Check(
            "llm_rubric", "judge", None, "gate", detail=f"skipped: judge failed: {exc}"
        ), []
    low = {d: s for d, s in scores.items() if s < cfg["judge"]["min_score"]}
    return (
        Check(
            "llm_rubric",
            "judge",
            not low,
            "gate",
            scores,
            cfg["judge"]["min_score"],
            "below threshold: " + ", ".join(low) if low else "",
        ),
        [str(i) for i in data.get("issues", [])],
    )


def api_facts(
    snap: api.Snapshot, prefixes: list[str], limit: int = 120, focus: list[str] | None = None
) -> str:
    """API facts for the reviewer. Symbols named in ``focus`` also get their docstring."""
    focus = focus or []

    def wanted(sym: str) -> bool:
        return any(sym == f or sym.endswith("." + f) for f in focus)

    blocks: list[str] = []
    for k, e in snap["symbols"].items():
        if e["kind"] not in ("class", "function", "method", "property") or not api.covers(
            prefixes, k
        ):
            continue
        if e["kind"] == "property":
            line = f"{k} (property: access without parentheses)"
        elif e["kind"] == "class" and e.get("protocols"):
            line = f"{k} (class; supports {', '.join(e['protocols'])})"
        else:
            line = f"{k}{e['sig']}"
        if wanted(k) and e.get("doc"):
            line += "\n    docs: " + " ".join(e["doc"].split())
        blocks.append(line)
    return "\n".join(blocks[:limit])


def expand_coderefs(md: str, root: Path) -> str:
    """Replace each coderef directive with the code it pulls in, for the model reviewer.

    Pages hold references, not code. A reviewer that only sees the references cannot judge
    whether the prose matches the example, so it reviews the page as a reader sees it.
    """
    lines, out, i = md.splitlines(), [], 0
    while i < len(lines):
        m = _OPEN.match(lines[i])
        if not (m and m["name"] == "coderef"):
            out.append(lines[i])
            i += 1
            continue
        region, i = None, i + 1
        while i < len(lines) and not _CLOSE.match(lines[i]):
            if rm := re.match(r"^\s*:region:\s*(\S+)", lines[i]):
                region = rm.group(1)
            i += 1
        i += 1
        rel = m["arg"].strip()
        try:
            code = coderef.extract((root / rel).read_text(), region)
        except (OSError, coderef.RegionError):
            code = "(could not resolve this code reference)\n"
        out.append(f"[CODE from {rel}" + (f", region {region}]" if region else "]"))
        out.extend("    " + ln for ln in code.splitlines())
        out.append("[END CODE]")
    return "\n".join(out)
