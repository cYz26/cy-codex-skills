from __future__ import annotations

import hashlib
import re
import shutil
import uuid
from pathlib import Path
from typing import Any

from workflow_dependency_catalog import (
    OPENSPEC_WORKFLOW_SKILLS,
    PROJECT_ORCHESTRATOR_SKILLS,
)
from workflow_methodology import (
    MATT_LICENSE_FILENAME,
    adapt_matt_file_bytes,
    expected_project_skill_files,
    matt_skill_source_root,
    required_matt_skills,
    verify_matt_vendor,
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
    triggered_capabilities: set[str] | None = None,
    openspec_skill_root: Path | None = None,
    openspec_generation_planned: bool = False,
    openspec_expected_version: str = "1.7.0",
) -> dict[str, Any]:
    required_matt = required_matt_skills(triggered_capabilities or set())
    methodology_source = verify_matt_vendor(plugin_root, required_matt)
    if not methodology_source["ready"]:
        return {
            "ok": False,
            "strategy": "project-local .agents/skills",
            "path_kind": OFFICIAL_PROJECT_SKILL_PATH_KIND,
            "items": [
                install_result(
                    "mattpocock-skills",
                    skill,
                    matt_skill_source_root(plugin_root) / skill,
                    official_project_skill_dir(repo, skill),
                    False,
                    "vendor-source-drift",
                )
                for skill in required_matt
            ],
            "openspec_transaction": None,
            "methodology_source": methodology_source,
        }
    installed = []
    for skill in PROJECT_ORCHESTRATOR_SKILLS:
        source = plugin_root / "skills" / skill
        installed.append(install_project_skill(repo, "dev-flow", skill, source, dry_run, refresh_existing))
    matt_root = matt_skill_source_root(plugin_root)
    for skill in required_matt:
        installed.append(
            install_matt_project_skill(
                repo,
                skill,
                matt_root / skill,
                dry_run,
                refresh_existing,
            )
        )
    openspec_transaction: dict[str, Any] | None = None
    if openspec_skill_root is None and not openspec_generation_planned:
        project_skill_root = official_project_skill_dir(
            repo, OPENSPEC_WORKFLOW_SKILLS[0]
        ).parent
        verification = verify_generated_openspec_skill_root(
            project_skill_root,
            openspec_expected_version,
        )
        for skill in OPENSPEC_WORKFLOW_SKILLS:
            installed.append(
                install_result(
                    "openspec",
                    skill,
                    None,
                    official_project_skill_dir(repo, skill),
                    bool(verification["ok"]),
                    (
                        "already-present"
                        if verification["ok"]
                        else "missing-or-untrusted-project-skill"
                    ),
                )
            )
        openspec_transaction = {
            **verification,
            "status": (
                "current" if verification["ok"] else "project-skills-not-ready"
            ),
            "changed": False,
            "rolledBack": False,
        }
    else:
        openspec_items, openspec_transaction = install_generated_openspec_skill_batch(
            repo,
            openspec_skill_root,
            dry_run=dry_run,
            refresh_existing=refresh_existing,
            generation_planned=openspec_generation_planned,
            expected_version=openspec_expected_version,
        )
        installed.extend(openspec_items)
    return {
        "ok": all(item["ok"] for item in installed),
        "strategy": "project-local .agents/skills",
        "path_kind": OFFICIAL_PROJECT_SKILL_PATH_KIND,
        "items": installed,
        "openspec_transaction": openspec_transaction,
        "methodology_source": methodology_source,
    }


def install_matt_project_skill(
    repo: Path,
    skill: str,
    source: Path,
    dry_run: bool = False,
    refresh_existing: bool = False,
) -> dict[str, Any]:
    target = official_project_skill_dir(repo, skill)
    expected = expected_project_skill_files(skill)
    if not dry_run:
        guard_project_skill_write(repo, target)
    if not source.is_dir() or not expected:
        return install_result(
            "mattpocock-skills", skill, source, target, False, "missing-source"
        )
    exists = target.exists() or target.is_symlink()
    if exists and target.is_dir() and not target.is_symlink() and tree_matches_hashes(target, expected):
        return install_result(
            "mattpocock-skills", skill, source, target, True, "already-present"
        )
    if exists and not refresh_existing:
        return install_result(
            "mattpocock-skills", skill, source, target, False, "source-conflict"
        )
    if dry_run:
        status = "would-refresh-copy" if exists else "would-copy"
        return install_result("mattpocock-skills", skill, source, target, True, status)
    return materialize_matt_project_skill(repo, skill, source, target, expected, exists)


