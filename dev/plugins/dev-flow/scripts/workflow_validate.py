from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from plugin_preflight_hooks import hook_cache_drift_issues
from workflow_compact_state import check_compact_state
from workflow_constants import resolve_plugin_root
from workflow_goal_gate import goal_gate_warning
from workflow_generated_artifacts import inspect_generated_artifact_lifecycle
from workflow_implementation_readiness import (
    IMPLEMENTATION_PROVIDER_READY,
    ReadinessError,
    inspect_repository_readiness,
)
from workflow_mode_routing import read_workflow_mode_config
from workflow_paths import repo_path
from workflow_state import parse_state, resolve_state


def validate_workflow_state(
    repo: Path,
    *,
    plugin_root: Optional[Path] = None,
    codex_home: Optional[Path] = None,
) -> dict[str, Any]:
    repo = repo_path(repo)
    issues: list[str] = []
    warnings: list[str] = []
    check_required_roots(repo, issues)
    check_agents_guidance(repo, issues, warnings)
    state = read_state_or_issue(repo, issues, warnings)
    check_workflow_config(repo, issues)
    check_change(repo, state, issues, warnings)
    check_compact_state(repo, state, issues, warnings)
    check_goal_gate(state, warnings)
    implementation_readiness = check_implementation_readiness(repo, state, issues, warnings)
    check_hook_cache_drift(issues, plugin_root=plugin_root, codex_home=codex_home)
    check_archive_gate(state, issues)
    generated_artifacts = inspect_generated_artifact_lifecycle(repo)
    check_generated_artifacts(generated_artifacts, issues, warnings)
    return {
        "ok": not issues,
        "issues": issues,
        "warnings": warnings,
        "state": state,
        "gates": state.get("gates", {}),
        "generatedArtifacts": generated_artifacts,
        "implementationReadiness": implementation_readiness,
    }


def check_required_roots(repo: Path, issues: list[str]) -> None:
    if not ((repo / "AGENTS.md").exists() or (repo / "AGENTS.md.generated").exists()):
        issues.append("Missing AGENTS.md or AGENTS.md.generated")
    if not (repo / "openspec" / "config.yaml").exists():
        issues.append("Missing openspec/config.yaml")


def check_agents_guidance(repo: Path, issues: list[str], warnings: list[str]) -> None:
    agents_path = repo / "AGENTS.md"
    generated_path = repo / "AGENTS.md.generated"
    active_path = agents_path if agents_path.exists() else generated_path
    if not active_path.exists():
        return

    text = active_path.read_text()
    missing = missing_agents_guidance(text)
    if missing:
        detail = ", ".join(missing)
        if active_path == agents_path and generated_path.exists():
            issues.append(
                "AGENTS.md.generated exists but active AGENTS.md is missing "
                f"DevFlow workflow guidance ({detail}); merge AGENTS.md.generated "
                "into AGENTS.md or rerun scaffold_workflow.py with --force-agents after review"
            )
        else:
            warnings.append(f"{active_path.name} is missing DevFlow workflow guidance: {detail}")

    if contains_slice_specific_agents_boundary(text):
        warnings.append(
            f"{active_path.name} contains a First Slice Boundary-style section; "
            "move current implementation boundaries into the active OpenSpec change "
            "and keep AGENTS.md focused on durable workflow rules"
        )


def missing_agents_guidance(text: str) -> list[str]:
    required_markers = {
        "Workflow Ownership": "## Workflow Ownership",
        "Project Control Plane": "## Project Control Plane",
        "Capability Routing": "## Capability Routing",
        "Intake and Planning": "## Intake and Planning",
        "Project-Directed Implementation Readiness": "## Project-Directed Implementation Readiness",
        "Goal Workflow": "## Goal Workflow",
        "AI Coding Planning Rules": "AI Coding Planning Rules",
        "Target State": "Target State",
        "Completion Contract": "Completion Contract",
        "Capability Slices": "Capability Slices",
        "Execution Ledger": "Execution Ledger",
        "Acceptance Criteria": "Acceptance Criteria",
        "Validation Commands": "Validation Commands",
        "Final Verification": "Final Verification",
        "Full OpenSpec routing": "Full OpenSpec",
        "Matt methodology contract": "Matt",
        "bounded subagent contract": "Agent Task Contract",
        "canonical artifact guidance": "canonical",
        "Workflow Mode Routing": "## Workflow Mode Routing",
        "Plugin Eval Gate": "## Plugin Eval Gate",
        "Local Reference Update Reminder": "## Local Reference Update Reminder",
        "DevFlow Refresh Workflow": "## DevFlow Refresh Workflow",
    }
    return [label for label, marker in required_markers.items() if marker not in text]


