from __future__ import annotations

from typing import Any


def build_governance(inputs: dict[str, Any]) -> dict[str, Any]:
    budget = inputs.get("budget") or {}
    config_audit = inputs.get("config_audit") or {}
    inventory = config_audit.get("inventory") or {}
    categories = collect_categories(budget)
    top_offenders = budget.get("top_offenders") or []

    recommendations: list[dict[str, Any]] = []
    recommendations.extend(build_profile_recommendations(categories, top_offenders, inventory))
    recommendations.extend(build_agents_recommendations(categories, top_offenders, inventory))
    recommendations.extend(build_skill_recommendations(categories, top_offenders, inventory))
    recommendations.extend(build_mcp_recommendations(categories, top_offenders, inventory))
    recommendations.extend(build_hook_recommendations(categories, top_offenders, inventory))
    recommendations.extend(build_command_recommendations(categories, top_offenders))

    return {
        "status": "advisory",
        "mutates_files": False,
        "recommendations": recommendations,
        "profile_suggestions": by_surface(recommendations, "profiles"),
        "agents_suggestions": by_surface(recommendations, "agents"),
        "skill_suggestions": by_surface(recommendations, "skills"),
        "mcp_suggestions": by_surface(recommendations, "mcp"),
        "hook_suggestions": by_surface(recommendations, "hooks"),
        "command_output_suggestions": by_surface(recommendations, "commands"),
    }


def collect_categories(budget: dict[str, Any]) -> dict[str, dict[str, Any]]:
    categories: dict[str, dict[str, Any]] = {}
    for section_name in ("baseline", "session_growth", "request_composition"):
        section = budget.get(section_name) or {}
        for category in section.get("categories") or []:
            name = str(category.get("category") or "unknown")
            current = categories.setdefault(
                name,
                {
                    "category": name,
                    "estimated_tokens": 0,
                    "count": 0,
                    "sections": [],
                    "items": [],
                },
            )
            current["estimated_tokens"] += int(category.get("estimated_tokens") or 0)
            current["count"] += int(category.get("count") or 0)
            current["sections"].append(section_name)
            current["items"].extend(category.get("items") or [])
    return categories


def build_profile_recommendations(
    categories: dict[str, dict[str, Any]], top_offenders: list[dict[str, Any]], inventory: dict[str, Any]
) -> list[dict[str, Any]]:
    if not has_any(categories, {"mcp_schema", "request_tool_schema"}) and not inventory.get("mcp_servers"):
        return []
    return [
        recommendation(
            surface="profiles",
            priority="P1",
            title="Profile suggestions for heavy tools",
            reason="MCP or request tool definitions add always-on or request-level context pressure.",
            action="Keep the default profile light; move research/design MCP servers into named profiles and enable only the tools needed for that task.",
            evidence=evidence_for(categories, top_offenders, {"mcp_schema", "request_tool_schema"}),
            snippet='[profiles.light]\n# keep heavy MCP disabled by default\n\n[profiles.research]\n# enable research MCP servers only for research tasks',
        )
    ]


def build_agents_recommendations(
    categories: dict[str, dict[str, Any]], top_offenders: list[dict[str, Any]], inventory: dict[str, Any]
) -> list[dict[str, Any]]:
    if not has_any(categories, {"project_agents", "global_agents", "nested_agents"}) and not inventory.get("instruction_chain_truncated"):
        return []
    return [
        recommendation(
            surface="agents",
            priority="P1" if inventory.get("instruction_chain_truncated") else "P2",
            title="AGENTS slimming",
            reason="Instruction files contribute baseline context and may be truncated when they exceed the configured budget.",
            action="Keep hard rules and routing in AGENTS.md; move long workflows, examples, and rare procedures into Skills or docs.",
            evidence=evidence_for(categories, top_offenders, {"project_agents", "global_agents", "nested_agents"}),
        )
    ]


