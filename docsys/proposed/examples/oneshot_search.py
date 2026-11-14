"""Summarize recent Splunk activity with a bounded oneshot search.

Goal: Run a bounded search over a fixed time range with `Jobs.oneshot`, read the
    aggregated rows, and separate result rows from server messages.
Prerequisites: A reachable Splunk instance. Set SPLUNK_HOST, SPLUNK_USERNAME and
    SPLUNK_PASSWORD in the environment. SPLUNK_PORT defaults to 8089.
Run: python oneshot_search.py ["search index=_internal | stats count by sourcetype"]
"""

import os
import sys
from contextlib import closing

import splunklib.client as client
import splunklib.results as results
from splunklib.binding import AuthenticationError, HTTPError

DEFAULT_QUERY = "search index=_internal | stats count by sourcetype | sort - count"


def main() -> int:
    try:
        service = client.connect(
            host=os.environ["SPLUNK_HOST"],
            port=int(os.environ.get("SPLUNK_PORT", "8089")),
            username=os.environ["SPLUNK_USERNAME"],
            password=os.environ["SPLUNK_PASSWORD"],
        )
    except KeyError as exc:
        print(f"Missing environment variable: {exc}", file=sys.stderr)
        return 2
    except AuthenticationError:
        print("Login failed. Check SPLUNK_USERNAME and SPLUNK_PASSWORD.", file=sys.stderr)
        return 1

    query = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_QUERY

    # region: search
    # Use `Jobs.oneshot` when the search is bounded: a fixed time range and a
    # modest result set. It blocks until the search finishes and creates no job
    # you have to clean up. For a large result set that you want to process as
    # it arrives, use `Jobs.export`. For a long search that you want to poll,
    # pause, or re-read, use `Jobs.create`.
    try:
        stream = service.jobs.oneshot(
            query,
            earliest_time="-15m",  # Bound the search so it stays cheap and predictable.
            latest_time="now",
            output_mode="json",  # `JSONResultsReader` only parses JSON output.
            count=0,  # 0 returns every result. The default cap is 100 rows.
        )
    except HTTPError as exc:
        # Splunk rejects invalid SPL here, for example a typo in a command name.
        print(f"Search failed: {exc}", file=sys.stderr)
        return 1
    # endregion: search

    # region: read
    # `closing` releases the HTTP response even if parsing fails midway.
    with closing(stream):
        reader = results.JSONResultsReader(stream)
        for item in reader:
            if isinstance(item, results.Message):
                # Messages carry diagnostics such as "no results found".
                print(f"[{item.type}] {item.message}")
            else:
                # Each row is a dict that maps field names to values.
                print(f"{item.get('sourcetype', '?'):<30} {item.get('count', '0')}")
    # endregion: read
    return 0


if __name__ == "__main__":
    sys.exit(main())
