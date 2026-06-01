from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

from workflow_paths import as_bool_text, rel, render_template


def parse_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---", 4)
    if end < 0:
        return "", text
    return text[4:end], text[end + 5 :].lstrip("\n")


def parse_state(repo: Path) -> dict[str, Any]:
    path = repo / ".planning" / "STATE.md"
    if not path.exists():
        return {}
    frontmatter, body = parse_frontmatter(path.read_text())
    state: dict[str, Any] = {"body": body, "gates": {}}
    parse_yaml_subset(frontmatter, state)
    return state


def parse_state_line(state: dict[str, Any], raw_line: str, current_section: Optional[str]) -> Optional[str]:
    line = raw_line.rstrip()
    if not line:
        return current_section
    if line.startswith(("current_phase:", "current_change:", "context_management:", "context_health:")):
        section = line.split(":", 1)[0]
        state[section] = {}
        return section
    if line.startswith("gates:"):
        return "gates"
    if line.startswith("  ") and ":" in line and current_section:
        key, value = line.strip().split(":", 1)
        state[current_section][key] = parse_scalar(value.strip())
        return current_section
    if ":" in line:
        key, value = line.split(":", 1)
        state[key] = parse_scalar(value.strip())
    return None


def parse_yaml_subset(frontmatter: str, state: dict[str, Any]) -> None:
    stack: list[tuple[int, Any]] = [(-1, state)]
    pending_key: Optional[tuple[int, dict[str, Any], str]] = None
    for raw_line in frontmatter.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if stripped.startswith("- "):
            if not pending_key:
                continue
            pending_indent, pending_parent, pending_name = pending_key
            if indent <= pending_indent:
                continue
            values = pending_parent.get(pending_name)
            if not isinstance(values, list):
                values = []
                pending_parent[pending_name] = values
            values.append(parse_scalar(stripped[2:].strip()))
            continue
        pending_key = None
        if ":" not in stripped or not isinstance(parent, dict):
            continue
        key, value = stripped.split(":", 1)
        value = value.strip()
        if value:
            parent[key] = parse_scalar(value)
            continue
        child: dict[str, Any] = {}
        parent[key] = child
        stack.append((indent, child))
        pending_key = (indent, parent, key)


def parse_scalar(value: str) -> Any:
    scalars = {"true": True, "false": False, "null": None}
    return scalars.get(value, value)


def default_state_values(project_mode: str, change_id: str, change_status: str = "planned") -> dict[str, Any]:
    return {
        "project_mode": project_mode,
        "current_stage": "planning",
        "phase_id": "01-foundation",
        "change_id": change_id,
        "change_status": change_status,
        "plan_written": True,
        "status_text": f"Workflow initialized for a {project_mode} repository.",
        "next_action": f"Review and approve the `{change_id}` change before implementation.",
        "last_checkpoint_id": "none",
        "last_checkpoint_file": "none",
        "compact_recommended": False,
        "compact_status": "not_needed",
        "last_compact_result_file": "none",
        "compact_source": "none",
        "compact_updated_at": "none",
        "compact_skip_reason": "none",
        "compact_error": "none",
        "last_context_health_report": "none",
        "last_context_health_risk": "unknown",
        "last_context_health_confidence": "unknown",
        "last_context_health_decision": "none",
        "last_goal_status": "unknown",
        "goal_summary": "none",
    }


def render_state(values: dict[str, Any]) -> str:
    return render_template("STATE.md.template", values)


def write_state(repo: Path, values: dict[str, Any], dry_run: bool = False) -> str:
    path = repo / ".planning" / "STATE.md"
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_state(values))
    return rel(repo, path)


def update_state(repo: Path, **overrides: Any) -> str:
    existing = parse_state(repo)
    values = merged_state_values(existing, overrides)
    text = render_state(values)
    for key, value in merged_gates(existing.get("gates", {}), overrides).items():
        text = re.sub(rf"  {key}: (true|false)", f"  {key}: {as_bool_text(bool(value))}", text)
    path = repo / ".planning" / "STATE.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return rel(repo, path)


def merged_state_values(existing: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    phase = existing.get("current_phase", {})
    change = existing.get("current_change", {})
    gates = existing.get("gates", {})
    values = default_state_values(
        str(overrides.get("project_mode", existing.get("project_mode", "brownfield"))),
        str(overrides.get("change_id", change.get("id", "none"))),
        str(overrides.get("change_status", change.get("status", "planned"))),
    )
    values["current_stage"] = str(overrides.get("current_stage", existing.get("current_stage", "planning")))
    values["phase_id"] = str(overrides.get("phase_id", phase.get("id", "01-foundation")))
    values["plan_written"] = bool(overrides.get("plan_written", gates.get("plan_written", True)))
    values["status_text"] = str(overrides.get("status_text", "Workflow state updated."))
    values["next_action"] = str(overrides.get("next_action", "Continue with the active planned task."))
    context = existing.get("context_management", {})
    values["last_checkpoint_id"] = str(overrides.get("last_checkpoint_id", context.get("last_checkpoint_id", "none")))
    values["last_checkpoint_file"] = str(
        overrides.get("last_checkpoint_file", context.get("last_checkpoint_file", "none"))
    )
    values["compact_recommended"] = bool(
        overrides.get("compact_recommended", context.get("compact_recommended", False))
    )
    values["compact_status"] = str(overrides.get("compact_status", context.get("compact_status", "not_needed")))
    values["last_compact_result_file"] = str(
        overrides.get("last_compact_result_file", context.get("last_compact_result_file", "none"))
    )
    values["compact_source"] = str(overrides.get("compact_source", context.get("compact_source", "none")))
    values["compact_updated_at"] = str(
        overrides.get("compact_updated_at", context.get("compact_updated_at", "none"))
    )
    values["compact_skip_reason"] = str(
        overrides.get("compact_skip_reason", context.get("compact_skip_reason", "none"))
    )
    values["compact_error"] = str(overrides.get("compact_error", context.get("compact_error", "none")))
    health = existing.get("context_health", {})
    values["last_context_health_report"] = str(
        overrides.get("last_context_health_report", health.get("last_report", "none"))
    )
    values["last_context_health_risk"] = str(
        overrides.get("last_context_health_risk", health.get("last_risk", "unknown"))
    )
    values["last_context_health_confidence"] = str(
        overrides.get("last_context_health_confidence", health.get("last_confidence", "unknown"))
    )
    values["last_context_health_decision"] = str(
        overrides.get("last_context_health_decision", health.get("last_decision", "none"))
    )
    values["last_goal_status"] = str(overrides.get("last_goal_status", health.get("last_goal_status", "unknown")))
    values["goal_summary"] = str(overrides.get("goal_summary", health.get("goal_summary", "none")))
    return values


def merged_gates(gates: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    defaults = {
        "workflow_initialized": True,
        "spec_approved": False,
        "plan_written": True,
        "tests_baseline_known": False,
        "implementation_done": False,
        "verification_passed": False,
        "state_updated": True,
        "archive_allowed": False,
    }
    return {key: overrides.get(key, gates.get(key, fallback)) for key, fallback in defaults.items()}
