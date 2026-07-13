from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from workflow_paths import rel, repo_path
from workflow_planning_paths import append_devflow_text, context_health_root


EVENT_FILE = "events.jsonl"
IMPORTED_EVENT_FILE = "imported-events.jsonl"


def event_store_path(repo: Path, imported: bool = False) -> Path:
    filename = IMPORTED_EVENT_FILE if imported else EVENT_FILE
    return context_health_root(repo_path(repo)) / filename


def record_event(repo: Path, event_type: str, payload: dict[str, Any], imported: bool = False) -> dict[str, Any]:
    repo = repo_path(repo)
    event = sanitize_event(repo, event_type, payload)
    path = event_store_path(repo, imported=imported)
    append_devflow_text(repo, path, f"{json.dumps(event, sort_keys=True)}\n")
    return event


def read_events(repo: Path, imported: bool = False, limit: int | None = None) -> list[dict[str, Any]]:
    path = event_store_path(repo, imported=imported)
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    if limit is not None:
        lines = lines[-limit:]
    events: list[dict[str, Any]] = []
    for line in lines:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            events.append(item)
    return events


def sanitize_event(repo: Path, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    tool_input = first_dict(payload.get("tool_input"), payload.get("input"), payload.get("arguments"))
    tool_response = first_dict(payload.get("tool_response"), payload.get("tool_result"), payload.get("response"))
    command = first_text(
        tool_input.get("command"),
        tool_input.get("cmd"),
        payload.get("command"),
    )
    target_files = target_file_hints(repo, payload, tool_input, command)
    output_text = first_text(
        tool_response.get("output"),
        tool_response.get("stdout"),
        tool_response.get("stderr"),
        payload.get("output"),
    )
    exit_code = first_int(tool_response.get("exit_code"), tool_response.get("returncode"), payload.get("exit_code"))
    status = status_for(exit_code, tool_response, payload)
    event = {
        "schema": 1,
        "ts": first_text(payload.get("timestamp"), payload.get("ts")) or now_iso(),
        "event_type": normalize_event_type(event_type),
        "cwd": first_text(payload.get("cwd")) or str(repo),
        "tool": first_text(payload.get("tool_name"), payload.get("tool")) or "unknown",
        "status": status,
        "exit_code": exit_code,
        "duration_ms": first_int(tool_response.get("duration_ms"), payload.get("duration_ms")),
        "target_files": target_files,
        "checkpoint_id": first_text(payload.get("checkpoint_id")) or "unknown",
        "goal_id": first_text(payload.get("goal_id")) or "unknown",
        "subagent_id": first_text(payload.get("subagent_id")) or "unknown",
    }
    if command:
        event.update(
            {
                "command_hash": hash_text(command),
                "command_redacted": redact_command(command),
                "command_category": command_category(command),
            }
        )
    if output_text:
        event["output_bytes"] = len(output_text.encode("utf-8"))
        event["output_lines"] = len(output_text.splitlines())
        event["output_hash"] = hash_text(output_text)
    return {key: value for key, value in event.items() if value is not None}


def normalize_event_type(value: str) -> str:
    return value.strip().lower().replace("-", "_") or "event"


def first_dict(*values: Any) -> dict[str, Any]:
    for value in values:
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
    return {}


def first_text(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return ""


def first_int(*values: Any) -> int | None:
    for value in values:
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                continue
    return None


def status_for(exit_code: int | None, tool_response: dict[str, Any], payload: dict[str, Any]) -> str:
    explicit = first_text(tool_response.get("status"), payload.get("status"))
    if explicit:
        lowered = explicit.lower()
        if lowered in {"success", "ok", "passed", "pass"}:
            return "pass"
        if lowered in {"error", "failed", "fail"}:
            return "fail"
        return lowered
    if exit_code is None:
        return "unknown"
    return "pass" if exit_code == 0 else "fail"


def target_file_hints(repo: Path, payload: dict[str, Any], tool_input: dict[str, Any], command: str) -> list[str]:
    values = [
        tool_input.get("file_path"),
        tool_input.get("path"),
        payload.get("file_path"),
        payload.get("path"),
    ]
    targets = [repo_relative(repo, value) for value in values if isinstance(value, str) and value]
    if command:
        targets.extend(command_path_hints(repo, command))
    return sorted(set(target for target in targets if target))


def command_path_hints(repo: Path, command: str) -> list[str]:
    hints: list[str] = []
    for raw in re.findall(r"(?<![\w/.-])[\w./-]+\.(?:py|md|toml|json|yaml|yml|ts|tsx|js|jsx|css|html)", command):
        hints.append(repo_relative(repo, raw))
    return hints


def repo_relative(repo: Path, value: str) -> str:
    path = Path(value).expanduser()
    try:
        if path.is_absolute():
            return rel(repo, path.resolve())
    except Exception:
        return value
    return value


def hash_text(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def redact_command(command: str) -> str:
    command = re.sub(r"(?i)(api[_-]?key|token|password|secret)=\S+", r"\1=<redacted>", command)
    command = re.sub(r"(?i)(--(?:api[-_]?key|token|password|secret))\s+\S+", r"\1 <redacted>", command)
    return command.strip()[:240]


def command_category(command: str) -> str:
    lowered = command.lower()
    if any(token in lowered for token in ("pytest", "unittest", "npm test", "pnpm test", "yarn test", "cargo test")):
        return "test"
    if any(token in lowered for token in ("lint", "ruff", "eslint", "mypy", "tsc")):
        return "lint"
    if any(token in lowered for token in ("build", "webpack", "vite build", "cargo build")):
        return "build"
    if lowered.strip().startswith("git "):
        return "git"
    if any(token in lowered for token in ("rg ", "grep ", "find ", "ls ", "sed ", "cat ", "nl ")):
        return "read"
    return "command"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
