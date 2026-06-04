from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from agent_kb_config import discover_agent_kb_config
from agent_kb_constants import EVENT_DIR
from agent_kb_event_security import hash_text, normalize_event_type, now_iso, redact_command
from agent_kb_event_status import command_category, status_for
from agent_kb_problem_capture import record_problem_signal
from agent_kb_scaffold import sanitize_project
from agent_kb_value_extract import first_dict, first_int, first_text
from workflow_paths import rel, repo_path


def record_agent_kb_event(repo: Path, event_type: str, payload: dict[str, Any]):
    repo = repo_path(repo)
    config = discover_agent_kb_config(repo)
    if not config:
        return {"ok": True, "recorded": False, "reason": "not_configured"}

    vault = repo_path(config["vault"])
    project = sanitize_project(str(config.get("project") or "knowledge-base"))
    event = sanitize_event(repo, project, event_type, payload)
    path = event_file_path(vault)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{json.dumps(event, sort_keys=True)}\n")
    problem_signal = record_problem_signal(vault, project, config, event)
    return {
        "ok": True,
        "recorded": True,
        "path": rel(vault, path),
        "project": project,
        "event_type": event["event_type"],
        "problem_signal": problem_signal,
    }


def event_file_path(vault: Path):
    today = date.today().isoformat()
    return vault / EVENT_DIR / f"session-{today}.jsonl"


def sanitize_event(repo: Path, project: str, event_type: str, payload: dict[str, Any]):
    tool_input = first_dict(payload.get("tool_input"), payload.get("input"), payload.get("arguments"))
    tool_response = first_dict(payload.get("tool_response"), payload.get("tool_result"), payload.get("response"))
    command = first_text(tool_input.get("command"), tool_input.get("cmd"), payload.get("command"))
    output = first_text(
        tool_response.get("output"),
        tool_response.get("stdout"),
        tool_response.get("stderr"),
        payload.get("output"),
    )
    exit_code = first_int(tool_response.get("exit_code"), tool_response.get("returncode"), payload.get("exit_code"))
    event = sanitized_base_event(repo, project, event_type, payload, tool_response, exit_code)
    add_command_metadata(event, command)
    add_output_metadata(event, output)
    return {key: value for key, value in event.items() if value is not None}


def sanitized_base_event(
    repo: Path,
    project: str,
    event_type: str,
    payload: dict[str, Any],
    tool_response: dict[str, Any],
    exit_code: int | None,
):
    return {
        "schema": 1,
        "ts": first_text(payload.get("timestamp"), payload.get("ts")) or now_iso(),
        "event_type": normalize_event_type(event_type),
        "project": project,
        "cwd": first_text(payload.get("cwd")) or str(repo),
        "tool": first_text(payload.get("tool_name"), payload.get("tool")) or "unknown",
        "status": status_for(exit_code, tool_response, payload),
        "exit_code": exit_code,
    }


def add_command_metadata(event: dict[str, Any], command: str):
    if command:
        event["command_hash"] = hash_text(command)
        event["command_redacted"] = redact_command(command)
        event["command_category"] = command_category(command)


def add_output_metadata(event: dict[str, Any], output: str):
    if output:
        event["output_bytes"] = len(output.encode("utf-8"))
        event["output_lines"] = len(output.splitlines())
        event["output_hash"] = hash_text(output)
