# Review (read-only): connect_and_inspect

Deterministic gates: pass  
Reviewer scores: {'accuracy': 4.0, 'clarity': 5.0, 'teaching_value': 3.0, 'completeness': 3.0}

## Issues

1. Facts truncate connect() docs and never list username/password; script relies on them without verification against the supplied facts.
2. service.info['serverName'] is assumed; facts say only 'dict' key-value pairs, so the serverName key is unverified.
3. Iterating service.apps directly is not shown as supported; facts say only Collection of Application entities, so the iteration and .name access are unconfirmed.
4. Catching OSError is unsupported by facts; SSL verification, self-signed certificates and the verify parameter are not discussed, although they are the most common connection failure.
5. Decision step is missing: the docstring promises deciding readiness, but the code only prints and never compares version or exits on restart_required.
