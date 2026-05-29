#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from workflow_agent_kb import lint_agent_kb


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint a Markdown-first AgentKB vault.")
    parser.add_argument("--vault", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = lint_agent_kb(vault=args.vault, project=args.project, write_report=args.write_report)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{report['finding_count']} finding(s), {report['blocking_findings']} blocking.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
