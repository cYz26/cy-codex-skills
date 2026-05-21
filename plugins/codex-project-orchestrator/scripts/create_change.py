#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from workflow_lib import create_change, repo_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an OpenSpec change skeleton.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--change-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--type", required=True, dest="change_type")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = create_change(
        repo_path(args.repo),
        change_id=args.change_id,
        title=args.title,
        change_type=args.change_type,
        dry_run=args.dry_run,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
