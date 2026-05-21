from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from workflow_dependency_catalog import (
    DEVELOPER_SKILLS,
    PROJECT_ORCHESTRATOR_SKILLS,
    REQUIRED_CLI_TOOLS,
    REQUIRED_GSD_AGENTS,
    REQUIRED_GSD_SKILLS,
    REQUIRED_OPENSPEC_SKILLS,
    REQUIRED_SKILLS,
    REQUIRED_SUPERPOWERS_PROJECT_SKILLS,
)
from workflow_dependency_plugin_checks import (
    add_skill_checks,
    check_global_plugin_inactive,
    check_plugin_activation,
    check_plugin_installed,
)


def check_external_dependencies(
    checks: list[dict[str, Any]],
    codex_home: Path,
    global_config: dict[str, Any],
    strict: bool,
    repo: Path | None = None,
) -> None:
    check_required_cli_tools(checks)
    check_global_plugin_inactive(checks, global_config, "superpowers")
    check_global_skills_inactive(checks, codex_home, global_config)
    if repo is not None:
        check_project_skills(checks, repo, PROJECT_ORCHESTRATOR_SKILLS, True)
        check_project_skills(checks, repo, REQUIRED_SUPERPOWERS_PROJECT_SKILLS, True)
        check_project_skills(checks, repo, REQUIRED_GSD_SKILLS, True)
        check_project_gsd_agents(checks, repo, True)
        check_project_skills(checks, repo, REQUIRED_OPENSPEC_SKILLS, True)
    for plugin, skills in REQUIRED_SKILLS.items():
        check_plugin_installed(checks, codex_home, plugin, "external plugin installed", True)
        add_skill_checks(checks, codex_home, plugin, skills, True)
    for plugin, skills in DEVELOPER_SKILLS.items():
        check_plugin_activation(checks, global_config, plugin, "developer plugin enabled", strict)
        add_skill_checks(checks, codex_home, plugin, skills, strict)


def check_required_cli_tools(checks: list[dict[str, Any]]) -> None:
    for tool in REQUIRED_CLI_TOOLS:
        path = shutil.which(tool)
        add_check(checks, f"external cli available: {tool}", path is not None, True, path or "missing")


def check_project_skills(
    checks: list[dict[str, Any]],
    repo: Path,
    skills: list[str],
    required: bool,
) -> None:
    for skill in skills:
        path = repo / ".codex" / "skills" / skill / "SKILL.md"
        add_check(checks, f"project skill active: {skill}", path.exists(), required, str(path))


def check_project_gsd_agents(checks: list[dict[str, Any]], repo: Path, required: bool) -> None:
    for agent in REQUIRED_GSD_AGENTS:
        path = repo / ".codex" / "agents" / agent
        add_check(checks, f"project gsd agent active: {agent}", path.exists(), required, str(path))


def check_global_skills_inactive(
    checks: list[dict[str, Any]],
    codex_home: Path,
    config: dict[str, Any],
) -> None:
    for skill in [*REQUIRED_GSD_SKILLS, *REQUIRED_OPENSPEC_SKILLS, *REQUIRED_SUPERPOWERS_PROJECT_SKILLS]:
        path = codex_home / "skills" / skill / "SKILL.md"
        inactive = not path.exists() or skill_disabled(config, path)
        detail = "not installed globally" if not path.exists() else skill_detail(path, config)
        add_check(checks, f"global skill inactive: {skill}", inactive, True, detail)


def skill_disabled(config: dict[str, Any], path: Path) -> bool:
    for entry in config.get("skills", {}).get("config", []):
        configured_path = entry.get("path")
        if configured_path == str(path) and entry.get("enabled") is False:
            return True
    return False


def skill_detail(path: Path, config: dict[str, Any]) -> str:
    if not path.exists():
        return "missing"
    if skill_disabled(config, path):
        return f"disabled: {path}"
    return str(path)


def add_check(checks: list[dict[str, Any]], name: str, ok: bool, required: bool, detail: str = "") -> None:
    checks.append({"name": name, "ok": bool(ok), "required": bool(required), "detail": detail})
