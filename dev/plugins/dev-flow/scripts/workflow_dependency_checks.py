from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

from workflow_dependency_catalog import (
    DEVELOPER_SKILLS,
    LEGACY_OPENSPEC_SKILLS,
    OPENSPEC_WORKFLOW_SKILLS,
    PROJECT_ORCHESTRATOR_SKILLS,
    REQUIRED_CLI_TOOLS,
)
from workflow_dependency_provenance import dependency_provenance_record
from workflow_methodology import diagnose_methodology
from workflow_project_skill_install import verify_generated_openspec_skill_root
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
    plugin_root: Path,
    triggered_capabilities: set[str] | None = None,
) -> dict[str, Any]:
    check_required_cli_tools(checks)
    methodology = {
        "ready": True,
        "status": "not_project_scoped",
        "requiredSkills": [],
        "skills": {},
    }
    if repo is not None:
        check_project_devflow_skills(checks, repo, plugin_root, True)
        check_project_openspec_setup(checks, repo, plugin_root, True)
        check_project_openspec_sync_workflow(checks, repo, False)
        check_project_openspec_update_workflow(checks, repo, False)
        check_legacy_project_skills(checks, repo, LEGACY_OPENSPEC_SKILLS, False)
        methodology = diagnose_methodology(
            repo,
            triggered_capabilities or set(),
            plugin_root,
            codex_home=codex_home,
        )
        add_methodology_checks(checks, repo, methodology)
    if strict:
        for plugin, skills in DEVELOPER_SKILLS.items():
            check_plugin_activation(checks, global_config, plugin, "developer plugin enabled", True)
            add_skill_checks(checks, codex_home, plugin, skills, True)
    return methodology


def add_methodology_checks(
    checks: list[dict[str, Any]],
    repo: Path,
    report: dict[str, Any],
) -> None:
    for skill in report.get("requiredSkills", []):
        skill_report = report.get("skills", {}).get(skill, {})
        add_check(
            checks,
            f"project methodology skill ready: {skill}",
            bool(skill_report.get("ready")),
            True,
            str(repo / ".agents" / "skills" / skill),
            status=skill_report.get("status", "missing"),
        )


def check_required_cli_tools(checks: list[dict[str, Any]]) -> None:
    for tool in REQUIRED_CLI_TOOLS:
        path = shutil.which(tool)
        add_check(checks, f"external cli available: {tool}", path is not None, True, path or "missing")


def check_project_devflow_skills(
    checks: list[dict[str, Any]],
    repo: Path,
    plugin_root: Path,
    required: bool,
) -> None:
    for skill in PROJECT_ORCHESTRATOR_SKILLS:
        report = diagnose_project_devflow_skill(repo, plugin_root, skill)
        add_check(
            checks,
            f"project DevFlow skill trusted: {skill}",
            bool(report["ready"]),
            required,
            report["status"],
            path_kind=OFFICIAL_PROJECT_SKILL_PATH_KIND,
            project_path=report["projectPath"],
            source_path=report["sourcePath"],
            project_hash=report.get("projectHash"),
            source_hash=report.get("sourceHash"),
            route=report.get("route"),
            status=report["status"],
        )
        add_project_skill_layout_check(checks, repo, skill)


def diagnose_project_devflow_skill(
    repo: Path,
    plugin_root: Path,
    skill: str,
) -> dict[str, Any]:
    project_root = repo / ".agents" / "skills"
    project_skill = project_root / skill
    source_root = plugin_root / "skills"
    source_skill = source_root / skill
    base = {
        "projectPath": str(project_skill),
        "sourcePath": str(source_skill),
    }
    if any(path.is_symlink() for path in (Path(plugin_root), source_root)):
        return {**base, "ready": False, "status": "source_untrusted"}
    source_files = trusted_tree_files(source_skill)
    if source_files is None or "SKILL.md" not in source_files:
        return {**base, "ready": False, "status": "source_untrusted"}
    source_hash = tree_digest(source_files)
    base["sourceHash"] = source_hash
    if any(parent.is_symlink() for parent in (repo / ".agents", project_root)):
        return {**base, "ready": False, "status": "nonlocal_skill_route"}
    if not project_skill.exists() and not project_skill.is_symlink():
        return {**base, "ready": False, "status": "missing"}
    if project_skill.is_symlink():
        try:
            route_matches = project_skill.resolve(strict=True) == source_skill.resolve(strict=True)
        except OSError:
            route_matches = False
        if not route_matches:
            return {**base, "ready": False, "status": "source_conflict"}
        return {
            **base,
            "ready": True,
            "status": "ready",
            "route": "source_symlink",
            "projectHash": source_hash,
        }
    project_files = trusted_tree_files(project_skill)
    if project_files is None:
        return {**base, "ready": False, "status": "source_conflict"}
    project_hash = tree_digest(project_files)
    if project_files != source_files:
        return {
            **base,
            "ready": False,
            "status": "source_conflict",
            "projectHash": project_hash,
        }
    return {
        **base,
        "ready": True,
        "status": "ready",
        "route": "exact_copy",
        "projectHash": project_hash,
    }


