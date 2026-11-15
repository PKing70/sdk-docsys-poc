# How the SDK connects to Splunk

Every task in the SDK starts with a connection. You call `splunklib.client.connect` once, and it returns a `Service` object. You then use that object to reach searches, indexes, apps, and the rest of the Splunk REST API.

## How it works

The SDK talks to the Splunk management port over HTTPS. By default that is port 8089 on `localhost`. When you call `splunklib.client.connect`, the SDK builds a `splunklib.client.Service` and logs in. The call makes one round trip to the server. The `Service` keeps the session token it receives, so later requests do not send your password again.

:::{coderef} examples/connect_and_inspect.py
:region: connect
:::

The values you pass control the connection:

- `host`, `port`, and `scheme` choose the server. The defaults are `localhost`, 8089, and `https`.
- `username` and `password` authenticate an account. You can pass a `token` or `cookie` instead if you already have a session.
- `owner`, `app`, and `sharing` set the namespace, which decides where the objects you create or list live. Objects saved with app sharing belong to one app. Objects saved with global sharing are visible across apps. The `sharing` value can be `user`, `app`, `global`, or `system`, and the default is `user`. For `owner` and `app`, the value `-` is a wildcard that matches any. Choose the namespace on purpose, because it decides what you can see.
- `autologin=True` makes the SDK sign in again if the session expires. Scripts that run longer than the server's session timeout need it.
- `verify` turns SSL verification on or off, and `self_signed_certificate` tells the SDK whether the server uses a self-signed certificate. Check both when a TLS error stops the connection.
- `retries` and `retryDelay` control how many times the SDK retries a failed HTTP connection and how long it waits between tries. The default is no retries.

The example reads connection settings from environment variables. That keeps credentials out of your source files and out of version control.

Three failures are common, and the example handles each with a clear message. A missing environment variable raises `KeyError`. A wrong username or password raises `splunklib.binding.AuthenticationError`. An unreachable host or a TLS problem raises an `OSError` or one of its subclasses. Without handlers, each of these ends in a long traceback that hides the cause.

Once you hold a `Service`, many of its attributes are properties, so you read them without parentheses. These include `info`, `splunk_version`, `restart_required`, and `apps`. The version is a tuple of integers, such as `(9, 2, 1)`. A collection such as `apps` supports iteration, the `in` test, `len()`, and lookup by name. This pattern repeats across the SDK, so learning it once pays off everywhere.

:::{coderef} examples/connect_and_inspect.py
:region: inspect
:::

## When to use

Use `connect` for scripts and services that call Splunk directly with a username and password or a token. It is the right starting point for the guides in this documentation.

Set `autologin=True` for anything that runs longer than the server's session timeout. For short scripts the default is fine.

If your code is a custom search command, the SDK already builds a service for you. Read it from the command's `service` property. It is available only when you set `requires_srinfo = true` in `commands.conf`, so that Splunk passes the session details to your command.
