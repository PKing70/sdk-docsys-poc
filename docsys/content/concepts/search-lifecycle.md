# How searches run: oneshot and jobs

Splunk can run a search in two ways, and the SDK exposes both. Choosing the right one saves you code now and trouble later. Each snippet below is one part of a complete script in the `examples` folder, so you can run that file as it is.

## How it works

A oneshot search is one request. You send the query, the server runs it, and the results stream back on the same connection. In the SDK that is `Jobs.oneshot`. The call blocks until the search finishes. There is no job to track and nothing to clean up.

A search job is a long-lived object on the server. `Jobs.create` starts the search and returns right away with a `Job`, which is a handle and not a stream of results. The search keeps running while your code does other work. You ask the job whether it has finished with `Job.is_done`. That method returns `False` until the job is ready, so you do not need a separate readiness check. When the job is done, `Job.results` returns the stream of results. Called on an unfinished job, it returns an empty event set, so do not skip the polling loop. A finished job keeps its results on the server until it expires or you cancel it.

:::{coderef} examples/poll_search_job.py
:region: create
:::

:::{coderef} examples/poll_search_job.py
:region: poll
:::

Both `Jobs.oneshot` and `Job.results` return a raw stream. To turn the stream into Python objects, pass it to `splunklib.results.JSONResultsReader` and ask the server for `output_mode="json"`. The reader yields a dict for each result row and a message object for each diagnostic from the server. Always handle both. A search that returns no rows can still carry a useful warning, and code that only expects dicts drops it silently.

:::{coderef} examples/oneshot_search.py
:region: search
:::

:::{coderef} examples/oneshot_search.py
:region: read
:::

Search strings sent over the REST API must begin with the `search` command or a pipe. A query such as `index=_internal | head 5` fails, while `search index=_internal | head 5` works. This differs from the Splunk Web search bar, which adds `search` for you.

You control how long a job lives. `Job.cancel` stops the job and deletes its results. `Job.finalize` stops the search but keeps the partial results, which suits a search that ran out of time. `Job.set_ttl` changes how long the server keeps the job, and `Job.touch` resets that clock.

:::{coderef} examples/poll_search_job.py
:region: results
:::

This snippet reads known columns from a statistics search, so it prints them by name. The earlier read snippet is generic, so it checks for a dict first.

## When to use

Use `Jobs.oneshot` when the query is quick and bounded, and you want the results immediately. Limit the output with `count` or a time range such as `earliest_time`, so one call cannot return an unbounded stream.

Use `Jobs.create` when the search may run for a while, when you want to read preview results with `Job.preview` while it runs, or when you want to read the same results more than once. Set a deadline in your polling loop, and put the cleanup in a `finally` block that calls `Job.cancel`, as the complete script does. A job you abandon keeps using server resources until it expires.
