# Reuse decisions: what we adopt, adapt, or build, and why

A living log. Its job is to answer two questions on demand: "Didn't a partner team already do
this?" and "Why didn't you reuse their approach for X?" Each row says what we decided and why, so
the answer is on the page and not in anyone's memory.

Status: 2026-11-14. Sources: a prior review of the SplunkUI docs build, done by the proof-of-concept
author in a signed-in browser (the build's own source package was not inspected); the public
documentation of commercial docs platforms; and an earlier proof of concept. Treat the SplunkUI
description as the best current understanding, to be confirmed with that team.

## What the SplunkUI docs build does (as understood)

- Package teams maintain component code and package docs. The portal build downloads configured
  package-doc versions from an artifact store, and adds portal-owned guides and a manifest of
  packages and versions.
- A shared build library, `@splunk/docs-gen`, wraps an existing React component parser
  (react-docgen). It extracts facts such as prop names, types, and whether a prop is required,
  and renders them in a component-doc format that also supports examples and authored Markdown or MDX.
- A separate step produces LLM-friendly output. A script lists selected authored pages with
  metadata and keywords. A build target turns the portal docs into Markdown plus an `llms.txt`
  index, and the full build links to each package's own `llms.txt`.
- It automates extraction, rendering, assembly, and packaging for LLM readers.
- It does not appear to: detect which docs a code change affects, infer who a page is for, write new
  concepts or tutorials, or ask a human a question when evidence is missing.

## Decisions

| Capability | SplunkUI approach | What the Python SDK needs | Decision | Why |
|---|---|---|---|---|
| Extract API facts from source | React-specific parser | Python signatures and docstrings | Do not adopt | The parser is React-only. Python already has Sphinx autodoc for reference, and docsys reads the API with `ast` for change detection |
| Explicit page list with metadata | Script of pages, paths, keywords | `manifest.toml`: pages, covers, key symbols, examples | Converge | Same idea. Align field names where cheap, and generate the LLM index from our manifest. No shared code needed |
| LLM-friendly Markdown and `llms.txt` | Yes, alongside the site | Wanted | Adopt the idea and conventions | Cheap and valuable. Ask their team for conventions so the two sites look alike to LLM readers. Implementation differs: their build is JavaScript and Webpack, ours is Python and Sphinx |
| Versioned inputs from an artifact store | Package docs by version | Versioned builds from git tags, for GitHub Pages | Keep parallel | Different source of versions. Share the versioning convention if there is one |
| Component-doc format and site renderer | Custom | Sphinx plus the Pages theme | Do not adopt | React-specific. The Python reference is already Sphinx |
| Change-impact detection | Not seen | Core | Build | Novel here: diff the public API and route each change to the pages and examples it affects |
| Plan, questions, and abstain | Not seen. The earlier proof of concept has it | Core for concepts and procedures | Build, borrowing the earlier proof of concept | Plan before drafting. Separate blocking questions from open issues. Allow "insufficient evidence" as a valid result |
| Tested example code kept apart from the docs | Examples authored inside the docs | Core | Build | Novel here: `coderef`, tests, and gates on every example |
| Quality loop with justification reports | Not seen | Core | Build | Novel here: gates, a reviewer, a bounded loop, and reports that say what was and was not evaluated |

## Questions for the SplunkUI maintainers

1. Is the LLM-output configuration in the shared build library package-neutral, or React-specific?
2. What are the `llms.txt` conventions: structure, naming, and which pages are included?
3. Is there a schema for the page metadata and keywords, and could we reuse it?
4. Does anything run on merges or pull requests beyond the build?
5. Is the source of the build library readable to us?
6. Would they want to align on shared conventions for exports?

## How to answer "SplunkUI already does this"

Short version: "They extract and package existing component docs for readers and LLMs. We adopted,
or propose to adopt, their LLM export convention. What we built is the part their build does not do:
spot which SDK changes need documentation, write new concepts and procedures with tested examples,
and score and explain the quality of each draft."

Be ready to say where we chose not to reuse something and why, using the table above. The strongest
point is that the two efforts are complementary: theirs prepares authored docs, ours helps create them.

## Other prior art to keep in view

- Commercial docs platforms (Mintlify, GitBook, ReadMe, and similar) offer a trigger, agent, and
  draft-PR workflow, much of it in beta. Ours runs in a repository we own, keeps examples tested, and
  produces review reports. A side-by-side trial on the same change would settle comparisons.
- The earlier proof of concept explored plan, then draft, with human gates, evidence citations, and
  abstention. Those ideas are on the v0.2 list.
- General practice worth citing: the Diátaxis split of tutorials, how-to guides, reference, and
  explanation; style linting with Vale; executable code samples; and rubric-based review with a
  human release gate.
