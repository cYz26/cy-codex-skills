from __future__ import annotations

from typing import Any

from workflow_context_relevance import relevant_to_project


def add_source_recommendations(
    inventory: dict[str, Any],
    signals: list[str],
    recommendations: list[dict[str, Any]],
) -> None:
    for tool in inventory["sourceTools"]:
        if tool.get("error") or not relevant_to_project(tool, signals):
            continue
        name = tool.get("name", "unknown")
        tool_type = tool.get("type", "tool")
        recommendations.append(
            {
                "kind": "discovery",
                "actionId": None,
                "title": f"Consider {tool_type} {name}",
                "reason": f"Source catalog entry matches project signals: {', '.join(signals)}.",
            }
        )
