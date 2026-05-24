from __future__ import annotations

from pathlib import Path

from workflow_paths import render_template, repo_path
from workflow_validate import validate_workflow_state


def doctor_workflow(repo: Path, write_report: bool = False) -> dict[str, object]:
    repo = repo_path(repo)
    validation = validate_workflow_state(repo)
    issues = validation["issues"] + validation["warnings"]
    recommendations = repair_recommendations(issues)
    status = "healthy" if validation["ok"] and not validation["warnings"] else "needs repair"
    report = {"diagnosis": status, "issues": issues, "recommendations": recommendations}
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
