#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from workflow_hooks import hook_response
from workflow_paths import repo_path
from workflow_release_sync import (
    _issue_release_apply_authorization,
    discover_assets,
    read_metadata,
    select_assets,
    sync_release_assets,
)
from workflow_side_effect_policy import default_plugin_root, side_effect_decision
from workflow_release_verification import release_promotion_readiness


def run_gate(repo: Path, apply: bool = False, target: str = "dev-flow") -> dict:
    repo = repo_path(repo)
    release_profile, profile_errors = resolve_release_profile(repo, target)
    if release_profile is None:
        return {
            "status": "unsupported_target",
            "message": (
                f"No release target profile is defined for {target}; add an "
                "asset-specific releaseVerificationCommand before promotion."
            ),
            "assets": [],
            "qualityGates": [],
            "requestedTargets": [target],
            "selectionErrors": profile_errors or ["unsupported_release_target_profile"],
        }
    readiness = release_promotion_readiness(
        repo,
        target,
        require_authorization=False,
    )
    authorization = side_effect_decision(
        default_plugin_root(),
        "release.promote_local",
        {"verified_approved_write_set"} if apply else set(),
    )
    if not readiness["ready"]:
        return {
            "status": "not_applicable",
            "message": "Release promotion waits for complete source-bound verification.",
            "assets": [],
            "sideEffect": authorization,
            "releaseReadiness": readiness,
        }
    apply_readiness = release_promotion_readiness(
        repo,
        target,
        require_authorization=True,
    )
    if apply and (not authorization["authorized"] or not apply_readiness["ready"]):
        return {
            "status": "authorization_required",
            "message": "Release promotion requires a verified approved local write set.",
            "assets": [],
            "sideEffect": authorization,
            "releaseReadiness": apply_readiness,
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
    label = "DevFlow" if target == "dev-flow" else target
    if report["status"] == "synced":
        message = f"{label}: release assets were synced; run release validation and Plugin Eval before commit."
    elif report["status"] == "pending":
        message = (
            f"{label}: release assets are pending sync; run "
            f"release_promotion_gate.py --target {target} --apply after verification."
        )
    elif report["status"] == "current":
        message = f"{label}: release assets are current."
    else:
        message = f"{label}: no release assets were applicable."
    return {
        **report,
        "message": message,
        "qualityGates": quality_gates(
            report,
            target=target,
            release_profile=release_profile,
        ),
        "releaseProfile": release_profile,
        "sideEffect": authorization,
        "releaseReadiness": apply_readiness if apply else readiness,
    }


def quality_gates(
    report: dict,
    target: str | None = None,
    release_profile: dict | None = None,
) -> list[dict]:
    target_records = report.get("evalTargets", [])
    if target is None:
        reported_names = [
            str(record.get("name"))
            for record in target_records
            if isinstance(record, dict) and record.get("name")
        ]
        target = reported_names[0] if len(set(reported_names)) == 1 else "dev-flow"
    eval_targets = [target["target"] for target in target_records]
    selected_record = next(
        (
            record
            for record in target_records
            if record.get("name") == target
        ),
        None,
    )
    plugin_eval_target = (
        selected_record["target"]
        if selected_record
        else (eval_targets[0] if eval_targets else f"plugins/{target}")
    )
    profile = release_profile or builtin_release_profile(target)
    if profile is None:
        raise ValueError(f"release target profile is unavailable for {target}")
    return [
        {
            "name": profile["name"],
            "command": profile["command"],
            "required": True,
        },
        {
            "name": "Plugin Eval release",
            "command": ["plugin-eval", "analyze", plugin_eval_target, "--format", "markdown"],
            "targets": eval_targets,
            "required": True,
        },
    ]


def release_runtime_verification_command(
    target: str,
) -> list[str]:
    if target == "dev-flow":
        return [
            "python3",
            "-B",
            "plugins/dev-flow/scripts/verify_release_runtime.py",
            "--plugin-root",
            "plugins/dev-flow",
            "--json",
        ]
    if target == "lark-feishu-ops":
        return [
            "python3.12",
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            "dev/plugins/lark-feishu-ops/verification",
            "-p",
            "test_release_package.py",
        ]
    raise ValueError(f"release target profile is unavailable for {target}")


def builtin_release_profile(target: str) -> dict | None:
    if target not in {"dev-flow", "lark-feishu-ops"}:
        return None
    return {
        "source": "builtin",
        "name": "release runtime verification",
        "command": release_runtime_verification_command(target),
    }


def resolve_release_profile(repo: Path, target: str) -> tuple[dict | None, list[str]]:
    builtin = builtin_release_profile(target)
    if builtin is not None:
        return builtin, []
    try:
        assets = discover_assets(repo)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return None, ["release target metadata is unreadable or malformed"]
    selected, errors = select_assets(repo, assets, [target])
    if errors or len(selected) != 1:
        return None, errors or ["release target did not resolve to one asset"]
    asset = selected[0]
    metadata = read_metadata(asset.source)
    raw_command = metadata.get("releaseVerificationCommand")
    if (
        not isinstance(raw_command, list)
        or not raw_command
        or not all(isinstance(token, str) and token for token in raw_command)
    ):
        return None, ["release target metadata lacks a valid releaseVerificationCommand"]
    substitutions = {
        "{python}": sys.executable,
        "{repo}": str(repo),
        "{source}": str(asset.source),
        "{release}": str(asset.release),
    }
    command = [
        replace_profile_tokens(token, substitutions)
        for token in raw_command
    ]
    raw_name = metadata.get("releaseVerificationName")
    name = (
        raw_name.strip()
        if isinstance(raw_name, str) and raw_name.strip()
        else "release runtime verification"
    )
    return {
        "source": "release-sync metadata",
        "name": name,
        "command": command,
        "kind": asset.kind,
    }, []


def replace_profile_tokens(value: str, substitutions: dict[str, str]) -> str:
    result = value
    for marker, replacement in substitutions.items():
        result = result.replace(marker, replacement)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote dev assets to release after verification passes.")
    parser.add_argument("--repo", help="Repository root. Defaults to hook cwd or current directory.")
    parser.add_argument(
        "--target",
        default="dev-flow",
        help="Maintained release target. Defaults to dev-flow for compatibility.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Apply the explicitly selected release sync.")
    mode.add_argument("--check", action="store_true", help="Dry-run only (the default).")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    payload = read_hook_payload()
    repo = Path(args.repo or payload.get("cwd") or Path.cwd())
    report = run_gate(repo, apply=args.apply, target=args.target)
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
