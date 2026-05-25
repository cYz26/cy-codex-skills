from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .session import Contributor
from .util import approx_tokens, json_size


@dataclass
class TraceStats:
    path: Path
    events: int = 0
    exact_usage_events: int = 0
    trace_format: str | None = None
    transport: str | None = None
    upstream_base_url: str | None = None
    request_path: str | None = None
    request_method: str | None = None
    model: str | None = None
    endpoint: str | None = None
    status: int | None = None
    latency_ms: int | None = None
    max_input_tokens: int = 0
    max_total_input_tokens: int = 0
    last_input_tokens: int = 0
    last_total_tokens: int = 0
    last_cached_input_tokens: int = 0
    last_output_tokens: int = 0
    last_reasoning_output_tokens: int = 0
    contributors: list[Contributor] = field(default_factory=list)
    timeline_events: list[dict[str, Any]] = field(default_factory=list)
    activity_events: list[dict[str, Any]] = field(default_factory=list)

    @property
    def cache_hit_pct(self) -> float:
        return self.last_cached_input_tokens / self.last_input_tokens if self.last_input_tokens else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "events": self.events,
            "exact_usage_events": self.exact_usage_events,
            "trace_format": self.trace_format,
            "transport": self.transport,
            "upstream_base_url": self.upstream_base_url,
            "request_path": self.request_path,
            "request_method": self.request_method,
            "model": self.model,
            "endpoint": self.endpoint,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "max_input_tokens": self.max_input_tokens,
            "max_total_input_tokens": self.max_total_input_tokens,
            "last_input_tokens": self.last_input_tokens,
            "last_total_tokens": self.last_total_tokens,
            "last_cached_input_tokens": self.last_cached_input_tokens,
            "last_output_tokens": self.last_output_tokens,
            "last_reasoning_output_tokens": self.last_reasoning_output_tokens,
            "cache_hit_pct": self.cache_hit_pct,
        }


def parse_trace(path: Path) -> TraceStats:
    stats = TraceStats(path=path)
    event_index = 0
    for obj in iter_jsonl(path):
        event_index += 1
        stats.events += 1
        request_body = extract_body(obj, "request")
        response_body = extract_body(obj, "response")
        collect_trace_metadata(stats, obj, request_body)
        endpoint = first_present(obj, "endpoint", "url", "target")
        if endpoint:
            stats.endpoint = str(endpoint)
        latency_ms = first_present(obj, "latency_ms", "duration_ms")
        if latency_ms:
            stats.latency_ms = int(latency_ms)
        response = obj.get("response") if isinstance(obj.get("response"), dict) else {}
        if isinstance(response, dict):
            stats.status = int(first_present(response, "status", "status_code") or stats.status or 0) or None

        if isinstance(request_body, dict):
            stats.model = str(request_body.get("model") or stats.model or "") or None
            if is_codex_claude_tap_record(obj, request_body):
                stats.trace_format = "claude-tap-codex"
                collect_codex_request_contributors(stats, request_body)
            collect_request_contributors(stats, request_body)
        usage = find_usage(obj, response_body)
        if usage:
            apply_usage(stats, usage)
        trace_event = build_trace_timeline_event(stats, obj, request_body, usage, path, event_index)
        stats.timeline_events.append(trace_event)
        stats.activity_events.extend(build_trace_activity_events(trace_event, request_body, path, event_index))
    return stats


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def extract_body(obj: dict[str, Any], key: str) -> dict[str, Any]:
    value = obj.get(key)
    if isinstance(value, dict):
        for body_key in ("body", "json", "payload"):
            body = value.get(body_key)
            if isinstance(body, dict):
                return body
        if key == "request" and any(item in value for item in ("input", "messages", "tools", "model")):
            return value
        if key == "response" and any(item in value for item in ("usage", "output", "choices")):
            return value
    body = obj.get(f"{key}_body")
    return body if isinstance(body, dict) else {}


def collect_trace_metadata(stats: TraceStats, obj: dict[str, Any], request_body: dict[str, Any]) -> None:
    request = obj.get("request") if isinstance(obj.get("request"), dict) else {}
    transport = first_present(obj, "transport", "protocol")
    upstream_base_url = first_present(obj, "upstream_base_url", "target", "endpoint")
    request_path = first_present(request, "path", "url")
    request_method = first_present(request, "method")
    if transport:
        stats.transport = str(transport)
    if upstream_base_url:
        stats.upstream_base_url = str(upstream_base_url)
    if request_path:
        stats.request_path = str(request_path)
    if request_method:
        stats.request_method = str(request_method)
    if is_codex_claude_tap_record(obj, request_body):
        stats.trace_format = "claude-tap-codex"


