# Review (read-only): procedure-send-and-find

Deterministic gates: pass  
Reviewer scores: {'accuracy': 4.0, 'clarity': 4.0, 'teaching_value': 4.0, 'completeness': 3.0}

## Issues

1. The `in` test and `service.indexes[INDEX]` lookup on the indexes collection are not in the supplied API facts, so they are unverified here, though `Collection.get` is listed.
2. The snippets never show `service`, `host`, `EXPECTED`, or the imports for `results`, `time` and `sys`. The `try`/`finally` structure is described but not shown, so the flow is hard to follow.
3. The `Index.upload` description says only 'send a file'. It does not say whether the path is local or on the server, and the supplied facts don't say either.
4. The `host` value contains a timestamp but is used unquoted in the search string, and the guide does not say how the host name is built. Special characters could break the query.
5. If the index already existed, the three demo events stay in it after the run. The guide never says this, and it conflicts with the 'scratch index' framing.