def build_skill_recommendations(
    categories: dict[str, dict[str, Any]], top_offenders: list[dict[str, Any]], inventory: dict[str, Any]
) -> list[dict[str, Any]]:
    if not categories.get("skill_metadata") and not inventory.get("global_skills") and not inventory.get("project_skills"):
        return []
    return [
        recommendation(
            surface="skills",
            priority="P2",
            title="Skill locality review",
            reason="Skill metadata is available as context before full skill instructions are loaded.",
            action="Keep only high-frequency skills global and move project-specific workflow guidance into project-local skills.",
            evidence=evidence_for(categories, top_offenders, {"skill_metadata"}),
        )
    ]


def build_mcp_recommendations(
    categories: dict[str, dict[str, Any]], top_offenders: list[dict[str, Any]], inventory: dict[str, Any]
) -> list[dict[str, Any]]:
    if not has_any(categories, {"mcp_schema", "request_tool_schema"}) and not inventory.get("mcp_servers") and not inventory.get("project_mcp_servers"):
        return []
    return [
        recommendation(
            surface="mcp",
            priority="P1",
            title="MCP profile governance",
            reason="MCP inventory and request tool schemas can become top context offenders.",
            action="Disable low-frequency MCP servers in the default profile and use profile-specific allowlists for research, design, or repository work.",
            evidence=evidence_for(categories, top_offenders, {"mcp_schema", "request_tool_schema"}),
            snippet='[mcp_servers.example]\nenabled = false\n# enable in a task-specific profile when needed',
        )
    ]


def build_hook_recommendations(
    categories: dict[str, dict[str, Any]], top_offenders: list[dict[str, Any]], inventory: dict[str, Any]
) -> list[dict[str, Any]]:
    if not categories.get("hooks_context"):
        return []
    return [
        recommendation(
            surface="hooks",
            priority="P2",
            title="Hook output guardrails",
            reason="Hook configuration is present and should stay metadata-only to avoid adding context noise.",
            action="Keep hook output short and use Context Fixer hook records for size/hash evidence instead of replaying full payloads.",
            evidence=evidence_for(categories, top_offenders, {"hooks_context"}),
        )
    ]


def build_command_recommendations(categories: dict[str, dict[str, Any]], top_offenders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not has_any(categories, {"bash_output", "patch_diff", "file_content"}):
        return []
    return [
        recommendation(
            surface="commands",
            priority="P1",
            title="Command output policy",
            reason="Runtime command output, diffs, or file reads are contributing to session growth.",
            action="Prefer targeted commands such as `tail -n 120`, path-limited `rg`, failure-only test reporters, or RTK-style summarization for large outputs.",
            evidence=evidence_for(categories, top_offenders, {"bash_output", "patch_diff", "file_content"}),
        )
    ]


def recommendation(
    *,
    surface: str,
    priority: str,
    title: str,
    reason: str,
    action: str,
    evidence: dict[str, Any],
    snippet: str | None = None,
) -> dict[str, Any]:
    result = {
        "surface": surface,
        "priority": priority,
        "title": title,
        "reason": reason,
        "action": action,
        "evidence": evidence,
        "applied": False,
    }
    if snippet:
        result["snippet"] = snippet
    return result


def has_any(categories: dict[str, dict[str, Any]], names: set[str]) -> bool:
    return any(name in categories for name in names)


def evidence_for(categories: dict[str, dict[str, Any]], top_offenders: list[dict[str, Any]], names: set[str]) -> dict[str, Any]:
    matching_offender = next((item for item in top_offenders if item.get("category") in names), None)
    matching_category = next((categories[name] for name in names if name in categories), None)
    if matching_offender:
        return {
            "section": matching_offender.get("evidence", {}).get("section", "top_offenders"),
            "category": matching_offender.get("category"),
            "label": matching_offender.get("label"),
            "estimated_tokens": matching_offender.get("estimated_tokens", 0),
            "path": matching_offender.get("path"),
        }
    if matching_category:
        return {
            "section": ",".join(sorted(set(matching_category.get("sections") or []))),
            "category": matching_category.get("category"),
            "estimated_tokens": matching_category.get("estimated_tokens", 0),
            "count": matching_category.get("count", 0),
        }
    return {"section": "config_audit", "category": sorted(names)[0], "estimated_tokens": 0}


def by_surface(recommendations: list[dict[str, Any]], surface: str) -> list[dict[str, Any]]:
    return [item for item in recommendations if item.get("surface") == surface]
