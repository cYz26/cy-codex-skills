from __future__ import annotations

from collections import Counter
from typing import Any


RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def collect_signals(
    events: list[dict[str, Any]],
    repo_truth: dict[str, Any],
    workflow_truth: dict[str, Any],
    goal: dict[str, Any],
    options: dict[str, Any],
) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    add_compact_signal(signals, workflow_truth)
    add_repeated_failure_signal(signals, events)
    add_repeated_read_signal(signals, events)
    add_diff_spread_signal(signals, repo_truth, options)
    add_validation_signal(signals, events, repo_truth, workflow_truth)
    add_context_usage_signal(signals, options)
    if goal.get("status") == "conflicting":
        signals.append(signal("goal_conflict", "high", "Goal state conflicts with current objective."))
    return signals


def add_compact_signal(
    signals: list[dict[str, Any]],
    workflow_truth: dict[str, Any],
) -> None:
    if workflow_truth.get("compact_status") == "pending":
        signals.append(signal("compact_pending", "high", "Workflow compact_status is pending."))


def add_repeated_failure_signal(
    signals: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> None:
    repeated_failure = repeated_command_failure(events)
    if not repeated_failure:
        return
    severity = "high" if repeated_failure["count"] >= 3 else "medium"
    message = f"Command failed {repeated_failure['count']} times without a passing event."
    signals.append(signal("repeated_command_failure", severity, message, repeated_failure))


def add_repeated_read_signal(
    signals: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> None:
    repeated_read = repeated_file_read(events)
    if repeated_read:
        signals.append(
            signal(
                "repeated_file_read",
                "medium",
                f"File was inspected {repeated_read['count']} times.",
                repeated_read,
            )
        )


def add_diff_spread_signal(
    signals: list[dict[str, Any]],
    repo_truth: dict[str, Any],
    options: dict[str, Any],
) -> None:
    expected_diff = int(options.get("expected_diff_files", 6))
    if repo_truth["diff_file_count"] <= expected_diff:
        return
    message = (
        f"Changed file count {repo_truth['diff_file_count']} "
        f"exceeds expected scope {expected_diff}."
    )
    signals.append(signal("diff_spread", "medium", message))


def add_validation_signal(
    signals: list[dict[str, Any]],
    events: list[dict[str, Any]],
    repo_truth: dict[str, Any],
    workflow_truth: dict[str, Any],
) -> None:
    if not repo_truth["production_like_changed_files"]:
        return
    if latest_validation(workflow_truth, events):
        return
    signals.append(
        signal(
            "validation_stale",
            "medium",
            "Production-like changes have no recent validation evidence.",
        )
    )


def add_context_usage_signal(
    signals: list[dict[str, Any]],
    options: dict[str, Any],
) -> None:
    context_usage = options.get("context_usage_pct")
    if not isinstance(context_usage, (int, float)):
        return
    if context_usage >= 80:
        signals.append(signal("context_usage_high", "high", f"Context usage is {context_usage}%."))
    elif context_usage >= 70:
        signals.append(signal("context_usage_warning", "medium", f"Context usage is {context_usage}%."))


def signal(
    signal_id: str,
    severity: str,
    message: str,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": signal_id,
        "severity": severity,
        "message": message,
        "evidence": evidence or {},
    }


def repeated_command_failure(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    failures: Counter[str] = Counter()
    passes: set[str] = set()
    labels: dict[str, str] = {}
    for event in events:
        command_hash = event.get("command_hash")
        if not command_hash:
            continue
        labels[str(command_hash)] = str(event.get("command_redacted", command_hash))
        if event.get("status") == "pass":
            passes.add(str(command_hash))
        if event.get("status") == "fail":
            failures[str(command_hash)] += 1
    candidates = [
        (key, count)
        for key, count in failures.items()
        if count >= 2 and key not in passes
    ]
    if not candidates:
        return None
    key, count = max(candidates, key=lambda item: item[1])
    return {"command_hash": key, "command": labels.get(key, key), "count": count}


def repeated_file_read(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    reads: Counter[str] = Counter()
    for event in events:
        if event.get("event_type") not in {"pre_tool_use", "post_tool_use"}:
            continue
        if not event_is_read(event):
            continue
        for target in event.get("target_files", []):
            reads[str(target)] += 1
    candidates = [(path, count) for path, count in reads.items() if count >= 4]
    if not candidates:
        return None
    path, count = max(candidates, key=lambda item: item[1])
    return {"path": path, "count": count}


def event_is_read(event: dict[str, Any]) -> bool:
    tool = str(event.get("tool", "")).lower()
    category = event.get("command_category")
    return tool in {"read", "grep", "glob", "ls"} or category == "read"


def latest_validation(
    workflow_truth: dict[str, Any],
    events: list[dict[str, Any]],
) -> bool:
    if workflow_truth.get("verification_records"):
        return True
    return any(
        event.get("command_category") == "test" and event.get("status") == "pass"
        for event in events
    )


def highest_risk(signals: list[dict[str, Any]]) -> str:
    if not signals:
        return "low"
    return max(
        (str(item.get("severity", "low")) for item in signals),
        key=lambda value: RISK_ORDER.get(value, 0),
    )


def decision_for(risk: str, signals: list[dict[str, Any]]) -> str:
    signal_ids = {item["id"] for item in signals}
    if "compact_pending" in signal_ids:
        return "checkpoint_compact"
    if risk == "critical":
        return "checkpoint_new_thread"
    if risk == "high":
        return "checkpoint_compact"
    if risk == "medium":
        return "reconcile"
    return "continue"


def score_for(signals: list[dict[str, Any]]) -> int:
    weights = {"low": 10, "medium": 40, "high": 70, "critical": 90}
    return min(
        100,
        sum(weights.get(str(signal.get("severity")), 0) for signal in signals),
    )


def confidence_for(
    events: list[dict[str, Any]],
    options: dict[str, Any],
) -> str:
    unknown_count = len(unknown_metrics(events, options))
    if unknown_count >= 4:
        return "low"
    if unknown_count or not events:
        return "medium"
    return "high"


def unknown_metrics(
    events: list[dict[str, Any]],
    options: dict[str, Any],
) -> list[str]:
    unknown = []
    if "context_usage_pct" not in options:
        unknown.append("context_usage_pct")
    if not events:
        unknown.extend([
            "tool_error_rate",
            "same_command_retry_count",
            "same_file_read_count",
        ])
    if "user_correction_count" not in options:
        unknown.append("user_correction_count")
    return sorted(set(unknown))
