from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .session import Contributor, discover_sessions, parse_session
from .static_sources import scan_codex_home, scan_project_sources
from .trace import parse_trace


def analyze_context(
    repo: Path | str | None = None,
    cwd: Path | str | None = None,
    codex_home: Path | str | None = None,
    sessions: list[Path | str] | None = None,
    traces: list[Path | str] | None = None,
    latest_sessions: int = 5,
) -> dict[str, Any]:
    repo_path = Path(repo).expanduser().resolve() if repo else None
    cwd_path = Path(cwd).expanduser().resolve() if cwd else repo_path
    codex_home_path = Path(codex_home).expanduser().resolve() if codex_home else Path.home() / ".codex"
    session_paths = [Path(path).expanduser().resolve() for path in sessions] if sessions else discover_sessions(codex_home_path, repo_path, latest_sessions)
    trace_paths = [Path(path).expanduser().resolve() for path in traces] if traces else []

    global_sources, global_inventory = scan_codex_home(codex_home_path)
    project_sources, project_inventory = scan_project_sources(
        repo_path,
        cwd_path,
        fallback_names=global_inventory.get("project_doc_fallback_filenames") or [],
        project_doc_max_bytes=global_inventory.get("project_doc_max_bytes"),
    )
    session_stats = [parse_session(path) for path in session_paths if path.exists()]
    trace_stats = [parse_trace(path) for path in trace_paths if path.exists()]
    contributors = project_sources + global_sources
    for stats in session_stats:
        contributors.extend(stats.contributors)
    for stats in trace_stats:
        contributors.extend(stats.contributors)

    timeline = build_timeline(session_stats, trace_stats)
    diagnosis = build_diagnosis(session_stats, trace_stats, timeline)
    config_audit = build_config_audit(project_inventory, global_inventory, project_sources)
    activity = build_activity(session_stats, trace_stats, config_audit)
    aggregated = aggregate_contributors(contributors)
    top = sorted((item.as_dict() for item in aggregated), key=lambda item: item["estimated_tokens"], reverse=True)[:20]
    data_sources = build_data_sources(session_stats, trace_stats)
    context_policy = build_context_policy(diagnosis)
    recommendations = build_recommendations(diagnosis, config_audit, top, data_sources, context_policy)
    return {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo": str(repo_path) if repo_path else None,
        "cwd": str(cwd_path) if cwd_path else None,
        "codex_home": str(codex_home_path),
        "sessions": [stats.as_dict() for stats in session_stats],
        "traces": [stats.as_dict() for stats in trace_stats],
        "data_sources": data_sources,
        "diagnosis": diagnosis,
        "timeline": timeline,
        "activity": activity,
        "context_policy": context_policy,
        "attribution": {
            "top_contributors": top,
            "static_total_estimated_tokens": sum(item.estimated_tokens for item in project_sources + global_sources),
            "runtime_total_estimated_tokens": sum(item.estimated_tokens for stats in session_stats for item in stats.contributors),
        },
        "config_audit": config_audit,
        "compression": {"recommendations": recommendations},
    }


def aggregate_contributors(contributors: list[Contributor]) -> list[Contributor]:
    grouped: dict[tuple[str, str, str, str | None], Contributor] = {}
    counts: dict[tuple[str, str, str, str | None], int] = {}
    for item in contributors:
        key = (item.label, item.kind, item.scope, item.path)
        if key not in grouped:
            grouped[key] = Contributor(item.label, item.kind, item.scope, 0, 0, item.confidence, path=item.path, note=item.note)
            counts[key] = 0
        grouped[key].estimated_tokens += item.estimated_tokens
        grouped[key].bytes += item.bytes
        counts[key] += 1
    for key, count in counts.items():
        if count > 1:
            grouped[key].note = f"aggregated from {count} records"
    return list(grouped.values())


