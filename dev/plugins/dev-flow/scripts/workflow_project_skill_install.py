from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

from workflow_dependency_catalog import (
    OPENSPEC_WORKFLOW_SKILLS,
    PROJECT_ORCHESTRATOR_SKILLS,
    STRICT_SUPERPOWERS_BASE_PROJECT_SKILLS,
    STRICT_SUPERPOWERS_CONDITIONAL_PROJECT_SKILLS,
)
from workflow_project_skill_paths import (
    OFFICIAL_PROJECT_SKILL_PATH_KIND,
    guard_project_skill_write,
    official_project_skill_dir,
)


def ensure_project_local_skills(
    repo: Path,
    plugin_root: Path,
    codex_home: Path,
    dry_run: bool = False,
    refresh_existing: bool = False,
    selection: dict[str, Any] | None = None,
    provider_diagnosis: dict[str, Any] | None = None,
    triggered_capabilities: set[str] | None = None,
) -> dict[str, Any]:
    installed = []
    for skill in PROJECT_ORCHESTRATOR_SKILLS:
        source = plugin_root / "skills" / skill
        installed.append(install_project_skill(repo, "dev-flow", skill, source, dry_run, refresh_existing))
    methodology = selection.get("effectiveMethodologyProfile") if selection else "core"
    if methodology == "strict-superpowers":
        root_value = (provider_diagnosis or {}).get("providers", {}).get("superpowers", {}).get("root")
        root = Path(root_value) if root_value else None
        for skill in strict_project_skills(triggered_capabilities or set()):
            source = root / "skills" / skill if root else find_cached_plugin_skill(codex_home, "superpowers", skill)
            installed.append(
                install_project_skill(
                    repo,
                    "superpowers",
                    skill,
                    source,
                    dry_run,
                    refresh_existing,
                    deferred_source=dry_run,
                )
            )
    elif methodology == "lean-matt":
        matt_report = (
            (provider_diagnosis or {})
            .get("providers", {})
            .get("mattpocock-skills", {})
        )
        skills = matt_report.get("implicitSkills", [])
        root = Path(str(matt_report.get("root") or (repo / ".agents" / "skills")))
        expected_hashes = matt_report.get("expectedSkillHashes", {})
        nonlocal_skills = set(matt_report.get("nonLocalSkills", []))
        for skill in skills:
            source = root / skill
            source_file = source / "SKILL.md"
            expected_hash = expected_hashes.get(skill)
            if source_file.exists() and (
                skill in nonlocal_skills
                or not expected_hash
                or hashlib.sha256(source_file.read_bytes()).hexdigest() != expected_hash
            ):
                installed.append(
                    install_result(
                        "mattpocock-skills",
                        skill,
                        source,
                        official_project_skill_dir(repo, skill),
                        False,
                        "source-conflict",
                    )
                )
                continue
            installed.append(
                install_project_skill(
                    repo,
                    "mattpocock-skills",
                    skill,
                    source,
                    dry_run,
                    refresh_existing,
                    deferred_source=dry_run,
                )
            )
    for skill in OPENSPEC_WORKFLOW_SKILLS:
        source = repo / ".codex" / "skills" / skill
        installed.append(install_generated_project_skill(repo, "openspec", skill, source, dry_run, refresh_existing))
    return {
        "ok": all(item["ok"] for item in installed),
        "strategy": "project-local .agents/skills",
        "path_kind": OFFICIAL_PROJECT_SKILL_PATH_KIND,
        "items": installed,
    }


def strict_project_skills(triggered_capabilities: set[str]) -> list[str]:
    from workflow_provider_registry import default_plugin_root, load_provider_registry

    registry = load_provider_registry(default_plugin_root())
    conditional = set(STRICT_SUPERPOWERS_CONDITIONAL_PROJECT_SKILLS)
    triggered = {
        skill
        for capability in triggered_capabilities
        for skill in registry["capabilities"].get(capability, {}).get("strict-superpowers", [])
        if skill in conditional
    }
    activation_conditionals = {
        "change-review": {"receiving-code-review"},
        "execution-orchestration": {
            "using-git-worktrees",
            "finishing-a-development-branch",
        },
    }
    for capability in triggered_capabilities:
        triggered.update(activation_conditionals.get(capability, set()))
    return [*STRICT_SUPERPOWERS_BASE_PROJECT_SKILLS, *sorted(triggered)]


def find_cached_plugin_skill(codex_home: Path, plugin: str, skill: str) -> Path | None:
    cache = codex_home / "plugins" / "cache"
    if not cache.exists():
        return None
    candidates: list[Path] = []
    for path in sorted(cache.rglob(f"skills/{skill}/SKILL.md")):
        if plugin in path.parts:
            candidates.append(path.parent)
    if candidates:
        return candidates[-1]
    return None


