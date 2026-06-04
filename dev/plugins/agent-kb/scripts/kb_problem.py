#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from agent_kb_config import discover_agent_kb_config
from agent_kb_problem_capture import record_manual_problem
from workflow_paths import repo_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Record AgentKB problem reflection drafts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    record_parser = subparsers.add_parser("record")
    record_parser.add_argument("--repo", required=True)
    record_parser.add_argument("--incident", required=True)
    record_parser.add_argument("--evidence", default="")
    record_parser.add_argument("--root-cause", default="")
    record_parser.add_argument("--lesson", default="")
    record_parser.add_argument("--prevention", default="")
    record_parser.add_argument("--validation", default="")
    record_parser.add_argument("--residual-risk", default="")
    record_parser.add_argument("--json", action="store_true")

    args = parser.parse_args()
    repo = repo_path(args.repo)
    config = discover_agent_kb_config(repo)
    if not config:
        report = {"ok": False, "recorded": False, "reason": "not_configured", "repo": str(repo)}
    else:
        report = record_manual_problem(
            repo,
            config,
            incident=args.incident,
            evidence=args.evidence,
            root_cause=args.root_cause,
            lesson=args.lesson,
            prevention=args.prevention,
            validation=args.validation,
            residual_risk=args.residual_risk,
        )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(report.get("path") or report.get("reason"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
