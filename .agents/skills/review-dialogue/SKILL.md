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

## Explanations read as natural prose

Findings are easiest to follow when written in plain, flowing sentences rather than code-heavy
shorthand.

Because each thread already anchors its target file and line, explanations can refer to
collaborators by their role in plain English—such as the shared items store, the dialog, or the
list route—and use backticked identifiers only when a specific symbol or type name is itself the
point of discussion. Avoid parenthetical asides, inline code chunks, or symbol lists mid-sentence
that break up the reading flow.

## The review workbench organizes the parallel threads

A local markdown file, `pr-<number>-review.md`, serves as the shared workbench for the review,
organized vertically by discussion thread or by review round when revisiting an archived review in
`~/pr-reviews/` after author updates.

On the first turn, each thread's initial explanation lives in the workbench and is written as if
talking directly to the reviewer in chat—making it easy to read and keep track of multiple parallel
threads in one place without scrolling through a long first chat message.

From there, the back-and-forth exploration happens naturally in chat. As an idea settles or a
comment is drafted, the thread's section in the workbench updates in place to record the outcome
beneath the explanation: a `**Draft comment:**` when feedback is warranted, or a brief
`**Resolution:**` when the thread is deferred or complete.

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

When the reviewer asks for an overall review summary, follow their lead on tone, priorities, and
what came together well—inline comments naturally focus on what to change, whereas the top-level
summary is where the reviewer highlights positive takeaways alongside the main ask.

## Agent posture

- Read and follow [Design Dialogue](../design-dialogue/SKILL.md) as the conversational foundation.
- On the first turn, write the per-thread explanations into `pr-<number>-review.md` in natural,
  conversational prose without parenthetical code chunks or walls of symbol names, and give a
  concise overview of the threads in chat rather than repeating the full breakdown.
- When revisiting a PR after author updates, re-open its workbench in `~/pr-reviews/` or pull
  forward deferred notes from earlier PRs in the stack and append the new round.
- Keep the ongoing discussion in chat, and update the workbench when an idea settles or when
  staging a `**Draft comment:**` or `**Resolution:**` beneath a thread's notes.
- Let the reviewer pace the traversal through the threads.
- Preserve the reviewer's voice, motivation, and framing when refining their drafts and overall
  review summary.
- Keep publishing separate until the reviewer explicitly asks to post comments to GitHub or create
  Linear issues.
- Once the review is published and complete, add the posted comment links, follow-up issue links,
  and a link to the current Cursor agent transcript in `agent-transcripts/` to the top of the
  review file, and move it into `~/pr-reviews/`.
