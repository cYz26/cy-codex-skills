from __future__ import annotations

from pathlib import Path
from typing import Any

from workflow_context_health_events import read_events, record_event
from workflow_context_health_runtime import context_health_check
from workflow_context_health_sessions import context_health_history, import_codex_sessions
from workflow_paths import repo_path


def record_context_health_event(
    repo: Path,
    event_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return record_event(repo_path(repo), event_type, payload)


def read_context_health_events(
    repo: Path,
    imported: bool = False,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    return read_events(repo_path(repo), imported=imported, limit=limit)


__all__ = [
    "context_health_check",
    "context_health_history",
    "import_codex_sessions",
    "read_context_health_events",
    "record_context_health_event",
]
