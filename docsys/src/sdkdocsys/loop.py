"""The bounded improve loop and its justification report.

measure -> (accept | revise) -> measure ... capped by ``max_iterations``.
The loop keeps the best version seen, stops early on a plateau, and always writes a
report that says what was measured, what changed, why it stopped, and what remains.
It never loops forever: finite budget, explicit stop reason.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from .quality import Check, Report

# Final statuses, strongest first.
ACCEPTED = "accepted"  # every gate passed (and the model review ran and passed)
ACCEPTED_UNREVIEWED = "accepted_unreviewed"  # deterministic gates pass, model review skipped
NEEDS_LLM = "needs_llm"  # gates fail and no model is available to revise
PLATEAU = "needs_human_plateau"  # revisions stopped helping while gates still fail
EXHAUSTED = "needs_human_budget"  # iteration budget spent while gates still fail


@dataclass
class Iteration:
    n: int
    score: float
    gate_failures: list[str]
    advisory_failures: list[str]
    skipped: list[str]
    action: str


@dataclass
class Outcome:
    artifact: str
    status: str
    reason: str
    iterations: list[Iteration]
    final: Report
    judge_issues: list[str]


def _final_status(rep: Report) -> str:
    judged = any(c.category == "judge" and c.passed is True for c in rep.checks)
    return ACCEPTED if judged else ACCEPTED_UNREVIEWED


def run(
    name: str,
    *,
    read: Callable[[], str],
    write: Callable[[str], None],
    measure: Callable[[str], tuple[Report, list[str]]],
    revise: Callable[[str, Report, list[str]], str] | None,
    max_iterations: int,
    min_improvement: float,
) -> Outcome:
    """Run the loop for one artifact. ``revise`` is None when no model is available."""
    best_text = read()
    report, issues = measure(best_text)
    best_report, best_issues = report, issues
    history: list[Iteration] = []

    def log(n: int, rep: Report, action: str) -> None:
        history.append(
            Iteration(
                n,
                round(rep.score, 3),
                [c.name for c in rep.failing if c.severity == "gate"],
                [c.name for c in rep.failing if c.severity == "advisory"],
                [c.name for c in rep.skipped],
                action,
            )
        )

    def finish(status: str, reason: str) -> Outcome:
        write(best_text)
        return Outcome(name, status, reason, history, best_report, best_issues)

    log(0, report, "initial draft")
    for n in range(1, max_iterations + 2):
        clean = best_report.gates_ok and not [c for c in best_report.failing]
        if best_report.gates_ok and (clean or revise is None):
            return finish(
                _final_status(best_report),
                "all gates pass" + ("" if clean else "; advisory items remain (see report)"),
            )
        if revise is None:
            return finish(NEEDS_LLM, "gates failing and no model available to revise")
        if n > max_iterations:
            if best_report.gates_ok:
                return finish(
                    _final_status(best_report),
                    f"iteration budget ({max_iterations}) spent; advisory items remain",
                )
            return finish(EXHAUSTED, f"iteration budget ({max_iterations}) spent, gates still fail")
        candidate = revise(best_text, best_report, best_issues)
        cand_report, cand_issues = measure(candidate)
        gain = cand_report.score - best_report.score
        if cand_report.score > best_report.score or (
            cand_report.gates_ok and not best_report.gates_ok
        ):
            log(n, cand_report, f"revision kept (score {gain:+.3f})")
            best_text, best_report, best_issues = candidate, cand_report, cand_issues
            if gain < min_improvement and not best_report.gates_ok:
                return finish(
                    PLATEAU, f"gain {gain:+.3f} below {min_improvement}; gates still fail"
                )
            if gain < min_improvement and best_report.gates_ok:
                return finish(
                    _final_status(best_report),
                    f"gain {gain:+.3f} below {min_improvement}; stopped polishing",
                )
        else:
            log(n, cand_report, f"revision discarded (score {gain:+.3f})")
            return finish(
                PLATEAU if not best_report.gates_ok else _final_status(best_report),
                "revision did not improve the best draft; stopped",
            )
    return finish(EXHAUSTED, "unreachable")  # pragma: no cover


# ------------------------------------------------------------------------- reporting


def _check_line(c: Check) -> str:
    state = {True: "pass", False: "FAIL", None: "skipped"}[c.passed]
    val = (
        f" ({c.value}" + (f" vs {c.threshold})" if c.threshold not in (None, "") else ")")
        if c.value not in (None, "")
        else ""
    )
    note = f" - {c.detail}" if c.detail and c.passed is not True else ""
    return f"| {c.name} | {c.severity} | {state}{val}{note} |"


def render_markdown(o: Outcome) -> str:
    lines = [
        f"# Quality justification: {o.artifact}",
        "",
        f"**Status:** `{o.status}`  ",
        f"**Why it stopped:** {o.reason}  ",
        f"**Final score:** {o.final.score:.2f} (weighted pass rate over checks that ran)",
        "",
        "## Iterations",
        "",
        "| Pass | Score | Gate failures | Advisory failures | Skipped | Action |",
        "|---|---|---|---|---|---|",
    ]
    for it in o.iterations:
        lines.append(
            f"| {it.n} | {it.score} | {', '.join(it.gate_failures) or '-'} | "
            f"{', '.join(it.advisory_failures) or '-'} | "
            f"{', '.join(it.skipped) or '-'} | {it.action} |"
        )
    lines += ["", "## Final checks", "", "| Check | Severity | Result |", "|---|---|---|"]
    lines += [_check_line(c) for c in o.final.checks]
    if o.judge_issues:
        lines += ["", "## Open reviewer issues", ""] + [f"- {i}" for i in o.judge_issues]
    skipped = [c.name for c in o.final.skipped]
    if skipped:
        lines += [
            "",
            "## Not evaluated",
            "",
            "These checks did not run, so this result does not vouch for them: "
            + ", ".join(skipped)
            + ".",
        ]
    return "\n".join(lines) + "\n"


def write_reports(o: Outcome, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "artifact": o.artifact,
        "status": o.status,
        "reason": o.reason,
        "score": round(o.final.score, 3),
        "iterations": [asdict(i) for i in o.iterations],
        "checks": [asdict(c) for c in o.final.checks],
        "judge_issues": o.judge_issues,
    }
    (out_dir / f"{o.artifact}.json").write_text(json.dumps(data, indent=1, default=str) + "\n")
    (out_dir / f"{o.artifact}.md").write_text(render_markdown(o))
