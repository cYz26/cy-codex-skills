from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from plugin_preflight_common import add_check, asset_exists, marketplace_base, read_json
from plugin_preflight_hooks import hook_commands, simulate_hook
from plugin_preflight_skills import skill_report
from workflow_dependencies import dependency_report


def run_preflight(
    plugin_root: Path,
    marketplace: Path | None,
    codex_home: Path | None = None,
    config_path: Path | None = None,
    strict: bool = False,
    repo: Path | None = None,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    manifest = read_json(manifest_path)
    skills = skill_report(plugin_root)
    hooks_path = plugin_root / manifest.get("hooks", "hooks.json")

    check_manifest(checks, manifest, hooks_path)
    check_skills_and_assets(checks, plugin_root, manifest, skills)
    registration, registered_path = check_marketplace(checks, marketplace, manifest, plugin_root)
    hook_result = check_hooks(checks, plugin_root, hooks_path)
    dependencies = check_dependencies(checks, plugin_root, codex_home, config_path, strict, repo)

    return preflight_report(
        plugin_root,
        manifest,
        marketplace,
        registration,
        registered_path,
        skills,
        hook_result,
        dependencies,
        checks,
    )


def check_manifest(checks: list[dict[str, Any]], manifest: dict[str, Any], hooks_path: Path) -> None:
    add_check(checks, "manifest.name", manifest.get("name") == "dev-flow")
    add_check(checks, "manifest.skills", manifest.get("skills") == "./skills/")
    add_check(checks, "manifest.hooks", manifest.get("hooks") == "./hooks.json")
    add_check(checks, "hooks file", hooks_path.exists(), str(hooks_path))


def check_skills_and_assets(
    checks: list[dict[str, Any]],
    plugin_root: Path,
    manifest: dict[str, Any],
    skills: dict[str, Any],
) -> None:
    interface = manifest.get("interface", {})
    add_check(checks, "skills valid", skills["count"] >= 8 and not skills["invalid"])
    add_check(checks, "logo", asset_exists(plugin_root, interface.get("logo")))
    add_check(checks, "composerIcon", asset_exists(plugin_root, interface.get("composerIcon")))


def check_marketplace(
    checks: list[dict[str, Any]],
    marketplace: Path | None,
    manifest: dict[str, Any],
    plugin_root: Path,
) -> tuple[dict[str, Any] | None, Path | None]:
    if not marketplace:
        return None, None
    catalog = read_json(marketplace)
    registration = next(
        (item for item in catalog.get("plugins", []) if item.get("name") == manifest["name"]),
        None,
    )
    registered_path = resolve_registered_path(marketplace, registration)
    add_check(checks, "marketplace registration", registration is not None, str(marketplace))
    add_check(checks, "marketplace path", registered_path == plugin_root.resolve(), str(registered_path))
    return registration, registered_path


def resolve_registered_path(marketplace: Path, registration: dict[str, Any] | None) -> Path | None:
    if not registration:
        return None
    source_path = registration.get("source", {}).get("path", "")
    return (marketplace_base(marketplace) / source_path).resolve()


def check_hooks(checks: list[dict[str, Any]], plugin_root: Path, hooks_path: Path) -> dict[str, Any]:
    for command in hook_commands(read_json(hooks_path)):
        script = plugin_root / command
        add_check(checks, f"hook command {command}", script.exists(), str(script))
    hook_result = simulate_hook(plugin_root)
    add_check(checks, "hook simulation", hook_result["exit_code"] == 0, hook_result["stderr"])
    return hook_result


def check_dependencies(
    checks: list[dict[str, Any]],
    plugin_root: Path,
    codex_home: Path | None,
    config_path: Path | None,
    strict: bool,
    repo: Path | None,
) -> dict[str, Any]:
    dependencies = dependency_report(plugin_root, codex_home, config_path, strict, repo)
    add_check(checks, "dependencies ready", dependencies["ok"], dependencies["status"])
    return dependencies


def preflight_report(
    plugin_root: Path,
    manifest: dict[str, Any],
    marketplace: Path | None,
    registration: dict[str, Any] | None,
    registered_path: Path | None,
    skills: dict[str, Any],
    hook_result: dict[str, Any],
    dependencies: dict[str, Any],
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "ok": all(item["ok"] for item in checks),
        "plugin": plugin_summary(plugin_root, manifest),
        "marketplace": marketplace_summary(marketplace, registration, registered_path),
        "skills": skills,
        "hookSimulation": hook_result,
        "dependencies": dependencies,
        "checks": checks,
    }


def plugin_summary(plugin_root: Path, manifest: dict[str, Any]) -> dict[str, str]:
    return {
        "name": str(manifest.get("name")),
        "version": str(manifest.get("version")),
        "root": str(plugin_root),
    }


def marketplace_summary(
    marketplace: Path | None,
    registration: dict[str, Any] | None,
    registered_path: Path | None,
) -> dict[str, Any]:
    return {
        "path": str(marketplace) if marketplace else None,
        "registered": registration is not None,
        "registeredPath": str(registered_path) if registered_path else None,
    }
