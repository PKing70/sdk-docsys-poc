# Quality justification: oneshot_search

**Status:** `needs_human_plateau`  
**Why it stopped:** gain +0.017 below 0.02; gates still fail  
**Final score:** 0.98 (weighted pass rate over checks that ran)

## Iterations

| Pass | Score | Gate failures | Advisory failures | Skipped | Action |
|---|---|---|---|---|---|
| 0 | 0.96 | llm_rubric | - | - | initial draft |
| 1 | 0.977 | llm_rubric | - | - | revision kept (score +0.017) |

## Final checks

| Check | Severity | Result |
|---|---|---|
| parses | gate | pass |
| header_docstring | gate | pass (ok) |
| entrypoint | gate | pass |
| regions_balanced | gate | pass (2 vs >=1) |
| self_contained | gate | pass (ok) |
| splunklib_symbols_exist | gate | pass (ok) |
| no_hardcoded_secrets | gate | pass (ok) |
| ruff_lint | gate | pass |
| ruff_format | advisory | pass |
| length | gate | pass (74 vs 90) |
| region_length | advisory | pass (17 vs 30) |
| complexity | advisory | pass (5 vs 12) |
| env_config | advisory | pass |
| llm_rubric | gate | FAIL ({'accuracy': 4.0, 'clarity': 5.0, 'teaching_value': 4.0, 'completeness': 3.0} vs 3.5) - below threshold: completeness |

## Open reviewer issues

- Default query is described as `search index=_internal | stats count by sourcetype`, but DEFAULT_QUERY adds `| sort - count`; the Run usage line and code disagree.
- Claims oneshot 'creates no job you have to clean up' and 'default cap is 100 rows' are not in the API facts; the 100-row default is actually 100 for oneshot only by convention and is unverified here.
- Only HTTPError wraps the search; the read loop can raise parsing/network errors, and closing() isn't paired with exception handling. Bad SPL may surface during iteration rather than at call time.
- Does not demonstrate or contrast Jobs.export or Jobs.create with code, though it mentions them; the 'separate result rows from messages' goal is shown only superficially.
- Imports AuthenticationError and HTTPError from splunklib.binding, which is outside the supplied API facts, and `Message.type`/`.message` attributes are used without being confirmed.
