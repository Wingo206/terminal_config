"""Shared plumbing for the mark-viewed scripts.

Covers `gh` calls, PR resolution, the paginated PR file query, and the snapshot cache at
`/tmp/mark-viewed/<owner>/<name>/<number>/` (override the root with `MARK_VIEWED_CACHE`).
Each fetched head SHA gets its own snapshot directory. `heads.txt` orders the snapshots, and
`marked.txt` logs every file the agent marked or unmarked, across heads.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

CACHE_ROOT = Path(os.environ.get("MARK_VIEWED_CACHE", "/tmp/mark-viewed"))
PR_URL_RE = re.compile(r"github\.com/([^/\s]+)/([^/\s#?]+)/pull/(\d+)")
DIFF_ANCHOR_RE = re.compile(r"diff-([0-9a-f]{64})")

PR_META_QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      id url title body changedFiles additions deletions
      baseRefName headRefName baseRefOid headRefOid
    }
  }
}
"""

PR_FILES_QUERY = """
query($owner: String!, $name: String!, $number: Int!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      files(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes { path additions deletions changeType viewerViewedState }
      }
    }
  }
}
"""


class GhError(RuntimeError):
    """A `gh` or `git` call failed, or the PR could not be resolved."""


@dataclass(frozen=True)
class PrRef:
    owner: str
    name: str
    number: int

    @property
    def repo(self) -> str:
        return f"{self.owner}/{self.name}"

    @property
    def url(self) -> str:
        return f"https://github.com/{self.repo}/pull/{self.number}"


@dataclass
class PrFile:
    path: str
    change_type: str
    additions: int
    deletions: int
    viewed_state: str
    facts: list[str] = field(default_factory=list)


@dataclass
class Snapshot:
    directory: Path
    meta: dict
    files: list[PrFile]

    @property
    def head_oid(self) -> str:
        return self.meta["headRefOid"]

    def chunk_path(self, path: str) -> Path:
        return self.directory / "files" / f"{path}.diff"

    def read_chunk(self, path: str) -> str | None:
        chunk_file = self.chunk_path(path)
        return chunk_file.read_text() if chunk_file.exists() else None


# --- CLI ---------------------------------------------------------------------------------


def add_pr_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("pr", help="PR number or URL")
    parser.add_argument(
        "--repo",
        help="owner/name when the PR is a bare number (default: the repo in the cwd)",
    )


def run_cli(main: Callable[[], int]) -> None:
    try:
        sys.exit(main())
    except GhError as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)


