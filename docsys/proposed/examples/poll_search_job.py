"""Run a longer search as a job, with a timeout and guaranteed cleanup.

Goal: Create a search job, poll until it finishes, read results and messages, and cancel the job.
Prerequisites: A reachable Splunk instance. Set SPLUNK_HOST, SPLUNK_USERNAME and
    SPLUNK_PASSWORD in the environment. SPLUNK_PORT defaults to 8089.
Run: python poll_search_job.py

Use a job when you need control: polling, a timeout, pausing, or reading results
more than once. For a short search, `Jobs.oneshot` returns results in one call.
For a very large result set, `Jobs.export` streams events without a stored job.
"""

import os
import sys
import time

import splunklib.client as client
import splunklib.results as results

TIMEOUT_SECONDS = 60


def main() -> None:
    service = client.connect(
        host=os.environ["SPLUNK_HOST"],
        port=int(os.environ.get("SPLUNK_PORT", "8089")),
        username=os.environ["SPLUNK_USERNAME"],
        password=os.environ["SPLUNK_PASSWORD"],
    )

    # region: create
    # `Jobs.create` returns right away with the default exec_mode="normal", so
    # you can poll and enforce your own timeout. Passing exec_mode="blocking"
    # makes the call wait until the search finishes, which leaves no room for a timeout.
    job = service.jobs.create("search index=_internal | stats count by sourcetype")
    try:
        # Safety net: if this script dies before cleanup, the server still
        # discards the job after 5 minutes instead of keeping it for its default TTL.
        job.set_ttl(300)
        # endregion: create

        # region: poll
        # `Job.is_ready` fetches the job's current state from the server. A job
        # that is still queued or parsing is not ready, and `Job.is_done` is only
        # meaningful after that. Checking both on every pass keeps the state fresh.
        deadline = time.monotonic() + TIMEOUT_SECONDS
        while not (job.is_ready() and job.is_done()):
            if time.monotonic() > deadline:
                raise SystemExit(f"Search did not finish in {TIMEOUT_SECONDS}s.")
            time.sleep(0.5)
        # endregion: poll

        # region: results
        # `JSONResultsReader` yields dicts for rows and `results.Message` objects
        # for diagnostics. Messages carry warnings such as truncated results, so
        # surface them rather than hiding a partial answer.
        reader = results.JSONResultsReader(job.results(output_mode="json", count=0))
        for item in reader:
            if isinstance(item, results.Message):
                print(f"[{item.type}] {item.message}", file=sys.stderr)
            elif isinstance(item, dict):
                print(f"{item['sourcetype']:<30} {item['count']}")
        # endregion: results
    finally:
        # Runs on success, timeout, or a parsing error, so the job never lingers.
        job.cancel()


if __name__ == "__main__":
    main()
