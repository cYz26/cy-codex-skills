#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from release_promotion_gate import run_gate as release_promotion_run_gate
from workflow_context_health import context_health_check
from workflow_compact_state import SUPPORTED_COMPACT_STATUSES, supported_compact_statuses_text
from workflow_hooks import hook_response
from workflow_paths import repo_path
from workflow_release_sync import sync_release_assets as release_sync_assets
from workflow_state import parse_state


def run_stop_checks(repo: Path) -> dict[str, Any]:
    repo = repo_path(repo)
    checks = [
        context_health_stop_check(repo),
        verification_stop_check(repo),
        checkpoint_stop_check(repo),
        superpowers_completion_stop_check(repo),
        release_promotion_stop_check(repo),
    ]
    failed = [item["id"] for item in checks if not item["ok"]]
    return {
        "ok": not failed,
        "status": "ready" if not failed else "blocked",
        "failedChecks": failed,
        "checks": checks,
    }


def context_health_stop_check(repo: Path) -> dict[str, Any]:
    report = context_health_check(repo, {"write_report": False})
    pending = pending_subagent_recommendations(report)
    ok = report.get("risk") not in {"high", "critical"}
    return {
        "id": "context_health",
        "ok": ok,
        "status": report.get("risk", "unknown"),
        "detail": context_health_detail(report, pending),
        "pendingRecommendations": pending,
    }


def context_health_detail(report: dict[str, Any], pending: list[dict[str, Any]]) -> str:
    detail = f"context health {report.get('risk', 'unknown')}"
    if not pending:
        return detail
    ids = ", ".join(item["id"] for item in pending)
    return f"{detail}; pending subagent recommendation disposition: {ids}"


def pending_subagent_recommendations(report: dict[str, Any]) -> list[dict[str, Any]]:
    subagents = report.get("subagents", {})
    if not isinstance(subagents, dict):
        return []
    if not subagents.get("dispositionRequired") or subagents.get("disposition") != "pending":
        return []
    return [
        {
            "id": str(subagents.get("recommendationId", "unknown")),
            "recommendation": str(subagents.get("recommendation", "unknown")),
            "disposition": "pending",
            "nextAction": str(subagents.get("nextAction", "")),
        }
    ]


def verification_stop_check(repo: Path) -> dict[str, Any]:
    state = parse_state(repo)
    ok = bool(state.get("gates", {}).get("verification_passed"))
    return {
        "id": "verification",
        "ok": ok,
        "status": "recorded" if ok else "missing",
        "detail": "verification evidence recorded" if ok else "verification has not been recorded",
    }


def checkpoint_stop_check(repo: Path) -> dict[str, Any]:
    state = parse_state(repo)
    context = state.get("context_management", {})
    status = context.get("compact_status", "not_needed")
    if status not in SUPPORTED_COMPACT_STATUSES:
        return {
            "id": "checkpoint",
            "ok": False,
            "status": status,
            "detail": f"unsupported compact_status; must be one of: {supported_compact_statuses_text()}",
        }
    ok = status not in {"failed", "blocked"}
    if status == "pending":
        detail = "compact pending advisory; checkpoint state is acceptable"
    else:
        detail = "checkpoint state is acceptable" if ok else "checkpoint/compact gate requires action"
    return {
        "id": "checkpoint",
        "ok": ok,
        "status": status,
        "detail": detail,
    }


def superpowers_completion_stop_check(repo: Path) -> dict[str, Any]:
    ledger = repo / "TASK_LEDGER.md"
    if not ledger.exists():
        return {"id": "superpowers_completion", "ok": True, "status": "not_applicable", "detail": "no ledger"}
    text = ledger.read_text().lower()
    incomplete = any(f"| {status} |" in text for status in ["planned", "executing", "review", "blocked"])
    return {
        "id": "superpowers_completion",
        "ok": not incomplete,
        "status": "complete" if not incomplete else "incomplete",
        "detail": "ledger tasks are closed" if not incomplete else "ledger has incomplete task rows",
    }


def release_promotion_stop_check(repo: Path) -> dict[str, Any]:
    report = release_promotion_run_gate(repo, apply=False)
    ok = report.get("status") not in {"pending", "synced"}
    return {
        "id": "release_promotion",
        "ok": ok,
        "status": report.get("status", "unknown"),
        "detail": report.get("message", "release promotion dry-run complete"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DevFlow read-only Stop checks.")
    parser.add_argument("--repo", help="Repository root. Defaults to hook cwd or current directory.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = read_hook_payload()
    repo = repo_path(args.repo or payload.get("cwd") or Path.cwd())
    report = run_stop_checks(repo)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["ok"] else 1
    if not report["ok"]:
        message = "DevFlow: Stop checks require follow-up: " + ", ".join(report["failedChecks"])
        return hook_response(repo, message, event_name="Stop", diagnostic={"stopChecks": report})
    return 0


def read_hook_payload() -> dict[str, Any]:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return {}


if __name__ == "__main__":
    raise SystemExit(main())
