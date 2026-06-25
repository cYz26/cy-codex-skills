from __future__ import annotations

from pathlib import Path
from typing import Any

from workflow_detect import (
    build_codebase_docs,
    detect_commands,
    detect_project_mode,
    source_areas,
)
from workflow_paths import normalize_project_name, render_template, repo_path
from workflow_state import default_state_values, render_state
from workflow_change import write_change_files
from workflow_contract_control_plane import write_missing_control_plane


class WritePlan:
    def __init__(self, repo: Path, dry_run: bool = False):
        self.repo = repo
        self.dry_run = dry_run
        self.written: list[str] = []
        self.skipped: list[str] = []
        self.planned_writes: list[str] = []

    def write(self, relative: str, content: str, *, force: bool = False) -> None:
        path = self.repo / relative
        self.planned_writes.append(relative)
        if path.exists() and not force:
            self.skipped.append(relative)
            return
        self.written.append(relative)
        if self.dry_run:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


def scaffold_workflow(
    repo: Path,
    mode: str = "auto",
    dry_run: bool = False,
    force_agents: bool = False,
) -> dict[str, Any]:
    repo = repo_path(repo)
    detection = detect_project_mode(repo)
    project_mode = detection["project_mode"] if mode == "auto" else mode
    change_id = "initial-target-state" if project_mode == "greenfield" else "current-system"
    writer = WritePlan(repo, dry_run=dry_run)

    write_base_files(writer, project_mode, force_agents)
    write_phase_files(writer, project_mode)
    write_openspec_base(writer, repo)
    write_change_files(writer, project_mode, change_id, setup_change_title(project_mode))
    if project_mode == "brownfield":
        write_brownfield_files(writer, repo)
    write_setup_state_and_report(writer, detection, project_mode, change_id)

    return {
        "dry_run": dry_run,
        "project_mode": project_mode,
        "detection": detection,
        "planned_writes": writer.planned_writes,
        "written": writer.written,
        "skipped": writer.skipped,
    }


def write_base_files(writer: WritePlan, project_mode: str, force_agents: bool) -> None:
    agents = render_template("AGENTS.md.template", {"project_mode": project_mode})
    target = "AGENTS.md.generated" if (writer.repo / "AGENTS.md").exists() and not force_agents else "AGENTS.md"
    writer.write(target, agents, force=force_agents)
    for item in write_missing_control_plane(writer.repo, dry_run=True):
        writer.write(item["path"], render_template(item["template"], {}))
    writer.write(
        ".planning/ROADMAP.md",
        render_template("ROADMAP.md.template", {"project_mode": project_mode}),
    )


def write_phase_files(writer: WritePlan, project_mode: str) -> None:
    values = {"project_mode": project_mode, "phase_id": "01-foundation"}
    writer.write(
        ".planning/phases/01-foundation/CONTEXT.md",
        render_template("PHASE_CONTEXT.md.template", values),
    )
    writer.write(
        ".planning/phases/01-foundation/PLAN.md",
        render_template("PHASE_PLAN.md.template", values),
    )
    writer.write(
        ".planning/phases/01-foundation/SUMMARY.md",
        render_template("PHASE_SUMMARY.md.template", values),
    )
    writer.write(
        ".planning/phases/01-foundation/VERIFICATION.md",
        render_template("VERIFICATION.md.template", {}),
    )


def write_openspec_base(writer: WritePlan, repo: Path) -> None:
    writer.write(
        "openspec/config.yaml",
        render_template("OPENSPEC_CONFIG.yaml.template", {"project_name": normalize_project_name(repo)}),
    )
    writer.write("openspec/specs/README.md", "# Specs\n\nCurrent behavior facts live here.\n")


def setup_change_title(project_mode: str) -> str:
    return "Initial Target State" if project_mode == "greenfield" else "Current System Baseline"


def write_brownfield_files(writer: WritePlan, repo: Path) -> None:
    for filename, content in build_codebase_docs(repo).items():
        writer.write(f".planning/codebase/{filename}", content)
    writer.write("openspec/specs/current-system/spec.md", current_system_spec(repo))


def current_system_spec(repo: Path) -> str:
    commands = "\n".join(f"- `{command}`" for command in detect_commands(repo))
    return render_template(
        "CURRENT_SYSTEM_SPEC.md.template",
        {
            "commands": commands or "- No commands detected",
            "source_areas": "\n".join(f"- {item}" for item in source_areas(repo)),
        },
    )


def write_setup_state_and_report(
    writer: WritePlan,
    detection: dict[str, Any],
    project_mode: str,
    change_id: str,
) -> None:
    state_values = default_state_values(project_mode, change_id)
    writer.write(".planning/STATE.md", render_state(state_values), force=True)
    writer.write(
        "setup-report.md",
        render_template(
            "SETUP_REPORT.md.template",
            setup_report_values(writer, detection, project_mode, change_id),
        ),
        force=True,
    )


def setup_report_values(
    writer: WritePlan,
    detection: dict[str, Any],
    project_mode: str,
    change_id: str,
) -> dict[str, Any]:
    return {
        "project_mode": project_mode,
        "recommended_flow": detection["recommended_flow"],
        "written": writer.written if writer.written else ["No files written"],
        "skipped": writer.skipped if writer.skipped else ["No files skipped"],
        "risks": ["Review generated specs before implementation."],
        "next_action": f"Review `{change_id}` and run workflow validation.",
    }
