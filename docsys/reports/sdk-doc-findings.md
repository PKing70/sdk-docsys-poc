# SDK documentation findings

Found while reviewing generated guides against the SDK source (SDK 3.0.1, commit fe9fb84).
These are gaps or errors in the SDK's own docstrings. The SDK was not modified. Each item
cites the behavior in the source or in the SDK's own tests.

| Symbol | Docstring says | The code and tests show |
|---|---|---|
| `KVStoreCollectionData.insert` | Returns the `_id` of the inserted object; `data` is a string | Returns a dict with `_key` (`tests/integration/test_kvstore_data.py` reads `["_key"]`). Also accepts a dict, which it JSON-encodes |
| `KVStoreCollectionData.query` | Valid options are `sort`, `limit`, `skip`, and `fields` | Also takes a `query` filter (the tests call `query(query='{"num": 10}')`). A dict value is JSON-encoded by the SDK |
| `KVStoreCollectionData.update` | `data` is a string | Also accepts a dict, which it JSON-encodes |
| `KVStoreCollectionData.delete` | `query` is a string | Passed through unchanged. A dict is not encoded, unlike in `query()`. The asymmetry is undocumented |

Why it matters: a docs reviewer or a reader who trusts the docstrings will conclude that correct
usage is wrong. In our review, an accurate KV Store page scored 2 out of 5 on accuracy for
exactly this reason.

Not filed anywhere. If you want these reported upstream, that is your call.
