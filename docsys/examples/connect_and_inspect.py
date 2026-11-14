"""Connect to Splunk and check what you are talking to.

Goal: Open an authenticated session, handle the common failures, and decide whether this
    Splunk is ready for your script.
Prerequisites: A reachable Splunk instance. Set SPLUNK_HOST, SPLUNK_USERNAME and
    SPLUNK_PASSWORD in the environment. SPLUNK_PORT defaults to 8089.
Run: python connect_and_inspect.py
"""

import os
import sys

import splunklib.binding as binding
import splunklib.client as client


def connect() -> client.Service:
    # region: connect
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
    # endregion: connect


def describe(service: client.Service) -> None:
    # region: inspect
    # info, splunk_version, restart_required and apps are properties: no parentheses.
    version = ".".join(str(part) for part in service.splunk_version)
    print(f"Connected to {service.info['serverName']}, Splunk {version}")
    print("Installed apps:", ", ".join(app.name for app in service.apps))
    if service.restart_required:  # the decision: do not script against a pending restart
        sys.exit("Not ready: restart Splunk first.")
    # endregion: inspect


def main() -> None:
    describe(connect())


if __name__ == "__main__":
    main()
