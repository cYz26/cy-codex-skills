#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from workflow_lib import inspect_repo, repo_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a brownfield codebase map.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--output")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    output = Path(args.output).expanduser().resolve() if args.output else None
    report = inspect_repo(repo_path(args.repo), output=output, dry_run=args.dry_run)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
