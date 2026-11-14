"""Create an index, send events to it, and search for them.

Goal: Show the write path (create an index, submit events) and the read path (search it),
    and clean up only what the script created.
Prerequisites: A reachable Splunk instance and an account allowed to create indexes. Set
    SPLUNK_HOST, SPLUNK_USERNAME and SPLUNK_PASSWORD. SPLUNK_PORT defaults to 8089.
Run: python send_and_find_events.py
"""

import os
import sys
import time

import splunklib.binding as binding
import splunklib.client as client
import splunklib.results as results

INDEX = "sdk_docs_demo"
EXPECTED = 3


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
    host = f"docs-demo-{int(time.time())}"  # unique per run, so old events never match

    # region: index
    created = INDEX not in service.indexes
    index = service.indexes.create(INDEX) if created else service.indexes[INDEX]
    # endregion: index

    try:
        # region: submit
        # submit() sends one HTTP request per event. For volume, use Index.attach() instead.
        for n in range(EXPECTED):
            index.submit(f"order {n} shipped", sourcetype="demo:orders", host=host)
        # endregion: submit

        # region: find
        query = f"search index={INDEX} host={host}"
        deadline = time.monotonic() + 30
        found = []
        while len(found) < EXPECTED and time.monotonic() < deadline:
            time.sleep(2)  # indexing is asynchronous: events appear after a short delay
            stream = service.jobs.oneshot(query, output_mode="json", earliest_time="-15m", count=0)
            # The reader mixes rows (dicts) with server messages, so keep only the dicts.
            found = [item for item in results.JSONResultsReader(stream) if isinstance(item, dict)]
        for event in found:
            print(event["_raw"])
        if len(found) < EXPECTED:
            sys.exit(f"Only {len(found)} of {EXPECTED} events were searchable in time.")
        print(f"Found all {EXPECTED} events")
        # endregion: find
    finally:
        # region: cleanup
        if created:  # never delete an index this script did not create
            service.indexes.delete(INDEX)
        # endregion: cleanup


if __name__ == "__main__":
    main()
