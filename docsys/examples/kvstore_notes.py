"""Store, query, update, and delete documents in a KV Store collection.

Goal: Use the KV Store as a small app database, and clean up only what the script created.
Prerequisites: A reachable Splunk instance with the KV Store enabled. Set SPLUNK_HOST,
    SPLUNK_USERNAME and SPLUNK_PASSWORD. SPLUNK_PORT defaults to 8089.
Run: python kvstore_notes.py
"""

import json
import os
import sys

import splunklib.binding as binding
import splunklib.client as client

COLLECTION = "sdk_docs_notes"


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

    # region: collection
    created = COLLECTION not in service.kvstore
    if created:
        service.kvstore.create(COLLECTION)
    notes = service.kvstore[COLLECTION].data
    # endregion: collection

    keys = {}
    try:
        # region: insert
        for title, priority in [("write docs", 2), ("review examples", 1)]:
            keys[title] = notes.insert({"title": title, "priority": priority})["_key"]
        # endregion: insert

        # region: query
        # The filter is a JSON string. query() returns a list of dicts, one per document.
        urgent = notes.query(query=json.dumps({"priority": {"$lte": 1}}), sort="priority")
        for doc in urgent:
            print(f"{doc['_key']}: {doc['title']}")
        # endregion: query

        # region: update
        notes.update(keys["write docs"], {"title": "write docs", "priority": 1})
        print(notes.query_by_id(keys["write docs"]))
        # endregion: update
    finally:
        # region: cleanup
        if created:
            service.kvstore.delete(COLLECTION)  # drops the collection and its documents
        else:
            # Filters are JSON strings here too, so delete only the documents this run added.
            notes.delete(json.dumps({"_key": {"$in": list(keys.values())}}))
        # endregion: cleanup


if __name__ == "__main__":
    main()
