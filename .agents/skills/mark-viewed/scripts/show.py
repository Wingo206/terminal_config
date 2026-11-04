#!/usr/bin/env python3
"""Print cached per-file diffs from the latest fetch.py snapshot.

    python3 ~/.cursor/skills/mark-viewed/scripts/show.py <pr> [paths...]
        [--max-lines N] [--grep RE] [--changed-only] [--unviewed]

Paths may be suffixes (`HomeShell.tsx`, `HomeShell/HomeShell.tsx`). A suffix that matches
several files shows all of them. `--max-lines` and `--grep` look at added and removed lines
only. The snapshot does not refresh itself; rerun fetch.py after the PR changes.
"""

from __future__ import annotations

import argparse
import re
import sys

from pr_snapshot import (
    PrFile,
    Snapshot,
    add_pr_arguments,
    parse_pr_ref,
    require_snapshot,
    resolve_paths,
    run_cli,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    add_pr_arguments(parser)
    parser.add_argument("paths", nargs="*", help="files to show (default: every file)")
    parser.add_argument("--max-lines", type=int, help="skip files with more changed lines")
    parser.add_argument("--grep", help="only files with an added or removed line matching RE")
    parser.add_argument("--changed-only", action="store_true", help="drop context lines")
    parser.add_argument("--unviewed", action="store_true", help="skip files viewed at fetch")
    args = parser.parse_intermixed_args()

    ref = parse_pr_ref(args.pr, args.repo)
    snapshot = require_snapshot(ref)
    selected = select_files(snapshot, args.paths, args.unviewed)
    pattern = re.compile(args.grep) if args.grep else None

    shown = 0
    for pr_file in selected:
        chunk = snapshot.read_chunk(pr_file.path)
        if chunk is None:
            continue
        header, body = split_chunk(chunk)
        changed = [line for line in body if line[:1] in "+-"]
        if args.max_lines is not None and len(changed) > args.max_lines:
            continue
        if pattern and not any(pattern.search(line[1:]) for line in changed):
            continue
        print_chunk(pr_file, header, body, args.changed_only)
        shown += 1

    head = snapshot.head_oid[:9]
    print(f"-- {shown} of {len(selected)} files shown from snapshot {head}", file=sys.stderr)
    return 0


def select_files(snapshot: Snapshot, paths: list[str], is_unviewed_only: bool) -> list[PrFile]:
    files = snapshot.files
    if paths:
        resolved, problems = resolve_paths(paths, [f.path for f in files], allow_multiple=True)
        for problem in problems:
            print(f"warning: {problem}", file=sys.stderr)
        by_path = {pr_file.path: pr_file for pr_file in files}
        files = [by_path[path] for path in resolved]
    if is_unviewed_only:
        files = [pr_file for pr_file in files if pr_file.viewed_state != "VIEWED"]
    return files


def split_chunk(chunk: str) -> tuple[list[str], list[str]]:
    """Split a `diff --git` chunk into its header lines and its hunk lines."""
    lines = chunk.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("@@"):
            return lines[:index], lines[index:]
    return lines, []


def print_chunk(pr_file: PrFile, header: list[str], body: list[str], is_changed_only: bool) -> None:
    facts = f" [{', '.join(pr_file.facts)}]" if pr_file.facts else ""
    print(
        f"===== {pr_file.path}  ({pr_file.change_type.lower()} +{pr_file.additions} "
        f"-{pr_file.deletions}, {pr_file.viewed_state.lower()}){facts}"
    )
    if is_changed_only:
        print("\n".join(line for line in body if line[:1] in "@+-"))
    else:
        print("\n".join(header[1:] + body))
    print()


if __name__ == "__main__":
    run_cli(main)
