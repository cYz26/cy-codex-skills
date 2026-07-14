from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from workflow_constants import resolve_plugin_root
from workflow_dependency_catalog import (
    LEGACY_OPENSPEC_SKILLS,
    OPENSPEC_WORKFLOW_SKILLS,
    PROJECT_ORCHESTRATOR_SKILLS,
)
from workflow_dependency_provenance import (
    dependency_provenance_record,
    dependency_provenance_source_path,
)
from workflow_methodology import diagnose_methodology, required_matt_skills
from workflow_mode_routing import read_workflow_mode_config
from workflow_paths import repo_path
from workflow_project_skill_install import (
    ensure_project_local_skills,
    verify_generated_openspec_skill_root,
)
from workflow_project_skill_paths import migrate_project_skill_layout
from workflow_side_effect_policy import side_effect_decision


def activate_project_dependencies(
    repo: Path,
    dry_run: bool = False,
    skip_official_installs: bool = False,
    plugin_root: Path | None = None,
    codex_home: Path | None = None,
    refresh_project_skills: bool = False,
    migrate_official_skill_layout: bool = False,
    apply_skill_layout_migration: bool = False,
    authorizations: set[str] | None = None,
    triggered_capabilities: set[str] | None = None,
) -> dict[str, Any]:
    repo = repo_path(repo)
    plugin_root = repo_path(plugin_root or resolve_plugin_root())
    codex_home = repo_path(codex_home or Path.home() / ".codex")
    requested = set(triggered_capabilities or set())
    workflow_config = read_workflow_mode_config(repo)
    if not workflow_config["valid"]:
        return blocked_legacy_config_report(
            repo,
            plugin_root,
            codex_home,
            dry_run,
            skip_official_installs,
            requested,
            workflow_config,
        )

    granted = set(authorizations or set())
    dependency_effect = side_effect_decision(
        plugin_root,
        "dependency.install_update",
        granted,
    )
    writes_blocked = not dry_run and not dependency_effect["authorized"]
    execution_dry_run = dry_run or writes_blocked
    commands = official_install_command_records(repo, plugin_root)
    command_results: list[dict[str, Any]] = []
    openspec_skill_root: Path | None = None
    openspec_generation_managed = False
    openspec_staging_root: Path | None = None
    skill_layout_migration: dict[str, Any] | None = None
    try:
        if not skip_official_installs:
            openspec_generation_managed = True
            generation_result, openspec_skill_root, openspec_staging_root = run_openspec_generation(
                commands[0],
                execution_dry_run,
            )
            command_results.append(generation_result)
        command_ok = all(item["ok"] for item in command_results)
        openspec_record = dependency_provenance_record("openspec-cli", plugin_root)
        skills_result = ensure_project_local_skills(
            repo,
            plugin_root,
            codex_home,
            execution_dry_run,
            refresh_project_skills,
            triggered_capabilities=requested,
            openspec_skill_root=openspec_skill_root,
            openspec_generation_planned=openspec_generation_managed,
            openspec_expected_version=str(openspec_record["expectedVersion"]),
        )
        if migrate_official_skill_layout and skills_result["ok"]:
            required_matt = set(required_matt_skills(requested))
            skill_layout_migration = migrate_project_skill_layout(
                repo,
                managed_project_skills(requested),
                dry_run=execution_dry_run or not apply_skill_layout_migration,
                script_path=Path(__file__).resolve(),
                authoritative_source_skills=required_matt,
            )
        elif migrate_official_skill_layout:
            skill_layout_migration = {
                "ok": False,
                "mode": "skipped",
                "status": "blocked_by_dependency_preflight",
                "items": [],
            }
    finally:
        if openspec_staging_root is not None:
            shutil.rmtree(openspec_staging_root, ignore_errors=True)

    methodology = diagnose_methodology(
        repo,
        requested,
        plugin_root,
        codex_home=codex_home,
    )
    methodology_ready = methodology["ready"] or execution_dry_run
    migration_ok = skill_layout_migration is None or skill_layout_migration["ok"]
    workflow_ready = bool(
        command_ok
        and migration_ok
        and skills_result["ok"]
        and methodology_ready
    )
    activation_ok = bool(workflow_ready and not writes_blocked)
    return {
        "ok": activation_ok,
        "status": (
            "planned"
            if execution_dry_run
            else "applied" if activation_ok else "blocked"
        ),
        "repo": str(repo),
        "plugin_root": str(plugin_root),
        "codex_home": str(codex_home),
        "dry_run": dry_run,
        "skip_official_installs": skip_official_installs,
        "refresh_project_skills": refresh_project_skills,
        "migrate_official_skill_layout": migrate_official_skill_layout,
        "apply_skill_layout_migration": apply_skill_layout_migration,
        "writes_blocked": writes_blocked,
        "side_effects": {"dependency.install_update": dependency_effect},
        "commands": command_results,
        "local_skills": skills_result,
        "skill_layout_migration": skill_layout_migration,
        "workflowConfig": workflow_config,
        "methodology": methodology,
        "triggered_capabilities": sorted(requested),
        "workflowReady": workflow_ready,
    }


def blocked_legacy_config_report(
    repo: Path,
    plugin_root: Path,
    codex_home: Path,
    dry_run: bool,
    skip_official_installs: bool,
    requested: set[str],
    workflow_config: dict[str, Any],
) -> dict[str, Any]:
    return {
        "ok": False,
        "status": "legacy_config_requires_inspection",
        "repo": str(repo),
        "plugin_root": str(plugin_root),
        "codex_home": str(codex_home),
        "dry_run": dry_run,
        "skip_official_installs": skip_official_installs,
        "writes_blocked": True,
        "commands": [],
        "local_skills": {"ok": False, "items": []},
        "workflowConfig": workflow_config,
        "methodology": None,
        "triggered_capabilities": sorted(requested),
        "workflowReady": False,
        "nextAction": "python3 scripts/inspect_legacy_workflow_config.py --repo . --json",
    }


