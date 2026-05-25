from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .util import approx_tokens, json_size


@dataclass
class Contributor:
    label: str
    kind: str
    scope: str
    estimated_tokens: int
    bytes: int
    confidence: str
    path: str | None = None
    note: str | None = None

    def as_dict(self) -> dict[str, Any]:
        data = {
            "label": self.label,
            "kind": self.kind,
            "scope": self.scope,
            "estimated_tokens": self.estimated_tokens,
            "bytes": self.bytes,
            "confidence": self.confidence,
        }
        if self.path:
            data["path"] = self.path
        if self.note:
            data["note"] = self.note
        return data


@dataclass
class SessionStats:
    path: Path
    cwd: str | None = None
    model_context_window: int | None = None
    token_events: int = 0
    compact_events: int = 0
    max_input_tokens: int = 0
    max_total_input_tokens: int = 0
    last_input_tokens: int = 0
    last_total_tokens: int = 0
    last_cached_input_tokens: int = 0
    last_output_tokens: int = 0
    last_reasoning_output_tokens: int = 0
    max_context_pct: float = 0.0
    contributors: list[Contributor] = field(default_factory=list)
    tool_output_tokens: dict[str, int] = field(default_factory=dict)
    tool_argument_tokens: dict[str, int] = field(default_factory=dict)
    conversation_tokens: int = 0
    timeline_events: list[dict[str, Any]] = field(default_factory=list)
    activity_events: list[dict[str, Any]] = field(default_factory=list)

    @property
    def cache_hit_pct(self) -> float:
        return self.last_cached_input_tokens / self.last_input_tokens if self.last_input_tokens else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "cwd": self.cwd,
            "model_context_window": self.model_context_window,
            "token_events": self.token_events,
            "compact_events": self.compact_events,
            "max_input_tokens": self.max_input_tokens,
            "max_total_input_tokens": self.max_total_input_tokens,
            "last_input_tokens": self.last_input_tokens,
            "last_total_tokens": self.last_total_tokens,
            "last_cached_input_tokens": self.last_cached_input_tokens,
            "last_output_tokens": self.last_output_tokens,
            "last_reasoning_output_tokens": self.last_reasoning_output_tokens,
            "cache_hit_pct": self.cache_hit_pct,
            "max_context_pct": self.max_context_pct,
        }


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def discover_sessions(codex_home: Path, repo: Path | None, limit: int = 5) -> list[Path]:
    root = codex_home / "sessions"
    if not root.exists():
        return []
    candidates = sorted(root.rglob("*.jsonl"), key=lambda path: path.stat().st_mtime, reverse=True)
    if repo is None:
        return candidates[:limit]
    repo_text = str(repo.resolve())
    matches = [path for path in candidates if (cwd := session_cwd(path)) and (cwd == repo_text or cwd.startswith(repo_text + "/"))]
    return matches[:limit] or candidates[:limit]


def session_cwd(path: Path) -> str | None:
    for obj in iter_jsonl(path):
        if obj.get("type") == "session_meta":
            cwd = (obj.get("payload") or {}).get("cwd")
            return str(cwd) if cwd else None
    return None


