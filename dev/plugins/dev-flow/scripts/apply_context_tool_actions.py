#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from workflow_context_tools import apply_context_tool_actions


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply selected context tool audit actions.")
    parser.add_argument("--plan", required=True, help="Saved JSON report from audit_context_tools.py.")
    parser.add_argument("--action", action="append", default=[], help="Action id to apply. Repeat as needed.")
    parser.add_argument(
        "--all-safe",
        action="store_true",
        help="Select every action marked safe in the report.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually change files. Without this flag the command is dry-run.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = json.loads(Path(args.plan).read_text())
    result = apply_context_tool_actions(report, args.action, args.all_safe, args.apply)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_text_result(result)
    return 0 if result["ok"] else 1


def print_text_result(result: dict) -> None:
    mode = "DRY RUN" if result["dryRun"] else "APPLY"
    print(f"Mode: {mode}")
    for item in result["applied"]:
        print(f"- {item['status']}: {item['id']}")
    for backup in result.get("backups", []):
        print(f"Backup: {backup}")
    for error in result["errors"]:
        print(f"ERROR: {error}")


if __name__ == "__main__":
    raise SystemExit(main())