def parse_pr_ref(text: str, repo: str | None = None) -> PrRef:
    match = PR_URL_RE.search(text)
    if match:
        return PrRef(match.group(1), match.group(2), int(match.group(3)))
    number = text.lstrip("#")
    if not number.isdigit():
        raise GhError(f"not a PR number or URL: {text}")
    repo = repo or run_gh(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"])
    owner, _separator, name = repo.strip().partition("/")
    return PrRef(owner, name, int(number))


def resolve_paths(
    requested: list[str], known: list[str], allow_multiple: bool
) -> tuple[list[str], list[str]]:
    """Match each requested path exactly, or as a `/`-bounded suffix of a PR path."""
    known_set = set(known)
    resolved: list[str] = []
    problems: list[str] = []
    for item in (raw.strip() for raw in requested):
        if not item:
            continue
        if item in known_set:
            resolved.append(item)
            continue
        suffix = "/" + item.lstrip("/")
        matches = [path for path in known if path.endswith(suffix)]
        if len(matches) == 1 or (matches and allow_multiple):
            resolved.extend(matches)
        elif matches:
            problems.append(f"{item} is ambiguous: {', '.join(matches)}")
        else:
            problems.append(f"{item} is not a file in this PR")
    return list(dict.fromkeys(resolved)), problems


def format_file_row(pr_file: PrFile) -> str:
    facts = f"  [{', '.join(pr_file.facts)}]" if pr_file.facts else ""
    return (
        f"{pr_file.change_type.lower():<8} +{pr_file.additions:<5} -{pr_file.deletions:<5} "
        f"{pr_file.viewed_state.lower():<9} {pr_file.path}{facts}"
    )


def count_viewed_states(files: list[PrFile]) -> str:
    counts = {"VIEWED": 0, "DISMISSED": 0, "UNVIEWED": 0}
    for pr_file in files:
        counts[pr_file.viewed_state] = counts.get(pr_file.viewed_state, 0) + 1
    return ", ".join(f"{state.lower()} {count}" for state, count in counts.items())


def diff_anchor(path: str) -> str:
    """GitHub's Files-tab anchor id for a path: `diff-<sha256(path)>`."""
    return hashlib.sha256(path.encode()).hexdigest()


# --- gh ----------------------------------------------------------------------------------


def run_gh(args: list[str]) -> str:
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise GhError(result.stderr.strip() or result.stdout.strip() or f"gh {args[0]} failed")
    return result.stdout


def graphql(query: str, variables: dict | None = None, allow_errors: bool = False) -> dict:
    """Run a GraphQL document. With `allow_errors`, return partial data alongside `errors`."""
    args = ["api", "graphql", "-f", f"query={query}"]
    for key, value in (variables or {}).items():
        flag = "-F" if isinstance(value, int) else "-f"
        args += [flag, f"{key}={value}"]
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise GhError(result.stderr.strip() or "gh api graphql returned no JSON") from None
    errors = response.get("errors")
    if errors and not allow_errors:
        raise GhError("; ".join(error.get("message", str(error)) for error in errors))
    return response


def fetch_pr_meta(ref: PrRef) -> dict:
    variables = {"owner": ref.owner, "name": ref.name, "number": ref.number}
    pull_request = graphql(PR_META_QUERY, variables)["data"]["repository"]["pullRequest"]
    if pull_request is None:
        raise GhError(f"no pull request at {ref.url}")
    return pull_request


def fetch_pr_files(ref: PrRef) -> list[PrFile]:
    variables: dict = {"owner": ref.owner, "name": ref.name, "number": ref.number}
    files: list[PrFile] = []
    while True:
        response = graphql(PR_FILES_QUERY, variables)
        page = response["data"]["repository"]["pullRequest"]["files"]
        files += [
            PrFile(
                path=node["path"],
                change_type=node["changeType"],
                additions=node["additions"],
                deletions=node["deletions"],
                viewed_state=node["viewerViewedState"],
            )
            for node in page["nodes"]
        ]
        if not page["pageInfo"]["hasNextPage"]:
            return files
        variables["cursor"] = page["pageInfo"]["endCursor"]


# --- Snapshots ---------------------------------------------------------------------------


def pr_cache_dir(ref: PrRef) -> Path:
    return CACHE_ROOT / ref.owner / ref.name / str(ref.number)


def write_snapshot(
    ref: PrRef, meta: dict, files: list[PrFile], chunks: dict[str, str], diff_text: str
) -> Snapshot:
    directory = pr_cache_dir(ref) / meta["headRefOid"]
    files_dir = directory / "files"
    if files_dir.exists():
        shutil.rmtree(files_dir)
    for path, chunk in chunks.items():
        chunk_file = files_dir / f"{path}.diff"
        chunk_file.parent.mkdir(parents=True, exist_ok=True)
        chunk_file.write_text(chunk)
    stored_meta = {key: value for key, value in meta.items() if key != "body"}
    (directory / "meta.json").write_text(json.dumps(stored_meta, indent=2) + "\n")
    (directory / "body.md").write_text(meta.get("body") or "")
    (directory / "diff.patch").write_text(diff_text)
    snapshot = Snapshot(directory, stored_meta, files)
    save_files(snapshot)
    _record_head(ref, snapshot.head_oid)
    return snapshot


def save_files(snapshot: Snapshot) -> None:
    files_json = json.dumps([asdict(pr_file) for pr_file in snapshot.files], indent=1)
    (snapshot.directory / "files.json").write_text(files_json + "\n")
    rows = "\n".join(format_file_row(pr_file) for pr_file in snapshot.files)
    (snapshot.directory / "files.tsv").write_text(rows + "\n")


def load_snapshot(directory: Path) -> Snapshot:
    meta = json.loads((directory / "meta.json").read_text())
    raw_files = json.loads((directory / "files.json").read_text())
    return Snapshot(directory, meta, [PrFile(**raw) for raw in raw_files])


def snapshot_history(ref: PrRef) -> list[Snapshot]:
    heads_file = pr_cache_dir(ref) / "heads.txt"
    if not heads_file.exists():
        return []
    directories = [pr_cache_dir(ref) / head for head in heads_file.read_text().split()]
    return [load_snapshot(directory) for directory in directories if directory.exists()]


def latest_snapshot(ref: PrRef) -> Snapshot | None:
    history = snapshot_history(ref)
    return history[-1] if history else None


def require_snapshot(ref: PrRef) -> Snapshot:
    snapshot = latest_snapshot(ref)
    if snapshot is None:
        raise GhError(f"no snapshot for {ref.url}; run fetch.py first")
    return snapshot


def _record_head(ref: PrRef, head_oid: str) -> None:
    heads_file = pr_cache_dir(ref) / "heads.txt"
    heads = heads_file.read_text().split() if heads_file.exists() else []
    if head_oid in heads:
        heads.remove(head_oid)
    heads.append(head_oid)
    heads_file.write_text("\n".join(heads) + "\n")


# --- Agent mark log ----------------------------------------------------------------------


def record_marks(ref: PrRef, head_oid: str, action: str, paths: list[str]) -> None:
    log_file = pr_cache_dir(ref) / "marked.txt"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a") as log:
        for path in paths:
            log.write(f"{action}\t{head_oid}\t{path}\n")


def agent_marked_paths(ref: PrRef) -> set[str]:
    """Paths the agent currently has marked, replaying `marked.txt` in order."""
    log_file = pr_cache_dir(ref) / "marked.txt"
    marked: set[str] = set()
    if not log_file.exists():
        return marked
    for line in log_file.read_text().splitlines():
        action, _head, path = line.split("\t", 2)
        if action == "mark":
            marked.add(path)
        else:
            marked.discard(path)
    return marked
