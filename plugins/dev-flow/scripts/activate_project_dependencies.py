#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from workflow_project_activation import activate_project_dependencies


def main() -> int:
    parser = argparse.ArgumentParser(description="Activate orchestrator dependencies in one target repo.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--plugin-root", default=None)
    parser.add_argument("--codex-home", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--skip-official-installs",
        action="store_true",
        help="Only install project-local orchestrator/Superpowers skills; do not run GSD/OpenSpec installers.",
    )
    parser.add_argument(
        "--refresh-project-skills",
        action="store_true",
        help="Refresh project-local symlinks that point at an older provider skill source.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = activate_project_dependencies(
        args.repo,
        args.dry_run,
        args.skip_official_installs,
        args.plugin_root,
        args.codex_home,
        args.refresh_project_skills,
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("OK" if report["ok"] else "FAIL")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