def materialize_matt_project_skill(
    repo: Path,
    skill: str,
    source: Path,
    target: Path,
    expected: dict[str, str],
    refreshing: bool,
) -> dict[str, Any]:
    transaction_id = uuid.uuid4().hex
    stage = target.parent / f".devflow-matt-stage-{skill}-{transaction_id}"
    backup = target.parent / f".devflow-matt-backup-{skill}-{transaction_id}"
    backed_up = False
    retain_backup = False
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        stage.mkdir()
        for source_file in sorted(source.rglob("*")):
            relative = source_file.relative_to(source).as_posix()
            if source_file.is_symlink():
                raise OSError(f"Matt source contains symlink: {relative}")
            if source_file.is_dir():
                (stage / relative).mkdir(parents=True, exist_ok=True)
                continue
            if not source_file.is_file():
                raise OSError(f"Matt source contains unsupported path: {relative}")
            target_file = stage / relative
            target_file.parent.mkdir(parents=True, exist_ok=True)
            adapted = adapt_matt_file_bytes(f"{skill}/{relative}", source_file.read_bytes())
            target_file.write_bytes(adapted)
            shutil.copymode(source_file, target_file)
        license_source = source.parent / MATT_LICENSE_FILENAME
        if license_source.is_symlink() or not license_source.is_file():
            raise OSError(f"Matt source license is missing or untrusted: {skill}")
        license_target = stage / MATT_LICENSE_FILENAME
        license_target.write_bytes(license_source.read_bytes())
        shutil.copymode(license_source, license_target)
        if not tree_matches_hashes(stage, expected):
            raise OSError(f"adapted Matt skill failed hash verification: {skill}")
        if target.exists() or target.is_symlink():
            target.replace(backup)
            backed_up = True
        stage.replace(target)
        remove_path(backup)
    except (OSError, UnicodeError, ValueError, shutil.Error) as error:
        remove_path(stage)
        if backed_up:
            retain_backup = True
            try:
                remove_path(target)
                if not (backup.exists() or backup.is_symlink()):
                    raise OSError("Matt rollback backup is missing")
                backup.replace(target)
            except (OSError, UnicodeError, ValueError, shutil.Error) as rollback_error:
                backup_available = backup.exists() or backup.is_symlink()
                retained_path = backup.absolute().relative_to(
                    Path(repo).absolute()
                ).as_posix()
                return install_result(
                    "mattpocock-skills",
                    skill,
                    source,
                    target,
                    False,
                    "transaction-rollback-failed",
                    error=str(error),
                    rollbackError=str(rollback_error),
                    rollbackStatus=(
                        "backup-retained" if backup_available else "backup-unavailable"
                    ),
                    retainedBackupPath=retained_path,
                )
            retain_backup = False
        return install_result(
            "mattpocock-skills",
            skill,
            source,
            target,
            False,
            "transaction-rolled-back",
            error=str(error),
        )
    finally:
        remove_path(stage)
        if not retain_backup:
            remove_path(backup)
    status = "refreshed-copy" if refreshing else "copied"
    return install_result("mattpocock-skills", skill, source, target, True, status)


def tree_matches_hashes(root: Path, expected: dict[str, str]) -> bool:
    if root.is_symlink() or not root.is_dir():
        return False
    actual: dict[str, Path] = {}
    try:
        paths = list(root.rglob("*"))
    except OSError:
        return False
    for path in paths:
        if path.is_symlink():
            return False
        if path.is_file():
            actual[path.relative_to(root).as_posix()] = path
        elif not path.is_dir():
            return False
    if set(actual) != set(expected):
        return False
    return all(
        hashlib.sha256(actual[relative].read_bytes()).hexdigest() == digest
        for relative, digest in expected.items()
    )


