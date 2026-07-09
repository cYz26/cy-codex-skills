#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from workflow_compact_state import SUPPORTED_COMPACT_STATUSES, supported_compact_statuses_text
from workflow_lib import hook_response, parse_state, repo_path


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}
    repo = repo_path(payload.get("cwd") or Path.cwd())
    state = parse_state(repo)
    context = state.get("context_management", {})
    status = context.get("compact_status")
    if status not in SUPPORTED_COMPACT_STATUSES:
        return hook_response(
            repo,
            f"DevFlow: unsupported compact_status `{status}`. "
            f"Regenerate workflow state or set one of: {supported_compact_statuses_text()}.",
            event_name="Stop",
        )
    if status == "pending":
        return 0
    if status == "skipped" and context.get("compact_skip_reason") in (None, "", "none"):
        return hook_response(
            repo,
            "DevFlow: compact was skipped without a recorded reason.",
            event_name="Stop",
        )
    if status in {"failed", "blocked"}:
        return hook_response(
            repo,
            "DevFlow: compact gate did not complete cleanly.",
            event_name="Stop",
        )
    if needs_checkpoint(state, context):
        return hook_response(
            repo,
            "DevFlow: major boundary reached without checkpoint. "
            "Run checkpoint-compact before ending this stage.",
            event_name="Stop",
        )
    return 0


def needs_checkpoint(state: dict, context: dict) -> bool:
    gates = state.get("gates", {})
    stage = state.get("current_stage")
    boundary_reached = bool(gates.get("verification_passed")) or stage == "phase_shipped"
    return boundary_reached and context.get("last_checkpoint_id") in (None, "", "none")


if __name__ == "__main__":
    raise SystemExit(main())
