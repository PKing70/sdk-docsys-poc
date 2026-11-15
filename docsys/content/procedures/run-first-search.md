# Run your first search

This guide shows you how to run a search from a Python script and read what comes back. The search counts your instance's own internal events by sourcetype over the last hour, so it works on any Splunk without extra data.

`Jobs.oneshot` makes a single round trip to the server. Creating a job with `Jobs.create` and then fetching its results takes two. That makes `oneshot` a good fit for a small, bounded search whose results you want right away. If `autologin` is set to `True` when you connect, it adds at most two more round trips. For a long-running search, create a job and poll it instead, as the guide "How searches run: oneshot and jobs" describes.

## Prerequisites

- A reachable Splunk instance and an account that can run searches and read the `_internal` index.
- The SDK installed in your Python environment.
- `SPLUNK_HOST`, `SPLUNK_USERNAME`, and `SPLUNK_PASSWORD` set in your environment. `SPLUNK_PORT` defaults to 8089.

## Steps

1. Get the script. The complete file is `examples/oneshot_search.py`. It connects with the same settings as the connection guide and turns login and network failures into short messages.

2. Choose a query. The script takes the query from its first argument, or uses the default shown in the next snippet, which counts events by sourcetype. A query sent over the REST API must start with `search` or a pipe.

3. Run the search with `Jobs.oneshot` and wrap the stream in `splunklib.results.JSONResultsReader`. Ask for JSON output with `output_mode="json"`, because the reader parses only JSON. The script passes `earliest_time` to limit the time range and `count` to limit the number of rows returned. The call blocks until the search finishes, so keep it bounded.

   :::{coderef} examples/oneshot_search.py
   :region: search
   :::

4. Read the reader in a loop. Check the type of each item. It is either a `splunklib.results.Message` from the server or a result row, which is a dict. A message has a `type`, such as `INFO` or `WARN`, and a `message` with the text. Print messages separately so a warning does not look like data. The reader also has an `is_preview` attribute. After you read the results of a oneshot search, `is_preview` is `False`, as in the example in the `Jobs.oneshot` docstring.

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

If the script prints `Login failed`, check your username and password. The SDK documents that `Jobs.oneshot` raises `ValueError` for an invalid query. The script does not catch it, so you see a traceback that ends with that error. Check the text of your query.
