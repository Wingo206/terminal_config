#!/usr/bin/env python3
"""Composable CLI for the lifecycle of a review-dialogue workbench in ~/pr-reviews/.

A workbench lives at ~/pr-reviews/pr-<number>-review.md from the first turn (`init`, status: active)
through completion (`post` / `done`, status: done). Its YAML frontmatter (pr, repo, title, author,
date, status, posted_comments, chat_id, skill_version) is kept in sync with the header block.

Steps (can be run individually; `publish` runs check -> post -> done):
    python3 ~/.cursor/skills/review-dialogue/publish-review.py init <pr-number-or-url> [--transcript <path>]
    python3 ~/.cursor/skills/review-dialogue/publish-review.py check <workbench>
    python3 ~/.cursor/skills/review-dialogue/publish-review.py post <workbench>
    python3 ~/.cursor/skills/review-dialogue/publish-review.py done <workbench> [--transcript <path>]
    python3 ~/.cursor/skills/review-dialogue/publish-review.py [publish] <workbench> [--transcript <path>]

<workbench> is a path, or `pr-2920-review.md` / `2920` / a PR URL, which resolve to
~/pr-reviews/pr-<number>-review.md when no such file exists in the current directory.
`archive` is an alias for `done`.
"""

from __future__ import annotations

import argparse
import bisect
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date

REVIEWS_DIR = Path.home() / "pr-reviews"
DEFAULT_OWNER, DEFAULT_REPO = "mach9robotics", "bagel"
FRONTMATTER_KEYS = (
    "pr",
    "repo",
    "title",
    "author",
    "date",
    "status",
    "posted_comments",
    "chat_id",
    "skill_version",
)

PR_URL_RE = re.compile(r"https://github\.com/([^/\s]+)/([^/\s#)]+)/pull/(\d+)")
PR_FILENAME_RE = re.compile(r"pr-(\d+)")
PR_REF_RE = re.compile(r"(?:([\w.-]+)/([\w.-]+))?#?(\d+)")
UUID_RE = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", re.IGNORECASE)
PLAIN_SCALAR_RE = re.compile(r"[A-Za-z][\w./-]*|\d{4}-\d{2}-\d{2}|\d+")
POSTED_MARKER_RE = re.compile(r"^(?:-\s*)?\*\*Posted\s+(?:comment|review summary)\b", re.IGNORECASE)
POSTED_LABEL_RE = re.compile(r"^(\s*)([-*]\s+)?(?:\*\*)?(?:Posted|Published)\b[^:]*:", re.IGNORECASE)
GITHUB_LINK_RE = re.compile(r"https://github\.com/[^\s)\]>]+")

HEADING_RE = re.compile(r"^(#{2,3})\s+(.+?)\s*$")
TARGET_HEADER_RE = re.compile(r"^(?:-\s*)?\*\*Targets?:?\*\*\s*(.*)$", re.IGNORECASE)
DRAFT_COMMENT_RE = re.compile(
    r"^(?:-\s*)?\*\*Draft\s+(?:inline\s+)?comment(?:\s*\(([^)]*)\))?\s*:?\*\*\s*(.*)$",
    re.IGNORECASE,
)
DRAFT_SUMMARY_RE = re.compile(
    r"^(?:-\s*)?\*\*Draft\s+(?:overall\s+)?(?:review\s+)?summary(?:\s*\(([^)]*)\))?\s*:?\*\*\s*(.*)$",
    re.IGNORECASE,
)
STOP_MARKER_RE = re.compile(
    r"^(?:---+\s*|"
    r"#{1,6}\s+|"
    r"(?:-\s*)?\*\*(?:Resolution|Working disposition|Targets?|Draft\b|Posted\b|"
    r"Personal follow-up|Linear issue|Implementation sketch|Follow-up|Evidence|Questions)\b[^*]*\*\*)",
    re.IGNORECASE,
)

BACKTICK_TARGET_RE = re.compile(
    r"`([^`\s:]+\.[a-zA-Z0-9_]+)(?::(\d+)(?:[-–](\d+))?)?`"
    r"(?:\s*\(lines?\s*(\d+)(?:[-–](\d+))?[^)]*\))?"
)
HUNK_HEADER_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


@dataclass(frozen=True)
class TargetSpec:
    raw_path: str
    start_line: int | None
    end_line: int | None


@dataclass
class DraftComment:
    section_title: str
    marker_line_index: int
    body: str
    targets: list[TargetSpec]
    resolved_path: str = ""
    resolved_start_line: int | None = None
    resolved_line: int = 1
    snap_note: str | None = None
    posted_url: str | None = None


@dataclass
class DraftSummary:
    section_title: str
    marker_line_index: int
    body: str
    posted_url: str | None = None


@dataclass
class ParsedWorkbench:
    owner: str
    repo: str
    pr_number: int
    lines: list[str]
    """Every line of the file, frontmatter included, so marker indices address the file directly."""
    summary: DraftSummary | None
    comments: list[DraftComment]
    frontmatter: dict[str, str] = field(default_factory=dict)


@dataclass
class PrFileDiff:
    filename: str
    status: str
    hunks: list[tuple[int, int]]
    changed_lines: list[int]


@dataclass
class PrContext:
    pr_id: str
    head_oid: str
    viewer_login: str
    pending_review: dict | None
    files: dict[str, PrFileDiff]


def run_gh_json(args: list[str], input_data: dict | None = None) -> dict | list:
    cmd = ["gh", *args]
    stdin_str = json.dumps(input_data) if input_data is not None else None
    result = subprocess.run(
        cmd,
        input=stdin_str,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed (`{' '.join(cmd)}`): {result.stderr.strip() or result.stdout.strip()}"
        )
    return json.loads(result.stdout) if result.stdout.strip() else {}


