from __future__ import annotations

from typing import Any


def goal_report(
    state: dict[str, Any],
    options: dict[str, Any],
    repo_truth: dict[str, Any],
) -> dict[str, Any]:
    context_health = state.get("context_health", {})
    summary = str(
        options.get("goal_summary")
        or context_health.get("goal_summary")
        or ""
    ).strip()
    if summary in {"", "none", "unknown"}:
        status = "missing" if options.get("current_objective") else "unknown"
    elif options.get("current_objective") and summary not in str(options.get("current_objective")):
        status = "stale"
    else:
        status = "aligned"
    if options.get("goal_conflicts"):
        status = "conflicting"
    return {
        "status": status,
        "summary": summary or "none",
        "prompt": goal_prompt(options, repo_truth, status),
    }


def goal_prompt(
    options: dict[str, Any],
    repo_truth: dict[str, Any],
    status: str,
) -> str:
    objective = options.get("current_objective") or "Continue the active DevFlow task."
    validation = options.get("validation_commands") or [
        "<run the smallest relevant validation command>",
    ]
    constraints = options.get("constraints") or [
        "Keep edits scoped to the active OpenSpec change.",
        "Do not store prompt bodies, file bodies, or command output bodies.",
        "Stop and reconcile if repo state conflicts with the goal.",
    ]
    changed_files = ", ".join(repo_truth.get("changed_files", [])) or "none"
    return "\n".join(
        [
            "# Goal Mode Prompt",
            "",
            f"Objective: {objective}",
            "",
            "Completion Contract:",
            "- Context health checks run and produce a grounded report.",
            "- High or Critical risks route to reconciliation, checkpoint, compact, or new-thread handoff.",
            "",
            "Constraints:",
            *[f"- {item}" for item in constraints],
            "",
            "Validation Commands:",
            *[f"- `{item}`" for item in validation],
            "",
            "Stop Conditions:",
            "- Stop when the Completion Contract is satisfied and validation evidence is recorded.",
            "- Stop early if goal status is conflicting or repo state drifts.",
            "",
            f"Current Goal Status: {status}",
            f"Current Changed Files: {changed_files}",
        ]
    )


def minimal_next_context(
    options: dict[str, Any],
    repo_truth: dict[str, Any],
    workflow_truth: dict[str, Any],
    goal: dict[str, Any],
) -> dict[str, Any]:
    latest_validation = workflow_truth.get("verification_records", [])[-1:] or [
        "not recorded",
    ]
    return {
        "objective": options.get("current_objective", "Continue active DevFlow task."),
        "changed_files": repo_truth.get("changed_files", []),
        "latest_validation": latest_validation,
        "goal_status": goal.get("status", "unknown"),
        "next_step": "Follow the context health decision before continuing implementation.",
    }
