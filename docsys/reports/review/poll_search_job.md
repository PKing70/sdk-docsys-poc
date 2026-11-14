# Review (read-only): poll_search_job

Deterministic gates: pass  
Reviewer scores: {'accuracy': 4.0, 'clarity': 5.0, 'teaching_value': 4.0, 'completeness': 4.0}

## Issues

1. Results are read right after job.finalize() with no wait; finalization may not have completed, so partial results could be empty or incomplete. The code never rechecks is_done().
2. The comment that is_done() is False until ready is not in the supplied API facts. is_ready() is listed, so the claim is unverified.
3. The else branch assumes every non-Message row is a dict. The documented pattern checks isinstance(row, dict), so unexpected types would raise a TypeError on row['sourcetype'].
4. The except KeyError sits around client.connect(), so a KeyError raised inside the SDK would be misreported as a missing environment variable. Read the variables before the try block.
5. splunklib.binding.AuthenticationError and client.Service are not in the supplied API facts, so the error handling and the return annotation cannot be verified.
