#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from workflow_spec_sync_evidence import record_spec_sync


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Record hash-bound evidence after openspec-sync-specs completes."
    )
    parser.add_argument("--repo", default=".")
    parser.add_argument("--change", required=True)
    parser.add_argument("--command", required=True)
    parser.add_argument("--result", choices=["pass", "fail"], required=True)
    parser.add_argument("--notes", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = record_spec_sync(
        Path(args.repo),
        args.change,
        command=args.command,
        result=args.result,
        notes=args.notes,
    )
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else report["status"])
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
