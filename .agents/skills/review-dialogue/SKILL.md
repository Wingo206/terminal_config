---
name: review-dialogue
description: Conducts a PR review as a design dialogue, turning initial observations and questions about a diff into a concise conceptual model, a living review document, and principled feedback in the reviewer's voice. Use only when explicitly invoked.
disable-model-invocation: true
---

# Review Dialogue

Review Dialogue applies [Design Dialogue](../design-dialogue/SKILL.md) to pull request reviews.

The goal of the review is to evaluate whether a change is solving the right problem at the right
boundary, build a clear conceptual picture of how it fits the system, and turn initial
observations and questions from reading a diff into well-scoped feedback.

## Investigation paints a conceptual picture

Initial review notes often point to a symptom or an unfamiliar area of the code. Investigating the
diff, commit history, surrounding subsystem, and any stacked PRs answers two high-level questions:

- **What's going on:** What job this piece is doing in the system, how it behaves in practice, and
  why the author shaped it this way, including whether later PRs in a stack change it.
- **Why it matters:** Which responsibility boundary, invariant, state lifetime, or codebase
  convention is at stake, and whether the current shape fits the broader system model.

The goal of the investigation is orientation and intuition—painting a concise conceptual picture
rather than an exhaustive code trace, commit log, or step-by-step reasoning chain. Understanding
checks and follow-up questions can then zoom into technical specifics where needed.

### Investigation rules

- When reviewing a stacked PR or revisiting a PR after author updates, read only the matching
  `~/pr-reviews/pr-<number>-review.md` files for that PR or stack rather than every file in
  `~/pr-reviews/`.
- Because `~/pr-reviews/` is outside the repo workspace, Cursor's `Glob` and `Grep` tools silently
  fall back to the workspace root. Use `Read` directly when you know the PR number, or `rg` / `head`
  via `Shell` on `~/pr-reviews/` when searching across prior reviews.
- When the reviewer references a prior review note or a Linear issue they think they created, check
  `~/pr-reviews/` and run a couple of targeted Linear queries; if it does not turn up, say so and
  offer to create it rather than searching external notes (such as Obsidian vaults) or agent
  transcripts unless explicitly asked.

## Explanations read as natural prose

Findings are easiest to follow when written in plain, flowing sentences rather than code-heavy
shorthand.

Because each thread already anchors its target file and line, explanations can refer to
collaborators by their role in plain English—such as the shared items store, the dialog, or the
list route—and use backticked identifiers only when a specific symbol or type name is itself the
point of discussion.

### Prose rules

- Write per-thread explanations in natural, conversational prose as if talking directly to the
  reviewer in chat.
- Avoid parenthetical asides, inline code chunks, call chains, or walls of symbol names
  mid-sentence that break up the reading flow.

## The review workbench organizes the parallel threads

A local markdown file, `pr-<number>-review.md`, serves as the shared workbench for the active
review, and completed reviews live in `~/pr-reviews/pr-<number>-review.md` with stack links,
follow-up Linear issues, and posted comment links in the top header block.

Keeping the detailed breakdown in the workbench makes it easy to read and track multiple parallel
threads in one place without scrolling through a long first chat message, while the ongoing
back-and-forth exploration happens naturally in chat.

### Working with the workbench

- Organize `pr-<number>-review.md` vertically by discussion thread, or by review round when
  re-opening an archived review from `~/pr-reviews/` after author updates or pulling forward
  deferred notes from earlier PRs in the stack.
- Include the GitHub PR link near the top of the file and anchor each thread with a `**Target:**`
  listing the repo-root file path and diff line or line range, such as
  `` `mach9-cloud/path/to/file.ts:23` `` or `` `mach9-cloud/path/to/file.ts:15-24` ``.
- On the first turn, write the full per-thread explanations into `pr-<number>-review.md` and give a
  concise overview of the threads in chat rather than repeating the full breakdown.
- Keep the ongoing discussion in chat, and update the thread's section in the workbench in place as
  an idea settles to record the outcome beneath the explanation:
  - `**Draft comment:**` (or ``**Draft comment (`mach9-cloud/path/to/file.ts:23`):**`` when a thread
    lists multiple target files and the comment anchors to a specific one) for an inline PR comment.
  - `**Draft summary:**` in an overview section when the reviewer wants a top-level review body.
  - `**Resolution:**` when the thread is deferred, tracked only in Linear, or resolved without a PR
    comment.

### Publishing and archiving

- Keep publishing separate until the reviewer explicitly asks to post comments to GitHub or create
  Linear issues.
- Create any agreed follow-up Linear issues first so their links can be included in the workbench
  and draft comments, then run `python3 ~/.cursor/skills/review-dialogue/publish-review.py` as a
  whole (`publish pr-<number>-review.md`) or step by step when recovering or staging:
  - `check pr-<number>-review.md`: validate `**Target:**` paths and diff hunk lines against GitHub
    without mutating anything.
  - `post pr-<number>-review.md`: publish remaining `**Draft summary:**` and `**Draft comment:**`
    blocks to GitHub and convert them in place to `**Posted comment ([link](...)):**` so re-runs
    are idempotent.
  - `archive pr-<number>-review.md`: stamp the active Cursor transcript link into the header and
    move the workbench to `~/pr-reviews/`.

## Alignment determines the disposition of each thread

Each thread can serve a different purpose once its underlying model is clear. Alignment resolves a
thread to the outcome that matches its scope:

- **Actionable suggestion on the PR:** A self-contained boundary, type, invariant, or cleanup
  improvement that belongs in this change.
- **Non-blocking note:** Context worth sharing on the PR when follow-up work is already tracked in
  later PRs or follow-up tickets, or when the observation is informational.
- **Defer to a later PR in the stack:** A concern that is addressed or better raised on a downstream
  PR in the stack, recorded in the workbench to verify when reviewing that PR.
- **Follow-up issue:** A broader architectural or state-model direction whose motivation and
  concrete examples belong in a dedicated Linear issue.
- **Resolved understanding:** A thread where understanding the mechanism confirms the current
  approach fits the problem.

## Feedback frames the motivation and direction

A review comment paints a clear conceptual picture for the author in the reviewer's first-person
voice, focusing on why a boundary or shape feels off and what the suggested direction unlocks
rather than tracing every internal symbol or prescribing low-level details of the fix:

1. **Initial impetus:** Start with the detail in the diff that caught the reviewer's eye and the
   question or intuition it raised.
2. **Bridging context when needed:** Add a sentence or two of context only when the impetus alone
   does not make the underlying issue clear. When the observation speaks for itself, go straight to
   the recommendation.
3. **Recommendation:** End with a direct, principle-backed `**Suggestion:** ...` or
   `**note (non-blocking):** ...` stating the conceptual change or boundary to aim for.

### Drafting rules

- Preserve the reviewer's voice, motivation, and framing when refining their drafts and overall
  review summary.
- When the reviewer asks for an overall review summary, follow their lead on tone, priorities, and
  what came together well—inline comments naturally focus on what to change, whereas the top-level
  summary is where the reviewer highlights positive takeaways alongside the main ask.

## Agent posture

- Read and follow [Design Dialogue](../design-dialogue/SKILL.md) as the conversational foundation.
- Let the reviewer pace the traversal through the threads.
- Keep settled material compressed in chat while recording the durable state in the workbench.
