---
name: review-dialogue
description: Conducts a PR review as a design dialogue, turning initial observations and questions about a diff into a grounded mental model, a living review document, and principled feedback in the reviewer's voice. Use only when explicitly invoked.
disable-model-invocation: true
---

# Review Dialogue

Review Dialogue applies [Design Dialogue](../design-dialogue/SKILL.md) to pull request reviews.

It is a shared process for turning initial observations, questions, and points of discomfort from
reading a diff into a grounded mental model of the change and well-scoped feedback.

## Investigation separates mechanism from design tension

Initial review notes often point to a symptom or an unfamiliar area of the code. Investigating the
diff, commit history, and surrounding subsystem separates two kinds of evidence:

- **Mechanical truth:** Why the code was written this way, what runtime sequence or constraint
  produced it, and how the surrounding system behaves today.
- **Underlying design tension:** Which invariant, ownership boundary, state lifetime, or codebase
  convention is at stake, and whether the surface detail exposes a deeper structural issue.

Understanding checks and follow-up questions test both layers. They clarify how the system works
and reveal whether the current tradeoff is sound or points to a deeper root cause.

## The review document tracks the state of each thread

A local markdown file (`pr-<number>-review.md`) serves as the shared workbench for the review,
organized vertically by discussion thread.

Each thread begins with its target location and the findings from investigation—what is happening
mechanically and the underlying design tension—giving the dialogue a persistent technical reference
as each thread is explored.

As a thread settles through conversation, its section evolves in place to record the outcome
beneath the investigation notes: a drafted comment when feedback is warranted, or a brief
resolution note when the thread is deferred or complete.

## Alignment determines the disposition of each thread

Each thread can serve a different purpose once its underlying model is clear. Alignment resolves a
thread to the outcome that matches its scope:

- **Actionable suggestion on the PR:** A self-contained boundary, type, invariant, or cleanup
  improvement that belongs in this change.
- **Non-blocking note:** Context worth sharing when follow-up work is already tracked or the
  observation is informational.
- **Follow-up issue:** A broader architectural or state-model direction whose motivation and
  concrete examples belong in a dedicated issue.
- **Resolved understanding:** A thread where understanding the mechanism confirms the current
  approach fits the problem.

## Feedback transfers the learning

A review comment lets the author experience the discovery arc that produced the insight, written in
the reviewer's first-person voice:

1. **Observation and motivation:** The concrete detail in the diff that caught the reviewer's eye
   and the question or suspicion it raised.
2. **Diagnosis:** What tracing the code exposed about the deeper issue and how it interacts with the
   rest of the subsystem or codebase conventions.
3. **Recommendation:** A direct, principle-backed `**Suggestion:** ...` (or
   `**note (non-blocking):** ...`) that states the concrete change and the invariant it preserves.

## Agent posture

- Read and follow [Design Dialogue](../design-dialogue/SKILL.md) as the conversational foundation.
- On the first turn, write the per-thread investigation into `pr-<number>-review.md` and give a
  concise overview of the threads in chat.
- Populate the review document with investigation findings first, and stage each `**Draft comment:**`
  or `**Resolution:**` in place beneath a thread's notes once that thread settles in dialogue.
- Let the reviewer pace the traversal through the threads.
- Preserve the reviewer's voice, motivation, and framing when refining their drafts.
- Keep publishing separate until the reviewer explicitly asks to post comments to GitHub or create
  Linear issues.
