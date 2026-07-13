#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from workflow_release_sync import release_eval_target, sync_release_assets


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync dev plugin and skill assets to release paths.")
    parser.add_argument("--repo", default=".", help="Repository root. Defaults to current directory.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Request apply. Direct CLI apply is denied; use "
            "release_promotion_gate.py --apply after verification."
        ),
    )
    parser.add_argument(
        "--target",
        action="append",
        help="Release asset name or source/release path. Required for apply; repeatable.",
    )
    parser.add_argument("--eval-target", help="Resolve a path to its release-preferred Plugin Eval target.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    if args.eval_target:
        payload = release_eval_target(repo, Path(args.eval_target))
    else:
        payload = sync_release_assets(repo, apply=args.apply, targets=args.target)

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_text(payload))
    denied = {"authorization_required", "target_required", "invalid_target"}
    return 0 if payload.get("status") not in denied else 2


def render_text(payload: dict) -> str:
    if "assets" not in payload:
        preferred = "release" if payload.get("releasePreferred") else "input"
        return f"Plugin Eval target ({preferred}): {payload['target']}"
    lines = [f"Release sync status: {payload['status']}"]
    for asset in payload["assets"]:
        changed = len(asset["changedFiles"])
        missing = len(asset["missingOutputs"])
        stale_outputs = len(asset.get("staleOutputs", []))
        stale_files = len(asset.get("staleFiles", []))
        deleted = len(asset.get("deletedFiles", []))
        lines.append(
            f"- {asset['kind']} {asset['name']}: {changed} changed, "
            f"{missing} missing outputs, {stale_outputs} stale outputs, "
            f"{stale_files} stale files, {deleted} deleted files"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
