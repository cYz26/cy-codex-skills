#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from workflow_agent_task_contract import validate_agent_task_contract_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a DevFlow Agent Task Contract markdown file.")
    parser.add_argument("--contract", required=True, help="Path to AGENT_TASK_CONTRACT.md.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args()

    report = validate_agent_task_contract_file(Path(args.contract))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("ok" if report["ok"] else "; ".join(report["errors"]))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
