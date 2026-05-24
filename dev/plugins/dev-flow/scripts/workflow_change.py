from __future__ import annotations

from pathlib import Path
from typing import Any

from workflow_detect import detect_project_mode
from workflow_paths import render_template, repo_path
from workflow_state import parse_state, update_state


def change_values(project_mode: str, change_id: str, title: str, change_type: str = "setup") -> dict[str, Any]:
    return {
        "title": title,
        "why": "Initialize a safe baseline for Codex-managed project work.",
        "what": "Create workflow state, planning files, OpenSpec artifacts, and verification gates.",
        "project_mode": project_mode,
        "change_type": change_type,
        "change_id": change_id,
    }


def write_change_files(writer: Any, project_mode: str, change_id: str, title: str) -> None:
    write_change_artifacts(writer, change_id, change_values(project_mode, change_id, title))


def write_change_artifacts(writer: Any, change_id: str, values: dict[str, Any]) -> None:
    for filename, template in change_templates().items():
        writer.write(
            f"openspec/changes/{change_id}/{filename.format(change_id=change_id)}",
            render_template(template, values),
        )


def change_templates() -> dict[str, str]:
    return {
        "proposal.md": "OPENSPEC_PROPOSAL.md.template",
        "design.md": "OPENSPEC_DESIGN.md.template",
        "tasks.md": "OPENSPEC_TASKS.md.template",
        "specs/{change_id}/spec.md": "OPENSPEC_SPEC.md.template",
    }


def create_change(
    repo: Path,
    change_id: str,
    title: str,
    change_type: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    from workflow_scaffold import WritePlan

    repo = repo_path(repo)
    project_mode = active_project_mode(repo)
    writer = WritePlan(repo, dry_run=dry_run)
    write_change_files_for_request(writer, project_mode, change_id, title, change_type)
    if not dry_run:
        update_state_for_change(repo, project_mode, change_id)
    return {
        "dry_run": dry_run,
        "change_id": change_id,
        "written": writer.written,
        "skipped": writer.skipped,
    }


def active_project_mode(repo: Path) -> str:
    state = parse_state(repo)
    return str(state.get("project_mode", detect_project_mode(repo)["project_mode"]))


def write_change_files_for_request(
    writer: Any,
    project_mode: str,
    change_id: str,
    title: str,
    change_type: str,
) -> None:
    values = change_values(project_mode, change_id, title, change_type)
    values["why"] = f"Implement the requested {change_type} safely through OpenSpec."
    values["what"] = f"Plan and verify `{change_id}` before implementation."
    write_change_artifacts(writer, change_id, values)


def update_state_for_change(repo: Path, project_mode: str, change_id: str) -> None:
    update_state(
        repo,
        project_mode=project_mode,
        current_stage="planning",
        change_id=change_id,
        change_status="planned",
        plan_written=True,
        verification_passed=False,
        implementation_done=False,
        archive_allowed=False,
        status_text=f"Change `{change_id}` has planning artifacts.",
        next_action=f"Review and approve `{change_id}` before executing tasks.",
    )
