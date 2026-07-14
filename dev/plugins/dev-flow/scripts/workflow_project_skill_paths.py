from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any, Iterable


OFFICIAL_PROJECT_SKILL_ROOT = Path(".agents") / "skills"
LEGACY_PROJECT_SKILL_ROOT = Path(".codex") / "skills"
OFFICIAL_PROJECT_SKILL_PATH_KIND = "official_repo_skill_path"
LEGACY_PROJECT_SKILL_PATH_KIND = "legacy_codex_skill_path"


class ProjectSkillOwnershipError(RuntimeError):
    pass


def official_project_skill_dir(repo: Path, skill: str) -> Path:
    return repo / OFFICIAL_PROJECT_SKILL_ROOT / skill


def official_project_skill_file(repo: Path, skill: str) -> Path:
    return official_project_skill_dir(repo, skill) / "SKILL.md"


def guard_project_skill_write(repo: Path, target: Path) -> Path:
    """Reject writes that can escape through a symlinked project skill parent."""
    repo_input = Path(repo).absolute()
    target_input = Path(target).absolute()
    try:
        relative_target = target_input.relative_to(repo_input)
    except ValueError as error:
        raise ProjectSkillOwnershipError(
            f"project skill target is outside repository: {target_input}"
        ) from error
    repo = repo_input.resolve()
    target = repo / relative_target
    skill_root = repo / OFFICIAL_PROJECT_SKILL_ROOT
    try:
        target.relative_to(skill_root)
    except ValueError as error:
        raise ProjectSkillOwnershipError(f"project skill target is outside {skill_root}: {target}") from error
    parents = [repo / ".agents", skill_root]
    current = skill_root
    for part in target.relative_to(skill_root).parts[:-1]:
        current = current / part
        parents.append(current)
    for parent in parents:
        if parent.is_symlink():
            raise ProjectSkillOwnershipError(f"project skill parent must not be a symlink: {parent}")
        if parent.exists() and not parent.is_dir():
            raise ProjectSkillOwnershipError(f"project skill parent is not a directory: {parent}")
        if parent.exists():
            try:
                parent.resolve().relative_to(repo)
            except ValueError as error:
                raise ProjectSkillOwnershipError(
                    f"project skill parent resolves outside repository: {parent}"
                ) from error
    return target


def legacy_project_skill_dir(repo: Path, skill: str) -> Path:
    return repo / LEGACY_PROJECT_SKILL_ROOT / skill


def legacy_project_skill_file(repo: Path, skill: str) -> Path:
    return legacy_project_skill_dir(repo, skill) / "SKILL.md"


def skill_dir_exists(path: Path) -> bool:
    return (path / "SKILL.md").exists()


def skill_layout_migration_command(repo: Path, apply: bool = False, script_path: Path | None = None) -> list[str]:
    command = [
        "python3",
        str(script_path or Path("activate_project_dependencies.py")),
        "--repo",
        str(repo),
        "--skip-official-installs",
        "--migrate-official-skill-layout",
    ]
    command.append("--apply" if apply else "--dry-run")
    command.append("--json")
    return command


def scan_project_skill_layout(
    repo: Path,
    managed_skills: Iterable[str],
    script_path: Path | None = None,
) -> dict[str, Any]:
    items = []
    for skill in managed_skills:
        official = official_project_skill_dir(repo, skill)
        legacy = legacy_project_skill_dir(repo, skill)
        official_exists = skill_dir_exists(official)
        legacy_exists = skill_dir_exists(legacy)
        if official_exists and legacy_exists:
            if skill_trees_match(official, legacy):
                items.append(layout_item(skill, "legacy_duplicate", official, legacy))
            else:
                items.append(layout_item(skill, "skill_layout_conflict", official, legacy))
        elif legacy_exists:
            items.append(layout_item(skill, "legacy_detected", official, legacy))
    return {
        "status": aggregate_layout_status(items),
        "pathKind": OFFICIAL_PROJECT_SKILL_PATH_KIND,
        "legacyPathKind": LEGACY_PROJECT_SKILL_PATH_KIND,
        "dryRunCommand": skill_layout_migration_command(repo, apply=False, script_path=script_path),
        "applyCommand": skill_layout_migration_command(repo, apply=True, script_path=script_path),
        "items": items,
    }


def layout_item(skill: str, status: str, official: Path, legacy: Path) -> dict[str, Any]:
    item = {
        "skill": skill,
        "status": status,
        "official_path": str(official),
        "legacy_path": str(legacy),
        "official_skill_path": str(official / "SKILL.md"),
        "legacy_skill_path": str(legacy / "SKILL.md"),
        "path_kind": OFFICIAL_PROJECT_SKILL_PATH_KIND,
        "legacy_path_kind": LEGACY_PROJECT_SKILL_PATH_KIND,
        "next_action": layout_next_action(status),
    }
    return item


def aggregate_layout_status(items: list[dict[str, Any]]) -> str:
    statuses = {item["status"] for item in items}
    if "skill_layout_conflict" in statuses:
        return "skill_layout_conflict"
    if "legacy_detected" in statuses:
        return "legacy_detected"
    if "legacy_duplicate" in statuses:
        return "legacy_duplicate"
    if "manual_review_required" in statuses:
        return "manual_review_required"
    return "current"