def install_project_skill(
    repo: Path,
    provider: str,
    skill: str,
    source: Path | None,
    dry_run: bool = False,
    refresh_existing: bool = False,
    refresh_generated_copy: bool = False,
    deferred_source: bool = False,
) -> dict[str, Any]:
    target = official_project_skill_dir(repo, skill)
    if not dry_run:
        guard_project_skill_write(repo, target)
    if source is None or not (source / "SKILL.md").exists():
        if dry_run and deferred_source:
            return install_result(provider, skill, source, target, True, "would-link-after-provider-install")
        return install_result(provider, skill, source, target, False, "missing-source")
    if target.is_symlink():
        if target.resolve() == source.resolve():
            return install_result(provider, skill, source, target, (target / "SKILL.md").exists(), "already-linked")
        if refresh_existing:
            if dry_run:
                return install_result(provider, skill, source, target, True, "would-refresh-link")
            target.unlink()
            status = write_skill_tree(source, target)
            refresh_status = "refreshed-link" if status == "linked" else "refreshed-copy"
            return install_result(provider, skill, source, target, (target / "SKILL.md").exists(), refresh_status)
        if provider in {"dev-flow", "mattpocock-skills"}:
            return install_result(provider, skill, source, target, False, "source-conflict")
        status = "already-linked-existing-source"
        return install_result(provider, skill, source, target, (target / "SKILL.md").exists(), status)
    if target.exists():
        target_skill = target / "SKILL.md"
        source_skill = source / "SKILL.md"
        if provider in {"dev-flow", "mattpocock-skills"} and target_skill.is_symlink():
            if target_skill.resolve() == source_skill.resolve():
                return install_result(provider, skill, source, target, True, "already-linked")
            return install_result(provider, skill, source, target, False, "source-conflict")
        if (
            refresh_existing
            and refresh_generated_copy
            and target.is_dir()
            and generated_skill_copy(target, provider)
        ):
            if dry_run:
                return install_result(provider, skill, source, target, True, "would-refresh-copy")
            shutil.rmtree(target)
            status = write_skill_tree(source, target)
            refresh_status = "refreshed-link" if status == "linked" else "refreshed-copy"
            return install_result(provider, skill, source, target, (target / "SKILL.md").exists(), refresh_status)
        if provider in {"dev-flow", "mattpocock-skills"} and not skill_files_match(source, target):
            return install_result(provider, skill, source, target, False, "source-conflict")
        return install_result(provider, skill, source, target, (target / "SKILL.md").exists(), "already-present")
    if dry_run:
        return install_result(provider, skill, source, target, True, "would-link")
    target.parent.mkdir(parents=True, exist_ok=True)
    status = write_skill_tree(source, target)
    return install_result(provider, skill, source, target, (target / "SKILL.md").exists(), status)


def install_generated_project_skill(
    repo: Path,
    provider: str,
    skill: str,
    source: Path,
    dry_run: bool = False,
    refresh_existing: bool = False,
) -> dict[str, Any]:
    target = official_project_skill_dir(repo, skill)
    if not (source / "SKILL.md").exists():
        if (target / "SKILL.md").exists():
            return install_result(provider, skill, source, target, True, "already-present-without-generated-source")
        return install_result(provider, skill, source, target, True, "missing-generated-source")
    return install_project_skill(
        repo,
        provider,
        skill,
        source,
        dry_run,
        refresh_existing,
        refresh_generated_copy=True,
    )


def write_skill_tree(source: Path, target: Path) -> str:
    try:
        target.symlink_to(source, target_is_directory=True)
        return "linked"
    except OSError:
        shutil.copytree(source, target)
        return "copied"


def generated_skill_copy(target: Path, provider: str) -> bool:
    if provider != "openspec":
        return False
    skill_file = target / "SKILL.md"
    if not skill_file.exists():
        return False
    try:
        text = skill_file.read_text()
    except OSError:
        return False
    return "author: openspec" in text or "generatedBy:" in text


def skill_files_match(source: Path, target: Path) -> bool:
    source_file = source / "SKILL.md"
    target_file = target / "SKILL.md"
    if not source_file.is_file() or not target_file.is_file():
        return False
    return hashlib.sha256(source_file.read_bytes()).digest() == hashlib.sha256(
        target_file.read_bytes()
    ).digest()


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
        "path_kind": OFFICIAL_PROJECT_SKILL_PATH_KIND,
        "status": status,
    }
