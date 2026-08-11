from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None

from legacy_workflow_config import HISTORY_PATHS, SUPERPOWERS_SKILLS
from workflow_dependency_catalog import OPENSPEC_WORKFLOW_SKILLS


LEGACY_WORKFLOW_AUTHORIZATION = "legacy-workflow-uninstall"
LEGACY_SKILL_LAYOUT_AUTHORIZATION = "legacy-skill-layout-cleanup"
GSD_SELECTION_GROUP = "legacy-gsd"
SUPERPOWERS_SELECTION_GROUP = "legacy-superpowers"
OPENSPEC_SELECTION_GROUP = "legacy-openspec-skill-layout"
REPORT_KIND = "devflow-legacy-workflow-uninstall-inspection"
SCHEMA_VERSION = "1.0"
CURRENT_OPENSPEC_GENERATED_VERSION = "1.7.0"

_GSD_HISTORY_PATHS = (
    ".codex/gsd-local-patches",
    ".codex/legacy-skills-backup",
)
_GSD_MARKER_PATHS = (
    (".codex/gsd-file-manifest.json", "recognized_gsd_manifest"),
    (".codex/gsd-install-state.json", "recognized_gsd_install_state"),
    (".codex/.gsd-profile", "recognized_gsd_profile"),
    (".codex/.gsd-surface.json", "recognized_gsd_surface_state"),
)


def inspect_legacy_workflow_uninstall(repo: str | Path) -> dict[str, Any]:
    """Return exact project-local legacy uninstall candidates without writing."""
    repo_path = Path(repo).expanduser().resolve()
    candidates: dict[str, dict[str, Any]] = {}
    manual: dict[str, dict[str, Any]] = {}
    preserved: dict[str, dict[str, Any]] = {}
    read_set: set[str] = set()

    def candidate(
        relative: str,
        *,
        selection_group: str,
        authorization: str,
        ownership: str,
        reason: str,
        evidence: dict[str, Any] | None = None,
    ) -> None:
        read_set.add(relative)
        path, error = _inspection_path(repo_path, relative)
        if error:
            manual_item(relative, error)
            return
        if path is None or not _lexists(path):
            return
        leaf_kind = _trusted_leaf_kind(path)
        if leaf_kind is None:
            manual_item(relative, "legacy_path_content_untrusted")
            return
        candidates[relative] = {
            "path": relative,
            "selectionGroup": selection_group,
            "authorization": authorization,
            "ownership": ownership,
            "reason": reason,
            "evidence": evidence or {},
            "leafKind": leaf_kind,
        }
        manual.pop(relative, None)

    def manual_item(relative: str, reason: str, *, kind: str = "legacy-workflow-artifact") -> None:
        read_set.add(relative)
        if relative not in candidates:
            manual[relative] = {"kind": kind, "path": relative, "reason": reason}

    def preserve(relative: str, reason: str) -> None:
        read_set.add(relative)
        path, error = _inspection_path(repo_path, relative)
        if error:
            manual_item(relative, error, kind="legacy-history")
            return
        if path is not None and _lexists(path):
            preserved[relative] = {
                "kind": "legacy-history",
                "path": relative,
                "reason": reason,
            }

    _inspect_gsd(
        repo_path,
        candidate,
        manual_item,
        read_set,
    )
    _inspect_superpowers(repo_path, candidate, manual_item, read_set)
    _inspect_legacy_openspec(repo_path, candidate, manual_item, read_set)

    for relative in (*HISTORY_PATHS, *_GSD_HISTORY_PATHS):
        preserve(relative, "historical_or_recovery_evidence_preserved")
    codex_root, codex_error = _inspection_path(repo_path, ".codex")
    if codex_error:
        manual_item(".codex", codex_error)
    elif codex_root is not None and codex_root.is_dir() and not codex_root.is_symlink():
        try:
            legacy_roots = sorted(codex_root.glob("skills.legacy-*"))
        except OSError:
            manual_item(".codex", "legacy_backup_scan_unreadable")
        else:
            for path in legacy_roots:
                preserve(path.relative_to(repo_path).as_posix(), "legacy_skill_backup_preserved")

    candidate_items = [candidates[path] for path in sorted(candidates)]
    manual_items = [manual[path] for path in sorted(manual)]
    preserved_items = [preserved[path] for path in sorted(preserved)]
    status = (
        "manual_review_required"
        if manual_items
        else ("cleanup_available" if candidate_items else "current")
    )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "kind": REPORT_KIND,
        "ok": not manual_items,
        "status": status,
        "readOnly": True,
        "valuesRedacted": True,
        "repo": str(repo_path),
        "candidates": candidate_items,
        "manualActions": manual_items,
        "preservedPaths": [item["path"] for item in preserved_items],
        "preservedItems": preserved_items,
        "readSet": sorted(read_set),
    }


