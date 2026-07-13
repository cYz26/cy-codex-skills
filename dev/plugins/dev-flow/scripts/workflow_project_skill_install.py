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
    openspec_skill_root: Path | None = None,
    openspec_generation_planned: bool = False,
    openspec_expected_version: str = "1.6.0",
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
    openspec_transaction: dict[str, Any] | None = None
    if openspec_skill_root is None and not openspec_generation_planned:
        for skill in OPENSPEC_WORKFLOW_SKILLS:
            source = repo / ".codex" / "skills" / skill
            installed.append(
                install_generated_project_skill(
                    repo,
                    "openspec",
                    skill,
                    source,
                    dry_run,
                    refresh_existing,
                )
            )
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
    }


def verify_generated_openspec_skill_root(
    source_root: Path,
    expected_version: str,
) -> dict[str, Any]:
    expected = set(OPENSPEC_WORKFLOW_SKILLS)
    try:
        children = list(source_root.iterdir()) if source_root.is_dir() else []
    except OSError as exc:
        children = []
        root_error = str(exc)
    else:
        root_error = None
    actual = {
        path.name
        for path in children
        if path.is_dir() and path.name.startswith("openspec-")
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
        if skill_dir.is_symlink() or skill_file.is_symlink():
            mismatches.append({"kind": "symlinked-generated-source", "skill": skill})
            continue
        if not skill_file.is_file():
            mismatches.append({"kind": "missing-skill-file", "skill": skill})
            continue
        try:
            text = skill_file.read_text()
        except OSError as exc:
            mismatches.append({"kind": "unreadable-skill-file", "skill": skill, "detail": str(exc)})
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
    try:
        for plan in actions:
            guard_project_skill_write(repo, plan["target"])
        skill_root.mkdir(parents=True, exist_ok=True)
        stage_root.mkdir()
        backup_root.mkdir()
        for plan in actions:
            shutil.copytree(plan["source"], stage_root / plan["skill"])
            if not (stage_root / plan["skill"] / "SKILL.md").is_file():
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
        for target in reversed(written):
            remove_path(target)
        for backup, target in reversed(backed_up):
            if target.exists() or target.is_symlink():
                remove_path(target)
            if backup.exists() or backup.is_symlink():
                backup.replace(target)
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
