from __future__ import annotations

from pathlib import Path
from typing import Any

from workflow_context_actions import (
    append_disabled_skill,
    apply_context_tool_actions,
    disable_global_plugin,
    disable_global_skill,
    dry_run_action,
    ensure_backup,
    escape_toml_string,
    execute_action,
    install_project_skill,
    missing_action_ids,
    next_section_index,
    select_actions,
    set_plugin_enabled,
    update_plugin_section,
)
from workflow_context_catalog import normalize_catalog_tools, read_catalog, read_url_catalog, source_tools
from workflow_context_inventory import (
    cache_plugin_parts,
    context_pressure,
    disabled_skill_paths,
    global_plugins,
    global_skills,
    installed_cache_skills,
    plugin_name,
    project_signals,
    project_skills,
    read_config,
)
from workflow_context_recommendations import (
    add_cleanup_recommendations,
    add_install_recommendations,
    add_source_recommendations,
    recommendation,
    relevant_to_project,
    slug,
)


__all__ = [
    "add_cleanup_recommendations",
    "add_install_recommendations",
    "add_source_recommendations",
    "append_disabled_skill",
    "apply_context_tool_actions",
    "audit_context_tools",
    "cache_plugin_parts",
    "context_pressure",
    "disabled_skill_paths",
    "disable_global_plugin",
    "disable_global_skill",
    "dry_run_action",
    "ensure_backup",
    "escape_toml_string",
    "execute_action",
    "global_plugins",
    "global_skills",
    "installed_cache_skills",
    "install_project_skill",
    "missing_action_ids",
    "next_section_index",
    "normalize_catalog_tools",
    "plugin_name",
    "project_signals",
    "project_skills",
    "read_catalog",
    "read_config",
    "read_url_catalog",
    "recommendation",
    "relevant_to_project",
    "select_actions",
    "set_plugin_enabled",
    "slug",
    "source_tools",
    "update_plugin_section",
]


def audit_context_tools(
    codex_home: Path,
    repo: Path | None = None,
    config_path: Path | None = None,
    source_catalogs: list[Path] | None = None,
    source_urls: list[str] | None = None,
) -> dict[str, Any]:
    codex_home = Path(codex_home).expanduser().resolve()
    repo = Path(repo).expanduser().resolve() if repo else None
    config_path = Path(config_path).expanduser().resolve() if config_path else codex_home / "config.toml"
    config = read_config(config_path)
    inventory = build_inventory(codex_home, repo, config, source_catalogs or [], source_urls or [])
    signals = project_signals(repo)
    findings: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    add_cleanup_recommendations(inventory, config_path, findings, recommendations, actions)
    add_install_recommendations(inventory, repo, signals, recommendations, actions)
    add_source_recommendations(inventory, signals, recommendations)
    return audit_report(codex_home, config_path, repo, inventory, signals, findings, recommendations, actions)


def build_inventory(
    codex_home: Path,
    repo: Path | None,
    config: dict[str, Any],
    source_catalogs: list[Path],
    source_urls: list[str],
) -> dict[str, Any]:
    return {
        "globalPlugins": global_plugins(config),
        "globalSkills": global_skills(codex_home, config),
        "projectSkills": project_skills(repo),
        "installedSkills": installed_cache_skills(codex_home),
        "sourceTools": source_tools(source_catalogs, source_urls),
    }


def audit_report(
    codex_home: Path,
    config_path: Path,
    repo: Path | None,
    inventory: dict[str, Any],
    signals: list[str],
    findings: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    actions: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "ok": True,
        "contextPressure": context_pressure(inventory),
        "codexHome": str(codex_home),
        "config": str(config_path),
        "repo": str(repo) if repo else None,
        "inventory": inventory,
        "projectSignals": signals,
        "findings": findings,
        "recommendations": recommendations,
        "actions": actions,
    }
