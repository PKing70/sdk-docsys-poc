# Docsys for managers: what it is, what it changes, what we need

*Draft for review. Based on the working proof of concept for the Python SDK.*

## The problem

Our SDK reference pages (eg https://docs.splunk.com/Documentation/PythonSDK) regenerate from source (https://github.com/splunk/splunk-sdk-python). The pages that teach people (concepts, how-tos,
tutorials, runnable examples, eg https://dev.splunk.com/enterprise/docs/devtools/python/sdk-python) are written by hand. When the SDK changes, someone has to be looped in,
work out which guides and tutorials are affected, rewrite them, and check that the example code still runs. That
work is manual, so it falls behind.

## What docsys does

When the SDK's public API changes, docsys opens a documentation pull request. It does five things:

1. **Detects the change.** It compares the API to the last accepted snapshot (planned: the last
   published version). This step is a
   mechanical comparison, with no model involved. Every signature change and every docstring edit is
   flagged.
2. **Finds the affected pages.** The doc plan lists which SDK symbols each page covers, and the system
   looks them up. Planned: each page declares its symbols in its own frontmatter, and the plan is
   generated from those declarations.
3. **Drafts the update.** A language model revises the affected pages and their examples. It prefers
   a light revision of existing text over a rewrite, so reviews stay small and writers keep their voice.
4. **Keeps example code in real, separate files.** Pages pull the code in at build time, so examples
   can be tested and maintained on their own.
5. **Checks its own work.** Automatic rules and a model reviewer score each draft. A short report
   explains why the draft is considered final and lists what was not checked.

## How it fits the engineering workflow

Engineers keep their current process: commit, regenerate the reference, tag, release. Docsys adds a
separate documentation PR. It does not block the release. The PR can be reviewed before the release
if there is time, or after it if an engineer needs to ship a fix today.

This is deliberate. It means docsys is a quality and coverage improvement, not a new gate for
engineering. An engineer can still ship an API with no docstring or writer review, which is true
today. The difference is that docsys makes that gap visible and produces a proposed fix.

A person reviews and approves every documentation PR. Nothing publishes without approval.

## What it does and does not promise

**Today it can show:**
- Named APIs exist in the SDK, and examples exercise the symbols a page claims to teach.
- Pages follow structure and readability rules, and examples meet code rules.
- Each page has a report that lists what ran and what was skipped.

**It does not yet show:**
- That examples run against a live Splunk. That needs a test environment, which is the next step, using a Docker-based runner.
- That readers find the pages helpful. This needs reader feedback.
- Automated publishing. Reference pages would go to GitHub Pages (TBD) and guides to dev.splunk.com, and
  neither path is fully built.

A passing quality score means a draft meets the stated rules. It never replaces human review. When a
reviewer disagrees with a high score, that disagreement is recorded and used to improve the checks.

## How we would measure it

- **Docs lag:** the time between an SDK release and approval of its documentation PR.
- **Coverage:** the share of public APIs that have at least one runnable example.
- **Review effort:** how much reviewers change a proposal before approving it.
- **Authoring effort:** the time a writer or SME spends reviewing a generated procedure, tutorial, or
  example, compared with authoring the same content by hand.

## What we need

1. **A live Splunk test environment** (Dockerized Splunk Enterprise) so examples run for real. The
   SDK's compose file accepts a license automatically, so we need a decision on that first.
2. **An approved route for model access.** The current corporate Circuit API route is too short-lived for an
   automated pipeline and afaik supports only chat completion. A production pipeline needs service credentials, not hand-renewed tokens.
3. **Real examples from the team.** The templates are shaped by one author's tutorials so far. More
   good material across the team and doc sets would improve them. This could include examples from
   the Nexus example gallery.
4. **A named reviewer team** in the repository to receive documentation PRs.

## Decision requested

Approve a pilot on the Python SDK with the non-blocking review model, using docs lag as the first
measure of success.

## What I will try next

What is unproven: no from-scratch generation run with a real model has been done yet. Everything
above that involves drafting new content is a design, not a result.

What I expect, and will test:
- One new API will probably not produce a full tutorial from scratch, but it could produce a usage
  procedure.
- A tutorial that invokes a collection of APIs could be maintained automatically once it exists. It
  probably cannot be synthesized from scratch without a template for the model to follow.

The goal: commit a new API and see the pipeline produce the Sphinx reference page (today's function),
a code example in the repo, a topic that pulls that example in with a `coderef` instead of embedded
text, and a conceptual or tutorial topic to go with it. We shall see.
