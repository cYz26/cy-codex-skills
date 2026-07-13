from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from workflow_dependency_catalog import (
    DEVELOPER_SKILLS,
    LEGACY_OPENSPEC_SKILLS,
    PROJECT_ORCHESTRATOR_SKILLS,
    REQUIRED_CLI_TOOLS,
    GSD_ROADMAP_AGENTS,
    GSD_ROADMAP_SKILLS,
    REQUIRED_SKILLS,
    STRICT_SUPERPOWERS_BASE_PROJECT_SKILLS,
    STRICT_SUPERPOWERS_PROJECT_SKILLS,
)
from workflow_dependency_plugin_checks import (
    SUPERPOWERS_RECOMMENDED,
    add_superpowers_governance_checks,
    add_skill_checks,
    check_global_plugin_inactive,
    check_plugin_activation,
    check_plugin_installed,
    compare_versions,
    superpowers_compatibility,
    superpowers_next_action,
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
    *,
    selection: dict[str, Any] | None = None,
    provider_report: dict[str, Any] | None = None,
    triggered_capabilities: set[str] | None = None,
) -> dict[str, Any]:
    methodology = selection.get("effectiveMethodologyProfile") if selection else "core"
    roadmap = selection.get("effectiveRoadmapProvider") if selection else "none"
    check_required_cli_tools(checks)
    check_global_plugin_inactive(checks, global_config, "superpowers", required=False)
    check_global_skills_inactive(checks, codex_home, global_config, methodology, roadmap)
    if repo is not None:
        check_project_skills(checks, repo, PROJECT_ORCHESTRATOR_SKILLS, True)
        if methodology == "strict-superpowers":
            check_project_skills(checks, repo, STRICT_SUPERPOWERS_BASE_PROJECT_SKILLS, True)
            conditional = strict_conditional_skills_for_capabilities(triggered_capabilities or set())
            check_project_skills(checks, repo, conditional, True)
        if roadmap == "gsd":
            check_project_skills(checks, repo, GSD_ROADMAP_SKILLS, True)
            check_project_gsd_core_runtime(checks, repo, True)
            check_project_gsd_agents(checks, repo, True)
        check_project_openspec_setup(checks, repo, True)
        check_project_openspec_sync_workflow(checks, repo, False)
        check_legacy_project_skills(checks, repo, LEGACY_OPENSPEC_SKILLS, False)
    superpowers, bound_superpowers = provider_superpowers_compatibility(provider_report, codex_home, strict)
    if methodology == "strict-superpowers":
        add_bound_superpowers_checks(checks, bound_superpowers, superpowers)
    for plugin, skills in DEVELOPER_SKILLS.items():
        check_plugin_activation(checks, global_config, plugin, "developer plugin enabled", strict)
        add_skill_checks(checks, codex_home, plugin, skills, strict)
    return superpowers


def strict_conditional_skills_for_capabilities(capabilities: set[str]) -> list[str]:
    from workflow_provider_registry import default_plugin_root, load_provider_registry

    registry = load_provider_registry(default_plugin_root())
    conditional = set(registry["methodologyProfiles"]["strict-superpowers"]["conditionalSkills"])
    return sorted(
        {
            skill
            for capability in capabilities
            for skill in registry["capabilities"].get(capability, {}).get("strict-superpowers", [])
            if skill in conditional
        }
    )


