from __future__ import annotations

from pathlib import Path
from typing import Optional

from workflow_paths import render_template, repo_path
from workflow_validate import validate_workflow_state
from workflow_constants import resolve_plugin_root
from workflow_stop_scope import stop_hook_protocol_check


def doctor_workflow(
    repo: Path,
    write_report: bool = False,
    *,
    plugin_root: Optional[Path] = None,
    codex_home: Optional[Path] = None,
    check_cache_drift: bool = False,
) -> dict[str, object]:
    repo = repo_path(repo)
    drift_plugin_root = plugin_root
    if check_cache_drift and drift_plugin_root is None:
        drift_plugin_root = resolve_plugin_root()
    validation = validate_workflow_state(
        repo,
        plugin_root=drift_plugin_root,
        codex_home=codex_home,
    )
    stop_hook_protocol = stop_hook_protocol_check()
    issues = validation["issues"] + validation["warnings"] + stop_hook_protocol["issues"]
    recommendations = repair_recommendations(issues)
    status = (
        "healthy"
        if validation["ok"] and not validation["warnings"] and stop_hook_protocol["ok"]
        else "needs repair"
    )
    report = {
        "diagnosis": status,
        "issues": issues,
        "recommendations": recommendations,
        "validation": validation,
        "generatedArtifacts": validation["generatedArtifacts"],
        "stopHookProtocol": stop_hook_protocol,
    }
    if write_report:
        write_doctor_reports(repo, status, issues, recommendations)
    return report


def repair_recommendations(issues: list[str]) -> list[str]:
    if not issues:
        return ["No workflow repair needed."]
    return [f"Repair: {issue}" for issue in issues] + ["Run validate_workflow_state.py after repairs."]


def write_doctor_reports(
    repo: Path,
    status: str,
    issues: list[str],
    recommendations: list[str],
) -> None:
    values = {"status": status, "issues": issues, "recommendations": recommendations}
    (repo / "workflow-diagnosis.md").write_text(render_template("DIAGNOSIS.md.template", values))
    (repo / "repair-plan.md").write_text(render_template("REPAIR_PLAN.md.template", values))
