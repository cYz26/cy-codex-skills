#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from workflow_lib import detect_project_mode, repo_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect greenfield or brownfield project mode.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = detect_project_mode(repo_path(args.repo))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
