from __future__ import annotations

from pathlib import Path
from typing import Any


EMPTY_VALUES = (None, "", "none")
SUPPORTED_COMPACT_STATUSES = {
    "pending",
    "not_needed",
    "completed",
    "skipped",
    "failed",
    "blocked",
}


def supported_compact_statuses_text() -> str:
    return ", ".join(sorted(SUPPORTED_COMPACT_STATUSES))


def check_compact_state(
    repo: Path,
    state: dict[str, Any],
    issues: list[str],
    warnings: list[str],
) -> None:
    context = state.get("context_management", {})
    status = context.get("compact_status")
    if status not in SUPPORTED_COMPACT_STATUSES:
        issues.append(
            f"Unsupported compact_status `{status}`; must be one of: {supported_compact_statuses_text()}"
        )
        return
    if status == "pending":
        warnings.append("compact_status is pending; run /compact or record an explicit skip reason")
    if status == "skipped" and context.get("compact_skip_reason") in EMPTY_VALUES:
        issues.append("compact_status is skipped but compact_skip_reason is missing")
    result_file = context.get("last_compact_result_file")
    if status == "completed" and result_file in EMPTY_VALUES:
        issues.append("compact_status is completed but last_compact_result_file is missing")
    if status == "completed" and result_file not in EMPTY_VALUES and not (repo / str(result_file)).exists():
        issues.append(f"Compact result file `{result_file}` is missing")
