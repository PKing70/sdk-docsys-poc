# FAQ: questions writers and managers ask

*Draft. Add your own questions as they come up in conversations.*

**What is it, in one sentence?**
A system beside an SDK that notices API changes, drafts the guides and the examples that explain
them, checks its own work, and hands a report to a person.

**Does it replace writers?**
No. It drafts and checks. People own review, judgment about readers, and publishing. The aim is to take
over the tedious parts: noticing changes, first drafts, and keeping examples working.

**How do you know the output is correct?**
In layers. Automatic rules catch certain mistakes outright. Examples are separate code that can be tested.
A model-based reviewer scores each draft against the real interface. A person makes the final call. No single
layer proves a page is right, and each report says what was not checked.

**What stops it from inventing features that do not exist?**
Every feature the page names must exist in a snapshot of the SDK's real interface, or the page fails.
Examples that use unknown functions fail too. One gap remains: calls made on objects after creation
cannot be checked without running the code, which is why running examples against a live Splunk is a
next step.

**Where does the example code live?**
In separate script files, each complete and runnable. Pages refer to named parts of a script, and the
code is pulled in when the page is built. Examples can be updated and tested without editing pages.

**How does it know which pages a change affects?**
It compares the SDK's public interface to the last documented version, and a plan file says what each
page and example covers. Only affected items are redone.

**What if the SDK's own documentation is wrong?**
We found cases. For example, some documented return values and options in the key-value store do not match
what the code does. The system flagged them because accurate pages scored low. We recorded them in a report.
Nothing has been reported to the SDK team yet.

**How is this different from what the SplunkUI team does?**
They extract and package existing component documentation for readers and for LLMs. We write new
concept and how-to content with automatically checked examples, and we explain quality. The efforts are complementary,
and we plan to adopt their LLM-export convention. A decision log records what we reuse, adapt, or build.

**Why not buy a documentation platform?**
Several products offer agents that draft docs from code changes, much of it in beta. Ours runs in our own
repository, checks examples automatically, produces review reports, and does not tie us to one vendor. A
side-by-side trial on the same change would settle it, and we would welcome one.

**What does it cost to run?**
Small. A full review of ten pages and examples took on the order of ten model calls. A usage meter prints
exact tokens for every run. We will publish measured numbers after the first from-scratch run.

**Where does the output go?**
Reference pages go to GitHub Pages. Guides go to dev.splunk.com, which is Markdown-sourced, so publishing
is mostly translation. Both destinations are planned, not built.

**What is proven and what is not?**
Proven: change detection and routing, separate, automatically checked examples, automatic checks, and a bounded review loop.
Not yet proven: writing guides from scratch at scale, running examples live, publishing, and cost across
many SDKs.

**Can it work for other SDKs or products?**
That is the direction. The design keeps the general parts separate from the Python-specific parts, but the
only way to learn what really varies is to try a second target.

**What are the risks?**
Trusting a score too much, made-up details, and automatic rewrites that damage good content. We keep people
as the final reviewer, compare named features to the real interface, and plan to change the loop so it
proposes edits instead of making them.

**What do you need from us?**
A decision on a running Splunk for testing examples, an approved route for model access, and a few real
page sources from the content team.
