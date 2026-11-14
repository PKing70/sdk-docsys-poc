# Review (read-only): procedure-first-search

Deterministic gates: pass  
Reviewer scores: {'accuracy': 3.0, 'clarity': 4.0, 'teaching_value': 3.0, 'completeness': 3.0}

## Issues

1. Claims 'Each item is either a dict or a Message', but the code uses a bare else instead of isinstance(item, dict), unlike the facts' documented pattern; other types are not excluded.
2. The default query (DEFAULT_QUERY) is never shown, yet Verify claims specific fields and sort order, which cannot be checked against the supplied code.
3. Never mentions that oneshot raises ValueError for invalid queries; the Verify section only says the server rejects the query, with no handling shown.
4. 'Reader parses only JSON' and 'must start with search or a pipe' are not in the API facts; they are plausible but unsupported claims.
5. Omits reader.is_preview, which the docs show checking; it is relevant for confirming completed results. Also ignores the oneshot single-roundtrip advantage.
