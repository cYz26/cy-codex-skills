#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from plugin_preflight_runner import run_preflight
from workflow_constants import resolve_plugin_root


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate dev-flow plugin packaging.")
    parser.add_argument("--plugin-root", default=str(resolve_plugin_root()))
    parser.add_argument("--marketplace")
    parser.add_argument("--repo", help="Target repo whose project-local .codex activation should be checked.")
    parser.add_argument("--codex-home")
    parser.add_argument("--config")
    parser.add_argument("--strict", action="store_true", help="Treat developer helpers as required.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    marketplace = Path(args.marketplace).expanduser().resolve() if args.marketplace else None
    report = run_preflight(
        Path(args.plugin_root).expanduser().resolve(),
        marketplace,
        Path(args.codex_home).expanduser().resolve() if args.codex_home else None,
        Path(args.config).expanduser().resolve() if args.config else None,
        args.strict,
        Path(args.repo).expanduser().resolve() if args.repo else None,
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for check in report["checks"]:
            print(f"{'OK' if check['ok'] else 'FAIL'} {check['name']}: {check['detail']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
