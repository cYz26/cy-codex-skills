from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from workflow_dependency_catalog import PROJECT_ORCHESTRATOR_SKILLS, REQUIRED_SUPERPOWERS_PROJECT_SKILLS


def ensure_project_local_skills(
    repo: Path,
    plugin_root: Path,
    codex_home: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    installed = []
    for skill in PROJECT_ORCHESTRATOR_SKILLS:
        source = plugin_root / "skills" / skill
        installed.append(install_project_skill(repo, "codex-project-orchestrator", skill, source, dry_run))
    for skill in REQUIRED_SUPERPOWERS_PROJECT_SKILLS:
        source = find_cached_plugin_skill(codex_home, "superpowers", skill)
        installed.append(install_project_skill(repo, "superpowers", skill, source, dry_run))
    return {
        "ok": all(item["ok"] for item in installed),
        "strategy": "project-local .codex/skills",
        "items": installed,
    }


def find_cached_plugin_skill(codex_home: Path, plugin: str, skill: str) -> Path | None:
    cache = codex_home / "plugins" / "cache"
    if not cache.exists():
        return None
    for path in cache.rglob(f"skills/{skill}/SKILL.md"):
        if plugin in path.parts:
            return path.parent
    return None


def install_project_skill(
    repo: Path,
    provider: str,
    skill: str,
    source: Path | None,
    dry_run: bool = False,
) -> dict[str, Any]:
    target = repo / ".codex" / "skills" / skill
    if source is None or not (source / "SKILL.md").exists():
        return install_result(provider, skill, source, target, False, "missing-source")
    if target.is_symlink():
        status = "already-linked" if target.resolve() == source.resolve() else "already-linked-existing-source"
        return install_result(provider, skill, source, target, (target / "SKILL.md").exists(), status)
    if target.exists():
        return install_result(provider, skill, source, target, (target / "SKILL.md").exists(), "already-present")
    if dry_run:
        return install_result(provider, skill, source, target, True, "would-link")
    target.parent.mkdir(parents=True, exist_ok=True)
    status = write_skill_tree(source, target)
    return install_result(provider, skill, source, target, (target / "SKILL.md").exists(), status)


def write_skill_tree(source: Path, target: Path) -> str:
    try:
        target.symlink_to(source, target_is_directory=True)
        return "linked"
    except OSError:
        shutil.copytree(source, target)
        return "copied"


def install_result(
    provider: str,
    skill: str,
    source: Path | None,
    target: Path,
    ok: bool,
    status: str,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "provider": provider,
        "skill": skill,
        "source": str(source) if source else None,
        "target": str(target),
        "status": status,
    }
