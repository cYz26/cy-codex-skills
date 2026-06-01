#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from workflow_lib import doctor_workflow, repo_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose Codex workflow drift.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--plugin-root")
    parser.add_argument("--codex-home")
    parser.add_argument("--check-cache-drift", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = doctor_workflow(
        repo_path(args.repo),
        write_report=args.write_report,
        plugin_root=Path(args.plugin_root).expanduser().resolve() if args.plugin_root else None,
        codex_home=Path(args.codex_home).expanduser().resolve() if args.codex_home else None,
        check_cache_drift=args.check_cache_drift,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
