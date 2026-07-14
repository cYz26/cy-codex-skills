#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from workflow_agent_task_contract import (
    validate_agent_task_contract_file,
    validate_agent_task_contract_files,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate one or more DevFlow Agent Task Contract markdown files.")
    parser.add_argument(
        "--contract",
        action="append",
        required=True,
        help="Path to AGENT_TASK_CONTRACT.md; repeat to validate disjoint worker write scopes.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args()

    contract_paths = [Path(value) for value in args.contract]
    report = (
        validate_agent_task_contract_file(contract_paths[0])
        if len(contract_paths) == 1
        else validate_agent_task_contract_files(contract_paths)
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("ok" if report["ok"] else "; ".join(report["errors"]))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
