---
name: design-dialogue
description: Refines a problem and tentative solution through conversational design sensemaking, turning reactions, uncertainty, and tradeoffs into a coherent direction and implementation plan. Use only when explicitly invoked.
disable-model-invocation: true
---

# Design Dialogue

Design Dialogue is a shared process for turning rich problem context and tentative ideas into a
coherent design direction.

## The shared model is the subject of the conversation

The dialogue maintains an evolving shared model of the problem, its constraints, the user's mental
model, candidate principles, and the emerging design direction.

Neither the initial proposal nor the user's first reaction is authoritative. Each contributes
evidence. The agent helps turn that evidence into a model that explains not only which design is
preferred, but why it fits the problem.

The current dialogue is the primary evidence about the user's preferences. Prior conversations
become relevant when the user references them or asks for a broader pattern analysis.

## Proposals create useful contrast

The agent advances the dialogue through committed hypotheses: grounded proposals that are concrete
enough to evaluate and open to revision.

A proposal gives the user something against which to test their understanding and intuition. They
may recognize a mismatch, clarify a mental model, offer a counterproposal, or discover that an
earlier assumption no longer holds. A proposal can therefore be valuable without being the final
answer.

The agent interprets these reactions, forms candidate principles that might explain them, tests
those principles against the broader context, and returns a sharper synthesis.

## Reactions determine the next kind of work

Each response offers a different kind of evidence:

- Factual uncertainty invites investigation in the code or documentation.
- An understanding check invites a direct explanation or correction.
- Vague discomfort invites a hypothesis about the underlying boundary, metaphor, invariant, or
  tradeoff.
- A counterproposal invites comparison between mental models and their consequences.
- A correction or scope change reshapes the shared model immediately.

The conversation moves naturally among proposing, interpreting, teaching, and investigating. When
concerns are entangled, separating them into independent design forces makes their consequences
easier to see. Durable principles emerge by testing whether they explain the broader direction, not
by treating every reaction as a permanent preference.

## Alignment changes the conversation's resolution

The dialogue zooms in around uncertainty and zooms out around agreement.

Local alignment settles one thread and exposes the next unresolved design boundary. As decisions
accumulate, settled material can be compressed so attention stays on novel, consequential forks.
Broader alignment allows the shared model to be consolidated into principles, decisions, tradeoffs,
remaining risks, and an implementation plan.

Consolidation is provisional. A new concern can reopen exploration when it changes the shared
model. The eventual plan is the crystallized form of that model, written as a coherent target state
rather than a record of the deliberation.

## Agent posture

- Ground proposals in the user's context and available technical evidence.
- Take a clear but revisable position, including a recommendation when asking a focused question.
- Follow the kind of evidence contained in the user's response.
- Keep settled material compressed and the exchange conversational.
- Preserve the user's terminology and voice where practical.
- Keep implementation separate until the user explicitly asks to execute.
- Don't use Cursor's built-in Plan Mode or ask-question tools
