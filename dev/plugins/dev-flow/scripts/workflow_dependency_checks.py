from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from workflow_dependency_catalog import (
    DEVELOPER_SKILLS,
    LEGACY_OPENSPEC_SKILLS,
    PROJECT_ORCHESTRATOR_SKILLS,
    REQUIRED_CLI_TOOLS,
    REQUIRED_GSD_AGENTS,
    REQUIRED_GSD_SKILLS,
    REQUIRED_SKILLS,
    REQUIRED_SUPERPOWERS_PROJECT_SKILLS,
)
from workflow_dependency_plugin_checks import (
    add_superpowers_governance_checks,
    add_skill_checks,
    check_global_plugin_inactive,
    check_plugin_activation,
    check_plugin_installed,
)
from workflow_project_skill_paths import (
    LEGACY_PROJECT_SKILL_PATH_KIND,
    OFFICIAL_PROJECT_SKILL_PATH_KIND,
    legacy_project_skill_file,
    official_project_skill_file,
    scan_project_skill_layout,
)


def check_external_dependencies(
    checks: list[dict[str, Any]],
    codex_home: Path,
    global_config: dict[str, Any],
    strict: bool,
    repo: Path | None = None,
) -> None:
    check_required_cli_tools(checks)
    check_global_plugin_inactive(checks, global_config, "superpowers", required=False)
    check_global_skills_inactive(checks, codex_home, global_config)
    if repo is not None:
        check_project_skills(checks, repo, PROJECT_ORCHESTRATOR_SKILLS, True)
        check_project_skills(checks, repo, REQUIRED_SUPERPOWERS_PROJECT_SKILLS, True)
        check_project_skills(checks, repo, REQUIRED_GSD_SKILLS, True)
        check_project_gsd_core_runtime(checks, repo, True)
        check_project_gsd_agents(checks, repo, True)
        check_project_openspec_setup(checks, repo, True)
        check_legacy_project_skills(checks, repo, LEGACY_OPENSPEC_SKILLS, False)
    for plugin, skills in REQUIRED_SKILLS.items():
        check_plugin_installed(checks, codex_home, plugin, "external plugin installed", True)
        add_skill_checks(checks, codex_home, plugin, skills, True)
    superpowers = add_superpowers_governance_checks(checks, codex_home, strict)
    for plugin, skills in DEVELOPER_SKILLS.items():
        check_plugin_activation(checks, global_config, plugin, "developer plugin enabled", strict)
        add_skill_checks(checks, codex_home, plugin, skills, strict)
    return superpowers


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
        path = official_project_skill_file(repo, skill)
        add_check(
            checks,
            f"project skill active: {skill}",
            path.exists(),
            required,
            str(path),
            path_kind=OFFICIAL_PROJECT_SKILL_PATH_KIND,
        )
        add_project_skill_layout_check(checks, repo, skill)


def add_project_skill_layout_check(checks: list[dict[str, Any]], repo: Path, skill: str) -> None:
    layout = scan_project_skill_layout(
        repo,
        [skill],
        script_path=Path(__file__).with_name("activate_project_dependencies.py"),
    )
    for item in layout["items"]:
        status = item["status"]
        required = status == "skill_layout_conflict"
        ok = False
        add_check(
            checks,
            f"project skill layout: {skill}",
            ok,
            required,
            item["next_action"],
            status=status,
            path_kind=item["path_kind"],
            legacy_path_kind=item["legacy_path_kind"],
            official_path=item["official_skill_path"],
            legacy_path=item["legacy_skill_path"],
            migration_command=layout["dryRunCommand"],
            next_action=item["next_action"],
        )


def check_legacy_project_skills(
    checks: list[dict[str, Any]],
    repo: Path,
    skills: list[str],
    required: bool,
) -> None:
    for skill in skills:
        path = legacy_project_skill_file(repo, skill)
        add_check(
            checks,
            f"legacy project skill active: {skill}",
            path.exists(),
            required,
            str(path),
            path_kind=LEGACY_PROJECT_SKILL_PATH_KIND,
        )


def check_project_openspec_setup(checks: list[dict[str, Any]], repo: Path, required: bool) -> None:
    config_path = repo / "openspec" / "config.yaml"
    legacy_skill_paths = [repo / ".codex" / "skills" / skill / "SKILL.md" for skill in LEGACY_OPENSPEC_SKILLS]
    legacy_complete = all(path.exists() for path in legacy_skill_paths)
    ok = config_path.exists() or legacy_complete
    if config_path.exists():
        detail = str(config_path)
    elif legacy_complete:
        detail = "legacy project-local OpenSpec skills"
    else:
        detail = f"missing {config_path}"
    add_check(checks, "project openspec setup active", ok, required, detail)


def check_project_gsd_agents(checks: list[dict[str, Any]], repo: Path, required: bool) -> None:
    for agent in REQUIRED_GSD_AGENTS:
        path = repo / ".codex" / "agents" / agent
        add_check(checks, f"project gsd agent active: {agent}", path.exists(), required, str(path))


def check_project_gsd_core_runtime(checks: list[dict[str, Any]], repo: Path, required: bool) -> None:
    tools = repo / ".codex" / "gsd-core" / "bin" / "gsd-tools.cjs"
    add_check(checks, "project gsd core runtime active", tools.exists(), required, str(tools))


def check_global_skills_inactive(
    checks: list[dict[str, Any]],
    codex_home: Path,
    config: dict[str, Any],
) -> None:
    for skill in [*REQUIRED_GSD_SKILLS, *LEGACY_OPENSPEC_SKILLS, *REQUIRED_SUPERPOWERS_PROJECT_SKILLS]:
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


def add_check(
    checks: list[dict[str, Any]],
    name: str,
    ok: bool,
    required: bool,
    detail: str = "",
    **extra: Any,
) -> None:
    payload = {"name": name, "ok": bool(ok), "required": bool(required), "detail": detail}
    payload.update(extra)
    checks.append(payload)
