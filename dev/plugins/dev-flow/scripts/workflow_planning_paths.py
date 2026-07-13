from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

from workflow_constants import resolve_plugin_root


LEGACY_STATE_SUNSET_RELEASE = "1.0.0"


class PlanningOwnershipError(RuntimeError):
    def __init__(self, code: str, path: Path, message: str):
        super().__init__(message)
        self.code = code
        self.path = path


def planning_root(repo: Path) -> Path:
    return Path(repo).resolve() / ".planning"


def devflow_root(repo: Path) -> Path:
    return planning_root(repo) / "devflow"


def state_path(repo: Path) -> Path:
    return devflow_root(repo) / "STATE.md"


def legacy_state_path(repo: Path) -> Path:
    return planning_root(repo) / "STATE.md"


def verification_root(repo: Path) -> Path:
    return devflow_root(repo) / "verification"


def checkpoint_root(repo: Path) -> Path:
    return devflow_root(repo) / "checkpoints"


def compact_result_root(repo: Path) -> Path:
    return devflow_root(repo) / "compact-results"


def context_health_root(repo: Path) -> Path:
    return devflow_root(repo) / "context-health"


def codebase_root(repo: Path) -> Path:
    return devflow_root(repo) / "codebase"


def provider_migration_root(repo: Path) -> Path:
    return devflow_root(repo) / "provider-migration"


def delegation_root(repo: Path) -> Path:
    return devflow_root(repo) / "claude-code"


def plugin_migration_root(repo: Path) -> Path:
    return devflow_root(repo) / "plugin-project-migration"


def guard_devflow_write(repo: Path, path: Path) -> bool:
    repo = Path(repo).resolve()
    candidate = Path(path).resolve()
    root = devflow_root(repo)
    try:
        relative = candidate.relative_to(repo)
    except ValueError as error:
        raise PlanningOwnershipError("outside_repo", candidate, "DevFlow write is outside the repository") from error
    expected_prefix = (".planning", "devflow")
    if tuple(relative.parts[:2]) != expected_prefix:
        raise PlanningOwnershipError(
            "owner_mismatch",
            candidate,
            "DevFlow may write only under .planning/devflow/**",
        )
    if candidate == root:
        raise PlanningOwnershipError("invalid_target", candidate, "DevFlow write target must be a file or child path")
    return True


def atomic_write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f"{path.name}-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_write_devflow(repo: Path, path: Path, text: str) -> None:
    guard_devflow_write(repo, path)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    guard_devflow_write(repo, path)
    atomic_write_text(path, text)


def append_devflow_text(repo: Path, path: Path, text: str) -> None:
    path = Path(path)
    guard_devflow_write(repo, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    guard_devflow_write(repo, path)
    flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        os.write(descriptor, text.encode())
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def current_plugin_version(plugin_root: Path | None = None) -> str:
    root = Path(plugin_root).resolve() if plugin_root else resolve_plugin_root(__file__)
    manifest = root / ".codex-plugin" / "plugin.json"
    try:
        version = str(json.loads(manifest.read_text()).get("version") or "0")
    except (OSError, json.JSONDecodeError):
        return "0.0.0"
    return version


def version_at_or_after(value: str, minimum: str) -> bool:
    return version_tuple(value) >= version_tuple(minimum)


def version_tuple(value: str) -> tuple[int, int, int]:
    core = re.split(r"[+-]", value.strip().lstrip("v"), maxsplit=1)[0]
    values = []
    for part in core.split("."):
        match = re.match(r"(\d+)", part)
        values.append(int(match.group(1)) if match else 0)
        if len(values) == 3:
            break
    while len(values) < 3:
        values.append(0)
    return tuple(values[:3])  # type: ignore[return-value]
