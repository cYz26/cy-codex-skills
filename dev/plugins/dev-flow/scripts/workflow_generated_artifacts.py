from __future__ import annotations

import hashlib
import json
import os
import secrets
from fnmatch import fnmatchcase
from functools import lru_cache
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import time
from typing import Any, Optional
import unicodedata


CONTRACT_SCHEMA = "generated-artifact-contract/v1"
MANIFEST_SCHEMA = "generated-artifact-manifest/v1"
RECEIPT_SCHEMA = "generated-artifact-cleanup-receipt/v1"
PLAN_SCHEMA = "generated-artifact-cleanup-plan/v1"

AUTO_CLEAN = "AUTO_CLEAN"
WAIT_OWNER = "WAIT_OWNER"
RETAIN = "RETAIN"
HUMAN_GATE = "HUMAN_GATE"
DECISIONS = (AUTO_CLEAN, WAIT_OWNER, RETAIN, HUMAN_GATE)
LIFECYCLE_EVIDENCE_ROOT = ".planning/devflow/generated-artifacts"

RETENTION_POLICIES = ("cleanup", "retain", "promote")
PID_MAX = 2_147_483_647
OS_SCALAR_MAX = 18_446_744_073_709_551_615
TIMESTAMP_NS_MIN = -9_223_372_036_854_775_808
TIMESTAMP_NS_MAX = 9_223_372_036_854_775_807
IDENTIFIER_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
)
PROTECTED_PATHS = {
    ".dev-flow.json",
    ".git",
    ".planning",
    "AGENTS.md",
    "ENGINEERING_POLICY.md",
    "EVIDENCE_TEMPLATE.md",
    "REVIEW_CHECKLIST.md",
    "TASK_LEDGER.md",
    "openspec",
}
CONTRACT_FIELDS = {
    "schema",
    "contractId",
    "sealedAtNs",
    "repository",
    "taskId",
    "runId",
    "owner",
    "command",
    "retention",
    "scopes",
}
REPOSITORY_FIELDS = {"root", "device", "inode", "gitRoot"}
OWNER_FIELDS = {"id", "pid", "uid", "processStartToken", "lease"}
COMMAND_FIELDS = {"argv", "sha256"}
ISOLATED_SCOPE_FIELDS = {"scopeId", "kind", "path", "shared", "beforeState"}
ADJACENT_SCOPE_FIELDS = {
    "scopeId",
    "kind",
    "parent",
    "pattern",
    "shared",
    "beforeState",
}
IDENTITY_FIELDS = {
    "path",
    "type",
    "device",
    "inode",
    "mode",
    "nlink",
    "uid",
    "gid",
    "mtimeNs",
    "ctimeNs",
    "size",
    "sha256",
    "members",
}
MANIFEST_FIELDS = {
    "schema",
    "contractSha256",
    "contractSeal",
    "observedAtNs",
    "repository",
    "taskId",
    "runId",
    "owner",
    "commandResult",
    "entries",
    "scopeInventories",
}
PLAN_FIELDS = {
    "schema",
    "contractSha256",
    "manifestSha256",
    "decision",
    "reasons",
    "entries",
    "retained",
}
MANIFEST_OWNER_FIELDS = {
    "id",
    "pid",
    "uid",
    "processAlive",
    "leaseActive",
    "completed",
}
COMMAND_RESULT_FIELDS = {"exitCode", "completed"}
MANIFEST_ENTRY_FIELDS = IDENTITY_FIELDS | {"scopeId"}
SCOPE_INVENTORY_FIELDS = {"scopeId", "entries"}
RECEIPT_FIELDS = {
    "schema",
    "contractSha256",
    "manifestSha256",
    "planSha256",
    "decision",
    "status",
    "removed",
    "remaining",
    "absent",
    "retained",
    "zeroUnlistedMutation",
    "effects",
    "failure",
}
EFFECT_FIELDS = {"process", "configuration", "git", "network"}
FAILURE_FIELDS = {"path", "code", "detail"}


class GeneratedArtifactError(ValueError):
    def __init__(self, code: str, detail: Optional[str] = None):
        self.code = code
        self.detail = detail
        message = code if not detail else f"{code}:{detail}"
        super().__init__(message)


def apply_cleanup(
    repo: Path,
    contract: dict[str, Any],
    manifest: dict[str, Any],
    plan: dict[str, Any],
    *,
    prior_receipt: Optional[dict[str, Any]] = None,
    remover: Optional[Any] = None,
) -> dict[str, Any]:
    repo = Path(repo).expanduser().resolve()
    entries = normalized_path_values(
        plan.get("entries") if isinstance(plan, dict) else None
    )
    if prior_receipt is not None and successful_replay(
        repo,
        contract,
        manifest,
        plan,
        prior_receipt,
    ):
        return prior_receipt

    current_plan = plan_cleanup(repo, contract, manifest)
    if plan != current_plan or current_plan["decision"] != AUTO_CLEAN:
        detail = (
            "stale_plan"
            if plan != current_plan
            else f"decision_{current_plan['decision'].lower()}"
        )
        return cleanup_receipt(
            contract,
            manifest,
            plan,
            decision=current_plan["decision"],
            status="blocked",
            removed=[],
            remaining=present_paths(repo, entries),
            failure={
                "path": entries[0] if entries else contract["scopes"][0].get(
                    "path",
                    contract["scopes"][0].get("parent", "contract"),
                ),
                "code": "preflight_failed",
                "detail": detail,
            },
        )

    entry_map = {
        entry["path"]: entry
        for entry in manifest["entries"]
        if entry["path"] in entries
    }
    if set(entry_map) != set(entries):
        return cleanup_receipt(
            contract,
            manifest,
            plan,
            decision=HUMAN_GATE,
            status="blocked",
            removed=[],
            remaining=present_paths(repo, entries),
            failure={
                "path": entries[0] if entries else "contract",
                "code": "preflight_failed",
                "detail": "plan_entry_not_bound_to_manifest",
            },
        )

    removal = remover or remove_exact_entry
    ordered = ordered_removal_entries(entry_map.values())
    removed: list[str] = []
    for entry in ordered:
        try:
            removal(repo, entry)
        except Exception as error:
            return cleanup_receipt(
                contract,
                manifest,
                plan,
                decision=AUTO_CLEAN,
                status="failed",
                removed=removed,
                remaining=present_paths(repo, entries),
                failure={
                    "path": entry["path"],
                    "code": "os_remove_failed",
                    "detail": str(error),
                },
            )
        removed.append(entry["path"])

    remaining = present_paths(repo, entries)
    if remaining:
        return cleanup_receipt(
            contract,
            manifest,
            plan,
            decision=AUTO_CLEAN,
            status="failed",
            removed=removed,
            remaining=remaining,
            failure={
                "path": remaining[0],
                "code": "postcondition_failed",
                "detail": "one or more exact targets remain",
            },
        )
    receipt = cleanup_receipt(
        contract,
        manifest,
        plan,
        decision=AUTO_CLEAN,
        status="complete",
        removed=removed,
        remaining=[],
        failure=None,
    )
    receipt_errors = validate_receipt(
        receipt,
        contract=contract,
        manifest=manifest,
        plan=plan,
    )
    if receipt_errors:
        raise GeneratedArtifactError(
            "receipt_invalid",
            ",".join(receipt_errors),
        )
    return receipt