def _inspect_gsd(
    repo: Path,
    candidate: Any,
    manual: Any,
    read_set: set[str],
) -> None:
    manifest_relative = ".codex/gsd-file-manifest.json"
    manifest_path, manifest_error = _inspection_path(repo, manifest_relative)
    read_set.add(manifest_relative)
    manifest_files: dict[str, str] = {}
    manifest_valid = False
    if manifest_error:
        manual(manifest_relative, manifest_error)
    elif manifest_path is not None and _lexists(manifest_path):
        payload = _read_json_object(manifest_path)
        raw_files = payload.get("files") if isinstance(payload, dict) else None
        if isinstance(raw_files, dict) and all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in raw_files.items()
        ):
            manifest_files = {str(key): str(value) for key, value in raw_files.items()}
            manifest_valid = True
        else:
            manual(manifest_relative, "gsd_manifest_invalid")

    grouped: dict[str, dict[str, str]] = {}
    for manifest_name, digest in sorted(manifest_files.items()):
        mapped = _map_gsd_manifest_path(manifest_name)
        if mapped is None:
            manual(manifest_relative, "gsd_manifest_path_unsupported")
            continue
        active_path, nested = mapped
        grouped.setdefault(active_path, {})[nested] = digest
    for active_path, expected in sorted(grouped.items()):
        path, error = _inspection_path(repo, active_path)
        if error:
            manual(active_path, error)
            continue
        if path is None or not _lexists(path):
            continue
        matches = _manifest_payload_matches(path, expected)
        reason = (
            "recognized_gsd_manifest_payload"
            if matches
            else "recognized_gsd_tree_with_manifest_drift"
        )
        candidate(
            active_path,
            selection_group=GSD_SELECTION_GROUP,
            authorization=LEGACY_WORKFLOW_AUTHORIZATION,
            ownership="explicit-legacy-gsd",
            reason=reason,
            evidence={"manifest": manifest_relative, "manifestMatch": matches},
        )

    for root, patterns in (
        (".agents/skills", ("gsd-*",)),
        (".codex/skills", ("gsd-*",)),
        (".codex/agents", ("gsd-*",)),
        (".codex/hooks", ("gsd-*",)),
    ):
        root_path, error = _inspection_path(repo, root)
        read_set.add(root)
        if error:
            manual(root, error)
            continue
        if root_path is None or not root_path.exists() or root_path.is_symlink():
            continue
        if not root_path.is_dir():
            manual(root, "legacy_root_not_directory")
            continue
        try:
            paths = sorted({path for pattern in patterns for path in root_path.glob(pattern)})
        except OSError:
            manual(root, "legacy_root_unreadable")
            continue
        for path in paths:
            relative = path.relative_to(repo).as_posix()
            if relative in grouped:
                continue
            candidate(
                relative,
                selection_group=GSD_SELECTION_GROUP,
                authorization=LEGACY_WORKFLOW_AUTHORIZATION,
                ownership="explicit-legacy-gsd",
                reason="recognized_gsd_namespace",
                evidence={"manifestPresent": manifest_valid},
            )

    for relative, reason in _GSD_MARKER_PATHS:
        if relative == manifest_relative and not manifest_valid:
            continue
        candidate(
            relative,
            selection_group=GSD_SELECTION_GROUP,
            authorization=LEGACY_WORKFLOW_AUTHORIZATION,
            ownership="explicit-legacy-gsd",
            reason=reason,
        )

    _inspect_gsd_config(repo, candidate, manual, read_set)
    _inspect_gsd_hooks_config(repo, candidate, manual, read_set)
    _inspect_gsd_package(repo, candidate, manual, read_set)


