# Run your first search

This guide shows you how to run a search from a Python script and print what comes back. It takes a few minutes and uses only your existing Splunk data.

## Prerequisites

- A reachable Splunk instance and an account that can run searches.
- The SDK installed in your Python environment.
- `SPLUNK_HOST`, `SPLUNK_USERNAME`, and `SPLUNK_PASSWORD` set in your environment. `SPLUNK_PORT` defaults to 8089.

## Steps

1. Connect and build the query. The script connects as described in the connection guide, then takes the query from the command line. The default query reads five internal events, which exist on every instance.

2. Run the search with `Jobs.oneshot` and wrap the stream in `splunklib.results.JSONResultsReader`. Ask for JSON output and cap the rows with `count`.

   :::{coderef} examples/oneshot_search.py
   :region: search
   :::

3. Read the reader in a loop. Each item is either a result row or a `Message` from the server. Print messages separately so a warning does not look like data.

   :::{coderef} examples/oneshot_search.py
   :region: read
   :::

4. Run the script from a shell.

## Verify

You see up to five dictionaries, one per event, each with fields such as `_time` and `_raw`. If you see a `[WARN]` line instead, read the message. It usually names the problem, such as a missing index or a permissions gap.

If the call raises an error that mentions the query, check that it starts with `search` or a pipe.
