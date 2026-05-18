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
    state = parse_state(repo)
    context = state.get("context_management", {})
    if context.get("compact_status") == "pending":
        return hook_response(
            repo,
            "codex-project-orchestrator: checkpoint is pending compact. "
            "Run /compact before continuing to the next major stage.",
        )
    if context.get("compact_status") == "skipped" and context.get("compact_skip_reason") in (None, "", "none"):
        return hook_response(
            repo,
            "codex-project-orchestrator: compact was skipped without a recorded reason.",
        )
    if context.get("compact_status") in {"failed", "blocked"}:
        return hook_response(
            repo,
            "codex-project-orchestrator: compact gate did not complete cleanly.",
        )
    if needs_checkpoint(state, context):
        return hook_response(
            repo,
            "codex-project-orchestrator: major boundary reached without checkpoint. "
            "Run checkpoint-compact before ending this stage.",
        )
    return 0


def needs_checkpoint(state: dict, context: dict) -> bool:
    gates = state.get("gates", {})
    stage = state.get("current_stage")
    boundary_reached = bool(gates.get("verification_passed")) or stage == "phase_shipped"
    return boundary_reached and context.get("last_checkpoint_id") in (None, "", "none")


if __name__ == "__main__":
    raise SystemExit(main())
