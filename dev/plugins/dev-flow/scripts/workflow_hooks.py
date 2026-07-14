from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from workflow_constants import CODE_EXTENSIONS, SOURCE_DIRS
from hook_response_adapter import advisory, block_stop_continue
from workflow_mode_routing import read_devflow_config_document
from workflow_state import parse_state


def hook_mode(repo: Path) -> str:
    document = read_devflow_config_document(repo)
    if not document["present"]:
        return "warn"
    if not document["valid"]:
        return "block"
    config = document["data"]
    hook = config.get("hook") if isinstance(config.get("hook"), dict) else {}
    mode = hook.get("mode", "warn")
    return mode if mode in {"off", "warn", "block"} else "warn"


def production_like_path(repo: Path, file_path: str | None) -> bool:
    if not file_path:
        return False
    relative = relative_tool_path(repo, file_path)
    parts = relative.parts
    if not parts:
        return False
    if parts[0] in {".planning", "openspec", "docs", "tests", "test"}:
        return False
    if str(relative) in generated_workflow_files():
        return False
    return relative.suffix in CODE_EXTENSIONS or parts[0] in SOURCE_DIRS


def relative_tool_path(repo: Path, file_path: str) -> Path:
    path = Path(file_path)
    try:
        return path.resolve().relative_to(repo)
    except Exception:
        return path


def generated_workflow_files() -> set[str]:
    return {
        "AGENTS.md",
        "README.md",
        "setup-report.md",
        "workflow-diagnosis.md",
        "repair-plan.md",
    }


def hook_response(
    repo: Path,
    message: str,
    event_name: str = "PreToolUse",
    diagnostic: dict[str, Any] | None = None,
    force_block: bool = False,
) -> int:
    mode = hook_mode(repo)
    if mode == "off":
        return 0
    decision = "block" if force_block or mode == "block" or event_name == "Stop" else "warn"
    payload_diagnostic = hook_diagnostic(repo, event_name, decision, message, diagnostic)
    if event_name == "Stop":
        print(json.dumps(block_stop_continue(message, payload_diagnostic)))
    else:
        print(json.dumps(advisory(event_name, message, payload_diagnostic)))
    return 1 if force_block or mode == "block" else 0


def hook_diagnostic(
    repo: Path,
    hook_name: str,
    decision: str,
    reason: str,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = parse_state(repo)
    gates = state.get("gates", {}) if isinstance(state.get("gates"), dict) else {}
    inferred = infer_hook_action(reason)
    failed_gates = list(inferred.get("failed_gates", []))
    for gate, value in gates.items():
        if value is False and gate not in failed_gates:
            failed_gates.append(gate)
    diagnostic: dict[str, Any] = {
        "hook_name": hook_name,
        "decision": decision,
        "reason": reason,
        "current_stage": state.get("current_stage", "unknown"),
        "failed_gates": failed_gates,
        "next_action": inferred["next_action"],
        "recommended_skill": inferred["recommended_skill"],
        "recommended_command": inferred["recommended_command"],
    }
    if inferred.get("legacy_skill_layout_status"):
        diagnostic["legacy_skill_layout_status"] = inferred["legacy_skill_layout_status"]
    if overrides:
        diagnostic.update(overrides)
    return diagnostic


def infer_hook_action(reason: str) -> dict[str, Any]:
    lowered = reason.lower()
    if "legacy skill layout" in lowered or ".codex/skills" in lowered:
        return {
            "failed_gates": ["legacy_skill_layout"],
            "next_action": "Run the project migration dry-run before applying skill-layout changes.",
            "recommended_skill": "plugin-project-migration",
            "recommended_command": (
                "python3 dev/plugins/dev-flow/scripts/plugin_project_migration.py "
                "--repo <repo> --dry-run --json"
            ),
            "legacy_skill_layout_status": "legacy_detected",
        }
    if "context health" in lowered:
        return {
            "failed_gates": ["context_health"],
            "next_action": "Run context-health-check and reconcile stale or risky context before continuing.",
            "recommended_skill": "context-health-check",
            "recommended_command": (
                "python3 dev/plugins/dev-flow/scripts/context_health_hook.py --event stop --check"
            ),
        }
    if "verification" in lowered or "claiming completion" in lowered:
        return {
            "failed_gates": ["verification_passed"],
            "next_action": "Run verification commands, record evidence, then use verify-and-archive.",
            "recommended_skill": "verify-and-archive",
            "recommended_command": "python3 dev/plugins/dev-flow/scripts/record_verification.py --repo <repo> --json",
        }
    if "archive gate" in lowered or "archive" in lowered:
        return {
            "failed_gates": ["archive_allowed", "verification_passed", "state_updated"],
            "next_action": "Record verification and state evidence, then use verify-and-archive.",
            "recommended_skill": "verify-and-archive",
            "recommended_command": "openspec validate --all --strict",
        }
    if "compact" in lowered or "checkpoint" in lowered:
        return {
            "failed_gates": ["compact_checkpoint"],
            "next_action": "Use checkpoint-compact to create or resolve the pending checkpoint.",
            "recommended_skill": "checkpoint-compact",
            "recommended_command": "python3 dev/plugins/dev-flow/scripts/create_checkpoint.py --repo <repo> --json",
        }
    if "production edit" in lowered or "approved execution" in lowered:
        return {
            "failed_gates": ["spec_approved", "current_stage"],
            "next_action": "Use feature-intake to classify the work and route it before editing production code.",
            "recommended_skill": "feature-intake",
            "recommended_command": "",
        }
    return {
        "failed_gates": [],
        "next_action": "Use project-orchestrator to inspect workflow state and choose the next action.",
        "recommended_skill": "project-orchestrator",
        "recommended_command": "python3 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo <repo> --json",
    }