def build_diagnosis(session_stats, trace_stats=None, timeline: dict[str, Any] | None = None) -> dict[str, Any]:
    trace_stats = trace_stats or []
    timeline = timeline or {}
    context_window = max((stats.model_context_window or 0 for stats in session_stats), default=0)
    trace_exact = latest_trace_with_usage(trace_stats)
    trace_pct = (trace_exact.max_input_tokens / context_window) if trace_exact and context_window else 0.0
    max_pct = max(max((stats.max_context_pct for stats in session_stats), default=0.0), trace_pct)
    max_input = max(
        max((stats.max_input_tokens for stats in session_stats), default=0),
        max((stats.max_input_tokens for stats in trace_stats), default=0),
    )
    max_total_input = max(
        max((stats.max_total_input_tokens for stats in session_stats), default=0),
        max((stats.max_total_input_tokens for stats in trace_stats), default=0),
    )
    context_window = max((stats.model_context_window or 0 for stats in session_stats), default=0)
    last = session_stats[0] if session_stats else None
    source_of_truth = "request_trace" if trace_exact else "session_jsonl" if last else "none"
    latest_input_tokens = trace_exact.last_input_tokens if trace_exact else last.last_input_tokens if last else 0
    latest_total_tokens = trace_exact.last_total_tokens if trace_exact else last.last_total_tokens if last else 0
    latest_cached_tokens = trace_exact.last_cached_input_tokens if trace_exact else last.last_cached_input_tokens if last else 0
    latest_output_tokens = trace_exact.last_output_tokens if trace_exact else last.last_output_tokens if last else 0
    latest_reasoning_tokens = trace_exact.last_reasoning_output_tokens if trace_exact else last.last_reasoning_output_tokens if last else 0
    cache_hit_pct = trace_exact.cache_hit_pct if trace_exact else last.cache_hit_pct if last else 0.0
    latest_valid = timeline.get("latest_valid_usage_event") or {}
    latest_valid_input = int(latest_valid.get("input_tokens") or 0)
    latest_valid_total = int(latest_valid.get("total_tokens") or 0)
    latest_valid_source = "request_trace" if latest_valid.get("source") == "request_trace" else "session_jsonl" if latest_valid else "none"
    severity = "low"
    if max_pct >= 0.9:
        severity = "critical"
    elif max_pct >= 0.75:
        severity = "high"
    elif max_pct >= 0.55:
        severity = "medium"
    findings = []
    if severity in {"critical", "high"}:
        findings.append({"level": severity, "message": f"Peak input reached {max_pct:.1%} of the model context window."})
    if sum(stats.compact_events for stats in session_stats):
        findings.append({"level": "info", "message": "Session history contains context compaction events."})
    if max_total_input and max_total_input >= 2 * max_input and max_input:
        findings.append({"level": "info", "message": "Accumulated input usage is much larger than the largest single-turn context load."})
    if trace_exact:
        findings.append({"level": "info", "message": "Request trace usage is available and is used as the highest-priority usage source."})
    if last and last.token_events and last.max_input_tokens == 0 and latest_valid_input:
        findings.append({"level": "warning", "message": "Latest session has zero token usage"})
    return {
        "severity": severity,
        "source_of_truth": source_of_truth,
        "context_window": context_window,
        "max_context_pct": max_pct,
        "max_input_tokens": max_input,
        "max_total_input_tokens": max_total_input,
        "headroom_tokens": max(context_window - max_input, 0) if context_window else 0,
        "last_input_tokens": latest_input_tokens,
        "last_total_tokens": latest_total_tokens,
        "last_cached_input_tokens": latest_cached_tokens,
        "last_output_tokens": latest_output_tokens,
        "last_reasoning_output_tokens": latest_reasoning_tokens,
        "latest_valid_input_tokens": latest_valid_input,
        "latest_valid_total_tokens": latest_valid_total,
        "latest_valid_source": latest_valid_source,
        "latest_valid_timestamp": latest_valid.get("timestamp"),
        "cache_hit_pct": cache_hit_pct,
        "token_events": sum(stats.token_events for stats in session_stats),
        "request_trace_events": sum(stats.events for stats in trace_stats),
        "request_trace_exact_usage_events": sum(stats.exact_usage_events for stats in trace_stats),
        "compact_events": sum(stats.compact_events for stats in session_stats),
        "findings": findings,
    }


