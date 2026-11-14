# Quality justification: concept-connecting

**Status:** `needs_human_plateau`  
**Why it stopped:** revision did not improve the best draft; stopped  
**Final score:** 0.96 (weighted pass rate over checks that ran)

## Iterations

| Pass | Score | Gate failures | Advisory failures | Skipped | Action |
|---|---|---|---|---|---|
| 0 | 0.96 | llm_rubric | - | - | initial draft |
| 1 | 0.949 | llm_rubric | - | - | revision discarded (score -0.011) |

## Final checks

| Check | Severity | Result |
|---|---|---|
| no_embedded_code | gate | pass (0 vs 0) |
| banned_terms | gate | pass (0 vs 0) |
| single_h1 | gate | pass (1 vs 1) |
| required_sections | gate | pass (ok vs how it works, when to use) |
| flesch_reading_ease | gate | pass (76.9 vs 30) |
| fk_grade | advisory | pass (5.4 vs 13) |
| avg_sentence_words | advisory | pass (11.6 vs 24) |
| max_sentence_words | advisory | pass (22 vs 45) |
| coderef_resolves | gate | pass (ok) |
| has_code_examples | advisory | pass (2 vs 1) |
| symbol_refs_exist | gate | pass (ok) |
| key_symbols_explained | gate | pass (ok) |
| key_symbols_exercised | gate | pass (ok) |
| llm_rubric | gate | FAIL ({'accuracy': 3.0, 'clarity': 4.0, 'teaching_value': 3.0, 'completeness': 3.0} vs 3.5) - below threshold: accuracy, teaching_value, completeness |

## Open reviewer issues

- The facts list splunklib.client.connect(**kwargs) but give no parameter defaults, token/cookie options, or autologin behavior. Claims about localhost/8089/https defaults, autologin, and token/cookie are unverified.
- The explanation that connect sends credentials and stores a session token in one round trip is unsupported by the facts; the facts only show Context.login/connect.
- The snippet uses AuthenticationError and `client` without imports, though the facts place AuthenticationError in splunklib.binding. As written, the except clause would raise NameError.
- The claim that an object saved in the `search` app is invisible from another app oversimplifies namespace and sharing. Sharing levels like global or system make objects visible across apps.
- The 'inside a Splunk app' advice is vague. It never names how to build a Service from an existing session, and the facts show no API for it.
