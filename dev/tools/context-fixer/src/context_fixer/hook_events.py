from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .session import Contributor
from .util import approx_tokens


@dataclass
class HookEventStats:
    path: Path
    events: int = 0
    malformed_records: int = 0
    external_records: int = 0
    skipped_external_records: int = 0
    contributors: list[Contributor] = field(default_factory=list)
    activity_events: list[dict[str, Any]] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "events": self.events,
            "malformed_records": self.malformed_records,
            "external_records": self.external_records,
            "skipped_external_records": self.skipped_external_records,
            "findings": list(self.findings),
        }


def parse_hook_events(path: Path, repo: Path | None = None, include_external: bool = False) -> HookEventStats:
    stats = HookEventStats(path=path)
    repo_path = repo.expanduser().resolve() if repo else None
    if not path.exists():
        stats.findings.append({"level": "warning", "message": f"Hook event file not found: {path}"})
        return stats

    with path.open(encoding="utf-8", errors="ignore") as handle:
        for order, line in enumerate(handle, start=1):
            record = parse_record(line)
            if record is None:
                stats.malformed_records += 1
                continue
            if is_external_record(record.get("cwd"), repo_path):
                stats.external_records += 1
                if not include_external:
                    stats.skipped_external_records += 1
                    continue
            add_record(stats, record, order)

    if stats.malformed_records:
        stats.findings.append(
            {
                "level": "warning",
                "message": f"Skipped {stats.malformed_records} malformed hook event record(s).",
            }
        )
    if stats.skipped_external_records:
        stats.findings.append(
            {
                "level": "info",
                "message": f"Skipped {stats.skipped_external_records} hook event record(s) outside the audited repository.",
            }
        )
    return stats


def parse_record(line: str) -> dict[str, Any] | None:
    try:
        value = json.loads(line)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def is_external_record(cwd: object, repo: Path | None) -> bool:
    if repo is None or not cwd:
        return False
    try:
        cwd_path = Path(str(cwd)).expanduser().resolve()
    except OSError:
        return True
    return cwd_path != repo and not cwd_path.is_relative_to(repo)


def add_record(stats: HookEventStats, record: dict[str, Any], order: int) -> None:
    stats.events += 1
    tool_name = str(record.get("tool_name") or "unknown")
    event_type = str(record.get("event_type") or "hook")
    timestamp = str(record.get("recorded_at") or record.get("timestamp") or "") or None
    status = record.get("status")
    input_tokens = token_count(record, "tool_input_estimated_tokens", "tool_input_bytes")
    output_tokens = token_count(record, "tool_response_estimated_tokens", "tool_response_bytes")
    input_bytes = int_value(record.get("tool_input_bytes")) or input_tokens * 4
    output_bytes = int_value(record.get("tool_response_bytes")) or output_tokens * 4

    if input_tokens:
        stats.contributors.append(
            Contributor(
                f"hook tool input: {tool_name}",
                "hook_tool_input",
                "runtime",
                input_tokens,
                input_bytes,
                "sanitized",
                path=str(stats.path),
                note="hook input body omitted",
                source_category="hook_tool_input",
            )
        )
        stats.activity_events.append(
            activity_event(stats.path, order, tool_name, event_type, "tool_call", timestamp, status, input_tokens, 0)
        )
    if output_tokens:
        stats.contributors.append(
            Contributor(
                f"hook tool output: {tool_name}",
                "hook_tool_output",
                "runtime",
                output_tokens,
                output_bytes,
                "sanitized",
                path=str(stats.path),
                note="hook output body omitted",
                source_category="hook_tool_output",
            )
        )
        stats.activity_events.append(
            activity_event(stats.path, order, tool_name, event_type, "tool_result", timestamp, status, 0, output_tokens)
        )


def activity_event(
    path: Path,
    order: int,
    tool_name: str,
    event_type: str,
    kind: str,
    timestamp: str | None,
    status: object,
    input_tokens: int,
    output_tokens: int,
) -> dict[str, Any]:
    return {
        "source": "hook_events",
        "kind": kind,
        "timestamp": timestamp,
        "path": str(path),
        "order": order,
        "name": tool_name,
        "call_type": event_type,
        "argument_estimated_tokens": input_tokens,
        "output_estimated_tokens": output_tokens,
        "status": status,
    }


def token_count(record: dict[str, Any], token_key: str, byte_key: str) -> int:
    explicit = int_value(record.get(token_key))
    if explicit:
        return explicit
    return approx_tokens(int_value(record.get(byte_key)))


def int_value(value: object) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0
