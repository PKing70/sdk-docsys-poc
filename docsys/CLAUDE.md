# docsys: instructions for a new chat

Read these first, in order, and don't read other files unless needed:

1. `docs/handoff.md`
2. `docs/handoff-addendum.md` (design decisions made after the handoff was written)
3. `docs/overview/one-pager.md`

Standing preferences:

- Never read the user's clipboard or load a secret for them unless they ask for that exact thing.
  Never put a key in a file, a command line, or the repo. Run model-using commands through
  `bin/with-key`.
- Ask before publishing or pushing anything. Make changes on a branch. Commits use the GitHub noreply
  address, not a work email.
- The SDK stays unmodified. Everything added lives in `docsys/` and one workflow file.
- Give plain explanations first, with short answers. Prefer checking claims against the source over
  trusting a score.
