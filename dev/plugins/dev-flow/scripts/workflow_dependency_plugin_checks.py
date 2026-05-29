from __future__ import annotations

from pathlib import Path
from typing import Any


def add_skill_checks(
    checks: list[dict[str, Any]],
    codex_home: Path,
    plugin: str,
    skills: list[str],
    required: bool,
) -> None:
    for skill in skills:
        add_skill_check(checks, codex_home, plugin, skill, required)


def check_plugin_activation(
    checks: list[dict[str, Any]],
    config: dict[str, Any],
    plugin: str,
    label: str,
    required: bool,
) -> None:
    enabled = plugin_enabled(config, plugin)
    detail = "enabled" if enabled else "missing/disabled"
    add_check(checks, f"{label}: {plugin}", enabled, required, detail)


def check_global_plugin_inactive(
    checks: list[dict[str, Any]],
    config: dict[str, Any],
    plugin: str,
    required: bool = True,
) -> None:
    enabled = plugin_enabled(config, plugin)
    detail = "globally enabled" if enabled else "not globally enabled"
    add_check(checks, f"global plugin inactive: {plugin}", not enabled, required, detail)


def check_plugin_installed(
    checks: list[dict[str, Any]],
    codex_home: Path,
    plugin: str,
    label: str,
    required: bool,
) -> None:
    installed = plugin_installed(codex_home, plugin)
    detail = "installed" if installed else "missing"
    add_check(checks, f"{label}: {plugin}", installed, required, detail)


def plugin_enabled(config: dict[str, Any], plugin: str) -> bool:
    plugins = config.get("plugins", {})
    for name, settings in plugins.items():
        if name.startswith(f"{plugin}@") and settings.get("enabled") is True:
            return True
    return False


def plugin_installed(codex_home: Path, plugin: str) -> bool:
    cache = codex_home / "plugins" / "cache"
    if not cache.exists():
        return False
    return any(plugin in path.parts for path in cache.rglob("skills"))


def add_skill_check(
    checks: list[dict[str, Any]],
    codex_home: Path,
    plugin: str,
    skill: str,
    required: bool,
) -> None:
    path = find_skill(codex_home, plugin, skill)
    detail = str(path) if path else "missing"
    add_check(checks, f"external skill available: {plugin}:{skill}", path is not None, required, detail)


def find_skill(codex_home: Path, plugin: str, skill: str) -> Path | None:
    cache = codex_home / "plugins" / "cache"
    if not cache.exists():
        return None
    for path in cache.rglob(f"skills/{skill}/SKILL.md"):
        if plugin in path.parts:
            return path
    return None


def add_check(checks: list[dict[str, Any]], name: str, ok: bool, required: bool, detail: str = "") -> None:
    checks.append({"name": name, "ok": bool(ok), "required": bool(required), "detail": detail})