def _inspect_gsd_config(repo: Path, candidate: Any, manual: Any, read_set: set[str]) -> None:
    relative = ".codex/config.toml"
    path, error = _inspection_path(repo, relative)
    read_set.add(relative)
    if error:
        manual(relative, error)
        return
    if path is None or not _lexists(path):
        return
    if path.is_symlink() or not path.is_file():
        manual(relative, "gsd_config_not_regular_file")
        return
    try:
        text = path.read_text()
    except (OSError, UnicodeError):
        manual(relative, "gsd_config_unreadable")
        return
    if not _contains_gsd(text):
        return
    if tomllib is None:
        manual(relative, "gsd_config_parser_unavailable")
        return
    try:
        payload = tomllib.loads(text)
    except ValueError:
        manual(relative, "gsd_config_unreadable")
        return
    if not _strict_gsd_config(payload):
        manual(relative, "mixed_gsd_config_ownership")
        return
    candidate(
        relative,
        selection_group=GSD_SELECTION_GROUP,
        authorization=LEGACY_WORKFLOW_AUTHORIZATION,
        ownership="strict-gsd-config",
        reason="strict_gsd_only_config",
    )


def _inspect_gsd_hooks_config(repo: Path, candidate: Any, manual: Any, read_set: set[str]) -> None:
    relative = ".codex/hooks.json"
    path, error = _inspection_path(repo, relative)
    read_set.add(relative)
    if error:
        manual(relative, error)
        return
    if path is None or not _lexists(path):
        return
    payload = _read_json_object(path)
    if payload is None:
        manual(relative, "gsd_hooks_config_unreadable")
        return
    commands = _json_commands(payload)
    if not any(_contains_gsd(command) for command in commands):
        return
    if set(payload) != {"hooks"} or not commands or not all(_contains_gsd(command) for command in commands):
        manual(relative, "mixed_gsd_hook_ownership")
        return
    candidate(
        relative,
        selection_group=GSD_SELECTION_GROUP,
        authorization=LEGACY_WORKFLOW_AUTHORIZATION,
        ownership="strict-gsd-hooks-config",
        reason="strict_gsd_only_hooks_config",
    )


def _inspect_gsd_package(repo: Path, candidate: Any, manual: Any, read_set: set[str]) -> None:
    relative = ".codex/package.json"
    path, error = _inspection_path(repo, relative)
    read_set.add(relative)
    if error:
        manual(relative, error)
        return
    if path is None or not _lexists(path):
        return
    payload = _read_json_object(path)
    if payload is None:
        manual(relative, "gsd_package_marker_unreadable")
        return
    if payload.get("name") != "@opengsd/gsd-core":
        if _contains_gsd(payload):
            manual(relative, "mixed_gsd_package_ownership")
        return
    candidate(
        relative,
        selection_group=GSD_SELECTION_GROUP,
        authorization=LEGACY_WORKFLOW_AUTHORIZATION,
        ownership="strict-gsd-package-marker",
        reason="recognized_gsd_package_marker",
    )


def _inspect_superpowers(repo: Path, candidate: Any, manual: Any, read_set: set[str]) -> None:
    for root in (".agents/skills", ".codex/skills"):
        for skill in SUPERPOWERS_SKILLS:
            relative = f"{root}/{skill}"
            path, error = _inspection_path(repo, relative)
            read_set.add(relative)
            if error:
                manual(relative, error)
                continue
            if path is None or not _lexists(path):
                continue
            attested = False
            if path.is_symlink():
                try:
                    attested = "superpowers" in os.readlink(path).lower()
                except OSError:
                    attested = False
            elif path.is_dir():
                skill_file = path / "SKILL.md"
                try:
                    text = skill_file.read_text() if skill_file.is_file() and not skill_file.is_symlink() else ""
                except (OSError, UnicodeError):
                    text = ""
                attestation_text = "\n".join(
                    line
                    for line in text.splitlines()
                    if not re.match(r"^\s*name\s*:", line, flags=re.IGNORECASE)
                )
                attested = "superpowers" in attestation_text.lower()
            if not attested:
                manual(relative, "superpowers_ownership_unattested")
                continue
            candidate(
                relative,
                selection_group=SUPERPOWERS_SELECTION_GROUP,
                authorization=LEGACY_WORKFLOW_AUTHORIZATION,
                ownership="attested-superpowers-skill",
                reason="recognized_superpowers_project_skill",
                evidence={"skill": skill},
            )


