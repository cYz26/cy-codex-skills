#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from workflow_context_health import context_health_check, record_context_health_event
from workflow_hooks import hook_response
from workflow_paths import repo_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Record DevFlow context-health hook metadata.")
    parser.add_argument("--event", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}
    repo = repo_path(payload.get("cwd") or Path.cwd())
    record_context_health_event(repo, args.event, payload)
    if args.check or args.event.lower() == "stop":
        report = context_health_check(repo)
        if report["risk"] in {"medium", "high", "critical"}:
            return hook_response(
                repo,
                f"DevFlow: context health is {report['risk']} ({report['decision']}). "
                "Run context-health-check before continuing.",
                event_name="Stop" if args.event.lower() == "stop" else "PreToolUse",
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
