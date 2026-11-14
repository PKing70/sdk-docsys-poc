"""Count events by sourcetype with a oneshot search.

Goal: Run a bounded statistics search over the last hour, read the rows, and tell result
    rows apart from messages the server sends.
Prerequisites: A reachable Splunk instance. Set SPLUNK_HOST, SPLUNK_USERNAME and
    SPLUNK_PASSWORD in the environment. SPLUNK_PORT defaults to 8089.
Run: python oneshot_search.py
    or python oneshot_search.py "search index=_audit | stats count by action"
"""

import os
import sys

import splunklib.binding as binding
import splunklib.client as client
import splunklib.results as results


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

    # region: search
    default_query = "search index=_internal | stats count by sourcetype | sort - count"
    query = sys.argv[1] if len(sys.argv) > 1 else default_query
    # oneshot blocks until the search finishes. earliest_time and count keep it bounded.
    stream = service.jobs.oneshot(query, output_mode="json", earliest_time="-1h", count=20)
    reader = results.JSONResultsReader(stream)
    # endregion: search

    # region: read
    for item in reader:
        if isinstance(item, results.Message):
            print(f"[{item.type}] {item.message}")  # a diagnostic from the server
        elif isinstance(item, dict):
            print(item)  # one result row
    # endregion: read


if __name__ == "__main__":
    main()
