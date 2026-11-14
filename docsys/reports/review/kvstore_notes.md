# Review (read-only): kvstore_notes

Deterministic gates: pass  
Reviewer scores: {'accuracy': 2.0, 'clarity': 4.0, 'teaching_value': 3.0, 'completeness': 3.0}

## Issues

1. query() is documented to accept only sort, limit, skip and fields; the artifact passes query={...} as a dict, which is not a documented option and may not serialize as valid JSON.
2. The comment that query() takes a dict filter while delete() takes a JSON string is unsupported by the facts and likely misleading; the filter encoding should match for both.
3. insert() is documented as returning the _id of the inserted object, but the code reads ['_key'] without explaining the discrepancy or verifying it.
4. sort="priority" is shown without explaining the sort syntax or direction (for example, descending order), so readers cannot adapt it.
5. Several documented operations (fields, limit, skip, batch_save, batch_find, delete_by_id, update_field) are not demonstrated, and the `in service.kvstore` check is not among the supplied API facts.
