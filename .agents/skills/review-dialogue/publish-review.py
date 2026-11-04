#!/usr/bin/env python3
"""Composable CLI for validating, posting, and archiving a review-dialogue workbench.

Steps (can be run individually or all together via `publish`):
    python3 ~/.cursor/skills/review-dialogue/publish-review.py check <workbench.md>
    python3 ~/.cursor/skills/review-dialogue/publish-review.py post <workbench.md>
    python3 ~/.cursor/skills/review-dialogue/publish-review.py archive <workbench.md> [--transcript <path>]
    python3 ~/.cursor/skills/review-dialogue/publish-review.py [publish] <workbench.md> [--transcript <path>]
"""

from __future__ import annotations

import argparse
import bisect
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from dataclasses import dataclass

PR_URL_RE = re.compile(r"https://github\.com/([^/\s]+)/([^/\s#)]+)/pull/(\d+)")
PR_FILENAME_RE = re.compile(r"pr-(\d+)")

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
    summary: DraftSummary | None
    comments: list[DraftComment]


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


def parse_workbench(path: Path) -> ParsedWorkbench:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    url_match = PR_URL_RE.search(text)
    if url_match:
        owner, repo, pr_num_str = url_match.group(1), url_match.group(2), url_match.group(3)
        pr_number = int(pr_num_str)
    else:
        fn_match = PR_FILENAME_RE.search(path.name)
        if not fn_match:
            raise ValueError(
                f"Could not find a GitHub PR URL in {path} or a PR number in filename {path.name}."
            )
        owner, repo, pr_number = "mach9robotics", "bagel", int(fn_match.group(1))

    current_heading = "General"
    current_targets: list[TargetSpec] = []
    in_target_block = False

    summary: DraftSummary | None = None
    comments: list[DraftComment] = []

    index = 0
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
    first_section_idx = next(
        (i for i, l in enumerate(lines) if l.startswith("## ") or re.match(r"^---+\s*$", l)),
        len(lines),
    )
    header_lines = list(lines[:first_section_idx])
    rest_lines = list(lines[first_section_idx:])

    header_text = "\n".join(header_lines)
    if transcript is not None:
        t_uuid, t_path = transcript
        if t_uuid not in header_text:
            transcript_line = (
                f"- Agent transcript: [PR {pr_number} review dialogue]({t_uuid}) (`{t_path}`)"
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

    return header_lines + rest_lines


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
) -> None:
    workbench, ctx = prechecked if prechecked is not None else step_check(workbench_path)

    if workbench.summary is None and not workbench.comments and ctx.pending_review is None:
        print("Nothing to post; skipping GitHub mutation.")
        return

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
        return

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
        if workbench_path is not None:
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


def step_archive(workbench_path: Path, explicit_transcript: str | None = None) -> Path:
    workbench = parse_workbench(workbench_path)
    if explicit_transcript:
        t_path = Path(explicit_transcript).expanduser()
        transcript = (t_path.stem, str(t_path))
    else:
        transcript = find_latest_transcript(workbench_path)

    skill_version = find_skill_version()
    updated_lines = insert_header_metadata(
        lines=workbench.lines,
        pr_number=workbench.pr_number,
        new_posted_bullets=[],
        transcript=transcript,
        skill_version=skill_version,
    )
    updated_content = "\n".join(updated_lines) + "\n"

    archive_dir = Path.home() / "pr-reviews"
    archive_dir.mkdir(parents=True, exist_ok=True)
    dest_path = (
        workbench_path
        if workbench_path.parent == archive_dir
        else archive_dir / workbench_path.name
    )
    dest_path.write_text(updated_content, encoding="utf-8")
    if dest_path != workbench_path:
        workbench_path.unlink()

    print(f"Archived workbench: {dest_path}")
    if transcript:
        print(f"  Transcript linked: {transcript[0]} ({transcript[1]})")
    return dest_path


def parse_cli_args(argv: list[str]) -> argparse.Namespace:
    commands = {"check", "post", "archive", "publish"}
    if argv and argv[0] not in commands and not argv[0].startswith("-"):
        argv = ["publish", *argv]

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_check = subparsers.add_parser(
        "check", help="Validate targets and diff hunks against GitHub (read-only)"
    )
    p_check.add_argument("workbench", type=Path, help="Path to pr-<number>-review.md")

    p_post = subparsers.add_parser(
        "post",
        help="Post draft comments/summary to GitHub and stamp links into the workbench in place",
    )
    p_post.add_argument("workbench", type=Path, help="Path to pr-<number>-review.md")

    p_archive = subparsers.add_parser(
        "archive",
        help="Stamp the active agent transcript link and move the workbench to ~/pr-reviews/",
    )
    p_archive.add_argument("workbench", type=Path, help="Path to pr-<number>-review.md")
    p_archive.add_argument(
        "--transcript", type=str, default=None, help="Explicit transcript path or UUID"
    )

    p_publish = subparsers.add_parser(
        "publish", help="Run check -> post -> archive in sequence (default)"
    )
    p_publish.add_argument("workbench", type=Path, help="Path to pr-<number>-review.md")
    p_publish.add_argument(
        "--dry-run", action="store_true", help="Alias for `check` (validate only)"
    )
    p_publish.add_argument(
        "--no-archive", action="store_true", help="Run `check` and `post` without `archive`"
    )
    p_publish.add_argument(
        "--transcript", type=str, default=None, help="Explicit transcript path or UUID"
    )

    return parser.parse_args(argv)


def main() -> int:
    args = parse_cli_args(sys.argv[1:])
    workbench_path = args.workbench.expanduser().resolve()
    if not workbench_path.exists():
        print(f"Error: workbench file not found: {workbench_path}", file=sys.stderr)
        return 1

    if args.command == "check":
        step_check(workbench_path)
        return 0

    if args.command == "post":
        step_post(workbench_path)
        return 0

    if args.command == "archive":
        step_archive(workbench_path, explicit_transcript=args.transcript)
        return 0

    if args.command == "publish":
        prechecked = step_check(workbench_path)
        if args.dry_run:
            return 0
        step_post(workbench_path, prechecked=prechecked)
        if not args.no_archive:
            step_archive(workbench_path, explicit_transcript=args.transcript)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
