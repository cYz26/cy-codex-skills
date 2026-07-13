#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from workflow_lib import record_verification, repo_path
from workflow_verification import record_gsd_verification


def main() -> int:
    parser = argparse.ArgumentParser(description="Record workflow verification evidence.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--command")
    parser.add_argument("--result", choices=["pass", "fail"])
    parser.add_argument("--notes", default="")
    parser.add_argument("--gsd-change")
    parser.add_argument("--gsd-phase")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if bool(args.gsd_change) != bool(args.gsd_phase):
        parser.error("--gsd-change and --gsd-phase must be provided together")
    if args.gsd_change:
        report = record_gsd_verification(
            repo_path(args.repo),
            change=args.gsd_change,
            phase=args.gsd_phase,
            command=args.command,
            result=args.result,
            notes=args.notes,
        )
    else:
        if not args.command or not args.result:
            parser.error("--command and --result are required for generic verification")
        report = record_verification(repo_path(args.repo), command=args.command, result=args.result, notes=args.notes)
    print(json.dumps(report, indent=2))
    return 0 if report.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
