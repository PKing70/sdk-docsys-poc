# Quality justification: procedure-send-and-find

**Status:** `needs_human_plateau`  
**Why it stopped:** gain +0.005 below 0.02; gates still fail  
**Final score:** 0.97 (weighted pass rate over checks that ran)

## Iterations

| Pass | Score | Gate failures | Advisory failures | Skipped | Action |
|---|---|---|---|---|---|
| 0 | 0.963 | llm_rubric | - | - | initial draft |
| 1 | 0.968 | llm_rubric | - | - | revision kept (score +0.005) |

## Final checks

| Check | Severity | Result |
|---|---|---|
| no_embedded_code | gate | pass (0 vs 0) |
| banned_terms | gate | pass (0 vs 0) |
| single_h1 | gate | pass (1 vs 1) |
| required_sections | gate | pass (ok vs prerequisites, steps, verify) |
| flesch_reading_ease | gate | pass (79.9 vs 30) |
| fk_grade | advisory | pass (5.1 vs 13) |
| avg_sentence_words | advisory | pass (11.9 vs 24) |
| max_sentence_words | advisory | pass (26 vs 45) |
| coderef_resolves | gate | pass (ok) |
| has_code_examples | gate | pass (4 vs 1) |
| symbol_refs_exist | gate | pass (ok) |
| key_symbols_explained | gate | pass (ok) |
| key_symbols_exercised | gate | pass (ok) |
| llm_rubric | gate | FAIL ({'accuracy': 3.0, 'clarity': 4.0, 'teaching_value': 4.0, 'completeness': 3.0} vs 3.5) - below threshold: accuracy, completeness |

## Open reviewer issues

- The roll_hot_buckets advice is misleading: hot-bucket events are already searchable, so rolling them to warm will not fix an empty search. Remove it or explain its real purpose.
- Step 1 says create returns an Index to use next, but the code discards that return value and re-fetches with service.indexes[INDEX]. Prose and code disagree.
- The default limit of 100 results for oneshot is not backed by the API facts, and the loop itself never passes count=0. State the source or soften the claim.
- The rerun advice conflicts with the loop. A leftover index already holds events, so the loop exits early with a wrong count, and `Found 3 of 3` is not guaranteed. Suggest Index.clean at the start.
- The guide omits Index.attach, attached_socket and upload for bulk or streaming ingest, so readers do not learn when per-event submit is the wrong tool.