def verify_generated_openspec_skill_root(
    source_root: Path,
    expected_version: str,
) -> dict[str, Any]:
    expected = set(OPENSPEC_WORKFLOW_SKILLS)
    root_untrusted = source_root.is_symlink() or source_root.parent.is_symlink()
    try:
        children = (
            list(source_root.iterdir())
            if source_root.is_dir() and not root_untrusted
            else []
        )
    except OSError:
        children = []
        root_error = "unreadable"
    else:
        root_error = "symlinked-root" if root_untrusted else None
    actual = {
        path.name
        for path in children
        if path.name.startswith("openspec-")
    }
    mismatches: list[dict[str, Any]] = []
    if root_error is not None:
        mismatches.append({"kind": "unreadable-skill-root", "detail": root_error})
    if actual != expected:
        mismatches.append(
            {
                "kind": "skill-set",
                "missing": sorted(expected - actual),
                "additional": sorted(actual - expected),
            }
        )
    for skill in sorted(expected & actual):
        skill_dir = source_root / skill
        skill_file = skill_dir / "SKILL.md"
        if skill_dir.is_symlink() or not skill_dir.is_dir() or skill_file.is_symlink():
            mismatches.append({"kind": "symlinked-generated-source", "skill": skill})
            continue
        skill_files = trusted_regular_tree_files(skill_dir)
        if skill_files is None:
            mismatches.append({"kind": "untrusted-skill-tree", "skill": skill})
            continue
        if set(skill_files) != {"SKILL.md"}:
            mismatches.append(
                {
                    "kind": "skill-tree",
                    "skill": skill,
                    "missing": sorted({"SKILL.md"} - set(skill_files)),
                    "additional": sorted(set(skill_files) - {"SKILL.md"}),
                }
            )
            continue
        try:
            text = skill_files["SKILL.md"].read_bytes().decode("utf-8")
        except (OSError, UnicodeError):
            mismatches.append({"kind": "unreadable-skill-file", "skill": skill})
            continue
        generated_by = frontmatter_value(text, "generatedBy")
        name = frontmatter_value(text, "name")
        if name != skill:
            mismatches.append(
                {"kind": "skill-identity", "skill": skill, "expected": skill, "actual": name}
            )
        if generated_by != expected_version:
            mismatches.append(
                {
                    "kind": "generated-version",
                    "skill": skill,
                    "expected": expected_version,
                    "actual": generated_by,
                }
            )
        if "allowed-tools: Bash(openspec:*)" not in text:
            mismatches.append({"kind": "openspec-tool-identity", "skill": skill})
    return {
        "ok": not mismatches,
        "status": "verified" if not mismatches else "contract_mismatch",
        "expectedVersion": expected_version,
        "expectedSkills": list(OPENSPEC_WORKFLOW_SKILLS),
        "actualSkills": sorted(actual),
        "mismatches": mismatches,
        "sourceRoot": str(source_root),
    }


def frontmatter_value(text: str, key: str) -> str | None:
    frontmatter = text.split("---", 2)[1] if text.startswith("---") and text.count("---") >= 2 else ""
    match = re.search(rf"^\s*{re.escape(key)}:\s*[\"']?([^\"'\n]+)[\"']?\s*$", frontmatter, re.MULTILINE)
    return match.group(1).strip() if match else None


