from __future__ import annotations

from pathlib import Path
from typing import Any

from workflow_compact import record_compact_result
from workflow_compact_options import clean_text
from workflow_paths import repo_path
from workflow_state import parse_state


def handle_compact_recovery_event(repo: Path, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    repo = repo_path(repo)
    event = normalize_event(event_type)
    if event != "post_compact":
        return no_op("unsupported_event")
    return record_post_compact(repo, payload)


def record_post_compact(repo: Path, payload: dict[str, Any]) -> dict[str, Any]:
    trigger = clean_text(payload.get("trigger"))
    if trigger != "manual":
        return no_op("ignored_trigger")
    state = parse_state(repo)
    context = state.get("context_management", {})
    if context.get("compact_status") != "pending":
        return no_op("state_not_pending")
    checkpoint = current_checkpoint(repo, context)
    if checkpoint["issues"]:
        return no_op("checkpoint_unavailable", checkpoint["issues"])
    report = record_compact_result(
        repo,
        {
            "status": "completed",
            "source": "cli",
            "checkpoint": checkpoint["checkpoint_file"],
            "raw_result": post_compact_summary(payload),
        },
    )
    if not report.get("ok"):
        return {
            "ok": False,
            "action": "record_failed",
            "issues": report.get("issues", []),
        }
    return {
        "ok": True,
        "action": "compact_completed",
        "checkpoint_id": checkpoint["checkpoint_id"],
        "compact_result_file": report.get("compact_result_file"),
    }


def current_checkpoint(repo: Path, context: dict[str, Any]) -> dict[str, Any]:
    checkpoint_id = clean_text(context.get("last_checkpoint_id"))
    checkpoint_file = clean_text(context.get("last_checkpoint_file"))
    issues: list[str] = []
    if not checkpoint_id:
        issues.append("STATE.md has no last checkpoint id")
    if not checkpoint_file:
        issues.append("STATE.md has no last checkpoint file")
    checkpoint_path = (repo / checkpoint_file) if checkpoint_file else None
    if checkpoint_path and not checkpoint_path.exists():
        issues.append(f"Checkpoint file does not exist: {checkpoint_file}")
    return {
        "checkpoint_id": checkpoint_id,
        "checkpoint_file": checkpoint_file,
        "issues": issues,
    }


def post_compact_summary(payload: dict[str, Any]) -> str:
    fields = {
        "event": clean_text(payload.get("hook_event_name")) or "PostCompact",
        "trigger": clean_text(payload.get("trigger")) or "manual",
        "session_id": clean_text(payload.get("session_id")),
        "turn_id": clean_text(payload.get("turn_id")),
        "model": clean_text(payload.get("model")),
    }
    return "DevFlow PostCompact hook recorded compact completion: " + ", ".join(
        f"{key}={value}" for key, value in fields.items() if value
    )


def normalize_event(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def no_op(action: str, issues: list[str] | None = None) -> dict[str, Any]:
    return {"ok": True, "action": action, "issues": issues or []}
