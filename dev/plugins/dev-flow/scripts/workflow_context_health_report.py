from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from workflow_paths import rel, write_json
from workflow_state import update_state


def write_health_report(
    repo: Path,
    report: dict[str, Any],
    update: bool = True,
) -> str:
    timestamp = datetime.now().astimezone().strftime("%Y%m%d%H%M%S")
    root = repo / ".planning" / "context-health" / "reports"
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / f"{timestamp}-context-health.json"
    md_path = root / f"{timestamp}-context-health.md"
    write_json(json_path, report)
    md_path.write_text(render_markdown_report(report), encoding="utf-8")
    rel_json = rel(repo, json_path)
    if update:
        update_state_from_report(repo, rel_json, report)
    return rel_json


def update_state_from_report(
    repo: Path,
    rel_json: str,
    report: dict[str, Any],
) -> None:
    try:
        update_state(
            repo,
            last_context_health_report=rel_json,
            last_context_health_risk=report["risk"],
            last_context_health_confidence=report["confidence"],
            last_context_health_decision=report["decision"],
            last_goal_status=report["goal"]["status"],
            goal_summary=report["goal"]["summary"],
        )
    except Exception:
        pass


def render_markdown_report(report: dict[str, Any]) -> str:
    signals = report.get("signals") or []
    signal_lines = render_signal_lines(signals)
    changed = render_list(report.get("repo_truth", {}).get("changed_files", []))
    unknown = render_list(report.get("unknown_metrics", []))
    minimal_context = json.dumps(report.get("minimal_next_context", {}), indent=2)
    goal = report.get("goal", {})
    subagents = report.get("subagents", {})
    return f"""# Context Health Report

## Decision

- risk: {report.get('risk')}
- confidence: {report.get('confidence')}
- decision: {report.get('decision')}
- score: {report.get('score')}

## Signals

{signal_lines}

## Changed Files

{changed}

## Goal

- status: {goal.get('status')}
- summary: {goal.get('summary')}

## Subagents

- recommendation: {subagents.get('recommendation')}
- recommendation_id: {subagents.get('recommendationId')}
- disposition: {subagents.get('disposition')}
- disposition_note: {subagents.get('dispositionNote', 'none')}
- reason: {subagents.get('reason')}
- next_action: {subagents.get('nextAction')}

## Unknown Metrics

{unknown}

## Minimal Next Context

```json
{minimal_context}
```
"""


def render_signal_lines(signals: list[dict[str, Any]]) -> str:
    if not signals:
        return "- none"
    return "\n".join(
        f"- {item['id']}: {item['severity']} - {item['message']}"
        for item in signals
    )


def render_list(items: list[str]) -> str:
    if not items:
        return "- none"
    return "\n".join(f"- {item}" for item in items)
