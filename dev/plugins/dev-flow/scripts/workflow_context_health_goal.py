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
    elif weak_goal_summary(summary):
        status = "weak"
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


def weak_goal_summary(summary: str) -> bool:
    normalized = " ".join(summary.strip().lower().split())
    if normalized in {
        "make progress",
        "keep investigating",
        "improve things",
        "continue work",
        "continue working",
        "work on it",
        "work on this",
    }:
        return True
    return normalized.startswith("work on ") and len(normalized.split()) <= 4


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
    scope = options.get("scope") or [
        "Use DevFlow artifacts for workflow state, ledgers, checkpoints, and verification evidence.",
        "Use define-goal for goal creation, goal refinement, and active goal checks.",
        "Apply the Goal Suitability Gate before context-health drift appears.",
    ]
    non_goals = options.get("non_goals") or [
        "Do not create duplicate goals.",
        "Do not force a goal for ordinary narrow implementation solely because it has multiple steps.",
        "Do not claim hooks or scripts create goals automatically.",
    ]
    goal_handoff = [
        "Apply the Goal Suitability Gate before context-health drift appears.",
        (
            "Use a goal for long-running, multi-slice, migration, release, broad-refactor, "
            "cross-context, subagent/delegation, or high definition-of-done drift risk."
        ),
        "Use `define-goal` before goal-backed execution.",
        "Let `define-goal` inspect the active goal before creating a new goal.",
        "The objective must include verification evidence, scope boundaries, and stop conditions.",
    ]
    goal_command_flow = [
        "After `define-goal` shapes the objective, set it with `/goal <objective>`.",
        "Use `/goal` to view the active goal.",
        "Use `/goal pause`, `/goal resume`, or `/goal clear` to control the active goal.",
        "If `/goal` is unavailable, enable `features.goals` or run `codex features enable goals`.",
        "Do not use a top-level CLI `goal` subcommand; Goal Mode is an interactive slash command.",
    ]
    if status == "weak":
        goal_handoff.append("Use `define-goal` to repair the weak activity goal before treating it as complete.")
    return "\n".join(
        [
            "# Goal Mode Prompt",
            "",
            "Define-Goal Handoff:",
            *[f"- {item}" for item in goal_handoff],
            "",
            "Goal Slash Command:",
            *[f"- {item}" for item in goal_command_flow],
            "",
            f"Objective: {objective}",
            "",
            "Completion Contract:",
            "- Context health checks run and produce a grounded report.",
            "- High or Critical risks route to reconciliation, checkpoint, compact, or new-thread handoff.",
            "- Goal-backed work has a concrete objective with verification evidence.",
            "",
            "Scope:",
            *[f"- {item}" for item in scope],
            "",
            "Non-Goals:",
            *[f"- {item}" for item in non_goals],
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
