from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

from .onboarding import cache_root
from .util import approx_tokens, json_size


def main(argv: list[str] | None = None, stdin: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(description="Context Fixer hook collector.")
    parser.add_argument("event_type", choices=["post-tool-use", "pre-tool-use", "stop", "user-prompt-submit"], help="Hook event type.")
    parser.add_argument("--input", metavar="PATH", help="Read hook JSON from PATH instead of stdin.")
    parser.add_argument("--output", metavar="PATH", help="Append sanitized JSONL to PATH instead of the default cache file.")
    args = parser.parse_args(argv)

    payload = read_payload(args.input, stdin)
    record = sanitize_hook_event(args.event_type, payload)
    output = Path(args.output).expanduser() if args.output else cache_root() / "hooks" / "events.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"recorded {args.event_type} context audit event at {output}")
    return 0


def read_payload(input_path: str | None, stdin: TextIO | None) -> dict[str, Any]:
    if input_path:
        text = Path(input_path).expanduser().read_text(encoding="utf-8", errors="ignore")
    else:
        source = stdin
        if source is None:
            import sys

            source = sys.stdin
        text = source.read()
    try:
        data = json.loads(text or "{}")
    except json.JSONDecodeError:
        data = {"raw": text}
    return data if isinstance(data, dict) else {"value": data}


def sanitize_hook_event(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    tool_input = first_dict(payload, "tool_input", "input", "toolInput")
    tool_response = first_dict(payload, "tool_response", "response", "toolResponse", "result")
    command = first_text(tool_input, "command", "cmd")
    output_value = first_present(tool_response, "output", "content", "result", "stdout", "stderr")
    tool_input_size = json_size(tool_input)
    tool_response_size = json_size(output_value if output_value is not None else tool_response)
    return {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "session_id": first_present(payload, "session_id", "sessionId"),
        "turn_id": first_present(payload, "turn_id", "turnId"),
        "cwd": first_present(payload, "cwd", "working_directory", "workingDirectory"),
        "tool_name": first_present(payload, "tool_name", "toolName", "name") or first_present(tool_input, "tool_name", "name"),
        "command_preview": preview(command),
        "status": first_present(tool_response, "status"),
        "exit_code": first_present(tool_response, "exit_code", "exitCode", "code"),
        "tool_input_bytes": tool_input_size,
        "tool_input_estimated_tokens": approx_tokens(tool_input_size),
        "tool_input_hash": stable_hash(tool_input),
        "tool_response_bytes": tool_response_size,
        "tool_response_estimated_tokens": approx_tokens(tool_response_size),
        "tool_response_hash": stable_hash(output_value if output_value is not None else tool_response),
        "payload_keys": sorted(str(key) for key in payload.keys()),
        "tool_input_keys": sorted(str(key) for key in tool_input.keys()),
        "tool_response_keys": sorted(str(key) for key in tool_response.keys()),
    }


def first_dict(data: dict[str, Any], *keys: str) -> dict[str, Any]:
    for key in keys:
        value = data.get(key)
        if isinstance(value, dict):
            return value
    return {}


def first_text(data: dict[str, Any], *keys: str) -> str | None:
    value = first_present(data, *keys)
    return str(value) if value not in (None, "") else None


def first_present(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


def stable_hash(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True) if not isinstance(value, str) else value
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:24]


def preview(value: str | None, limit: int = 160) -> str | None:
    if not value:
        return None
    compact = " ".join(value.split())
    return compact[:limit]


if __name__ == "__main__":
    raise SystemExit(main())
