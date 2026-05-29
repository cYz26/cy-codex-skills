#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from workflow_context_health import context_health_check
from workflow_paths import repo_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze DevFlow context health.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--current-objective")
    parser.add_argument("--context-usage-pct", type=float)
    parser.add_argument("--expected-diff-files", type=int, default=6)
    parser.add_argument("--validation-command", action="append", default=[])
    parser.add_argument("--goal-summary")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--update-state", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    options = {
        "current_objective": args.current_objective,
        "context_usage_pct": args.context_usage_pct,
        "expected_diff_files": args.expected_diff_files,
        "validation_commands": args.validation_command,
        "goal_summary": args.goal_summary,
        "write_report": args.write_report,
        "update_state": args.update_state or args.write_report,
    }
    report = context_health_check(
        repo_path(args.repo),
        {
            key: value
            for key, value in options.items()
            if value not in (None, [])
        },
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"risk: {report['risk']}")
        print(f"confidence: {report['confidence']}")
        print(f"decision: {report['decision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
