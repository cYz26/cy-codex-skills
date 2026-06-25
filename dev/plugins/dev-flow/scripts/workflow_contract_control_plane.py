from __future__ import annotations

from pathlib import Path
from typing import Any

from workflow_paths import render_template, repo_path


CONTROL_PLANE_TEMPLATES = {
    "ENGINEERING_POLICY.md": "ENGINEERING_POLICY.md.template",
    "TASK_LEDGER.md": "TASK_LEDGER.md.template",
    "EVIDENCE_TEMPLATE.md": "EVIDENCE_TEMPLATE.md.template",
    "REVIEW_CHECKLIST.md": "REVIEW_CHECKLIST.md.template",
}


def control_plane_status(repo: Path) -> dict[str, Any]:
    repo = repo_path(repo)
    missing = [path for path in CONTROL_PLANE_TEMPLATES if not (repo / path).exists()]
    return {
        "status": "current" if not missing else "missing",
        "requiredFiles": sorted(CONTROL_PLANE_TEMPLATES),
        "missingFiles": missing,
    }


def write_missing_control_plane(repo: Path, dry_run: bool = False) -> list[dict[str, Any]]:
    repo = repo_path(repo)
    changes: list[dict[str, Any]] = []
    for relative, template in CONTROL_PLANE_TEMPLATES.items():
        path = repo / relative
        if path.exists():
            continue
        changes.append({"kind": "control-plane-file", "path": relative, "template": template})
        if dry_run:
            continue
        path.write_text(render_template(template, {}))
    return changes


def parse_goal_contract(text: str) -> dict[str, str]:
    contract: dict[str, str] = {}
    in_contract = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            in_contract = line.lower() == "## goal contract"
            continue
        if not in_contract or not line.startswith("- ") or ":" not in line:
            continue
        key, value = line[2:].split(":", 1)
        contract[key.strip()] = value.strip()
    return contract


def validate_goal_contract(repo: Path) -> dict[str, Any]:
    repo = repo_path(repo)
    ledger = repo / "TASK_LEDGER.md"
    if not ledger.exists():
        return {"ok": False, "errors": ["missing TASK_LEDGER.md"], "goal": {}}
    goal = parse_goal_contract(ledger.read_text())
    required = [
        "goal_id",
        "objective",
        "scope_in",
        "scope_out",
        "acceptance_criteria",
        "validation_commands",
        "knowledge_update_target",
    ]
    missing = [key for key in required if not goal.get(key)]
    return {"ok": not missing, "errors": [f"missing {key}" for key in missing], "goal": goal}


def parse_task_rows(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    headers: list[str] = []
    in_tasks = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            in_tasks = line.lower() == "## tasks"
            continue
        if not in_tasks or not line.startswith("|") or "---" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not headers:
            headers = cells
            continue
        if len(cells) != len(headers):
            continue
        rows.append(dict(zip(headers, cells)))
    return rows


def validate_task_ledger(repo: Path) -> dict[str, Any]:
    repo = repo_path(repo)
    ledger = repo / "TASK_LEDGER.md"
    if not ledger.exists():
        return {"ok": False, "errors": ["missing TASK_LEDGER.md"], "tasks": []}
    tasks = parse_task_rows(ledger.read_text())
    required = ["task_id", "summary", "owner", "write_set", "required_evidence", "review_gate", "status"]
    errors: list[str] = []
    if not tasks:
        errors.append("missing task rows")
    for index, task in enumerate(tasks, start=1):
        for key in required:
            if not task.get(key):
                errors.append(f"task {index} missing {key}")
    return {"ok": not errors, "errors": errors, "tasks": tasks}
