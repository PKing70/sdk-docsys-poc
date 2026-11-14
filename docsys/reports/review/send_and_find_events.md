# Review (read-only): send_and_find_events

Deterministic gates: pass  
Reviewer scores: {'accuracy': 4.0, 'clarity': 5.0, 'teaching_value': 4.0, 'completeness': 4.0}

## Issues

1. If the index already exists, the script reuses it and leaves the 3 submitted events behind. This contradicts the docstring's 'clean up only what the script created'.
2. `INDEX not in service.indexes` and `service.indexes[INDEX]` rely on Collection membership and item lookup, which the supplied API facts do not document. `Collection.get` is the documented lookup.
3. Server Messages are silently discarded by the isinstance(dict) filter. Search diagnostics or errors that explain missing events are never shown, which hides a realistic debugging clue.
4. `indexes.create` sits outside the try block, and `Indexes.delete` is not confirmed to be synchronous. Failures there would surface as raw tracebacks, with no guidance on permissions or a delete that has not taken effect.
