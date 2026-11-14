# SDK Docsys: automated documentation/example system

*A one-page overview of a proof of concept. Draft for review.*

## SDKs could write their own docs

Our SDKs change faster than my developer's guide. The reference pages are currently generated from source code, but documentation
that teaches people, conceptually orients readers, and guides customers through use cases with runnable examples, is currently written by hand, whether by an Eng within a Sphinx code comment, or by a Writer contributing to devportal. 

When an SDK changes, someone notices, determines which guides are affected, rewrites them, and checks that the example code still works. That work is manual, and prone to outdatedness. If that someone becomes an agent in the SDK production workflow, this work can largely be drafted, then presented to SMEs for efficient review before approval.

## What we built

An agent-style workflow that sits beside the SDK without changing it. When the SDK's public API changes, it:

1. **Notices what changed** by comparing the API to the last documented version.
2. **Finds the affected guides and examples** using a plan that says what each page covers.
3. **Drafts new or updated pages and short, runnable examples** with a language model (Claude today; the model is swappable).
4. **Keeps the example code in separate, automatically checked files.** Pages pull the code in at publish time, so the code is maintained and checked on its own.
5. **Checks its own work** with automatic rules, a model-based reviewer, and a limited number of
   improvement passes. Every page gets a short report explaining why it is considered final, and what was checked or not checked.

People stay in charge of review and publishing.

## New value

- **It writes the developer guidance content, not only the reference.** Existing tools (eg Sphinx, OpenAPI) mostly extract and package
  what writers already wrote or tables of facts from code signatures, eg data types of parameters.
- **Examples are real code that is checked automatically,** not snippets embedded within a page. Examples become not only automated but, once run against a live Splunk, real and functional (and transpilable, someday)
- **Quality is explained,** with a report per page. TBD: our metrics and tools for "quality" (such as incorporating our style guides and linter rules) are still to come. But the framework is here, with 43 automated tests, about 30 automatic checks across prose, code, and coverage, and a model reviewer that scores accuracy, clarity, teaching value, and completeness.
- **It does not depend on one vendor.** (Meaning, Mintlify et al, though they deserve some credit for inspiration). It runs in our own repository, and the model can be swapped.

## Current progress

- Built and tested for the Python SDK, with 43 automatic tests passing.
- Reviewed by a model reviewer. It found real gaps in our drafts, and we fixed them. It also exposed
  errors in the SDK's own documentation.
- Not yet proven: writing guides from scratch at scale, running the examples against a live Splunk, and
  publishing to the developer site. Those are the next steps.

## What's next

Reference pages publish to GitHub Pages. Guides publish to dev.splunk.com, which is Markdown-sourced, so
publishing is mostly translation. We plan to align with the SplunkUI team on LLM-friendly exports, and to
reuse what helps instead of rebuilding it.

## What I need

* Live Splunk for testing examples (going to add Dockerized Splunk Enterprise and test framework in next rev)
* An approved route for model access (circuit 1 hour chat completion is insufficient; ai-devx onboarding should give 24-hour tokens to anthropic. Real production pipelines that are truly automated will need service principals instead of hand-renewed tokens).
* Real examples to shape templates; I've started with my own tutorials and dev guide but that's both myopic and I know we have more great stuff out there across the team members and doc sets.
