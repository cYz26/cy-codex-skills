#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from workflow_compact import record_compact_result
from workflow_lib import repo_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Record compact completion, skip, failure, or block status for a checkpoint."
    )
    parser.add_argument("--repo", required=True)
    parser.add_argument("--checkpoint")
    parser.add_argument("--checkpoint-id")
    parser.add_argument("--status", required=True, choices=["completed", "skipped", "failed", "blocked"])
    parser.add_argument("--source", default="manual", choices=["manual", "cli", "responses_api", "harness"])
    parser.add_argument("--raw-result")
    parser.add_argument("--result-file")
    parser.add_argument("--skip-reason")
    parser.add_argument("--error")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = record_compact_result(repo_path(args.repo), vars(args))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
