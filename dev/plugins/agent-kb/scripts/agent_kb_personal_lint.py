from __future__ import annotations

from pathlib import Path

from agent_kb_lint_rules import file_age_days
from agent_kb_markdown import finding, formal_notes, relative_note


def capture_backlog_findings(vault: Path, stale_days: int):
    return aged_note_findings(
        vault / "inbox" / "codex-captures",
        vault,
        stale_days,
        "capture-unprocessed",
        "Capture is waiting for routing evidence.",
    )


def promotion_backlog_findings(vault: Path, stale_days: int):
    return aged_note_findings(
        vault / "promotion" / "candidates",
        vault,
        stale_days,
        "promotion-candidate-stale",
        "Promotion candidate is waiting for review.",
    )


def aged_note_findings(root: Path, vault: Path, stale_days: int, rule: str, message: str):
    if not root.exists():
        return []
    findings: list[dict[str, str]] = []
    for path in root.rglob("*.md"):
        if file_age_days(path) > stale_days:
            findings.append(finding(rule, relative_note(vault, path), "warning", message))
    return findings


def needs_review_findings(vault: Path):
    findings: list[dict[str, str]] = []
    for note_path in formal_notes(vault):
        text = note_path.read_text(encoding="utf-8")
        if "needs_review: true" in text:
            findings.append(
                finding("needs-review", relative_note(vault, note_path), "warning", "Note needs review.")
            )
    return findings


ARCHIVE_MARKERS = ("archive/", "[[archive", "[[../archive", "[[../../archive")


def active_archive_reference_findings(vault: Path):
    findings: list[dict[str, str]] = []
    for note_path in formal_notes(vault):
        relative = relative_note(vault, note_path)
        text = note_path.read_text(encoding="utf-8")
        if not relative.startswith("archive/") and any(marker in text for marker in ARCHIVE_MARKERS):
            findings.append(
                finding(
                    "active-archive-reference",
                    relative,
                    "warning",
                    "Active note references archived content.",
                )
            )
    return findings
