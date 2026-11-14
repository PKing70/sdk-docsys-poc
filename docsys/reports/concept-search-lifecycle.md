# Quality justification: concept-search-lifecycle

**Status:** `needs_human_plateau`  
**Why it stopped:** revision did not improve the best draft; stopped  
**Final score:** 0.95 (weighted pass rate over checks that ran)

## Iterations

| Pass | Score | Gate failures | Advisory failures | Skipped | Action |
|---|---|---|---|---|---|
| 0 | 0.955 | llm_rubric | - | - | initial draft |
| 1 | 0.869 | banned_terms, llm_rubric | - | - | revision discarded (score -0.085) |

## Final checks

| Check | Severity | Result |
|---|---|---|
| no_embedded_code | gate | pass (0 vs 0) |
| banned_terms | gate | pass (0 vs 0) |
| single_h1 | gate | pass (1 vs 1) |
| required_sections | gate | pass (ok vs how it works, when to use) |
| flesch_reading_ease | gate | pass (83.0 vs 30) |
| fk_grade | advisory | pass (5.0 vs 13) |
| avg_sentence_words | advisory | pass (13.3 vs 24) |
| max_sentence_words | advisory | pass (26 vs 45) |
| coderef_resolves | gate | pass (ok) |
| has_code_examples | advisory | pass (2 vs 1) |
| symbol_refs_exist | gate | pass (ok) |
| key_symbols_explained | gate | pass (ok) |
| key_symbols_exercised | gate | pass (ok) |
| llm_rubric | gate | FAIL ({'accuracy': 3.0, 'clarity': 3.0, 'teaching_value': 3.0, 'completeness': 3.0} vs 3.5) - below threshold: accuracy, clarity, teaching_value, completeness |

## Open reviewer issues

- "Both styles return a raw stream" is wrong: Jobs.create returns a Job. Only Jobs.oneshot and Job.results return streams, and the text never shows calling Job.results.
- Prose says to cancel the job when the deadline passes, but the poll code raises SystemExit without calling job.cancel(), leaving the job running.
- The claim that is_done is only meaningful after is_ready, and that checking both keeps state fresh, is unsupported by the API facts. The combined loop condition is redundant and misleading.
- No snippet passes output_mode="json" to oneshot or Job.results, so the reader setup is incomplete. The `closing` import and the stream's origin are also missing.
- The tradeoffs omit Jobs.export for large streaming results, and Job.set_ttl and Job.pause for managing job lifetime and resources.
