#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from workflow_lib import hook_response, parse_state, repo_path
from workflow_archive_policy import archive_change_from_command, archive_status, mutating_archive_command


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}
    repo = repo_path(payload.get("cwd") or Path.cwd())
    command = command_from_payload(payload)
    if not mutating_archive_command(command):
        return 0
    gates = parse_state(repo).get("gates", {})
    change = archive_change_from_command(command) or parse_state(repo).get("current_change", {}).get("id")
    report = archive_status(
        repo,
        change,
        explicit_request=True,
        allow_risk=bool(gates.get("archive_allowed", False)),
    )
    if not report["canArchive"]:
        return hook_response(
            repo,
            "DevFlow: archive confirmation or risk resolution is required before mutating archive state.",
            diagnostic={"archiveStatus": report},
            force_block=True,
        )
    return 0


def command_from_payload(payload: dict) -> str:
    tool_input = payload.get("tool_input") or {}
    if isinstance(tool_input, dict) and "command" in tool_input:
        return str(tool_input.get("command") or "")
    if isinstance(tool_input, dict):
        return " ".join(str(value) for value in tool_input.values())
    return str(tool_input or "")


if __name__ == "__main__":
    raise SystemExit(main())
