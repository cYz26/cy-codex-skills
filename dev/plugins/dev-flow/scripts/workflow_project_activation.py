from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from workflow_paths import repo_path
from workflow_dependency_catalog import (
    LEGACY_OPENSPEC_SKILLS,
    PROJECT_ORCHESTRATOR_SKILLS,
    GSD_ROADMAP_SKILLS,
    STRICT_SUPERPOWERS_PROJECT_SKILLS,
)
from workflow_project_skill_paths import migrate_project_skill_layout
from workflow_project_skill_install import ensure_project_local_skills
from workflow_constants import resolve_plugin_root
from workflow_dependency_provenance import (
    dependency_install_command,
    dependency_provenance_source_path,
    load_dependency_provenance,
)
from workflow_provider_profiles import diagnose_provider_selection, resolve_provider_selection
from workflow_provider_activation import (
    apply_provider_selection_overrides,
    apply_provider_source_overrides,
    persist_provider_selection_transaction,
)
from workflow_context_config import read_config
from workflow_provider_registry import default_plugin_root as provider_registry_root, side_effect_decision


def activate_project_dependencies(
    repo: Path,
    dry_run: bool = False,
    skip_official_installs: bool = False,
    plugin_root: Path | None = None,
    codex_home: Path | None = None,
    refresh_project_skills: bool = False,
    migrate_official_skill_layout: bool = False,
    apply_skill_layout_migration: bool = False,
    provider_sources: list[str] | None = None,
    persist_provider_selection: bool = False,
    authorizations: set[str] | None = None,
    triggered_capabilities: set[str] | None = None,
    methodology_profile: str | None = None,
    roadmap_provider: str | None = None,
) -> dict[str, Any]:
    repo = repo_path(repo)
    plugin_root = repo_path(plugin_root or resolve_plugin_root())
    codex_home = repo_path(codex_home or Path.home() / ".codex")
    global_config = read_config(codex_home / "config.toml")
    provenance = load_dependency_provenance(plugin_root)
    source_records = provenance.get("providerSources", {})

    def resolve_active_selection() -> dict[str, Any]:
        resolved = resolve_provider_selection(repo, codex_home, global_config)
        resolved = apply_provider_selection_overrides(
            resolved,
            methodology_profile,
            roadmap_provider,
        )
        return apply_provider_source_overrides(resolved, provider_sources, source_records)

    selection_overrides = methodology_profile is not None or roadmap_provider is not None
    selection = resolve_active_selection()
    provider_diagnosis = diagnose_provider_selection(
        selection,
        repo,
        codex_home,
        triggered_capabilities=triggered_capabilities,
        core_plugin_root=plugin_root,
    )
    granted = (
        set(authorizations)
        if authorizations is not None
        else ({"explicit_named_dependency_request"} if not dry_run else set())
    )
    dependency_effect = side_effect_decision(
        provider_registry_root(),
        "dependency.install_update",
        granted,
    )
    explicit_overrides = bool(provider_sources) or selection_overrides
    persistence_authorized = not explicit_overrides or dry_run or persist_provider_selection
    writes_blocked = not persistence_authorized or (not dry_run and not dependency_effect["authorized"])
    execution_dry_run = dry_run or writes_blocked
    commands = official_install_command_records(
        repo,
        plugin_root,
        selection,
        provider_diagnosis,
        source_records,
        codex_home,
    )
    command_results = []
    if not skip_official_installs:
        for command in commands:
            result = run_command(
                command["command"],
                repo,
                execution_dry_run,
                command.get("provenanceSource"),
                command.get("environment"),
            )
            command_results.append({**command, **result})
    command_ok = all(item["ok"] for item in command_results)
    receipts = successful_provider_install_receipts(command_results)
    active_diagnosis = provider_diagnosis
    if not execution_dry_run and command_ok:
        selection = resolve_active_selection()
        active_diagnosis = diagnose_provider_selection(
            selection,
            repo,
            codex_home,
            triggered_capabilities=triggered_capabilities,
            trusted_install_receipts=receipts,
            core_plugin_root=plugin_root,
        )
    skill_layout_migration = None
    if migrate_official_skill_layout:
        skill_layout_migration = migrate_project_skill_layout(
            repo,
            managed_project_skills(),
            dry_run=execution_dry_run or not apply_skill_layout_migration,
            script_path=Path(__file__).resolve(),
        )
    skills_result = ensure_project_local_skills(
        repo,
        plugin_root,
        codex_home,
        execution_dry_run,
        refresh_project_skills,
        selection,
        active_diagnosis,
        triggered_capabilities=triggered_capabilities,
    )
    if not execution_dry_run and command_ok and skills_result["ok"]:
        selection = resolve_active_selection()
        active_diagnosis = diagnose_provider_selection(
            selection,
            repo,
            codex_home,
            triggered_capabilities=triggered_capabilities,
            trusted_install_receipts=receipts,
            core_plugin_root=plugin_root,
        )
    migration_ok = skill_layout_migration is None or skill_layout_migration["ok"]
    persistence_requested = bool(active_diagnosis.get("selectedProviders")) or selection_overrides
    persistence_authority = provider_persistence_authorized(
        selection,
        provider_sources,
        persist_provider_selection,
        selection_overrides,
    )
    ready_for_persistence = bool(
        active_diagnosis.get("methodologyReady")
        and active_diagnosis.get("roadmapReady")
    )
    config_persistence = None
    lock_persistence = None
    if persistence_requested and explicit_overrides and not persistence_authority and not dry_run:
        config_persistence = lock_persistence = {
            "ok": False,
            "status": "authorization_required",
            "changed": False,
        }
    elif persistence_requested and ready_for_persistence:
        config_persistence, lock_persistence = persist_provider_selection_transaction(
            active_diagnosis,
            repo,
            apply=not execution_dry_run,
            persist_selection=persistence_authority,
        )
    elif persistence_requested:
        config_persistence = lock_persistence = {
            "ok": execution_dry_run,
            "status": "planned_after_provider_ready" if execution_dry_run else "readiness_required",
            "changed": False,
        }
    provider_persistence = combine_provider_persistence(config_persistence, lock_persistence)
    if (
        not execution_dry_run
        and provider_persistence["ok"]
        and provider_persistence["status"] in {"applied", "current"}
    ):
        selection = resolve_provider_selection(repo, codex_home, global_config)
        active_diagnosis = diagnose_provider_selection(
            selection,
            repo,
            codex_home,
            triggered_capabilities=triggered_capabilities,
            core_plugin_root=plugin_root,
        )
    return {
        "ok": (
            command_ok
            and migration_ok
            and skills_result["ok"]
            and provider_persistence["ok"]
            and not writes_blocked
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
        "selection": selection,
        "providers": active_diagnosis["providers"],
        "triggered_capabilities": sorted(triggered_capabilities or set()),
        "coreReady": active_diagnosis["coreReady"],
        "methodologyReady": active_diagnosis["methodologyReady"],
        "roadmapReady": active_diagnosis["roadmapReady"],
        "provider_persistence": provider_persistence,
    }


def combine_provider_persistence(
    config_result: dict[str, Any] | None,
    lock_result: dict[str, Any] | None,
) -> dict[str, Any]:
    if config_result is None or lock_result is None:
        return {"ok": True, "status": "not_requested", "changed": False}
    statuses = {config_result["status"], lock_result["status"]}
    if "readiness_required" in statuses:
        status = "readiness_required"
    elif "planned_after_provider_ready" in statuses:
        status = "planned_after_provider_ready"
    elif "authorization_required" in statuses:
        status = "authorization_required"
    elif statuses == {"planned"}:
        status = "planned"
    elif "applied" in statuses:
        status = "applied"
    else:
        status = "current"
    return {
        "ok": bool(config_result["ok"] and lock_result["ok"]),
        "status": status,
        "changed": bool(config_result.get("changed") or lock_result.get("changed")),
        "config": config_result,
        "lock": lock_result,
    }


def official_install_commands(
    repo: Path,
    selection: dict[str, Any] | None = None,
) -> list[list[str]]:
    return [item["command"] for item in official_install_command_records(repo, selection=selection)]


def official_install_command_records(
    repo: Path,
    plugin_root: Path | None = None,
    selection: dict[str, Any] | None = None,
    diagnosis: dict[str, Any] | None = None,
    source_records: dict[str, Any] | None = None,
    codex_home: Path | None = None,
) -> list[dict[str, Any]]:
    provenance_source = str(dependency_provenance_source_path(plugin_root))
    commands = [
        {"command": ["openspec", "init", "--tools", "codex", "--profile", "core", str(repo), "--force"]},
    ]
    if selection is None:
        return commands
    reports = (diagnosis or {}).get("providers", {})
    selected = {
        "strict-superpowers": "superpowers",
        "lean-matt": "mattpocock-skills",
    }.get(selection.get("effectiveMethodologyProfile"))
    selected_report = reports.get(selected, {}) if selected else {}
    if selected and provider_install_is_safe_remediation(selected, selected_report):
        source = selected_source_record(
            selected,
            selection,
            source_records or {},
            selected_report,
        )
        if source and (source.get("installCommand") or source.get("updateCommand")):
            commands.append(provider_install_record(selected, source, provenance_source, codex_home))
    if (
        selection.get("effectiveRoadmapProvider") == "gsd"
        and not reports.get("gsd", {}).get("ready", False)
    ):
        source = selected_source_record("gsd", selection, source_records or {})
        if source is None:
            gsd_sources = [
                {"source_id": source_id, **record}
                for source_id, record in (source_records or {}).items()
                if isinstance(record, dict) and record.get("provider") == "gsd"
            ]
            source = gsd_sources[0] if len(gsd_sources) == 1 else None
        if source:
            commands.append(provider_install_record("gsd", source, provenance_source, codex_home))
    return commands


def provider_install_is_safe_remediation(
    provider: str,
    report: dict[str, Any],
) -> bool:
    if report.get("ready", False):
        return False
    status = report.get("status")
    if provider == "mattpocock-skills":
        return bool(
            status == "missing_capabilities"
            and report.get("projectRootLocal", False)
            and not report.get("nonLocalSkills")
        )
    if provider == "superpowers":
        return status in {"missing", "missing_capabilities"}
    return False


def selected_source_record(
    provider: str,
    selection: dict[str, Any],
    source_records: dict[str, Any],
    provider_report: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    selector = selection.get("providerSelectors", {}).get(provider, {})
    candidates = [
        {"source_id": source_id, **record}
        for source_id, record in source_records.items()
        if isinstance(record, dict) and record.get("provider") == provider
    ]
    if isinstance(selector, dict) and selector:
        return matching_source_record(provider, selector, candidates)
    lock = selection.get("providerLock", {}).get("providers", {}).get(provider, {})
    if isinstance(lock, dict) and lock:
        return matching_source_record(provider, lock, candidates)
    diagnosed_identity = (provider_report or {}).get("sourceIdentity", {})
    if isinstance(diagnosed_identity, dict) and diagnosed_identity:
        return matching_source_record(provider, diagnosed_identity, candidates)
    return candidates[0] if len(candidates) == 1 else None


def matching_source_record(
    provider: str,
    identity: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> dict[str, Any] | None:
    aliases = {
        "source_id": ("source_id", "sourceId"),
        "source_channel": ("source_channel", "sourceChannel"),
        "repository": ("repository",),
        "ref": ("ref",),
        "commit": ("commit",),
        "package": ("package",),
        "version": ("version",),
    }

    def value(names: tuple[str, ...]) -> Any:
        return next((identity[name] for name in names if identity.get(name) not in (None, "")), None)

    source_id = value(aliases["source_id"])
    if source_id is not None:
        matched = [item for item in candidates if str(item.get("source_id")) == str(source_id)]
        if len(matched) != 1:
            return None
        candidate = matched[0]
        for key, names in aliases.items():
            expected = value(names)
            if key == "source_id" or expected in (None, ""):
                continue
            if str(candidate.get(key)) != str(expected):
                return None
        return candidate
    keys = {
        "superpowers": ("source_channel", "version"),
        "mattpocock-skills": ("repository", "ref", "commit"),
        "gsd": ("package", "version"),
    }.get(provider, ())
    expected = {
        key: value(aliases[key])
        for key in keys
        if value(aliases[key]) not in (None, "")
    }
    if not keys or not expected:
        return None
    if provider == "mattpocock-skills" and set(expected) != set(keys):
        return None
    matched = [
        item
        for item in candidates
        if all(str(item.get(key)) == str(expected_value) for key, expected_value in expected.items())
    ]
    return matched[0] if len(matched) == 1 else None


def provider_install_record(
    provider: str,
    source: dict[str, Any],
    provenance_source: str,
    codex_home: Path | None,
) -> dict[str, Any]:
    environment = {
        key: str(value).replace("{codexHome}", str(codex_home or Path.home() / ".codex"))
        for key, value in source.get("environment", {}).items()
    }
    return {
        "provider": provider,
        "source_id": source.get("source_id"),
        "command": list(source.get("installCommand") or source.get("updateCommand") or []),
        "environment": environment,
        "provenanceSource": provenance_source,
    }


def successful_provider_install_receipts(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        str(item["provider"]): {
            "ok": True,
            "source_id": item.get("source_id"),
            "command": item.get("command"),
        }
        for item in results
        if item.get("provider") and item.get("ok") is True and item.get("skipped") is not True
    }


def provider_persistence_authorized(
    selection: dict[str, Any],
    provider_sources: list[str] | None,
    persist_provider_selection: bool,
    selection_overrides: bool = False,
) -> bool:
    if provider_sources or selection_overrides:
        return persist_provider_selection
    if selection.get("selectionSource") == "explicit_config":
        return True
    return persist_provider_selection


def managed_project_skills() -> list[str]:
    return [
        *PROJECT_ORCHESTRATOR_SKILLS,
        *STRICT_SUPERPOWERS_PROJECT_SKILLS,
        *GSD_ROADMAP_SKILLS,
        *LEGACY_OPENSPEC_SKILLS,
    ]


def run_command(
    command: list[str],
    repo: Path,
    dry_run: bool,
    provenance_source: str | None = None,
    environment: dict[str, str] | None = None,
) -> dict[str, Any]:
    if dry_run:
        result = {"ok": True, "command": command, "skipped": True}
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
    if environment:
        output["environment"] = environment
    return output
