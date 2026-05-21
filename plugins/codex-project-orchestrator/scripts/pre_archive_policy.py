#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from workflow_lib import hook_response, parse_state, repo_path


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}
    repo = repo_path(payload.get("cwd") or Path.cwd())
    command = " ".join(str(value) for value in (payload.get("tool_input") or {}).values())
    if "archive" not in command and "openspec/changes" not in command:
        return 0
    gates = parse_state(repo).get("gates", {})
    if not gates.get("archive_allowed", False):
        return hook_response(
            repo,
            "codex-project-orchestrator: archive gate is closed. Record verification and update state first.",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
