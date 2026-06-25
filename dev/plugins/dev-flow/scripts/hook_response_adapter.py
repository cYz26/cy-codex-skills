from __future__ import annotations

from typing import Any


def advisory(event_name: str, message: str, diagnostic: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "additionalContext": message,
            "diagnostic": diagnostic or {},
        }
    }


def deny_pre_tool_use(message: str, diagnostic: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "decision": "deny",
        "reason": message,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "additionalContext": message,
            "diagnostic": diagnostic or {},
        },
    }


def block_stop_continue(message: str, diagnostic: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"decision": "block", "reason": message, "diagnostic": diagnostic or {}}


def permission_request_deny(message: str) -> dict[str, Any]:
    return {"decision": "deny", "reason": message}
