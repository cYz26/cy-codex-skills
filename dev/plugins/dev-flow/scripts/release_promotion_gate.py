#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from workflow_hooks import hook_response
from workflow_paths import repo_path
from workflow_release_sync import _issue_release_apply_authorization, sync_release_assets
from workflow_state import parse_state
from workflow_provider_registry import default_plugin_root, side_effect_decision


def run_gate(repo: Path, apply: bool = False, target: str = "dev-flow") -> dict:
    repo = repo_path(repo)
    state = parse_state(repo)
    gates = state.get("gates", {})
    authorization = side_effect_decision(
        default_plugin_root(),
        "archive_release",
        {"verified_and_explicit_user_request"} if apply else set(),
    )
    if not gates.get("verification_passed", False):
        return {
            "status": "not_applicable",
            "message": "Release promotion waits for recorded verification.",
            "assets": [],
            "sideEffect": authorization,
        }
    if apply and not authorization["authorized"]:
        return {
            "status": "authorization_required",
            "message": "Release promotion requires explicit archive/release authorization.",
            "assets": [],
            "sideEffect": authorization,
        }
    apply_authorization = (
        _issue_release_apply_authorization(repo, [target])
        if apply
        else None
    )
    report = sync_release_assets(
        repo,
        apply=apply,
        targets=[target],
        _apply_authorization=apply_authorization,
    )
    if report["status"] == "synced":
        message = "DevFlow: release assets were synced; run release validation and Plugin Eval before commit."
    elif report["status"] == "pending":
        message = (
            "DevFlow: release assets are pending sync; run "
            "release_promotion_gate.py --apply after verification."
        )
    elif report["status"] == "current":
        message = "DevFlow: release assets are current."
    else:
        message = "DevFlow: no release assets were applicable."
    return {
        **report,
        "message": message,
        "qualityGates": quality_gates(report),
        "sideEffect": authorization,
    }


def quality_gates(report: dict) -> list[dict]:
    target_records = report.get("evalTargets", [])
    eval_targets = [target["target"] for target in target_records]
    devflow = next(
        (
            target["target"]
            for target in target_records
            if target.get("kind") == "plugin" and target.get("name") == "dev-flow"
        ),
        None,
    )
    plugin_eval_target = devflow or (eval_targets[0] if eval_targets else "plugins/dev-flow")
    return [
        {
            "name": "release runtime verification",
            "command": [
                "python3",
                "plugins/dev-flow/scripts/verify_release_runtime.py",
                "--plugin-root",
                "plugins/dev-flow",
                "--json",
            ],
            "required": True,
        },
        {
            "name": "Plugin Eval release",
            "command": ["plugin-eval", "analyze", plugin_eval_target, "--format", "markdown"],
            "targets": eval_targets,
            "required": True,
        },
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote dev assets to release after verification passes.")
    parser.add_argument("--repo", help="Repository root. Defaults to hook cwd or current directory.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Apply the explicitly selected release sync.")
    mode.add_argument("--check", action="store_true", help="Dry-run only (the default).")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    payload = read_hook_payload()
    repo = Path(args.repo or payload.get("cwd") or Path.cwd())
    report = run_gate(repo, apply=args.apply)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    if report["status"] in {"synced", "pending"}:
        return hook_response(repo_path(repo), report["message"], event_name="Stop")
    return 0


def read_hook_payload() -> dict:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return {}


if __name__ == "__main__":
    raise SystemExit(main())