def _inspect_legacy_openspec(repo: Path, candidate: Any, manual: Any, read_set: set[str]) -> None:
    official_verified = _official_openspec_set_verified(repo)
    legacy_root, root_error = _inspection_path(repo, ".codex/skills")
    read_set.add(".codex/skills")
    if root_error:
        manual(".codex/skills", root_error)
        return
    if legacy_root is None or not legacy_root.exists() or legacy_root.is_symlink():
        return
    if not legacy_root.is_dir():
        manual(".codex/skills", "legacy_root_not_directory")
        return
    try:
        entries = sorted(path for path in legacy_root.iterdir() if _lexists(path))
    except OSError:
        manual(".codex/skills", "legacy_root_unreadable")
        return
    known_superpowers = set(SUPERPOWERS_SKILLS)
    for path in entries:
        skill = path.name
        relative = path.relative_to(repo).as_posix()
        if skill.startswith("gsd-") or skill in known_superpowers:
            continue
        if skill not in OPENSPEC_WORKFLOW_SKILLS:
            manual(relative, "custom_legacy_skill_preserved")
            continue
        if not official_verified:
            manual(relative, "official_openspec_skill_set_unverified")
            continue
        identity = _generated_skill_identity(path)
        if identity is None or identity[0] != skill or identity[1] == CURRENT_OPENSPEC_GENERATED_VERSION:
            manual(relative, "legacy_openspec_identity_unattested")
            continue
        candidate(
            relative,
            selection_group=OPENSPEC_SELECTION_GROUP,
            authorization=LEGACY_SKILL_LAYOUT_AUTHORIZATION,
            ownership="obsolete-generated-openspec-skill",
            reason="verified_obsolete_openspec_skill_copy",
            evidence={
                "legacyGeneratedBy": identity[1],
                "officialGeneratedBy": CURRENT_OPENSPEC_GENERATED_VERSION,
            },
        )


def _official_openspec_set_verified(repo: Path) -> bool:
    root, error = _inspection_path(repo, ".agents/skills")
    if error or root is None or root.is_symlink() or not root.is_dir():
        return False
    try:
        actual = {path.name for path in root.iterdir() if path.name.startswith("openspec-")}
    except OSError:
        return False
    if actual != set(OPENSPEC_WORKFLOW_SKILLS):
        return False
    for skill in OPENSPEC_WORKFLOW_SKILLS:
        path = root / skill
        identity = _generated_skill_identity(path)
        if identity != (skill, CURRENT_OPENSPEC_GENERATED_VERSION):
            return False
        try:
            files = [item.relative_to(path).as_posix() for item in path.rglob("*") if item.is_file()]
            text = (path / "SKILL.md").read_text()
        except (OSError, UnicodeError):
            return False
        if files != ["SKILL.md"] or "allowed-tools: Bash(openspec:*)" not in text:
            return False
    return True


def _generated_skill_identity(path: Path) -> tuple[str, str] | None:
    if path.is_symlink() or not path.is_dir():
        return None
    skill_file = path / "SKILL.md"
    if skill_file.is_symlink() or not skill_file.is_file():
        return None
    try:
        text = skill_file.read_text()
    except (OSError, UnicodeError):
        return None
    return _frontmatter_value(text, "name") or "", _frontmatter_value(text, "generatedBy") or ""