def trusted_tree_files(root: Path) -> dict[str, str] | None:
    if root.is_symlink() or not root.is_dir():
        return None
    files: dict[str, str] = {}
    try:
        paths = sorted(root.rglob("*"))
    except OSError:
        return None
    for path in paths:
        if path.is_symlink():
            return None
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            try:
                files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                return None
        elif not path.is_dir():
            return None
    return files


def tree_digest(files: dict[str, str]) -> str:
    canonical = "\n".join(f"{path}\0{digest}" for path, digest in sorted(files.items()))
    return hashlib.sha256(canonical.encode()).hexdigest()


def add_project_skill_layout_check(checks: list[dict[str, Any]], repo: Path, skill: str) -> None:
    layout = scan_project_skill_layout(
        repo,
        [skill],
        script_path=Path(__file__).with_name("activate_project_dependencies.py"),
    )
    for item in layout["items"]:
        status = item["status"]
        add_check(
            checks,
            f"project skill layout: {skill}",
            False,
            status == "skill_layout_conflict",
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


def check_project_openspec_setup(
    checks: list[dict[str, Any]],
    repo: Path,
    plugin_root: Path,
    required: bool,
) -> None:
    config_path = repo / "openspec" / "config.yaml"
    expected_version = str(
        dependency_provenance_record("openspec-cli", plugin_root)["expectedVersion"]
    )
    verification = verify_generated_openspec_skill_root(
        repo / ".agents" / "skills",
        expected_version,
    )
    ok = config_path.is_file() and verification["ok"]
    missing = [] if config_path.is_file() else [str(config_path)]
    add_check(
        checks,
        "project openspec setup active",
        ok,
        required,
        (
            f"{config_path}; six trusted project-local OpenSpec skills"
            if ok
            else "missing or untrusted OpenSpec project setup"
        ),
        expected_skills=list(OPENSPEC_WORKFLOW_SKILLS),
        expected_version=expected_version,
        missing=missing,
        skill_status=verification["status"],
        skill_mismatches=verification["mismatches"],
        path_kind=OFFICIAL_PROJECT_SKILL_PATH_KIND,
    )


def check_project_openspec_sync_workflow(checks: list[dict[str, Any]], repo: Path, required: bool) -> None:
    check_project_openspec_workflow(checks, repo, "openspec-sync-specs", "sync", required)


def check_project_openspec_update_workflow(checks: list[dict[str, Any]], repo: Path, required: bool) -> None:
    check_project_openspec_workflow(checks, repo, "openspec-update-change", "update", required)


def check_project_openspec_workflow(
    checks: list[dict[str, Any]],
    repo: Path,
    skill: str,
    workflow: str,
    required: bool,
) -> None:
    official = official_project_skill_file(repo, skill)
    legacy = legacy_project_skill_file(repo, skill)
    ok = official.is_file() and not official.is_symlink()
    if official.exists():
        detail = str(official)
        path_kind = OFFICIAL_PROJECT_SKILL_PATH_KIND
    elif legacy.exists():
        detail = f"legacy-only {legacy}; migrate to .agents/skills"
        path_kind = OFFICIAL_PROJECT_SKILL_PATH_KIND
    else:
        detail = (
            f"missing {skill}; run the activation dry-run before an explicit apply: "
            f"`python3 {Path(__file__).with_name('activate_project_dependencies.py')} "
            f"--repo {repo} --refresh-project-skills --dry-run --json`"
        )
        path_kind = OFFICIAL_PROJECT_SKILL_PATH_KIND
    add_check(
        checks,
        f"project openspec {workflow} workflow available",
        ok,
        required,
        detail,
        path_kind=path_kind,
    )


def add_check(
    checks: list[dict[str, Any]],
    name: str,
    ok: bool,
    required: bool,
    detail: str = "",
    **extra: Any,
) -> None:
    checks.append(
        {
            "name": name,
            "ok": bool(ok),
            "required": bool(required),
            "detail": detail,
            **extra,
        }
    )


def check_plugin_activation(
    checks: list[dict[str, Any]],
    config: dict[str, Any],
    plugin: str,
    label: str,
    required: bool,
) -> None:
    enabled = any(
        name.startswith(f"{plugin}@")
        and isinstance(settings, dict)
        and settings.get("enabled") is True
        for name, settings in config.get("plugins", {}).items()
    )
    add_check(
        checks,
        f"{label}: {plugin}",
        enabled,
        required,
        "enabled" if enabled else "missing/disabled",
    )


def add_skill_checks(
    checks: list[dict[str, Any]],
    codex_home: Path,
    plugin: str,
    skills: list[str],
    required: bool,
) -> None:
    cache = codex_home / "plugins" / "cache"
    for skill in skills:
        candidates = [
            path
            for path in cache.rglob(f"skills/{skill}/SKILL.md")
            if plugin in path.parts
        ] if cache.exists() else []
        path = sorted(candidates)[-1] if candidates else None
        add_check(
            checks,
            f"external skill available: {plugin}:{skill}",
            path is not None,
            required,
            str(path) if path else "missing",
        )
