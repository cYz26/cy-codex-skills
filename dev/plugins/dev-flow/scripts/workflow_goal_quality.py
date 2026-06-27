from __future__ import annotations

from typing import Any


WEAK_ACTIVITY_GOALS = {
    "make progress",
    "keep investigating",
    "improve things",
    "continue work",
    "continue working",
    "work on it",
    "work on this",
}


def goal_quality_report(objective: str) -> dict[str, Any]:
    text = " ".join(objective.strip().split())
    lowered = text.lower()
    checks = {
        "outcome": has_outcome(lowered),
        "verification_evidence": contains_any(
            lowered,
            [
                "verified by",
                "verify with",
                "verification",
                "evidence",
                "test",
                "unittest",
                "openspec",
                "plugin eval",
                "runtime verification",
            ],
        ),
        "scope_boundaries": contains_any(
            lowered,
            ["limited to", "scope", "only", "within", "under", "affected", "files"],
        ),
        "non_goals": contains_any(
            lowered,
            ["excluding", "without", "do not", "not touch", "out of scope", "non-goal"],
        ),
        "success_threshold": contains_any(
            lowered,
            [
                "exit 0",
                "exiting 0",
                "passes",
                "passing",
                "all commands",
                "no unresolved",
                "0 failures",
                "no failing",
                "threshold",
            ],
        ),
        "stop_conditions": contains_any(
            lowered,
            ["stop before", "stop and ask", "ask before", "wait for", "human", "stop if"],
        ),
    }
    missing = [name for name, ok in checks.items() if not ok]
    errors = [error_for(name) for name in missing]
    return {
        "ok": not missing,
        "objective": text,
        "checks": checks,
        "missing": missing,
        "errors": errors,
        "template": (
            "Achieve <outcome>, limited to <scope-in>, excluding <scope-out>, "
            "verified by <commands/evidence>, and stop before <human-gate conditions>."
        ),
    }


def has_outcome(text: str) -> bool:
    if not text or text in WEAK_ACTIVITY_GOALS:
        return False
    if text.startswith("work on ") and len(text.split()) <= 4:
        return False
    return len(text.split()) >= 8 and contains_any(
        text,
        ["implement", "add", "repair", "resolve", "complete", "deliver", "achieve", "reduce", "validate"],
    )


def contains_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def error_for(check: str) -> str:
    return {
        "outcome": "Objective must name a concrete outcome, not just activity.",
        "verification_evidence": "Objective must include verification evidence.",
        "scope_boundaries": "Objective must include scope boundaries.",
        "non_goals": "Objective must include non-goals or exclusions when scope matters.",
        "success_threshold": "Objective must include a pass/fail success threshold.",
        "stop_conditions": "Objective must include stop or human-review conditions.",
    }[check]
