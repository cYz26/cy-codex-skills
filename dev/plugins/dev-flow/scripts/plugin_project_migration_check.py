#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from plugin_project_migration import migration_reminder
from workflow_hooks import hook_response


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a lightweight plugin project migration reminder check.")
    parser.add_argument("--event", default="manual")
    parser.add_argument("--plugin-root", default=os.environ.get("PLUGIN_ROOT"))
    parser.add_argument("--codex-home", default=os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}
    repo = Path(payload.get("cwd") or Path.cwd()).expanduser().resolve()
    plugin_root = Path(args.plugin_root).expanduser().resolve() if args.plugin_root else Path(__file__).parents[1]
    message = migration_reminder(repo=repo, plugin_root=plugin_root, codex_home=args.codex_home)
    if not message:
        return 0
    return hook_response(repo, message)


if __name__ == "__main__":
    raise SystemExit(main())
