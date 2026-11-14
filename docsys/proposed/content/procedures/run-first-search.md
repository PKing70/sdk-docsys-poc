# Run your first search

This guide shows you how to run a bounded search from a Python script, stream the results, and keep server messages separate from events. It uses only data already in your Splunk instance.

## Prerequisites

- A reachable Splunk instance and an account that can run searches.
- The SDK installed in your Python environment.
- `SPLUNK_HOST`, `SPLUNK_USERNAME`, and `SPLUNK_PASSWORD` set in your environment. `SPLUNK_PORT` defaults to 8089.
- A connected `service` object. `Jobs.oneshot` is a method on the `Jobs` collection, and you reach that collection through the connected service. The script needs this object, plus imports for the SDK's client and results modules, before the steps below run.

## Steps

1. Define the query and run it with `Jobs.oneshot`. The method takes the query string and passes any extra keyword arguments to the server as `**params`. This example uses those parameters to request JSON output and to limit the number of rows. A one-shot call blocks until the search finishes and returns the results directly, so you do not create or poll a job yourself.

   :::{coderef} examples/oneshot_search.py
   :region: search
   :::

2. Wrap the response in `splunklib.results.JSONResultsReader` and loop over it. Each item is either a result row or a `splunklib.results.Message` from the server. The loop prints messages separately so a warning does not look like data. For each result row, it prints the `sourcetype` and `count` fields.

   :::{coderef} examples/oneshot_search.py
   :region: read
   :::

3. Run the script with Python from a shell.

## Verify

You see one line per result row, showing its `sourcetype` and `count` values. The query in the `search` region must return rows with those two fields. If a row lacks one of them, the loop prints a placeholder instead: `?` for a missing `sourcetype` and `0` for a missing `count`. A line of placeholders means the query did not produce the fields the loop prints. It does not mean the search failed.

If you see a message line instead of rows, read it. Server messages usually name the problem, such as a missing index or a permissions gap.

If the server rejects the query, the call raises an `HTTPError`, which the example catches. This is the case when the search string is malformed. A search must begin with a search term or with a pipe followed by a generating command. Other exceptions are not caught, so they appear as a normal Python traceback.
