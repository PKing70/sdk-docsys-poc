# Roadmap and parking lot (not v0.1)

Status: notes from 2026-11-14. Nothing here changes v0.1 scope. It records what we learned
about where the output goes, so v0.1 does not paint v0.2 into a corner.

## Direction

docsys should become a documentation generator that is not specific to one SDK. The Python SDK
is the first target. After it works end to end, a second target shows which parts really vary.

## Two output targets, two workstreams

| Content | Destination | Source of truth |
|---|---|---|
| API reference | GitHub Pages, one static site per SDK | Sphinx output from SDK docstrings and `.rst` |
| Concepts, procedures, tutorials | dev.splunk.com, in their own sections | docsys pages and examples |

Today docsys builds one combined Sphinx site. In v0.2 it feeds two destinations. The change
detection, the tested example files, and the quality loop do not depend on the destination. The
Sphinx staging, the theme, and the `coderef` directive are the parts that change.

## Input 1: the GitHub Pages reference preview (`sdk-docs-preview`)

What it is (from a read-only review, not verified by building):
- A hand-built static snapshot of six SDK and library references: 301 pages, built output only.
  It is not connected to the SDK repos and is not automated.
- The Python reference is ordinary Sphinx (Sphinx 9.1, Furo theme, a shared Splunk style overlay),
  in four versions built from git release tags: `latest`, 3.0.0, 2.1.1, 2.1.0.
- Search is client-side. Links must stay relative so the site works under a subpath.
- Hosted by GitHub Pages from a branch. No workflow, no build scripts, and the build source
  (config, overlay, masthead, version picker) is not in that repository.

What docsys would need:
- Furo plus the style overlay, checked against MyST and `coderef`.
- Versioned output built per git tag, with a version picker, banner, and redirects.
- A build-and-deploy workflow, replacing manual copy and push.
- A decision on whether guides live in the same site or only on dev.splunk.com.

Questions for the owner: where the build source lives; one repo per SDK or a central repo;
retention rule for old versions (count-based is more stable than date-based); whether canonical
and noindex handling is implemented.

## Input 2: the SplunkUI docs build, and an earlier proof of concept

The SplunkUI docs build extracts React component facts and assembles authored guides into a site. A
separate step also produces Markdown and an `llms.txt` index for LLM readers. As understood, it does
not detect change impact, write new guides, or ask humans questions. Full details, and the
adopt, adapt, or build decision for each capability, are in [reuse-decisions.md](reuse-decisions.md).

Conclusions so far:
- Adopt the idea of an LLM-friendly Markdown and `llms.txt` export alongside the HTML. Ask the
  SplunkUI maintainers for their conventions, so the two sites look alike to LLM readers.
- Converge the page manifest idea: our `manifest.toml` already plays the role of their page list.
- Do not adopt the React-specific parser or renderer.
- The novel parts stay ours: change-impact routing, tested examples, and the quality loop.

An earlier proof of concept explored plan, then draft, with human gates. Ideas to bring into docsys:
- A planning step before drafting: what changed, who is affected, what to write, and what is missing.
- Separate blocking questions (pause) from open issues (carried into the draft and flagged).
- "Insufficient evidence" as a valid outcome, and citations for factual claims.
- Treat issue text and repository content as untrusted input to the model.

Also keep in mind: any model used in CI may need an approval process, so the provider interface
stays swappable, and `coderef` must be expanded before any LLM export.

## Input 3: templates from the existing dev.splunk.com pages

Observed on the live site (rendered pages reviewed; authoring system not visible):
- The Python SDK section has a concept overview, Get started, Examples, a How-to hub of seven
  task pages, and Troubleshooting. There are no Python SDK tutorials today.
- Tutorials are not organized by language. They are multi-page modules: a parent page, numbered
  step pages, and a summary page, each step ending with a Review recap.
- Code appears inline, with copy buttons, and also in linked GitHub repositories. External
  references link to reference docs.
- The content looks client-rendered from a content system. The source format is not visible.

How our skeletons compare:

| Type | Site pattern | Our current skeleton | Note |
|---|---|---|---|
| Concept | Noun-phrase title, lead definition, "What you can do", architecture, "See also" | "How it works", "When to use" | Close. Add a lead, capabilities, and "See also" |
| Procedure | "How to ... using the Splunk Enterprise SDK for Python", intro, "To do X" subsections, parameters, "See also" | Prerequisites, Steps, Verify | Ours is clearer. Keeping it is a deliberate departure to confirm with the docs owners |
| Tutorial | Module parent, step pages, summary | none | New content type. Greenfield for Python |

Other notes:
- The site's how-to pages say their examples skip error handling for simplicity. Ours include
  it. That is a tone decision to settle.
- Several existing how-to pages overlap our procedures (connect, run searches, get data). The
  generator needs an "update an existing page" mode, not only "write a new page".
- Because the site shows code inline, a publish step must expand `coderef` into inline code.

## What this means for v0.1

Nothing blocks v0.1. Three seams are worth protecting while we finish it:
1. Pages stay plain Markdown with named code regions, independent of the destination.
2. A publish step that expands `coderef` into inline code (the reviewer already does this).
3. The model provider interface stays swappable.

Cheap additions to consider in v0.1: a `destination` field and a `type` that includes tutorial in
`manifest.toml`.

## v0.2 candidates

- Reference build for GitHub Pages: theme, versioned builds from tags, CI deploy.
- Publish stage for dev.splunk.com: confirm the intake format first, then convert and inline code.
- Tutorial type and a how-to hub page, from the template findings.
- Update-in-place mode for existing pages.
- Template-driven prompts per content type.
- Planning step before generation, with blocking questions versus open issues, abstention, and citations.
- LLM-friendly Markdown and `llms.txt` export alongside the HTML, using conventions agreed with the SplunkUI team.
- Non-destructive loop that writes proposals for review.
- Live example validation against a running Splunk.

## Parking lot: features still to be listed

To be filled in from the product owner's list. For each: does it touch v0.1 design, what it needs
first, and rough size.
