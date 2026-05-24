from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from workflow_compact_policy import recommend_compact
from workflow_git import git_branch, git_changed_files
from workflow_paths import rel, render_template, repo_path
from workflow_state import parse_state, update_state


def create_checkpoint(repo: Path, options: dict[str, Any]) -> dict[str, Any]:
    repo = repo_path(repo)
    state = parse_state(repo)
    phase_id = option_or_state(options, state, "phase", "current_phase")
    change_id = option_or_state(options, state, "change", "current_change")
    checkpoint_file = unique_checkpoint_file(
        repo,
        build_checkpoint_id(options["boundary"], change_id),
        options.get("output"),
    )
    values = checkpoint_values(repo, state, options, checkpoint_file, phase_id, change_id)
    if not options.get("dry_run"):
        write_checkpoint(repo, checkpoint_file, values, options, state)
    return checkpoint_report(repo, checkpoint_file, values, options)


def write_checkpoint(
    repo: Path,
    checkpoint_file: Path,
    values: dict[str, Any],
    options: dict[str, Any],
    state: dict[str, Any],
) -> None:
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_file.write_text(render_template("CHECKPOINT.md.template", values))
    update_state(
        repo,
        last_checkpoint_id=checkpoint_file.stem,
        last_checkpoint_file=rel(repo, checkpoint_file),
        compact_recommended=values["compact_recommended"],
        compact_status=values["compact_status"],
        current_stage=options.get("next_stage", state.get("current_stage", "planning")),
    )


def checkpoint_report(
    repo: Path,
    checkpoint_file: Path,
    values: dict[str, Any],
    options: dict[str, Any],
) -> dict[str, Any]:
    return {
        "dry_run": bool(options.get("dry_run")),
        "checkpoint_id": checkpoint_file.stem,
        "checkpoint_file": rel(repo, checkpoint_file),
        "compact_recommended": values["compact_recommended"],
        "compact_status": values["compact_status"],
        "next_stage": values["next_stage"],
    }


def option_or_state(options: dict[str, Any], state: dict[str, Any], option_key: str, state_key: str) -> str:
    value = options.get(option_key)
    if value:
        return str(value)
    return str(state.get(state_key, {}).get("id", "none"))


def build_checkpoint_id(boundary: str, change_id: str) -> str:
    date = datetime.now().astimezone().strftime("%Y-%m-%d")
    suffix = checkpoint_suffix(change_id)
    return f"{date}-{slugify(boundary)}-{suffix}"


def checkpoint_suffix(change_id: str) -> str:
    return slugify(change_id) if change_id not in ("", "none") else "project"


def unique_checkpoint_file(repo: Path, checkpoint_id: str, output: str | None = None) -> Path:
    root = repo / checkpoint_output(output)
    candidate = root / f"{checkpoint_id}.md"
    counter = 2
    while candidate.exists():
        candidate = root / f"{checkpoint_id}-{counter}.md"
        counter += 1
    return candidate


def checkpoint_output(output: str | None) -> str:
    return output if output else ".planning/checkpoints"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-")
    return slug if slug else "checkpoint"


def checkpoint_values(
    repo: Path,
    state: dict[str, Any],
    options: dict[str, Any],
    checkpoint_file: Path,
    phase_id: str,
    change_id: str,
) -> dict[str, Any]:
    boundary = options["boundary"]
    compact = recommend_compact(boundary)
    return {
        "checkpoint_id": checkpoint_file.stem,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "boundary": boundary,
        "project_mode": state.get("project_mode", "unknown"),
        "phase_id": phase_id,
        "change_id": change_id,
        "compact_recommended": compact,
        "compact_status": "pending" if compact else "not_needed",
        "next_stage": options.get("next_stage", "next_stage"),
        "title": title_for_boundary(boundary, change_id),
        "current_goal": options.get("current_goal", "Not recorded."),
        "completed_work": list_block(options.get("completed_work"), "No completed work recorded."),
        "durable_context": list_block(durable_context(repo, phase_id, change_id), "No durable context found."),
        "key_decisions": list_block(options.get("decisions"), "No key decisions recorded."),
        "open_questions": list_block(options.get("open_questions"), "No open questions recorded."),
        "risks": list_block(options.get("risks"), "No risks recorded."),
        "validation_command": options.get("validation_command", "not-run"),
        "validation_result": options.get("validation_result", "not-run"),
        "validation_notes": options.get("validation_notes", "No validation notes recorded."),
        "git_branch": git_branch(repo),
        "changed_files": git_changed_files(repo),
    }


def list_block(items: list[str] | None, fallback: str) -> str:
    source = items if items else []
    values = [item for item in source if item]
    return "\n".join(f"- {item}" for item in values) if values else f"- {fallback}"


def durable_context(repo: Path, phase_id: str, change_id: str) -> list[str]:
    candidates = [
        "AGENTS.md",
        ".planning/STATE.md",
        f".planning/phases/{phase_id}/PLAN.md",
        f".planning/phases/{phase_id}/SUMMARY.md",
        f".planning/phases/{phase_id}/VERIFICATION.md",
        f"openspec/changes/{change_id}/proposal.md",
        f"openspec/changes/{change_id}/design.md",
        f"openspec/changes/{change_id}/tasks.md",
    ]
    return [path for path in candidates if (repo / path).exists()]


def title_for_boundary(boundary: str, change_id: str) -> str:
    suffix = f" for {change_id}" if change_id not in ("", "none") else ""
    return f"{boundary.replace('_', ' ')}{suffix}"
