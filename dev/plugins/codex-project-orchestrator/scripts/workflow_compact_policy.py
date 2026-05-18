from __future__ import annotations

from pathlib import Path
from typing import Any

from workflow_paths import repo_path
from workflow_state import parse_state


MAJOR_BOUNDARIES = {
    "project_setup_completed",
    "codebase_mapping_completed",
    "brainstorm_completed",
    "design_saved",
    "openspec_change_planned",
    "phase_plan_saved",
    "verification_passed",
    "change_archived",
    "phase_shipped",
}
SKIP_BOUNDARIES = {"small_task_update", "typo_fix", "docs_only_micro_change"}


def recommend_compact(boundary: str) -> bool:
    return boundary in MAJOR_BOUNDARIES


def compact_recommendation(repo: Path, boundary: str, next_stage: str) -> dict[str, Any]:
    repo = repo_path(repo)
    if boundary in SKIP_BOUNDARIES:
        return recommendation(False, f"{boundary} is configured to skip compact.", next_stage)
    if boundary in MAJOR_BOUNDARIES:
        return recommendation(True, f"{boundary} is a major workflow boundary.", next_stage)
    context = parse_state(repo).get("context_management", {})
    if context.get("compact_status") == "pending":
        return recommendation(True, "A checkpoint is pending compact.", next_stage)
    return recommendation(False, "No compact trigger matched.", next_stage)


def recommendation(should_compact: bool, reason: str, next_stage: str) -> dict[str, Any]:
    instruction = (
        f"Run /compact before continuing to {next_stage}."
        if should_compact
        else f"Continue to {next_stage}; compact is not required."
    )
    return {"recommend_compact": should_compact, "reason": reason, "instruction": instruction}
