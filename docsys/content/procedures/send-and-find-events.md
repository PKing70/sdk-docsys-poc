# Send events to an index and find them

This guide walks through the full write-then-read loop. You create a scratch index, send three events to it, search for them, and remove the index again.

## Prerequisites

- A Splunk instance and an account that is allowed to create and delete indexes.
- `SPLUNK_HOST`, `SPLUNK_USERNAME`, and `SPLUNK_PASSWORD` set in your environment. `SPLUNK_PORT` is optional and defaults to 8089.
- The complete script is `examples/send_and_find_events.py`. It uses the index name `sdk_docs_demo`. If an index with that name already exists, the script uses it and leaves it in place. It deletes the index only when it created it, so with an existing index the three demo events stay in it.

## Steps

1. Create the index if it is missing. `Collection.create` makes a new entity, and the `indexes` collection supports the `in` test for existence checks. The script remembers whether it created the index, so cleanup can be safe.

   :::{coderef} examples/send_and_find_events.py
   :region: index
   :::

2. Send the events with `Index.submit`. Each call posts one event over HTTP, which suits small numbers of events. For larger volumes, use `Index.attach`, which opens a writable socket to the index, or `Index.upload` to send a file, which must be locally accessible from the server. Set `sourcetype` and `host` so you can find the events by those fields. The script puts a timestamp in the host name, so events from earlier runs never match.

   :::{coderef} examples/send_and_find_events.py
   :region: submit
   :::

3. Search for the events with `Jobs.oneshot`. Indexing is asynchronous, so the events do not appear at once. The loop retries until all three arrive or thirty seconds pass. The reader returns result rows as dicts and server messages as another type, so the loop keeps only the dicts. The search looks back fifteen minutes with `earliest_time` and sets `count=0`, so the defaults cannot hide events.

   :::{coderef} examples/send_and_find_events.py
   :region: find
   :::

4. Clean up. The script runs steps 2 and 3 inside a `try` block, and the complete script puts the cleanup in the matching `finally` block, so it runs even if the search fails. The snippet shows the cleanup body.

   :::{coderef} examples/send_and_find_events.py
   :region: cleanup
   :::

## Verify

The script prints the three raw events, then `Found all 3 events`. If fewer than three arrive in time, it exits with a message that says how many it found, and the script still removes the index if it created it. Raise the `30` in `deadline = time.monotonic() + 30` and run it again, because a slow indexing pipeline is the usual cause.

If creating the index fails with a permissions error, the account lacks the capability to manage indexes.
