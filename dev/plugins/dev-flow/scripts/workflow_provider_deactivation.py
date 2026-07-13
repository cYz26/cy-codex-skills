from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any

from workflow_dependency_provenance import load_dependency_provenance
from workflow_provider_registry import load_provider_registry, side_effect_decision


SUPPORTED_PROVIDER_DEACTIVATIONS = ("mattpocock-skills", "superpowers")
_PROJECT_SKILL_LAYOUTS = (
    ("official_repo_skill_path", Path(".agents") / "skills"),
    ("legacy_repo_skill_path", Path(".codex") / "skills"),
)


def deactivate_project_provider_skills(
    repo: Path,
    provider: str,
    plugin_root: Path,
    *,
    codex_home: Path | None = None,
    apply: bool = False,
    authorized_provider: str | None = None,
    authorized_plan_digest: str | None = None,
    selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    repo = Path(repo).expanduser().resolve()
    plugin_root = Path(plugin_root).expanduser().resolve()
    trusted_cache_roots = (
        [(Path(codex_home).expanduser().resolve() / "plugins" / "cache").resolve()]
        if codex_home is not None
        else []
    )
    if provider not in SUPPORTED_PROVIDER_DEACTIVATIONS:
        raise ValueError(f"unsupported provider deactivation: {provider}")

    authorization_name = "explicit_file_list_and_rollback"
    named_authorization = authorized_provider == provider
    side_effect = side_effect_decision(
        plugin_root,
        "destructive.cleanup",
        {authorization_name} if named_authorization else set(),
    )
    selected = provider_is_selected(provider, selection or {})
    known_hashes = provider_skill_hashes(plugin_root, provider)
    items: list[dict[str, Any]] = []

    for path_kind, base in _PROJECT_SKILL_LAYOUTS:
        skill_base = repo / base
        layout_safe, layout_detail = project_skill_layout_safety(repo, skill_base)
        if not layout_safe:
            items.append(
                {
                    "provider": provider,
                    "skill": "*",
                    "path": str(skill_base),
                    "pathKind": path_kind,
                    "changed": False,
                    "verified": False,
                    "verification": "not_applicable",
                    "status": "preserved_unsafe_layout",
                    "detail": layout_detail,
                }
            )
            continue
        for skill in provider_skill_names(plugin_root, provider):
            path = skill_base / skill
            item = classify_provider_skill_path(
                path,
                path_kind,
                provider,
                skill,
                known_hashes.get(skill, set()),
                trusted_cache_roots,
            )
            if item is None:
                continue
            items.append(item)

    verified_candidates = [item for item in items if item["verified"]]
    cleanup_plan = provider_cleanup_plan(provider, verified_candidates)
    plan_digest = cleanup_plan_digest(cleanup_plan)
    plan_digest_matches = bool(
        authorized_plan_digest
        and authorized_plan_digest == plan_digest
    )
    can_remove = bool(
        apply
        and named_authorization
        and side_effect["authorized"]
        and plan_digest_matches
        and not selected
    )
    apply_error: str | None = None
    rollback_failures: list[dict[str, str]] = []
    removed_items: list[dict[str, Any]] = []
    layout_fds: dict[str, int] = {}

    for item in verified_candidates:
        if selected:
            item["status"] = "preserved_selected_provider"
        elif not apply:
            item["status"] = "would_remove"
        elif not can_remove:
            item["status"] = "preserved_authorization_required"
        else:
            item["status"] = "pending_remove"

    if can_remove:
        for item in verified_candidates:
            path = Path(item["path"])
            try:
                layout_key = str(path.parent)
                layout_fd = layout_fds.get(layout_key)
                if layout_fd is None:
                    layout_fd = open_project_skill_layout_fd(repo, path.parent)
                    layout_fds[layout_key] = layout_fd
                leaf_stat = os.stat(path.name, dir_fd=layout_fd, follow_symlinks=False)
                if (
                    not stat.S_ISLNK(leaf_stat.st_mode)
                    or os.readlink(path.name, dir_fd=layout_fd) != item["rawTarget"]
                ):
                    raise OSError("cleanup candidate changed after plan creation")
                os.unlink(path.name, dir_fd=layout_fd)
                item["status"] = "removed"
                item["changed"] = True
                removed_items.append(item)
                if not project_skill_layout_fd_matches_path(repo, path.parent, layout_fd):
                    raise OSError("cleanup parent layout changed during anchored removal")
            except OSError as exc:
                apply_error = f"{type(exc).__name__}: {exc}"
                if item not in removed_items:
                    item["status"] = "preserved_apply_failed"
                break

    if apply_error is not None:
        for item in reversed(removed_items):
            path = Path(item["path"])
            try:
                layout_fd = layout_fds[str(path.parent)]
                layout_still_attached = project_skill_layout_fd_matches_path(
                    repo,
                    path.parent,
                    layout_fd,
                )
                os.symlink(item["rawTarget"], path.name, dir_fd=layout_fd)
            except OSError as exc:
                rollback_failures.append(
                    {
                        "path": item["path"],
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                item["status"] = "rollback_failed"
            else:
                item["changed"] = False
                if layout_still_attached:
                    item["status"] = "rolled_back"
                else:
                    item["status"] = "rollback_manual_review"
                    rollback_failures.append(
                        {
                            "path": item["path"],
                            "error": (
                                "parent layout changed; link restored through the anchored "
                                "directory descriptor but the project path needs manual review"
                            ),
                        }
                    )
        for item in verified_candidates:
            if item["status"] == "pending_remove":
                item["status"] = "preserved_transaction_aborted"

    for layout_fd in layout_fds.values():
        try:
            os.close(layout_fd)
        except OSError:
            pass

    changed = any(item["changed"] for item in items)
    preserved_paths = [item for item in items if not item["verified"]]
    if selected:
        ok = False
        status = "selected_provider_active"
    elif apply_error is not None:
        ok = False
        status = (
            "apply_failed_rollback_failed"
            if rollback_failures
            else "apply_failed_rolled_back"
        )
    elif apply and not can_remove:
        ok = False
        status = "authorization_required"
    elif changed:
        ok = True
        status = "applied_with_preserved_paths" if preserved_paths else "applied"
    elif verified_candidates and not apply:
        ok = True
        status = "planned_with_preserved_paths" if preserved_paths else "planned"
    else:
        ok = True
        status = "current_with_preserved_paths" if preserved_paths else "current"
    return {
        "ok": ok,
        "status": status,
        "mode": "apply" if apply else "dry-run",
        "provider": provider,
        "changed": changed,
        "authorization": authorization_name,
        "namedAuthorization": authorized_provider,
        "namedAuthorizationMatches": named_authorization,
        "authorizedPlanDigest": authorized_plan_digest,
        "planDigest": plan_digest,
        "planDigestMatches": plan_digest_matches,
        "authorizationChecks": {
            "provider": named_authorization,
            "sideEffect": bool(side_effect["authorized"]),
            "planDigest": plan_digest_matches,
        },
        "plan": cleanup_plan,
        "sideEffect": side_effect,
        "items": items,
        "removed": [item["path"] for item in items if item["status"] == "removed"],
        "preserved": [
            item["path"]
            for item in items
            if item["status"].startswith(("preserved_", "rollback_"))
            or item["status"] == "rolled_back"
        ],
        "applyError": apply_error,
        "rollbackFailures": rollback_failures,
    }


def provider_cleanup_plan(
    provider: str,
    verified_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "provider": provider,
        "items": sorted(
            (
                {
                    "path": item["path"],
                    "rawTarget": item["rawTarget"],
                    "verification": item["verification"],
                    "skillSha256": item.get("skillSha256"),
                    "rollback": item["rollback"],
                }
                for item in verified_candidates
            ),
            key=lambda item: item["path"],
        ),
    }


def cleanup_plan_digest(plan: dict[str, Any]) -> str:
    canonical = json.dumps(
        plan,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def provider_is_selected(provider: str, selection: dict[str, Any]) -> bool:
    methodology = selection.get("effectiveMethodologyProfile")
    return (provider == "superpowers" and methodology == "strict-superpowers") or (
        provider == "mattpocock-skills" and methodology == "lean-matt"
    )


def provider_skill_names(plugin_root: Path, provider: str) -> list[str]:
    registry = load_provider_registry(plugin_root)
    if provider == "superpowers":
        profile = registry["methodologyProfiles"]["strict-superpowers"]
        skills = [*profile["requiredSkills"], *profile["conditionalSkills"]]
    else:
        profile = registry["methodologyProfiles"]["lean-matt"]
        skills = [*profile["implicitSkills"], *profile["excludedImplicitSkills"]]
    return sorted(set(skills))


def provider_skill_hashes(plugin_root: Path, provider: str) -> dict[str, set[str]]:
    records = load_dependency_provenance(plugin_root).get("providerSources", {})
    hashes: dict[str, set[str]] = {}
    for record in records.values():
        if record.get("provider") != provider:
            continue
        for skill, digest in record.get("skillHashes", {}).items():
            if isinstance(digest, str) and len(digest) == 64:
                hashes.setdefault(skill, set()).add(digest)
    return hashes


def classify_provider_skill_path(
    path: Path,
    path_kind: str,
    provider: str,
    skill: str,
    known_hashes: set[str],
    trusted_cache_roots: list[Path],
) -> dict[str, Any] | None:
    if not path.is_symlink() and not path.exists():
        return None
    base: dict[str, Any] = {
        "provider": provider,
        "skill": skill,
        "path": str(path),
        "pathKind": path_kind,
        "changed": False,
        "verified": False,
        "verification": "not_applicable",
    }
    if not path.is_symlink():
        return {
            **base,
            "status": "preserved_copy",
            "detail": "not a symlink; user content was preserved",
        }

    raw_target = os.readlink(path)
    unresolved = Path(raw_target).expanduser()
    if not unresolved.is_absolute():
        unresolved = path.parent / unresolved
    resolved_target = unresolved.resolve(strict=False)
    skill_file = resolved_target / "SKILL.md"
    digest = hashlib.sha256(skill_file.read_bytes()).hexdigest() if skill_file.is_file() else None
    if digest and digest in known_hashes:
        verification = "provenance_hash"
    elif exact_legacy_provider_target(
        provider,
        skill,
        resolved_target,
        trusted_cache_roots,
    ):
        verification = "exact_legacy_provider_target"
    else:
        return {
            **base,
            "status": "preserved_unknown_link",
            "rawTarget": raw_target,
            "resolvedTarget": str(resolved_target),
            "detail": "symlink identity did not match provider provenance or an exact legacy target",
        }
    return {
        **base,
        "verified": True,
        "verification": verification,
        "status": "verified",
        "rawTarget": raw_target,
        "resolvedTarget": str(resolved_target),
        "skillSha256": digest,
        "rollback": {
            "command": ["ln", "-s", raw_target, str(path)],
            "rawTarget": raw_target,
        },
    }


def exact_legacy_provider_target(
    provider: str,
    skill: str,
    target: Path,
    trusted_cache_roots: list[Path],
) -> bool:
    parts = [part.lower() for part in target.parts]
    if (
        target.name != skill
        or target.parent.name != "skills"
        or not any(path_is_within(target, root) for root in trusted_cache_roots)
    ):
        return False
    if provider == "superpowers":
        return "superpowers" in parts or any(part.startswith("superpowers-") for part in parts)
    return any("mattpocock" in part for part in parts)


def path_is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def project_skill_layout_safety(repo: Path, skill_base: Path) -> tuple[bool, str]:
    """Reject cleanup when a project skill-layout parent can escape the repo."""
    repo = Path(repo).resolve()
    skill_base = Path(skill_base)
    try:
        relative = skill_base.relative_to(repo)
    except ValueError:
        return False, "skill layout is outside the repository"
    allowed = {base for _, base in _PROJECT_SKILL_LAYOUTS}
    if relative not in allowed:
        return False, "skill layout is not a supported project-local layout"
    current = repo
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return False, f"skill layout parent is a symlink: {current}"
    if not path_is_within(current.resolve(strict=False), repo):
        return False, "skill layout resolves outside the repository"
    return True, "project-local layout verified"


def open_project_skill_layout_fd(repo: Path, skill_base: Path) -> int:
    """Open a supported skill layout without following any parent symlink."""
    safe, detail = project_skill_layout_safety(repo, skill_base)
    if not safe:
        raise OSError(detail)
    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise OSError("platform lacks directory no-follow support")
    repo = Path(repo).resolve()
    relative = Path(skill_base).relative_to(repo)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    flags |= getattr(os, "O_CLOEXEC", 0)
    current_fd = os.open(repo, flags)
    try:
        for part in relative.parts:
            next_fd = os.open(part, flags, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        if not stat.S_ISDIR(os.fstat(current_fd).st_mode):
            raise OSError("project skill layout is not a directory")
        return current_fd
    except Exception:
        os.close(current_fd)
        raise


def project_skill_layout_fd_matches_path(repo: Path, skill_base: Path, layout_fd: int) -> bool:
    """Confirm the anchored directory is still reachable at the reviewed path."""
    try:
        current_fd = open_project_skill_layout_fd(repo, skill_base)
    except OSError:
        return False
    try:
        anchored = os.fstat(layout_fd)
        current = os.fstat(current_fd)
        return (anchored.st_dev, anchored.st_ino) == (current.st_dev, current.st_ino)
    finally:
        os.close(current_fd)


__all__ = [
    "SUPPORTED_PROVIDER_DEACTIVATIONS",
    "cleanup_plan_digest",
    "deactivate_project_provider_skills",
    "provider_cleanup_plan",
    "open_project_skill_layout_fd",
    "project_skill_layout_safety",
    "project_skill_layout_fd_matches_path",
]
