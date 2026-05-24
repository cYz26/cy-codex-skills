#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from workflow_compact import validate_checkpoint
from workflow_lib import repo_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate that a checkpoint is safe to compact from.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = validate_checkpoint(repo_path(args.repo), args.checkpoint)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
