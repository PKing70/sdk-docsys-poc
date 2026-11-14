# Review (read-only): oneshot_search

Deterministic gates: pass  
Reviewer scores: {'accuracy': 3.0, 'clarity': 4.0, 'teaching_value': 3.0, 'completeness': 3.0}

## Issues

1. Docstring says 'Count events by sourcetype ... bounded', but the default query has no head/limit; count=20 is not in the supplied facts, so the boundedness claim is unverified.
2. Uses binding.AuthenticationError, the OSError handler, and the 'blocks until search finishes' comment, none of which the API facts support; the error handling is unverifiable.
3. Never checks reader.is_preview or explains it, though the facts highlight it and the goal is to tell rows from messages.
4. The docstring's 'python oneshot_search.py "search index=main | head 5"' example contradicts the stats-by-sourcetype theme and doesn't use the earliest_time/count bounds meaningfully.
5. The facts' param list for earliest_time/count is truncated, so passing them as oneshot params is unverified; no explanation of why messages appear or how to handle them.
