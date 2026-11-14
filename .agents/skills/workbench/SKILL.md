---
name: workbench
description: Organizes multi-threaded technical investigations, reorientations, self-reviews, comment triage, and audits in a living markdown workbench while keeping chat focused on working through open questions and scope decisions. Use only when explicitly invoked.
disable-model-invocation: true
---

# Workbench

Workbench organizes broad or multi-threaded technical context in a living markdown document so
parallel threads stay anchored and readable in one place while chat stays focused on open questions,
tradeoffs, and decisions.

## Synthesis builds a coherent system picture

Initial notes, diffs, stashed feedback, or review comments often point to scattered symptoms across
a codebase. Investigating the relevant code, commit history, and codebase precedents builds a
concise conceptual picture of the coherent system shape: which responsibilities belong together,
where their boundary should sit, and which invariants that boundary must preserve, keeping
incidental friction from the current composition subordinate to the architectural question.

Treat the initial threads as working hypotheses rather than a fixed outline. Preserve distinct
observations so the user can traverse them one at a time, then consolidate their shared framing and
merge or narrow threads in place when dialogue reveals that they are symptoms of the same root
cause.

## Thread anatomy and prose

Organize the workbench vertically with a short top header for sources and system overview when
helpful, followed by one section per thread:

- **Target anchor:** Start each thread with `**Target:**` listing the exact repo-root file paths and
  line ranges, such as `` `mach9-cloud/path/to/file.ts:15-24` ``, or commit and PR references when a
  thread spans a broader change.
- **Natural prose:** Because `**Target:**` already carries the code coordinates, write the thread's
  conceptual picture and any drafted outputs in plain, flowing prose as if talking directly to a
  teammate. Refer to collaborators by their role in plain English and use backticked identifiers
  only when a specific symbol or type name is itself the point of discussion.
- **In-place outcome:** Once a thread settles through dialogue, record its outcome at the bottom of
  that thread's section using `**Resolution:**` or a workflow-specific deliverable marker, keeping
  the concise conceptual notes above it intact for reference.

## Workbench and chat flow

- **First turn:** Write the per-thread conceptual pictures directly into the workbench without
  pre-baking final prescriptions, and give a brief list of the threads in chat so the user can
  choose where to start.
- **Ongoing dialogue:** Use chat to work through understanding checks, open questions, and
  tradeoffs. When an idea settles or a thread is updated in the workbench, confirm the update in a
  sentence or two in chat rather than repeating or paraphrasing the workbench text.
- **Pacing:** Let the user pace the traversal through the threads.

## Standalone workbench defaults

When `/workbench` is used directly rather than through a specialized workflow such as
`/review-dialogue`:

- **Conversational foundation:** Read and follow [Design Dialogue](../design-dialogue/SKILL.md)
  whenever the session involves open-ended design exploration, reorientation, or boundary choices.
- **Location:** When working with the Obsidian vault in `~/Research`, create the workbench in
  `~/Research/notes/agent/<slug>-workbench.md`, anchor it from its parent hub or note, and attach a
  `## Context` footer via `vault.py footer` per `/vault`. Otherwise, keep the workbench in
  `~/workbenches/<slug>.md` so repository clones stay clean across branch switches.
- **Dispositions:** Resolve each settled thread under `**Resolution:**` to the scope that fits:
  address in the current change, apply a minimal bridge now and track the deeper refactor
  separately, defer to a downstream branch or Linear issue or vault note, or close as resolved
  understanding. Consolidate settled threads into a standalone implementation plan only when the
  user asks to prepare for execution.