def build_config_audit(project_inventory: dict[str, Any], global_inventory: dict[str, Any], project_sources: list[Contributor]) -> dict[str, Any]:
    findings = []
    if project_inventory.get("agents_files", 0) == 0:
        findings.append({"level": "warning", "message": "No project AGENTS.md was found."})
    if project_inventory.get("instruction_chain_truncated"):
        findings.append({"level": "warning", "message": "Project instruction chain exceeds project_doc_max_bytes and may be truncated."})
    if project_inventory.get("legacy_ai_files", 0):
        findings.append({"level": "info", "message": "Legacy AI instruction files are present; check for drift from AGENTS.md."})
    if project_inventory.get("project_mcp_servers", 0):
        findings.append({"level": "info", "message": "Project-scoped MCP servers are configured; verify they are needed for this repository."})
    if global_inventory.get("enabled_global_plugins", 0) >= 8:
        findings.append({"level": "warning", "message": "Many global plugins are enabled, increasing baseline context and tool inventory."})
    elif global_inventory.get("enabled_global_plugins", 0):
        findings.append({"level": "info", "message": "Global plugins are enabled; project-local activation may reduce baseline context."})
    if global_inventory.get("global_skills", 0):
        findings.append({"level": "warning", "message": "Global skills are present and may be loaded in unrelated projects."})
    for source in project_sources:
        if source.kind == "agents" and source.estimated_tokens > 2000:
            findings.append({"level": "warning", "message": f"{source.path} is large for an instruction file."})
    inventory = dict(global_inventory)
    inventory.update(project_inventory)
    return {
        "inventory": inventory,
        "instruction_chain": {
            "global": global_inventory.get("global_instruction_file"),
            "project": project_inventory.get("instruction_chain", []),
        },
        "findings": findings,
    }


