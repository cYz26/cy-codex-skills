from __future__ import annotations

from typing import Any

from .session import Contributor


def build_budget(
    *,
    baseline_contributors: list[Contributor],
    session_contributors: list[Contributor],
    request_contributors: list[Contributor],
    all_contributors: list[Contributor],
    session_stats: list[Any],
    trace_stats: list[Any],
    timeline: dict[str, Any],
    diagnosis: dict[str, Any],
    context_policy: dict[str, Any],
    compression_recommendations: list[dict[str, Any]],
) -> dict[str, Any]:
    top_offenders = build_top_offenders(all_contributors)
    return {
        "baseline": build_section("baseline", baseline_contributors),
        "session_growth": build_section("session_growth", session_contributors),
        "turn_deltas": build_turn_deltas(timeline),
        "request_composition": build_request_composition(request_contributors, trace_stats),
        "top_offenders": top_offenders,
        "recommendations": build_budget_recommendations(compression_recommendations, top_offenders, diagnosis, context_policy),
    }


def build_section(name: str, contributors: list[Contributor]) -> dict[str, Any]:
    categories = aggregate_categories(contributors)
    total_tokens = sum(item["estimated_tokens"] for item in categories)
    total_bytes = sum(item["bytes"] for item in categories)
    return {
        "name": name,
        "total_estimated_tokens": total_tokens,
        "total_bytes": total_bytes,
        "risk": risk_for_tokens(total_tokens),
        "categories": categories,
    }


def build_request_composition(contributors: list[Contributor], trace_stats: list[Any]) -> dict[str, Any]:
    section = build_section("request_composition", contributors)
    section.update(
        {
            "status": "enabled" if trace_stats else "not_provided",
            "files": len(trace_stats),
            "events": sum(int(getattr(stats, "events", 0) or 0) for stats in trace_stats),
            "exact_usage_events": sum(int(getattr(stats, "exact_usage_events", 0) or 0) for stats in trace_stats),
            "last_input_tokens": next((int(getattr(stats, "last_input_tokens", 0) or 0) for stats in reversed(trace_stats) if getattr(stats, "last_input_tokens", 0)), 0),
            "last_total_tokens": next((int(getattr(stats, "last_total_tokens", 0) or 0) for stats in reversed(trace_stats) if getattr(stats, "last_total_tokens", 0)), 0),
            "requests": [request_summary(stats) for stats in trace_stats],
        }
    )
    return section


def request_summary(stats: Any) -> dict[str, Any]:
    return {
        "path": str(getattr(stats, "path", "")),
        "trace_format": getattr(stats, "trace_format", None),
        "transport": getattr(stats, "transport", None),
        "request_path": getattr(stats, "request_path", None),
        "request_method": getattr(stats, "request_method", None),
        "model": getattr(stats, "model", None),
        "status": getattr(stats, "status", None),
        "last_input_tokens": int(getattr(stats, "last_input_tokens", 0) or 0),
        "last_total_tokens": int(getattr(stats, "last_total_tokens", 0) or 0),
        "exact_usage_events": int(getattr(stats, "exact_usage_events", 0) or 0),
    }


