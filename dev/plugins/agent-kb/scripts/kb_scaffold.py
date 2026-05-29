#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from workflow_agent_kb import scaffold_agent_kb


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold a Markdown-first AgentKB vault.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--vault", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--owner", default="owner")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = scaffold_agent_kb(
        repo=args.repo,
        vault=args.vault,
        project=args.project,
        owner=args.owner,
        force=args.force,
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Scaffolded {len(report['written'])} files, skipped {len(report['skipped'])} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
