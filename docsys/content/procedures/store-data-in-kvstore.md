# Store and query data in the KV Store

The KV Store is a small document database built into Splunk. This guide shows you how to create a collection, add documents, query them, update one, and clean up.

## Prerequisites

- A Splunk instance with the KV Store enabled and an account that can create collections.
- `SPLUNK_HOST`, `SPLUNK_USERNAME`, and `SPLUNK_PASSWORD` set in your environment. `SPLUNK_PORT` is optional and defaults to 8089.
- The complete script is `examples/kvstore_notes.py`. It uses the collection name `sdk_docs_notes`. If that collection already exists, the script uses it and removes only the documents it added. It drops the collection only when it created it.
- A collection belongs to an app. To choose the app, add `app=` to the `client.connect(...)` call inside the script's `connect()` function.

## Steps

1. Get or create the collection, then take its `data` endpoint. That endpoint is a `KVStoreCollectionData` object, and it carries the document operations. The `in` test checks whether the collection already exists. The script remembers whether it created it.

   :::{coderef} examples/kvstore_notes.py
   :region: collection
   :::

2. Add documents with `KVStoreCollectionData.insert`. Each call takes a dictionary and stores it as one document. Splunk assigns the `_key` field and returns it, so the script keeps each key for later calls.

   :::{coderef} examples/kvstore_notes.py
   :region: insert
   :::

3. Read documents back with `KVStoreCollectionData.query`. Pass a MongoDB-style filter as `query`, written as a JSON string with `json.dumps` (the script imports `json`), and use `sort` to order the results. The call returns a list of dicts. This filter selects documents with a priority of 1 or lower.

   :::{coderef} examples/kvstore_notes.py
   :region: query
   :::

4. Change a document with `KVStoreCollectionData.update`, which replaces the document with the data you pass, and read one document back by its key with `query_by_id`.

   :::{coderef} examples/kvstore_notes.py
   :region: update
   :::

5. Clean up. A collection the script created is dropped with `service.kvstore.delete`, which removes its documents too. For an existing collection, the script uses `KVStoreCollectionData.delete` with a JSON filter on the keys it inserted, so it removes only its own documents. Called with no filter, `delete` removes every document in the collection.

   :::{coderef} examples/kvstore_notes.py
   :region: cleanup
   :::

## Verify

With a collection the script created, it prints one line with the `_key` and title of the "review examples" document, which is the only one with priority 1. If the collection already existed, the query also prints any existing documents with priority 1 or lower. Then it prints the "write docs" document after the update, now with priority 1. The cleanup step prints nothing.

If the script prints a login, missing-variable, or unreachable-host message, see the connection guide. If the first step fails, check that the KV Store service is running on the instance. If a query returns an unexpected list, look at your filter: documents that do not match are left out.