def layout_next_action(status: str) -> str:
    if status == "legacy_detected":
        return "Run the dry-run migration command before applying official skill layout migration."
    if status == "legacy_duplicate":
        return "Review and cleanup the legacy .codex/skills entry after confirming the official copy."
    if status == "skill_layout_conflict":
        return "Resolve the conflict with manual selection before migration."
    if status == "manual_review_required":
        return "Review unmanaged legacy skill manually; DevFlow will not migrate it automatically."
    if status == "authoritative_source_install_required":
        return "Install the triggered skill from its pinned DevFlow vendor source; preserve the legacy path."
    if status == "legacy_preserved_authoritative_source":
        return "Use the verified project-local copy and preserve the legacy path for separate review."
    return "No skill layout action needed."


def migrate_project_skill_layout(
    repo: Path,
    managed_skills: Iterable[str],
    dry_run: bool,
    script_path: Path | None = None,
    authoritative_source_skills: Iterable[str] = (),
) -> dict[str, Any]:
    managed = set(managed_skills)
    authoritative = set(authoritative_source_skills)
    items = []
    for skill in sorted(managed):
        official = official_project_skill_dir(repo, skill)
        legacy = legacy_project_skill_dir(repo, skill)
        if not skill_dir_exists(legacy):
            continue
        official_exists = skill_dir_exists(official)
        if skill in authoritative:
            status = (
                "legacy_preserved_authoritative_source"
                if official_exists
                else "authoritative_source_install_required"
            )
            items.append(migration_item(skill, status, official, legacy))
            continue
        if official_exists and skill_trees_match(official, legacy):
            items.append(migration_item(skill, "legacy_duplicate", official, legacy))
            continue
        if official_exists:
            items.append(migration_item(skill, "skill_layout_conflict", official, legacy, ok=False))
            continue
        if dry_run:
            items.append(migration_item(skill, "would_migrate", official, legacy))
            continue
        write_skill_tree_from_legacy(legacy, official)
        items.append(
            migration_item(
                skill,
                "migrated",
                official,
                legacy,
                rollback={"remove_created_path": str(official)},
            )
        )
    items.extend(unmanaged_legacy_skill_items(repo, managed))
    ok = all(item.get("ok", True) for item in items)
    return {
        "ok": ok,
        "mode": "dry-run" if dry_run else "apply",
        "status": migration_status(items, ok),
        "pathKind": OFFICIAL_PROJECT_SKILL_PATH_KIND,
        "dryRunCommand": skill_layout_migration_command(repo, apply=False, script_path=script_path),
        "applyCommand": skill_layout_migration_command(repo, apply=True, script_path=script_path),
        "items": items,
    }


def migration_item(
    skill: str,
    status: str,
    official: Path,
    legacy: Path,
    ok: bool = True,
    rollback: dict[str, Any] | None = None,
) -> dict[str, Any]:
    item = layout_item(skill, status, official, legacy)
    item["ok"] = ok
    item["rollback"] = rollback or {}
    return item


def unmanaged_legacy_skill_items(repo: Path, managed: set[str]) -> list[dict[str, Any]]:
    legacy_root = repo / LEGACY_PROJECT_SKILL_ROOT
    if not legacy_root.exists():
        return []
    items = []
    for skill_file in sorted(legacy_root.glob("*/SKILL.md")):
        skill = skill_file.parent.name
        if skill in managed:
            continue
        item = layout_item(skill, "manual_review_required", official_project_skill_dir(repo, skill), skill_file.parent)
        item["ok"] = True
        item["rollback"] = {}
        items.append(item)
    return items


def migration_status(items: list[dict[str, Any]], ok: bool) -> str:
    if not ok:
        return "blocked"
    statuses = {item["status"] for item in items}
    if "migrated" in statuses:
        return "applied"
    if "would_migrate" in statuses:
        return "migration_available"
    if "authoritative_source_install_required" in statuses:
        return "source_install_required"
    if "legacy_preserved_authoritative_source" in statuses:
        return "legacy_preserved"
    if statuses:
        return aggregate_layout_status(items)
    return "current"


def skill_trees_match(left: Path, right: Path) -> bool:
    try:
        if left.is_symlink() and right.is_symlink() and left.resolve() == right.resolve():
            return True
    except OSError:
        return False
    return skill_tree_digest(left) == skill_tree_digest(right)


def skill_tree_digest(root: Path) -> str | None:
    source = root.resolve() if root.is_symlink() else root
    if not skill_dir_exists(source):
        return None
    digest = hashlib.sha256()
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(source).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).hexdigest().encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def write_skill_tree_from_legacy(legacy: Path, official: Path) -> str:
    repo = official.parents[2]
    guard_project_skill_write(repo, official)
    official.parent.mkdir(parents=True, exist_ok=True)
    if legacy.is_symlink():
        official.symlink_to(legacy.resolve(), target_is_directory=True)
        return "linked"
    shutil.copytree(legacy, official)
    return "copied"
