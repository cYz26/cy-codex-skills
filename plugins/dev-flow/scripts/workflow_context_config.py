from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


def read_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}
    return tomllib.loads(config_path.read_text())


def global_plugins(config: dict[str, Any]) -> list[dict[str, Any]]:
    plugins = []
    for key, settings in sorted(config.get("plugins", {}).items()):
        plugins.append(
            {
                "key": key,
                "name": plugin_name(key),
                "enabled": settings.get("enabled") is True,
                "settings": dict(settings),
            }
        )
    return plugins


def disabled_skill_paths(config: dict[str, Any]) -> set[str]:
    disabled = set()
    for entry in config.get("skills", {}).get("config", []):
        if entry.get("enabled") is False and entry.get("path"):
            disabled.add(str(entry["path"]))
    return disabled


def plugin_name(key: str) -> str:
    return key.split("@", 1)[0]
