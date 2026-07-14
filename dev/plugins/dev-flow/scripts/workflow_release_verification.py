from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from workflow_planning_paths import atomic_write_devflow, release_verification_root
from workflow_state import resolve_state, trusted_repo_regular_file


SCHEMA_VERSION = 1
TARGET_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
REQUIRED_STATE_GATES = (
    "spec_approved",
    "plan_written",
    "implementation_done",
    "verification_passed",
    "state_updated",
)
IGNORED_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache"}
IGNORED_SUFFIXES = {".pyc", ".pyo", ".log", ".tmp"}
DEVFLOW_PREPROMOTION_COMMAND = (
    "pythondontwritebytecode=1 python3.12 "
    "dev/scripts/run_devflow_prepromotion_tests.py"
)
DEVFLOW_PREPROMOTION_RUNNER = "dev/scripts/run_devflow_prepromotion_tests.py"


def record_release_verification(
    repo: Path,
    target: str,
    change: str,
    *,
    development_command: str,
    development_result: str,
    openspec_command: str,
    openspec_result: str,
    diff_command: str,
    diff_result: str,
) -> dict[str, Any]:
    repo = Path(repo).resolve()
    validate_target(target)
    snapshot = release_source_snapshot(repo, target)
    checks = {
        "development": check_record(development_command, development_result),
        "openspec": check_record(openspec_command, openspec_result),
        "diff": check_record(diff_command, diff_result),
    }
    command_errors = validate_release_commands(target, checks)
    if not snapshot["ready"] or command_errors:
        return {
            "ok": False,
            "status": "source_or_verification_incomplete",
            "source": snapshot,
            "errors": command_errors,
        }
    receipt = {
        "schemaVersion": SCHEMA_VERSION,
        "target": target,
        "change": change,
        "sourceSha256": snapshot["sha256"],
        "sourceFiles": snapshot["files"],
        "checks": checks,
        "recordedAt": datetime.now(timezone.utc).isoformat(),
    }
    path = release_verification_path(repo, target)
    atomic_write_devflow(repo, path, json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return {
        "ok": True,
        "status": "recorded",
        "path": path.relative_to(repo).as_posix(),
        "sourceSha256": snapshot["sha256"],
    }


def verify_release_verification(repo: Path, target: str, change: str) -> dict[str, Any]:
    repo = Path(repo).resolve()
    validate_target(target)
    path = release_verification_path(repo, target)
    if not trusted_repo_regular_file(repo, path):
        return verification_report(False, "missing_or_untrusted_evidence", path)
    try:
        receipt = json.loads(path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError):
        return verification_report(False, "invalid_evidence", path)
    if not isinstance(receipt, dict) or receipt.get("schemaVersion") != SCHEMA_VERSION:
        return verification_report(False, "invalid_evidence", path)
    if receipt.get("target") != target or receipt.get("change") != change:
        return verification_report(False, "change_or_target_mismatch", path)
    checks = receipt.get("checks")
    if not isinstance(checks, dict):
        return verification_report(False, "invalid_evidence", path)
    errors = validate_release_commands(target, checks)
    if errors:
        return verification_report(False, "incomplete_verification", path, errors=errors)
    snapshot = release_source_snapshot(repo, target)
    if not snapshot["ready"]:
        return verification_report(False, "untrusted_source", path, source=snapshot)
    if receipt.get("sourceSha256") != snapshot["sha256"]:
        return verification_report(False, "stale_evidence", path)
    if receipt.get("sourceFiles") != snapshot["files"]:
        return verification_report(False, "stale_evidence", path)
    return verification_report(
        True,
        "ready",
        path,
        sourceSha256=snapshot["sha256"],
    )


def release_promotion_readiness(
    repo: Path,
    target: str,
    *,
    require_authorization: bool,
) -> dict[str, Any]:
    repo = Path(repo).resolve()
    resolution = resolve_state(repo)
    state = resolution.get("data", {})
    gates = state.get("gates", {}) if isinstance(state.get("gates"), dict) else {}
    change = state.get("current_change", {})
    change_id = str(change.get("id") or "") if isinstance(change, dict) else ""
    change_status = str(change.get("status") or "") if isinstance(change, dict) else ""
    blockers: list[str] = []
    if resolution.get("status") != "namespaced":
        blockers.append("trusted_namespaced_state")
    blockers.extend(key for key in REQUIRED_STATE_GATES if not bool(gates.get(key)))
    if not change_id or change_id == "none":
        blockers.append("current_change")
    if change_status != "verified":
        blockers.append("current_change_verified")
    evidence = (
        verify_release_verification(repo, target, change_id)
        if change_id and change_id != "none"
        else {"ready": False, "status": "missing_change"}
    )
    if not evidence.get("ready"):
        blockers.append("fresh_complete_release_verification")
    if require_authorization and not bool(gates.get("release_allowed")):
        blockers.append("durable_release_authorization")
    return {
        "ready": not blockers,
        "target": target,
        "change": change_id or None,
        "stateStatus": resolution.get("status"),
        "stateGates": gates,
        "evidence": evidence,
        "blockers": sorted(set(blockers)),
        "durableReleaseAuthorization": bool(gates.get("release_allowed")),
    }


def release_source_snapshot(repo: Path, target: str) -> dict[str, Any]:
    repo = Path(repo).resolve()
    validate_target(target)
    roots = [repo / "dev" / "plugins" / target, repo / "dev" / "skills" / target]
    source_root = next((root for root in roots if root.exists() or root.is_symlink()), roots[0])
    if source_root.is_symlink() or not source_root.is_dir():
        return {"ready": False, "status": "missing_or_untrusted_source", "files": []}
    if not path_components_are_local(repo, source_root):
        return {"ready": False, "status": "missing_or_untrusted_source", "files": []}
    files: dict[str, str] = {}
    untrusted: list[str] = []
    for path in sorted(source_root.rglob("*")):
        relative = path.relative_to(repo).as_posix()
        if path.is_symlink() or not path_components_are_local(repo, path):
            untrusted.append(relative)
            continue
        if path.is_dir():
            continue
        if not path.is_file():
            untrusted.append(relative)
            continue
        local = path.relative_to(source_root)
        if any(part in IGNORED_PARTS for part in local.parts):
            continue
        if path.suffix in IGNORED_SUFFIXES or path.name == ".DS_Store":
            continue
        files[relative] = file_sha256(path)
    helpers, helper_errors = release_build_helpers(repo, source_root, target)
    untrusted.extend(helper_errors)
    for helper in helpers:
        if not trusted_repo_regular_file(repo, helper):
            untrusted.append(repo_relative_or_absolute(repo, helper))
            continue
        files[helper.relative_to(repo).as_posix()] = file_sha256(helper)
    canonical = "\n".join(f"{path}\0{digest}" for path, digest in sorted(files.items()))
    ready = bool(files) and not untrusted
    return {
        "ready": ready,
        "status": "ready" if ready else "untrusted_source",
        "sha256": hashlib.sha256(canonical.encode()).hexdigest() if ready else None,
        "files": [{"path": path, "sha256": digest} for path, digest in sorted(files.items())],
        "untrustedPaths": sorted(set(untrusted)),
    }


def release_build_helpers(
    repo: Path,
    source_root: Path,
    target: str,
) -> tuple[list[Path], list[str]]:
    metadata = source_root / ".codex-plugin" / "release-sync.json"
    required = target == "dev-flow"
    if not (metadata.exists() or metadata.is_symlink()):
        missing = [repo_relative_or_absolute(repo, metadata)] if required else []
        return [], missing
    if not trusted_repo_regular_file(repo, metadata):
        return [], [repo_relative_or_absolute(repo, metadata)]
    try:
        document = json.loads(metadata.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return [], [repo_relative_or_absolute(repo, metadata)]
    if not isinstance(document, dict) or not isinstance(document.get("buildCommands", []), list):
        return [], [repo_relative_or_absolute(repo, metadata)]
    helpers: list[Path] = []
    for command in document.get("buildCommands", []):
        if not isinstance(command, list):
            continue
        for token in command:
            if not isinstance(token, str) or not token.startswith("dev/"):
                continue
            # Include declared repository-local helpers even when they are
            # missing. The caller's trusted-file check then makes an absent
            # build dependency a release-source blocker instead of silently
            # omitting it from the source snapshot.
            helpers.append(repo / token)
    if required:
        helpers.append(repo / DEVFLOW_PREPROMOTION_RUNNER)
    return sorted(set(helpers)), []


def validate_release_commands(target: str, checks: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = {"development", "openspec", "diff"}
    if set(checks) != expected:
        errors.append("release verification must contain development, openspec, and diff checks")
        return errors
    for name in sorted(expected):
        record = checks.get(name)
        if not isinstance(record, dict) or record.get("result") != "pass":
            errors.append(f"{name} verification did not pass")
            continue
        command = str(record.get("command") or "")
        normalized = " ".join(command.lower().split())
        if name == "development" and not complete_development_command(normalized, target):
            errors.append("development verification is not the canonical complete test command")
        elif name == "openspec" and not all(
            marker in normalized for marker in ("openspec", "validate", "--all", "--strict")
        ):
            errors.append("OpenSpec verification must be strict and repository-wide")
        elif name == "diff" and "git diff --check" not in normalized:
            errors.append("diff verification must run git diff --check")
    return errors


def complete_development_command(command: str, target: str) -> bool:
    if target == "dev-flow":
        return command == DEVFLOW_PREPROMOTION_COMMAND
    return command == (
        "pythondontwritebytecode=1 python3.12 -m unittest discover "
        f"-s dev/plugins/{target}/tests -p 'test_*.py'"
    )


def repo_relative_or_absolute(repo: Path, path: Path) -> str:
    try:
        return path.relative_to(repo).as_posix()
    except ValueError:
        return str(path)


def check_record(command: str, result: str) -> dict[str, str]:
    return {"command": command.strip(), "result": result.strip().lower()}


def release_verification_path(repo: Path, target: str) -> Path:
    validate_target(target)
    return release_verification_root(repo) / f"{target}.json"


def validate_target(target: str) -> None:
    if not TARGET_ID.fullmatch(str(target)):
        raise ValueError(f"invalid release target: {target!r}")


def path_components_are_local(repo: Path, path: Path) -> bool:
    repo = Path(repo).resolve()
    candidate = Path(path).absolute()
    try:
        relative = candidate.relative_to(repo)
    except ValueError:
        return False
    current = repo
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return False
    return True


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verification_report(ready: bool, status: str, path: Path, **extra: Any) -> dict[str, Any]:
    return {"ready": ready, "status": status, "path": str(path), **extra}
