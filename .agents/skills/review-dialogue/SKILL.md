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

The goal of the investigation is orientation and intuition. Build a concise conceptual picture of
the coherent system shape: which responsibilities belong together, where their boundary should
sit, and which invariants that boundary must preserve. Use the implementation, history, and
codebase precedents to test and refine that picture, keeping incidental friction from the current
composition subordinate to the architectural question. Understanding checks and follow-up
questions can then zoom into technical specifics where needed.

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

A markdown file in `~/pr-reviews/pr-<number>-review.md` serves as the shared workbench for the
review from the first turn through completion, with YAML frontmatter (`pr`, `repo`, `title`,
`author`, `date`, `status`, `posted_comments`, `chat_id`, `skill_version`) and a top header block
holding stack links, follow-up Linear issues, posted comment links, and the transcript link.

Keeping the workbench in `~/pr-reviews/` from the start prevents untracked review files from sitting
in repo clones when switching tasks, and keeps the detailed breakdown and drafted comments in one
durable place while chat stays focused on working through open questions and tradeoffs.

### Working with the workbench

- Create and update `~/pr-reviews/pr-<number>-review.md` directly in place from the first turn
  (running `python3 ~/.cursor/skills/review-dialogue/publish-review.py init <pr>` to scaffold the
  frontmatter and header with `status: active`, or re-opening an existing `~/pr-reviews/pr-<number>-review.md`
  when revisiting a PR after author updates).
- Organize `~/pr-reviews/pr-<number>-review.md` vertically by discussion thread, or by review round
  when revisiting a PR after author updates or pulling forward deferred notes from earlier PRs in
  the stack.
- Treat the initial threads as working hypotheses rather than a fixed outline. Preserve distinct
  observations so the reviewer can traverse them independently, then consolidate their shared
  framing and merge or narrow threads when the dialogue reveals that they are symptoms of the same
  architectural force.
- Include the GitHub PR link near the top of the file and anchor each thread with a `**Target:**`
  listing the repo-root file path and diff line or line range, such as
  `` `mach9-cloud/path/to/file.ts:23` `` or `` `mach9-cloud/path/to/file.ts:15-24` ``.
- On the first turn, write the per-thread explanations into `~/pr-reviews/pr-<number>-review.md`
  and briefly list the threads in chat so the reviewer can choose where to start.
- Use chat to work through open questions and tradeoffs. Once a thread's direction is clear, update
  that thread's section in `~/pr-reviews/pr-<number>-review.md` in place and briefly confirm the
  update in chat so the reviewer can read the draft in the workbench:
  - `**Draft comment:**` or ``**Draft comment (`mach9-cloud/path/to/file.ts:23`):**`` when a thread
    lists multiple target files and the comment anchors to a specific one.
  - `**Draft summary:**` in an overview section when the reviewer wants a top-level review body.
  - `**Resolution:**` when the thread is deferred, tracked only in Linear, or resolved without a PR
    comment.

### Publishing and finishing

- Keep publishing separate until the reviewer explicitly asks to post comments to GitHub, create
  Linear issues, or mark the review done.
- Create any agreed follow-up Linear issues first so their links can be included in the workbench
  and draft comments, then run `python3 ~/.cursor/skills/review-dialogue/publish-review.py`:
  - `init <pr-number-or-url>`: create or refresh `~/pr-reviews/pr-<number>-review.md` with YAML
    frontmatter (`status: active`), PR metadata from GitHub, active `chat_id`, and `skill_version`.
  - `check ~/pr-reviews/pr-<number>-review.md`: validate `**Target:**` paths and diff hunk lines
    against GitHub without mutating anything.
  - `post ~/pr-reviews/pr-<number>-review.md`: publish remaining `**Draft summary:**` and
    `**Draft comment:**` blocks to GitHub, convert them in place to `**Posted comment ([link](...)):**`,
    and update frontmatter (`status: done`, `posted_comments`, `chat_id`, `skill_version`).
  - `done ~/pr-reviews/pr-<number>-review.md` (or `archive`): stamp `status: done`, the active
    Cursor transcript `chat_id`, and `skill_version` in place (moving the file into `~/pr-reviews/`
    if it was started elsewhere), for reviews that finish without posting comments.
  - `publish ~/pr-reviews/pr-<number>-review.md`: run `check`, `post`, and `done` in sequence.

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
