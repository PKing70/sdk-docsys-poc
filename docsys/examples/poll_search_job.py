"""Run a longer search as a job, with a timeout.

Goal: Create a search job, poll until it finishes, read the results, and always clean up.
Prerequisites: A reachable Splunk instance. Set SPLUNK_HOST, SPLUNK_USERNAME and
    SPLUNK_PASSWORD in the environment. SPLUNK_PORT defaults to 8089.
Run: python poll_search_job.py
"""

import os
import sys
import time

import splunklib.binding as binding
import splunklib.client as client
import splunklib.results as results

TIMEOUT_SECONDS = 60


def connect() -> client.Service:
    try:
        return client.connect(
            host=os.environ["SPLUNK_HOST"],
            port=int(os.environ.get("SPLUNK_PORT", "8089")),
            username=os.environ["SPLUNK_USERNAME"],
            password=os.environ["SPLUNK_PASSWORD"],
        )
    except KeyError as exc:
        sys.exit(f"Set the {exc.args[0]} environment variable.")
    except binding.AuthenticationError:
        sys.exit("Login failed: check SPLUNK_USERNAME and SPLUNK_PASSWORD.")
    except OSError as exc:
        sys.exit(f"Could not reach Splunk with that host and port: {exc}")


def main() -> None:
    service = connect()

    # region: create
    job = service.jobs.create("search index=_internal | stats count by sourcetype")
    # endregion: create

    try:
        # region: poll
        deadline = time.monotonic() + TIMEOUT_SECONDS
        while not job.is_done():  # False until the job is ready, so no is_ready() check needed
            if time.monotonic() > deadline:
                job.finalize()  # stop searching but keep the partial results
                print(f"Stopped after {TIMEOUT_SECONDS}s. Showing partial results.")
                break
            time.sleep(0.5)
        # endregion: poll

        # region: results
        reader = results.JSONResultsReader(job.results(output_mode="json", count=0))
        for row in reader:
            if isinstance(row, results.Message):
                print(f"[{row.type}] {row.message}")
            else:
                print(f"{row['sourcetype']:<30} {row['count']}")
        # endregion: results
    finally:
        job.cancel()  # always release the job and its cached results on the server


if __name__ == "__main__":
    main()
