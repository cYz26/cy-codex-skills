#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from workflow_contract_control_plane import validate_goal_contract


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DevFlow Goal Contract in TASK_LEDGER.md.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = validate_goal_contract(Path(args.repo))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("ok" if report["ok"] else "; ".join(report["errors"]))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
