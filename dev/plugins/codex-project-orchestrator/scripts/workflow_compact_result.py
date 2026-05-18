from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from workflow_compact_options import clean_text, option_issues
from workflow_compact_resolve import raw_compact_result, resolve_checkpoint
from workflow_paths import rel, repo_path, write_json
from workflow_state import update_state


def record_compact_result(repo: Path, options: dict[str, Any]) -> dict[str, Any]:
    repo = repo_path(repo)
    status = str(options.get("status", "")).strip()
    source = str(options.get("source") or "manual").strip()
    recorded_at = datetime.now().astimezone().isoformat(timespec="seconds")
    issues = option_issues(status, source, options)
    checkpoint = resolve_checkpoint(repo, options)
    issues.extend(checkpoint["issues"])
    raw_result = raw_compact_result(repo, options, issues)
    checkpoint_id = checkpoint["checkpoint_id"] or "unknown-checkpoint"
    result_file = repo / ".planning" / "compact-results" / f"{checkpoint_id}.json"
    report = compact_report(
        repo,
        checkpoint,
        result_file,
        status,
        source,
        recorded_at,
        issues,
        options,
    )
    if issues or options.get("dry_run"):
        return report
    write_compact_result(repo, result_file, checkpoint, status, source, recorded_at, raw_result, options)
    update_compact_state(repo, checkpoint, result_file, status, source, recorded_at, options)
    return report


def compact_report(
    repo: Path,
    checkpoint: dict[str, Any],
    result_file: Path,
    status: str,
    source: str,
    recorded_at: str,
    issues: list[str],
    options: dict[str, Any],
) -> dict[str, Any]:
    return {
        "ok": not issues,
        "dry_run": bool(options.get("dry_run")),
        "checkpoint_id": checkpoint["checkpoint_id"],
        "checkpoint_file": checkpoint["checkpoint_file"],
        "compact_status": status,
        "compact_source": source,
        "compact_result_file": rel(repo, result_file),
        "recorded_at": recorded_at,
        "issues": issues,
    }


def write_compact_result(
    repo: Path,
    result_file: Path,
    checkpoint: dict[str, Any],
    status: str,
    source: str,
    recorded_at: str,
    raw_result: str | None,
    options: dict[str, Any],
) -> None:
    write_json(
        result_file,
        {
            "checkpoint_id": checkpoint["checkpoint_id"],
            "checkpoint_file": checkpoint["checkpoint_file"],
            "status": status,
            "source": source,
            "recorded_at": recorded_at,
            "raw_result": raw_result,
            "skip_reason": clean_text(options.get("skip_reason")) or "none",
            "error": clean_text(options.get("error")) or "none",
        },
    )


def update_compact_state(
    repo: Path,
    checkpoint: dict[str, Any],
    result_file: Path,
    status: str,
    source: str,
    recorded_at: str,
    options: dict[str, Any],
) -> None:
    update_state(
        repo,
        last_checkpoint_id=checkpoint["checkpoint_id"],
        last_checkpoint_file=checkpoint["checkpoint_file"],
        compact_recommended=status in {"failed", "blocked"},
        compact_status=status,
        last_compact_result_file=rel(repo, result_file),
        compact_source=source,
        compact_updated_at=recorded_at,
        compact_skip_reason=clean_text(options.get("skip_reason")) or "none",
        compact_error=clean_text(options.get("error")) or "none",
    )
