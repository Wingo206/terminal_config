#!/usr/bin/env python3
"""Snapshot a PR for review triage and print its file table.

    python3 ~/.cursor/skills/mark-viewed/scripts/fetch.py <pr> [--repo owner/name]
        [--same-as REF [--git-dir DIR]]

Writes one diff per file to `<snapshot>/files/<path>.diff`, plus `body.md`, `meta.json`,
`diff.patch`, and `files.tsv`. Facts only state what cannot be wrong: `deleted`, `pure-rename`
(renamed with no line changes), `no-diff` (GitHub returned no patch), and with `--same-as REF`,
`identical-to:REF` (the head blob equals REF's) or `absent-in:REF` (a deleted file REF no
longer has either). Facts are inputs to the reviewer's judgment, not a verdict.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from pr_snapshot import (
    DIFF_ANCHOR_RE,
    GhError,
    PrFile,
    PrRef,
    Snapshot,
    add_pr_arguments,
    count_viewed_states,
    diff_anchor,
    fetch_pr_files,
    fetch_pr_meta,
    format_file_row,
    parse_pr_ref,
    run_cli,
    run_gh,
    snapshot_history,
    write_snapshot,
)

CHUNK_PATH_PREFIXES = ("+++ b/", "rename to ", "copy to ", "--- a/")
LS_TREE_BATCH_SIZE = 200


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    add_pr_arguments(parser)
    parser.add_argument(
        "--same-as",
        metavar="REF",
        help="tag files whose head blob matches REF in a local clone, e.g. origin/develop",
    )
    parser.add_argument("--git-dir", default=".", help="any directory inside the local clone")
    args = parser.parse_intermixed_args()

    ref = parse_pr_ref(args.pr, args.repo)
    meta = fetch_pr_meta(ref)
    files = fetch_pr_files(ref)
    diff_text = fetch_diff(ref)
    chunks = split_diff(diff_text)
    tag_facts(files, chunks)
    if args.same_as:
        tag_same_as(files, meta["headRefOid"], args.same_as, args.git_dir)

    snapshot = write_snapshot(ref, meta, files, chunks, diff_text)
    print_summary(ref, snapshot, anchored_path(args.pr, files))
    return 0


def fetch_diff(ref: PrRef) -> str:
    try:
        return run_gh(["pr", "diff", str(ref.number), "--repo", ref.repo])
    except GhError as error:
        print(
            f"warning: gh pr diff failed ({error}); falling back to REST per-file patches, "
            "which omit very large files",
            file=sys.stderr,
        )
        return rest_patches_as_diff(ref)


def rest_patches_as_diff(ref: PrRef) -> str:
    output = run_gh(
        [
            "api",
            "--paginate",
            f"repos/{ref.repo}/pulls/{ref.number}/files?per_page=100",
            "--jq",
            ".[] | {filename, previous_filename, patch} | @json",
        ]
    )
    parts = []
    for line in filter(str.strip, output.splitlines()):
        entry = json.loads(line)
        if entry.get("patch") is None:
            continue
        new_path = entry["filename"]
        old_path = entry.get("previous_filename") or new_path
        header = f"diff --git a/{old_path} b/{new_path}\n--- a/{old_path}\n+++ b/{new_path}\n"
        parts.append(header + entry["patch"] + "\n")
    return "".join(parts)


def split_diff(diff_text: str) -> dict[str, str]:
    chunks: dict[str, str] = {}
    current: list[str] = []
    for line in diff_text.splitlines(keepends=True):
        if line.startswith("diff --git ") and current:
            chunks[chunk_path(current)] = "".join(current)
            current = []
        current.append(line)
    if current and current[0].startswith("diff --git "):
        chunks[chunk_path(current)] = "".join(current)
    return chunks


def chunk_path(lines: list[str]) -> str:
    """The post-change path of one `diff --git` chunk, read from its header lines."""
    found: dict[str, str] = {}
    for line in lines[1:]:
        if line.startswith("@@"):
            break
        text = line.rstrip("\n")
        for prefix in CHUNK_PATH_PREFIXES:
            if text.startswith(prefix):
                found.setdefault(prefix, _unquote(text[len(prefix) :]))
    for prefix in CHUNK_PATH_PREFIXES:
        if prefix in found:
            return found[prefix]
    return _unquote(lines[0].rstrip("\n").rsplit(" b/", 1)[-1])


def _unquote(path: str) -> str:
    return path[1:-1] if len(path) > 1 and path[0] == path[-1] == '"' else path


def tag_facts(files: list[PrFile], chunks: dict[str, str]) -> None:
    for pr_file in files:
        if pr_file.change_type == "DELETED":
            pr_file.facts.append("deleted")
        is_unchanged = pr_file.additions == 0 and pr_file.deletions == 0
        if pr_file.change_type == "RENAMED" and is_unchanged:
            pr_file.facts.append("pure-rename")
        if pr_file.path not in chunks:
            pr_file.facts.append("no-diff")


def tag_same_as(files: list[PrFile], head_oid: str, ref_name: str, git_dir: str) -> None:
    root = run_git(git_dir, ["rev-parse", "--show-toplevel"]).strip()
    ensure_commit(root, head_oid)
    paths = [pr_file.path for pr_file in files]
    head_blobs = blob_ids(root, head_oid, paths)
    ref_blobs = blob_ids(root, ref_name, paths)
    for pr_file in files:
        ref_blob = ref_blobs.get(pr_file.path)
        if pr_file.change_type == "DELETED":
            if ref_blob is None:
                pr_file.facts.append(f"absent-in:{ref_name}")
        elif ref_blob is not None and ref_blob == head_blobs.get(pr_file.path):
            pr_file.facts.append(f"identical-to:{ref_name}")


def run_git(cwd: str, args: list[str]) -> str:
    command = ["git", "--literal-pathspecs", "-C", cwd, *args]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise GhError(result.stderr.strip() or f"git {args[0]} failed")
    return result.stdout


def ensure_commit(root: str, oid: str) -> None:
    try:
        run_git(root, ["cat-file", "-e", f"{oid}^{{commit}}"])
    except GhError:
        run_git(root, ["fetch", "--quiet", "origin", oid])


def blob_ids(root: str, rev: str, paths: list[str]) -> dict[str, str]:
    blobs: dict[str, str] = {}
    for start in range(0, len(paths), LS_TREE_BATCH_SIZE):
        batch = paths[start : start + LS_TREE_BATCH_SIZE]
        output = run_git(root, ["ls-tree", "-r", "-z", rev, "--", *batch])
        for entry in filter(None, output.split("\0")):
            info, path = entry.split("\t", 1)
            blobs[path] = info.split()[2]
    return blobs


def anchored_path(pr_text: str, files: list[PrFile]) -> str | None:
    match = DIFF_ANCHOR_RE.search(pr_text)
    if not match:
        return None
    by_anchor = {diff_anchor(pr_file.path): pr_file.path for pr_file in files}
    return by_anchor.get(match.group(1), f"no file in this PR (diff-{match.group(1)[:12]}…)")


def print_summary(ref: PrRef, snapshot: Snapshot, anchor_target: str | None) -> None:
    meta, files = snapshot.meta, snapshot.files
    print(f"{ref.repo}#{ref.number}: {meta['title']}")
    print(f"  {meta['url']}")
    print(
        f"  base {meta['baseRefName']} @ {meta['baseRefOid'][:9]}, "
        f"head {meta['headRefName']} @ {meta['headRefOid'][:9]}"
    )
    print(f"  node id {meta['id']}")
    print(
        f"  {len(files)} files, +{meta['additions']} -{meta['deletions']}; "
        f"{count_viewed_states(files)}"
    )
    if len(files) != meta["changedFiles"]:
        print(f"  warning: GitHub reports {meta['changedFiles']} changed files")
    if anchor_target:
        print(f"  link anchor points at {anchor_target}")
    print(f"  snapshot {snapshot.directory}  (files/<path>.diff, body.md, files.tsv)")
    history = snapshot_history(ref)
    if len(history) > 1:
        previous_head = history[-2].head_oid[:9]
        print(f"  previous snapshot at {previous_head}: state.py --since-last shows what changed")
    print()
    for pr_file in files:
        print(format_file_row(pr_file))


if __name__ == "__main__":
    run_cli(main)
