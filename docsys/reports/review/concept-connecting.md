# Review (read-only): concept-connecting

Deterministic gates: pass  
Reviewer scores: {'accuracy': 3.0, 'clarity': 4.0, 'teaching_value': 4.0, 'completeness': 3.0}

## Issues

1. `username`, `password`, `token`, `cookie`, `autologin` are not in the supplied facts (docs excerpt truncated); asserted without support, and `autologin=True` described as required for long scripts is unverified.
2. Claims about `info['serverName']`, `splunk_version` being a tuple, and collections supporting `in`/`len()`/name lookup aren't backed by the API facts.
3. The custom search command claim (`service` property, `requires_srinfo`) is outside the supplied API facts and cannot be verified.
4. Says OSError covers TLS problems, but no verify/self_signed_certificate guidance is given; the documented `verify` parameter is never explained, so certificate failures remain unaddressed.
5. Omits the `connect` alternatives: constructing `Service` then calling `login()`, `Service.login`/`logout`, and the `HTTPError` that failed requests can raise; the error handling is thus incomplete.
