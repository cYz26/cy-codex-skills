#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from workflow_hooks import hook_response
from workflow_paths import repo_path
from workflow_release_sync import sync_release_assets
from workflow_state import parse_state


def run_gate(repo: Path, apply: bool = True) -> dict:
    repo = repo_path(repo)
    state = parse_state(repo)
    gates = state.get("gates", {})
    if not gates.get("verification_passed", False):
        return {
            "status": "not_applicable",
            "message": "Release promotion waits for recorded verification.",
            "assets": [],
        }
    report = sync_release_assets(repo, apply=apply)
    if report["status"] == "synced":
        message = "DevFlow: release assets were synced; run release validation and Plugin Eval before commit."
    elif report["status"] == "pending":
        message = "DevFlow: release assets are pending sync; run sync_release_assets.py --apply."
    elif report["status"] == "current":
        message = "DevFlow: release assets are current."
    else:
        message = "DevFlow: no release assets were applicable."
    return {**report, "message": message}


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote dev assets to release after verification passes.")
    parser.add_argument("--repo", help="Repository root. Defaults to hook cwd or current directory.")
    parser.add_argument("--check", action="store_true", help="Dry-run only.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    payload = read_hook_payload()
    repo = Path(args.repo or payload.get("cwd") or Path.cwd())
    report = run_gate(repo, apply=not args.check)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    if report["status"] in {"synced", "pending"}:
        return hook_response(repo_path(repo), report["message"])
    return 0


def read_hook_payload() -> dict:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return {}


if __name__ == "__main__":
    raise SystemExit(main())