def contains_slice_specific_agents_boundary(text: str) -> bool:
    boundary_headings = (
        "## First Slice Boundary",
        "## Current Slice Boundary",
        "## Implementation Slice Boundary",
    )
    return any(heading in text for heading in boundary_headings)


def read_state_or_issue(
    repo: Path,
    issues: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    resolution = resolve_state(repo)
    if resolution["status"] == "missing":
        issues.append("Missing .planning/devflow/STATE.md")
        return {}
    if resolution["status"] == "legacy_read_only":
        warnings.append(
            "Legacy DevFlow root state is read-only; migrate to .planning/devflow/STATE.md before the 1.0.0 sunset"
        )
        return resolution["data"]
    if resolution["status"] != "namespaced":
        issues.append(
            f"DevFlow state is `{resolution['status']}`; manual migration review is required"
        )
        return resolution["data"]
    return parse_state(repo)


def check_workflow_config(repo: Path, issues: list[str]) -> None:
    config = read_workflow_mode_config(repo)
    if not config.get("valid", True):
        issues.extend(f"Invalid .dev-flow.json: {error}" for error in config.get("config_errors", []))


def check_change(
    repo: Path,
    state: dict[str, Any],
    issues: list[str],
    warnings: list[str],
) -> None:
    change_id = state.get("current_change", {}).get("id")
    if change_id in (None, "none"):
        return
    change_root = repo / "openspec" / "changes" / str(change_id)
    if not change_root.exists():
        issues.append(f"Current change `{change_id}` is missing")
        return
    for filename in ("proposal.md", "tasks.md"):
        if not (change_root / filename).exists():
            issues.append(f"Current change `{change_id}` is missing {filename}")
    if not any((change_root / "specs").rglob("spec.md")):
        warnings.append(f"Current change `{change_id}` has no spec.md under specs/")


def check_archive_gate(state: dict[str, Any], issues: list[str]) -> None:
    gates = state.get("gates", {})
    if bool(gates.get("archive_allowed")) and not archive_requirements_met(gates):
        issues.append("archive_allowed is true but one or more archive gates are false")
    if bool(gates.get("release_allowed")) and not archive_requirements_met(gates):
        issues.append("release_allowed is true but one or more release gates are false")


def archive_requirements_met(gates: dict[str, Any]) -> bool:
    keys = (
        "spec_approved",
        "plan_written",
        "implementation_done",
        "verification_passed",
        "state_updated",
    )
    return all(bool(gates.get(key)) for key in keys)


def check_goal_gate(state: dict[str, Any], warnings: list[str]) -> None:
    warning = goal_gate_warning(state)
    if warning:
        warnings.append(warning)


def check_implementation_readiness(
    repo: Path,
    state: dict[str, Any],
    issues: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    change = state.get("current_change", {})
    change_id = str(change.get("id") or "") if isinstance(change, dict) else ""
    try:
        report = inspect_repository_readiness(repo, change_id or None)
    except ReadinessError as error:
        report = {
            "applicable": True,
            "report": {"state": "IMPLEMENTATION_PROVIDER_NOT_READY", "nextAction": "restore-current-consumer-context"},
            "receiptCurrent": False,
            "issues": [error.code],
        }
    if not report.get("applicable"):
        return report
    readiness = report.get("report") if isinstance(report.get("report"), dict) else {}
    current = bool(
        readiness.get("state") == IMPLEMENTATION_PROVIDER_READY
        and report.get("receiptCurrent")
    )
    if current:
        return report
    message = (
        "Implementation readiness is not current for governed execution: "
        f"state={readiness.get('state', 'unknown')}, "
        f"receiptCurrent={bool(report.get('receiptCurrent'))}, "
        f"nextAction={readiness.get('nextAction', 'inspect-implementation-readiness')}"
    )
    stage = str(state.get("current_stage") or "").strip().lower().replace("-", "_")
    if stage in {"planning", "intake", "research", "draft"}:
        warnings.append(message)
    else:
        issues.append(message)
    return report


def check_hook_cache_drift(
    issues: list[str],
    *,
    plugin_root: Optional[Path] = None,
    codex_home: Optional[Path] = None,
) -> None:
    if plugin_root is None and codex_home is None:
        return
    root = plugin_root or resolve_plugin_root()
    issues.extend(hook_cache_drift_issues(root, codex_home=codex_home))


def check_generated_artifacts(
    report: dict[str, Any],
    issues: list[str],
    warnings: list[str],
) -> None:
    issues.extend(
        f"Generated Artifact Lifecycle: {issue}"
        for issue in report.get("issues", [])
    )
    warnings.extend(
        "Generated Artifact Lifecycle "
        f"`{record['contractId']}` is {record['decision']}: "
        f"{record['nextAction']}"
        for record in report.get("unresolved", [])
    )
