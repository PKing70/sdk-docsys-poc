# Run your first search

This guide shows you how to run a search from a Python script and read what comes back. The search counts your instance's own internal events by sourcetype over the last hour, so it works on any Splunk without extra data.

## Prerequisites

- A reachable Splunk instance and an account that can run searches and read the `_internal` index.
- The SDK installed in your Python environment.
- `SPLUNK_HOST`, `SPLUNK_USERNAME`, and `SPLUNK_PASSWORD` set in your environment. `SPLUNK_PORT` defaults to 8089.

## Steps

1. Get the script. The complete file is `examples/oneshot_search.py`. It connects with the same settings as the connection guide and turns login and network failures into short messages.

2. Choose a query. The script takes the query from its first argument, or uses the default shown in the next snippet, which counts events by sourcetype. A query sent over the REST API must start with `search` or a pipe.

3. Run the search with `Jobs.oneshot` and wrap the stream in `splunklib.results.JSONResultsReader`. Ask for JSON output with `output_mode="json"`, because the reader parses only JSON. `earliest_time` limits the time range and `count` limits the number of rows. The call blocks until the search finishes, so keep it bounded.

   :::{coderef} examples/oneshot_search.py
   :region: search
   :::

4. Read the reader in a loop. Check the type of each item. It is either a `splunklib.results.Message` from the server or a result row, which is a dict. A message has a `type`, such as `INFO` or `WARN`, and a `message` with the text. Print messages separately so a warning does not look like data.

   :::{coderef} examples/oneshot_search.py
   :region: read
   :::

5. Run the script from a shell. To use a query of your own, pass it as one quoted argument.

   ```console
   python oneshot_search.py
   python oneshot_search.py "search index=main | head 5"
   ```

## Verify

You see one dictionary per row. With the default query, each row has a `sourcetype` and a `count`, and the rows are sorted from the highest count down. If you passed an event search such as `head 5`, each row is an event with fields such as `_time` and `_raw`.

If a line starting with `[WARN]` appears, read its text. The server writes it, and it usually names the cause, such as a missing index or a permissions gap.

If the script prints `Login failed`, check your username and password. If the server rejects the query, check that it starts with `search` or a pipe.
