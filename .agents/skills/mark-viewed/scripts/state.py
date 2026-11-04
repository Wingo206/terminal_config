#!/usr/bin/env python3
"""Show a PR's live viewed state, what changed since the previous snapshot, or the reviewer's
own marks.

    python3 ~/.cursor/skills/mark-viewed/scripts/state.py <pr> [--only viewed|unviewed|dismissed]
    python3 ~/.cursor/skills/mark-viewed/scripts/state.py <pr> --mine
    python3 ~/.cursor/skills/mark-viewed/scripts/state.py <pr> --since-last [--interdiff]

`--mine` lists files viewed on GitHub that the agent never marked (the reviewer's seed
examples) and files the agent marked that are no longer viewed. `--since-last` compares the
two newest fetch.py snapshots, ignoring blob ids and hunk line numbers, so a rebase that
leaves a file's diff alone does not count as a change. GitHub resets a viewed file to
`dismissed` when its diff changes, so the changed list is what needs another look.
"""

from __future__ import annotations

import argparse
import difflib
import re

from pr_snapshot import (
    GhError,
    PrFile,
    PrRef,
    add_pr_arguments,
    agent_marked_paths,
    count_viewed_states,
    fetch_pr_files,
    fetch_pr_meta,
    format_file_row,
    parse_pr_ref,
    run_cli,
    snapshot_history,
)

HUNK_RANGE_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    add_pr_arguments(parser)
    parser.add_argument("--only", choices=["viewed", "unviewed", "dismissed"])
    parser.add_argument("--mine", action="store_true", help="reviewer's marks vs the agent's")
    parser.add_argument("--since-last", action="store_true", help="diff the two newest snapshots")
    parser.add_argument("--interdiff", action="store_true", help="with --since-last, show how each diff changed")
    args = parser.parse_intermixed_args()

    ref = parse_pr_ref(args.pr, args.repo)
    live = fetch_pr_files(ref)
    if args.since_last:
        print_since_last(ref, live, args.interdiff)
    if args.mine:
        print_mine(ref, live)
    if not (args.since_last or args.mine):
        print_table(live, args.only)
    return 0


def print_table(live: list[PrFile], only: str | None) -> None:
    print(f"{len(live)} files; {count_viewed_states(live)}")
    for pr_file in live:
        if only is None or pr_file.viewed_state == only.upper():
            print(format_file_row(pr_file))


def print_mine(ref: PrRef, live: list[PrFile]) -> None:
    agent_marked = agent_marked_paths(ref)
    if not agent_marked:
        print("No agent marks are recorded for this PR, so every viewed file is listed.")
    yours = [f for f in live if f.viewed_state == "VIEWED" and f.path not in agent_marked]
    lost = [f for f in live if f.path in agent_marked and f.viewed_state != "VIEWED"]
    print_section("Viewed by the reviewer, not marked by the agent", yours)
    print_section("Marked by the agent, no longer viewed", lost)


def print_since_last(ref: PrRef, live: list[PrFile], show_interdiff: bool) -> None:
    history = snapshot_history(ref)
    if not history:
        raise GhError(f"no snapshot for {ref.url}; run fetch.py first")
    latest = history[-1]
    live_head = fetch_pr_meta(ref)["headRefOid"]
    if live_head != latest.head_oid:
        print(
            f"The PR head is now {live_head[:9]}, but the newest snapshot is "
            f"{latest.head_oid[:9]}. Run fetch.py, then rerun this."
        )
        return
    if len(history) < 2:
        print(f"Only one snapshot exists ({latest.head_oid[:9]}); nothing to compare.")
        return

    previous = history[-2]
    previous_paths = {pr_file.path for pr_file in previous.files}
    latest_paths = [pr_file.path for pr_file in latest.files]
    live_by_path = {pr_file.path: pr_file for pr_file in live}
    added = [path for path in latest_paths if path not in previous_paths]
    removed = sorted(previous_paths - set(latest_paths))
    changed = [
        path
        for path in latest_paths
        if path in previous_paths
        and normalize(previous.read_chunk(path)) != normalize(latest.read_chunk(path))
    ]

    print(f"Snapshot {previous.head_oid[:9]} -> {latest.head_oid[:9]}")
    print_section("Diff changed", [live_by_path[path] for path in changed if path in live_by_path])
    print_section("New in the PR", [live_by_path[path] for path in added if path in live_by_path])
    print_paths("No longer in the PR", removed)
    unchanged_count = len(latest_paths) - len(changed) - len(added)
    print(f"\n{unchanged_count} files have the same diff as before.")
    if show_interdiff:
        for path in changed:
            print_interdiff(path, previous.read_chunk(path), latest.read_chunk(path))


def normalize(chunk: str | None) -> list[str]:
    """Chunk lines without blob ids or hunk line numbers, which shift on a plain rebase."""
    lines = (chunk or "").splitlines()
    return [HUNK_RANGE_RE.sub("@@", line) for line in lines if not line.startswith("index ")]


def print_interdiff(path: str, old_chunk: str | None, new_chunk: str | None) -> None:
    print(f"\n===== interdiff {path}")
    interdiff = difflib.unified_diff(
        normalize(old_chunk), normalize(new_chunk), "previous", "latest", lineterm="", n=1
    )
    print("\n".join(interdiff))


def print_section(title: str, files: list[PrFile]) -> None:
    print(f"\n{title} ({len(files)}):")
    for pr_file in files:
        print(f"  {format_file_row(pr_file)}")


def print_paths(title: str, paths: list[str]) -> None:
    print(f"\n{title} ({len(paths)}):")
    for path in paths:
        print(f"  {path}")


if __name__ == "__main__":
    run_cli(main)
