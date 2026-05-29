#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from workflow_context_health import context_health_history
from workflow_paths import repo_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize DevFlow context-health history.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = context_health_history(repo_path(args.repo))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"event_count: {report['event_count']}")
        print(f"coverage: {report['coverage']}")
        print(f"confidence: {report['confidence']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
