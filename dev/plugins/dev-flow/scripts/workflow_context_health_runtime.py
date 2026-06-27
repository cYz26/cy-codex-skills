from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from workflow_context_health_goal import goal_report, minimal_next_context
from workflow_context_health_repo import collect_repo_truth, collect_workflow_truth
from workflow_context_health_report import write_health_report
from workflow_context_health_signals import (
    collect_signals,
    confidence_for,
    decision_for,
    highest_risk,
    score_for,
    unknown_metrics,
)
from workflow_context_health_subagents import subagent_report
from workflow_context_health_events import read_events
from workflow_paths import repo_path
from workflow_state import parse_state


def context_health_check(
    repo: Path,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    repo = repo_path(repo)
    options = options or {}
    events = read_events(repo)
    state = parse_state(repo)
    effective_options = {
        **options,
        "subagent_dispositions": {
            **previous_subagent_dispositions(repo, state),
            **dict_value(options.get("subagent_dispositions")),
        },
        "subagent_disposition_notes": {
            **previous_subagent_disposition_notes(repo, state),
            **dict_value(options.get("subagent_disposition_notes")),
        },
    }
    repo_truth = collect_repo_truth(repo)
    workflow_truth = collect_workflow_truth(repo, state)
    goal = goal_report(state, effective_options, repo_truth)
    signals = collect_signals(events, repo_truth, workflow_truth, goal, effective_options)
    risk = highest_risk(signals)
    report = {
        "ok": True,
        "risk": risk,
        "confidence": confidence_for(events, effective_options),
        "decision": decision_for(risk, signals),
        "score": score_for(signals),
        "signals": signals,
        "repo_truth": repo_truth,
        "workflow_truth": workflow_truth,
        "goal": goal,
        "subagents": subagent_report(events, signals, effective_options),
        "minimal_next_context": minimal_next_context(
            effective_options,
            repo_truth,
            workflow_truth,
            goal,
        ),
        "unknown_metrics": unknown_metrics(events, effective_options),
    }
    if options.get("write_report"):
        report["report_file"] = write_health_report(
            repo,
            report,
            update=bool(options.get("update_state", True)),
        )
    return report


def previous_subagent_dispositions(repo: Path, state: dict[str, Any]) -> dict[str, str]:
    previous = previous_subagent_report(repo, state)
    if not previous:
        return {}
    recommendation_id = str(previous.get("recommendationId", ""))
    disposition = str(previous.get("disposition", ""))
    if not recommendation_id or disposition not in {"accepted", "declined", "superseded", "blocked"}:
        return {}
    return {recommendation_id: disposition}


def previous_subagent_disposition_notes(repo: Path, state: dict[str, Any]) -> dict[str, str]:
    previous = previous_subagent_report(repo, state)
    if not previous:
        return {}
    recommendation_id = str(previous.get("recommendationId", ""))
    note = str(previous.get("dispositionNote", "")).strip()
    if not recommendation_id or not note:
        return {}
    return {recommendation_id: note}


def previous_subagent_report(repo: Path, state: dict[str, Any]) -> dict[str, Any]:
    last_report = state.get("context_health", {}).get("last_report")
    if not last_report or last_report == "none":
        return {}
    path = repo / str(last_report)
    if not path.is_file():
        return {}
    try:
        report = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    subagents = report.get("subagents", {})
    return subagents if isinstance(subagents, dict) else {}


def dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
