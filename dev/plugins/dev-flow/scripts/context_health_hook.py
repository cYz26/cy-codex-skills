#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from workflow_context_health import context_health_check, record_context_health_event
from workflow_hooks import hook_response
from workflow_paths import repo_path
from workflow_state import parse_state


def should_prompt_context_health(repo: Path, report: dict[str, Any]) -> bool:
    risk = report.get("risk")
    if risk in {"high", "critical"}:
        return True
    if risk != "medium":
        return False
    return not medium_report_can_be_advisory(repo, report)


def medium_report_can_be_advisory(repo: Path, report: dict[str, Any]) -> bool:
    return has_acknowledged_medium_report(repo, report)


def has_acknowledged_medium_report(repo: Path, report: dict[str, Any]) -> bool:
    state = parse_state(repo)
    last_report = state.get("context_health", {}).get("last_report")
    if not last_report or last_report == "none":
        return False
    path = repo / str(last_report)
    if not path.is_file():
        return False
    try:
        previous = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    return context_health_signature(previous) == context_health_signature(report)


def context_health_signature(report: dict[str, Any]) -> dict[str, Any]:
    repo_truth = report.get("repo_truth", {})
    return {
        "risk": report.get("risk"),
        "decision": report.get("decision"),
        "signals": sorted(
            (signal.get("id"), signal.get("severity"))
            for signal in report.get("signals", [])
        ),
        "changed_files": sorted(repo_truth.get("changed_files", [])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Record DevFlow context-health hook metadata.")
    parser.add_argument("--event", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}
    repo = repo_path(payload.get("cwd") or Path.cwd())
    record_context_health_event(repo, args.event, payload)
    if args.check or args.event.lower() == "stop":
        report = context_health_check(repo, {"write_report": True})
        if should_prompt_context_health(repo, report):
            return hook_response(
                repo,
                f"DevFlow: context health is {report['risk']} ({report['decision']}). "
                "Run context-health-check before continuing.",
                event_name="Stop" if args.event.lower() == "stop" else "PreToolUse",
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
