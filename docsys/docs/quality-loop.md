# The validate-and-improve phase

A first draft is not documentation. This phase turns a draft into a final draft you can
defend, without chasing perfection forever.

## What gets measured

| Category | Checks (gate = blocks acceptance, advisory = lowers score only) |
|---|---|
| Prose | No embedded code (gate), no banned terms (gate), one H1 and required sections per page kind (gate), Flesch reading ease (gate), grade level, average and maximum sentence length (advisory) |
| Code | Parses, header docstring, `main()` plus guard, balanced regions, stdlib and `splunklib` only, no hard-coded secrets, module-level API exists, ruff lint, length (gates); ruff format, region length, complexity, env-based config (advisory) |
| Coverage | Every `splunklib.x.y` named in prose exists (gate); each manifest `key_symbol` is named in the page and exercised by an example (gates) |
| Model rubric | Accuracy, clarity, teaching value, completeness, each 1-5 against the API facts, with a minimum score (gate) |

Thresholds are in `quality.toml`. They are modest on purpose: a known, explained floor.

## The loop

```text
measure draft
  gates pass and nothing else fails?  -> accept
  no model available?                 -> stop, report needs_llm (or accept_unreviewed if gates pass)
  budget spent?                       -> stop, report why
  ask the model to fix the listed problems -> measure again
  better?  keep it.  worse?  discard it and stop.
  gain below min_improvement?         -> stop (plateau)
```

Three things bound the loop, so it cannot run forever:

1. `max_iterations` revision passes (default 3).
2. A plateau stop when a pass gains less than `min_improvement` (default 0.02).
3. A regression stop: a revision that scores worse is thrown away, and the best version wins.

The score is the weighted pass fraction over checks that actually ran: gates count 1.0,
advisory checks 0.25. Skipped checks are excluded and listed.

## Final statuses

| Status | Meaning |
|---|---|
| `accepted` | All gates pass and the model review ran and passed |
| `accepted_unreviewed` | Deterministic gates pass; model review did not run |
| `needs_llm` | Gates fail and no model is available to revise |
| `needs_human_plateau` | Revisions stopped helping while gates still fail |
| `needs_human_budget` | Budget spent while gates still fail |

CI fails on the three `needs_*` statuses and passes the accepted ones.

## The justification report

Each artifact gets `reports/<id>.md` and `.json` with: the status and why the loop stopped,
the score per pass, which checks failed on which pass and what the model changed, the final
check table, open reviewer issues, and a "Not evaluated" section naming anything that did not
run. A reader can see why the draft is final and what it does not vouch for.

## What this does not prove

Passing means the draft meets the stated rules. It does not prove the examples work against a
live Splunk or that a reader finds the page helpful. Live example runs and reader feedback are
the next signals to add.
