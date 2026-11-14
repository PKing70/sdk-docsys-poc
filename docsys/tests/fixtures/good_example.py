"""Run a oneshot search and print its events.

Goal: Run a bounded search, stream the results, and separate events from server messages.
Prerequisites: A reachable Splunk instance. Set SPLUNK_HOST, SPLUNK_USERNAME and
    SPLUNK_PASSWORD in the environment. SPLUNK_PORT defaults to 8089.
Run: python oneshot_search.py "search index=_internal | head 5"
"""

import os
import sys

import splunklib.client as client
import splunklib.results as results


def main() -> None:
    service = client.connect(
        host=os.environ["SPLUNK_HOST"],
        port=int(os.environ.get("SPLUNK_PORT", "8089")),
        username=os.environ["SPLUNK_USERNAME"],
        password=os.environ["SPLUNK_PASSWORD"],
    )
    query = sys.argv[1] if len(sys.argv) > 1 else "search index=_internal | head 5"

    # region: search
    stream = service.jobs.oneshot(query, output_mode="json", count=20)
    reader = results.JSONResultsReader(stream)
    # endregion: search

    # region: read
    for item in reader:
        if isinstance(item, results.Message):
            print(f"[{item.type}] {item.message}")
        else:
            print(item)
    # endregion: read


if __name__ == "__main__":
    main()