def provider_superpowers_compatibility(
    provider_report: dict[str, Any] | None,
    codex_home: Path,
    strict: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if provider_report is None:
        report = add_superpowers_governance_checks([], codex_home, strict)
        return report, report
    bound = dict(provider_report.get("providers", {}).get("superpowers", {}))
    version = str(bound.get("version") or "0")
    bound_status = bound.get("status")
    if bound_status == "ready":
        status = (
            "superpowers_ok"
            if compare_versions(version, SUPERPOWERS_RECOMMENDED) >= 0
            else "superpowers_upgrade_recommended"
        )
    else:
        status = {
            "hook_untrusted_when_declared": "superpowers_hook_untrusted",
            "hook_missing_when_declared": "superpowers_hook_missing",
            "ambiguous_source": "superpowers_ambiguous_source",
            "stale_lock": "superpowers_stale_lock",
            "missing": "superpowers_missing",
            "missing_capabilities": "superpowers_unsupported",
        }.get(str(bound_status), "superpowers_missing")
    report = {
        "status": status,
        "version": bound.get("version"),
        "sourceChannel": bound.get("sourceChannel"),
        "pluginRoot": bound.get("root"),
        "compatibility": superpowers_compatibility(version),
        "requiredSkills": bound.get("skills", {}),
        "sessionStartHookPresent": bound.get("hookPresent", False),
        "sessionStartHookTrusted": bound.get("hookTrusted", False),
        "strict": strict,
        "nextAction": superpowers_next_action(status),
    }
    return report, bound


def add_bound_superpowers_checks(
    checks: list[dict[str, Any]],
    report: dict[str, Any],
    compatibility: dict[str, Any],
) -> None:
    ready = bool(report.get("ready"))
    add_check(
        checks,
        "external plugin installed: superpowers",
        bool(report.get("candidates")),
        True,
        report.get("root") or report.get("status", "missing"),
    )
    skills = report.get("skills", {})
    skill_paths = report.get("skillPaths", {})
    for skill in REQUIRED_SKILLS["superpowers"]:
        add_check(
            checks,
            f"external skill available: superpowers:{skill}",
            bool(skills.get(skill)),
            True,
            skill_paths.get(skill, "missing"),
        )
    add_check(
        checks,
        "superpowers dependency status",
        compatibility["status"] == "superpowers_ok",
        not ready,
        compatibility.get("nextAction", report.get("status", "missing")),
        status=compatibility.get("status"),
        version=report.get("version"),
        sourceChannel=report.get("sourceChannel"),
    )
    latest_ready = compare_versions(str(report.get("version") or "0"), SUPERPOWERS_RECOMMENDED) >= 0
    latest_ready = latest_ready and all(report.get("skills", {}).values())
    add_check(
        checks,
        "superpowers latest ready",
        latest_ready,
        False,
        f"version {report.get('version') or 'unknown'}, recommended {SUPERPOWERS_RECOMMENDED}",
        status=compatibility.get("status"),
    )
    if report.get("hookDeclared"):
        add_check(
            checks,
            "superpowers session-start hook present",
            bool(report.get("hookPresent")),
            True,
            "SessionStart hook present" if report.get("hookPresent") else "missing SessionStart hook",
            status=compatibility.get("status"),
        )
        add_check(
            checks,
            "superpowers session-start hook trusted",
            bool(report.get("hookTrusted")),
            True,
            "trusted" if report.get("hookTrusted") else "review and trust with /hooks",
            status=compatibility.get("status"),
        )


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


def check_project_openspec_sync_workflow(checks: list[dict[str, Any]], repo: Path, required: bool) -> None:
    official = official_project_skill_file(repo, "openspec-sync-specs")
    legacy = legacy_project_skill_file(repo, "openspec-sync-specs")
    ok = official.exists() or legacy.exists()
    if official.exists():
        detail = str(official)
        path_kind = OFFICIAL_PROJECT_SKILL_PATH_KIND
    elif legacy.exists():
        detail = str(legacy)
        path_kind = LEGACY_PROJECT_SKILL_PATH_KIND
    else:
        detail = (
            "missing openspec-sync-specs; refresh with "
            f"`openspec init --tools codex --profile core {repo} --force`"
        )
        path_kind = OFFICIAL_PROJECT_SKILL_PATH_KIND
    add_check(
        checks,
        "project openspec sync workflow available",
        ok,
        required,
        detail,
        path_kind=path_kind,
    )


def check_project_gsd_agents(checks: list[dict[str, Any]], repo: Path, required: bool) -> None:
    for agent in GSD_ROADMAP_AGENTS:
        path = repo / ".codex" / "agents" / agent
        add_check(checks, f"project gsd agent active: {agent}", path.exists(), required, str(path))


def check_project_gsd_core_runtime(checks: list[dict[str, Any]], repo: Path, required: bool) -> None:
    tools = repo / ".codex" / "gsd-core" / "bin" / "gsd-tools.cjs"
    add_check(checks, "project gsd core runtime active", tools.exists(), required, str(tools))


def check_global_skills_inactive(
    checks: list[dict[str, Any]],
    codex_home: Path,
    config: dict[str, Any],
    methodology: str = "strict-superpowers",
    roadmap: str = "gsd",
) -> None:
    skill_requirements = [
        *[(skill, roadmap == "gsd") for skill in GSD_ROADMAP_SKILLS],
        *[(skill, True) for skill in LEGACY_OPENSPEC_SKILLS],
        *[(skill, methodology == "strict-superpowers") for skill in STRICT_SUPERPOWERS_PROJECT_SKILLS],
    ]
    for skill, required in skill_requirements:
        path = codex_home / "skills" / skill / "SKILL.md"
        inactive = not path.exists() or skill_disabled(config, path)
        detail = "not installed globally" if not path.exists() else skill_detail(path, config)
        add_check(checks, f"global skill inactive: {skill}", inactive, required, detail)


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
