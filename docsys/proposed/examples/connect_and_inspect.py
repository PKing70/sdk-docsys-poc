"""Connect to Splunk, inspect the instance, and run a oneshot search.

Goal: Open an authenticated session, read basic facts about the instance, and run
    a small search so you see the full connect, inspect, query loop.
Prerequisites: A reachable Splunk instance. Set SPLUNK_HOST, SPLUNK_USERNAME and
    SPLUNK_PASSWORD. SPLUNK_PORT defaults to 8089, the management port (not the
    web port 8000). SPLUNK_SCHEME defaults to https. Set SPLUNK_VERIFY=false only
    for a lab instance with a self-signed certificate. Properties such as
    `Service.apps`, `Service.saved_searches` and `Service.jobs` are accessed
    without parentheses. They return collections you can iterate.
Run: python connect_and_inspect.py
"""

import os
import sys

import splunklib.client as client
import splunklib.results as results
from splunklib.binding import AuthenticationError

REQUIRED = ("SPLUNK_HOST", "SPLUNK_USERNAME", "SPLUNK_PASSWORD")


def connect() -> client.Service:
    # region: connect
    missing = [name for name in REQUIRED if not os.environ.get(name)]
    if missing:
        sys.exit(f"Set these environment variables first: {', '.join(missing)}")
    verify = os.environ.get("SPLUNK_VERIFY", "true").lower() != "false"
    try:
        return client.connect(
            scheme=os.environ.get("SPLUNK_SCHEME", "https"),
            host=os.environ["SPLUNK_HOST"],
            port=int(os.environ.get("SPLUNK_PORT", "8089")),
            username=os.environ["SPLUNK_USERNAME"],
            password=os.environ["SPLUNK_PASSWORD"],
            verify=verify,
        )
    except AuthenticationError:
        sys.exit("Login failed. Check SPLUNK_USERNAME and SPLUNK_PASSWORD.")
    except OSError as exc:
        sys.exit(f"Cannot reach Splunk (check host, port, TLS settings): {exc}")
    # endregion: connect


def inspect(service: client.Service) -> None:
    # region: inspect
    # Print the version as the SDK returns it; do not assume its shape.
    print("Splunk version:", service.splunk_version)
    print("Apps:", ", ".join(app.name for app in service.apps))
    saved = [s.name for s in service.saved_searches]
    print(f"Saved searches: {len(saved)}")
    # endregion: inspect


def top_sourcetypes(service: client.Service) -> None:
    # region: search
    query = "search index=_internal | stats count by sourcetype | sort - count | head 5"
    # A oneshot search blocks until done and returns results directly, so you
    # create no job to clean up. Use it for small, quick queries.
    stream = service.jobs.oneshot(query, output_mode="json", count=0)
    for item in results.JSONResultsReader(stream):
        # The reader also yields diagnostic Message objects; keep only rows.
        if isinstance(item, dict):
            print(f"{item['sourcetype']}: {item['count']}")
    # endregion: search


def main() -> None:
    service = connect()
    inspect(service)
    top_sourcetypes(service)


if __name__ == "__main__":
    main()
