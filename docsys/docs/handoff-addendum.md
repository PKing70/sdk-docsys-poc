# Handoff addendum: design decisions from the 2026-11-14 walkthrough

Add this next to `docsys/docs/handoff.md`. It records decisions made in an understanding chat that the
current handoff, requirements, and architecture documents do not yet reflect. Treat each item as a
decision to implement or to reconcile with the existing docs, not as built behavior.

## Decisions

1. **The manifest is generated from page frontmatter.** Writers (or the agent) tag each page in its
   frontmatter with the SDK symbols it covers, including `key_symbol`. `manifest.toml` becomes a
   generated output, not a hand-maintained input, so it cannot drift from the pages. This changes the
   handoff's description of the manifest as "the doc plan." Open point: how a planned but unwritten page
   is represented (suggested: a stub page whose frontmatter says it is planned and what it covers).

2. **Draft by revising first.** When a change affects a page, the model first assesses whether a
   revision to the existing text is enough, and rewrites only when it is not. Reasons: stability and
   familiarity, easier review, localization, efficiency. This depends on the known v0.1 gap: the improve
   loop must write proposals instead of editing files in place.

3. **Detection rule.** Flag every public signature change and every docstring edit. A model or a person
   triages each one, since a docstring edit may be a typo or a behavior change. Do not flag
   implementation changes that leave the signature and docstring alone. The baseline is the last
   published version, not the last pipeline run. To verify: that the snapshot includes docstrings, and
   how the baseline is tracked today, since publishing is not built.

4. **Review happens in a pull request.** The PR description summarizes results and what to focus on,
   and links to the per-page report (`reports/<id>.md`) when long. The diff gives file-level detail. A
   GitHub team is assigned as reviewer. The approver always sees which checks ran and which were skipped.
   Approval is the writer's call, even when every check passed.

5. **Rejections feed a pattern log.** A rejection reason is a PR comment with a label (suggested:
   `docsys-feedback`). Each pattern becomes a deterministic check where possible, and a rubric change
   only when it cannot be mechanized. A low score on a correct page counts as signal too. Not built.

6. **The docs PR is non-blocking.** Engineers keep their current speed. An SDK change merges and releases
   as today, and docsys opens a separate docs PR that can be reviewed before or after the release.
   Revisit blocking once the review process is trusted. Track docs lag, the time between an SDK release
   and approval of its docs PR.

## Things to be honest about when pitching

- Green CI does not mean a page was reviewed. CI fails on the three `needs_*` statuses and passes both
  `accepted` and `accepted_unreviewed`.
- Examples have not been run against a live Splunk. Today an example can resolve and pass static
  checks, and "it runs" is not yet true. The license decision for the SDK's compose file comes first.
- Dependabot was removed from this repo, so dependency updates by bots are a goal, not a feature.
- Engineers can still ship an API with no docstring or writer review. Docsys makes that gap visible
  and fixable. It does not prevent it.

## Suggested additions to the roadmap

- Gate or advisory: compare a page's frontmatter tags with the SDK calls its example code makes. The
  existing gate requires each key symbol to be exercised by an example. The reverse direction (an API
  used by the example but missing from the tags) is not covered.
- Advisory: flag a changed signature whose docstring did not change, as gentle feedback to engineers.
- Cost controls for PR-triggered runs, for example running the model only when the API diff is non-empty.
- A policy for docs PRs that sit unreviewed (regenerate against the latest SDK, or close).

## Walkthrough order, for explaining the system

1. Notice what changed. 2. Route it to pages. 3. Draft. 4. Keep code in separate checked files.
5. Check the work (gates, advisory checks, model rubric, bounded loop, report). 6. Human review in a PR.
