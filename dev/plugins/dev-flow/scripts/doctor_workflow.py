#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from workflow_lib import doctor_workflow, repo_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose Codex workflow drift.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = doctor_workflow(repo_path(args.repo), write_report=args.write_report)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
