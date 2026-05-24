from __future__ import annotations

from pathlib import Path
from typing import Any

from workflow_context_config import disabled_skill_paths


def global_skills(codex_home: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    skills_root = codex_home / "skills"
    if not skills_root.exists():
        return []
    disabled = disabled_skill_paths(config)
    return [
        {
            "name": path.parent.name,
            "path": str(path),
            "enabled": str(path) not in disabled,
        }
        for path in sorted(skills_root.glob("*/SKILL.md"))
    ]


def project_skills(repo: Path | None) -> list[dict[str, Any]]:
    if repo is None:
        return []
    skills_root = repo / ".codex" / "skills"
    if not skills_root.exists():
        return []
    return [{"name": path.parent.name, "path": str(path)} for path in sorted(skills_root.glob("*/SKILL.md"))]


def installed_cache_skills(codex_home: Path) -> list[dict[str, Any]]:
    cache = codex_home / "plugins" / "cache"
    if not cache.exists():
        return []
    skills = []
    for path in sorted(cache.rglob("skills/*/SKILL.md")):
        plugin, source = cache_plugin_parts(cache, path)
        skills.append(
            {
                "name": path.parent.name,
                "path": str(path),
                "plugin": plugin,
                "source": source,
                "key": f"{plugin}@{source}" if source else plugin,
            }
        )
    return skills


def cache_plugin_parts(cache: Path, skill_path: Path) -> tuple[str, str]:
    relative = skill_path.relative_to(cache)
    parts = relative.parts
    if len(parts) >= 4:
        return parts[1], parts[0]
    return "unknown", ""
