from __future__ import annotations

from pathlib import Path
from typing import Any

from workflow_context_recommendation_common import recommendation
from workflow_context_relevance import slug


def add_cleanup_recommendations(
    inventory: dict[str, Any],
    config_path: Path,
    findings: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    actions: list[dict[str, Any]],
) -> None:
    for plugin in inventory["globalPlugins"]:
        if plugin["enabled"]:
            add_global_plugin_cleanup(plugin, config_path, findings, recommendations, actions)
    for skill in inventory["globalSkills"]:
        if skill["enabled"]:
            add_global_skill_cleanup(skill, config_path, findings, recommendations, actions)


def add_global_plugin_cleanup(
    plugin: dict[str, Any],
    config_path: Path,
    findings: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    actions: list[dict[str, Any]],
) -> None:
    action = {
        "id": f"disable-global-plugin-{slug(plugin['key'])}",
        "type": "disable_global_plugin",
        "title": f"Disable global plugin {plugin['key']}",
        "reason": "Global plugins occupy every session; prefer project-local tools when possible.",
        "safety": "safe",
        "requiresAuthorization": True,
        "payload": {"configPath": str(config_path), "pluginKey": plugin["key"]},
    }
    actions.append(action)
    findings.append({"level": "warning", "message": f"Global plugin is enabled: {plugin['key']}"})
    recommendations.append(recommendation("cleanup", action, action["reason"]))


def add_global_skill_cleanup(
    skill: dict[str, Any],
    config_path: Path,
    findings: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    actions: list[dict[str, Any]],
) -> None:
    action = {
        "id": f"disable-global-skill-{slug(skill['name'])}",
        "type": "disable_global_skill",
        "title": f"Disable global skill {skill['name']}",
        "reason": "Global skills occupy baseline context; prefer repo-local activation.",
        "safety": "safe",
        "requiresAuthorization": True,
        "payload": {"configPath": str(config_path), "skillPath": skill["path"], "skillName": skill["name"]},
    }
    actions.append(action)
    findings.append({"level": "warning", "message": f"Global skill is active: {skill['name']}"})
    recommendations.append(recommendation("cleanup", action, action["reason"]))
