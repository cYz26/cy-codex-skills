#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from workflow_implementation_readiness import repository_mutation_gate
from workflow_lib import hook_response, parse_state, production_like_path, repo_path


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}
    repo = repo_path(payload.get("cwd") or Path.cwd())
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("path")
    if not production_like_path(repo, file_path):
        return 0
    state = parse_state(repo)
    stage = state.get("current_stage", "setup")
    gates = state.get("gates", {})
    if stage != "executing" or not gates.get("spec_approved", False):
        return hook_response(
            repo,
            "DevFlow: production edit before approved execution state. "
            "Use project-orchestrator / feature-intake / change-plan first.",
        )
    readiness = repository_mutation_gate(repo, ordinary_authority=True)
    if readiness["applicable"] and not readiness["allowed"]:
        codes = ", ".join(readiness["issueCodes"]) or "unknown"
        return hook_response(
            repo,
            "DevFlow: implementation readiness blocks this production edit "
            f"({codes}). Next action: {readiness['nextAction']}.",
            diagnostic={"implementationReadiness": readiness},
            force_block=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
