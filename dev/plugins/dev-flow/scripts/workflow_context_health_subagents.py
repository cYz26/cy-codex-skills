from __future__ import annotations

from typing import Any


ALLOWED_DISPOSITIONS = ["pending", "accepted", "declined", "superseded", "blocked"]
RESOLVED_DISPOSITIONS = {"accepted", "declined", "superseded", "blocked"}


def subagent_report(
    events: list[dict[str, Any]],
    signals: list[dict[str, Any]],
    options: dict[str, Any],
) -> dict[str, Any]:
    repeated_read = next((item for item in signals if item["id"] == "repeated_file_read"), None)
    repeated_failure = next(
        (item for item in signals if item["id"] == "repeated_command_failure"),
        None,
    )
    if repeated_read:
        path = repeated_read["evidence"].get("path", "relevant file")
        return recommendation_report(
            kind="explorer",
            signal_id="repeated_file_read",
            key=str(path),
            reason="Repeated file reads indicate investigation pressure in the main context.",
            scoped_files=[path],
            prompt=explorer_prompt(path, options),
            options=options,
        )
    if repeated_failure:
        command_hash = str(repeated_failure["evidence"].get("command_hash", "unknown-command"))
        return recommendation_report(
            kind="explorer",
            signal_id="repeated_command_failure",
            key=command_hash,
            reason="Repeated command failures may benefit from a second-opinion explorer.",
            scoped_files=[],
            prompt=explorer_prompt("the failing area", options),
            options=options,
        )
    return {
        "recommendation": "none",
        "reason": "No subagent trigger matched.",
        "scoped_files": [],
        "prompt": "",
        "recommendationId": "none",
        "dispositionRequired": False,
        "disposition": "not_applicable",
        "allowedDispositions": ALLOWED_DISPOSITIONS,
        "nextAction": "No subagent recommendation needs disposition.",
    }


def recommendation_report(
    *,
    kind: str,
    signal_id: str,
    key: str,
    reason: str,
    scoped_files: list[str],
    prompt: str,
    options: dict[str, Any],
) -> dict[str, Any]:
    recommendation_id = recommendation_key(kind, signal_id, key)
    disposition = disposition_for(recommendation_id, options)
    report = {
        "recommendation": kind,
        "reason": reason,
        "scoped_files": scoped_files,
        "prompt": prompt,
        "recommendationId": recommendation_id,
        "dispositionRequired": True,
        "disposition": disposition,
        "allowedDispositions": ALLOWED_DISPOSITIONS,
        "nextAction": next_action_for(recommendation_id, disposition),
    }
    note = disposition_note_for(recommendation_id, options)
    if note:
        report["dispositionNote"] = note
    return report


def recommendation_key(kind: str, signal_id: str, key: str) -> str:
    normalized = "-".join(str(key).strip().split()) or "unknown"
    return f"{kind}:{signal_id}:{normalized}"


def disposition_for(recommendation_id: str, options: dict[str, Any]) -> str:
    dispositions = options.get("subagent_dispositions", {})
    if not isinstance(dispositions, dict):
        return "pending"
    disposition = str(dispositions.get(recommendation_id, "")).strip().lower()
    if disposition in ALLOWED_DISPOSITIONS:
        return disposition
    return "pending"


def disposition_note_for(recommendation_id: str, options: dict[str, Any]) -> str:
    notes = options.get("subagent_disposition_notes", {})
    if not isinstance(notes, dict):
        return ""
    return str(notes.get(recommendation_id, "")).strip()


def next_action_for(recommendation_id: str, disposition: str) -> str:
    if disposition == "pending":
        return (
            f"Record a disposition for {recommendation_id}: accepted, declined, "
            "superseded, or blocked before treating this recommendation as handled."
        )
    if disposition == "accepted":
        return "Execute or review the accepted Agent Task Contract, then record main-agent verification."
    if disposition == "declined":
        return "Continue only if the decline reason explains why a subagent is not useful."
    if disposition == "superseded":
        return "Continue only if another action has resolved the investigation need."
    if disposition == "blocked":
        return "Wait for the missing user authorization or context before dispatching."
    return "No subagent recommendation needs disposition."


def pending_recommendation(report: dict[str, Any]) -> bool:
    return bool(report.get("dispositionRequired")) and report.get("disposition") == "pending"


def explorer_prompt(path: str, options: dict[str, Any]) -> str:
    objective = options.get("current_objective") or "Investigate the active task."
    return "\n".join(
        [
            "# Agent Task Contract",
            "",
            "## Goal",
            f"Complete a read-only explorer investigation for: {objective}",
            "",
            "## Scope",
            f"Allowed: inspect scoped files or areas related to {path}.",
            "Forbidden: Do not edit files, do not broaden scope, do not update workflow state, "
            "and do not change repository files.",
            "",
            "## Constraints",
            "Read-only explorer. Keep output concise, preserve privacy, and do not paste full logs.",
            "",
            "## Verification",
            "Not applicable: this is a read-only explorer task; verify by reporting inspected files "
            "and residual risks.",
            "",
            "## Evidence",
            "Report status, files changed or inspected, commands or tests run, test logs or "
            "validation results, unverified areas, risk notes, review needs, and recommended next action.",
            "",
            "## Human Gate",
            "Wait for main-agent review before editing files, expanding scope, touching forbidden files, "
            "or continuing with missing evidence.",
            "",
            "Output schema:",
            "- status: DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT, or BLOCKED",
            "- files changed or inspected",
            "- commands or tests run",
            "- test logs or validation results",
            "- unverified areas",
            "- residual risks",
            "- review needs",
            "- recommended next action",
            "Integration constraint: return a concise summary only; the main agent owns verification, "
            "workflow evidence, and final integration.",
        ]
    )