def build_recommendations(
    diagnosis: dict[str, Any],
    config_audit: dict[str, Any],
    top_contributors: list[dict[str, Any]],
    data_sources: dict[str, Any] | None = None,
    context_policy: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    recommendations = []
    if diagnosis["severity"] == "critical":
        recommendations.append(
            {
                "priority": "P0",
                "title": "Compact before continuing substantial work",
                "reason": "Peak context usage is above 90%, so new evidence is at high risk of being truncated or diluted.",
                "action": "Create a durable checkpoint, then compact the session before the next implementation stage.",
            }
        )
    elif diagnosis["severity"] == "high":
        recommendations.append(
            {
                "priority": "P1",
                "title": "Plan a compaction boundary soon",
                "reason": "Peak context usage is above 75%.",
                "action": "Summarize decisions and verification evidence before the next major task.",
            }
        )
    if diagnosis.get("compact_events", 0):
        recommendations.append(
            {
                "priority": "P1",
                "title": "Create a durable checkpoint before compacting",
                "reason": "Compaction events are present, so important decisions may only exist in summarized form.",
                "action": "Save current goals, decisions, changed files, and verification evidence before relying on another compacted turn.",
            }
        )
    if (context_policy or {}).get("compact_recommended") and diagnosis["severity"] not in {"critical", "high"}:
        recommendations.append(
            {
                "priority": "P1",
                "title": "Compact according to context policy",
                "reason": f"Policy status is {(context_policy or {}).get('status')}, which crossed the compact threshold.",
                "action": "Checkpoint decisions, open risks, changed files, and verification evidence before compacting.",
            }
        )
    if diagnosis.get("cache_hit_pct", 1.0) < 0.15 and diagnosis.get("token_events", 0) >= 1:
        recommendations.append(
            {
                "priority": "P2",
                "title": "Stabilize recurring prompt inputs",
                "reason": "The latest cached input ratio is low.",
                "action": "Keep long-lived instructions stable and move volatile details into files read only when needed.",
            }
        )
    if (data_sources or {}).get("request_trace", {}).get("status") == "enabled":
        recommendations.append(
            {
                "priority": "P1",
                "title": "Inspect request trace contributors",
                "reason": "Request trace data is available, so request-only messages, tool schemas, and tool results can be checked with higher confidence.",
                "action": "Use the request_trace contributors as the source of truth for prompt shape and API usage, then compare against session-level estimates.",
            }
        )
    if diagnosis.get("last_input_tokens") == 0 and diagnosis.get("latest_valid_input_tokens", 0) > 0:
        recommendations.append(
            {
                "priority": "P1",
                "title": "Use the timeline before trusting the latest snapshot",
                "reason": "The latest raw session has zero token usage, but an earlier valid usage event exists.",
                "action": "Inspect the timeline peak and latest valid usage events to distinguish probe or interrupted sessions from real context pressure.",
            }
        )
    recommendations.extend(recommend_top_contributors(top_contributors))
    inventory = config_audit["inventory"]
    if inventory.get("instruction_chain_truncated"):
        recommendations.append(
            {
                "priority": "P1",
                "title": "Split or slim project instruction files",
                "reason": "The discovered project instruction chain exceeds the configured project_doc_max_bytes limit.",
                "action": "Move examples and long procedures into linked docs or narrower subdirectory AGENTS.md files.",
            }
        )
    if inventory.get("enabled_global_plugins", 0) or inventory.get("global_skills", 0):
        recommendations.append(
            {
                "priority": "P2",
                "title": "Audit global Codex activation",
                "reason": "Global plugins and skills add baseline context to every project.",
                "action": "Disable broad global tools where possible and install project-relevant skills locally.",
            }
        )
    return recommendations


def latest_trace_with_usage(trace_stats):
    for stats in reversed(trace_stats):
        if stats.exact_usage_events:
            return stats
    return None


def build_timeline(session_stats, trace_stats) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    for stats in session_stats:
        events.extend(copy_timeline_events(stats.timeline_events))
    for stats in trace_stats:
        events.extend(copy_timeline_events(stats.timeline_events))
    events = sorted(events, key=timeline_sort_key)

    usage_events = [event for event in events if int(event.get("input_tokens") or 0) > 0]
    peak_event = max(usage_events, key=lambda event: int(event.get("input_tokens") or 0), default=None)
    latest_valid_usage = usage_events[-1] if usage_events else None
    compactions = [event for event in events if event.get("kind") == "compaction"]
    anomalies = [event for event in events if event.get("kind") == "anomaly"]
    anomalies.extend(request_anomalies(events))
    growth_events = build_growth_events(events)

    return {
        "summary": {
            "total_events": len(events),
            "usage_events": len(usage_events),
            "request_events": sum(1 for event in events if event.get("source") == "request_trace"),
            "exact_usage_events": sum(1 for event in events if event.get("source") == "request_trace" and event.get("exact_usage")),
            "compaction_events": len(compactions),
            "anomaly_events": len(anomalies),
        },
        "peak_event": compact_event(peak_event),
        "latest_valid_usage_event": compact_event(latest_valid_usage),
        "growth_events": [compact_event(event) for event in growth_events[:10]],
        "compaction_events": [compact_event(event) for event in compactions[:20]],
        "anomalies": [compact_event(event) for event in anomalies[:20]],
        "events": [compact_event(event) for event in events[:200]],
    }


def build_activity(session_stats, trace_stats, config_audit: dict[str, Any]) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    for stats in session_stats:
        events.extend(copy_timeline_events(getattr(stats, "activity_events", [])))
    for stats in trace_stats:
        events.extend(copy_timeline_events(getattr(stats, "activity_events", [])))
    events = sorted(events, key=timeline_sort_key)
    observed_calls = aggregate_observed_calls(events)
    request_activity = [compact_activity_event(event) for event in events if event.get("kind") == "network_request"]
    available_tools = sorted(
        {
            str(name)
            for event in events
            if event.get("kind") in {"available_tools", "request_tool_inventory"}
            for name in event.get("tool_names", [])
            if name
        }
    )
    inventory = config_audit.get("inventory", {})
    activation_inventory = {
        "enabled_global_plugins": int(inventory.get("enabled_global_plugins") or 0),
        "enabled_global_plugin_keys": list(inventory.get("enabled_global_plugin_keys") or []),
        "global_skills": int(inventory.get("global_skills") or 0),
        "project_skills": int(inventory.get("project_skills") or 0),
        "mcp_servers": int(inventory.get("mcp_servers") or 0),
        "mcp_server_keys": list(inventory.get("mcp_server_keys") or []),
        "project_mcp_servers": int(inventory.get("project_mcp_servers") or 0),
    }
    return {
        "summary": {
            "observed_tool_calls": sum(1 for event in events if event.get("kind") == "tool_call"),
            "observed_tool_results": sum(1 for event in events if event.get("kind") == "tool_result"),
            "request_activity_events": len(request_activity),
            "request_tool_inventory_events": sum(1 for event in events if event.get("kind") == "request_tool_inventory"),
            "available_tools": len(available_tools),
            "enabled_global_plugins": activation_inventory["enabled_global_plugins"],
            "global_skills": activation_inventory["global_skills"],
            "project_skills": activation_inventory["project_skills"],
            "mcp_servers": activation_inventory["mcp_servers"],
        },
        "observed_calls": observed_calls,
        "request_activity": request_activity[:100],
        "available_tools": available_tools[:200],
        "activation_inventory": activation_inventory,
        "events": [compact_activity_event(event) for event in events[:300]],
    }


def aggregate_observed_calls(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for event in events:
        if event.get("kind") not in {"tool_call", "tool_result"}:
            continue
        name = str(event.get("name") or "unknown")
        item = grouped.setdefault(
            name,
            {
                "name": name,
                "call_count": 0,
                "result_count": 0,
                "argument_estimated_tokens": 0,
                "output_estimated_tokens": 0,
                "call_types": set(),
                "first_timestamp": event.get("timestamp"),
                "last_timestamp": event.get("timestamp"),
            },
        )
        if event.get("kind") == "tool_call":
            item["call_count"] += 1
            item["argument_estimated_tokens"] += int(event.get("argument_estimated_tokens") or 0)
        if event.get("kind") == "tool_result":
            item["result_count"] += 1
            item["output_estimated_tokens"] += int(event.get("output_estimated_tokens") or 0)
        if event.get("call_type"):
            item["call_types"].add(str(event.get("call_type")))
        timestamp = event.get("timestamp")
        if timestamp:
            item["last_timestamp"] = timestamp
            if not item.get("first_timestamp"):
                item["first_timestamp"] = timestamp
    results = []
    for item in grouped.values():
        item["call_types"] = sorted(item["call_types"])
        results.append(item)
    return sorted(results, key=lambda item: (item["call_count"] + item["result_count"], item["output_estimated_tokens"]), reverse=True)


def compact_activity_event(event: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "source",
        "kind",
        "category",
        "timestamp",
        "path",
        "file",
        "order",
        "name",
        "call_type",
        "argument_estimated_tokens",
        "output_estimated_tokens",
        "status",
        "method",
        "model",
        "latency_ms",
        "exact_usage",
        "tool_names",
        "tool_count",
    }
    return {key: value for key, value in event.items() if key in allowed and value not in (None, "")}


def copy_timeline_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(event) for event in events]


def build_growth_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_path: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        if event.get("kind") != "token_count":
            continue
        path = str(event.get("path") or event.get("file") or "")
        by_path.setdefault(path, []).append(event)
    growth = []
    for path, token_events in by_path.items():
        ordered = sorted(token_events, key=timeline_sort_key)
        previous = None
        for event in ordered:
            current = int(event.get("input_tokens") or 0)
            if previous is not None:
                delta = current - int(previous.get("input_tokens") or 0)
                if delta > 0:
                    growth.append(
                        {
                            "source": event.get("source"),
                            "kind": "growth",
                            "timestamp": event.get("timestamp"),
                            "path": path,
                            "from_input_tokens": int(previous.get("input_tokens") or 0),
                            "to_input_tokens": current,
                            "delta_input_tokens": delta,
                        }
                    )
            previous = event
    return sorted(growth, key=lambda event: int(event.get("delta_input_tokens") or 0), reverse=True)


def request_anomalies(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    anomalies = []
    for event in events:
        if event.get("source") != "request_trace":
            continue
        status = event.get("status")
        if isinstance(status, int) and status >= 400:
            anomalies.append(
                {
                    "source": "request_trace",
                    "kind": "anomaly",
                    "anomaly_type": "request_error",
                    "timestamp": event.get("timestamp"),
                    "path": event.get("path"),
                    "status": status,
                    "message": f"Request trace returned HTTP {status}.",
                }
            )
    return anomalies


def compact_event(event: dict[str, Any] | None) -> dict[str, Any] | None:
    if not event:
        return None
    allowed = {
        "source",
        "kind",
        "timestamp",
        "path",
        "file",
        "order",
        "input_tokens",
        "total_tokens",
        "cached_input_tokens",
        "output_tokens",
        "reasoning_output_tokens",
        "model_context_window",
        "context_pct",
        "input_tokens_before",
        "total_tokens_before",
        "from_input_tokens",
        "to_input_tokens",
        "delta_input_tokens",
        "anomaly_type",
        "message",
        "method",
        "model",
        "status",
        "latency_ms",
        "exact_usage",
        "trace_format",
        "transport",
    }
    return {key: value for key, value in event.items() if key in allowed and value not in (None, "")}


def timeline_sort_key(event: dict[str, Any]) -> tuple[str, str, int]:
    timestamp = str(event.get("timestamp") or "")
    parsed = parse_timestamp(timestamp)
    sortable_time = parsed.isoformat() if parsed else timestamp
    path = str(event.get("path") or event.get("file") or "")
    return (sortable_time, path, int(event.get("order") or 0))


def parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def build_data_sources(session_stats, trace_stats) -> dict[str, Any]:
    trace_events = sum(stats.events for stats in trace_stats)
    trace_exact = sum(stats.exact_usage_events for stats in trace_stats)
    return {
        "session_parser": {
            "status": "enabled" if session_stats else "missing",
            "files": len(session_stats),
            "token_events": sum(stats.token_events for stats in session_stats),
            "precision": "medium-high",
            "default": True,
        },
        "request_trace": {
            "status": "enabled" if trace_stats else "not_provided",
            "files": len(trace_stats),
            "events": trace_events,
            "exact_usage_events": trace_exact,
            "precision": "highest" if trace_exact else "estimated" if trace_stats else "unavailable",
            "opt_in": True,
        },
    }


def build_context_policy(diagnosis: dict[str, Any]) -> dict[str, Any]:
    warning_ratio = 0.60
    compact_ratio = 0.70
    hard_warning_ratio = 0.80
    used_ratio = float(diagnosis.get("max_context_pct") or 0.0)
    window = int(diagnosis.get("context_window") or 0)
    if used_ratio >= hard_warning_ratio:
        status = "red"
    elif used_ratio >= compact_ratio:
        status = "orange"
    elif used_ratio >= warning_ratio:
        status = "yellow"
    else:
        status = "green"
    compact_start = int(window * compact_ratio) if window else 0
    hard_start = int(window * hard_warning_ratio) if window else 0
    return {
        "profile": "standard_coding",
        "status": status,
        "used_percent": used_ratio,
        "warning_ratio": warning_ratio,
        "compact_ratio": compact_ratio,
        "hard_warning_ratio": hard_warning_ratio,
        "compact_recommended": used_ratio >= compact_ratio,
        "compact_range_tokens": [compact_start, hard_start] if window else [],
        "tool_output_token_limit": 8000,
    }


def recommend_top_contributors(top_contributors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recommendations = []
    for item in top_contributors[:5]:
        if item["kind"] == "tool_output" and item["estimated_tokens"] >= 10000:
            recommendations.append(
                {
                    "priority": "P1",
                    "title": f"Reduce large tool output from {item['label']}",
                    "reason": f"Estimated contribution is {item['estimated_tokens']} tokens.",
                    "action": "Save large outputs to files and read targeted excerpts instead of replaying full output into chat.",
                }
            )
        if item["kind"] == "agents" and item["estimated_tokens"] >= 2000:
            recommendations.append(
                {
                    "priority": "P2",
                    "title": "Slim AGENTS.md",
                    "reason": "Project instructions are large enough to materially affect every turn.",
                    "action": "Keep rules and routing in AGENTS.md; move examples and long procedures into linked docs.",
                }
            )
    return recommendations
