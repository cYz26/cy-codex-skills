#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from workflow_release_sync import release_eval_target, sync_release_assets


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync dev plugin and skill assets to release paths.")
    parser.add_argument("--repo", default=".", help="Repository root. Defaults to current directory.")
    parser.add_argument("--apply", action="store_true", help="Apply the sync. Omit for dry-run drift detection.")
    parser.add_argument("--eval-target", help="Resolve a path to its release-preferred Plugin Eval target.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    if args.eval_target:
        payload = release_eval_target(repo, Path(args.eval_target))
    else:
        payload = sync_release_assets(repo, apply=args.apply)

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_text(payload))
    return 0


def render_text(payload: dict) -> str:
    if "assets" not in payload:
        preferred = "release" if payload.get("releasePreferred") else "input"
        return f"Plugin Eval target ({preferred}): {payload['target']}"
    lines = [f"Release sync status: {payload['status']}"]
    for asset in payload["assets"]:
        changed = len(asset["changedFiles"])
        missing = len(asset["missingOutputs"])
        lines.append(f"- {asset['kind']} {asset['name']}: {changed} changed, {missing} missing outputs")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
