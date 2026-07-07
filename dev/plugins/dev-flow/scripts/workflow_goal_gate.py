from __future__ import annotations

from typing import Any


GOAL_REQUIRED_THRESHOLD = 3

COMPLEXITY_SIGNALS: tuple[tuple[str, int, str], ...] = (
    ("multiple_open_spec_changes", 2, "multiple OpenSpec changes"),
    ("multiple_capability_slices", 2, "multiple capability slices"),
    ("long_running_language", 2, "long-running execution language"),
    ("governed_surface", 1, "governed implementation surface"),
    ("archive_or_release_gate", 1, "archive or release gate"),
    ("resume_or_compaction", 1, "resume or context-compaction risk"),
)

LONG_RUNNING_MARKERS = (
    "依次",
    "持续",
    "直到需要人工介入",
    "完整实现",
    "完整推进",
    "continue until",
    "until human",
    "long-running",
)

GOVERNED_MARKERS = (
    "persistence",
    "data model",
    "integration",
    "migration",
    "ai",
    "api",
    "持久化",
    "数据模型",
    "集成",
    "迁移",
    "平台采集",
)


def goal_gate_warning(state: dict[str, Any]) -> str | None:
    gate = state.get("goal_gate")
    if not isinstance(gate, dict) or not bool(gate.get("required")):
        return None

    context_health = state.get("context_health", {})
    goal_summary = str(context_health.get("goal_summary", "none")).strip()
    gate_status = str(gate.get("status", "missing")).strip()
    active_goal_recorded = goal_summary not in ("", "none", "unknown") or gate_status in (
        "active",
        "skipped-with-reason",
    )
    if active_goal_recorded:
        return None

    reason = str(gate.get("reason", "unspecified")).strip() or "unspecified"
    suggested = str(gate.get("suggested_goal", "")).strip()
    suffix = f"; suggested {suggested}" if suggested else ""
    return f"Goal Suitability Gate requires an active goal or explicit skip: {reason}{suffix}"


def goal_complexity_score(
    *,
    open_spec_changes: int = 0,
    capability_slices: int = 0,
    prompt_text: str = "",
    governed_surfaces: list[str] | None = None,
    archive_or_release_gate: bool = False,
    resume_or_compaction: bool = False,
) -> dict[str, Any]:
    normalized_prompt = prompt_text.lower()
    normalized_surfaces = {surface.lower() for surface in governed_surfaces or []}
    matched: list[dict[str, Any]] = []

    if open_spec_changes > 1:
        matched.append(_signal("multiple_open_spec_changes"))
    if capability_slices > 1:
        matched.append(_signal("multiple_capability_slices"))
    if any(marker in normalized_prompt for marker in LONG_RUNNING_MARKERS):
        matched.append(_signal("long_running_language"))
    if normalized_surfaces or any(marker in normalized_prompt for marker in GOVERNED_MARKERS):
        matched.append(_signal("governed_surface"))
    if archive_or_release_gate:
        matched.append(_signal("archive_or_release_gate"))
    if resume_or_compaction:
        matched.append(_signal("resume_or_compaction"))

    score = sum(signal["points"] for signal in matched)
    required = score >= GOAL_REQUIRED_THRESHOLD
    recommended = 0 < score < GOAL_REQUIRED_THRESHOLD
    return {
        "required": required,
        "recommended": recommended,
        "score": score,
        "threshold": GOAL_REQUIRED_THRESHOLD,
        "signals": matched,
        "status": "required" if required else "recommended" if recommended else "not_required",
    }


def _signal(signal_id: str) -> dict[str, Any]:
    for candidate_id, points, label in COMPLEXITY_SIGNALS:
        if candidate_id == signal_id:
            return {"id": candidate_id, "points": points, "label": label}
    raise ValueError(f"Unknown goal gate signal: {signal_id}")
