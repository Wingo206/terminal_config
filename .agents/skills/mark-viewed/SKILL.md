---
name: mark-viewed
description: Pre-filters a GitHub pull request by marking mechanical, deleted, or out-of-scope files as viewed via the GitHub GraphQL API so the reviewer can focus on substantive changes. Use only when explicitly invoked.
disable-model-invocation: true
---

# Mark Viewed

Mark Viewed clears mechanical and plumbing noise out of a pull request's Files tab on GitHub so the
reviewer can focus their attention on the files where design and behavior are actually decided.

## First pass: separate decision sites from consequence sites

Inspect every changed file in the PR diff before marking anything. If the reviewer pastes a PR URL
with a `#diff-<sha>` anchor and does not ask to extrapolate from that specific file, treat the hash
as a browser scroll artifact and classify the entire PR.

Ask of each file: *Once the reviewer reads the file where the new contract or feature is defined,
does this file require any separate design or behavioral judgment?* Mark a file as viewed on the
first pass when its diff is purely a downstream consequence or passive wiring:

- **Deletions, moves, and verbatim extractions:** Purely deleted files, moved or renamed files with
  no behavioral edits, functions/types/constants extracted unchanged into a new module (plus the
  source file when its diff only removes the extracted code and imports it), and interfaces or
  models that only delete a removed member.
- **Imports, barrels, and caller adaptation:** Import-path updates, barrel re-exports, consumer
  call sites, prop or port threading, and test harnesses or fixtures that only adapt to a renamed
  symbol, moved hook or provider, or updated parameter shape defined elsewhere in the PR.
- **Backwards-compatible seam and optional-parameter plumbing:** Files that only add an optional
  parameter, prop, or dependency port whose default preserves existing behavior, or controllers,
  hooks, and pages that only accept and forward an injected dependency without choosing which
  implementation is built.
- **Passive host-element wiring:** Existing UI components that only attach or remove a passive ref,
  anchor hook (such as `useTourAnchor`), `data-*` attribute, or forwarded `ref` prop on an existing
  element. Leave unviewed any component that also changes its control flow, state ownership, or DOM
  structure, or that opts a surface into a behavioral policy (such as modal-presence tracking).
- **Routine catalog, registration, and doc entries:** Boilerplate registration rows (such as
  command ID catalogs or routine analytics classification tables and their matching table tests),
  comment-only edits, README index links, and README table rows that mirror a constant or config
  defined in code. Leave unviewed ADRs and docs that specify architecture, rules, or workflows.

When in doubt on the first pass, leave the file unviewed. A tiny diff that changes a rule,
fallback, state lifecycle, or boundary contract is a decision site even if it is only a few lines
long.

## Report what was hidden and surface calibration candidates

After marking the files on GitHub, give the reviewer a clear breakdown:

- **Marked as viewed:** Group the marked files by the kind of change they made so the reviewer can
  sanity-check the batch at a glance. For moved or extracted code, name the file it came from; for
  passive wiring or catalog rows, briefly state what was wired or registered.
- **Kept unviewed despite looking similar:** Call out small, repetitive, or adjacent diffs that
  looked like plumbing on the surface but were left unviewed because they carry a behavioral,
  policy, or boundary choice. Group repeated borderline patterns clearly so the reviewer can decide
  whether to sweep them into the viewed set on a follow-up turn.
- **Substantive files remaining:** Group the remaining unviewed files by area or runtime flow so
  the reviewer has a clean map of what is left to read.

## Iterative recalibration

Filtering a large PR is often a multi-turn dialogue. As the reviewer scans the remaining files or
the borderline patterns in the report, they may paste example file paths, describe a pattern to
hide, or scope out a subsystem:

- **Seed-example or pattern extrapolation:** When the reviewer points to a few example files or
  names a pattern to filter out, identify the exact transformation those files share, sweep all
  remaining unviewed files in the PR for diffs limited to that same transformation, and mark the
  matching batch.
- **Delegated domain:** When the reviewer asks to hide a specific subsystem—such as files already
  reviewed by a teammate—mark files that belong purely to that subsystem while leaving shared
  boundary files unviewed.
- **Focused follow-up report:** On recalibration turns, report only the newly marked batch and any
  lookalikes from that pattern that were still kept unviewed because they mixed the pattern with
  another behavioral change.

## Tools

The scripts in `~/.cursor/skills/mark-viewed/scripts/` handle the GitHub plumbing: pagination past
100 files, diff splitting, batched mutations, and verification. Run them as `python3 <script>`.
Don't hand-write `markFileAsViewed` mutations or diff splitters. Each script takes a PR number or
URL; pass `--repo owner/name` with a bare number when the cwd is not that repo. Run any script with
`-h` for its full options.

- **`fetch.py <pr>`** — start here. It caches the PR at its head SHA under `/tmp/mark-viewed/` and
  prints the file table: change type, +/-, viewed state, and facts. Each file's diff lands in
  `<snapshot>/files/<path>.diff`, next to `body.md`. When the URL carries a `#diff-<sha>` anchor, it
  also prints the file the anchor points at. Facts are only what cannot be wrong: `deleted`,
  `pure-rename`, `no-diff`, and with `--same-as <ref>`, `identical-to:<ref>` or `absent-in:<ref>`.
  Use `--same-as origin/develop` for a stacked PR whose base has merged. Facts are evidence for the
  classification, not the classification itself.
- **`show.py <pr> [paths…]`** — print cached diffs. Paths may be suffixes such as
  `HomeShell.tsx`. Filters: `--max-lines N`, `--grep RE` (added and removed lines only),
  `--changed-only`, and `--unviewed`. For a pattern scan these filters can't express, such as
  import-only diffs or a rename normalized away, write a one-off script or run `rg` over the
  snapshot's `files/` directory.
- **`mark.py <pr> <paths…>`**, with `--unmark` to reverse and `--from-file` for long lists. It
  checks every path against the live PR before sending anything, then confirms the result on
  GitHub and records the agent's marks.
- **`state.py <pr>`** — live viewed state. On follow-up turns:
  - When the PR was updated, rerun `fetch.py`, then `state.py --since-last` lists files whose diff
    changed (GitHub dismisses their viewed mark), new files, and removed files. Add `--interdiff`
    to see how each changed diff moved.
  - When the reviewer marked files by hand and asks to extrapolate, `state.py --mine` lists files
    viewed on GitHub that the agent never marked. Those are the seed examples.
- **`anchor.py`** — a `#diff-<sha>` anchor to its path, or a path to a Files-tab link for the
  report.
