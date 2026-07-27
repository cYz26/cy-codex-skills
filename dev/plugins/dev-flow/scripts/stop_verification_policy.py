#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from workflow_generated_artifacts import inspect_generated_artifact_lifecycle
from workflow_lib import hook_response, parse_state, repo_path


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}
    repo = repo_path(payload.get("cwd") or Path.cwd())
    state = parse_state(repo)
    if not state:
        return 0
    generated_artifacts = inspect_generated_artifact_lifecycle(repo)
    if not generated_artifacts["ok"]:
        next_actions = "; ".join(generated_artifacts["nextActions"])
        return hook_response(
            repo,
            "DevFlow: Generated Artifact Lifecycle is unresolved. "
            f"{next_actions}",
            event_name="Stop",
        )
    gates = state.get("gates", {})
    if not gates.get("verification_passed", False):
        return hook_response(
            repo,
            "DevFlow: verification has not been recorded. "
            "Run relevant checks and record evidence before claiming completion.",
            event_name="Stop",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
