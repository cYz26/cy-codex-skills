#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from workflow_context_health import import_codex_sessions
from workflow_paths import repo_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Import historical Codex session metadata for context health.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--codex-home", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = import_codex_sessions(repo_path(args.repo), repo_path(args.codex_home))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"imported_events: {report['imported_events']}")
        print(f"coverage: {report['coverage']}")
        print(f"confidence: {report['confidence']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
