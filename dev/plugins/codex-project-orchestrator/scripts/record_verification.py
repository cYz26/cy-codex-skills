#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from workflow_lib import record_verification, repo_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Record workflow verification evidence.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--command", required=True)
    parser.add_argument("--result", choices=["pass", "fail"], required=True)
    parser.add_argument("--notes", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = record_verification(repo_path(args.repo), command=args.command, result=args.result, notes=args.notes)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
