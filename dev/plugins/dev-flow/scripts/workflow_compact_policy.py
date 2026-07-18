from __future__ import annotations

from pathlib import Path
from typing import Any

from workflow_paths import repo_path
from workflow_state import parse_state


MAJOR_BOUNDARIES = {
    "project_setup_completed",
    "codebase_mapping_completed",
    "decision_resolution_completed",
    "design_saved",
    "openspec_change_planned",
    "verification_passed",
    "change_archived",
}
SKIP_BOUNDARIES = {"small_task_update", "typo_fix", "docs_only_micro_change"}
STOPPING_POINT_STAGES = {
    "archive",
    "archived",
    "done",
    "complete",
    "completed",
    "finished",
    "closed",
    "idle",
    "stop",
    "end",
}


def recommend_compact(boundary: str, continuation_required: bool = True) -> bool:
    return continuation_required and boundary in MAJOR_BOUNDARIES


def compact_recommendation(
    repo: Path,
    boundary: str,
    next_stage: str,
    continuation_required: bool | None = None,
) -> dict[str, Any]:
    repo = repo_path(repo)
    continuation = resolve_continuation_required(next_stage, continuation_required)
    if boundary in SKIP_BOUNDARIES:
        return recommendation(False, f"{boundary} is configured to skip compact.", next_stage, continuation)
    if boundary in MAJOR_BOUNDARIES and not continuation:
        return recommendation(
            False,
            f"{boundary} is a major workflow boundary, but no continuation is required in this thread.",
            next_stage,
            continuation,
        )
    if boundary in MAJOR_BOUNDARIES:
        return recommendation(
            True,
            f"{boundary} is a major workflow boundary with a continuation.",
            next_stage,
            continuation,
        )
    context = parse_state(repo).get("context_management", {})
    if continuation and context.get("compact_status") == "pending":
        return recommendation(True, "A checkpoint is pending compact.", next_stage, continuation)
    return recommendation(False, "No compact trigger matched.", next_stage, continuation)


def resolve_continuation_required(next_stage: str | None, explicit: bool | None = None) -> bool:
    if explicit is not None:
        return explicit
    normalized = normalize_stage(next_stage)
    return normalized not in STOPPING_POINT_STAGES


def normalize_stage(next_stage: str | None) -> str:
    return str(next_stage or "").strip().lower().replace("-", "_").replace(" ", "_")


def recommendation(should_compact: bool, reason: str, next_stage: str, continuation_required: bool) -> dict[str, Any]:
    instruction = (
        f"Compact is recommended before {next_stage}; run `/compact` at a stable boundary "
        "or continue from the checkpoint if automatic compaction/recovery is available."
        if should_compact
        else "State is updated. Compact is optional before starting a new thread or handoff."
    )
    return {
        "recommend_compact": should_compact,
        "reason": reason,
        "instruction": instruction,
        "continuation_required": continuation_required,
    }