def install_generated_openspec_skill_batch(
    repo: Path,
    source_root: Path | None,
    *,
    dry_run: bool,
    refresh_existing: bool,
    generation_planned: bool,
    expected_version: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if source_root is not None:
        verification = verify_generated_openspec_skill_root(source_root, expected_version)
        if not verification["ok"]:
            items = [
                install_result(
                    "openspec",
                    skill,
                    source_root / skill,
                    official_project_skill_dir(repo, skill),
                    False,
                    "generated-source-contract-mismatch",
                )
                for skill in OPENSPEC_WORKFLOW_SKILLS
            ]
            return items, {**verification, "changed": False, "rolledBack": False}
    elif not (dry_run and generation_planned):
        items = [
            install_result(
                "openspec",
                skill,
                None,
                official_project_skill_dir(repo, skill),
                False,
                "missing-generated-source",
            )
            for skill in OPENSPEC_WORKFLOW_SKILLS
        ]
        return items, {
            "ok": False,
            "status": "missing-generated-source",
            "changed": False,
            "rolledBack": False,
        }

    plans: list[dict[str, Any]] = []
    conflicts = False
    for skill in OPENSPEC_WORKFLOW_SKILLS:
        source = source_root / skill if source_root is not None else None
        target = official_project_skill_dir(repo, skill)
        exists = target.exists() or target.is_symlink()
        if exists and not generated_skill_copy(target, "openspec"):
            status = "manual-source-conflict"
            ok = False
            action = "conflict"
            conflicts = True
        elif not exists:
            status = "would-copy-after-openspec-generation" if source is None else "would-copy"
            ok = True
            action = "copy"
        elif source is not None and skill_files_match(source, target):
            status = "already-present"
            ok = True
            action = "current"
        elif refresh_existing:
            status = "would-refresh-copy"
            ok = True
            action = "refresh"
        else:
            status = "generated-copy-refresh-required"
            ok = False
            action = "refresh-required"
            conflicts = True
        plans.append(
            {
                "skill": skill,
                "source": source,
                "target": target,
                "status": status,
                "ok": ok,
                "action": action,
            }
        )

    if conflicts:
        items = [
            install_result(
                "openspec",
                plan["skill"],
                plan["source"],
                plan["target"],
                False if plan["action"] in {"copy", "refresh"} else plan["ok"],
                "blocked-by-openspec-conflict"
                if plan["action"] in {"copy", "refresh"}
                else plan["status"],
            )
            for plan in plans
        ]
        return items, {
            "ok": False,
            "status": "manual-source-conflict",
            "changed": False,
            "rolledBack": False,
        }

    if dry_run:
        items = [
            install_result(
                "openspec",
                plan["skill"],
                plan["source"],
                plan["target"],
                plan["ok"],
                plan["status"],
            )
            for plan in plans
        ]
        return items, {
            "ok": True,
            "status": "planned",
            "changed": False,
            "rolledBack": False,
        }

    actions = [plan for plan in plans if plan["action"] in {"copy", "refresh"}]
    if not actions:
        items = [
            install_result("openspec", plan["skill"], plan["source"], plan["target"], True, plan["status"])
            for plan in plans
        ]
        return items, {"ok": True, "status": "current", "changed": False, "rolledBack": False}

    return materialize_openspec_skill_transaction(repo, plans, actions)


def materialize_openspec_skill_transaction(
    repo: Path,
    plans: list[dict[str, Any]],
    actions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    skill_root = official_project_skill_dir(repo, OPENSPEC_WORKFLOW_SKILLS[0]).parent
    transaction_id = uuid.uuid4().hex
    stage_root = skill_root / f".devflow-openspec-stage-{transaction_id}"
    backup_root = skill_root / f".devflow-openspec-backup-{transaction_id}"
    backed_up: list[tuple[Path, Path]] = []
    written: list[Path] = []
    retain_backup_root = False
    try:
        for plan in actions:
            guard_project_skill_write(repo, plan["target"])
        skill_root.mkdir(parents=True, exist_ok=True)
        stage_root.mkdir()
        backup_root.mkdir()
        for plan in actions:
            staged_skill = stage_root / plan["skill"]
            shutil.copytree(plan["source"], staged_skill, symlinks=True)
            staged_files = trusted_regular_tree_files(staged_skill)
            if staged_files is None or set(staged_files) != {"SKILL.md"}:
                raise OSError(f"staged skill is incomplete: {plan['skill']}")
        for plan in actions:
            target = plan["target"]
            backup = backup_root / plan["skill"]
            if target.exists() or target.is_symlink():
                replace_path(target, backup)
                backed_up.append((backup, target))
            replace_path(stage_root / plan["skill"], target)
            written.append(target)
    except (OSError, shutil.Error) as exc:
        rollback_errors: list[str] = []
        for target in reversed(written):
            try:
                remove_path(target)
            except OSError as rollback_error:
                rollback_errors.append(str(rollback_error))
        for backup, target in reversed(backed_up):
            try:
                if target.exists() or target.is_symlink():
                    remove_path(target)
                if not (backup.exists() or backup.is_symlink()):
                    raise OSError(f"OpenSpec rollback backup is missing: {backup.name}")
                replace_path(backup, target)
            except (OSError, shutil.Error) as rollback_error:
                rollback_errors.append(str(rollback_error))
        if rollback_errors:
            retain_backup_root = backup_root.exists() or backup_root.is_symlink()
            retained_path = (
                backup_root.absolute().relative_to(Path(repo).absolute()).as_posix()
                if retain_backup_root
                else None
            )
            items = [
                install_result(
                    "openspec",
                    plan["skill"],
                    plan["source"],
                    plan["target"],
                    False,
                    "transaction-rollback-failed",
                )
                if plan["action"] in {"copy", "refresh"}
                else install_result(
                    "openspec",
                    plan["skill"],
                    plan["source"],
                    plan["target"],
                    True,
                    plan["status"],
                )
                for plan in plans
            ]
            return items, {
                "ok": False,
                "status": "rollback-failed",
                "changed": False,
                "rolledBack": False,
                "error": str(exc),
                "rollbackErrors": rollback_errors,
                "rollbackStatus": (
                    "backup-retained" if retain_backup_root else "backup-unavailable"
                ),
                "retainedBackupPath": retained_path,
            }
        items = [
            install_result(
                "openspec",
                plan["skill"],
                plan["source"],
                plan["target"],
                False,
                "transaction-rolled-back",
            )
            if plan["action"] in {"copy", "refresh"}
            else install_result(
                "openspec",
                plan["skill"],
                plan["source"],
                plan["target"],
                True,
                plan["status"],
            )
            for plan in plans
        ]
        return items, {
            "ok": False,
            "status": "rolled-back",
            "changed": False,
            "rolledBack": True,
            "error": str(exc),
        }
    finally:
        remove_path(stage_root)
        if not retain_backup_root:
            remove_path(backup_root)

    statuses = {
        plan["skill"]: "refreshed-copy" if plan["action"] == "refresh" else "copied"
        for plan in actions
    }
    items = [
        install_result(
            "openspec",
            plan["skill"],
            plan["source"],
            plan["target"],
            True,
            statuses.get(plan["skill"], plan["status"]),
        )
        for plan in plans
    ]
    return items, {"ok": True, "status": "applied", "changed": True, "rolledBack": False}


def replace_path(source: Path, target: Path) -> None:
    source.replace(target)


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)


def install_project_skill(
    repo: Path,
    source_kind: str,
    skill: str,
    source: Path | None,
    dry_run: bool = False,
    refresh_existing: bool = False,
    refresh_generated_copy: bool = False,
    copy_source: bool = False,
) -> dict[str, Any]:
    target = official_project_skill_dir(repo, skill)
    if not dry_run:
        guard_project_skill_write(repo, target)
    if source is None or not (source / "SKILL.md").exists():
        return install_result(source_kind, skill, source, target, False, "missing-source")
    if target.is_symlink():
        if copy_source:
            if not refresh_existing:
                return install_result(source_kind, skill, source, target, False, "source-conflict")
            if dry_run:
                return install_result(source_kind, skill, source, target, True, "would-refresh-copy")
            target.unlink()
            shutil.copytree(source, target)
            return install_result(source_kind, skill, source, target, True, "refreshed-copy")
        if target.resolve() == source.resolve():
            return install_result(source_kind, skill, source, target, (target / "SKILL.md").exists(), "already-linked")
        if refresh_existing:
            if dry_run:
                return install_result(source_kind, skill, source, target, True, "would-refresh-link")
            target.unlink()
            status = write_skill_tree(source, target)
            refresh_status = "refreshed-link" if status == "linked" else "refreshed-copy"
            return install_result(source_kind, skill, source, target, (target / "SKILL.md").exists(), refresh_status)
        if source_kind in {"dev-flow", "mattpocock-skills"}:
            return install_result(source_kind, skill, source, target, False, "source-conflict")
        status = "already-linked-existing-source"
        return install_result(source_kind, skill, source, target, (target / "SKILL.md").exists(), status)
    if target.exists():
        target_skill = target / "SKILL.md"
        source_skill = source / "SKILL.md"
        if source_kind in {"dev-flow", "mattpocock-skills"} and target_skill.is_symlink():
            if target_skill.resolve() == source_skill.resolve():
                return install_result(source_kind, skill, source, target, True, "already-linked")
            return install_result(source_kind, skill, source, target, False, "source-conflict")
        if (
            refresh_existing
            and refresh_generated_copy
            and target.is_dir()
            and generated_skill_copy(target, source_kind)
        ):
            if dry_run:
                return install_result(source_kind, skill, source, target, True, "would-refresh-copy")
            shutil.rmtree(target)
            status = write_skill_tree(source, target)
            refresh_status = "refreshed-link" if status == "linked" else "refreshed-copy"
            return install_result(source_kind, skill, source, target, (target / "SKILL.md").exists(), refresh_status)
        matches = (
            skill_trees_match(source, target)
            if copy_source or source_kind == "dev-flow"
            else skill_files_match(source, target)
        )
        if source_kind in {"dev-flow", "mattpocock-skills"} and not matches:
            return install_result(source_kind, skill, source, target, False, "source-conflict")
        return install_result(source_kind, skill, source, target, (target / "SKILL.md").exists(), "already-present")
    if dry_run:
        return install_result(
            source_kind,
            skill,
            source,
            target,
            True,
            "would-copy" if copy_source else "would-link",
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    if copy_source:
        shutil.copytree(source, target)
        status = "copied"
    else:
        status = write_skill_tree(source, target)
    return install_result(source_kind, skill, source, target, (target / "SKILL.md").exists(), status)


def write_skill_tree(source: Path, target: Path) -> str:
    try:
        target.symlink_to(source, target_is_directory=True)
        return "linked"
    except OSError:
        shutil.copytree(source, target)
        return "copied"


def generated_skill_copy(target: Path, source_kind: str) -> bool:
    if source_kind != "openspec":
        return False
    files = trusted_regular_tree_files(target)
    if files is None or set(files) != {"SKILL.md"}:
        return False
    try:
        text = files["SKILL.md"].read_bytes().decode("utf-8")
    except (OSError, UnicodeError):
        return False
    return bool(
        frontmatter_value(text, "name") == target.name
        and frontmatter_value(text, "generatedBy")
    )


def skill_files_match(source: Path, target: Path) -> bool:
    source_file = source / "SKILL.md"
    target_file = target / "SKILL.md"
    if not source_file.is_file() or not target_file.is_file():
        return False
    return hashlib.sha256(source_file.read_bytes()).digest() == hashlib.sha256(
        target_file.read_bytes()
    ).digest()


def skill_trees_match(source: Path, target: Path) -> bool:
    source_files = trusted_regular_tree_files(source)
    target_files = trusted_regular_tree_files(target)
    if source_files is None or target_files is None:
        return False
    if set(source_files) != set(target_files):
        return False
    try:
        return all(
            hashlib.sha256(source_files[name].read_bytes()).digest()
            == hashlib.sha256(target_files[name].read_bytes()).digest()
            for name in source_files
        )
    except OSError:
        return False


def trusted_regular_tree_files(root: Path) -> dict[str, Path] | None:
    if root.is_symlink() or not root.is_dir():
        return None
    try:
        paths = list(root.rglob("*"))
    except OSError:
        return None
    files: dict[str, Path] = {}
    for path in paths:
        if path.is_symlink():
            return None
        if path.is_file():
            files[path.relative_to(root).as_posix()] = path
        elif not path.is_dir():
            return None
    return files


def install_result(
    source_kind: str,
    skill: str,
    source: Path | None,
    target: Path,
    ok: bool,
    status: str,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "sourceKind": source_kind,
        "skill": skill,
        "source": str(source) if source else None,
        "target": str(target),
        "path_kind": OFFICIAL_PROJECT_SKILL_PATH_KIND,
        "status": status,
        **extra,
    }
