from __future__ import annotations

from typing import Any


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
        return {
            "recommendation": "explorer",
            "reason": "Repeated file reads indicate investigation pressure in the main context.",
            "scoped_files": [path],
            "prompt": explorer_prompt(path, options),
        }
    if repeated_failure:
        return {
            "recommendation": "explorer",
            "reason": "Repeated command failures may benefit from a second-opinion explorer.",
            "scoped_files": [],
            "prompt": explorer_prompt("the failing area", options),
        }
    return {
        "recommendation": "none",
        "reason": "No subagent trigger matched.",
        "scoped_files": [],
        "prompt": "",
    }


def explorer_prompt(path: str, options: dict[str, Any]) -> str:
    objective = options.get("current_objective") or "Investigate the active task."
    return "\n".join(
        [
            "Use an explorer subagent for a read-only investigation.",
            f"Objective: {objective}",
            f"Scoped files: {path}",
            "Non-goals: Do not edit files. Do not broaden scope.",
            "Output schema:",
            "- status: DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT, or BLOCKED",
            "- files changed or inspected",
            "- commands or tests run",
            "- residual risks",
            "- review needs",
            "- recommended next action",
            "Integration constraint: return a concise summary only; do not paste full logs.",
        ]
    )