def extract_targets_from_text(text: str) -> list[TargetSpec]:
    targets: list[TargetSpec] = []
    for match in BACKTICK_TARGET_RE.finditer(text):
        raw_path = match.group(1).strip()
        if "/" not in raw_path and not raw_path.endswith(
            (".ts", ".tsx", ".py", ".md", ".js", ".json")
        ):
            continue
        colon_start = match.group(2)
        colon_end = match.group(3)
        paren_start = match.group(4)
        paren_end = match.group(5)

        if colon_start is not None:
            start = int(colon_start)
            end = int(colon_end) if colon_end is not None else start
        elif paren_start is not None:
            start = int(paren_start)
            end = int(paren_end) if paren_end is not None else start
        else:
            start = None
            end = None

        targets.append(TargetSpec(raw_path=raw_path, start_line=start, end_line=end))
    return targets


def clean_draft_body(raw_lines: list[str]) -> str:
    lines = list(raw_lines)
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""

    non_empty = [line for line in lines if line.strip()]
    if non_empty and all(line.lstrip().startswith(">") for line in non_empty):
        stripped: list[str] = []
        for line in lines:
            s = line.lstrip()
            if s.startswith("> "):
                stripped.append(s[2:])
            elif s.startswith(">"):
                stripped.append(s[1:])
            else:
                stripped.append(line)
        lines = stripped

    return "\n".join(lines).strip()


def clean_section_title(raw_title: str) -> str:
    return re.sub(r"^(?:Round\s+\d+:\s*|[A-Z]?\d+\.\s*)", "", raw_title).strip()


def frontmatter_end(lines: list[str]) -> int:
    """Index of the first line after a leading `---` YAML block, or 0 when there is none."""
    if not lines or lines[0].strip() != "---":
        return 0
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return index + 1
    return 0


