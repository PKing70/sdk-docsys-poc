# Review (read-only): procedure-kvstore

Deterministic gates: pass  
Reviewer scores: {'accuracy': 2.0, 'clarity': 4.0, 'teaching_value': 3.0, 'completeness': 3.0}

## Issues

1. Step 3 passes `query=` to `query()`, but the facts list only sort, limit, skip and fields as valid options. The claim that the SDK converts a dict filter to JSON is also unsupported.
2. Step 2 says `insert` takes a dictionary and returns `_key`. The facts document `data` as a string and the return as the `_id` of the inserted object.
3. `service.kvstore.delete(COLLECTION)` and `COLLECTION not in service.kvstore` are not in the supplied API facts, which list only indexing and `create` for KVStoreCollections.
4. Claims that `update` replaces the whole document, and that `connect` accepts `app`, are not backed by the facts. The artifact also never shows the connection or `service` setup.
5. The artifact omits the batch operations (`batch_save`, `batch_find`) and the `limit`, `skip` and `fields` query options. These matter for realistic bulk loading and paging.
