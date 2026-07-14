#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from workflow_release_verification import record_release_verification


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Record source-bound pre-promotion verification evidence."
    )
    parser.add_argument("--repo", default=".")
    parser.add_argument("--target", required=True)
    parser.add_argument("--change", required=True)
    parser.add_argument("--development-command", required=True)
    parser.add_argument("--development-result", choices=["pass", "fail"], required=True)
    parser.add_argument("--openspec-command", required=True)
    parser.add_argument("--openspec-result", choices=["pass", "fail"], required=True)
    parser.add_argument("--diff-command", required=True)
    parser.add_argument("--diff-result", choices=["pass", "fail"], required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = record_release_verification(
        Path(args.repo),
        args.target,
        args.change,
        development_command=args.development_command,
        development_result=args.development_result,
        openspec_command=args.openspec_command,
        openspec_result=args.openspec_result,
        diff_command=args.diff_command,
        diff_result=args.diff_result,
    )
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else report["status"])
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
