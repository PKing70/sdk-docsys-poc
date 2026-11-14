# Send events to an index and find them

This guide walks through the full write-then-read loop. You create a scratch index, send three events to it, search for them, and remove the index. Along the way you see why a search right after a write can come back empty, and how to make the search reliable.

## Prerequisites

- A Splunk instance and an account that is allowed to create and delete indexes.
- `SPLUNK_HOST`, `SPLUNK_USERNAME`, and `SPLUNK_PASSWORD` set in your environment.
- The index name `sdk_docs_demo` must be free. The script deletes it at the end, so do not point it at an index you want to keep.
- The full file, `examples/send_and_find_events.py`. The snippets below show only the labeled regions. They assume a connected `service` object. The import lines and the connection setup that reads the environment variables live at the top of the file, outside these regions. Run the whole file rather than pasting the snippets on their own.

## Steps

1. Create the index if it is missing. The `service.indexes` collection supports `in` for existence checks, so you can skip creation on a rerun. `Collection.create` creates the index and returns an `Index` object. You use that object for the next steps.

   :::{coderef} examples/send_and_find_events.py
   :region: index
   :::

2. Send the events with `Index.submit`. Each call submits one event. Set `sourcetype` and `host` so you can find the events by those fields later.

   :::{coderef} examples/send_and_find_events.py
   :region: submit
   :::

3. Search for the events with `Jobs.oneshot`. Indexing is asynchronous, so the events may not be searchable the moment `Index.submit` returns. The loop runs the search again until all three events arrive or the deadline passes.

   Each retry runs a new search, so the result limit matters. A oneshot search returns at most the default number of results, which is 100, unless you raise it. Pass `count=0` to `Jobs.oneshot` to remove the limit. Three events fit under the default, but a larger event set would be cut off silently and the loop would never see the full count. Add `count=0` whenever you adapt this loop to more events.

   :::{coderef} examples/send_and_find_events.py
   :region: find
   :::

4. Clean up with `Indexes.delete`, which removes the index by name. This region is a plain delete call. It does not wrap the work in error handling, so if the script stops before this point, the index stays on the server. In that case, delete `sdk_docs_demo` yourself, or rerun the script. The `in` check from step 1 reuses the existing index, and the cleanup then removes it. If you adapt the script for real use, put the delete in a `try`/`finally` block of your own so it runs after a failure too.

   :::{coderef} examples/send_and_find_events.py
   :region: cleanup
   :::

## Verify

The script prints `Found 3 of 3 events` followed by the three raw events. If it reports fewer, work through these checks:

- **Indexing delay.** The events may not be searchable yet. Raise the deadline and run the script again.
- **Truncated results.** If you changed the search to match more events, make sure `Jobs.oneshot` gets `count=0`. Otherwise results stop at the default limit.
- **Time range.** A search covers a time range. If you submitted events with timestamps outside it, they do not match. Pass `earliest_time` (and `latest_time` if needed) in the `Jobs.oneshot` params to widen the range.
- **Leftover data.** If earlier runs left events in the index, your counts can be off. Call `Index.clean` to remove all data from the index. It takes a `timeout` in seconds, 60 by default. Deleting and recreating the index also works.
- **Buckets.** Call `Index.roll_hot_buckets` to roll the index's hot buckets to warm. Try this if you suspect recent data is still in a hot bucket.

If creating the index fails with a permissions error, the account lacks the capability to manage indexes. Use an account that has it, or ask an administrator to grant it.
