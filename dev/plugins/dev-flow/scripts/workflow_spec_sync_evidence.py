from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from workflow_planning_paths import atomic_write_devflow, spec_sync_root


SCHEMA_VERSION = 1
CHANGE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def record_spec_sync(
    repo: Path,
    change: str,
    *,
    command: str,
    result: str,
    notes: str = "",
) -> dict[str, Any]:
    repo = Path(repo).resolve()
    validate_change_id(change)
    normalized_result = result.strip().lower()
    if normalized_result not in {"pass", "fail"}:
        raise ValueError("spec sync result must be pass or fail")
    snapshot = spec_snapshot(repo, change)
    ok = (
        normalized_result == "pass"
        and snapshot["ready"]
        and "openspec-sync-specs" in command
    )
    receipt = {
        "schemaVersion": SCHEMA_VERSION,
        "change": change,
        "result": normalized_result,
        "command": command.strip(),
        "recordedAt": datetime.now(timezone.utc).isoformat(),
        "specs": snapshot["specs"],
        "notes": notes,
    }
    path = spec_sync_receipt_path(repo, change)
    atomic_write_devflow(repo, path, json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return {
        "ok": ok,
        "status": "recorded" if ok else "failed_or_incomplete",
        "path": path.relative_to(repo).as_posix(),
        "missing": snapshot["missing"],
    }


def verify_spec_sync(repo: Path, change: str) -> dict[str, Any]:
    repo = Path(repo).resolve()
    validate_change_id(change)
    path = spec_sync_receipt_path(repo, change)
    if has_symlink_component(repo, path) or not path.is_file():
        return sync_report(False, "missing_evidence", path)
    try:
        receipt = json.loads(path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError):
        return sync_report(False, "invalid_evidence", path)
    if not isinstance(receipt, dict) or receipt.get("schemaVersion") != SCHEMA_VERSION:
        return sync_report(False, "invalid_evidence", path)
    if receipt.get("change") != change or receipt.get("result") != "pass":
        return sync_report(False, "failed_evidence", path)
    command = str(receipt.get("command") or "")
    if "openspec-sync-specs" not in command:
        return sync_report(False, "untrusted_command_evidence", path)
    current = spec_snapshot(repo, change)
    if not current["ready"]:
        return sync_report(False, "missing_spec_files", path, missing=current["missing"])
    if receipt.get("specs") != current["specs"]:
        return sync_report(False, "stale_evidence", path)
    return sync_report(True, "ready", path, specs=current["specs"])


def spec_snapshot(repo: Path, change: str) -> dict[str, Any]:
    delta_root = repo / "openspec" / "changes" / change / "specs"
    if has_symlink_component(repo, delta_root):
        return {
            "ready": False,
            "specs": [],
            "missing": [f"openspec/changes/{change}/specs (nonlocal)"],
        }
    delta_paths = sorted(delta_root.glob("*/spec.md")) if delta_root.is_dir() else []
    specs: list[dict[str, str]] = []
    missing: list[str] = []
    if not delta_paths:
        missing.append(f"openspec/changes/{change}/specs/*/spec.md")
    for delta in delta_paths:
        capability = delta.parent.name
        main = repo / "openspec" / "specs" / capability / "spec.md"
        if has_symlink_component(repo, delta) or not delta.is_file():
            missing.append(delta.relative_to(repo).as_posix())
            continue
        if has_symlink_component(repo, main) or not main.is_file():
            missing.append(main.relative_to(repo).as_posix())
            continue
        specs.append(
            {
                "capability": capability,
                "deltaPath": delta.relative_to(repo).as_posix(),
                "deltaSha256": file_sha256(delta),
                "mainPath": main.relative_to(repo).as_posix(),
                "mainSha256": file_sha256(main),
            }
        )
    return {"ready": not missing and bool(specs), "specs": specs, "missing": sorted(missing)}


def spec_sync_receipt_path(repo: Path, change: str) -> Path:
    validate_change_id(change)
    return spec_sync_root(repo) / f"{change}.json"


def validate_change_id(change: str) -> None:
    if not CHANGE_ID.fullmatch(str(change)):
        raise ValueError(f"invalid OpenSpec change id: {change!r}")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def has_symlink_component(repo: Path, path: Path) -> bool:
    repo = Path(repo).resolve()
    candidate = Path(path).absolute()
    try:
        relative = candidate.relative_to(repo)
    except ValueError:
        return True
    current = repo
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def sync_report(ready: bool, status: str, path: Path, **extra: Any) -> dict[str, Any]:
    return {
        "ready": ready,
        "status": status,
        "path": str(path),
        **extra,
    }