def _frontmatter_value(text: str, key: str) -> str | None:
    frontmatter = text.split("---", 2)[1] if text.startswith("---") and text.count("---") >= 2 else ""
    match = re.search(
        rf"^\s*{re.escape(key)}:\s*[\"']?([^\"'\n]+)[\"']?\s*$",
        frontmatter,
        re.MULTILINE,
    )
    return match.group(1).strip() if match else None


def _map_gsd_manifest_path(relative: str) -> tuple[str, str] | None:
    requested = Path(relative)
    if requested.is_absolute() or not requested.parts or ".." in requested.parts:
        return None
    parts = requested.parts
    if parts[0] == "skills" and len(parts) >= 3 and parts[1].startswith("gsd-"):
        return f".agents/skills/{parts[1]}", Path(*parts[2:]).as_posix()
    if parts[0] == "gsd-core" and len(parts) >= 2:
        return ".codex/gsd-core", Path(*parts[1:]).as_posix()
    if parts[0] in {"agents", "scripts"} and len(parts) >= 2:
        return f".codex/{relative}", "."
    return None


def _manifest_payload_matches(path: Path, expected: dict[str, str]) -> bool:
    if expected.keys() == {"."}:
        if path.is_symlink() or not path.is_file():
            return False
        try:
            return hashlib.sha256(path.read_bytes()).hexdigest() == expected["."]
        except OSError:
            return False
    if path.is_symlink() or not path.is_dir():
        return False
    try:
        actual = {
            item.relative_to(path).as_posix(): hashlib.sha256(item.read_bytes()).hexdigest()
            for item in path.rglob("*")
            if item.is_file() and not item.is_symlink()
        }
    except OSError:
        return False
    return actual == expected


def _strict_gsd_config(payload: dict[str, Any]) -> bool:
    if not payload or set(payload) - {"features", "agents"}:
        return False
    features = payload.get("features", {})
    if not isinstance(features, dict) or set(features) - {"hooks"}:
        return False
    if "hooks" in features and features.get("hooks") is not True:
        return False
    agents = payload.get("agents", {})
    if not isinstance(agents, dict) or not agents:
        return False
    for name, value in agents.items():
        if not str(name).startswith("gsd-") or not isinstance(value, dict):
            return False
        config_file = value.get("config_file")
        if not isinstance(config_file, str) or "gsd-" not in config_file.lower():
            return False
    return True


def _json_commands(value: Any) -> list[str]:
    commands: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "command" and isinstance(item, str):
                commands.append(item)
            else:
                commands.extend(_json_commands(item))
    elif isinstance(value, list):
        for item in value:
            commands.extend(_json_commands(item))
    return commands


def _contains_gsd(value: Any) -> bool:
    if isinstance(value, str):
        lowered = value.lower()
        return "gsd" in lowered or "get-shit-done" in lowered or "opengsd" in lowered
    if isinstance(value, dict):
        return any(_contains_gsd(key) or _contains_gsd(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_gsd(item) for item in value)
    return False


def _read_json_object(path: Path) -> dict[str, Any] | None:
    if path.is_symlink() or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _trusted_leaf_kind(path: Path) -> str | None:
    if path.is_symlink():
        return "symlink"
    if path.is_file():
        return "file"
    if not path.is_dir():
        return None
    try:
        descendants = list(path.rglob("*"))
    except OSError:
        return None
    if any(item.is_symlink() or (not item.is_file() and not item.is_dir()) for item in descendants):
        return None
    return "tree"


def _inspection_path(repo: Path, relative: str) -> tuple[Path | None, str | None]:
    requested = Path(relative)
    if requested.is_absolute() or not requested.parts or ".." in requested.parts:
        return None, "legacy_path_invalid"
    cursor = repo
    for segment in requested.parts[:-1]:
        cursor = cursor / segment
        if cursor.is_symlink():
            return None, "legacy_path_untrusted_ancestry"
        if cursor.exists() and not cursor.is_dir():
            return None, "legacy_path_untrusted_ancestry"
    return repo.joinpath(*requested.parts), None


def _lexists(path: Path) -> bool:
    return path.exists() or path.is_symlink()
