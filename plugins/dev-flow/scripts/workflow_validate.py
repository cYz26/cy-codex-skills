from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from plugin_preflight_hooks import hook_cache_drift_issues
from workflow_compact_state import check_compact_state
from workflow_paths import repo_path
from workflow_state import parse_state


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
    state = read_state_or_issue(repo, issues)
    check_phase(repo, state, issues)
    check_change(repo, state, issues, warnings)
    check_compact_state(repo, state, issues, warnings)
    check_hook_cache_drift(issues, plugin_root=plugin_root, codex_home=codex_home)
    check_archive_gate(state, issues)
    return {
        "ok": not issues,
        "issues": issues,
        "warnings": warnings,
        "state": state,
        "gates": state.get("gates", {}),
    }


def check_required_roots(repo: Path, issues: list[str]) -> None:
    if not ((repo / "AGENTS.md").exists() or (repo / "AGENTS.md.generated").exists()):
        issues.append("Missing AGENTS.md or AGENTS.md.generated")
    if not (repo / "openspec" / "config.yaml").exists():
        issues.append("Missing openspec/config.yaml")


def read_state_or_issue(repo: Path, issues: list[str]) -> dict[str, Any]:
    if not (repo / ".planning" / "STATE.md").exists():
        issues.append("Missing .planning/STATE.md")
        return {}
    return parse_state(repo)


def check_phase(repo: Path, state: dict[str, Any], issues: list[str]) -> None:
    phase_id = state.get("current_phase", {}).get("id")
    if phase_id in (None, "none"):
        return
    if not (repo / ".planning" / "phases" / str(phase_id) / "PLAN.md").exists():
        issues.append(f"Current phase `{phase_id}` is missing PLAN.md")


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


def archive_requirements_met(gates: dict[str, Any]) -> bool:
    keys = (
        "spec_approved",
        "plan_written",
        "implementation_done",
        "verification_passed",
        "state_updated",
    )
    return all(bool(gates.get(key)) for key in keys)


def check_hook_cache_drift(
    issues: list[str],
    *,
    plugin_root: Optional[Path] = None,
    codex_home: Optional[Path] = None,
) -> None:
    if plugin_root is None and codex_home is None:
        return
    root = plugin_root or Path(__file__).resolve().parents[1]
    issues.extend(hook_cache_drift_issues(root, codex_home=codex_home))
