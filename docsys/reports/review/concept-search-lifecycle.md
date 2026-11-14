# Review (read-only): concept-search-lifecycle

Deterministic gates: pass  
Reviewer scores: {'accuracy': 4.0, 'clarity': 4.0, 'teaching_value': 4.0, 'completeness': 3.0}

## Issues

1. The claim that is_done() returns False until the job is ready, so no is_ready() check is needed, is not in the supplied facts, which only say is_done reports whether the job finished.
2. The text says the example puts cleanup in a `finally` block, but no snippet shows `finally`, `cancel`, or `Jobs.create`, so the claim cannot be verified.
3. The oneshot snippet omits the `Jobs.oneshot(..., output_mode="json")` call and the reader construction, so the key pairing is never shown.
4. The REST rule that queries must start with `search` or a pipe is not in the supplied API facts, and it has no code example.
5. `JSONResultsReader.is_preview` is never mentioned, though the text recommends `Job.preview` while a search is still running.
