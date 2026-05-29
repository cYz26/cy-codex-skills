from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALLOWED_OPERATIONS = {
    "hook_install",
    "mcp_profile_toggle",
    "agents_extract_section",
    "skill_locality",
    "command_policy",
}

SURFACE_OPERATIONS = {
    "profiles": ("mcp_profile_toggle", ".context-fixer/remediation/profile-suggestions.toml"),
    "mcp": ("mcp_profile_toggle", ".context-fixer/remediation/mcp-profile-suggestions.toml"),
    "agents": ("agents_extract_section", ".context-fixer/remediation/agents-slimming.md"),
    "skills": ("skill_locality", ".context-fixer/remediation/skill-locality.md"),
    "hooks": ("hook_install", ".context-fixer/remediation/hook-guardrails.md"),
    "commands": ("command_policy", ".context-fixer/remediation/command-output-policy.md"),
}


class RemediationError(ValueError):
    pass


def build_remediation_plan(report: dict[str, Any], repo: Path) -> dict[str, Any]:
    operations = []
    seen_targets: set[tuple[str, str]] = set()
    for index, recommendation in enumerate((report.get("governance") or {}).get("recommendations") or [], start=1):
        surface = str(recommendation.get("surface") or "")
        if surface not in SURFACE_OPERATIONS:
            continue
        operation_type, target_path = SURFACE_OPERATIONS[surface]
        key = (operation_type, target_path)
        if key in seen_targets:
            continue
        seen_targets.add(key)
        operations.append(
            {
                "id": f"op-{index}",
                "type": operation_type,
                "surface": surface,
                "title": recommendation.get("title"),
                "reason": recommendation.get("reason"),
                "action": recommendation.get("action"),
                "target_path": target_path,
                "content": operation_content(recommendation, operation_type),
            }
        )
    return {
        "version": 1,
        "repo": str(repo.expanduser().resolve()),
        "dry_run": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "operations": operations,
        "privacy": {
            "omits_bodies": True,
            "note": "Plan is derived from sanitized governance recommendations.",
        },
    }


def operation_content(recommendation: dict[str, Any], operation_type: str) -> str:
    lines = [
        f"# {recommendation.get('title') or operation_type}",
        "",
        f"Surface: {recommendation.get('surface') or 'general'}",
        f"Priority: {recommendation.get('priority') or '-'}",
        "",
        "Reason:",
        str(recommendation.get("reason") or ""),
        "",
        "Suggested action:",
        str(recommendation.get("action") or ""),
    ]
    snippet = recommendation.get("snippet")
    if snippet:
        lines.extend(["", "Suggested snippet:", "```", str(snippet), "```"])
    return "\n".join(lines).rstrip() + "\n"


def apply_remediation_plan(plan_path: Path, repo: Path, backup_dir: Path | None = None) -> dict[str, Any]:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    repo_path = repo.expanduser().resolve()
    operations = plan.get("operations") or []
    validated = [validate_operation(operation, repo_path) for operation in operations]
    backup_root = (backup_dir or repo_path / ".context-fixer" / "backups" / timestamp()).expanduser().resolve()
    changes = []
    for operation, target in validated:
        target.parent.mkdir(parents=True, exist_ok=True)
        backup_path = None
        if target.exists():
            backup_path = backup_root / target.relative_to(repo_path)
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup_path)
        target.write_text(str(operation.get("content") or ""), encoding="utf-8")
        changes.append(
            {
                "id": operation.get("id"),
                "type": operation.get("type"),
                "target_path": str(target),
                "backup_path": str(backup_path) if backup_path else None,
                "status": "written",
            }
        )
    return {"applied": True, "changes": changes}


def validate_operation(operation: dict[str, Any], repo: Path) -> tuple[dict[str, Any], Path]:
    operation_type = str(operation.get("type") or "")
    if operation_type not in ALLOWED_OPERATIONS:
        raise RemediationError(f"unsupported operation: {operation_type or 'missing'}")
    target_text = str(operation.get("target_path") or "")
    if not target_text:
        raise RemediationError("unsafe target path: missing")
    target = Path(target_text).expanduser()
    if target.is_absolute():
        resolved = target.resolve()
    else:
        resolved = (repo / target).resolve()
    if resolved != repo and not resolved.is_relative_to(repo):
        raise RemediationError(f"unsafe target path: {target_text}")
    return operation, resolved


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
