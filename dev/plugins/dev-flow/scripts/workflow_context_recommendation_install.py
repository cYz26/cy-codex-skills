from __future__ import annotations

from pathlib import Path
from typing import Any

from workflow_context_recommendation_common import recommendation
from workflow_context_relevance import relevant_to_project, slug
from workflow_project_skill_paths import OFFICIAL_PROJECT_SKILL_PATH_KIND, official_project_skill_dir


def add_install_recommendations(
    inventory: dict[str, Any],
    repo: Path | None,
    signals: list[str],
    recommendations: list[dict[str, Any]],
    actions: list[dict[str, Any]],
) -> None:
    if repo is None:
        return
    active_project_skills = {item["name"] for item in inventory["projectSkills"]}
    for skill in inventory["installedSkills"]:
        if skill["name"] in active_project_skills or not relevant_to_project(skill, signals):
            continue
        add_project_skill_install(skill, repo, signals, recommendations, actions)


def add_project_skill_install(
    skill: dict[str, Any],
    repo: Path,
    signals: list[str],
    recommendations: list[dict[str, Any]],
    actions: list[dict[str, Any]],
) -> None:
    destination = official_project_skill_dir(repo, skill["name"])
    action = {
        "id": f"install-project-skill-{slug(skill['name'])}",
        "type": "install_project_skill",
        "title": f"Install project-local skill {skill['name']}",
        "reason": f"Installed skill matches project signals: {', '.join(signals)}.",
        "safety": "safe",
        "requiresAuthorization": True,
        "payload": {
            "sourcePath": skill["path"],
            "destinationPath": str(destination),
            "pathKind": OFFICIAL_PROJECT_SKILL_PATH_KIND,
            "repo": str(repo),
            "skillName": skill["name"],
        },
    }
    actions.append(action)
    recommendations.append(recommendation("install", action, action["reason"]))
