from __future__ import annotations

from pathlib import Path
from typing import Any

from workflow_context_action_handlers import execute_action


def apply_context_tool_actions(
    report: dict[str, Any],
    action_ids: list[str] | None = None,
    all_safe: bool = False,
    apply: bool = False,
    timestamp: str | None = None,
) -> dict[str, Any]:
    missing = missing_action_ids(report.get("actions", []), action_ids or [])
    if missing:
        return {"ok": False, "dryRun": not apply, "applied": [], "errors": [unknown_actions_error(missing)]}
    selected = select_actions(report.get("actions", []), action_ids or [], all_safe)
    if not selected:
        return {"ok": False, "dryRun": not apply, "applied": [], "errors": ["no actions selected"]}
    return run_selected_actions(selected, apply, timestamp)


def run_selected_actions(selected: list[dict[str, Any]], apply: bool, timestamp: str | None) -> dict[str, Any]:
    backups: dict[Path, Path] = {}
    results = []
    errors = []
    for action in selected:
        try:
            results.append(execute_action(action, backups, timestamp) if apply else dry_run_action(action))
        except Exception as exc:
            errors.append(f"{action['id']}: {exc}")
    return {
        "ok": not errors,
        "dryRun": not apply,
        "applied": results,
        "errors": errors,
        "backups": [str(path) for path in backups.values()],
    }


def unknown_actions_error(missing: list[str]) -> str:
    return f"unknown actions: {', '.join(missing)}"


def dry_run_action(action: dict[str, Any]) -> dict[str, Any]:
    return {"id": action["id"], "type": action["type"], "status": "dry-run"}


def missing_action_ids(actions: list[dict[str, Any]], action_ids: list[str]) -> list[str]:
    available = {action["id"] for action in actions}
    return sorted(set(action_ids) - available)


def select_actions(actions: list[dict[str, Any]], action_ids: list[str], all_safe: bool) -> list[dict[str, Any]]:
    selected_ids = set(action_ids)
    selected = []
    for action in actions:
        if action["id"] in selected_ids or (all_safe and action.get("safety") == "safe"):
            selected.append(action)
    return selected