def aggregate_categories(contributors: list[Contributor]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for contributor in contributors:
        category = category_for(contributor)
        item = grouped.setdefault(
            category,
            {
                "category": category,
                "estimated_tokens": 0,
                "bytes": 0,
                "count": 0,
                "items": [],
            },
        )
        item["estimated_tokens"] += int(contributor.estimated_tokens or 0)
        item["bytes"] += int(contributor.bytes or 0)
        item["count"] += 1
        item["items"].append(contributor_item(contributor, category))
    for item in grouped.values():
        item["risk"] = risk_for_tokens(item["estimated_tokens"])
        item["items"] = sorted(item["items"], key=lambda entry: int(entry["estimated_tokens"] or 0), reverse=True)[:20]
    return sorted(grouped.values(), key=lambda item: int(item["estimated_tokens"] or 0), reverse=True)


def contributor_item(contributor: Contributor, category: str) -> dict[str, Any]:
    data = {
        "label": contributor.label,
        "kind": contributor.kind,
        "scope": contributor.scope,
        "category": category,
        "estimated_tokens": contributor.estimated_tokens,
        "bytes": contributor.bytes,
        "confidence": contributor.confidence,
    }
    if contributor.path:
        data["path"] = contributor.path
    if contributor.note:
        data["note"] = contributor.note
    return data


def build_turn_deltas(timeline: dict[str, Any]) -> list[dict[str, Any]]:
    results = []
    for event in timeline.get("growth_events") or []:
        delta = int(event.get("delta_input_tokens") or 0)
        if delta <= 0:
            continue
        results.append(
            {
                "source": event.get("source"),
                "timestamp": event.get("timestamp"),
                "path": event.get("path"),
                "from_input_tokens": int(event.get("from_input_tokens") or 0),
                "to_input_tokens": int(event.get("to_input_tokens") or 0),
                "delta_input_tokens": delta,
                "estimated_tokens": delta,
                "evidence": {"section": "timeline", "kind": "token_count_growth"},
            }
        )
    return sorted(results, key=lambda item: item["delta_input_tokens"], reverse=True)[:20]


def build_top_offenders(contributors: list[Contributor]) -> list[dict[str, Any]]:
    offenders = []
    for rank, contributor in enumerate(sorted(contributors, key=lambda item: int(item.estimated_tokens or 0), reverse=True)[:20], start=1):
        category = category_for(contributor)
        item = contributor_item(contributor, category)
        item.update(
            {
                "rank": rank,
                "evidence": {
                    "section": section_for_scope(contributor.scope),
                    "category": category,
                    "label": contributor.label,
                    "path": contributor.path,
                },
            }
        )
        offenders.append(item)
    return offenders


def build_budget_recommendations(
    compression_recommendations: list[dict[str, Any]],
    top_offenders: list[dict[str, Any]],
    diagnosis: dict[str, Any],
    context_policy: dict[str, Any],
) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    for recommendation in compression_recommendations:
        copied = dict(recommendation)
        copied.setdefault(
            "evidence",
            {
                "section": "compression",
                "severity": diagnosis.get("severity"),
                "policy_status": context_policy.get("status"),
            },
        )
        recommendations.append(copied)
    seen_titles = {item.get("title") for item in recommendations}
    for offender in top_offenders[:8]:
        category = offender["category"]
        generated = recommendation_for_category(category, offender)
        if generated and generated["title"] not in seen_titles:
            seen_titles.add(generated["title"])
            recommendations.append(generated)
    return recommendations


def recommendation_for_category(category: str, offender: dict[str, Any]) -> dict[str, Any] | None:
    templates = {
        "project_agents": (
            "Slim project AGENTS.md",
            "Move long workflow prose, examples, and low-frequency procedures into project skills or docs.",
        ),
        "global_agents": (
            "Keep global AGENTS.md minimal",
            "Leave only global hard rules in the global instruction file and move project-specific process into the repository.",
        ),
        "skill_metadata": (
            "Audit enabled skills",
            "Keep high-frequency skills globally available and move project-specific skills into the repository.",
        ),
        "mcp_schema": (
            "Move heavy MCP servers behind profiles",
            "Disable low-frequency MCP servers by default or use allowlists/profiles for research-heavy work.",
        ),
        "bash_output": (
            "Limit command output in future turns",
            "Use targeted commands, failure-only reporters, or tail/RTK-style summarization for large shell output.",
        ),
        "patch_diff": (
            "Checkpoint after large diffs",
            "Use diff stats or path-limited diffs unless the full patch is needed in the next turn.",
        ),
        "file_content": (
            "Read narrower file ranges",
            "Use targeted excerpts and directory indexes instead of repeatedly loading full files.",
        ),
        "request_tool_schema": (
            "Review request tool definitions",
            "Use request trace evidence to identify large tool schemas and move rarely used tools out of the default profile.",
        ),
    }
    if category not in templates:
        return None
    title, action = templates[category]
    return {
        "priority": "P1" if category in {"bash_output", "mcp_schema", "patch_diff"} else "P2",
        "title": title,
        "reason": f"{offender['label']} contributes an estimated {offender['estimated_tokens']} tokens.",
        "action": action,
        "evidence": offender.get("evidence", {"section": "top_offenders", "category": category}),
    }


def category_for(contributor: Contributor) -> str:
    if contributor.source_category:
        return contributor.source_category
    if contributor.scope == "request_trace":
        return {
            "request_instructions": "request_instructions",
            "request_messages": "request_messages",
            "request_tool_definitions": "request_tool_schema",
            "request_tool_results": "request_tool_results",
        }.get(contributor.kind, contributor.kind)
    if contributor.kind == "agents":
        if contributor.scope == "global":
            return "global_agents"
        if contributor.path and "/" in contributor.path:
            return "nested_agents"
        return "project_agents"
    return {
        "skill_metadata": "skill_metadata",
        "mcp_schema": "mcp_schema",
        "hooks": "hooks_context",
        "config": "codex_config",
        "workflow_state": "workflow_context",
        "workflow_config": "workflow_context",
        "legacy_ai_config": "legacy_ai_config",
        "conversation": "conversation_history",
        "tool_arguments": "tool_call_args",
        "tool_output": "tool_result",
        "base_instructions": "system_internal",
        "developer_instructions": "developer_instructions",
        "conversation_summary": "conversation_summary",
        "dynamic_tools": "request_tool_schema",
    }.get(contributor.kind, contributor.kind)


def section_for_scope(scope: str) -> str:
    if scope == "request_trace":
        return "request_composition"
    if scope in {"runtime", "session", "turn"}:
        return "session_growth"
    return "baseline"


def risk_for_tokens(tokens: int) -> str:
    if tokens >= 20000:
        return "high"
    if tokens >= 8000:
        return "medium"
    return "low"
