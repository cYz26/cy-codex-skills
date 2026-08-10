from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from workflow_paths import as_bool_text, rel, render_template
from workflow_planning_paths import (
    LEGACY_STATE_SUNSET_RELEASE,
    PlanningOwnershipError,
    current_plugin_version,
    atomic_write_devflow,
    guard_devflow_write,
    legacy_state_path,
    state_path,
    version_at_or_after,
)


def parse_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---", 4)
    if end < 0:
        return "", text
    return text[4:end], text[end + 5 :].lstrip("\n")


def parse_state(repo: Path, current_version: str | None = None) -> dict[str, Any]:
    return resolve_state(repo, current_version=current_version)["data"]


def parse_state_text(text: str) -> dict[str, Any]:
    frontmatter, body = parse_frontmatter(text)
    state: dict[str, Any] = {"body": body, "gates": {}}
    parse_yaml_subset(frontmatter, state)
    return state


def resolve_state(repo: Path, current_version: str | None = None) -> dict[str, Any]:
    repo = Path(repo).resolve()
    namespaced = state_path(repo)
    legacy = legacy_state_path(repo)
    version = current_version or current_plugin_version()
    if path_lexists(namespaced):
        if not trusted_repo_regular_file(repo, namespaced):
            return state_resolution(
                "untrusted",
                {},
                namespaced,
                namespaced,
                False,
                next_action="restore_repository_local_state",
            )
        try:
            namespaced_text = namespaced.read_text()
        except (OSError, UnicodeError):
            return state_resolution(
                "unreadable",
                {},
                namespaced,
                namespaced,
                False,
                next_action="restore_readable_repository_state",
            )
        return state_resolution(
            "namespaced",
            parse_state_text(namespaced_text),
            namespaced,
            namespaced,
            True,
        )
    if not path_lexists(legacy):
        return state_resolution("missing", {}, None, namespaced, True)
    if not trusted_repo_regular_file(repo, legacy):
        return state_resolution(
            "untrusted",
            {},
            legacy,
            namespaced,
            False,
            next_action="review_untrusted_legacy_state",
        )
    try:
        text = legacy.read_text()
    except (OSError, UnicodeError):
        return state_resolution(
            "unreadable",
            {},
            legacy,
            namespaced,
            False,
            next_action="review_unreadable_legacy_state",
        )
    frontmatter, _ = parse_frontmatter(text)
    has_devflow = "workflow_version:" in frontmatter
    if has_devflow:
        if version_at_or_after(version, LEGACY_STATE_SUNSET_RELEASE):
            return state_resolution(
                "legacy_expired",
                {},
                legacy,
                namespaced,
                False,
                next_action="migrate_devflow_state",
            )
        return state_resolution(
            "legacy_read_only",
            parse_state_text(text),
            legacy,
            namespaced,
            False,
            next_action="migrate_devflow_state",
        )
    return state_resolution(
        "manual_review_required",
        {},
        legacy,
        namespaced,
        False,
        next_action="review_unknown_root_state",
    )


def state_resolution(
    status: str,
    data: dict[str, Any],
    read_path: Path | None,
    write_path: Path,
    write_allowed: bool,
    *,
    next_action: str = "",
) -> dict[str, Any]:
    return {
        "status": status,
        "data": data,
        "readPath": str(read_path) if read_path else None,
        "writePath": str(write_path),
        "writeAllowed": write_allowed,
        "nextAction": next_action,
        "sunsetRelease": LEGACY_STATE_SUNSET_RELEASE,
    }


def path_lexists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def trusted_repo_regular_file(repo: Path, path: Path) -> bool:
    repo = Path(repo).resolve()
    candidate = Path(path).absolute()
    try:
        relative = candidate.relative_to(repo)
    except ValueError:
        return False
    current = repo
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return False
    return candidate.is_file()


def parse_state_line(state: dict[str, Any], raw_line: str, current_section: Optional[str]) -> Optional[str]:
    line = raw_line.rstrip()
    if not line:
        return current_section
    if line.startswith(("current_change:", "context_management:", "context_health:")):
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
    if value in scalars:
        return scalars[value]
    if value.startswith("[") and value.endswith("]"):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return value
        return parsed if isinstance(parsed, list) else value
    return value


def default_state_values(project_mode: str, change_id: str, change_status: str = "planned") -> dict[str, Any]:
    return {
        "workflow_version": current_plugin_version(),
        "project_mode": project_mode,
        "current_stage": "planning",
        "change_id": change_id,
        "change_status": change_status,
        "plan_written": True,
        "implementation_readiness_required": False,
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
        "goal_gate_required": False,
        "goal_gate_id": "none",
        "goal_gate_status": "not_required",
        "goal_gate_reason": "none",
        "goal_gate_suggested_goal": "none",
        "authority_gate_key": "none",
        "authority_gate_status": "inactive",
        "authority_gate_resolution_digest": "none",
        "authority_gate_evidence_digest": "none",
        "authority_gate_next_question": "none",
        "authority_gate_missing_authority_json": "[]",
        "standing_milestone_status": "inactive",
        "standing_milestone_contract_path": "none",
        "standing_milestone_contract_sha256": "none",
        "standing_milestone_goal_id": "none",
        "standing_milestone_change_id": "none",
        "standing_milestone_candidate_digest": "none",
        "standing_milestone_validation_digest": "none",
        "standing_milestone_review_digest": "none",
    }


def render_state(values: dict[str, Any]) -> str:
    return render_template("STATE.md.template", values)


