from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from workflow_paths import repo_path
from workflow_dependency_catalog import (
    LEGACY_OPENSPEC_SKILLS,
    PROJECT_ORCHESTRATOR_SKILLS,
    REQUIRED_GSD_SKILLS,
    REQUIRED_SUPERPOWERS_PROJECT_SKILLS,
)
from workflow_project_skill_paths import migrate_project_skill_layout
from workflow_project_skill_install import ensure_project_local_skills
from workflow_constants import resolve_plugin_root
from workflow_dependency_provenance import dependency_install_command, dependency_provenance_source_path


def activate_project_dependencies(
    repo: Path,
    dry_run: bool = False,
    skip_official_installs: bool = False,
    plugin_root: Path | None = None,
    codex_home: Path | None = None,
    refresh_project_skills: bool = False,
    migrate_official_skill_layout: bool = False,
    apply_skill_layout_migration: bool = False,
) -> dict[str, Any]:
    repo = repo_path(repo)
    plugin_root = repo_path(plugin_root or resolve_plugin_root())
    codex_home = repo_path(codex_home or Path.home() / ".codex")
    commands = official_install_command_records(repo, plugin_root)
    command_results = []
    if not skip_official_installs:
        for command in commands:
            command_results.append(run_command(command["command"], repo, dry_run, command.get("provenanceSource")))
    skill_layout_migration = None
    if migrate_official_skill_layout:
        skill_layout_migration = migrate_project_skill_layout(
            repo,
            managed_project_skills(),
            dry_run=not apply_skill_layout_migration,
            script_path=Path(__file__).resolve(),
        )
    skills_result = ensure_project_local_skills(repo, plugin_root, codex_home, dry_run, refresh_project_skills)
    migration_ok = skill_layout_migration is None or skill_layout_migration["ok"]
    return {
        "ok": all(item["ok"] for item in command_results) and migration_ok and skills_result["ok"],
        "repo": str(repo),
        "plugin_root": str(plugin_root),
        "codex_home": str(codex_home),
        "dry_run": dry_run,
        "skip_official_installs": skip_official_installs,
        "refresh_project_skills": refresh_project_skills,
        "migrate_official_skill_layout": migrate_official_skill_layout,
        "apply_skill_layout_migration": apply_skill_layout_migration,
        "commands": command_results,
        "local_skills": skills_result,
        "skill_layout_migration": skill_layout_migration,
    }


def official_install_commands(repo: Path) -> list[list[str]]:
    return [item["command"] for item in official_install_command_records(repo)]


def official_install_command_records(repo: Path, plugin_root: Path | None = None) -> list[dict[str, Any]]:
    provenance_source = str(dependency_provenance_source_path(plugin_root))
    return [
        {"command": ["openspec", "init", "--tools", "codex", "--profile", "core", str(repo), "--force"]},
        {
            "command": dependency_install_command("gsd-core", plugin_root),
            "provenanceSource": provenance_source,
        },
    ]


def managed_project_skills() -> list[str]:
    return [
        *PROJECT_ORCHESTRATOR_SKILLS,
        *REQUIRED_SUPERPOWERS_PROJECT_SKILLS,
        *REQUIRED_GSD_SKILLS,
        *LEGACY_OPENSPEC_SKILLS,
    ]


def run_command(command: list[str], repo: Path, dry_run: bool, provenance_source: str | None = None) -> dict[str, Any]:
    if dry_run:
        result = {"ok": True, "command": command, "skipped": True}
        if provenance_source:
            result["provenanceSource"] = provenance_source
        return result
    try:
        result = subprocess.run(command, cwd=repo, text=True, capture_output=True, check=False)
    except FileNotFoundError:
        output = {"ok": False, "command": command, "error": f"missing executable: {command[0]}"}
        if provenance_source:
            output["provenanceSource"] = provenance_source
        return output
    output = {
        "ok": result.returncode == 0,
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    if provenance_source:
        output["provenanceSource"] = provenance_source
    return output
