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
from workflow_continuation import (
    AWAIT_HUMAN,
    CHECKPOINT_AND_CONTINUE,
    COMPLETE,
    CONTINUE_NEXT_ITEM,
    READY_FOR_EXTERNAL_EFFECT,
    VERIFY_ACTIVE_CHANGE,
    COMPLETE_LEDGER_STATUSES,
    INCOMPLETE_LEDGER_STATUSES,
    continuation_decision,
    ledger_execution_source,
    markdown_table_cells,
    markdown_table_column_values,
)
from workflow_hooks import hook_response
from workflow_generated_artifacts import inspect_generated_artifact_lifecycle
from workflow_paths import repo_path
from workflow_release_sync import sync_release_assets as release_sync_assets
from workflow_state import parse_state, resolve_state


def run_stop_checks(repo: Path) -> dict[str, Any]:
    repo = repo_path(repo)
    state_resolution = resolve_state(repo)
    if state_resolution["status"] == "missing":
        return {
            "ok": True,
            "status": "not_applicable",
            "failedChecks": [],
            "checks": [
                {
                    "id": "workflow_state",
                    "ok": True,
                    "status": "not_applicable",
                    "detail": "DevFlow workflow state is not present",
                }
            ],
        }
    release_report = release_promotion_run_gate(repo, apply=False)
    continuation = continuation_stop_check(repo, release_status=release_report.get("status"))
    action = continuation["action"]
    checks = [
        contextual_stop_check(context_health_stop_check(repo), action),
        generated_artifact_stop_check(repo),
        contextual_verification_stop_check(repo, action),
        contextual_stop_check(checkpoint_stop_check(repo), action),
        continuation,
        contextual_release_promotion_stop_check(repo, release_report, action),
    ]
    failed = [item["id"] for item in checks if not item["ok"]]
    return {
        "ok": not failed,
        "status": "ready" if not failed else "blocked",
        "failedChecks": failed,
        "checks": checks,
    }


def generated_artifact_stop_check(repo: Path) -> dict[str, Any]:
    report = inspect_generated_artifact_lifecycle(repo)
    return {
        "id": "generated_artifact_lifecycle",
        "ok": bool(report["ok"]),
        "status": str(report["status"]),
        "detail": (
            "generated artifact lifecycle is resolved"
            if report["ok"]
            else "one or more generated artifact lifecycle decisions remain unresolved"
        ),
        "decisions": [
            {
                "contractId": record["contractId"],
                "decision": record["decision"],
                "status": record["status"],
                "nextAction": record["nextAction"],
            }
            for record in report["records"]
        ],
        "nextActions": report["nextActions"],
    }


def continuation_stop_check(repo: Path, release_status: str | None = None) -> dict[str, Any]:
    result = continuation_decision(repo, release_status=release_status)
    return {
        "id": "execution_continuation",
        "ok": bool(result["stopAllowed"]),
        "status": result["action"].lower(),
        "detail": result["reason"],
        "action": result["action"],
        "nextAction": result["nextAction"],
        "continuationRequired": result["continuationRequired"],
        "executionSource": result["executionSource"],
    }


def contextual_stop_check(check: dict[str, Any], action: str) -> dict[str, Any]:
    if action not in {AWAIT_HUMAN, READY_FOR_EXTERNAL_EFFECT}:
        return check
    return {
        **check,
        "ok": True,
        "status": f"advisory_at_{action.lower()}",
        "detail": f"{check['detail']}; reported without blocking a valid {action} boundary",
    }


def contextual_verification_stop_check(repo: Path, action: str) -> dict[str, Any]:
    if action in {CONTINUE_NEXT_ITEM, CHECKPOINT_AND_CONTINUE, AWAIT_HUMAN}:
        return {
            "id": "verification",
            "ok": True,
            "status": "not_applicable",
            "detail": f"final verification is not the current action while continuation outcome is {action}",
        }
    return verification_stop_check(repo)


def contextual_release_promotion_stop_check(
    repo: Path,
    report: dict[str, Any],
    action: str,
) -> dict[str, Any]:
    check = release_promotion_stop_check(repo, report=report)
    if action not in {AWAIT_HUMAN, READY_FOR_EXTERNAL_EFFECT}:
        return check
    return {
        **check,
        "ok": True,
        "status": "authorization_boundary" if action == READY_FOR_EXTERNAL_EFFECT else "not_applicable",
        "detail": (
            "release promotion is ready for separate explicit authorization"
            if action == READY_FOR_EXTERNAL_EFFECT
            else "release promotion is not required before presenting the Human Gate"
        ),
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


def ledger_completion_stop_check(repo: Path) -> dict[str, Any]:
    ledger = repo / "TASK_LEDGER.md"
    if not ledger.exists():
        return {
            "id": "ledger_completion",
            "ok": True,
            "status": "not_applicable",
            "detail": "no ledger",
        }
    source = ledger_execution_source(repo, ledger, ledger.read_text())
    unknown = source["invalidStatuses"]
    incomplete = not source["valid"] or bool(source["incomplete"])
    return {
        "id": "ledger_completion",
        "ok": not incomplete,
        "status": "complete" if not incomplete else "incomplete",
        "detail": (
            "ledger tasks are closed"
            if not incomplete
            else (source["issues"][0] if source["issues"] else "ledger has incomplete task rows")
        ),
        "invalidStatuses": unknown,
    }


def release_promotion_stop_check(
    repo: Path,
    report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report = report if report is not None else release_promotion_run_gate(repo, apply=False)
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