def remove_exact_entry(repo: Path, entry: dict[str, Any]) -> None:
    relative = normalize_relative_path(entry["path"])
    parts = PurePosixPath(relative).parts
    if not parts:
        raise GeneratedArtifactError("empty_removal_path")
    parent_fd = open_parent_dirfd(repo, parts[:-1])
    quarantine_name: Optional[str] = None
    moved = False
    try:
        name = parts[-1]
        require_dirfd_exact_name(parent_fd, name, relative)
        quarantine_name = unused_quarantine_name(parent_fd)
        os.rename(
            name,
            quarantine_name,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
        )
        moved = True
        current = os.stat(
            quarantine_name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
        if entry["type"] == "directory":
            verify_directory_for_removal(
                parent_fd,
                quarantine_name,
                current,
                entry,
            )
            verify_quarantined_leaf(parent_fd, quarantine_name, current, entry)
            os.rmdir(quarantine_name, dir_fd=parent_fd)
            moved = False
            return
        verify_non_directory_for_removal(
            parent_fd,
            quarantine_name,
            current,
            entry,
            renamed=True,
        )
        verify_quarantined_leaf(parent_fd, quarantine_name, current, entry)
        os.unlink(quarantine_name, dir_fd=parent_fd)
        moved = False
    except Exception:
        if moved and quarantine_name is not None:
            restore_quarantined_leaf(
                parent_fd,
                quarantine_name,
                parts[-1],
                relative,
            )
        raise
    finally:
        os.close(parent_fd)


def unused_quarantine_name(parent_fd: int) -> str:
    for _attempt in range(32):
        candidate = f".devflow-q-{secrets.token_hex(16)}"
        try:
            os.stat(candidate, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return candidate
    raise GeneratedArtifactError("quarantine_name_unavailable")


def verify_quarantined_leaf(
    parent_fd: int,
    name: str,
    current: os.stat_result,
    expected: dict[str, Any],
) -> None:
    latest = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if latest.st_dev != current.st_dev or latest.st_ino != current.st_ino:
        raise GeneratedArtifactError(
            "removal_identity_drift",
            expected["path"],
        )


def restore_quarantined_leaf(
    parent_fd: int,
    quarantine_name: str,
    original_name: str,
    relative: str,
) -> None:
    try:
        os.stat(original_name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        pass
    else:
        raise GeneratedArtifactError(
            "quarantine_restore_blocked",
            relative,
        )
    os.rename(
        quarantine_name,
        original_name,
        src_dir_fd=parent_fd,
        dst_dir_fd=parent_fd,
    )


def open_parent_dirfd(repo: Path, parts: tuple[str, ...]) -> int:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    current_fd = os.open(repo, flags)
    try:
        for part in parts:
            require_dirfd_exact_name(current_fd, part, "/".join(parts))
            next_fd = os.open(
                part,
                flags | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=current_fd,
            )
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except Exception:
        os.close(current_fd)
        raise


def require_dirfd_exact_name(directory_fd: int, name: str, relative: str) -> None:
    try:
        names = os.listdir(directory_fd)
    except OSError as error:
        raise GeneratedArtifactError(
            "filesystem_path_unavailable",
            relative,
        ) from error
    if name not in names:
        raise GeneratedArtifactError("filesystem_path_alias", relative)


def verify_directory_for_removal(
    parent_fd: int,
    name: str,
    current: os.stat_result,
    expected: dict[str, Any],
) -> None:
    if not stat.S_ISDIR(current.st_mode):
        raise GeneratedArtifactError("removal_type_drift", expected["path"])
    verify_stable_node(current, expected)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    directory_fd = os.open(
        name,
        flags | getattr(os, "O_NOFOLLOW", 0),
        dir_fd=parent_fd,
    )
    try:
        if os.listdir(directory_fd):
            raise GeneratedArtifactError("removal_directory_not_empty", expected["path"])
    finally:
        os.close(directory_fd)


def verify_non_directory_for_removal(
    parent_fd: int,
    name: str,
    current: os.stat_result,
    expected: dict[str, Any],
    *,
    renamed: bool = False,
) -> None:
    if stat.S_ISDIR(current.st_mode) or stat.S_ISLNK(current.st_mode):
        raise GeneratedArtifactError("removal_type_drift", expected["path"])
    current_type = file_type(current.st_mode)
    if current_type != expected["type"]:
        raise GeneratedArtifactError("removal_type_drift", expected["path"])
    verify_stable_node(
        current,
        expected,
        include_times=True,
        include_ctime=not renamed,
    )
    if current_type != "file":
        return
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    file_fd = os.open(name, flags, dir_fd=parent_fd)
    try:
        opened = os.fstat(file_fd)
        if opened.st_dev != current.st_dev or opened.st_ino != current.st_ino:
            raise GeneratedArtifactError("removal_identity_drift", expected["path"])
        if descriptor_sha256(file_fd) != expected["sha256"]:
            raise GeneratedArtifactError("removal_hash_drift", expected["path"])
    finally:
        os.close(file_fd)


def verify_stable_node(
    current: os.stat_result,
    expected: dict[str, Any],
    *,
    include_times: bool = False,
    include_ctime: bool = True,
) -> None:
    actual = {
        "device": current.st_dev,
        "inode": current.st_ino,
        "mode": stat.S_IMODE(current.st_mode),
        "uid": current.st_uid,
        "gid": current.st_gid,
    }
    fields = tuple(actual)
    if include_times:
        actual.update(
            {
                "nlink": current.st_nlink,
                "mtimeNs": current.st_mtime_ns,
                "size": current.st_size,
            }
        )
        if include_ctime:
            actual["ctimeNs"] = current.st_ctime_ns
        fields = tuple(actual)
    if any(actual[field] != expected[field] for field in fields):
        raise GeneratedArtifactError("removal_identity_drift", expected["path"])


def descriptor_sha256(file_fd: int) -> str:
    digest = hashlib.sha256()
    os.lseek(file_fd, 0, os.SEEK_SET)
    while True:
        chunk = os.read(file_fd, 1024 * 1024)
        if not chunk:
            break
        digest.update(chunk)
    return digest.hexdigest()


def ordered_removal_entries(
    entries: Any,
) -> list[dict[str, Any]]:
    values = list(entries)
    non_directories = sorted(
        (entry for entry in values if entry["type"] != "directory"),
        key=lambda entry: entry["path"],
    )
    directories = sorted(
        (entry for entry in values if entry["type"] == "directory"),
        key=lambda entry: (
            -len(PurePosixPath(entry["path"]).parts),
            entry["path"],
        ),
    )
    return non_directories + directories


def cleanup_receipt(
    contract: dict[str, Any],
    manifest: dict[str, Any],
    plan: dict[str, Any],
    *,
    decision: str,
    status: str,
    removed: list[str],
    remaining: list[str],
    failure: Optional[dict[str, str]],
) -> dict[str, Any]:
    entries = normalized_path_values(
        plan.get("entries") if isinstance(plan, dict) else None
    )
    removed_paths = normalized_path_values(removed)
    remaining_paths = normalized_path_values(remaining)
    retained_paths = normalized_path_values(
        plan.get("retained") if isinstance(plan, dict) else None
    )
    return {
        "schema": RECEIPT_SCHEMA,
        "contractSha256": document_sha256(contract),
        "manifestSha256": document_sha256(manifest),
        "planSha256": document_sha256(plan),
        "decision": decision,
        "status": status,
        "removed": removed_paths,
        "remaining": remaining_paths,
        "absent": sorted(set(entries) - set(remaining_paths)),
        "retained": retained_paths,
        "zeroUnlistedMutation": set(removed_paths).issubset(entries),
        "effects": {
            "process": False,
            "configuration": False,
            "git": False,
            "network": False,
        },
        "failure": failure,
    }


def successful_replay(
    repo: Path,
    contract: dict[str, Any],
    manifest: dict[str, Any],
    plan: dict[str, Any],
    receipt: dict[str, Any],
) -> bool:
    return not validate_terminal_cleanup(
        repo,
        contract,
        manifest,
        plan,
        receipt,
    )


def present_paths(repo: Path, paths: list[str]) -> list[str]:
    return sorted(path for path in paths if exact_path_present(repo, path))


def exact_path_present(repo: Path, relative: str) -> bool:
    try:
        parts = PurePosixPath(normalize_relative_path(relative)).parts
        parent_fd = open_parent_dirfd(repo, parts[:-1])
    except (FileNotFoundError, NotADirectoryError, GeneratedArtifactError):
        return False
    try:
        os.stat(parts[-1], dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    except OSError:
        return True
    finally:
        os.close(parent_fd)
    return True


def observe_artifacts(
    repo: Path,
    contract: dict[str, Any],
    *,
    exit_code: int,
    now_ns: Optional[int] = None,
) -> dict[str, Any]:
    repo = Path(repo).expanduser().resolve()
    errors = validate_contract(repo, contract)
    if errors:
        raise GeneratedArtifactError("contract_invalid", ",".join(errors))
    if not isinstance(exit_code, int) or isinstance(exit_code, bool):
        raise GeneratedArtifactError("invalid_exit_code")
    contract_seal = capture_contract_seal(repo, contract)

    scope_inventories: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for scope in contract["scopes"]:
        inventory = observe_scope_inventory(repo, scope)
        scope_inventories.append(
            {
                "scopeId": scope["scopeId"],
                "entries": inventory,
            }
        )
        candidates.extend(scope_candidates(scope, inventory))
    candidates.sort(key=lambda entry: entry["path"])
    if len({entry["path"] for entry in candidates}) != len(candidates):
        raise GeneratedArtifactError("duplicate_candidate_path")

    process_alive = owner_process_active(contract)
    lease_active = owner_lease_active(repo, contract["owner"].get("lease"))
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "contractSha256": document_sha256(contract),
        "contractSeal": contract_seal,
        "observedAtNs": int(now_ns if now_ns is not None else time.time_ns()),
        "repository": contract["repository"],
        "taskId": contract["taskId"],
        "runId": contract["runId"],
        "owner": {
            "id": contract["owner"]["id"],
            "pid": contract["owner"]["pid"],
            "uid": contract["owner"]["uid"],
            "processAlive": process_alive,
            "leaseActive": lease_active,
            "completed": not process_alive and not lease_active,
        },
        "commandResult": {
            "exitCode": exit_code,
            "completed": True,
        },
        "entries": candidates,
        "scopeInventories": scope_inventories,
    }
    manifest_errors = validate_manifest(repo, manifest, contract=contract)
    if manifest_errors:
        raise GeneratedArtifactError(
            "manifest_invalid",
            ",".join(manifest_errors),
        )
    return manifest


def plan_cleanup(
    repo: Path,
    contract: Optional[dict[str, Any]],
    manifest: Optional[dict[str, Any]],
    *,
    candidates: Optional[list[str]] = None,
) -> dict[str, Any]:
    repo = Path(repo).expanduser().resolve()
    if contract is None:
        candidate_paths = normalized_path_values(candidates)
        return cleanup_plan(
            contract=None,
            manifest=None,
            decision=HUMAN_GATE,
            reasons=["unregistered_contract"],
            entries=candidate_paths,
        )
    contract_errors = validate_contract(repo, contract)
    if contract_errors:
        return cleanup_plan(
            contract=contract,
            manifest=manifest,
            decision=HUMAN_GATE,
            reasons=contract_errors,
            entries=manifest_paths(manifest),
        )
    if manifest is None:
        return cleanup_plan(
            contract=contract,
            manifest=None,
            decision=HUMAN_GATE,
            reasons=["missing_manifest"],
            entries=[],
        )
    manifest_errors = validate_manifest(repo, manifest, contract=contract)
    if manifest_errors:
        return cleanup_plan(
            contract=contract,
            manifest=manifest,
            decision=HUMAN_GATE,
            reasons=manifest_errors,
            entries=manifest_paths(manifest),
        )

    reasons = safety_reasons(repo, contract, manifest)
    entries = manifest_paths(manifest)
    if reasons:
        decision = HUMAN_GATE
    elif contract["retention"] in ("retain", "promote"):
        decision = RETAIN
        reasons = [f"retention_{contract['retention']}"]
    elif owner_is_active(repo, contract, manifest):
        decision = WAIT_OWNER
        reasons = ["owner_active"]
    else:
        decision = AUTO_CLEAN
        reasons = ["all_invariants_pass"]
    retained = entries if decision == RETAIN else []
    return cleanup_plan(
        contract=contract,
        manifest=manifest,
        decision=decision,
        reasons=reasons,
        entries=entries,
        retained=retained,
    )


def observe_scope_inventory(
    repo: Path,
    scope: dict[str, Any],
) -> list[dict[str, Any]]:
    if scope["kind"] == "isolated_root":
        relative = scope["path"]
        path = local_path(repo, relative, require_exists=False)
        if not path.exists():
            return []
        if path.is_symlink() or not path.is_dir():
            raise GeneratedArtifactError("isolated_root_not_directory", relative)
        return inventory_tree(repo, path, include_root=True)
    parent = local_path(repo, scope["parent"], require_exists=True)
    if parent.is_symlink() or not parent.is_dir():
        raise GeneratedArtifactError("adjacent_parent_not_directory", scope["parent"])
    return inventory_tree(repo, parent, include_root=False)


def scope_candidates(
    scope: dict[str, Any],
    inventory: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    scope_id = scope["scopeId"]
    if scope["kind"] == "isolated_root":
        baseline = scope["beforeState"]["state"]
        root = scope["path"]
        selected = [
            identity
            for identity in inventory
            if baseline == "absent" or identity["path"] != root
        ]
        return [{"scopeId": scope_id, **identity} for identity in selected]

    parent = PurePosixPath(scope["parent"])
    baseline_paths = {
        entry["path"] for entry in scope["beforeState"]["entries"]
    }
    by_path = {entry["path"]: entry for entry in inventory}
    selected_paths: set[str] = set()
    for entry in inventory:
        relative = PurePosixPath(entry["path"]).relative_to(parent).as_posix()
        if entry["path"] in baseline_paths:
            continue
        if artifact_pattern_matches(relative, scope["pattern"]):
            selected_paths.add(entry["path"])
            selected_paths.update(
                new_candidate_ancestors(
                    entry["path"],
                    scope["parent"],
                    baseline_paths,
                    by_path,
                )
            )
    return [
        {"scopeId": scope_id, **by_path[path]}
        for path in sorted(selected_paths)
    ]


def new_candidate_ancestors(
    relative: str,
    parent: str,
    baseline_paths: set[str],
    inventory: dict[str, dict[str, Any]],
) -> set[str]:
    result: set[str] = set()
    boundary = PurePosixPath(parent)
    current = PurePosixPath(relative).parent
    while current != boundary and boundary in current.parents:
        value = current.as_posix()
        if value not in baseline_paths and value in inventory:
            result.add(value)
        current = current.parent
    return result


def artifact_pattern_matches(relative: str, pattern: str) -> bool:
    pure = PurePosixPath(relative)
    if pure.match(pattern) or fnmatchcase(relative, pattern):
        return True
    return pattern.startswith("**/") and pure.match(pattern[3:])


def owner_binding_reasons(
    contract: dict[str, Any],
    manifest: dict[str, Any],
) -> list[str]:
    owner = contract.get("owner")
    manifest_owner = manifest.get("owner")
    if not isinstance(owner, dict) or not isinstance(manifest_owner, dict):
        return []
    return [
        f"owner_binding_mismatch:{field}"
        for field in ("id", "pid", "uid")
        if manifest_owner.get(field) != owner.get(field)
    ]


def recorded_safety_reasons(
    contract: dict[str, Any],
    manifest: dict[str, Any],
    *,
    repo: Optional[Path] = None,
) -> list[str]:
    reasons = owner_binding_reasons(contract, manifest)
    owner = contract.get("owner")
    if isinstance(owner, dict) and owner.get("uid") != os.getuid():
        reasons.append("owner_uid_mismatch:contract")
    tracked: set[str] = set()
    if repo is not None:
        tracked, tracked_error = tracked_paths(Path(repo).expanduser().resolve())
        if tracked_error:
            reasons.append(tracked_error)
    tracked_keys = {
        path_comparison_key(repo, tracked_path)
        for tracked_path in tracked
    }

    scope_documents = contract.get("scopes")
    scopes = (
        {
            scope.get("scopeId"): scope
            for scope in scope_documents
            if isinstance(scope, dict) and isinstance(scope.get("scopeId"), str)
        }
        if isinstance(scope_documents, list)
        else {}
    )
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        return sorted(set(reasons))
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            continue
        path = entry["path"]
        scope_id = entry.get("scopeId")
        scope = scopes.get(scope_id) if isinstance(scope_id, str) else None
        if scope is None:
            reasons.append(f"unknown_scope:{path}")
        else:
            try:
                reasons.extend(entry_scope_reasons(scope, entry))
            except (KeyError, TypeError, ValueError):
                reasons.append(f"invalid_scope_binding:{path}")
        if protected_path(path, repo=repo):
            reasons.append(f"protected_path:{path}")
        if path_comparison_key(repo, path) in tracked_keys:
            reasons.append(f"tracked_path:{path}")
        entry_type = entry.get("type")
        if entry_type == "symlink":
            reasons.append(f"symlink_path:{path}")
        if isinstance(entry_type, str) and entry_type in ("device", "other"):
            reasons.append(f"unsafe_type:{path}")
        if (
            entry_type != "directory"
            and json_integer(entry.get("nlink"))
            and entry["nlink"] > 1
        ):
            reasons.append(f"hardlink_path:{path}")
        if (
            isinstance(owner, dict)
            and json_integer(entry.get("uid"))
            and entry["uid"] != owner.get("uid")
        ):
            reasons.append(f"owner_uid_mismatch:{path}")
        if (
            json_integer(entry.get("ctimeNs"))
            and json_integer(contract.get("sealedAtNs"))
            and entry["ctimeNs"] < contract["sealedAtNs"]
        ):
            reasons.append(f"predates_contract:{path}")
    return sorted(set(reasons))


def safety_reasons(
    repo: Path,
    contract: dict[str, Any],
    manifest: dict[str, Any],
) -> list[str]:
    reasons = recorded_safety_reasons(contract, manifest, repo=repo)
    reasons.extend(contract_seal_safety_reasons(repo, contract, manifest))
    owner = contract["owner"]
    reasons.extend(lease_safety_reasons(repo, owner.get("lease")))

    for entry in manifest["entries"]:
        reasons.extend(current_identity_reasons(repo, entry))
    reasons.extend(scope_inventory_reasons(repo, contract, manifest))
    return sorted(set(reasons))


def contract_seal_safety_reasons(
    repo: Path,
    contract: dict[str, Any],
    manifest: dict[str, Any],
) -> list[str]:
    recorded = manifest.get("contractSeal")
    if not valid_identity(recorded):
        return ["invalid_contract_seal"]
    reasons: list[str] = []
    try:
        current = capture_contract_seal(repo, contract)
    except GeneratedArtifactError as error:
        return [error.code]
    if current != recorded:
        reasons.append("contract_seal_identity_drift")
    if recorded.get("path") != contract_document_relative_path(contract):
        reasons.append("contract_seal_path_mismatch")
    if recorded.get("sha256") != document_sha256(contract):
        reasons.append("contract_seal_hash_mismatch")
    owner = contract.get("owner")
    if (
        not isinstance(owner, dict)
        or recorded.get("uid") != owner.get("uid")
    ):
        reasons.append("contract_seal_owner_mismatch")
    if recorded.get("nlink") != 1:
        reasons.append("contract_seal_shared")
    sealed_at = contract.get("sealedAtNs")
    seal_ctime = recorded.get("ctimeNs")
    if (
        positive_timestamp_ns(sealed_at)
        and json_integer(seal_ctime)
        and seal_ctime < sealed_at
    ):
        reasons.append("contract_seal_timestamp_mismatch")
    entries = manifest.get("entries")
    for entry in entries if isinstance(entries, list) else []:
        if (
            isinstance(entry, dict)
            and isinstance(entry.get("path"), str)
            and json_integer(entry.get("ctimeNs"))
            and json_integer(seal_ctime)
            and entry["ctimeNs"] < seal_ctime
        ):
            reasons.append(
                f"contract_sealed_after_artifact:{entry['path']}"
            )
    return sorted(set(reasons))


def entry_scope_reasons(
    scope: dict[str, Any],
    entry: dict[str, Any],
) -> list[str]:
    path = PurePosixPath(entry["path"])
    reasons: list[str] = []
    if scope["kind"] == "isolated_root":
        root = PurePosixPath(scope["path"])
        if path != root and root not in path.parents:
            reasons.append(f"scope_escape:{entry['path']}")
        if scope["beforeState"]["state"] == "empty" and path == root:
            reasons.append(f"preexisting_path:{entry['path']}")
        return reasons
    parent = PurePosixPath(scope["parent"])
    if parent not in path.parents:
        reasons.append(f"scope_escape:{entry['path']}")
        return reasons
    baseline_paths = {
        item["path"] for item in scope["beforeState"]["entries"]
    }
    if entry["path"] in baseline_paths:
        reasons.append(f"preexisting_path:{entry['path']}")
    relative = path.relative_to(parent).as_posix()
    if not artifact_pattern_matches(relative, scope["pattern"]):
        ancestor_of_candidate = any(
            path in PurePosixPath(candidate).parents
            for candidate in (
                item["path"]
                for item in scope["beforeState"]["entries"]
                if artifact_pattern_matches(
                    PurePosixPath(item["path"]).relative_to(parent).as_posix(),
                    scope["pattern"],
                )
            )
        )
        if not ancestor_of_candidate and entry["type"] != "directory":
            reasons.append(f"pattern_mismatch:{entry['path']}")
    return reasons


def current_identity_reasons(
    repo: Path,
    expected: dict[str, Any],
) -> list[str]:
    try:
        path = local_path(repo, expected["path"], require_exists=True)
        current = capture_identity(repo, path)
    except GeneratedArtifactError:
        return [f"identity_drift:{expected['path']}"]
    expected_identity = {
        field: expected[field]
        for field in IDENTITY_FIELDS
    }
    if expected_identity == current:
        return []
    if (
        expected_identity["type"] == "directory"
        and expected_identity["members"] != current["members"]
    ):
        return [f"membership_drift:{expected['path']}"]
    return [f"identity_drift:{expected['path']}"]


def scope_inventory_reasons(
    repo: Path,
    contract: dict[str, Any],
    manifest: dict[str, Any],
) -> list[str]:
    scopes = {scope["scopeId"]: scope for scope in contract["scopes"]}
    reasons: list[str] = []
    for expected in manifest["scopeInventories"]:
        scope = scopes.get(expected["scopeId"])
        if scope is None:
            reasons.append(f"unknown_scope_inventory:{expected['scopeId']}")
            continue
        try:
            current = observe_scope_inventory(repo, scope)
        except GeneratedArtifactError:
            reasons.append(f"scope_inventory_drift:{expected['scopeId']}")
            continue
        expected_by_path = {entry["path"]: entry for entry in expected["entries"]}
        current_by_path = {entry["path"]: entry for entry in current}
        for path in sorted(set(current_by_path) - set(expected_by_path)):
            reasons.append(f"unlisted_scope_entry:{path}")
        for path in sorted(set(expected_by_path) - set(current_by_path)):
            reasons.append(f"missing_scope_entry:{path}")
        for path in sorted(set(expected_by_path) & set(current_by_path)):
            before = expected_by_path[path]
            after = current_by_path[path]
            if before == after:
                continue
            if before["type"] == "directory" and before["members"] != after["members"]:
                reasons.append(f"membership_drift:{path}")
            else:
                reasons.append(f"identity_drift:{path}")
    return reasons


def cleanup_plan(
    *,
    contract: Optional[dict[str, Any]],
    manifest: Optional[dict[str, Any]],
    decision: str,
    reasons: list[str],
    entries: list[str],
    retained: Optional[list[str]] = None,
) -> dict[str, Any]:
    return {
        "schema": PLAN_SCHEMA,
        "contractSha256": document_sha256(contract) if contract is not None else None,
        "manifestSha256": document_sha256(manifest) if manifest is not None else None,
        "decision": decision,
        "reasons": sorted(set(reasons)),
        "entries": sorted(set(entries)),
        "retained": sorted(set(retained or [])),
    }


def manifest_paths(manifest: Any) -> list[str]:
    if not isinstance(manifest, dict) or not isinstance(manifest.get("entries"), list):
        return []
    return sorted(
        {
            entry["path"]
            for entry in manifest["entries"]
            if isinstance(entry, dict) and safe_relative_path(entry.get("path"))
        }
    )


def normalized_path_values(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({item for item in value if safe_relative_path(item)})


def owner_is_active(
    repo: Path,
    contract: dict[str, Any],
    manifest: dict[str, Any],
) -> bool:
    owner = contract["owner"]
    return (
        bool(manifest["owner"]["processAlive"])
        or bool(manifest["owner"]["leaseActive"])
        or owner_process_active(contract)
        or owner_lease_active(repo, owner.get("lease"))
        or not bool(manifest["owner"]["completed"])
    )


def pid_alive(pid: int) -> bool:
    if not valid_pid(pid):
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except (OSError, OverflowError, ValueError):
        return True
    return True


def process_start_token(pid: int) -> Optional[str]:
    if not valid_pid(pid) or not pid_alive(pid):
        return None
    if sys.platform == "darwin":
        token = darwin_process_start_token(pid)
        if token is not None:
            return token
    proc_stat = Path(f"/proc/{pid}/stat")
    try:
        raw_stat = proc_stat.read_text()
        closing_parenthesis = raw_stat.rfind(")")
        fields = raw_stat[closing_parenthesis + 2 :].split()
        if closing_parenthesis >= 0 and len(fields) > 19:
            try:
                boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
            except OSError:
                boot_id = "unknown-boot"
            return f"linux:{boot_id}:{fields[19]}"
    except OSError:
        pass
    probe_environment = os.environ.copy()
    probe_environment.update(
        {
            "LANG": "C",
            "LC_ALL": "C",
            "TZ": "UTC",
        }
    )
    try:
        result = subprocess.run(
            ["ps", "-o", "lstart=", "-p", str(pid)],
            text=True,
            capture_output=True,
            check=False,
            env=probe_environment,
        )
    except OSError:
        return None
    value = " ".join(result.stdout.split())
    return f"ps:{value}" if result.returncode == 0 and value else None


def darwin_process_start_token(pid: int) -> Optional[str]:
    try:
        import ctypes

        class ProcBsdInfo(ctypes.Structure):
            _fields_ = [
                *(
                    (name, ctypes.c_uint32)
                    for name in (
                        "flags",
                        "status",
                        "xstatus",
                        "pid",
                        "ppid",
                        "uid",
                        "gid",
                        "ruid",
                        "rgid",
                        "svuid",
                        "svgid",
                        "reserved",
                    )
                ),
                ("comm", ctypes.c_char * 16),
                ("name", ctypes.c_char * 32),
                *(
                    (name, ctypes.c_uint32)
                    for name in (
                        "nfiles",
                        "pgid",
                        "pjobc",
                        "tdev",
                        "tpgid",
                    )
                ),
                ("nice", ctypes.c_int32),
                ("start_seconds", ctypes.c_uint64),
                ("start_microseconds", ctypes.c_uint64),
            ]

        library = ctypes.CDLL("/usr/lib/libproc.dylib")
        library.proc_pidinfo.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint64,
            ctypes.c_void_p,
            ctypes.c_int,
        ]
        library.proc_pidinfo.restype = ctypes.c_int
        info = ProcBsdInfo()
        size = library.proc_pidinfo(
            pid,
            3,
            0,
            ctypes.byref(info),
            ctypes.sizeof(info),
        )
        if size != ctypes.sizeof(info):
            return None
        return f"darwin:{info.start_seconds}:{info.start_microseconds}"
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def owner_process_active(contract: dict[str, Any]) -> bool:
    owner = contract.get("owner")
    if not isinstance(owner, dict):
        return True
    pid = owner.get("pid")
    if not valid_pid(pid):
        return True
    if not pid_alive(pid):
        return False
    recorded_token = owner.get("processStartToken")
    if not isinstance(recorded_token, str):
        return True
    current_token = process_start_token(pid)
    return current_token is None or current_token == recorded_token


def owner_lease_active(repo: Path, lease: Any) -> bool:
    if not isinstance(lease, dict):
        return False
    try:
        path = local_path(repo, lease["path"], require_exists=False)
    except (GeneratedArtifactError, KeyError):
        return True
    if not (path.exists() or path.is_symlink()):
        return False
    try:
        return capture_identity(repo, path) == lease.get("identity")
    except GeneratedArtifactError:
        return True


def lease_safety_reasons(repo: Path, lease: Any) -> list[str]:
    if not isinstance(lease, dict):
        return []
    try:
        path = local_path(repo, lease["path"], require_exists=False)
    except GeneratedArtifactError:
        return ["lease_scope_invalid"]
    if not (path.exists() or path.is_symlink()):
        return []
    try:
        current = capture_identity(repo, path)
    except GeneratedArtifactError:
        return ["lease_identity_drift"]
    return [] if current == lease.get("identity") else ["lease_identity_drift"]


def tracked_paths(repo: Path) -> tuple[set[str], Optional[str]]:
    result = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "-z"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return set(), "git_state_unavailable"
    paths = {
        item.decode("utf-8", errors="surrogateescape")
        for item in result.stdout.split(b"\0")
        if item
    }
    return paths, None


def prepare_contract(
    *,
    repo: Path,
    task_id: str,
    run_id: str,
    owner_id: str,
    owner_pid: int,
    command: list[str],
    isolated_roots: list[str],
    adjacent_outputs: list[dict[str, str]],
    retention: str = "cleanup",
    contract_id: Optional[str] = None,
    lease_path: Optional[str] = None,
    now_ns: Optional[int] = None,
) -> dict[str, Any]:
    repo = Path(repo).expanduser().resolve()
    require_identifier("task_id", task_id)
    require_identifier("run_id", run_id)
    require_identifier("owner_id", owner_id)
    if not valid_pid(owner_pid):
        raise GeneratedArtifactError("invalid_owner_pid")
    owner_was_alive = pid_alive(owner_pid)
    process_start = (
        process_start_token(owner_pid)
        if owner_was_alive
        else "absent-at-contract-seal"
    )
    if not isinstance(command, list) or not command:
        raise GeneratedArtifactError("command_required")
    if not all(isinstance(token, str) and token for token in command):
        raise GeneratedArtifactError("invalid_command")
    if retention not in RETENTION_POLICIES:
        raise GeneratedArtifactError("invalid_retention", retention)
    identifier = contract_id or f"{task_id}-{run_id}"
    require_identifier("contract_id", identifier)
    if not isolated_roots and not adjacent_outputs:
        raise GeneratedArtifactError("scope_required")

    scopes: list[dict[str, Any]] = []
    for index, relative in enumerate(isolated_roots, 1):
        scopes.append(prepare_isolated_scope(repo, relative, index))
    for index, specification in enumerate(adjacent_outputs, 1):
        scopes.append(prepare_adjacent_scope(repo, specification, index))
    ensure_disjoint_scopes(scopes, repo=repo)

    lease = None
    if lease_path is not None:
        relative = normalize_relative_path(lease_path)
        path = local_path(repo, relative, require_exists=True)
        lease = {"path": relative, "identity": capture_identity(repo, path)}

    root_stat = os.stat(repo, follow_symlinks=False)
    contract = {
        "schema": CONTRACT_SCHEMA,
        "contractId": identifier,
        "sealedAtNs": int(now_ns if now_ns is not None else time.time_ns()),
        "repository": {
            "root": str(repo),
            "device": root_stat.st_dev,
            "inode": root_stat.st_ino,
            "gitRoot": git_root(repo),
        },
        "taskId": task_id,
        "runId": run_id,
        "owner": {
            "id": owner_id,
            "pid": owner_pid,
            "uid": os.getuid(),
            "processStartToken": process_start,
            "lease": lease,
        },
        "command": {
            "argv": list(command),
            "sha256": command_sha256(command),
        },
        "retention": retention,
        "scopes": scopes,
    }
    errors = validate_contract(repo, contract, require_current_baseline=True)
    if errors:
        raise GeneratedArtifactError("contract_invalid", ",".join(errors))
    return contract


def contract_document_relative_path(contract: dict[str, Any]) -> str:
    contract_id = contract.get("contractId") if isinstance(contract, dict) else None
    require_identifier("contract_id", contract_id)
    return (
        f"{LIFECYCLE_EVIDENCE_ROOT}/contracts/"
        f"{contract_id}.contract.json"
    )


def contract_document_path(repo: Path, contract: dict[str, Any]) -> Path:
    return local_path(
        Path(repo).expanduser().resolve(),
        contract_document_relative_path(contract),
        require_exists=False,
    )


def capture_contract_seal(
    repo: Path,
    contract: dict[str, Any],
) -> dict[str, Any]:
    repo = Path(repo).expanduser().resolve()
    relative = contract_document_relative_path(contract)
    path = local_path(repo, relative, require_exists=True)
    identity = capture_identity(repo, path)
    if identity["type"] != "file":
        raise GeneratedArtifactError("contract_seal_not_regular", relative)
    if identity["sha256"] != document_sha256(contract):
        raise GeneratedArtifactError("contract_seal_hash_mismatch", relative)
    return identity


def prepare_isolated_scope(repo: Path, relative: str, index: int) -> dict[str, Any]:
    normalized = normalize_relative_path(relative)
    reject_protected_path(normalized, repo=repo)
    path = local_path(repo, normalized, require_exists=False)
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_dir():
            raise GeneratedArtifactError("isolated_root_not_directory", normalized)
        members = sorted(item.name for item in os.scandir(path))
        if members:
            raise GeneratedArtifactError("isolated_root_not_empty", normalized)
        before_state = {
            "state": "empty",
            "identity": capture_identity(repo, path),
            "members": [],
        }
    else:
        before_state = {"state": "absent", "identity": None, "members": []}
    return {
        "scopeId": f"isolated-{index}",
        "kind": "isolated_root",
        "path": normalized,
        "shared": False,
        "beforeState": before_state,
    }


def prepare_adjacent_scope(
    repo: Path,
    specification: dict[str, str],
    index: int,
) -> dict[str, Any]:
    if not isinstance(specification, dict):
        raise GeneratedArtifactError("invalid_adjacent_scope")
    if set(specification) != {"parent", "pattern"}:
        raise GeneratedArtifactError("invalid_adjacent_scope_fields")
    parent = normalize_relative_path(specification["parent"])
    reject_protected_path(parent, repo=repo)
    pattern = normalize_pattern(specification["pattern"])
    parent_path = local_path(repo, parent, require_exists=True)
    if parent_path.is_symlink() or not parent_path.is_dir():
        raise GeneratedArtifactError("adjacent_parent_not_directory", parent)
    return {
        "scopeId": f"adjacent-{index}",
        "kind": "adjacent_output",
        "parent": parent,
        "pattern": pattern,
        "shared": False,
        "beforeState": {
            "parentIdentity": capture_identity(repo, parent_path),
            "entries": inventory_tree(repo, parent_path, include_root=False),
        },
    }


def validate_contract(
    repo: Path,
    contract: Any,
    *,
    require_current_baseline: bool = False,
) -> list[str]:
    repo = Path(repo).expanduser().resolve()
    if not isinstance(contract, dict):
        return ["contract_not_object"]
    errors = field_errors(contract, CONTRACT_FIELDS)
    for field in sorted(CONTRACT_FIELDS - set(contract)):
        errors.append(f"missing_field:{field}")
    if contract.get("schema") != CONTRACT_SCHEMA:
        errors.append("invalid_schema")
    for field in ("contractId", "taskId", "runId"):
        if not valid_identifier(contract.get(field)):
            errors.append(f"invalid_identifier:{field}")
    if not positive_timestamp_ns(contract.get("sealedAtNs")):
        errors.append("invalid_sealed_at")
    errors.extend(validate_repository(repo, contract.get("repository")))
    errors.extend(validate_owner(contract.get("owner")))
    owner = contract.get("owner")
    if isinstance(owner, dict) and owner.get("uid") != os.getuid():
        errors.append("owner_uid_mismatch:contract")
    errors.extend(validate_command(contract.get("command")))
    if contract.get("retention") not in RETENTION_POLICIES:
        errors.append("invalid_retention")
    errors.extend(
        validate_scopes(
            repo,
            contract.get("scopes"),
            require_current_baseline=require_current_baseline,
        )
    )
    return sorted(set(errors))


def validate_manifest(
    repo: Path,
    manifest: Any,
    *,
    contract: Optional[dict[str, Any]] = None,
) -> list[str]:
    repo = Path(repo).expanduser().resolve()
    if not isinstance(manifest, dict):
        return ["manifest_not_object"]
    errors = field_errors(manifest, MANIFEST_FIELDS)
    for field in sorted(MANIFEST_FIELDS - set(manifest)):
        errors.append(f"missing_field:{field}")
    if manifest.get("schema") != MANIFEST_SCHEMA:
        errors.append("invalid_manifest_schema")
    if not valid_sha256(manifest.get("contractSha256")):
        errors.append("invalid_contract_digest")
    contract_seal = manifest.get("contractSeal")
    if not valid_identity(contract_seal):
        errors.append("invalid_contract_seal")
    if not positive_timestamp_ns(manifest.get("observedAtNs")):
        errors.append("invalid_observed_at")
    errors.extend(validate_repository(repo, manifest.get("repository")))
    for field in ("taskId", "runId"):
        if not valid_identifier(manifest.get(field)):
            errors.append(f"invalid_identifier:{field}")
    errors.extend(validate_manifest_owner(manifest.get("owner")))
    errors.extend(validate_command_result(manifest.get("commandResult")))
    errors.extend(validate_manifest_entries(manifest.get("entries")))
    errors.extend(validate_scope_inventories(manifest.get("scopeInventories")))
    errors.extend(validate_manifest_identity_times(manifest, contract))
    if contract is not None:
        if manifest.get("contractSha256") != document_sha256(contract):
            errors.append("manifest_contract_mismatch")
        expected_seal_path = contract_document_relative_path(contract)
        if (
            isinstance(contract_seal, dict)
            and contract_seal.get("path") != expected_seal_path
        ):
            errors.append("manifest_contract_seal_path_mismatch")
        if (
            isinstance(contract_seal, dict)
            and contract_seal.get("sha256") != document_sha256(contract)
        ):
            errors.append("manifest_contract_seal_hash_mismatch")
        if (
            positive_timestamp_ns(manifest.get("observedAtNs"))
            and isinstance(contract_seal, dict)
            and json_integer(contract_seal.get("ctimeNs"))
            and manifest["observedAtNs"] < contract_seal["ctimeNs"]
        ):
            errors.append("manifest_observed_before_contract_seal")
        if (
            positive_timestamp_ns(manifest.get("observedAtNs"))
            and positive_timestamp_ns(contract.get("sealedAtNs"))
            and manifest["observedAtNs"] < contract["sealedAtNs"]
        ):
            errors.append("manifest_observed_before_contract")
        if manifest.get("taskId") != contract.get("taskId"):
            errors.append("manifest_task_mismatch")
        if manifest.get("runId") != contract.get("runId"):
            errors.append("manifest_run_mismatch")
        if manifest.get("repository") != contract.get("repository"):
            errors.append("manifest_repository_mismatch")
        errors.extend(owner_binding_reasons(contract, manifest))
        errors.extend(validate_manifest_contract_coverage(contract, manifest))
    return sorted(set(errors))


def validate_manifest_identity_times(
    manifest: dict[str, Any],
    contract: Optional[dict[str, Any]],
) -> list[str]:
    observed_at = manifest.get("observedAtNs")
    if not positive_timestamp_ns(observed_at):
        return []
    sealed_at = contract.get("sealedAtNs") if isinstance(contract, dict) else None
    errors: list[str] = []
    entries = manifest.get("entries")
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict) or not json_integer(entry.get("ctimeNs")):
            continue
        path = str(entry.get("path") or "unknown")
        if positive_timestamp_ns(sealed_at) and entry["ctimeNs"] < sealed_at:
            errors.append(f"invalid_manifest_entry_before_contract:{path}")
        if entry["ctimeNs"] > observed_at:
            errors.append(f"invalid_manifest_entry_after_observation:{path}")
    inventories = manifest.get("scopeInventories")
    for inventory in inventories if isinstance(inventories, list) else []:
        inventory_entries = (
            inventory.get("entries")
            if isinstance(inventory, dict)
            else None
        )
        for entry in inventory_entries if isinstance(inventory_entries, list) else []:
            if not isinstance(entry, dict) or not json_integer(entry.get("ctimeNs")):
                continue
            if entry["ctimeNs"] > observed_at:
                path = str(entry.get("path") or "unknown")
                errors.append(
                    f"invalid_scope_inventory_entry_after_observation:{path}"
                )
    return errors


def validate_manifest_owner(owner: Any) -> list[str]:
    if not isinstance(owner, dict):
        return ["invalid_manifest_owner"]
    errors = nested_field_errors("owner", owner, MANIFEST_OWNER_FIELDS)
    if not valid_identifier(owner.get("id")):
        errors.append("invalid_owner_id")
    if not valid_pid(owner.get("pid")):
        errors.append("invalid_owner_pid")
    if not nonnegative_integer(owner.get("uid")):
        errors.append("invalid_owner_uid")
    for field in ("processAlive", "leaseActive", "completed"):
        if not isinstance(owner.get(field), bool):
            label = {
                "processAlive": "process_alive",
                "leaseActive": "lease_active",
                "completed": "completed",
            }[field]
            errors.append(f"invalid_owner_{label}")
    return errors


def validate_command_result(result: Any) -> list[str]:
    if not isinstance(result, dict):
        return ["invalid_command_result"]
    errors = nested_field_errors("commandResult", result, COMMAND_RESULT_FIELDS)
    exit_code = result.get("exitCode")
    if not isinstance(exit_code, int) or isinstance(exit_code, bool):
        errors.append("invalid_command_exit_code")
    if result.get("completed") is not True:
        errors.append("invalid_command_completion")
    return errors


def scope_inventory_structure_errors(
    scope: dict[str, Any],
    entries: list[dict[str, Any]],
) -> list[str]:
    label = str(scope.get("scopeId") or "unknown")
    error = [f"manifest_scope_inventory_structure:{label}"]
    by_path = {entry["path"]: entry for entry in entries}
    if len(by_path) != len(entries):
        return error

    kind = scope.get("kind")
    boundary_value = (
        scope.get("path")
        if kind == "isolated_root"
        else scope.get("parent")
        if kind == "adjacent_output"
        else None
    )
    if not safe_relative_path(boundary_value):
        return error
    boundary = PurePosixPath(boundary_value)

    if kind == "isolated_root":
        before_state = scope.get("beforeState")
        root_required = (
            isinstance(before_state, dict)
            and before_state.get("state") == "empty"
        )
        root_entry = by_path.get(boundary_value)
        if (entries or root_required) and (
            not isinstance(root_entry, dict)
            or root_entry.get("type") != "directory"
        ):
            return error

    for path, entry in by_path.items():
        current = PurePosixPath(path)
        if kind == "isolated_root" and current == boundary:
            continue
        if boundary not in current.parents:
            return error
        parent = current.parent
        if parent == boundary and kind == "adjacent_output":
            continue
        parent_entry = by_path.get(parent.as_posix())
        if not isinstance(parent_entry, dict) or parent_entry.get("type") != "directory":
            return error
    return []


def validate_manifest_contract_coverage(
    contract: dict[str, Any],
    manifest: dict[str, Any],
) -> list[str]:
    scopes = contract.get("scopes")
    inventories = manifest.get("scopeInventories")
    entries = manifest.get("entries")
    if (
        not isinstance(scopes, list)
        or not isinstance(inventories, list)
        or not isinstance(entries, list)
        or not all(isinstance(scope, dict) for scope in scopes)
        or not all(isinstance(inventory, dict) for inventory in inventories)
        or not all(isinstance(entry, dict) for entry in entries)
    ):
        return []

    expected_scope_ids = [scope.get("scopeId") for scope in scopes]
    actual_scope_ids = [inventory.get("scopeId") for inventory in inventories]
    errors: list[str] = []
    if (
        not all(valid_identifier(scope_id) for scope_id in expected_scope_ids)
        or not all(valid_identifier(scope_id) for scope_id in actual_scope_ids)
        or len(expected_scope_ids) != len(set(expected_scope_ids))
        or actual_scope_ids != expected_scope_ids
    ):
        errors.append("manifest_scope_inventory_mismatch")
        return errors

    candidates: list[dict[str, Any]] = []
    for scope, inventory in zip(scopes, inventories):
        inventory_entries = inventory.get("entries")
        if (
            not isinstance(inventory_entries, list)
            or not all(valid_identity(entry) for entry in inventory_entries)
        ):
            errors.append(
                f"manifest_scope_inventory_unusable:{scope.get('scopeId', 'unknown')}"
            )
            continue
        structure_errors = scope_inventory_structure_errors(scope, inventory_entries)
        if structure_errors:
            errors.extend(structure_errors)
            continue
        try:
            candidates.extend(scope_candidates(scope, inventory_entries))
        except (GeneratedArtifactError, KeyError, TypeError, ValueError):
            errors.append(
                f"manifest_scope_inventory_unusable:{scope.get('scopeId', 'unknown')}"
            )
            continue
    candidates.sort(key=lambda entry: entry.get("path", ""))
    scopes_by_id = {
        scope["scopeId"]: scope
        for scope in scopes
        if valid_identifier(scope.get("scopeId"))
    }
    for entry in entries:
        scope_id = entry.get("scopeId")
        scope = scopes_by_id.get(scope_id) if isinstance(scope_id, str) else None
        if not isinstance(scope, dict):
            continue
        path = entry.get("path")
        before_state = scope.get("beforeState")
        if not isinstance(before_state, dict):
            continue
        if scope.get("kind") == "isolated_root":
            if (
                before_state.get("state") == "empty"
                and path == scope.get("path")
            ):
                errors.append(f"preexisting_path:{path}")
        else:
            baseline_entries = before_state.get("entries")
            baseline_paths = (
                [
                    item["path"]
                    for item in baseline_entries
                    if isinstance(item, dict)
                    and safe_relative_path(item.get("path"))
                ]
                if isinstance(baseline_entries, list)
                else []
            )
            if isinstance(path, str) and path in baseline_paths:
                errors.append(f"preexisting_path:{path}")
    if candidates != entries:
        errors.append("manifest_candidate_coverage_mismatch")
    return errors


def validate_manifest_entries(entries: Any) -> list[str]:
    if not isinstance(entries, list):
        return ["invalid_manifest_entries"]
    errors: list[str] = []
    paths: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != MANIFEST_ENTRY_FIELDS:
            errors.append("invalid_manifest_entry")
            continue
        identity = {field: entry[field] for field in IDENTITY_FIELDS}
        if not valid_identity(identity):
            errors.append(f"invalid_manifest_entry:{entry.get('path', 'unknown')}")
        if not valid_identifier(entry.get("scopeId")):
            errors.append(f"invalid_manifest_scope:{entry.get('path', 'unknown')}")
        if isinstance(entry.get("path"), str):
            paths.append(entry["path"])
    if paths != sorted(set(paths)):
        errors.append("invalid_manifest_entry_order")
    return errors


def validate_scope_inventories(inventories: Any) -> list[str]:
    if not isinstance(inventories, list):
        return ["invalid_scope_inventories"]
    errors: list[str] = []
    scope_ids: list[str] = []
    for inventory in inventories:
        if not isinstance(inventory, dict) or set(inventory) != SCOPE_INVENTORY_FIELDS:
            errors.append("invalid_scope_inventory")
            continue
        scope_id = inventory.get("scopeId")
        if not valid_identifier(scope_id):
            errors.append("invalid_scope_inventory_id")
        else:
            scope_ids.append(scope_id)
        entries = inventory.get("entries")
        if not isinstance(entries, list) or not all(valid_identity(item) for item in entries):
            errors.append(f"invalid_scope_inventory_entries:{scope_id or 'unknown'}")
            continue
        paths = [entry["path"] for entry in entries]
        if paths != sorted(set(paths)):
            errors.append(f"invalid_scope_inventory_order:{scope_id or 'unknown'}")
        for entry in entries:
            if entry["type"] != "directory":
                continue
            entry_path = PurePosixPath(entry["path"])
            expected_members = sorted(
                path
                for path in paths
                if PurePosixPath(path).parent == entry_path
            )
            if entry["members"] != expected_members:
                errors.append(
                    "invalid_scope_inventory_membership:"
                    f"{scope_id or 'unknown'}:{entry['path']}"
                )
    if len(scope_ids) != len(set(scope_ids)):
        errors.append("duplicate_scope_inventory")
    return errors


def validate_receipt(
    receipt: Any,
    *,
    contract: Optional[dict[str, Any]] = None,
    manifest: Optional[dict[str, Any]] = None,
    plan: Optional[dict[str, Any]] = None,
) -> list[str]:
    if not isinstance(receipt, dict):
        return ["receipt_not_object"]
    errors = field_errors(receipt, RECEIPT_FIELDS)
    for field in sorted(RECEIPT_FIELDS - set(receipt)):
        errors.append(f"missing_field:{field}")
    if receipt.get("schema") != RECEIPT_SCHEMA:
        errors.append("invalid_receipt_schema")
    for field in ("contractSha256", "manifestSha256", "planSha256"):
        if not valid_sha256(receipt.get(field)):
            errors.append(f"invalid_receipt_digest:{field}")
    if receipt.get("decision") not in DECISIONS:
        errors.append("invalid_receipt_decision")
    if receipt.get("status") not in ("complete", "failed", "blocked"):
        errors.append("invalid_receipt_status")
    for field in ("removed", "remaining", "absent", "retained"):
        errors.extend(validate_path_list(receipt.get(field), f"receipt_{field}"))
    if not isinstance(receipt.get("zeroUnlistedMutation"), bool):
        errors.append("invalid_zero_unlisted_mutation")
    effects = receipt.get("effects")
    if not isinstance(effects, dict) or set(effects) != EFFECT_FIELDS:
        errors.append("invalid_receipt_effects")
    else:
        for effect in sorted(EFFECT_FIELDS):
            if effects.get(effect) is not False:
                errors.append(f"receipt_unlisted_effect:{effect}")
    failure = receipt.get("failure")
    if failure is not None:
        if not isinstance(failure, dict) or set(failure) != FAILURE_FIELDS:
            errors.append("invalid_receipt_failure")
    if contract is not None and receipt.get("contractSha256") != document_sha256(contract):
        errors.append("receipt_contract_mismatch")
    if manifest is not None and receipt.get("manifestSha256") != document_sha256(manifest):
        errors.append("receipt_manifest_mismatch")
    if plan is not None and receipt.get("planSha256") != document_sha256(plan):
        errors.append("receipt_plan_mismatch")
    return sorted(set(errors))


def validate_plan(
    plan: Any,
    *,
    contract: Optional[dict[str, Any]] = None,
    manifest: Optional[dict[str, Any]] = None,
    repo: Optional[Path] = None,
) -> list[str]:
    if not isinstance(plan, dict):
        return ["plan_not_object"]
    errors = field_errors(plan, PLAN_FIELDS)
    for field in sorted(PLAN_FIELDS - set(plan)):
        errors.append(f"missing_field:{field}")
    if plan.get("schema") != PLAN_SCHEMA:
        errors.append("invalid_plan_schema")
    if not valid_sha256(plan.get("contractSha256")):
        errors.append("invalid_plan_digest:contractSha256")
    if not valid_sha256(plan.get("manifestSha256")):
        errors.append("invalid_plan_digest:manifestSha256")
    if plan.get("decision") not in DECISIONS:
        errors.append("invalid_plan_decision")
    reasons = plan.get("reasons")
    if (
        not isinstance(reasons, list)
        or not reasons
        or not all(isinstance(reason, str) and reason for reason in reasons)
        or reasons != sorted(set(reasons))
    ):
        errors.append("invalid_plan_reasons")
    entries = plan.get("entries")
    retained = plan.get("retained")
    errors.extend(validate_path_list(entries, "plan_entries"))
    errors.extend(validate_path_list(retained, "plan_retained"))
    entries_are_paths = isinstance(entries, list) and all(
        safe_relative_path(entry) for entry in entries
    )
    retained_are_paths = isinstance(retained, list) and all(
        safe_relative_path(entry) for entry in retained
    )
    if entries_are_paths and retained_are_paths:
        if not set(retained).issubset(set(entries)):
            errors.append("plan_retained_not_subset")
        if plan.get("decision") == RETAIN and retained != entries:
            errors.append("plan_retain_incomplete")
        if plan.get("decision") != RETAIN and retained:
            errors.append("plan_unexpected_retained")
    if contract is not None and plan.get("contractSha256") != document_sha256(contract):
        errors.append("plan_contract_mismatch")
    if manifest is not None and plan.get("manifestSha256") != document_sha256(manifest):
        errors.append("plan_manifest_mismatch")
    if manifest is not None and plan.get("entries") != manifest_paths(manifest):
        errors.append("plan_entries_manifest_mismatch")
    if contract is not None and manifest is not None:
        errors.extend(
            validate_plan_contract_policy(
                plan,
                contract,
                manifest,
                repo=repo,
            )
        )
    return sorted(set(errors))


def validate_plan_contract_policy(
    plan: dict[str, Any],
    contract: dict[str, Any],
    manifest: dict[str, Any],
    *,
    repo: Optional[Path] = None,
) -> list[str]:
    decision = plan.get("decision")
    reasons = plan.get("reasons")
    retention = contract.get("retention")
    errors: list[str] = []
    recorded_reasons = recorded_safety_reasons(contract, manifest, repo=repo)
    if recorded_reasons:
        if decision != HUMAN_GATE:
            errors.append("plan_decision_contract_mismatch")
        reason_values = (
            {reason for reason in reasons if isinstance(reason, str)}
            if isinstance(reasons, list)
            else set()
        )
        if (
            not isinstance(reasons, list)
            or not set(recorded_reasons).issubset(reason_values)
        ):
            errors.append("plan_reasons_contract_mismatch")
        return errors
    if not isinstance(retention, str):
        return errors
    if retention in ("retain", "promote"):
        if decision not in (RETAIN, HUMAN_GATE):
            errors.append("plan_decision_contract_mismatch")
            if reasons != [f"retention_{retention}"]:
                errors.append("plan_reasons_contract_mismatch")
        elif decision == RETAIN and reasons != [f"retention_{retention}"]:
            errors.append("plan_reasons_contract_mismatch")
        return errors
    if retention != "cleanup":
        return errors

    owner = manifest.get("owner")
    owner_active = (
        isinstance(owner, dict)
        and (
            owner.get("processAlive") is True
            or owner.get("leaseActive") is True
            or owner.get("completed") is not True
        )
    )
    if repo is not None:
        try:
            owner_active = owner_active or owner_is_active_without_manifest(
                Path(repo).expanduser().resolve(),
                contract,
            )
        except (GeneratedArtifactError, KeyError, OSError, TypeError, ValueError):
            owner_active = True
    if decision == RETAIN:
        errors.append("plan_decision_contract_mismatch")
    elif decision == WAIT_OWNER:
        if not owner_active:
            errors.append("plan_decision_contract_mismatch")
        if reasons != ["owner_active"]:
            errors.append("plan_reasons_contract_mismatch")
    elif decision == AUTO_CLEAN:
        if owner_active:
            errors.append("plan_decision_contract_mismatch")
        if reasons != ["all_invariants_pass"]:
            errors.append("plan_reasons_contract_mismatch")
    return errors


def validate_terminal_cleanup(
    repo: Path,
    contract: Any,
    manifest: Any,
    plan: Any,
    receipt: Any,
) -> list[str]:
    repo = Path(repo).expanduser().resolve()
    bound_contract = contract if isinstance(contract, dict) else None
    bound_manifest = manifest if isinstance(manifest, dict) else None
    bound_plan = plan if isinstance(plan, dict) else None
    errors = [
        *(f"contract:{error}" for error in validate_contract(repo, contract)),
        *(
            f"manifest:{error}"
            for error in validate_manifest(
                repo,
                manifest,
                contract=bound_contract,
            )
        ),
        *(
            f"plan:{error}"
            for error in validate_plan(
                plan,
                contract=bound_contract,
                manifest=bound_manifest,
                repo=repo,
            )
        ),
        *(
            f"receipt:{error}"
            for error in validate_receipt(
                receipt,
                contract=bound_contract,
                manifest=bound_manifest,
                plan=bound_plan,
            )
        ),
    ]
    if not all(
        isinstance(document, dict)
        for document in (contract, manifest, plan, receipt)
    ):
        return sorted(set(errors))
    raw_entries = plan.get("entries")
    entries = (
        raw_entries
        if isinstance(raw_entries, list)
        and all(isinstance(entry, str) for entry in raw_entries)
        else []
    )
    if plan.get("decision") != AUTO_CLEAN:
        errors.append("terminal_cleanup_requires_auto_clean")
    if receipt.get("decision") != AUTO_CLEAN:
        errors.append("terminal_receipt_not_auto_clean")
    if receipt.get("status") != "complete":
        errors.append("terminal_receipt_not_complete")
    if receipt.get("failure") is not None:
        errors.append("terminal_receipt_has_failure")
    if receipt.get("removed") != entries:
        errors.append("terminal_receipt_removed_mismatch")
    if receipt.get("remaining") != []:
        errors.append("terminal_receipt_has_remaining")
    if receipt.get("absent") != entries:
        errors.append("terminal_receipt_absent_mismatch")
    if receipt.get("retained") != plan.get("retained", []):
        errors.append("terminal_receipt_retained_mismatch")
    if receipt.get("zeroUnlistedMutation") is not True:
        errors.append("terminal_receipt_unlisted_mutation")
    remaining = set(present_paths(repo, entries))
    try:
        scopes = contract.get("scopes")
        for scope in scopes if isinstance(scopes, list) else []:
            inventory = observe_scope_inventory(repo, scope)
            remaining.update(
                entry["path"]
                for entry in scope_candidates(scope, inventory)
            )
    except (GeneratedArtifactError, KeyError, TypeError, ValueError) as error:
        code = error.code if isinstance(error, GeneratedArtifactError) else "invalid_scope"
        errors.append(f"terminal_scope_observation_failed:{code}")
    errors.extend(
        f"generated_artifact_remaining:{path}"
        for path in sorted(remaining)
    )
    return sorted(set(errors))


def inspect_generated_artifact_lifecycle(repo: Path) -> dict[str, Any]:
    repo = Path(repo).expanduser().resolve()
    root = repo / LIFECYCLE_EVIDENCE_ROOT
    if not (root.exists() or root.is_symlink()):
        return lifecycle_inspection_report([], [])
    if root.is_symlink() or not root.is_dir():
        return lifecycle_inspection_report(
            [],
            ["generated_artifact_registry_not_trusted"],
        )

    documents: list[dict[str, Any]] = []
    issues: list[str] = []
    recognized_schemas = {
        CONTRACT_SCHEMA,
        MANIFEST_SCHEMA,
        PLAN_SCHEMA,
        RECEIPT_SCHEMA,
    }
    try:
        entries = sorted(os.scandir(root), key=lambda entry: entry.name)
    except OSError as error:
        return lifecycle_inspection_report(
            [],
            [f"generated_artifact_registry_unreadable:{error}"],
        )
    document_paths: list[Path] = []
    for entry in entries:
        path = root / entry.name
        relative = path.relative_to(repo).as_posix()
        if entry.name == "contracts" and not entry.is_symlink():
            if not entry.is_dir(follow_symlinks=False):
                issues.append(f"untrusted_lifecycle_entry:{relative}")
                continue
            try:
                contract_entries = sorted(
                    os.scandir(path),
                    key=lambda item: item.name,
                )
            except OSError as error:
                issues.append(
                    f"generated_artifact_contract_registry_unreadable:{error}"
                )
                continue
            for contract_entry in contract_entries:
                contract_path = path / contract_entry.name
                contract_relative = contract_path.relative_to(repo).as_posix()
                if (
                    contract_entry.is_symlink()
                    or not contract_entry.is_file(follow_symlinks=False)
                ):
                    issues.append(
                        f"untrusted_lifecycle_entry:{contract_relative}"
                    )
                    continue
                document_paths.append(contract_path)
            continue
        if entry.is_symlink() or not entry.is_file(follow_symlinks=False):
            issues.append(f"untrusted_lifecycle_entry:{relative}")
            continue
        document_paths.append(path)

    for path in document_paths:
        relative = path.relative_to(repo).as_posix()
        try:
            document = load_immutable_document(path)
        except GeneratedArtifactError as error:
            issues.append(f"invalid_lifecycle_document:{relative}:{error.code}")
            continue
        if document.get("schema") not in recognized_schemas:
            issues.append(f"unknown_lifecycle_document:{relative}")
            continue
        if (
            path.parent.name == "contracts"
            and document.get("schema") != CONTRACT_SCHEMA
        ):
            issues.append(f"invalid_contract_seal_document:{relative}")
            continue
        documents.append(
            {
                "path": relative,
                "document": document,
                "sha256": document_sha256(document),
            }
        )

    by_schema = {
        schema: [
            item
            for item in documents
            if item["document"].get("schema") == schema
        ]
        for schema in recognized_schemas
    }
    records: list[dict[str, Any]] = []
    used_paths: set[str] = set()
    for contract_item in by_schema[CONTRACT_SCHEMA]:
        used_paths.add(contract_item["path"])
        record, consumed = inspect_registered_contract(
            repo,
            contract_item,
            manifests=by_schema[MANIFEST_SCHEMA],
            plans=by_schema[PLAN_SCHEMA],
            receipts=by_schema[RECEIPT_SCHEMA],
        )
        used_paths.update(consumed)
        records.append(record)

    for item in documents:
        if item["path"] not in used_paths:
            issues.append(f"orphan_lifecycle_document:{item['path']}")
    records.sort(key=lambda record: (record["contractId"], record["contractPath"]))
    return lifecycle_inspection_report(records, issues)


def inspect_registered_contract(
    repo: Path,
    contract_item: dict[str, Any],
    *,
    manifests: list[dict[str, Any]],
    plans: list[dict[str, Any]],
    receipts: list[dict[str, Any]],
) -> tuple[dict[str, Any], set[str]]:
    contract = contract_item["document"]
    consumed = {contract_item["path"]}
    contract_errors = validate_contract(repo, contract)
    if contract_errors:
        return (
            lifecycle_record(
                contract,
                contract_path=contract_item["path"],
                decision=HUMAN_GATE,
                status="invalid",
                reasons=contract_errors,
                next_action=human_gate_next_action(),
            ),
            consumed,
        )

    manifest_matches = [
        item
        for item in manifests
        if item["document"].get("contractSha256") == contract_item["sha256"]
    ]
    consumed.update(item["path"] for item in manifest_matches)
    if len(manifest_matches) != 1:
        owner_active = owner_is_active_without_manifest(repo, contract)
        decision = WAIT_OWNER if not manifest_matches and owner_active else HUMAN_GATE
        reasons = (
            ["owner_active"]
            if decision == WAIT_OWNER
            else [
                "missing_manifest"
                if not manifest_matches
                else "ambiguous_manifest_binding"
            ]
        )
        next_action = (
            wait_owner_next_action()
            if decision == WAIT_OWNER
            else (
                "Observe the bound command result and persist one immutable manifest "
                "before planning cleanup."
                if not manifest_matches
                else human_gate_next_action()
            )
        )
        return (
            lifecycle_record(
                contract,
                contract_path=contract_item["path"],
                decision=decision,
                status="waiting" if decision == WAIT_OWNER else "unresolved",
                reasons=reasons,
                next_action=next_action,
            ),
            consumed,
        )

    manifest_item = manifest_matches[0]
    manifest = manifest_item["document"]
    manifest_errors = validate_manifest(repo, manifest, contract=contract)
    if manifest_errors:
        return (
            lifecycle_record(
                contract,
                contract_path=contract_item["path"],
                manifest_path=manifest_item["path"],
                decision=HUMAN_GATE,
                status="invalid",
                reasons=manifest_errors,
                next_action=human_gate_next_action(),
            ),
            consumed,
        )

    plan_matches = [
        item
        for item in plans
        if (
            item["document"].get("contractSha256") == contract_item["sha256"]
            and item["document"].get("manifestSha256") == manifest_item["sha256"]
        )
    ]
    consumed.update(item["path"] for item in plan_matches)
    if len(plan_matches) > 1:
        return (
            lifecycle_record(
                contract,
                contract_path=contract_item["path"],
                manifest_path=manifest_item["path"],
                decision=HUMAN_GATE,
                status="unresolved",
                reasons=["ambiguous_plan_binding"],
                next_action=human_gate_next_action(),
            ),
            consumed,
        )

    fresh_plan = plan_cleanup(repo, contract, manifest)
    plan_item = plan_matches[0] if plan_matches else None
    plan = plan_item["document"] if plan_item else fresh_plan
    if plan_item:
        plan_errors = validate_plan(
            plan,
            contract=contract,
            manifest=manifest,
            repo=repo,
        )
        if plan_errors:
            return (
                lifecycle_record(
                    contract,
                    contract_path=contract_item["path"],
                    manifest_path=manifest_item["path"],
                    plan_path=plan_item["path"],
                    decision=HUMAN_GATE,
                    status="unresolved",
                    reasons=plan_errors,
                    next_action=human_gate_next_action(),
                ),
                consumed,
            )

    plan_sha = document_sha256(plan)
    receipt_matches = [
        item
        for item in receipts
        if (
            item["document"].get("contractSha256") == contract_item["sha256"]
            and item["document"].get("manifestSha256") == manifest_item["sha256"]
            and item["document"].get("planSha256") == plan_sha
        )
    ]
    consumed.update(item["path"] for item in receipt_matches)
    if len(receipt_matches) > 1:
        return (
            lifecycle_record(
                contract,
                contract_path=contract_item["path"],
                manifest_path=manifest_item["path"],
                plan_path=plan_item["path"] if plan_item else None,
                decision=HUMAN_GATE,
                status="unresolved",
                reasons=["ambiguous_receipt_binding"],
                next_action=human_gate_next_action(),
            ),
            consumed,
        )
    if receipt_matches:
        receipt_item = receipt_matches[0]
        terminal_errors = validate_terminal_cleanup(
            repo,
            contract,
            manifest,
            plan,
            receipt_item["document"],
        )
        if not terminal_errors:
            return (
                lifecycle_record(
                    contract,
                    contract_path=contract_item["path"],
                    manifest_path=manifest_item["path"],
                    plan_path=plan_item["path"] if plan_item else None,
                    receipt_path=receipt_item["path"],
                    decision=AUTO_CLEAN,
                    status="complete",
                    reasons=["terminal_cleanup_receipt_valid"],
                    next_action=(
                        "Continue the owning workflow and retain the terminal "
                        "cleanup receipt as evidence."
                    ),
                ),
                consumed,
            )
        return (
            lifecycle_record(
                contract,
                contract_path=contract_item["path"],
                manifest_path=manifest_item["path"],
                plan_path=plan_item["path"] if plan_item else None,
                receipt_path=receipt_item["path"],
                decision=HUMAN_GATE,
                status="invalid",
                reasons=terminal_errors,
                next_action=human_gate_next_action(),
            ),
            consumed,
        )

    if plan_item and plan != fresh_plan:
        return (
            lifecycle_record(
                contract,
                contract_path=contract_item["path"],
                manifest_path=manifest_item["path"],
                plan_path=plan_item["path"],
                decision=HUMAN_GATE,
                status="unresolved",
                reasons=["stale_or_self_authored_plan"],
                next_action=human_gate_next_action(),
            ),
            consumed,
        )

    decision = fresh_plan["decision"]
    status = {
        AUTO_CLEAN: "ready",
        WAIT_OWNER: "waiting",
        RETAIN: "retained",
        HUMAN_GATE: "unresolved",
    }[decision]
    next_action = {
        AUTO_CLEAN: (
            "Persist the fresh plan, run `cleanup --apply`, and retain the "
            "terminal cleanup receipt."
        ),
        WAIT_OWNER: wait_owner_next_action(),
        RETAIN: (
            "Retain the artifacts under the owning workflow and do not apply cleanup."
        ),
        HUMAN_GATE: human_gate_next_action(),
    }[decision]
    return (
        lifecycle_record(
            contract,
            contract_path=contract_item["path"],
            manifest_path=manifest_item["path"],
            plan_path=plan_item["path"] if plan_item else None,
            decision=decision,
            status=status,
            reasons=fresh_plan["reasons"],
            next_action=next_action,
        ),
        consumed,
    )


def lifecycle_record(
    contract: dict[str, Any],
    *,
    contract_path: str,
    decision: str,
    status: str,
    reasons: list[str],
    next_action: str,
    manifest_path: Optional[str] = None,
    plan_path: Optional[str] = None,
    receipt_path: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "contractId": str(contract.get("contractId") or "unknown"),
        "taskId": str(contract.get("taskId") or "unknown"),
        "runId": str(contract.get("runId") or "unknown"),
        "decision": decision,
        "status": status,
        "reasons": sorted(set(reasons)),
        "nextAction": next_action,
        "contractPath": contract_path,
        "manifestPath": manifest_path,
        "planPath": plan_path,
        "cleanupReceiptPath": receipt_path,
    }


def lifecycle_inspection_report(
    records: list[dict[str, Any]],
    issues: list[str],
) -> dict[str, Any]:
    unique_issues = sorted(set(issues))
    unresolved = [
        record
        for record in records
        if record["status"] not in ("complete", "retained")
    ]
    ok = not unique_issues and not unresolved
    if unique_issues:
        status = "invalid"
    elif unresolved:
        status = "unresolved"
    elif records:
        status = "complete"
    else:
        status = "not_applicable"
    next_actions = {
        record["nextAction"]
        for record in records
        if record["status"] != "complete"
    }
    if unique_issues:
        next_actions.add(human_gate_next_action())
    return {
        "ok": ok,
        "status": status,
        "records": records,
        "unresolved": unresolved,
        "issues": unique_issues,
        "nextActions": sorted(next_actions),
    }


def owner_is_active_without_manifest(repo: Path, contract: dict[str, Any]) -> bool:
    owner = contract["owner"]
    return owner_process_active(contract) or owner_lease_active(
        repo,
        owner.get("lease"),
    )


def wait_owner_next_action() -> str:
    return (
        "Wait for the owning process or lease to exit, then observe and plan again."
    )


def human_gate_next_action() -> str:
    return (
        "Record the failed invariants and resolve the Human Gate before any cleanup."
    )


def validate_path_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(safe_relative_path(item) for item in value):
        return [f"invalid_{label}"]
    if value != sorted(set(value)):
        return [f"invalid_{label}_order"]
    return []


def validate_repository(repo: Path, repository: Any) -> list[str]:
    if not isinstance(repository, dict):
        return ["invalid_repository"]
    errors = nested_field_errors("repository", repository, REPOSITORY_FIELDS)
    if repository.get("root") != str(repo):
        errors.append("repository_root_mismatch")
    try:
        root_stat = os.stat(repo, follow_symlinks=False)
    except OSError:
        return errors + ["repository_unavailable"]
    recorded_device = repository.get("device")
    recorded_inode = repository.get("inode")
    if not nonnegative_integer(recorded_device):
        errors.append("invalid_repository_device")
    elif recorded_device != root_stat.st_dev:
        errors.append("repository_device_mismatch")
    if not nonnegative_integer(recorded_inode):
        errors.append("invalid_repository_inode")
    elif recorded_inode != root_stat.st_ino:
        errors.append("repository_inode_mismatch")
    recorded_git_root = repository.get("gitRoot")
    if recorded_git_root is not None and not isinstance(recorded_git_root, str):
        errors.append("invalid_repository_git_root")
    if recorded_git_root != git_root(repo):
        errors.append("repository_git_root_mismatch")
    return errors


def validate_owner(owner: Any) -> list[str]:
    if not isinstance(owner, dict):
        return ["invalid_owner"]
    errors = nested_field_errors("owner", owner, OWNER_FIELDS)
    if not valid_identifier(owner.get("id")):
        errors.append("invalid_owner_id")
    if not valid_pid(owner.get("pid")):
        errors.append("invalid_owner_pid")
    if not nonnegative_integer(owner.get("uid")):
        errors.append("invalid_owner_uid")
    process_start = owner.get("processStartToken")
    if process_start is not None and (
        not isinstance(process_start, str)
        or not process_start
        or len(process_start) > 512
    ):
        errors.append("invalid_owner_process_start_token")
    lease = owner.get("lease")
    if lease is not None:
        if not isinstance(lease, dict) or set(lease) != {"path", "identity"}:
            errors.append("invalid_owner_lease")
        else:
            lease_path = lease.get("path")
            identity = lease.get("identity")
            if not safe_relative_path(lease_path):
                errors.append("invalid_owner_lease_path")
            if not valid_identity(identity):
                errors.append("invalid_owner_lease_identity")
            elif identity.get("path") != lease_path:
                errors.append("owner_lease_identity_path_mismatch")
    return errors


def validate_command(command: Any) -> list[str]:
    if not isinstance(command, dict):
        return ["invalid_command"]
    errors = nested_field_errors("command", command, COMMAND_FIELDS)
    argv = command.get("argv")
    if not isinstance(argv, list) or not argv:
        errors.append("invalid_command_argv")
        return errors
    if not all(isinstance(token, str) and token for token in argv):
        errors.append("invalid_command_argv")
        return errors
    if command.get("sha256") != command_sha256(argv):
        errors.append("command_digest_mismatch")
    return errors


def validate_scopes(
    repo: Path,
    scopes: Any,
    *,
    require_current_baseline: bool,
) -> list[str]:
    if not isinstance(scopes, list) or not scopes:
        return ["invalid_scopes"]
    errors: list[str] = []
    scope_ids: list[str] = []
    for scope in scopes:
        if not isinstance(scope, dict):
            errors.append("invalid_scope")
            continue
        kind = scope.get("kind")
        allowed = (
            ISOLATED_SCOPE_FIELDS
            if kind == "isolated_root"
            else ADJACENT_SCOPE_FIELDS
            if kind == "adjacent_output"
            else set()
        )
        if not allowed:
            errors.append("invalid_scope_kind")
            continue
        errors.extend(nested_field_errors("scope", scope, allowed))
        scope_id = scope.get("scopeId")
        if not valid_identifier(scope_id):
            errors.append("invalid_scope_id")
        else:
            scope_ids.append(scope_id)
        if scope.get("shared") is not False:
            errors.append(f"shared_scope:{scope_id or 'unknown'}")
        relative = scope.get("path") if kind == "isolated_root" else scope.get("parent")
        if not safe_relative_path(relative):
            errors.append(f"invalid_scope_path:{scope_id or 'unknown'}")
        elif protected_path(str(relative), repo=repo):
            errors.append(f"protected_scope:{scope_id or 'unknown'}")
        if kind == "adjacent_output":
            try:
                normalize_pattern(scope.get("pattern"))
            except GeneratedArtifactError:
                errors.append(f"invalid_scope_pattern:{scope_id or 'unknown'}")
        before_state_errors = validate_before_state(
            kind,
            scope.get("beforeState"),
            scope_id,
            relative,
        )
        errors.extend(before_state_errors)
        if (
            not before_state_errors
            and safe_relative_path(relative)
        ):
            errors.extend(
                validate_stable_baseline_identity(
                    repo,
                    scope,
                    scope_id,
                )
            )
            if require_current_baseline:
                errors.extend(
                    validate_current_baseline(
                        repo,
                        scope,
                        scope_id,
                    )
                )
    if len(scope_ids) != len(set(scope_ids)):
        errors.append("duplicate_scope_id")
    try:
        ensure_disjoint_scopes(
            [scope for scope in scopes if isinstance(scope, dict)],
            repo=repo,
        )
    except GeneratedArtifactError as error:
        errors.append(error.code)
    return errors


def validate_before_state(
    kind: str,
    before_state: Any,
    scope_id: Any,
    scope_root: Any,
) -> list[str]:
    label = str(scope_id or "unknown")
    if not isinstance(before_state, dict):
        return [f"invalid_before_state:{label}"]
    if kind == "isolated_root":
        if set(before_state) != {"state", "identity", "members"}:
            return [f"invalid_before_state:{label}"]
        if before_state.get("state") not in ("absent", "empty"):
            return [f"invalid_before_state:{label}"]
        if before_state.get("members") != []:
            return [f"invalid_before_state:{label}"]
        identity = before_state.get("identity")
        if before_state.get("state") == "absent" and identity is not None:
            return [f"invalid_before_state:{label}"]
        if before_state.get("state") == "empty" and not valid_identity(identity):
            return [f"invalid_before_state:{label}"]
        if (
            before_state.get("state") == "empty"
            and identity.get("path") != scope_root
        ):
            return [f"isolated_baseline_identity_mismatch:{label}"]
        if (
            before_state.get("state") == "empty"
            and (
                identity.get("type") != "directory"
                or identity.get("members") != []
                or identity.get("sha256") is not None
            )
        ):
            return [f"isolated_baseline_not_empty:{label}"]
        return []
    if set(before_state) != {"parentIdentity", "entries"}:
        return [f"invalid_before_state:{label}"]
    if not valid_identity(before_state.get("parentIdentity")):
        return [f"invalid_before_state:{label}"]
    errors: list[str] = []
    parent_identity = before_state["parentIdentity"]
    if parent_identity.get("path") != scope_root:
        errors.append(f"adjacent_baseline_identity_mismatch:{label}")
    if (
        parent_identity.get("type") != "directory"
        or parent_identity.get("sha256") is not None
    ):
        errors.append(f"adjacent_baseline_parent_not_directory:{label}")
    entries = before_state.get("entries")
    if not isinstance(entries, list) or not all(valid_identity(item) for item in entries):
        return [f"invalid_before_state:{label}"]
    paths = [item["path"] for item in entries]
    if paths != sorted(set(paths)):
        errors.append(f"invalid_before_state_order:{label}")
    if safe_relative_path(scope_root):
        parent = PurePosixPath(str(scope_root))
        if any(parent not in PurePosixPath(path).parents for path in paths):
            errors.append(f"adjacent_baseline_scope_escape:{label}")
        expected_members = sorted(
            path
            for path in paths
            if PurePosixPath(path).parent == parent
        )
        if parent_identity.get("members") != expected_members:
            errors.append(f"adjacent_baseline_membership_mismatch:{label}")
        entries_by_path = {
            item["path"]: item
            for item in entries
        }
        for entry in entries:
            if entry.get("type") != "directory":
                continue
            entry_path = PurePosixPath(entry["path"])
            children = sorted(
                path
                for path in entries_by_path
                if PurePosixPath(path).parent == entry_path
            )
            if entry.get("members") != children:
                errors.append(f"adjacent_baseline_membership_mismatch:{label}")
                break
    return errors


def validate_stable_baseline_identity(
    repo: Path,
    scope: dict[str, Any],
    scope_id: Any,
) -> list[str]:
    label = str(scope_id or "unknown")
    before_state = scope["beforeState"]
    if scope["kind"] == "isolated_root":
        if before_state["state"] != "empty":
            return []
        relative = scope["path"]
        recorded = before_state["identity"]
        error = f"isolated_baseline_identity_drift:{label}"
    else:
        relative = scope["parent"]
        recorded = before_state["parentIdentity"]
        error = f"adjacent_baseline_identity_drift:{label}"
    try:
        current = capture_identity(
            repo,
            local_path(repo, relative, require_exists=True),
        )
    except GeneratedArtifactError:
        return [error]
    stable_fields = ("path", "type", "device", "inode", "mode", "uid", "gid")
    if any(recorded.get(field) != current.get(field) for field in stable_fields):
        return [error]
    return []


def validate_current_baseline(
    repo: Path,
    scope: dict[str, Any],
    scope_id: Any,
) -> list[str]:
    label = str(scope_id or "unknown")
    before_state = scope["beforeState"]
    if scope["kind"] == "isolated_root":
        relative = scope["path"]
        try:
            path = local_path(repo, relative, require_exists=False)
        except GeneratedArtifactError:
            return [f"isolated_baseline_not_absent:{label}"]
        if before_state["state"] == "absent":
            if path.exists() or path.is_symlink():
                return [f"isolated_baseline_not_absent:{label}"]
            return []
        try:
            current = capture_identity(repo, path)
        except GeneratedArtifactError:
            return [f"isolated_baseline_identity_drift:{label}"]
        if current != before_state["identity"]:
            return [f"isolated_baseline_identity_drift:{label}"]
        return []
    try:
        parent = local_path(repo, scope["parent"], require_exists=True)
        parent_identity = capture_identity(repo, parent)
        entries = inventory_tree(repo, parent, include_root=False)
    except GeneratedArtifactError:
        return [f"adjacent_baseline_identity_drift:{label}"]
    errors: list[str] = []
    if parent_identity != before_state["parentIdentity"]:
        errors.append(f"adjacent_baseline_identity_drift:{label}")
    if entries != before_state["entries"]:
        errors.append(f"adjacent_baseline_inventory_incomplete:{label}")
    return errors


def inventory_tree(repo: Path, root: Path, *, include_root: bool) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    pending = [root]
    while pending:
        current = pending.pop()
        if current != root or include_root:
            entries.append(capture_identity(repo, current))
        try:
            current_stat = os.lstat(current)
        except OSError as error:
            raise GeneratedArtifactError("inventory_stat_failed", str(error)) from error
        if not stat.S_ISDIR(current_stat.st_mode):
            continue
        try:
            children = sorted(
                (Path(entry.path) for entry in os.scandir(current)),
                key=lambda path: path.name,
                reverse=True,
            )
        except OSError as error:
            raise GeneratedArtifactError("inventory_read_failed", str(error)) from error
        pending.extend(children)
    return sorted(entries, key=lambda entry: entry["path"])


def capture_identity(repo: Path, path: Path) -> dict[str, Any]:
    try:
        value = os.lstat(path)
    except OSError as error:
        raise GeneratedArtifactError("identity_stat_failed", str(error)) from error
    kind = file_type(value.st_mode)
    digest = file_sha256(path) if kind == "file" else None
    members: list[str] = []
    if kind == "directory":
        try:
            members = sorted(
                relative_path(repo, Path(entry.path))
                for entry in os.scandir(path)
            )
        except OSError as error:
            raise GeneratedArtifactError("identity_membership_failed", str(error)) from error
    return {
        "path": relative_path(repo, path),
        "type": kind,
        "device": value.st_dev,
        "inode": value.st_ino,
        "mode": stat.S_IMODE(value.st_mode),
        "nlink": value.st_nlink,
        "uid": value.st_uid,
        "gid": value.st_gid,
        "mtimeNs": value.st_mtime_ns,
        "ctimeNs": value.st_ctime_ns,
        "size": value.st_size,
        "sha256": digest,
        "members": members,
    }


def valid_identity(identity: Any) -> bool:
    if not isinstance(identity, dict) or set(identity) != IDENTITY_FIELDS:
        return False
    if not safe_relative_path(identity.get("path")):
        return False
    identity_type = identity.get("type")
    if not isinstance(identity_type, str) or identity_type not in (
        "file",
        "directory",
        "symlink",
        "socket",
        "fifo",
        "device",
        "other",
    ):
        return False
    nonnegative_fields = (
        "device",
        "inode",
        "uid",
        "gid",
        "size",
    )
    if not all(
        bounded_nonnegative_integer(identity.get(field))
        for field in nonnegative_fields
    ):
        return False
    mode = identity.get("mode")
    if not nonnegative_integer(mode) or mode > 0o7777:
        return False
    if (
        not positive_integer(identity.get("nlink"))
        or identity["nlink"] > OS_SCALAR_MAX
    ):
        return False
    if not all(
        timestamp_ns(identity.get(field))
        for field in ("mtimeNs", "ctimeNs")
    ):
        return False
    digest = identity.get("sha256")
    members = identity.get("members")
    if (
        not isinstance(members, list)
        or not all(safe_relative_path(item) for item in members)
        or members != sorted(set(members))
    ):
        return False
    if identity_type == "file":
        return valid_sha256(digest) and members == []
    if digest is not None:
        return False
    return identity_type == "directory" or members == []


def local_path(repo: Path, relative: str, *, require_exists: bool) -> Path:
    normalized = normalize_relative_path(relative)
    candidate = repo.joinpath(*PurePosixPath(normalized).parts)
    current = repo
    for part in PurePosixPath(normalized).parts:
        try:
            names = {entry.name for entry in os.scandir(current)}
        except (FileNotFoundError, NotADirectoryError):
            break
        except OSError as error:
            raise GeneratedArtifactError(
                "filesystem_path_unavailable",
                normalized,
            ) from error
        next_path = current / part
        if part not in names and (next_path.exists() or next_path.is_symlink()):
            raise GeneratedArtifactError("filesystem_path_alias", normalized)
        current = next_path
        if current.is_symlink():
            raise GeneratedArtifactError("scope_symlink", normalized)
        if not current.exists():
            break
    if require_exists and not candidate.exists():
        raise GeneratedArtifactError("scope_missing", normalized)
    return candidate


def normalize_relative_path(value: Any) -> str:
    if not safe_relative_path(value):
        raise GeneratedArtifactError("unsafe_relative_path", str(value))
    return PurePosixPath(str(value)).as_posix()


def safe_relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        return False
    pure = PurePosixPath(value)
    if pure.is_absolute() or value != pure.as_posix():
        return False
    if value in (".", "..") or any(part in ("", ".", "..") for part in pure.parts):
        return False
    return True


def normalize_pattern(value: Any) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise GeneratedArtifactError("unsafe_pattern")
    pure = PurePosixPath(value)
    if pure.is_absolute() or any(part == ".." for part in pure.parts):
        raise GeneratedArtifactError("unsafe_pattern")
    return pure.as_posix()


def filesystem_case_insensitive(repo: Optional[Path]) -> bool:
    if repo is None:
        return False
    return cached_filesystem_case_insensitive(
        str(Path(repo).expanduser().resolve())
    )


@lru_cache(maxsize=256)
def cached_filesystem_case_insensitive(root_value: str) -> bool:
    root = Path(root_value)
    for probe in (root, *root.parents):
        alias_name = ascii_case_alias(probe.name)
        if alias_name is None:
            continue
        alias = probe.with_name(alias_name)
        try:
            if alias.exists() and os.path.samefile(probe, alias):
                return True
        except OSError:
            continue
    return False


def ascii_case_alias(value: str) -> Optional[str]:
    for index, character in enumerate(value):
        if character.isascii() and character.isalpha():
            return value[:index] + character.swapcase() + value[index + 1 :]
    return None


def path_comparison_key(repo: Optional[Path], relative: str) -> str:
    normalized = unicodedata.normalize("NFC", relative)
    return normalized.casefold() if filesystem_case_insensitive(repo) else normalized


def protected_path(relative: str, *, repo: Optional[Path] = None) -> bool:
    key = path_comparison_key(repo, relative)
    pure = PurePosixPath(key)
    return any(
        pure == PurePosixPath(path_comparison_key(repo, protected))
        or PurePosixPath(path_comparison_key(repo, protected)) in pure.parents
        for protected in PROTECTED_PATHS
    )


def reject_protected_path(relative: str, *, repo: Optional[Path] = None) -> None:
    if protected_path(relative, repo=repo):
        raise GeneratedArtifactError("protected_scope", relative)


def ensure_disjoint_scopes(
    scopes: list[dict[str, Any]],
    *,
    repo: Optional[Path] = None,
) -> None:
    roots: list[tuple[str, PurePosixPath]] = []
    for scope in scopes:
        relative = scope.get("path") or scope.get("parent")
        if not isinstance(relative, str):
            continue
        root = PurePosixPath(path_comparison_key(repo, relative))
        for other_id, other in roots:
            if root == other or root in other.parents or other in root.parents:
                current_id = str(scope.get("scopeId") or "unknown")
                raise GeneratedArtifactError(
                    "overlapping_scopes",
                    f"{other_id}:{current_id}",
                )
        roots.append((str(scope.get("scopeId") or "unknown"), root))


def field_errors(document: dict[str, Any], allowed: set[str]) -> list[str]:
    return [f"unknown_field:{field}" for field in sorted(set(document) - allowed)]


def nested_field_errors(
    prefix: str,
    document: dict[str, Any],
    allowed: set[str],
) -> list[str]:
    errors = [
        f"unknown_field:{prefix}.{field}"
        for field in sorted(set(document) - allowed)
    ]
    errors.extend(
        f"missing_field:{prefix}.{field}"
        for field in sorted(allowed - set(document))
    )
    return errors


def require_identifier(label: str, value: Any) -> None:
    if not valid_identifier(value):
        raise GeneratedArtifactError(f"invalid_{label}")


def valid_identifier(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and len(value) <= 128
        and value[0].isalnum()
        and value[0].isascii()
        and all(character in IDENTIFIER_CHARS for character in value)
    )


def require_positive_integer(label: str, value: Any) -> None:
    if not positive_integer(value):
        raise GeneratedArtifactError(f"invalid_{label}")


def positive_integer(value: Any) -> bool:
    return json_integer(value) and value > 0


def valid_pid(value: Any) -> bool:
    return positive_integer(value) and value <= PID_MAX


def positive_timestamp_ns(value: Any) -> bool:
    return positive_integer(value) and value <= TIMESTAMP_NS_MAX


def timestamp_ns(value: Any) -> bool:
    return (
        json_integer(value)
        and TIMESTAMP_NS_MIN <= value <= TIMESTAMP_NS_MAX
    )


def bounded_nonnegative_integer(value: Any) -> bool:
    return nonnegative_integer(value) and value <= OS_SCALAR_MAX


def nonnegative_integer(value: Any) -> bool:
    return json_integer(value) and value >= 0


def json_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def command_sha256(command: list[str]) -> str:
    payload = json.dumps(command, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def document_sha256(document: Any) -> str:
    return hashlib.sha256(canonical_document_bytes(document)).hexdigest()


def canonical_document_bytes(document: Any) -> bytes:
    return (
        json.dumps(
            document,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    ).encode()


def load_immutable_document(path: Path) -> dict[str, Any]:
    path = Path(path).expanduser()
    if path.is_symlink() or not path.is_file():
        raise GeneratedArtifactError("document_not_regular", str(path))
    try:
        raw = path.read_bytes()
        document = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise GeneratedArtifactError("document_invalid", str(path)) from error
    if not isinstance(document, dict):
        raise GeneratedArtifactError("document_not_object", str(path))
    if raw != canonical_document_bytes(document):
        raise GeneratedArtifactError("document_not_canonical", str(path))
    return document


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise GeneratedArtifactError("identity_hash_failed", str(error)) from error
    return digest.hexdigest()


def valid_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(character in "0123456789abcdef" for character in value)


def file_type(mode: int) -> str:
    if stat.S_ISREG(mode):
        return "file"
    if stat.S_ISDIR(mode):
        return "directory"
    if stat.S_ISLNK(mode):
        return "symlink"
    if stat.S_ISSOCK(mode):
        return "socket"
    if stat.S_ISFIFO(mode):
        return "fifo"
    if stat.S_ISCHR(mode) or stat.S_ISBLK(mode):
        return "device"
    return "other"


def relative_path(repo: Path, path: Path) -> str:
    try:
        return path.absolute().relative_to(repo).as_posix()
    except ValueError as error:
        raise GeneratedArtifactError("scope_escape", str(path)) from error


def git_root(repo: Path) -> Optional[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return str(Path(result.stdout.strip()).resolve())