def is_codex_claude_tap_record(obj: dict[str, Any], request_body: dict[str, Any]) -> bool:
    client = str(obj.get("client") or "").lower()
    transport = str(obj.get("transport") or "").lower()
    upstream = str(first_present(obj, "upstream_base_url", "target", "endpoint") or "").lower()
    request = obj.get("request") if isinstance(obj.get("request"), dict) else {}
    path = str(first_present(request, "path", "url") or "").lower()
    body_type = str(request_body.get("type") or "").lower()
    has_responses_shape = bool(
        request_body.get("instructions") is not None
        or request_body.get("previous_response_id") is not None
        or body_type == "response.create"
    )
    if client == "codex":
        return True
    if "backend-api/codex" in upstream:
        return True
    return bool(has_responses_shape and "responses" in path and transport in {"websocket", "ws", "http", "sse", ""})


def collect_codex_request_contributors(stats: TraceStats, body: dict[str, Any]) -> None:
    instruction_tokens = value_tokens(body.get("instructions"))
    if instruction_tokens:
        stats.contributors.append(
            Contributor(
                "request codex instructions",
                "request_instructions",
                "request_trace",
                instruction_tokens,
                instruction_tokens * 4,
                "estimated",
                note="instruction body omitted",
            )
        )


def collect_request_contributors(stats: TraceStats, body: dict[str, Any]) -> None:
    role_tokens: dict[str, int] = {}
    tool_result_tokens = 0
    for message in request_messages(body):
        role = str(message.get("role") or message.get("type") or "unknown")
        content = first_present(message, "content", "text", "output")
        tokens = value_tokens(content)
        if not tokens:
            continue
        if role in {"tool", "function_call_output"} or message.get("type") == "function_call_output":
            tool_result_tokens += tokens
        else:
            role_tokens[role] = role_tokens.get(role, 0) + tokens

    for role, tokens in role_tokens.items():
        stats.contributors.append(
            Contributor(
                f"request messages: {role}",
                "request_messages",
                "request_trace",
                tokens,
                tokens * 4,
                "estimated",
                note="message bodies omitted",
            )
        )
    if tool_result_tokens:
        stats.contributors.append(
            Contributor(
                "request tool results",
                "request_tool_results",
                "request_trace",
                tool_result_tokens,
                tool_result_tokens * 4,
                "estimated",
                note="tool result bodies omitted",
            )
        )

    tools = body.get("tools") or body.get("functions")
    if tools:
        size = json_size(tools)
        stats.contributors.append(
            Contributor(
                "request tool definitions",
                "request_tool_definitions",
                "request_trace",
                approx_tokens(size),
                size,
                "estimated",
                note="tool schemas summarized by size",
            )
        )


def request_messages(body: dict[str, Any]) -> list[dict[str, Any]]:
    raw = body.get("input")
    if raw is None:
        raw = body.get("messages")
    if isinstance(raw, str):
        return [{"role": "user", "content": raw}]
    if isinstance(raw, list):
        messages = []
        for item in raw:
            if isinstance(item, dict):
                messages.append(item)
            elif isinstance(item, str):
                messages.append({"role": "user", "content": item})
        return messages
    return []


def find_usage(obj: dict[str, Any], response_body: dict[str, Any]) -> dict[str, Any]:
    for candidate in (
        response_body.get("usage") if isinstance(response_body, dict) else None,
        obj.get("usage"),
        response_body.get("token_usage") if isinstance(response_body, dict) else None,
    ):
        if isinstance(candidate, dict):
            return candidate
    return {}


