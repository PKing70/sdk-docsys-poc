# Docsys for writers: what changes in your day

*Draft for review. Based on the proof of concept for the Python SDK. Items marked "planned" are
decisions, not yet built.*

When the SDK changes, docsys drafts updates to the guides and examples that the change affects, and
opens a pull request for you to review. You stay in charge. Nothing publishes without your approval.
The system is a fast first drafter, and you are the editor and the approver.

## What stays the same

- You own the voice, accuracy, and structure of the guides.
- You decide what gets published.
- You can still write any page from scratch as you want.

## What changes

1. **You review proposals more often than you write from a blank page.** The system prefers a light
   revision of existing text over a rewrite, so most proposals should be small diffs.
2. **Examples are real code files, not text inside the page.** Each example is a `.py` file in the
   repository with named regions. The page pulls the code in with a `coderef`. Pages contain no
   embedded code.
3. **You tag each page with the SDK symbols it covers (planned).** The tags go in the page's
   frontmatter. The system uses them to find which pages a change affects, and the doc plan is
   generated from them. You tag once, and nothing else needs updating by hand.
4. **Reviews happen in a pull request.** The description says what to focus on and links to a report
   for each page. The diff shows exactly what changed.
5. **Drafts will be shaped toward Splunk doc voice (planned).** Before a draft reaches you, the system
   will draw on existing content, examples from the Nexus example gallery, the style guide, and linter
   rules, and score drafts against them. The aim is a first draft that already reads like our docs.

## A change, start to finish

1. An engineer changes the SDK. A new method appears, or a docstring is edited.
2. Docsys flags the change. Every signature change and every docstring edit is flagged, because a
   docstring edit might be a typo or a behavior change.
3. The system finds the pages whose tags include the changed symbols.
4. A model drafts revisions and updated examples. Checks run, and a report is written for each page.
5. A documentation PR opens, and your team is assigned to review it.
6. You review the diff and the report, edit as needed, and approve or reject.

The documentation PR does not block the engineer's release. It may arrive before the release or after
it, depending on timing.

## What you will review

Start with the report for each page. It tells you what to trust and what to check yourself.
- **What passed.** Rules such as: named APIs exist, examples exercise the symbols the page teaches,
  required sections are present, and no code is embedded in the page.
- **What was skipped.** Anything that did not run is listed under "Not evaluated." Skipped means
  unchecked, not passed.
- **The model's review scores.** These cover accuracy, clarity, teaching value, and completeness. They
  help you decide where to look first. They do not replace your judgment.

A high score does not mean the page is right. Some SDK docstrings are wrong, and a draft built on a
wrong docstring can read well and still be inaccurate. If something looks wrong to you, trust that.

## When you disagree with the system

Reject or edit the page, and say why in a PR comment (planned: a `docsys-feedback` label). Patterns in
those comments are how the checks improve. A rejection is useful input, and it is not a failure.

## What you will need to learn

- **Examples live outside the page.** You edit a `.py` file when you want to change an example, not the
  page text.
- **The `coderef` directive.** It pulls a named region of an example into a page.
- **Frontmatter tags (planned).** One short list per page.

The agent drafts these pieces for you at first, so the early learning curve is reading and reviewing.

## What it does not do yet

- It has not run examples against a live Splunk. Today an example can pass static checks, and "it
  runs" is not yet proven. A test environment is the next step.
- It has not generated a guide from scratch with a real model. Expect it to be strongest at keeping
  existing pages current. A new tutorial probably needs a template for the model to follow, at least if you want to read like existing tutorials.
- It does not publish. Publishing to the developer site is not built, but when it is, approval will still go through the doc team writer.

## What would help from you

- **Examples worth imitating.** Send your best tutorials and how-tos, so templates reflect the team's
  work and not one author's.
- **First reviews.** The first few PRs will show what the report should say and where the checks miss.
- **Opinions on the workflow.** Is a PR the right place to review? What should the PR description lead
  with?
