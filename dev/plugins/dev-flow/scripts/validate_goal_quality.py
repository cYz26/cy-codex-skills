#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from workflow_goal_quality import goal_quality_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DevFlow candidate goal objective quality.")
    parser.add_argument("--objective", required=True, help="Candidate goal objective text.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args()

    report = goal_quality_report(args.objective)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("ok" if report["ok"] else "; ".join(report["errors"]))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
