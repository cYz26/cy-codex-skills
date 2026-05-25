from __future__ import annotations

from typing import Any


def context_pressure(inventory: dict[str, Any]) -> str:
    enabled_plugins = [item for item in inventory["globalPlugins"] if item["enabled"]]
    enabled_skills = [item for item in inventory["globalSkills"] if item["enabled"]]
    active_count = len(enabled_plugins) + len(enabled_skills)
    if active_count >= 3:
        return "high"
    if active_count:
        return "medium"
    return "low"
