from __future__ import annotations

from typing import Any


VALID_STATUSES = {"completed", "skipped", "failed", "blocked"}
VALID_SOURCES = {"manual", "cli", "responses_api", "harness"}


def option_issues(status: str, source: str, options: dict[str, Any]) -> list[str]:
    issues = []
    if status not in VALID_STATUSES:
        issues.append(f"Unsupported compact status `{status}`")
    if source not in VALID_SOURCES:
        issues.append(f"Unsupported compact source `{source}`")
    if status == "skipped" and not clean_text(options.get("skip_reason")):
        issues.append("Skipped compact requires --skip-reason")
    if status in {"failed", "blocked"} and not clean_text(options.get("error")):
        issues.append(f"{status} compact requires --error")
    return issues


def first_text(primary: Any, fallback: Any) -> str:
    primary_text = clean_text(primary)
    if primary_text:
        return primary_text
    return clean_text(fallback)


def clean_text(value: Any) -> str:
    if value in (None, "", "none"):
        return ""
    return " ".join(str(value).split())
