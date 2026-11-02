---
name: mark-viewed
description: Pre-filters a GitHub pull request by marking mechanical, deleted, or out-of-scope files as viewed via the GitHub GraphQL API so the reviewer can focus on substantive changes. Use only when explicitly invoked.
disable-model-invocation: true
---

# Mark Viewed

Mark Viewed clears mechanical noise out of a pull request's Files tab on GitHub so the reviewer can
focus their attention on the files where design and behavior actually change.

## Classify by behavioral substance, not line count

Inspect every changed file in the PR diff before marking anything. A file belongs in the viewed set
only when its diff is purely mechanical or explicitly out of scope for the reviewer's pass:

- **Default mechanical changes:**
  - Purely deleted files, or moved and renamed files with no behavioral edits.
  - Import-path updates and barrel re-export adjustments.
  - Consumer call sites, prop threading, and test harnesses that only adapt to a renamed symbol,
    moved hook or provider, or updated parameter shape defined elsewhere in the PR.
- **Seed-example extrapolation:** When the reviewer points to a few example files, identify the
  exact transformation those files share and find the remaining files in the PR whose diffs are
  limited to that same transformation.
- **Delegated domain:** When the reviewer asks to hide a specific subsystem—such as files already
  reviewed by a teammate—mark files that belong purely to that subsystem while leaving shared
  boundary files unviewed.

When in doubt, leave the file unviewed. A tiny diff that changes a rule, fallback, state lifecycle,
or boundary contract is substantive even if it is only a few lines long.

## Report what was hidden and what remains

After marking the files on GitHub, give the reviewer a clear breakdown:

- **Marked as viewed:** Group the marked files by the kind of mechanical change they made so the
  reviewer can sanity-check the batch at a glance.
- **Kept unviewed despite looking similar:** Call out any small or adjacent diffs that looked like
  mechanical updates on the surface but were left unviewed because they carry a real behavioral or
  boundary change.
- **Substantive files remaining:** Group the remaining unviewed files by area or runtime flow so
  the reviewer has a clean map of what is left to read.

## Execution mechanics

- Fetch the PR node ID and full diff using `gh pr view <num> --json id` and `gh pr diff <num>`.
  Rely on `gh pr diff` or paginated GraphQL rather than `gh pr view --json files` alone, which caps
  at 100 files on large PRs.
- Mark files as viewed using GitHub's `markFileAsViewed` GraphQL mutation with aliased fields,
  batching 8–10 files per `gh api graphql` call so GitHub does not time out on large transactions:

```bash
gh api graphql -f query='
mutation {
  f1: markFileAsViewed(input: { pullRequestId: "PR_...", path: "path/to/fileA.ts" }) { clientMutationId }
  f2: markFileAsViewed(input: { pullRequestId: "PR_...", path: "path/to/fileB.ts" }) { clientMutationId }
}'
```