def read_frontmatter(lines: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in lines[1 : max(1, frontmatter_end(lines) - 1)]:
        key, sep, value = line.partition(":")
        if sep and key.strip() and not key[:1].isspace():
            fields[key.strip()] = parse_scalar(value.strip())
    return fields


def parse_scalar(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] == '"':
        try:
            return str(json.loads(value))
        except ValueError:
            return value[1:-1]
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return value.partition(" #")[0].strip()


def format_scalar(value: object) -> str:
    text = str(value)
    return text if PLAIN_SCALAR_RE.fullmatch(text) or UUID_RE.fullmatch(text) else json.dumps(text, ensure_ascii=False)


def upsert_frontmatter(
    lines: list[str],
    updates: dict[str, object | None],
    keep_existing: frozenset[str] = frozenset(),
) -> list[str]:
    """`lines` with frontmatter fields set from `updates`, creating the block when missing.

    `None` values are skipped, keys in `keep_existing` are only filled in when absent, and every
    other existing field keeps its line and position.
    """
    end = frontmatter_end(lines)
    block = list(lines[1 : end - 1]) if end else []
    existing = read_frontmatter(lines)
    ordered = [key for key in FRONTMATTER_KEYS if key in updates] + [k for k in updates if k not in FRONTMATTER_KEYS]
    for key in ordered:
        value = updates[key]
        if value is None or value == "" or (key in keep_existing and existing.get(key)):
            continue
        rendered = f"{key}: {format_scalar(value)}"
        position = next((i for i, line in enumerate(block) if line.partition(":")[0].strip() == key), None)
        if position is None:
            block.append(rendered)
        else:
            block[position] = rendered
    return ["---", *block, "---", *lines[end:]]


def count_posted_comments(lines: list[str]) -> int:
    """Posted comments recorded in a workbench.

    The larger of the in-place `**Posted comment ...**` / `**Posted review summary ...**` markers and
    the GitHub links listed under `Posted comments:` / `Published comments:` / `Posted to PR #N:`
    labels, since older workbenches only kept the header list.
    """
    markers = sum(1 for line in lines if POSTED_MARKER_RE.match(line.strip()))
    listed = 0
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        label = POSTED_LABEL_RE.match(line)
        if not label or POSTED_MARKER_RE.match(line.strip()):
            continue
        base_indent, is_bulleted = len(label.group(1)), bool(label.group(2))
        if not is_bulleted and index < len(lines) and not lines[index].strip():
            index += 1
        while index < len(lines) and lines[index].strip():
            item = lines[index]
            indent = len(item) - len(item.lstrip())
            if indent <= base_indent and (is_bulleted or not item.lstrip().startswith(("- ", "* "))):
                break
            listed += len(GITHUB_LINK_RE.findall(item))
            index += 1
    return max(markers, listed)


def header_bounds(lines: list[str]) -> tuple[int, int]:
    """[start, end) of the header block: after the frontmatter, up to the first `## ` or `---`."""
    start = frontmatter_end(lines)
    end = next(
        (i for i in range(start, len(lines)) if lines[i].startswith("## ") or re.match(r"^---+\s*$", lines[i])),
        len(lines),
    )
    return start, end


def is_in_reviews_dir(path: Path) -> bool:
    return REVIEWS_DIR.exists() and path.resolve().parent == REVIEWS_DIR.resolve()


def resolve_workbench_path(raw: str) -> Path:
    """`raw` if it exists, else ~/pr-reviews/pr-<number>-review.md for a number, PR URL, or filename."""
    candidate = Path(raw).expanduser()
    if candidate.exists():
        return candidate.absolute()
    url = PR_URL_RE.search(raw)
    ref = re.fullmatch(r"#?(\d+)", raw.strip())
    number = url.group(3) if url else ref.group(1) if ref else None
    if number:
        return REVIEWS_DIR / f"pr-{number}-review.md"
    return REVIEWS_DIR / candidate.name


def parse_workbench(path: Path) -> ParsedWorkbench:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    fields = read_frontmatter(lines)
    body_start = frontmatter_end(lines)

    url_match = PR_URL_RE.search("\n".join(lines[body_start:]))
    fn_match = PR_FILENAME_RE.search(path.name)
    if fields.get("pr", "").isdigit():
        owner, _, repo = (fields.get("repo") or f"{DEFAULT_OWNER}/{DEFAULT_REPO}").partition("/")
        pr_number = int(fields["pr"])
    elif url_match:
        owner, repo, pr_num_str = url_match.group(1), url_match.group(2), url_match.group(3)
        pr_number = int(pr_num_str)
    elif fn_match:
        owner, repo, pr_number = DEFAULT_OWNER, DEFAULT_REPO, int(fn_match.group(1))
    else:
        raise ValueError(
            f"Could not find a PR in the frontmatter of {path}, a GitHub PR URL, or a PR number in {path.name}."
        )

    current_heading = "General"
    current_targets: list[TargetSpec] = []
    in_target_block = False

    summary: DraftSummary | None = None
    comments: list[DraftComment] = []

    index = body_start
    while index < len(lines):
        line = lines[index]

        heading_match = HEADING_RE.match(line)
        if heading_match:
            hashes, title_text = heading_match.group(1), heading_match.group(2)
            if len(hashes) == 2:
                current_heading = clean_section_title(title_text)
                current_targets = []
            elif not current_targets:
                current_heading = clean_section_title(title_text)
            in_target_block = False
            index += 1
            continue

        target_match = TARGET_HEADER_RE.match(line)
        if target_match:
            in_target_block = True
            current_targets.extend(extract_targets_from_text(target_match.group(1)))
            index += 1
            continue

        if in_target_block:
            if not line.strip():
                if current_targets:
                    in_target_block = False
                index += 1
                continue
            if line.lstrip().startswith(("-", "*")) or line.lstrip().startswith("`"):
                extracted = extract_targets_from_text(line)
                if extracted:
                    current_targets.extend(extracted)
                    index += 1
                    continue
            in_target_block = False

        summary_match = DRAFT_SUMMARY_RE.match(line)
        if summary_match:
            marker_idx = index
            first_line_rest = summary_match.group(2).strip()
            body_lines = [first_line_rest] if first_line_rest else []
            index += 1
            while index < len(lines) and not STOP_MARKER_RE.match(lines[index]):
                body_lines.append(lines[index])
                index += 1
            body = clean_draft_body(body_lines)
            if body:
                summary = DraftSummary(
                    section_title=current_heading,
                    marker_line_index=marker_idx,
                    body=body,
                )
            continue

        comment_match = DRAFT_COMMENT_RE.match(line)
        if comment_match:
            marker_idx = index
            inline_target_text = comment_match.group(1) or ""
            first_line_rest = comment_match.group(2).strip()
            inline_targets = extract_targets_from_text(inline_target_text)
            if not inline_targets and inline_target_text.strip():
                inline_targets = extract_targets_from_text(f"`{inline_target_text.strip('` ')}`")

            body_lines = [first_line_rest] if first_line_rest else []
            index += 1
            while index < len(lines) and not STOP_MARKER_RE.match(lines[index]):
                body_lines.append(lines[index])
                index += 1

            body = clean_draft_body(body_lines)
            if body:
                effective_targets = inline_targets if inline_targets else list(current_targets)
                if (
                    not effective_targets
                    and summary is None
                    and "general" in current_heading.lower()
                ):
                    summary = DraftSummary(
                        section_title=current_heading,
                        marker_line_index=marker_idx,
                        body=body,
                    )
                else:
                    comments.append(
                        DraftComment(
                            section_title=current_heading,
                            marker_line_index=marker_idx,
                            body=body,
                            targets=effective_targets,
                        )
                    )
            continue

        index += 1

    return ParsedWorkbench(
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        lines=lines,
        summary=summary,
        comments=comments,
        frontmatter=fields,
    )


def parse_patch_hunks(patch: str) -> tuple[list[tuple[int, int]], list[int]]:
    hunks: list[tuple[int, int]] = []
    changed_lines: list[int] = []
    current_start: int | None = None
    current_line = 0

    for raw_line in patch.splitlines():
        hunk_match = HUNK_HEADER_RE.match(raw_line)
        if hunk_match:
            if current_start is not None and current_line >= current_start:
                hunks.append((current_start, current_line))
            current_start = int(hunk_match.group(1))
            current_line = current_start - 1
            continue

        if current_start is None:
            continue

        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            current_line += 1
            changed_lines.append(current_line)
        elif raw_line.startswith("-") and not raw_line.startswith("---"):
            continue
        elif raw_line.startswith(" "):
            current_line += 1

    if current_start is not None and current_line >= current_start:
        hunks.append((current_start, current_line))

    return hunks, changed_lines


def fetch_pr_context(owner: str, repo: str, pr_number: int) -> PrContext:
    query = """
    query($owner: String!, $repo: String!, $number: Int!) {
      viewer { login }
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $number) {
          id
          headRefOid
          url
          reviews(last: 10, states: [PENDING]) {
            nodes {
              id
              author { login }
              body
              comments(first: 50) {
                nodes {
                  id
                  path
                  line
                  url
                }
              }
            }
          }
        }
      }
    }
    """
    data = run_gh_json(
        [
            "api",
            "graphql",
            "-f",
            f"query={query}",
            "-f",
            f"owner={owner}",
            "-f",
            f"repo={repo}",
            "-F",
            f"number={pr_number}",
        ]
    )
    viewer_login = data["data"]["viewer"]["login"]
    pr_node = data["data"]["repository"]["pullRequest"]
    pr_id = pr_node["id"]
    head_oid = pr_node["headRefOid"]

    pending_review = None
    for rev in pr_node["reviews"]["nodes"]:
        if rev.get("author", {}).get("login") == viewer_login:
            pending_review = rev
            break

    raw_files = run_gh_json(
        ["api", "--paginate", f"repos/{owner}/{repo}/pulls/{pr_number}/files"]
    )
    pr_files: dict[str, PrFileDiff] = {}
    for item in raw_files:
        filename = item["filename"]
        patch = item.get("patch") or ""
        hunks, changed_lines = parse_patch_hunks(patch)
        pr_files[filename] = PrFileDiff(
            filename=filename,
            status=item.get("status", "modified"),
            hunks=hunks,
            changed_lines=changed_lines,
        )

    return PrContext(
        pr_id=pr_id,
        head_oid=head_oid,
        viewer_login=viewer_login,
        pending_review=pending_review,
        files=pr_files,
    )


def resolve_file_path(raw_path: str, pr_files: dict[str, PrFileDiff]) -> str | None:
    cleaned = raw_path.strip().lstrip("./")
    if cleaned in pr_files:
        return cleaned
    prefixed = f"mach9-cloud/{cleaned}"
    if prefixed in pr_files:
        return prefixed
    suffix_matches = [p for p in pr_files if p.endswith(f"/{cleaned}") or p == cleaned]
    if len(suffix_matches) == 1:
        return suffix_matches[0]
    basename = os.path.basename(cleaned)
    base_matches = [p for p in pr_files if os.path.basename(p) == basename]
    if len(base_matches) == 1:
        return base_matches[0]
    return None


def resolve_line_in_hunks(
    start_line: int | None,
    end_line: int | None,
    file_diff: PrFileDiff,
) -> tuple[int | None, int, str | None]:
    hunks = file_diff.hunks
    if not hunks:
        line = end_line or start_line or 1
        return None, line, "file has no text patch hunks; using line as-is"

    if start_line is None or end_line is None:
        first_line = file_diff.changed_lines[0] if file_diff.changed_lines else hunks[0][0]
        return None, first_line, f"no line specified; defaulted to first changed line {first_line}"

    s_line = min(start_line, end_line)
    e_line = max(start_line, end_line)

    for h_start, h_end in hunks:
        if h_start <= s_line and e_line <= h_end:
            return (s_line if s_line < e_line else None), e_line, None

    for h_start, h_end in hunks:
        if s_line <= h_end and e_line >= h_start:
            clamped_s = max(s_line, h_start)
            clamped_e = min(e_line, h_end)
            note = f"clamped lines {s_line}-{e_line} to diff hunk {h_start}-{h_end} -> {clamped_s}-{clamped_e}"
            return (clamped_s if clamped_s < clamped_e else None), clamped_e, note

    best_hunk = min(
        hunks,
        key=lambda h: min(abs(e_line - h[0]), abs(e_line - h[1])),
    )
    h_start, h_end = best_hunk
    snapped = h_start if abs(e_line - h_start) <= abs(e_line - h_end) else h_end
    if file_diff.changed_lines:
        idx = bisect.bisect_left(file_diff.changed_lines, e_line)
        candidates = []
        if idx < len(file_diff.changed_lines):
            candidates.append(file_diff.changed_lines[idx])
        if idx > 0:
            candidates.append(file_diff.changed_lines[idx - 1])
        if candidates:
            snapped = min(candidates, key=lambda c: abs(c - e_line))

    note = f"line {e_line} outside diff hunks {hunks}; snapped to nearest changed line {snapped}"
    return None, snapped, note


def resolve_all_comments(
    comments: list[DraftComment],
    pr_files: dict[str, PrFileDiff],
) -> None:
    for comment in comments:
        if not comment.targets:
            raise ValueError(
                f"Draft comment in section '{comment.section_title}' (line {comment.marker_line_index + 1}) "
                "has no `**Target:**` or inline `**Draft comment (`path:line`):**` anchor."
            )

        chosen_target: TargetSpec | None = None
        chosen_path: str | None = None
        for candidate in comment.targets:
            resolved = resolve_file_path(candidate.raw_path, pr_files)
            if resolved is not None and pr_files[resolved].hunks:
                chosen_target = candidate
                chosen_path = resolved
                break

        if chosen_path is None:
            for candidate in comment.targets:
                resolved = resolve_file_path(candidate.raw_path, pr_files)
                if resolved is not None:
                    chosen_target = candidate
                    chosen_path = resolved
                    break

        if chosen_path is None or chosen_target is None:
            tried = ", ".join(t.raw_path for t in comment.targets)
            raise ValueError(
                f"Could not match any target path ({tried}) for section '{comment.section_title}' "
                "in PR changed files."
            )

        file_diff = pr_files[chosen_path]
        r_start, r_line, note = resolve_line_in_hunks(
            chosen_target.start_line,
            chosen_target.end_line,
            file_diff,
        )
        comment.resolved_path = chosen_path
        comment.resolved_start_line = r_start
        comment.resolved_line = r_line
        comment.snap_note = note


def print_check_report(workbench: ParsedWorkbench, ctx: PrContext) -> None:
    print(
        f"PR #{workbench.pr_number} ({workbench.owner}/{workbench.repo}) @ {ctx.head_oid[:10]} (viewer: {ctx.viewer_login})"
    )
    if ctx.pending_review:
        existing_count = len(ctx.pending_review.get("comments", {}).get("nodes", []))
        print(
            f"  Found existing PENDING review ({ctx.pending_review['id']}) with {existing_count} comment(s); "
            "`post` will attach threads and submit."
        )
    if workbench.summary is None and not workbench.comments:
        print("  No unposted `**Draft summary:**` or `**Draft comment:**` blocks found.")
        return

    if workbench.summary:
        print(
            f"  Summary ({workbench.summary.section_title}): {len(workbench.summary.body)} chars"
        )
    for idx, c in enumerate(workbench.comments, 1):
        loc = (
            f"{c.resolved_path}:{c.resolved_start_line}-{c.resolved_line}"
            if c.resolved_start_line
            else f"{c.resolved_path}:{c.resolved_line}"
        )
        print(f"  [{idx}] {c.section_title} -> {loc} ({len(c.body)} chars)")
        if c.snap_note:
            print(f"      Note: {c.snap_note}")


def insert_header_metadata(
    lines: list[str],
    pr_number: int,
    new_posted_bullets: list[str],
    transcript: tuple[str, str] | None,
    skill_version: str | None = None,
) -> list[str]:
    """Add transcript, skill version, and posted-comment bullets to the header block.

    Lines already there are kept as they are, including transcript lines that the vault linker
    upgraded to `[[chats/...]]` wikilinks (they still carry the chat_id, so no duplicate is added).
    """
    header_start, first_section_idx = header_bounds(lines)
    prefix_lines = list(lines[:header_start])
    header_lines = list(lines[header_start:first_section_idx])
    rest_lines = list(lines[first_section_idx:])

    header_text = "\n".join(header_lines)
    if transcript is not None:
        t_uuid, t_path = transcript
        if t_uuid not in header_text:
            transcript_line = f"- Agent transcript: [PR {pr_number} review dialogue]({t_uuid})" + (
                f" (`{t_path}`)" if t_path else ""
            )
            insert_at = len(header_lines)
            while insert_at > 0 and not header_lines[insert_at - 1].strip():
                insert_at -= 1
            header_lines.insert(insert_at, transcript_line)

    if skill_version is not None and "Skill version:" not in header_text:
        version_line = f"- Skill version: `{skill_version}`"
        insert_at = len(header_lines)
        while insert_at > 0 and not header_lines[insert_at - 1].strip():
            insert_at -= 1
        header_lines.insert(insert_at, version_line)

    if new_posted_bullets:
        posted_idx = next(
            (
                i
                for i, l in enumerate(header_lines)
                if re.match(r"^-?\s*Posted\b", l, re.IGNORECASE)
            ),
            None,
        )
        if posted_idx is not None:
            insert_pos = posted_idx + 1
            while insert_pos < len(header_lines) and header_lines[insert_pos].startswith("  - "):
                insert_pos += 1
            for bullet in new_posted_bullets:
                if bullet not in header_lines:
                    header_lines.insert(insert_pos, bullet)
                    insert_pos += 1
        else:
            insert_at = len(header_lines)
            while insert_at > 0 and not header_lines[insert_at - 1].strip():
                insert_at -= 1
            header_lines.insert(insert_at, "- Posted comments:")
            insert_at += 1
            for bullet in new_posted_bullets:
                header_lines.insert(insert_at, bullet)
                insert_at += 1

    if header_lines and header_lines[-1].strip():
        header_lines.append("")

    return prefix_lines + header_lines + rest_lines


def save_posted_progress(
    workbench_path: Path,
    workbench: ParsedWorkbench,
    extra_pending: list[tuple[str, str]],
) -> None:
    """Persist any `posted_url` values recorded so far into the workbench file in place."""
    lines = list(workbench.lines)
    new_posted_bullets: list[str] = []

    if workbench.summary is not None and workbench.summary.posted_url:
        idx = workbench.summary.marker_line_index
        lines[idx] = f"**Posted review summary ([link]({workbench.summary.posted_url})):**"
        new_posted_bullets.append(
            f"  - [Overall review summary]({workbench.summary.posted_url})"
        )

    for comment in workbench.comments:
        if not comment.posted_url:
            continue
        idx = comment.marker_line_index
        lines[idx] = f"**Posted comment ([link]({comment.posted_url})):**"
        short_file = os.path.basename(comment.resolved_path)
        line_str = (
            f"{comment.resolved_start_line}-{comment.resolved_line}"
            if comment.resolved_start_line
            else f"{comment.resolved_line}"
        )
        new_posted_bullets.append(
            f"  - [`{short_file}:{line_str}` — {comment.section_title}]({comment.posted_url})"
        )

    for label, url in extra_pending:
        new_posted_bullets.append(f"  - [{label}]({url})")

    updated_lines = insert_header_metadata(
        lines=lines,
        pr_number=workbench.pr_number,
        new_posted_bullets=new_posted_bullets,
        transcript=None,
    )
    workbench.lines = updated_lines
    workbench_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")


def step_check(workbench_path: Path) -> tuple[ParsedWorkbench, PrContext]:
    workbench = parse_workbench(workbench_path)
    ctx = fetch_pr_context(workbench.owner, workbench.repo, workbench.pr_number)
    if workbench.comments:
        resolve_all_comments(workbench.comments, ctx.files)
    print_check_report(workbench, ctx)
    return workbench, ctx


def step_post(
    workbench_path: Path,
    prechecked: tuple[ParsedWorkbench, PrContext] | None = None,
) -> bool:
    """Publish drafts to GitHub; returns whether anything was posted."""
    workbench, ctx = prechecked if prechecked is not None else step_check(workbench_path)

    if workbench.summary is None and not workbench.comments and ctx.pending_review is None:
        print("Nothing to post; skipping GitHub mutation.")
        return False

    extra_pending: list[tuple[str, str]] = []

    if ctx.pending_review is not None:
        review_id = ctx.pending_review["id"]
        add_thread_mutation = """
        mutation($input: AddPullRequestReviewThreadInput!) {
          addPullRequestReviewThread(input: $input) {
            thread {
              comments(first: 1) {
                nodes { url }
              }
            }
          }
        }
        """
        try:
            for comment in workbench.comments:
                thread_input: dict = {
                    "pullRequestReviewId": review_id,
                    "path": comment.resolved_path,
                    "line": comment.resolved_line,
                    "side": "RIGHT",
                    "body": comment.body,
                }
                if comment.resolved_start_line is not None:
                    thread_input["startLine"] = comment.resolved_start_line
                    thread_input["startSide"] = "RIGHT"

                res = run_gh_json(
                    ["api", "graphql", "--input", "-"],
                    input_data={
                        "query": add_thread_mutation,
                        "variables": {"input": thread_input},
                    },
                )
                comment.posted_url = res["data"]["addPullRequestReviewThread"]["thread"][
                    "comments"
                ]["nodes"][0]["url"]

            submit_query = """
            mutation($input: SubmitPullRequestReviewInput!) {
              submitPullRequestReview(input: $input) {
                pullRequestReview {
                  url
                }
              }
            }
            """
            submit_input: dict = {
                "pullRequestReviewId": review_id,
                "event": "COMMENT",
            }
            existing_body = (ctx.pending_review.get("body") or "").strip()
            if workbench.summary is not None:
                submit_input["body"] = workbench.summary.body
            elif existing_body:
                submit_input["body"] = existing_body

            submit_res = run_gh_json(
                ["api", "graphql", "--input", "-"],
                input_data={"query": submit_query, "variables": {"input": submit_input}},
            )
            review_url = submit_res["data"]["submitPullRequestReview"]["pullRequestReview"]["url"]
            if workbench.summary is not None:
                workbench.summary.posted_url = review_url

            for existing in ctx.pending_review.get("comments", {}).get("nodes", []):
                if existing.get("url"):
                    label = (
                        f"`{os.path.basename(existing.get('path', 'comment'))}:"
                        f"{existing.get('line', '')}` (pending comment submitted)"
                    )
                    extra_pending.append((label, existing["url"]))
        finally:
            if any(c.posted_url for c in workbench.comments) or (
                workbench.summary and workbench.summary.posted_url
            ):
                save_posted_progress(workbench_path, workbench, extra_pending)

        print(f"\nPublished pending review: {review_url}")
        for c in workbench.comments:
            print(f"  - {c.section_title}: {c.posted_url}")
        return True

    mutation = """
    mutation($input: AddPullRequestReviewInput!) {
      addPullRequestReview(input: $input) {
        pullRequestReview {
          id
          url
          comments(first: 100) {
            nodes {
              url
              path
              line
            }
          }
        }
      }
    }
    """
    threads_payload: list[dict] = []
    for comment in workbench.comments:
        t: dict = {
            "path": comment.resolved_path,
            "line": comment.resolved_line,
            "side": "RIGHT",
            "body": comment.body,
        }
        if comment.resolved_start_line is not None:
            t["startLine"] = comment.resolved_start_line
            t["startSide"] = "RIGHT"
        threads_payload.append(t)

    review_input: dict = {
        "pullRequestId": ctx.pr_id,
        "commitOID": ctx.head_oid,
        "event": "COMMENT",
        "threads": threads_payload,
    }
    if workbench.summary is not None:
        review_input["body"] = workbench.summary.body

    res = run_gh_json(
        ["api", "graphql", "--input", "-"],
        input_data={"query": mutation, "variables": {"input": review_input}},
    )
    review_node = res["data"]["addPullRequestReview"]["pullRequestReview"]
    review_url = review_node["url"]
    if workbench.summary is not None:
        workbench.summary.posted_url = review_url

    nodes = review_node.get("comments", {}).get("nodes", [])
    for comment, node in zip(workbench.comments, nodes):
        comment.posted_url = node["url"]

    save_posted_progress(workbench_path, workbench, extra_pending=[])
    print(f"\nPublished review: {review_url}")
    for c in workbench.comments:
        print(f"  - {c.section_title}: {c.posted_url}")
    return True


def find_latest_transcript(workbench_path: Path | None = None) -> tuple[str, str] | None:
    projects_dir = Path.home() / ".cursor" / "projects"
    conv_id = os.environ.get("CURSOR_CONVERSATION_ID", "").strip()
    env_transcripts_dir = os.environ.get("AGENT_TRANSCRIPTS", "").strip()

    if conv_id:
        if env_transcripts_dir:
            for candidate in (
                Path(env_transcripts_dir) / conv_id / f"{conv_id}.jsonl",
                Path(env_transcripts_dir) / f"{conv_id}.jsonl",
            ):
                if candidate.exists():
                    return conv_id, str(candidate)
        if projects_dir.exists():
            for match in projects_dir.glob(f"*/agent-transcripts/{conv_id}/{conv_id}.jsonl"):
                return conv_id, str(match)

    scoped_dirs: list[Path] = []
    if env_transcripts_dir:
        env_path = Path(env_transcripts_dir)
        if env_path.is_dir():
            scoped_dirs.append(env_path)

    if projects_dir.exists():
        roots = [Path.cwd()]
        # ~/pr-reviews is not a code workspace, so only a workbench still inside a repo clone scopes the search.
        if workbench_path is not None and not is_in_reviews_dir(workbench_path):
            roots.insert(0, workbench_path.parent)
        for root in roots:
            for directory in (root.resolve(), *root.resolve().parents):
                slug = re.sub(r"[^a-zA-Z0-9]+", "-", str(directory).lstrip("/")).strip("-")
                if not slug:
                    continue
                candidate_dir = projects_dir / slug / "agent-transcripts"
                if candidate_dir.is_dir() and candidate_dir not in scoped_dirs:
                    scoped_dirs.append(candidate_dir)

    search_groups = [
        [p for d in scoped_dirs for p in d.glob("*/*.jsonl")],
        list(projects_dir.glob("*/agent-transcripts/*/*.jsonl")) if projects_dir.exists() else [],
    ]

    for group in search_groups:
        candidates: list[tuple[float, Path]] = []
        for jsonl in group:
            if "subagents" in jsonl.parts:
                continue
            try:
                candidates.append((jsonl.stat().st_mtime, jsonl))
            except OSError:
                continue
        if candidates:
            candidates.sort(key=lambda item: item[0], reverse=True)
            latest_path = candidates[0][1]
            return latest_path.stem, str(latest_path)

    return None


def find_skill_version() -> str | None:
    skill_dir = Path(__file__).resolve().parent
    try:
        proc = subprocess.run(
            ["git", "-C", str(skill_dir), "log", "-1", "--format=%h", "--", "SKILL.md"],
            capture_output=True,
            text=True,
            check=False,
        )
        sha = proc.stdout.strip()
        return sha or None
    except OSError:
        return None


def resolve_transcript(explicit: str | None, workbench_path: Path | None) -> tuple[str, str] | None:
    """(chat_id, jsonl path) from `--transcript` (a path or a UUID), else the active session's transcript."""
    if not explicit:
        return find_latest_transcript(workbench_path)
    value = explicit.strip()
    if UUID_RE.fullmatch(value):
        projects_dir = Path.home() / ".cursor" / "projects"
        match = next(projects_dir.glob(f"*/agent-transcripts/{value}/{value}.jsonl"), None)
        return value, str(match) if match else ""
    t_path = Path(value).expanduser()
    return t_path.stem, str(t_path)


def header_chat_id(lines: list[str]) -> str | None:
    """The first chat_id on a header transcript line, for workbenches that predate frontmatter."""
    start, end = header_bounds(lines)
    for index in range(start, end):
        if "transcript" not in lines[index].lower():
            continue
        block = [lines[index]]
        for line in lines[index + 1 : end]:
            if not line[:1].isspace():
                break
            block.append(line)
        match = UUID_RE.search("\n".join(block))
        if match:
            return match.group(0).lower()
    return None


def stamp_workbench(
    workbench_path: Path,
    transcript: tuple[str, str] | None,
    skill_version: str | None,
) -> list[str]:
    """Mark the workbench done in place: header transcript and skill lines, then the frontmatter."""
    workbench = parse_workbench(workbench_path)
    lines = insert_header_metadata(
        lines=workbench.lines,
        pr_number=workbench.pr_number,
        new_posted_bullets=[],
        transcript=transcript,
        skill_version=skill_version,
    )
    lines = upsert_frontmatter(
        lines,
        {
            "pr": workbench.pr_number,
            "repo": f"{workbench.owner}/{workbench.repo}",
            "date": date.today().isoformat(),
            "status": "done",
            "posted_comments": count_posted_comments(lines),
            "chat_id": header_chat_id(workbench.lines) or (transcript[0] if transcript else None),
            "skill_version": skill_version,
        },
        keep_existing=frozenset({"pr", "repo", "date", "chat_id", "skill_version"}),
    )
    workbench_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return lines


def step_done(workbench_path: Path, explicit_transcript: str | None = None) -> Path:
    dest_path = workbench_path
    if not is_in_reviews_dir(workbench_path):
        dest_path = REVIEWS_DIR / workbench_path.name
        if dest_path.exists():
            raise FileExistsError(f"{dest_path} already exists; merge {workbench_path} into it by hand.")

    transcript = resolve_transcript(explicit_transcript, workbench_path)
    lines = stamp_workbench(workbench_path, transcript, find_skill_version())
    if dest_path != workbench_path:
        REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
        shutil.move(str(workbench_path), dest_path)

    fields = read_frontmatter(lines)
    print(f"Marked done: {dest_path}")
    print(f"  chat_id: {fields.get('chat_id') or '(none)'} · posted_comments: {fields.get('posted_comments')}")
    if transcript:
        print(f"  Active transcript: {transcript[0]} ({transcript[1] or 'path unknown'})")
    return dest_path


def resolve_init_target(target: str) -> tuple[Path, str, str, int]:
    """(workbench path, owner, repo, PR number) for an existing workbench, PR URL, `owner/repo#N`, or number."""
    candidate = Path(target).expanduser()
    if candidate.is_file():
        workbench = parse_workbench(candidate)
        return candidate.absolute(), workbench.owner, workbench.repo, workbench.pr_number
    url = PR_URL_RE.search(target)
    ref = PR_REF_RE.fullmatch(target.strip())
    name = PR_FILENAME_RE.search(candidate.name)
    if url:
        owner, repo, number = url.group(1), url.group(2), int(url.group(3))
    elif ref:
        owner, repo, number = ref.group(1) or DEFAULT_OWNER, ref.group(2) or DEFAULT_REPO, int(ref.group(3))
    elif name:
        owner, repo, number = DEFAULT_OWNER, DEFAULT_REPO, int(name.group(1))
    else:
        raise ValueError(f"Expected a PR number, PR URL, `owner/repo#N`, or pr-<number>-review.md; got {target!r}.")
    path = resolve_workbench_path(f"pr-{number}-review.md" if url or ref else target)
    return path, owner, repo, number


def pr_header_lines(pr: dict, owner: str, repo: str) -> list[str]:
    lines = [f"- **PR:** [{owner}/{repo}#{pr['number']} — {pr['title']}]({pr['url']})"]
    login = (pr.get("author") or {}).get("login")
    if login:
        lines.append(f"- **Author:** `@{login}`")
    if pr.get("headRefName"):
        lines.append(f"- **Branch:** `{pr['headRefName']}` → `{pr.get('baseRefName') or '?'}`")
    return lines


def ensure_pr_header(lines: list[str], pr: dict, owner: str, repo: str) -> list[str]:
    """A new workbench's title and PR block; an existing one only gains the PR lines if it lacks a link."""
    if not lines:
        return [f"# PR #{pr['number']} Review Workbench", "", *pr_header_lines(pr, owner, repo), ""]
    start, end = header_bounds(lines)
    if f"/pull/{pr['number']}" in "\n".join(lines[start:end]):
        return lines
    title_index = next((i for i in range(start, end) if lines[i].startswith("# ")), None)
    at = title_index + 1 if title_index is not None else start
    while at < end and not lines[at].strip():
        at += 1
    block = pr_header_lines(pr, owner, repo)
    if at < len(lines) and lines[at].strip():
        block.append("")
    if title_index is not None and at == title_index + 1:
        block.insert(0, "")
    return lines[:at] + block + lines[at:]


def step_init(target: str, explicit_transcript: str | None = None) -> Path:
    workbench_path, owner, repo, number = resolve_init_target(target)
    pr = run_gh_json(
        [
            "pr",
            "view",
            str(number),
            "--repo",
            f"{owner}/{repo}",
            "--json",
            "number,title,author,url,headRefName,baseRefName",
        ]
    )
    transcript = resolve_transcript(explicit_transcript, workbench_path)
    skill_version = find_skill_version()
    is_new = not workbench_path.exists()
    lines = [] if is_new else workbench_path.read_text(encoding="utf-8").splitlines()
    lines = ensure_pr_header(lines, pr, owner, repo)
    lines = insert_header_metadata(
        lines=lines,
        pr_number=number,
        new_posted_bullets=[],
        transcript=transcript,
        skill_version=skill_version,
    )
    lines = upsert_frontmatter(
        lines,
        {
            "pr": number,
            "repo": f"{owner}/{repo}",
            "title": pr.get("title"),
            "author": (pr.get("author") or {}).get("login"),
            "date": date.today().isoformat(),
            "status": "active",
            "posted_comments": count_posted_comments(lines),
            "chat_id": header_chat_id(lines) or (transcript[0] if transcript else None),
            "skill_version": skill_version,
        },
        keep_existing=frozenset({"date", "chat_id", "skill_version"}),
    )
    workbench_path.parent.mkdir(parents=True, exist_ok=True)
    workbench_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{'Created' if is_new else 'Updated'} workbench: {workbench_path}")
    print(f"  PR #{number} — {pr.get('title')} ({owner}/{repo})")
    if transcript:
        print(f"  Transcript: {transcript[0]}")
    return workbench_path


def parse_cli_args(argv: list[str]) -> argparse.Namespace:
    commands = {"init", "check", "post", "done", "archive", "publish"}
    if argv and argv[0] not in commands and not argv[0].startswith("-"):
        argv = ["publish", *argv]

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)
    workbench_help = "pr-<number>-review.md path, filename, PR number, or PR URL"

    p_init = subparsers.add_parser(
        "init",
        help="Create or refresh ~/pr-reviews/pr-<number>-review.md with frontmatter (status: active) and header",
    )
    p_init.add_argument("target", help="PR number, PR URL, owner/repo#N, or an existing workbench path")
    p_init.add_argument("--transcript", type=str, default=None, help="Explicit transcript path or UUID")

    p_check = subparsers.add_parser(
        "check", help="Validate targets and diff hunks against GitHub (read-only)"
    )
    p_check.add_argument("workbench", help=workbench_help)

    p_post = subparsers.add_parser(
        "post",
        help="Post draft comments/summary to GitHub, stamp links in place, and mark the frontmatter done",
    )
    p_post.add_argument("workbench", help=workbench_help)

    p_done = subparsers.add_parser(
        "done",
        aliases=["archive"],
        help="Stamp status: done, posted_comments, chat_id, and skill_version; move into ~/pr-reviews/ if elsewhere",
    )
    p_done.add_argument("workbench", help=workbench_help)
    p_done.add_argument(
        "--transcript", type=str, default=None, help="Explicit transcript path or UUID"
    )

    p_publish = subparsers.add_parser(
        "publish", help="Run check -> post -> done in sequence (default)"
    )
    p_publish.add_argument("workbench", help=workbench_help)
    p_publish.add_argument(
        "--dry-run", action="store_true", help="Alias for `check` (validate only)"
    )
    p_publish.add_argument(
        "--no-archive", action="store_true", help="Run `check` and `post` without `done`"
    )
    p_publish.add_argument(
        "--transcript", type=str, default=None, help="Explicit transcript path or UUID"
    )

    return parser.parse_args(argv)


def main() -> int:
    args = parse_cli_args(sys.argv[1:])
    try:
        if args.command == "init":
            step_init(args.target, explicit_transcript=args.transcript)
            return 0

        workbench_path = resolve_workbench_path(args.workbench)
        if not workbench_path.exists():
            print(f"Error: workbench file not found: {workbench_path}", file=sys.stderr)
            return 1

        if args.command == "check":
            step_check(workbench_path)
            return 0

        if args.command == "post":
            if step_post(workbench_path):
                stamp_workbench(workbench_path, find_latest_transcript(workbench_path), find_skill_version())
            return 0

        if args.command in ("done", "archive"):
            step_done(workbench_path, explicit_transcript=args.transcript)
            return 0

        if args.command == "publish":
            prechecked = step_check(workbench_path)
            if args.dry_run:
                return 0
            posted = step_post(workbench_path, prechecked=prechecked)
            if not args.no_archive:
                step_done(workbench_path, explicit_transcript=args.transcript)
            elif posted:
                stamp_workbench(workbench_path, resolve_transcript(args.transcript, workbench_path), find_skill_version())
            return 0
    except (ValueError, RuntimeError, FileExistsError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
