---
name: review-dialogue
description: Conducts a PR review as a design dialogue, turning initial observations and questions about a diff into a concise conceptual model, a living review workbench, and principled feedback in the reviewer's voice. Use only when explicitly invoked.
disable-model-invocation: true
---

# Review Dialogue

Review Dialogue applies [Design Dialogue](../design-dialogue/SKILL.md) and
[Workbench](../workbench/SKILL.md) to pull request reviews.

The goal of the review is to evaluate whether a change is solving the right problem at the right
boundary, build a clear conceptual picture of how it fits the system, and turn initial observations
and questions from reading a diff into well-scoped feedback.

## Investigation and stack context

Investigating the diff, commit history, surrounding subsystem, and any stacked PRs clarifies what
job the piece is doing in the system, why the author shaped it this way, and whether later PRs in a
stack change it, following [Synthesis builds a coherent system picture](../workbench/SKILL.md#synthesis-builds-a-coherent-system-picture).

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

## The review workbench

A markdown file in `~/pr-reviews/pr-<number>-review.md` serves as the shared workbench for the
review from the first turn through completion, with YAML frontmatter (`pr`, `repo`, `title`,
`author`, `date`, `status`, `posted_comments`, `chat_id`, `skill_version`) and a top header block
holding stack links, follow-up Linear issues, posted comment links, and the transcript link.

### Working with the workbench

Follow [Thread anatomy and prose](../workbench/SKILL.md#thread-anatomy-and-prose) and
[Workbench and chat flow](../workbench/SKILL.md#workbench-and-chat-flow):

- Create and update `~/pr-reviews/pr-<number>-review.md` in place from the first turn by running
  `python3 ~/.cursor/skills/review-dialogue/publish-review.py init <pr>` to scaffold the frontmatter
  and header with `status: active`, or re-open the existing file and append a new round when
  revisiting a PR after author updates or pulling forward deferred stack notes.
- Anchor each thread with `**Target:**` using repo-root paths and diff lines such as
  `` `mach9-cloud/path/to/file.ts:15-24` ``, write the first-turn explanations into the workbench in
  natural prose, and keep the first chat reply to a short index of the threads rather than repeating
  the full explanations in chat.
- Once a thread's direction settles in chat, record its outcome in place in
  `~/pr-reviews/pr-<number>-review.md` and confirm briefly in chat without repeating drafts:
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
    Cursor transcript `chat_id`, and `skill_version` in place for reviews that finish without
    posting comments.
  - `publish ~/pr-reviews/pr-<number>-review.md`: run `check`, `post`, and `done` in sequence.

## Alignment determines the disposition of each thread

Each thread resolves to the outcome that matches its scope once its underlying model is clear:

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

- Apply
  [Explanations stay at the level of roles and invariants](../design-dialogue/SKILL.md#explanations-stay-at-the-level-of-roles-and-invariants)
  to every `**Draft comment:**` and `**Draft summary:**`: state collective findings in plain English,
  name concrete identifiers only when they are the boundary under discussion or an explicit target
  to change, and avoid parenthetical asides, inline code chunks, call chains, or mid-sentence symbol
  lists.
- Preserve the reviewer's voice, principles, and motivation when writing or trimming drafts,
  cutting mechanical code traces rather than the underlying principle or why it matters.
- When the reviewer asks for an overall review summary, follow their lead on tone, priorities, and
  what came together well. Inline comments naturally focus on what to change, whereas the top-level
  summary highlights positive takeaways alongside the main ask.

## Agent posture

- Read and follow [Design Dialogue](../design-dialogue/SKILL.md) and the shared invariants in
  [Workbench](../workbench/SKILL.md) as the foundation of the review.
- Let the reviewer pace the traversal through the threads, keeping settled material compressed in
  chat while recording the durable state in `~/pr-reviews/pr-<number>-review.md`.
