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
diff, commit history, and surrounding subsystem answers two high-level questions:

- **Role and intent:** What job this piece is doing in the system and why the author shaped it this
  way.
- **Design tension:** Which responsibility boundary, invariant, state lifetime, or codebase
  convention is at stake, and whether the current shape fits the broader system model.

The goal of writing this down for the reviewer is orientation and intuition—painting a concise
conceptual picture rather than an exhaustive code trace, commit log, or step-by-step reasoning
chain. Understanding checks and follow-up questions can then zoom into technical specifics only
where needed.

## The review document tracks the state of each thread

A local markdown file (`pr-<number>-review.md`) serves as the shared workbench for the review,
organized vertically by discussion thread.

Each thread begins with its target location and a brief, skimmable summary of the role/intent and
design tension—giving the dialogue a persistent reference as each thread is explored.

As a thread settles through conversation, its section evolves in place to record the outcome
beneath the notes: a drafted comment when feedback is warranted, or a brief resolution note when
the thread is deferred or complete.

## Alignment determines the disposition of each thread

Each thread can serve a different purpose once its underlying model is clear. Alignment resolves a
thread to the outcome that matches its scope:

- **Actionable suggestion on the PR:** A self-contained boundary, type, invariant, or cleanup
  improvement that belongs in this change.
- **Non-blocking note:** Context worth sharing on the PR when follow-up work is already tracked
  (including the reviewer's own follow-up tickets) or the observation is informational.
- **Follow-up issue:** A broader architectural or state-model direction whose motivation and
  concrete examples belong in a dedicated Linear issue.
- **Resolved understanding:** A thread where understanding the mechanism confirms the current
  approach fits the problem.

## Feedback frames the motivation and direction

A review comment paints a clear conceptual picture for the author in the reviewer's first-person
voice, focusing on why a boundary or shape feels off and what direction to take rather than
prescribing every low-level detail of the fix:

1. **Initial impetus:** Start with the concrete detail in the diff that caught the reviewer's eye
   and the question or intuition it raised.
2. **Bridging context (only as needed):** Add a sentence or two of technical context only when the
   impetus alone does not make the underlying issue clear. When the observation speaks for itself,
   go straight to the recommendation.
3. **Recommendation:** End with a direct, principle-backed `**Suggestion:** ...` (or
   `**note (non-blocking):** ...`) stating the conceptual change or boundary to aim for.

## Agent posture

- Read and follow [Design Dialogue](../design-dialogue/SKILL.md) as the conversational foundation.
- On the first turn, write the per-thread conceptual notes into `pr-<number>-review.md` (keeping
  each thread's notes to a few high-signal bullets rather than a wall of code details) and give a
  concise overview of the threads in chat.
- Populate the review document with investigation notes first, and stage each `**Draft comment:**`
  or `**Resolution:**` in place beneath a thread's notes once that thread settles in dialogue.
- Let the reviewer pace the traversal through the threads.
- Preserve the reviewer's voice, motivation, and framing when refining their drafts.
- Keep publishing separate until the reviewer explicitly asks to post comments to GitHub or create
  Linear issues.
- Once the review is published and complete, add the posted comment links, follow-up issue links,
  and a link to the current Cursor agent transcript (`.jsonl` in `agent-transcripts/`) to the top
  of the review file, and move it into `~/pr-reviews/`.
