#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from workflow_lib import repo_path, validate_workflow_state


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Codex workflow state consistency.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = validate_workflow_state(repo_path(args.repo))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
