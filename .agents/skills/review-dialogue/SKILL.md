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
diff, commit history, surrounding subsystem, and any stacked PRs clarifies what job the piece is
doing in the system, why the author shaped it this way, and whether later PRs in a stack change it,
along with which responsibility boundary, invariant, state lifetime, or codebase convention is at
stake.

The goal of the investigation is orientation and intuition. Paint a concise conceptual picture
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
  offer to create it rather than searching external notes or agent transcripts unless explicitly
  asked.

## Explanations and comments read as natural prose

Explanations in the workbench, replies in chat, and drafted comments are easiest to follow when
written in plain, flowing sentences rather than code-heavy shorthand.

Because each thread already anchors its target file and line, prose can refer to collaborators by
their role in plain English and use backticked identifiers only when a specific symbol or type name
is itself the point of discussion.

### Prose rules

All explanations, chat replies, and drafted comments follow these rules:

- Write in natural, conversational prose as if talking directly to a teammate.
- Avoid parenthetical asides, inline code chunks, call chains, or walls of symbol names
  mid-sentence that break up the reading flow.

## The review workbench organizes the parallel threads

A local markdown file, `pr-<number>-review.md`, serves as the shared workbench for the active
review, and completed reviews live in `~/pr-reviews/pr-<number>-review.md` with stack links,
follow-up Linear issues, and posted comment links in the top header block.

Keeping the detailed breakdown and drafted comments in the workbench makes it easy to read and
track multiple parallel threads in one place, while chat stays focused on working through open
questions and tradeoffs.

### Working with the workbench

- Organize `pr-<number>-review.md` vertically by discussion thread, or by review round when
  re-opening an archived review from `~/pr-reviews/` after author updates or pulling forward
  deferred notes from earlier PRs in the stack.
- Include the GitHub PR link near the top of the file and anchor each thread with a `**Target:**`
  listing the repo-root file path and diff line or line range, such as
  `` `mach9-cloud/path/to/file.ts:23` `` or `` `mach9-cloud/path/to/file.ts:15-24` ``.
- On the first turn, write the per-thread explanations into `pr-<number>-review.md` and briefly
  list the threads in chat so the reviewer can choose where to start.
- Use chat to work through open questions and tradeoffs. Once a thread's direction is clear, update
  that thread's section in `pr-<number>-review.md` in place and briefly confirm the update in chat
  so the reviewer can read the draft in the workbench:
  - `**Draft comment:**` or ``**Draft comment (`mach9-cloud/path/to/file.ts:23`):**`` when a thread
    lists multiple target files and the comment anchors to a specific one.
  - `**Draft summary:**` in an overview section when the reviewer wants a top-level review body.
  - `**Resolution:**` when the thread is deferred, tracked only in Linear, or resolved without a PR
    comment.

### Publishing and archiving

- Keep publishing separate until the reviewer explicitly asks to post comments to GitHub or create
  Linear issues.
- Create any agreed follow-up Linear issues first so their links can be included in the workbench
  and draft comments, then run `python3 ~/.cursor/skills/review-dialogue/publish-review.py`:
  - `check pr-<number>-review.md`: validate `**Target:**` paths and diff hunk lines against GitHub
    without mutating anything.
  - `post pr-<number>-review.md`: publish remaining `**Draft summary:**` and `**Draft comment:**`
    blocks to GitHub and convert them in place to `**Posted comment ([link](...)):**` so re-runs
    are idempotent.
  - `archive pr-<number>-review.md`: stamp the active Cursor transcript link into the header and
    move the workbench to `~/pr-reviews/`.
  - `publish pr-<number>-review.md`: run `check`, `post`, and `archive` in sequence.

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
voice, focusing on the design principle at stake and what the suggested direction unlocks rather
than narrating how the current code works:

1. **The tension and principle:** Start with what caught the reviewer's eye in the diff and why the
   responsibility split or boundary feels off, grounding it in the relevant design principle or
   codebase precedent.
2. **The direction and leverage:** End with a `**Suggestion:** ...` or
   `**note (non-blocking):** ...` stating the conceptual boundary to aim for and what capability or
   guarantee it unlocks, leaving low-level implementation mechanics to the author.

### Drafting rules

- Preserve the reviewer's voice, principles, and motivation when writing or trimming drafts,
  cutting mechanical code traces rather than the underlying principle or why it matters.
- When the reviewer asks for an overall review summary, follow their lead on tone, priorities, and
  what came together well. Inline comments naturally focus on what to change, whereas the top-level
  summary highlights positive takeaways alongside the main ask.

## Agent posture

- Read and follow [Design Dialogue](../design-dialogue/SKILL.md) as the conversational foundation.
- Let the reviewer pace the traversal through the threads.
- Keep settled material compressed in chat while recording the durable state in the workbench.
