#!/usr/bin/env python3
"""Parent-side continuity state for Lark Feishu Ops subagent work."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


RUNTIME_ROOT = Path(".dev-flow") / "lark-feishu-ops" / "agent-context"
ACTIVE_REGISTRY = "active_agents.json"
SNAPSHOT_DIR = "snapshots"
SCHEMA_VERSION = "1.0"
DEFAULT_TTL_SECONDS = 86400
MAX_STRING_LENGTH = 1200

SAFE_RESOURCE_KEYS = {
    "type",
    "id",
    "name",
    "title",
    "url",
    "revision",
    "revision_id",
    "cursor",
    "page_token",
    "time_window",
    "range",
    "sheet_id",
    "table_id",
    "chat_id",
    "message_id",
    "event_id",
    "meeting_id",
    "task_id",
    "approval_id",
}
SAFE_TOKEN_KEYS = {
    "doc_token",
    "file_token",
    "wiki_token",
    "sheet_token",
    "app_token",
    "bitable_token",
}
SENSITIVE_EXACT_KEYS = {
    "access_token",
    "refresh_token",
    "tenant_access_token",
    "user_access_token",
    "app_secret",
    "client_secret",
    "secret",
    "password",
    "authorization",
    "auth_header",
    "cookie",
    "api_key",
    "private_key",
    "token",
}
SENSITIVE_KEY_PARTS = ("credential", "bearer", "session_secret")
AUTHORIZATION_RE = re.compile(r"Authorization:\s*Bearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
BEARER_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{8,}", re.IGNORECASE)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat(value: datetime | str | None) -> str:
    if value is None:
        value = utc_now()
    if isinstance(value, str):
        return value
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    text = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def runtime_root(repo: Path | str) -> Path:
    return Path(repo).expanduser().resolve() / RUNTIME_ROOT


def active_registry_path(repo: Path | str) -> Path:
    return runtime_root(repo) / ACTIVE_REGISTRY


def snapshots_dir(repo: Path | str) -> Path:
    return runtime_root(repo) / SNAPSHOT_DIR


def ensure_runtime(repo: Path | str) -> None:
    snapshots_dir(repo).mkdir(parents=True, exist_ok=True)


def read_json_file(path: Path, default: Any) -> Any:
    if not path.is_file():
        return copy.deepcopy(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return copy.deepcopy(default)


def write_json_file(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def is_sensitive_key(key: str) -> bool:
    normalized = key.lower().strip()
    if normalized in SAFE_TOKEN_KEYS:
        return False
    if normalized in SENSITIVE_EXACT_KEYS:
        return True
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def redact_string(value: str, *, max_length: int = MAX_STRING_LENGTH) -> str:
    redacted = AUTHORIZATION_RE.sub("Authorization: [REDACTED]", value)
    redacted = BEARER_RE.sub("[REDACTED]", redacted)
    if len(redacted) > max_length:
        omitted = len(redacted) - max_length
        return f"{redacted[:max_length]}[TRUNCATED {omitted} chars]"
    return redacted


def redact_value(value: Any, *, key: str | None = None) -> Any:
    if key is not None and is_sensitive_key(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {item_key: redact_value(item_value, key=str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, str):
        return redact_string(value)
    return value


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return copy.deepcopy(value)
    return [copy.deepcopy(value)]


def as_dict(value: Any) -> dict[str, Any]:
    return copy.deepcopy(value) if isinstance(value, dict) else {}


def is_write_action(action: str, hints: dict[str, Any] | None = None) -> bool:
    hints = hints or {}
    if hints.get("side_effects") or hints.get("read_only") is False:
        return True
    lower = action.lower()
    write_markers = (
        ".send",
        ".upsert",
        ".create",
        ".update",
        ".delete",
        ".write",
        ".patch",
        ".move",
        ".copy",
        ".join",
        ".leave",
        ".confirm",
        "auth.login",
    )
    return any(marker in lower for marker in write_markers)


def action_domain(action: str) -> str:
    return action.split(".", 1)[0] if action else "unknown"


def extract_resource_refs(payload: Any) -> list[str]:
    refs: set[str] = set()

    def visit(value: Any, key: str | None = None) -> None:
        if isinstance(value, dict):
            item_id = value.get("id")
            if isinstance(item_id, (str, int)) and str(item_id):
                refs.add(str(item_id))
            for item_key, item_value in value.items():
                visit(item_value, str(item_key))
            return
        if isinstance(value, list):
            for item in value:
                visit(item)
            return
        if isinstance(value, (str, int)) and key:
            normalized = key.lower()
            if normalized in SAFE_TOKEN_KEYS or normalized.endswith("_id") or normalized == "id":
                text = str(value).strip()
                if text:
                    refs.add(text)

    visit(payload)
    return sorted(refs)


def compact_resource_object(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    compact = {}
    for key, value in item.items():
        if key in SAFE_RESOURCE_KEYS or key in SAFE_TOKEN_KEYS:
            compact[key] = value
    if "id" not in compact:
        for token_key in SAFE_TOKEN_KEYS:
            if token_key in compact:
                compact["id"] = compact[token_key]
                break
    return compact or None


def compact_resource_objects(items: Any) -> list[dict[str, Any]]:
    compacted: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in as_list(items):
        compact = compact_resource_object(item)
        if compact is None:
            continue
        key = json.dumps(compact, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            compacted.append(compact)
    return compacted


def affinity_key(action: str, resource_refs: list[str]) -> str:
    resource_part = ",".join(sorted(resource_refs)) if resource_refs else "no-resource"
    return f"{action_domain(action)}:{resource_part}"


def normalize_delegation_request(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("delegation request must be a JSON object")

    request = copy.deepcopy(payload)
    action = str(request.get("action") or "domain.call")
    hints = as_dict(request.get("dispatch_hints"))
    write = is_write_action(action, hints)

    hints.setdefault("identity", "none")
    hints.setdefault("profile", "default")
    hints.setdefault("direct_allowed", not write)
    hints.setdefault("read_only", not write)
    hints.setdefault("bounded", True)
    hints.setdefault("single_domain", True)
    hints.setdefault("cross_domain", False)
    hints.setdefault("raw_openapi", action.startswith("openapi."))
    hints.setdefault("large_or_paginated", False)
    hints.setdefault("requires_auth_profile_change", False)
    hints.setdefault("explicit_subagent", False)

    handoff = as_dict(request.get("handoff_context"))
    handoff.setdefault("user_goal", "")
    handoff["parent_context"] = as_list(handoff.get("parent_context"))
    handoff["known_resources"] = compact_resource_objects(handoff.get("known_resources"))
    handoff.setdefault("prior_evidence_pack", {})
    handoff["freshness"] = as_dict(handoff.get("freshness"))
    handoff["non_goals"] = as_list(handoff.get("non_goals"))

    resource_refs = extract_resource_refs(
        {
            "target": request.get("target"),
            "known_resources": handoff.get("known_resources"),
        }
    )

    request.setdefault("request_id", stable_request_id(action, request.get("target"), handoff))
    request["action"] = action
    request["target"] = as_dict(request.get("target"))
    request["handoff_context"] = handoff
    request["constraints"] = as_list(request.get("constraints"))
    request["success_criteria"] = as_list(request.get("success_criteria"))
    request["stop_conditions"] = as_list(request.get("stop_conditions"))
    request.setdefault("expected_output", "evidence_pack")
    request.setdefault("return_format", "json")
    request["dispatch_hints"] = hints
    request["risk_class"] = "write" if write else "read"
    request["resource_refs"] = resource_refs
    request["affinity_key"] = affinity_key(action, resource_refs)
    return request


def stable_request_id(action: str, target: Any, handoff: dict[str, Any]) -> str:
    digest = hashlib.sha256(
        json.dumps({"action": action, "target": target, "handoff": handoff}, sort_keys=True, default=str).encode()
    ).hexdigest()[:12]
    return f"req-{digest}"


def normalize_agent_result(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("agent result must be a JSON object")

    result = copy.deepcopy(payload)
    result["status"] = str(result.get("status") or "FAILED").upper()
    result.setdefault("action", "")
    result.setdefault("identity", "none")
    result["commands_or_tools_used"] = as_list(result.get("commands_or_tools_used"))
    result["targets"] = as_dict(result.get("targets"))
    result["progress"] = as_dict(result.get("progress"))
    result["progress"].setdefault("last_signal", "")
    result["progress"].setdefault("state", "complete" if result["status"] == "PASS" else "blocked")
    result_data = as_dict(result.get("result"))
    result_data["evidence_pack"] = as_dict(result_data.get("evidence_pack"))
    result_data["next_resources"] = as_list(result_data.get("next_resources"))
    result["result"] = result_data
    result["side_effects"] = as_list(result.get("side_effects"))
    result["validation"] = as_dict(result.get("validation"))
    result["artifacts"] = as_list(result.get("artifacts"))
    result["blockers"] = as_list(result.get("blockers"))
    result["residual_risk"] = as_list(result.get("residual_risk"))

    update = as_dict(result.get("context_cache_update"))
    update["resource_refs"] = compact_resource_objects(update.get("resource_refs"))
    update["resource_map"] = as_dict(update.get("resource_map"))
    update["known_command_shapes"] = as_list(update.get("known_command_shapes"))
    update["missing_evidence"] = as_list(update.get("missing_evidence"))
    update["freshness"] = as_dict(update.get("freshness"))
    update["provenance"] = as_dict(update.get("provenance"))
    result["context_cache_update"] = update
    return result


def read_active_registry(repo: Path | str) -> dict[str, Any]:
    registry = read_json_file(active_registry_path(repo), {"schema_version": SCHEMA_VERSION, "agents": []})
    if not isinstance(registry, dict):
        return {"schema_version": SCHEMA_VERSION, "agents": []}
    agents = registry.get("agents")
    if not isinstance(agents, list):
        registry["agents"] = []
    registry.setdefault("schema_version", SCHEMA_VERSION)
    return registry


def write_active_registry(repo: Path | str, registry: dict[str, Any]) -> None:
    ensure_runtime(repo)
    write_json_file(active_registry_path(repo), registry)


def record_active_agent(
    repo: Path | str,
    *,
    agent_id: str,
    request: dict[str, Any],
    last_progress_at: datetime | str | None = None,
    state: str = "active",
    last_snapshot_id: str | None = None,
) -> dict[str, Any]:
    normalized = normalize_delegation_request(request)
    entry = {
        "agent_id": agent_id,
        "state": state,
        "request_id": normalized["request_id"],
        "action": normalized["action"],
        "affinity_key": normalized["affinity_key"],
        "resource_refs": normalized["resource_refs"],
        "identity": normalized["dispatch_hints"].get("identity", "none"),
        "profile": normalized["dispatch_hints"].get("profile", "default"),
        "risk_class": normalized["risk_class"],
        "last_progress_at": isoformat(last_progress_at),
        "last_snapshot_id": last_snapshot_id,
    }
    registry = read_active_registry(repo)
    registry["agents"] = [agent for agent in registry["agents"] if agent.get("agent_id") != agent_id]
    registry["agents"].append(entry)
    write_active_registry(repo, registry)
    return entry


def snapshot_id_for(request: dict[str, Any], agent_id: str | None, created_at: str) -> str:
    seed = json.dumps(
        {
            "request_id": request.get("request_id"),
            "affinity_key": request.get("affinity_key"),
            "agent_id": agent_id,
            "created_at": created_at,
        },
        sort_keys=True,
    )
    return hashlib.sha256(seed.encode()).hexdigest()[:16]


def write_context_snapshot(
    repo: Path | str,
    request: dict[str, Any],
    result: dict[str, Any],
    *,
    agent_id: str | None = None,
    now: datetime | str | None = None,
) -> dict[str, Any]:
    ensure_runtime(repo)
    normalized_request = normalize_delegation_request(request)
    normalized_result = normalize_agent_result(result)
    created_at = isoformat(now)
    ttl_seconds = int(normalized_result["context_cache_update"]["freshness"].get("ttl_seconds") or DEFAULT_TTL_SECONDS)
    created_dt = parse_time(created_at) or utc_now()
    expires_at = isoformat(created_dt + timedelta(seconds=ttl_seconds))
    snapshot_id = snapshot_id_for(normalized_request, agent_id, created_at)
    path = snapshots_dir(repo) / f"{snapshot_id}.json"

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": snapshot_id,
        "created_at": created_at,
        "expires_at": expires_at,
        "agent_id": agent_id,
        "request_id": normalized_request["request_id"],
        "action": normalized_request["action"],
        "affinity_key": normalized_request["affinity_key"],
        "resource_refs": normalized_request["resource_refs"],
        "identity": normalized_request["dispatch_hints"].get("identity", "none"),
        "profile": normalized_request["dispatch_hints"].get("profile", "default"),
        "risk_class": normalized_request["risk_class"],
        "request": normalized_request,
        "result_status": normalized_result["status"],
        "evidence_pack": normalized_result["result"]["evidence_pack"],
        "next_resources": normalized_result["result"]["next_resources"],
        "context_cache_update": normalized_result["context_cache_update"],
        "validation": normalized_result["validation"],
        "blockers": normalized_result["blockers"],
        "residual_risk": normalized_result["residual_risk"],
    }
    redacted = redact_value(snapshot)
    write_json_file(path, redacted)
    return {"snapshot_id": snapshot_id, "path": str(path), "snapshot": redacted}


def list_context_snapshots(repo: Path | str) -> list[dict[str, Any]]:
    directory = snapshots_dir(repo)
    if not directory.is_dir():
        return []
    snapshots: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        payload = read_json_file(path, None)
        if isinstance(payload, dict):
            payload["_path"] = str(path)
            snapshots.append(payload)
    snapshots.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return snapshots


def direct_eligible(request: dict[str, Any]) -> bool:
    hints = request["dispatch_hints"]
    return bool(
        hints.get("direct_allowed")
        and hints.get("read_only")
        and hints.get("bounded")
        and hints.get("single_domain")
        and not hints.get("explicit_subagent")
        and not hints.get("cross_domain")
        and not hints.get("raw_openapi")
        and not hints.get("large_or_paginated")
        and not hints.get("requires_auth_profile_change")
        and request["risk_class"] == "read"
    )


def shares_resources(request: dict[str, Any], candidate: dict[str, Any]) -> bool:
    request_refs = set(request.get("resource_refs") or [])
    candidate_refs = set(candidate.get("resource_refs") or [])
    return bool(request_refs and candidate_refs and request_refs.intersection(candidate_refs))


def candidate_rejection_reason(
    request: dict[str, Any],
    candidate: dict[str, Any],
    *,
    now: datetime,
    stale_check: bool,
) -> str | None:
    if not shares_resources(request, candidate):
        return "resource mismatch"
    if request["dispatch_hints"].get("identity") != candidate.get("identity"):
        return "identity/profile mismatch"
    if request["dispatch_hints"].get("profile") != candidate.get("profile"):
        return "identity/profile mismatch"
    if request["risk_class"] == "write" and candidate.get("risk_class") == "read":
        return "read context cannot seed write"
    if stale_check:
        expires_at = parse_time(candidate.get("expires_at"))
        if expires_at is not None and expires_at < now:
            return "stale snapshot"
    return None


def reconstruct_request_from_snapshot(request: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    reconstructed = copy.deepcopy(request)
    handoff = reconstructed["handoff_context"]
    update = as_dict(snapshot.get("context_cache_update"))
    prior_resources = compact_resource_objects(update.get("resource_refs"))
    existing_resources = compact_resource_objects(handoff.get("known_resources"))

    merged_resources: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in existing_resources + prior_resources:
        key = json.dumps(item, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            merged_resources.append(item)

    handoff["known_resources"] = merged_resources
    handoff["prior_evidence_pack"] = as_dict(snapshot.get("evidence_pack"))
    handoff["prior_resource_map"] = as_dict(update.get("resource_map"))
    handoff["freshness"] = {
        **as_dict(handoff.get("freshness")),
        **as_dict(update.get("freshness")),
        "source_snapshot_id": snapshot.get("snapshot_id"),
        "source_snapshot_created_at": snapshot.get("created_at"),
    }
    handoff["provenance"] = as_dict(update.get("provenance"))
    reconstructed["handoff_context"] = handoff
    return reconstructed


def runtime_boundary() -> dict[str, Any]:
    return {
        "subagent_primitives": "parent_agent_runtime",
        "helper_does_not_call": ["spawn_agent", "send_input", "wait_agent", "close_agent"],
    }


def prepare_dispatch_report(
    repo: Path | str,
    request_payload: dict[str, Any],
    *,
    now: datetime | str | None = None,
) -> dict[str, Any]:
    now_dt = parse_time(now) if isinstance(now, str) else now
    if now_dt is None:
        now_dt = utc_now()
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)
    now_dt = now_dt.astimezone(timezone.utc)

    request = normalize_delegation_request(request_payload)
    rejected: list[str] = []

    for agent in read_active_registry(repo).get("agents", []):
        if agent.get("state") != "active":
            continue
        reason = candidate_rejection_reason(request, agent, now=now_dt, stale_check=False)
        if reason is None:
            return {
                "status": "PASS",
                "request": request,
                "dispatch": {
                    "decision": "reuse_active",
                    "reason": (
                        "related active FeishuOps agent has compatible resource refs, "
                        "identity, profile, and risk"
                    ),
                    "agent_id": agent.get("agent_id"),
                    "follow_up_request": request,
                    "rejected_candidates": rejected,
                },
                "runtime_boundary": runtime_boundary(),
                "state_paths": state_paths(repo),
            }
        rejected.append(f"active:{agent.get('agent_id')}:{reason}")

    for snapshot in list_context_snapshots(repo):
        reason = candidate_rejection_reason(request, snapshot, now=now_dt, stale_check=True)
        if reason is None:
            return {
                "status": "PASS",
                "request": request,
                "dispatch": {
                    "decision": "reconstruct_from_cache",
                    "reason": "fresh related snapshot can seed a new FeishuOps handoff",
                    "snapshot_id": snapshot.get("snapshot_id"),
                    "reconstructed_request": reconstruct_request_from_snapshot(request, snapshot),
                    "rejected_candidates": rejected,
                },
                "runtime_boundary": runtime_boundary(),
                "state_paths": state_paths(repo),
            }
        rejected.append(f"snapshot:{snapshot.get('snapshot_id')}:{reason}")

    if direct_eligible(request):
        decision = {
            "decision": "direct",
            "reason": "bounded low-risk read can run in the main agent without subagent continuity",
            "rejected_candidates": rejected,
        }
    else:
        decision = {
            "decision": "fresh_subagent",
            "reason": "FeishuOps is required and no safe continuity candidate exists",
            "rejected_candidates": rejected,
        }
    return {
        "status": "PASS",
        "request": request,
        "dispatch": decision,
        "runtime_boundary": runtime_boundary(),
        "state_paths": state_paths(repo),
    }


def state_paths(repo: Path | str) -> dict[str, str]:
    return {
        "root": str(runtime_root(repo)),
        "active_registry": str(active_registry_path(repo)),
        "snapshots": str(snapshots_dir(repo)),
    }


def read_request_json(path: str) -> dict[str, Any]:
    if path == "-":
        payload = json.loads(sys.stdin.read())
    else:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("request JSON must be an object")
    return payload


def run_cli(argv: list[str] | None = None) -> tuple[int, dict[str, Any]]:
    parser = argparse.ArgumentParser(description="Manage Lark Feishu Ops agent continuity state.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Prepare dispatch recommendation for a request.")
    prepare.add_argument("--repo", required=True)
    prepare.add_argument("--request-json", required=True)
    prepare.add_argument("--json", action="store_true")

    record_active = subparsers.add_parser("record-active", help="Record a parent-spawned active FeishuOps agent.")
    record_active.add_argument("--repo", required=True)
    record_active.add_argument("--agent-id", required=True)
    record_active.add_argument("--request-json", required=True)
    record_active.add_argument("--state", default="active")
    record_active.add_argument("--json", action="store_true")

    record_result = subparsers.add_parser("record-result", help="Record a FeishuOps result as a context snapshot.")
    record_result.add_argument("--repo", required=True)
    record_result.add_argument("--request-json", required=True)
    record_result.add_argument("--result-json", required=True)
    record_result.add_argument("--agent-id")
    record_result.add_argument("--json", action="store_true")

    list_state = subparsers.add_parser("list", help="List continuity state.")
    list_state.add_argument("--repo", required=True)
    list_state.add_argument("--json", action="store_true")

    try:
        args = parser.parse_args(argv)
        if args.command == "prepare":
            return 0, prepare_dispatch_report(args.repo, read_request_json(args.request_json))
        if args.command == "record-active":
            entry = record_active_agent(
                args.repo,
                agent_id=args.agent_id,
                request=read_request_json(args.request_json),
                state=args.state,
            )
            return 0, {"status": "PASS", "active_agent": entry, "runtime_boundary": runtime_boundary()}
        if args.command == "record-result":
            request = read_request_json(args.request_json)
            result = json.loads(Path(args.result_json).read_text(encoding="utf-8"))
            snapshot = write_context_snapshot(args.repo, request, result, agent_id=args.agent_id)
            return 0, {"status": "PASS", "snapshot": snapshot, "runtime_boundary": runtime_boundary()}
        if args.command == "list":
            return 0, {
                "status": "PASS",
                "active_registry": read_active_registry(args.repo),
                "snapshots": list_context_snapshots(args.repo),
                "state_paths": state_paths(args.repo),
                "runtime_boundary": runtime_boundary(),
            }
    except Exception as exc:  # pragma: no cover - command-line safety net
        return 2, {"status": "FAIL", "error": str(exc), "runtime_boundary": runtime_boundary()}

    return 2, {"status": "FAIL", "error": "unknown command", "runtime_boundary": runtime_boundary()}


def main(argv: list[str] | None = None) -> int:
    exit_code, payload = run_cli(argv)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
