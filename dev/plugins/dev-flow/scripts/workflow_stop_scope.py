from __future__ import annotations

from typing import Any


def stop_hook_scope(payload: dict[str, Any]) -> dict[str, object]:
    if payload.get("stop_hook_active") is True:
        return {
            "enforce": False,
            "status": "already_continued",
            "detail": "Codex already continued this turn from a Stop decision",
        }
    if "transcript_path" in payload and payload.get("transcript_path") is None:
        return {
            "enforce": False,
            "status": "ephemeral_transcript",
            "detail": "ephemeral conversations do not own durable repository continuation",
        }
    if payload.get("transcript_path"):
        return {
            "enforce": True,
            "status": "durable_transcript",
            "detail": "durable conversation is eligible for repository continuation checks",
        }
    return {
        "enforce": True,
        "status": "legacy_payload",
        "detail": "legacy or unscoped payload preserves existing continuation checks",
    }


def stop_hook_protocol_check() -> dict[str, object]:
    examples = (
        (
            "already_continued",
            {"stop_hook_active": True, "transcript_path": "/tmp/rollout.jsonl"},
            False,
        ),
        (
            "ephemeral_transcript",
            {"stop_hook_active": False, "transcript_path": None},
            False,
        ),
        (
            "durable_transcript",
            {"stop_hook_active": False, "transcript_path": "/tmp/rollout.jsonl"},
            True,
        ),
        ("legacy_payload", {"stop_hook_active": False}, True),
    )
    cases = []
    for case_id, payload, expected in examples:
        result = stop_hook_scope(payload)
        enforce = bool(result["enforce"])
        matches = enforce is expected and result["status"] == case_id
        cases.append(
            {
                "id": case_id,
                "ok": matches,
                "enforce": enforce,
                "expected": expected,
                "status": result["status"],
            }
        )
    issues = [
        f"Stop-hook scope invariant failed: {case['id']}"
        for case in cases
        if not case["ok"]
    ]
    return {
        "ok": not issues,
        "status": "ready" if not issues else "needs_repair",
        "cases": cases,
        "issues": issues,
    }