def write_state(repo: Path, values: dict[str, Any], dry_run: bool = False) -> str:
    path = state_write_path(repo)
    if not dry_run:
        atomic_write_devflow(repo, path, render_state(values))
    return rel(repo, path)


def update_state(repo: Path, **overrides: Any) -> str:
    existing = parse_state(repo)
    values = merged_state_values(existing, overrides)
    text = render_state(values)
    for key, value in merged_gates(existing.get("gates", {}), overrides).items():
        rendered = as_bool_text(value) if isinstance(value, bool) else str(value)
        text = re.sub(rf"  {key}: .*", f"  {key}: {rendered}", text)
    path = state_write_path(repo)
    atomic_write_devflow(repo, path, text)
    return rel(repo, path)


def state_write_path(repo: Path) -> Path:
    resolution = resolve_state(repo)
    path = Path(resolution["writePath"])
    if not resolution["writeAllowed"]:
        status = resolution["status"]
        code = {
            "legacy_read_only": "migration_required",
            "legacy_expired": "migration_required",
            "manual_review_required": "manual_review_required",
        }.get(status, "owner_mismatch")
        raise PlanningOwnershipError(code, path, f"DevFlow state write blocked: {status}")
    guard_devflow_write(repo, path)
    return path


def merged_state_values(existing: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    change = existing.get("current_change", {})
    gates = existing.get("gates", {})
    values = default_state_values(
        str(overrides.get("project_mode", existing.get("project_mode", "brownfield"))),
        str(overrides.get("change_id", change.get("id", "none"))),
        str(overrides.get("change_status", change.get("status", "planned"))),
    )
    values["workflow_version"] = str(
        overrides.get("workflow_version", existing.get("workflow_version", current_plugin_version()))
    )
    values["current_stage"] = str(overrides.get("current_stage", existing.get("current_stage", "planning")))
    values["plan_written"] = bool(overrides.get("plan_written", gates.get("plan_written", True)))
    readiness = existing.get("implementation_readiness", {})
    values["implementation_readiness_required"] = bool(
        overrides.get(
            "implementation_readiness_required",
            readiness.get("required", False) if isinstance(readiness, dict) else False,
        )
    )
    values["status_text"] = str(
        overrides.get(
            "status_text",
            state_body_section(existing, "Current Status") or "Workflow state updated.",
        )
    )
    values["next_action"] = str(
        overrides.get(
            "next_action",
            state_body_section(existing, "Next Action") or "Continue with the active planned task.",
        )
    )
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
    goal_gate = existing.get("goal_gate", {})
    values["goal_gate_id"] = str(overrides.get("goal_gate_id", goal_gate.get("id", "none")))
    values["goal_gate_required"] = bool(
        overrides.get("goal_gate_required", goal_gate.get("required", False))
    )
    values["goal_gate_status"] = str(overrides.get("goal_gate_status", goal_gate.get("status", "not_required")))
    values["goal_gate_reason"] = str(overrides.get("goal_gate_reason", goal_gate.get("reason", "none")))
    values["goal_gate_suggested_goal"] = str(
        overrides.get("goal_gate_suggested_goal", goal_gate.get("suggested_goal", "none"))
    )
    standing = existing.get("standing_milestone", {})
    if not isinstance(standing, dict):
        standing = {}
    for key, fallback in (
        ("status", "inactive"),
        ("contract_path", "none"),
        ("contract_sha256", "none"),
        ("goal_id", "none"),
        ("change_id", "none"),
        ("candidate_digest", "none"),
        ("validation_digest", "none"),
        ("review_digest", "none"),
    ):
        values[f"standing_milestone_{key}"] = str(
            overrides.get(f"standing_milestone_{key}", standing.get(key, fallback))
        )
    authority_gate = existing.get("authority_gate", {})
    if not isinstance(authority_gate, dict):
        authority_gate = {}
    values["authority_gate_key"] = str(
        overrides.get("authority_gate_key", authority_gate.get("key", "none"))
    )
    values["authority_gate_status"] = str(
        overrides.get("authority_gate_status", authority_gate.get("status", "inactive"))
    )
    values["authority_gate_resolution_digest"] = str(
        overrides.get(
            "authority_gate_resolution_digest",
            authority_gate.get("resolution_digest", "none"),
        )
    )
    values["authority_gate_evidence_digest"] = str(
        overrides.get(
            "authority_gate_evidence_digest",
            authority_gate.get("evidence_digest", "none"),
        )
    )
    values["authority_gate_next_question"] = str(
        overrides.get(
            "authority_gate_next_question",
            authority_gate.get("next_question", "none"),
        )
    )
    missing_authority = overrides.get(
        "authority_gate_missing_authority",
        authority_gate.get("missing_authority", []),
    )
    if not isinstance(missing_authority, list):
        missing_authority = []
    values["authority_gate_missing_authority_json"] = json.dumps(
        [str(item) for item in missing_authority],
        ensure_ascii=False,
        separators=(",", ":"),
    )
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
        "release_allowed": False,
    }
    return {key: overrides.get(key, gates.get(key, fallback)) for key, fallback in defaults.items()}


def state_body_section(existing: dict[str, Any], heading: str) -> str:
    body = str(existing.get("body", ""))
    match = re.search(
        rf"^## {re.escape(heading)}\s*\n+(.*?)(?=\n## |\Z)",
        body,
        flags=re.MULTILINE | re.DOTALL,
    )
    return match.group(1).strip() if match else ""
