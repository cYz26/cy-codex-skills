#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from workflow_lib import repo_path, scaffold_workflow


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold Codex project workflow files.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--mode", choices=["auto", "greenfield", "brownfield"], default="auto")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-agents", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = scaffold_workflow(
        repo_path(args.repo),
        mode=args.mode,
        dry_run=args.dry_run,
        force_agents=args.force_agents,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
