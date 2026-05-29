#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from workflow_agent_kb import record_agent_kb_event


def main() -> int:
    parser = argparse.ArgumentParser(description="Record sanitized AgentKB hook metadata.")
    parser.add_argument("--event", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}
    repo = payload.get("cwd") or Path.cwd()
    report = record_agent_kb_event(repo, args.event, payload)
    if args.json:
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