def official_install_commands(
    repo: Path,
) -> list[list[str]]:
    return [item["command"] for item in official_install_command_records(repo)]


def official_install_command_records(
    repo: Path,
    plugin_root: Path | None = None,
) -> list[dict[str, Any]]:
    provenance_source = str(dependency_provenance_source_path(plugin_root))
    openspec_record = dependency_provenance_record("openspec-cli", plugin_root)
    return [isolated_openspec_generation_record(openspec_record, provenance_source)]


def isolated_openspec_generation_record(
    dependency: dict[str, Any],
    provenance_source: str,
) -> dict[str, Any]:
    return {
        "sourceKind": "openspec",
        "kind": "isolated-skill-generation",
        "command": [
            "openspec",
            "init",
            "--tools",
            "codex",
            "--profile",
            "core",
            "{isolatedStagingProject}",
            "--force",
        ],
        "environment": {
            "XDG_CONFIG_HOME": "{isolatedXdgConfigHome}",
            "CODEX_HOME": "{isolatedCodexHome}",
            "OPENSPEC_TELEMETRY": "0",
        },
        "expectedVersion": dependency.get("expectedVersion"),
        "expectedSkills": list(LEGACY_OPENSPEC_SKILLS),
        "isolation": {
            "project": "temporary",
            "xdgConfig": "temporary",
            "codexHome": "temporary",
            "telemetry": "disabled",
            "realGlobalPaths": "excluded",
        },
        "provenanceSource": provenance_source,
    }


def run_openspec_generation(
    record: dict[str, Any],
    dry_run: bool,
) -> tuple[dict[str, Any], Path | None, Path | None]:
    if dry_run:
        return (
            {
                **record,
                "ok": True,
                "skipped": True,
                "generation": {
                    "ok": True,
                    "status": "planned",
                    "expectedVersion": record.get("expectedVersion"),
                    "expectedSkills": list(LEGACY_OPENSPEC_SKILLS),
                },
            },
            None,
            None,
        )

    staging_root = Path(tempfile.mkdtemp(prefix="devflow-openspec-generation-"))
    staging_project = staging_root / "project"
    isolated_xdg = staging_root / "xdg"
    isolated_codex_home = staging_root / "codex-home"
    try:
        staging_project.mkdir()
        isolated_xdg.mkdir()
        isolated_codex_home.mkdir()
    except OSError as exc:
        shutil.rmtree(staging_root, ignore_errors=True)
        generation = {
            "ok": False,
            "status": "staging_setup_failed",
            "expectedVersion": record.get("expectedVersion"),
            "expectedSkills": list(LEGACY_OPENSPEC_SKILLS),
            "actualSkills": [],
            "mismatches": [{"kind": "staging-setup-failed", "detail": str(exc)}],
            "stagingProject": str(staging_project),
        }
        return ({**record, "ok": False, "error": str(exc), "generation": generation}, None, None)

    replacements = {
        "{isolatedStagingProject}": str(staging_project),
        "{isolatedXdgConfigHome}": str(isolated_xdg),
        "{isolatedCodexHome}": str(isolated_codex_home),
    }
    command = [replacements.get(part, part) for part in record["command"]]
    environment = {
        key: replacements.get(value, value)
        for key, value in record.get("environment", {}).items()
    }
    result = run_command(
        command,
        staging_project,
        False,
        record.get("provenanceSource"),
        environment,
    )
    if result["ok"]:
        generation = verify_generated_openspec_skill_root(
            staging_project / ".codex" / "skills",
            str(record.get("expectedVersion") or ""),
        )
    else:
        generation = {
            "ok": False,
            "status": "command_failed",
            "expectedVersion": record.get("expectedVersion"),
            "expectedSkills": list(LEGACY_OPENSPEC_SKILLS),
            "actualSkills": [],
            "mismatches": [
                {"kind": "command-failed", "returncode": result.get("returncode")}
            ],
        }
    generation["stagingProject"] = str(staging_project)
    combined = {
        **record,
        **result,
        "command": command,
        "environment": environment,
        "ok": bool(result["ok"] and generation["ok"]),
        "generation": generation,
    }
    source_root = staging_project / ".codex" / "skills" if generation["ok"] else None
    return combined, source_root, staging_root


def managed_project_skills(triggered_capabilities: set[str] | None = None) -> list[str]:
    return [
        *PROJECT_ORCHESTRATOR_SKILLS,
        *required_matt_skills(triggered_capabilities or set()),
        *OPENSPEC_WORKFLOW_SKILLS,
    ]


def run_command(
    command: list[str],
    repo: Path,
    dry_run: bool,
    provenance_source: str | None = None,
    environment: dict[str, str] | None = None,
) -> dict[str, Any]:
    if dry_run:
        result: dict[str, Any] = {"ok": True, "command": command, "skipped": True}
        if provenance_source:
            result["provenanceSource"] = provenance_source
        if environment:
            result["environment"] = environment
        return result
    try:
        command_environment = dict(os.environ)
        command_environment.update(environment or {})
        result = subprocess.run(
            command,
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
            env=command_environment,
        )
    except FileNotFoundError:
        output: dict[str, Any] = {
            "ok": False,
            "command": command,
            "error": f"missing executable: {command[0]}",
        }
        if provenance_source:
            output["provenanceSource"] = provenance_source
        return output
    except OSError as exc:
        output = {"ok": False, "command": command, "error": str(exc)}
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
    if environment:
        output["environment"] = environment
    return output
