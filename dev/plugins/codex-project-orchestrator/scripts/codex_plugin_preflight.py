#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from plugin_preflight_runner import run_preflight


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate codex-project-orchestrator plugin packaging.")
    parser.add_argument("--plugin-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--marketplace")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    marketplace = Path(args.marketplace).expanduser().resolve() if args.marketplace else None
    report = run_preflight(Path(args.plugin_root).expanduser().resolve(), marketplace)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for check in report["checks"]:
            print(f"{'OK' if check['ok'] else 'FAIL'} {check['name']}: {check['detail']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
