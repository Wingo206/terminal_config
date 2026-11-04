#!/usr/bin/env python3
"""Mark (or unmark) PR files as viewed, then confirm the result on GitHub.

    python3 ~/.cursor/skills/mark-viewed/scripts/mark.py <pr> [paths...] [--from-file F] [--unmark]

The only writes this script makes are `markFileAsViewed` and `unmarkFileAsViewed`. Paths may be
unique suffixes of PR paths. Every path is checked against the live PR before anything is
sent, so a typo marks nothing. Files that land are appended to the agent's mark log, which
`state.py --mine` uses to tell the reviewer's own marks apart from the agent's.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pr_snapshot import (
    GhError,
    PrFile,
    add_pr_arguments,
    fetch_pr_files,
    fetch_pr_meta,
    graphql,
    latest_snapshot,
    parse_pr_ref,
    record_marks,
    resolve_paths,
    run_cli,
    save_files,
)

BATCH_SIZE = 10


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    add_pr_arguments(parser)
    parser.add_argument("paths", nargs="*", help="files to mark")
    parser.add_argument("--from-file", help="read more paths, one per line ('-' for stdin)")
    parser.add_argument("--unmark", action="store_true", help="unmark instead of mark")
    args = parser.parse_intermixed_args()

    ref = parse_pr_ref(args.pr, args.repo)
    requested = args.paths + read_path_list(args.from_file)
    if not requested:
        raise GhError("no paths given")
    meta = fetch_pr_meta(ref)
    live_paths = [pr_file.path for pr_file in fetch_pr_files(ref)]
    paths, problems = resolve_paths(requested, live_paths, allow_multiple=False)
    if problems:
        raise GhError("nothing sent:\n  " + "\n  ".join(problems))

    mutation = "unmarkFileAsViewed" if args.unmark else "markFileAsViewed"
    failures = send_mutations(meta["id"], mutation, paths)
    after = {pr_file.path: pr_file for pr_file in fetch_pr_files(ref)}
    not_landed = [path for path in paths if not has_landed(after[path], args.unmark)]
    landed = [path for path in paths if path not in not_landed]

    record_marks(ref, meta["headRefOid"], "unmark" if args.unmark else "mark", landed)
    refresh_snapshot_states(ref, meta["headRefOid"], after)
    report(args.unmark, ref.url, paths, landed, failures, not_landed)
    return 1 if not_landed else 0


def read_path_list(source: str | None) -> list[str]:
    if source is None:
        return []
    text = sys.stdin.read() if source == "-" else Path(source).read_text()
    return [line.strip() for line in text.splitlines() if line.strip()]


def send_mutations(pull_request_id: str, mutation: str, paths: list[str]) -> dict[str, str]:
    """Send aliased mutations in batches; return an error message per failed path."""
    failures: dict[str, str] = {}
    for start in range(0, len(paths), BATCH_SIZE):
        batch = paths[start : start + BATCH_SIZE]
        declarations = ", ".join(["$pr: ID!"] + [f"$p{i}: String!" for i in range(len(batch))])
        fields = "\n".join(
            f"  f{i}: {mutation}(input: {{pullRequestId: $pr, path: $p{i}}}) {{ clientMutationId }}"
            for i in range(len(batch))
        )
        variables = {"pr": pull_request_id, **{f"p{i}": path for i, path in enumerate(batch)}}
        try:
            response = graphql(f"mutation({declarations}) {{\n{fields}\n}}", variables, True)
        except GhError as error:
            failures.update({path: str(error) for path in batch})
            continue
        failures.update(batch_failures(batch, response.get("errors") or []))
    return failures


def batch_failures(batch: list[str], errors: list[dict]) -> dict[str, str]:
    failures: dict[str, str] = {}
    for error in errors:
        alias = (error.get("path") or [""])[0]
        message = error.get("message", str(error))
        if alias.startswith("f") and alias[1:].isdigit():
            failures[batch[int(alias[1:])]] = message
        else:
            failures.update({path: message for path in batch})
    return failures


def has_landed(pr_file: PrFile, is_unmark: bool) -> bool:
    is_viewed = pr_file.viewed_state == "VIEWED"
    return not is_viewed if is_unmark else is_viewed


def refresh_snapshot_states(ref, head_oid: str, after: dict[str, PrFile]) -> None:
    snapshot = latest_snapshot(ref)
    if snapshot is None or snapshot.head_oid != head_oid:
        return
    for pr_file in snapshot.files:
        if pr_file.path in after:
            pr_file.viewed_state = after[pr_file.path].viewed_state
    save_files(snapshot)


def report(
    is_unmark: bool,
    url: str,
    paths: list[str],
    landed: list[str],
    failures: dict[str, str],
    not_landed: list[str],
) -> None:
    verb = "Unmarked" if is_unmark else "Marked"
    print(f"{verb} {len(landed)} of {len(paths)} files on {url}")
    for path in not_landed:
        reason = failures.get(path, "GitHub shows no change")
        print(f"  not landed: {path} ({reason})")


if __name__ == "__main__":
    run_cli(main)
