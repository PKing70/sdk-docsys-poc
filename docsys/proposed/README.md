# Proposed model revisions

Model-revised versions of five artifacts from the first reviewed run (2026-11-14), saved for
comparison. They are NOT the project's content: the hand-written versions in `content/` and
`examples/` are. A passing review score does not mean a rewrite is correct. One earlier
rewrite replaced the SDK's `JSONResultsReader` with hand-parsed JSON and added claims about
index deletion that the reviewer could not verify. Review each diff before adopting anything.

`sdkdocsys loop` now writes here automatically: a revised page or example lands at the same relative
path as the original (for example `proposed/content/...`), and the original is never edited. Diff with
`diff -u content/<path> proposed/content/<path>`. An existing proposal is replaced only when the loop
produces a new one for that artifact.

When one run revises both examples and pages, each page is scored against that run's example
proposals, so the pair is judged as it would ship. Proposals from earlier runs are not overlaid.

To adopt: `uv run sdkdocsys adopt --example ID`, `--page ID`, or `--all`. Add `--dry-run` to see the diffs
only. Adopt re-runs the deterministic gates over everything; if it causes a new gate failure it restores
the originals and keeps the proposals. It does not commit.