def apply_usage(stats: TraceStats, usage: dict[str, Any]) -> None:
    input_tokens = int(first_present(usage, "input_tokens", "prompt_tokens") or 0)
    output_tokens = int(first_present(usage, "output_tokens", "completion_tokens") or 0)
    cached_tokens = int(first_present(usage, "cached_input_tokens", "cached_prompt_tokens") or 0)
    reasoning_tokens = int(first_present(usage, "reasoning_output_tokens", "reasoning_tokens") or 0)
    total_tokens = int(first_present(usage, "total_tokens") or input_tokens + output_tokens or 0)
    details = usage.get("input_tokens_details") or usage.get("prompt_tokens_details") or {}
    if isinstance(details, dict):
        cached_tokens = cached_tokens or int(details.get("cached_tokens") or 0)
    output_details = usage.get("output_tokens_details") or usage.get("completion_tokens_details") or {}
    if isinstance(output_details, dict):
        reasoning_tokens = reasoning_tokens or int(output_details.get("reasoning_tokens") or 0)

    stats.exact_usage_events += 1
    stats.last_input_tokens = input_tokens
    stats.last_output_tokens = output_tokens
    stats.last_cached_input_tokens = cached_tokens
    stats.last_reasoning_output_tokens = reasoning_tokens
    stats.last_total_tokens = total_tokens
    stats.max_input_tokens = max(stats.max_input_tokens, input_tokens)
    stats.max_total_input_tokens = max(stats.max_total_input_tokens, input_tokens)


def first_present(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


def build_trace_timeline_event(
    stats: TraceStats,
    obj: dict[str, Any],
    request_body: dict[str, Any],
    usage: dict[str, Any],
    path: Path,
    order: int,
) -> dict[str, Any]:
    request = obj.get("request") if isinstance(obj.get("request"), dict) else {}
    method = first_present(request, "method") or stats.request_method
    request_path = first_present(request, "path", "url") or stats.request_path or stats.endpoint
    status = None
    response = obj.get("response") if isinstance(obj.get("response"), dict) else {}
    if isinstance(response, dict):
        status_value = first_present(response, "status", "status_code")
        status = int(status_value) if status_value else None
    if status is None:
        status = stats.status
    model = request_body.get("model") or stats.model
    latency_value = first_present(obj, "latency_ms", "duration_ms")
    event = {
        "source": "request_trace",
        "kind": "request",
        "timestamp": str(first_present(obj, "timestamp", "time", "created_at") or "") or None,
        "path": safe_path(str(request_path or "")),
        "method": str(method or ""),
        "model": str(model or ""),
        "status": status,
        "latency_ms": int(latency_value) if latency_value else None,
        "exact_usage": bool(usage),
        "trace_format": stats.trace_format,
        "transport": stats.transport,
        "file": str(path),
        "order": order,
    }
    if usage:
        event.update(
            {
                "input_tokens": int(first_present(usage, "input_tokens", "prompt_tokens") or 0),
                "total_tokens": int(first_present(usage, "total_tokens") or 0),
                "output_tokens": int(first_present(usage, "output_tokens", "completion_tokens") or 0),
            }
        )
    return event


def build_trace_activity_events(trace_event: dict[str, Any], request_body: dict[str, Any], file_path: Path, order: int) -> list[dict[str, Any]]:
    events = [
        {
            "source": "request_trace",
            "kind": "network_request",
            "category": request_category(str(trace_event.get("path") or "")),
            "timestamp": trace_event.get("timestamp"),
            "path": trace_event.get("path"),
            "method": trace_event.get("method"),
            "model": trace_event.get("model"),
            "status": trace_event.get("status"),
            "latency_ms": trace_event.get("latency_ms"),
            "exact_usage": trace_event.get("exact_usage"),
            "file": str(file_path),
            "order": order,
        }
    ]
    tools = request_body.get("tools") or request_body.get("functions") or []
    tool_names = sorted(
        str(item.get("name") or item.get("type") or "")
        for item in tools
        if isinstance(item, dict) and (item.get("name") or item.get("type"))
    )
    if tool_names:
        events.append(
            {
                "source": "request_trace",
                "kind": "request_tool_inventory",
                "timestamp": trace_event.get("timestamp"),
                "path": trace_event.get("path"),
                "file": str(file_path),
                "order": order,
                "tool_names": tool_names[:100],
                "tool_count": len(tool_names),
            }
        )
    return events


def request_category(path: str) -> str:
    clean = safe_path(path)
    if "responses" in clean or clean.endswith("/chat/completions"):
        return "model_request"
    if clean == "/mcp" or "/mcp" in clean:
        return "mcp"
    if "plugins" in clean:
        return "plugin_registry"
    if "connectors" in clean:
        return "connector_directory"
    if "oauth" in clean or "token" in clean:
        return "auth"
    if "analytics" in clean or "wham" in clean:
        return "analytics"
    if clean.startswith("/repos/"):
        return "repository"
    return "other"


def safe_path(value: str) -> str:
    if not value:
        return ""
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        return parsed.path or "/"
    return value.split("?", 1)[0]


def value_tokens(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, str):
        return approx_tokens(value)
    return approx_tokens(json_size(value))
