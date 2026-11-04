#!/usr/bin/env python3
"""Translate between GitHub Files-tab anchors and PR paths.

    python3 ~/.cursor/skills/mark-viewed/scripts/anchor.py <pr-url-with-#diff-...>
    python3 ~/.cursor/skills/mark-viewed/scripts/anchor.py <pr> <diff-sha | path>...

An anchor (`#diff-<sha256 of the path>`) prints the path it points at. A path, or a unique
suffix of one, prints a link that opens the Files tab on that file. Uses the latest snapshot
when one exists, otherwise the live file list.
"""

from __future__ import annotations

import argparse
import re

from pr_snapshot import (
    DIFF_ANCHOR_RE,
    add_pr_arguments,
    diff_anchor,
    fetch_pr_files,
    latest_snapshot,
    parse_pr_ref,
    resolve_paths,
    run_cli,
)

BARE_SHA_RE = re.compile(r"^(?:diff-)?([0-9a-f]{64})$")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    add_pr_arguments(parser)
    parser.add_argument("targets", nargs="*", help="anchors or paths (default: the PR URL's anchor)")
    args = parser.parse_intermixed_args()

    ref = parse_pr_ref(args.pr, args.repo)
    snapshot = latest_snapshot(ref)
    files = snapshot.files if snapshot else fetch_pr_files(ref)
    paths = [pr_file.path for pr_file in files]
    by_anchor = {diff_anchor(path): path for path in paths}

    exit_code = 0
    for target in args.targets or [args.pr]:
        anchor = anchor_in(target)
        if anchor:
            print(f"diff-{anchor[:12]}…\t{by_anchor.get(anchor, 'no file in this PR')}")
            exit_code |= anchor not in by_anchor
            continue
        resolved, problems = resolve_paths([target], paths, allow_multiple=True)
        for problem in problems:
            print(f"{target}\t{problem}")
            exit_code = 1
        for path in resolved:
            print(f"{path}\t{ref.url}/changes#diff-{diff_anchor(path)}")
    return exit_code


def anchor_in(target: str) -> str | None:
    match = BARE_SHA_RE.match(target) or DIFF_ANCHOR_RE.search(target)
    return match.group(1) if match else None


if __name__ == "__main__":
    run_cli(main)
