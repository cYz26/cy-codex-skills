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
    context = parse_state(repo).get("context_management", {})
    status = context.get("compact_status")
    if status == "pending":
        return hook_response(
            repo,
            "DevFlow: compact_status is pending. "
            "Run /compact or record a skip reason before entering the next phase.",
        )
    if status == "skipped" and context.get("compact_skip_reason") in (None, "", "none"):
        return hook_response(
            repo,
            "DevFlow: compact_status is skipped without a skip reason. "
            "Record one with record_compact_result.py before entering the next phase.",
        )
    if status in {"failed", "blocked"}:
        return hook_response(
            repo,
            f"DevFlow: compact gate is {status}. "
            "Record a completed compact result or an explicit skip reason before continuing.",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