def parse_session(path: Path) -> SessionStats:
    stats = SessionStats(path=path)
    call_names: dict[str, str] = {}
    event_index = 0
    for obj in iter_jsonl(path):
        event_index += 1
        payload = obj.get("payload") or {}
        event_type = obj.get("type")
        payload_type = payload.get("type")
        if event_type == "session_meta":
            stats.cwd = str(payload.get("cwd")) if payload.get("cwd") else stats.cwd
            add_value_contributor(stats, "session base instructions", "base_instructions", "session", (payload.get("base_instructions") or {}).get("text"))
            tools = payload.get("dynamic_tools") or []
            if tools:
                size = json_size(tools)
                stats.contributors.append(
                    Contributor("session dynamic tool definitions", "dynamic_tools", "session", approx_tokens(size), size, "estimated")
                )
                names = sorted(
                    str(item.get("name") or item.get("type") or "")
                    for item in tools
                    if isinstance(item, dict) and (item.get("name") or item.get("type"))
                )
                if names:
                    stats.activity_events.append(
                        {
                            "source": "session_jsonl",
                            "kind": "available_tools",
                            "timestamp": event_timestamp(obj, payload),
                            "path": str(path),
                            "order": event_index,
                            "tool_names": names[:100],
                            "tool_count": len(names),
                        }
                    )
        if event_type == "turn_context":
            stats.cwd = str(payload.get("cwd")) if payload.get("cwd") else stats.cwd
            add_value_contributor(stats, "turn developer instructions", "developer_instructions", "turn", payload.get("developer_instructions"))
            collaboration_settings = ((payload.get("collaboration_mode") or {}).get("settings") or {})
            add_value_contributor(
                stats,
                "collaboration mode developer instructions",
                "developer_instructions",
                "turn",
                collaboration_settings.get("developer_instructions"),
            )
            add_value_contributor(stats, "turn context summary", "conversation_summary", "turn", payload.get("summary"))
        if event_type == "compacted" or payload_type == "context_compacted":
            stats.compact_events += 1
            stats.timeline_events.append(
                {
                    "source": "session_jsonl",
                    "kind": "compaction",
                    "timestamp": event_timestamp(obj, payload),
                    "path": str(path),
                    "order": event_index,
                    "input_tokens_before": stats.last_input_tokens,
                    "total_tokens_before": stats.last_total_tokens,
                }
            )
        if payload_type == "task_started":
            stats.model_context_window = payload.get("model_context_window") or stats.model_context_window
        if payload_type in {"message", "user_message", "agent_message"}:
            stats.conversation_tokens += value_tokens(first_present(payload, "message", "content", "text"))
        if payload_type == "token_count":
            info = payload.get("info") or {}
            usage = info.get("last_token_usage") or {}
            total_usage = info.get("total_token_usage") or {}
            window = info.get("model_context_window") or stats.model_context_window
            stats.model_context_window = window
            stats.token_events += 1
            stats.last_input_tokens = int(usage.get("input_tokens") or 0)
            stats.last_total_tokens = int(usage.get("total_tokens") or 0)
            stats.last_cached_input_tokens = int(usage.get("cached_input_tokens") or 0)
            stats.last_output_tokens = int(usage.get("output_tokens") or 0)
            stats.last_reasoning_output_tokens = int(usage.get("reasoning_output_tokens") or 0)
            stats.max_input_tokens = max(stats.max_input_tokens, stats.last_input_tokens)
            stats.max_total_input_tokens = max(stats.max_total_input_tokens, int(total_usage.get("input_tokens") or 0))
            if window:
                stats.max_context_pct = max(stats.max_context_pct, stats.last_input_tokens / int(window))
            stats.timeline_events.append(
                {
                    "source": "session_jsonl",
                    "kind": "token_count",
                    "timestamp": event_timestamp(obj, payload),
                    "path": str(path),
                    "order": event_index,
                    "input_tokens": stats.last_input_tokens,
                    "total_tokens": stats.last_total_tokens,
                    "cached_input_tokens": stats.last_cached_input_tokens,
                    "output_tokens": stats.last_output_tokens,
                    "reasoning_output_tokens": stats.last_reasoning_output_tokens,
                    "model_context_window": int(window or 0),
                    "context_pct": stats.last_input_tokens / int(window) if window else 0.0,
                }
            )
            if stats.last_input_tokens == 0 and stats.last_total_tokens == 0:
                stats.timeline_events.append(
                    {
                        "source": "session_jsonl",
                        "kind": "anomaly",
                        "anomaly_type": "zero_usage_session",
                        "timestamp": event_timestamp(obj, payload),
                        "path": str(path),
                        "order": event_index,
                        "message": "Session token event reported zero usage.",
                    }
                )
        if payload_type in {"function_call", "custom_tool_call", "tool_search_call", "web_search_call"}:
            call_id = payload.get("call_id")
            name = str(payload.get("name") or payload_type)
            if call_id:
                call_names[str(call_id)] = name
            argument_tokens = value_tokens(first_present(payload, "arguments", "input", "query"))
            if argument_tokens:
                stats.tool_argument_tokens[name] = stats.tool_argument_tokens.get(name, 0) + argument_tokens
            stats.activity_events.append(
                {
                    "source": "session_jsonl",
                    "kind": "tool_call",
                    "timestamp": event_timestamp(obj, payload),
                    "path": str(path),
                    "order": event_index,
                    "name": name,
                    "call_type": str(payload_type),
                    "argument_estimated_tokens": argument_tokens,
                }
            )
        if payload_type in {"function_call_output", "custom_tool_call_output", "tool_search_call_output", "web_search_end"}:
            call_id = str(payload.get("call_id") or "unknown")
            name = call_names.get(call_id, "unknown")
            tokens = value_tokens(first_present(payload, "output", "result", "content"))
            if tokens:
                stats.tool_output_tokens[name] = stats.tool_output_tokens.get(name, 0) + tokens
            stats.activity_events.append(
                {
                    "source": "session_jsonl",
                    "kind": "tool_result",
                    "timestamp": event_timestamp(obj, payload),
                    "path": str(path),
                    "order": event_index,
                    "name": name,
                    "call_type": str(payload_type),
                    "output_estimated_tokens": tokens,
                    "status": payload.get("status"),
                }
            )
        if payload_type == "reasoning":
            add_value_contributor(stats, "assistant reasoning metadata", "reasoning", "runtime", first_present(payload, "summary", "content", "text"))
    if stats.conversation_tokens:
        stats.contributors.append(
            Contributor(
                "session conversation messages",
                "conversation",
                "runtime",
                stats.conversation_tokens,
                stats.conversation_tokens * 4,
                "estimated",
                note="message bodies omitted",
            )
        )
    for name, tokens in stats.tool_argument_tokens.items():
        stats.contributors.append(
            Contributor(
                f"runtime tool arguments: {name}",
                "tool_arguments",
                "runtime",
                tokens,
                tokens * 4,
                "estimated",
                note="argument bodies omitted",
            )
        )
    for name, tokens in stats.tool_output_tokens.items():
        stats.contributors.append(
            Contributor(
                f"runtime tool output: {name}",
                "tool_output",
                "runtime",
                tokens,
                tokens * 4,
                "estimated",
                note="output bodies omitted",
            )
        )
    if stats.token_events and stats.max_input_tokens == 0:
        stats.timeline_events.append(
            {
                "source": "session_jsonl",
                "kind": "anomaly",
                "anomaly_type": "zero_usage_session",
                "timestamp": None,
                "path": str(path),
                "order": event_index + 1,
                "message": "Session contains token events but no non-zero usage.",
            }
        )
    return stats


def first_present(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


def value_tokens(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, str):
        return approx_tokens(value)
    return approx_tokens(json_size(value))


def value_bytes(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, str):
        return len(value)
    return json_size(value)


def add_value_contributor(stats: SessionStats, label: str, kind: str, scope: str, value: Any) -> None:
    tokens = value_tokens(value)
    if not tokens:
        return
    stats.contributors.append(Contributor(label, kind, scope, tokens, value_bytes(value), "estimated", note="body omitted"))


def event_timestamp(obj: dict[str, Any], payload: dict[str, Any]) -> str | None:
    value = first_present(obj, "timestamp", "time", "created_at")
    if value is None:
        value = first_present(payload, "timestamp", "time", "created_at")
    return str(value) if value else None
