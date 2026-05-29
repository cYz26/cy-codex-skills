from __future__ import annotations

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
    repo_truth = collect_repo_truth(repo)
    workflow_truth = collect_workflow_truth(repo, state)
    goal = goal_report(state, options, repo_truth)
    signals = collect_signals(events, repo_truth, workflow_truth, goal, options)
    risk = highest_risk(signals)
    report = {
        "ok": True,
        "risk": risk,
        "confidence": confidence_for(events, options),
        "decision": decision_for(risk, signals),
        "score": score_for(signals),
        "signals": signals,
        "repo_truth": repo_truth,
        "workflow_truth": workflow_truth,
        "goal": goal,
        "subagents": subagent_report(events, signals, options),
        "minimal_next_context": minimal_next_context(
            options,
            repo_truth,
            workflow_truth,
            goal,
        ),
        "unknown_metrics": unknown_metrics(events, options),
    }
    if options.get("write_report"):
        report["report_file"] = write_health_report(
            repo,
            report,
            update=bool(options.get("update_state", True)),
        )
    return report
