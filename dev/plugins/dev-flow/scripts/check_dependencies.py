#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from workflow_dependencies import dependency_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Codex plugin dependencies before use.")
    parser.add_argument("--plugin-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--repo", help="Target repo whose project-local .codex activation should be checked.")
    parser.add_argument("--codex-home")
    parser.add_argument("--config")
    parser.add_argument("--strict", action="store_true", help="Treat developer helpers as required.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = dependency_report(
        Path(args.plugin_root).expanduser().resolve(),
        Path(args.codex_home).expanduser().resolve() if args.codex_home else None,
        Path(args.config).expanduser().resolve() if args.config else None,
        args.strict,
        Path(args.repo).expanduser().resolve() if args.repo else None,
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for check in report["checks"]:
            state = "OK" if check["ok"] else "FAIL"
            required = "required" if check["required"] else "recommended"
            print(f"{state} {check['name']} ({required}): {check['detail']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
