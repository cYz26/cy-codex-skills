#!/usr/bin/env python3
"""Fail-closed dispatch and metadata-only continuity facade for FeishuOps."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

import lark_feishu_ops_policy as policy
import lark_feishu_ops_runtime as runtime
import lark_feishu_ops_state as state


RUNTIME_ROOT = state.RUNTIME_ROOT
ACTIVE_REGISTRY = state.ACTIVE_REGISTRY
SNAPSHOT_DIR = state.SNAPSHOT_DIR
SCHEMA_VERSION = state.SCHEMA_VERSION
DEFAULT_TTL_SECONDS = state.MAX_TTL_SECONDS
MAX_STRING_LENGTH = state.MAX_STRING_BYTES
DOMAIN_ALIASES = policy.DOMAIN_ALIASES
DOMAIN_GUIDANCE = policy.DOMAIN_GUIDANCE
run_command = runtime.run_command
RUNTIME_MAX_DEPTH = 64
AUTHENTICATION_KEYS = frozenset(
    {
        "access_token",
        "app_secret",
        "authorization",
        "authorization_header",
        "client_secret",
        "code_verifier",
        "cookie",
        "credential",
        "credentials",
        "device_code",
        "password",
        "refresh_token",
        "tenant_access_token",
        "user_access_token",
        "verification_code",
        "verification_uri",
        "verification_url",
    }
)


def utc_now() -> datetime:
    return state.utc_now()


def isoformat(value: datetime | str | None) -> str:
    return state.isoformat(value)


def parse_time(value: Any) -> datetime | None:
    return state.parse_time(value)


def runtime_root(repo: Path | str) -> Path:
    return state.runtime_root(repo)


def active_registry_path(repo: Path | str) -> Path:
    return state.active_registry_path(repo)


def snapshots_dir(repo: Path | str) -> Path:
    return state.snapshots_dir(repo)


def ensure_runtime(repo: Path | str) -> None:
    state.ensure_runtime(repo)


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def bounded_runtime_string(value: Any) -> str:
    return str(value or "")


def sanitize_runtime_value(value: Any, *, depth: int = 0) -> Any:
    if depth >= RUNTIME_MAX_DEPTH:
        raise ValueError("runtime operation capsule exceeds the maximum nesting depth")
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                continue
            normalized_key = key.strip().lower().replace("-", "_")
            if normalized_key in AUTHENTICATION_KEYS:
                continue
            sanitized = sanitize_runtime_value(item, depth=depth + 1)
            if sanitized is not None:
                result[key] = sanitized
        return result
    if isinstance(value, (list, tuple)):
        return [
            sanitized
            for item in value
            if (sanitized := sanitize_runtime_value(item, depth=depth + 1)) is not None
        ]
    if isinstance(value, str):
        return bounded_runtime_string(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return bounded_runtime_string(value)


def canonical_domain(value: str | None) -> str:
    return policy.canonical_domain(value)


def action_domain(action: str) -> str:
    return policy.action_domain(action)


def string_tokens(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return []


def expansion_domains(request_payload: dict[str, Any]) -> list[str]:
    hints = as_dict(request_payload.get("dispatch_hints"))
    values = [
        *string_tokens(hints.get("expand_resources")),
        *string_tokens(hints.get("domains")),
    ]
    domains: list[str] = []
    for value in values:
        domain = canonical_domain(value)
        if domain and domain not in domains:
            domains.append(domain)
    return domains


def guidance_domains(action: str, request_payload: dict[str, Any] | None = None) -> list[str]:
    domains: list[str] = []
    primary = action_domain(action)
    if primary:
        domains.append(primary)
    for domain in expansion_domains(request_payload or {}):
        if domain not in domains:
            domains.append(domain)
    return domains


def lark_cli_executable() -> str | None:
    explicit = os.environ.get("LARK_CLI_PATH")
    if explicit:
        path = Path(explicit).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    return shutil.which("lark-cli")


def embedded_skill_inventory() -> dict[str, Any]:
    executable = lark_cli_executable()
    if executable is None:
        return {"ok": False, "skills": set(), "errors": ["lark-cli unavailable"]}
    result = run_command([executable, "skills", "list", "--json"], timeout=30)
    contract = runtime.validate_json_result(
        result,
        required_fields=("skills",),
        require_ok_envelope=True,
    )
    names: set[str] = set()
    payload = contract.get("payload")
    if contract["ok"] and isinstance(payload, dict):
        for item in as_list(payload.get("skills")):
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                names.add(item["name"])
    return {"ok": bool(contract["ok"]), "skills": names, "errors": contract["errors"]}


def resolve_guidance_sources(
    action: str,
    request_payload: dict[str, Any] | None = None,
    *,
    skill_roots: list[Path] | tuple[Path, ...] | None = None,
) -> list[dict[str, Any]]:
    # `skill_roots` remains accepted for call compatibility but is intentionally
    # ignored. Local paths are not a trusted guidance transport.
    del skill_roots
    inventory = embedded_skill_inventory()
    available = set(inventory.get("skills") or set())
    sources: list[dict[str, Any]] = []
    for domain in guidance_domains(action, request_payload):
        if domain not in DOMAIN_GUIDANCE:
            sources.append(
                {
                    "source_type": "blocker",
                    "domain": domain,
                    "name": "unmapped-domain",
                    "status": "blocked",
                    "reason": (
                        "No trusted typed-domain guidance mapping is available; "
                        "explicit raw OpenAPI authorization is required."
                    ),
                }
            )
            continue
        guidance = policy.guidance_for_domain(domain)
        for skill_name in guidance["skills"]:
            if skill_name not in available:
                continue
            sources.append(
                {
                    "source_type": "cli_embedded_skill",
                    "domain": domain,
                    "name": skill_name,
                    "status": "available",
                    "argv": ["lark-cli", "skills", "read", skill_name],
                    "provenance": "version-matched lark-cli embedded skill",
                }
            )
        for command in guidance["cli_help"]:
            sources.append(
                {
                    "source_type": "cli_help",
                    "domain": domain,
                    "name": f"{domain}-help",
                    "status": "available" if lark_cli_executable() else "unavailable",
                    "command": ["lark-cli", *[str(part) for part in command]],
                }
            )
    return sources


def is_write_action(action: str, hints: dict[str, Any] | None = None) -> bool:
    return policy.classify_action(action, hints) in {policy.RISK_WRITE, policy.RISK_HIGH}


def compact_resource_object(item: Any) -> dict[str, Any] | None:
    return state.sanitize_resource(item)


def compact_resource_objects(items: Any) -> list[dict[str, Any]]:
    return state.sanitize_resources(as_list(items))


def extract_resource_objects(payload: dict[str, Any]) -> list[dict[str, Any]]:
    handoff = as_dict(payload.get("handoff_context"))
    known = as_list(handoff.get("known_resources"))
    target = as_dict(payload.get("target"))
    target_resource: dict[str, Any] = {}
    if target:
        target_resource["type"] = target.get("type") or action_domain(str(payload.get("action") or ""))
        for key, value in target.items():
            if key == "type":
                continue
            if key.endswith("_token") or key.endswith("_id") or key == "id":
                target_resource["id"] = value
                break
    candidates = [*known]
    if target_resource.get("id"):
        candidates.append(target_resource)
    return state.sanitize_resources(candidates)


def extract_resource_refs(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []
    return [str(item["id"]) for item in extract_resource_objects(payload) if item.get("id")]


def affinity_key(action: str, resource_refs: list[str]) -> str:
    suffix = ":".join(sorted(set(resource_refs))) if resource_refs else "none"
    return state.bounded_string(f"{action_domain(action)}:{suffix}")


def stable_request_id(action: str, target: Any, handoff: dict[str, Any]) -> str:
    canonical = json.dumps([action, target, handoff.get("known_resources", [])], sort_keys=True, default=str)
    return f"req-{hashlib.sha256(canonical.encode()).hexdigest()[:16]}"


def normalized_dispatch_hints(action: str, hints: dict[str, Any], risk: str) -> dict[str, Any]:
    identity = str(hints.get("identity") or "unknown")
    if identity not in state.IDENTITY_VALUES:
        identity = "unknown"
    normalized = {
        "identity": identity,
        "profile": state.bounded_identifier(hints.get("profile"), "unknown"),
        "direct_allowed": bool(hints.get("direct_allowed", True)),
        "read_only": bool(hints.get("read_only", False)),
        "bounded": bool(hints.get("bounded", False)),
        "single_domain": bool(hints.get("single_domain", False)),
        "cross_domain": bool(hints.get("cross_domain", False)),
        "raw_openapi": bool(hints.get("raw_openapi", False)),
        "large_or_paginated": bool(hints.get("large_or_paginated", False)),
        "requires_auth_profile_change": bool(hints.get("requires_auth_profile_change", False)),
        "side_effects": bool(hints.get("side_effects", hints.get("side_effect", False))),
        "explicit_subagent": bool(hints.get("explicit_subagent", False)),
        "expand_resources": string_tokens(hints.get("expand_resources")),
        "domains": string_tokens(hints.get("domains")),
    }
    rejected: list[str] = []
    if risk != policy.RISK_READ:
        if normalized["direct_allowed"]:
            rejected.append("direct_allowed conflicts with classified risk")
        if normalized["read_only"]:
            rejected.append("read_only conflicts with classified risk")
        if hints.get("side_effects") is False:
            rejected.append("side_effects=false cannot downgrade a mutating action")
        normalized["direct_allowed"] = False
        normalized["read_only"] = False
    if action_domain(action) == "openapi":
        normalized["raw_openapi"] = True
        normalized["direct_allowed"] = False
    if rejected:
        normalized["rejected_hints"] = rejected
    return normalized


def cli_execution_contract(hints: dict[str, Any]) -> dict[str, Any]:
    identity = str(hints.get("identity") or "unknown")
    profile = str(hints.get("profile") or "unknown")
    required_global_args: list[str] = []
    if identity in {"user", "bot"}:
        required_global_args.extend(["--as", identity])
    if profile != "unknown":
        required_global_args.extend(["--profile", profile])
    return {
        "identity": identity,
        "profile": profile,
        "required_global_args": required_global_args,
        "forbid_identity_fallback": True,
    }


def normalize_delegation_request(payload: dict[str, Any]) -> dict[str, Any]:
    action = str(payload.get("action") or "").strip().lower().replace("_", "-")
    raw_hints = as_dict(payload.get("dispatch_hints"))
    risk = policy.classify_action(action, raw_hints)
    hints = normalized_dispatch_hints(action, raw_hints, risk)
    handoff_input = as_dict(payload.get("handoff_context"))
    resources = extract_resource_objects(payload)
    resource_refs = [str(item["id"]) for item in resources]
    trust_warnings: list[str] = []
    if payload.get("guidance_sources"):
        trust_warnings.append("caller guidance source rejected; only lark-cli embedded guidance is trusted")
    freshness = state.sanitize_freshness(handoff_input.get("freshness"))
    safe_target = sanitize_runtime_value(payload.get("target"))
    if not isinstance(safe_target, dict):
        safe_target = {}
    safe_evidence_request = sanitize_runtime_value(payload.get("evidence_request"))
    if not isinstance(safe_evidence_request, dict):
        safe_evidence_request = {}
    safe_content = sanitize_runtime_value(payload.get("content"))
    if not isinstance(safe_content, dict):
        safe_content = {}
    normalized = {
        "request_id": state.bounded_string(
            payload.get("request_id") or stable_request_id(action, payload.get("target"), handoff_input)
        ),
        "action": action,
        "domain": action_domain(action),
        "goal": bounded_runtime_string(payload.get("goal")),
        "intent": bounded_runtime_string(payload.get("intent")),
        "question": bounded_runtime_string(payload.get("question")),
        "target": safe_target,
        "handoff_context": {
            "user_goal": sanitize_runtime_value(handoff_input.get("user_goal")),
            "parent_context": sanitize_runtime_value(handoff_input.get("parent_context")) or [],
            "known_resources": resources,
            "prior_evidence_pack": sanitize_runtime_value(
                handoff_input.get("prior_evidence_pack")
            )
            or {},
            "freshness": freshness,
            "non_goals": sanitize_runtime_value(handoff_input.get("non_goals")) or [],
        },
        "dispatch_hints": hints,
        "cli_execution": cli_execution_contract(hints),
        "risk_class": risk,
        "resource_refs": resource_refs,
        "affinity_key": affinity_key(action, resource_refs),
        "evidence_request": safe_evidence_request,
        "content": safe_content,
        "constraints": sanitize_runtime_value(payload.get("constraints")) or [],
        "expected_output": state.bounded_string(payload.get("expected_output") or "evidence_pack"),
        "success_criteria": sanitize_runtime_value(payload.get("success_criteria")) or [],
        "stop_conditions": sanitize_runtime_value(payload.get("stop_conditions")) or [],
        "return_format": state.bounded_string(payload.get("return_format") or "json"),
        "cache_policy": payload.get("cache_policy", "enabled"),
        "trust_boundary_warnings": trust_warnings,
    }
    normalized["guidance_sources"] = resolve_guidance_sources(action, {**payload, "dispatch_hints": hints})
    return normalized


def normalize_agent_result(payload: dict[str, Any]) -> dict[str, Any]:
    progress = as_dict(payload.get("progress"))
    update = as_dict(payload.get("context_cache_update"))
    provenance = as_dict(update.get("provenance"))
    status_value = str(payload.get("status") or "").strip().upper()
    if status_value not in {"PASS", "BLOCKED", "FAILED"}:
        status_value = "UNKNOWN"
    progress_state = str(progress.get("state") or "").strip().lower()
    if progress_state not in {"active", "complete", "blocked", "failed"}:
        progress_state = ""
    return {
        "status": status_value,
        "action": state.bounded_identifier(payload.get("action")),
        "identity": (
            str(payload.get("identity"))
            if str(payload.get("identity")) in state.IDENTITY_VALUES
            else "none"
        ),
        "profile": state.bounded_identifier(payload.get("profile"), "unknown"),
        "progress": {"state": progress_state},
        "resource_refs": state.sanitize_resources(as_list(update.get("resource_refs"))),
        "freshness": state.sanitize_freshness(update.get("freshness")),
        "provenance_classifications": [
            state.provenance_source(
                provenance.get("source_type"),
                fallback="unknown",
            )
        ],
        "excluded_content_classes": list(state.EXCLUDED_CONTENT_CLASSES),
    }


def read_active_registry(repo: Path | str) -> dict[str, Any]:
    return state.read_active_registry(repo)


def write_active_registry(repo: Path | str, registry: dict[str, Any]) -> None:
    state.write_active_registry(repo, registry)


def record_active_agent(
    repo: Path | str,
    *,
    agent_id: str,
    request: dict[str, Any],
    last_progress_at: datetime | str | None = None,
) -> dict[str, Any]:
    normalized = request if request.get("risk_class") else normalize_delegation_request(request)
    progress_time = parse_time(last_progress_at) if isinstance(last_progress_at, str) else last_progress_at
    progress_time = progress_time or utc_now()
    registry = state.read_active_registry(repo, now=progress_time)
    hints = as_dict(normalized.get("dispatch_hints"))
    entry = {
        "schema_version": SCHEMA_VERSION,
        "agent_id": agent_id,
        "request_id": normalized.get("request_id"),
        "action": normalized.get("action"),
        "domain": normalized.get("domain"),
        "affinity_key": normalized.get("affinity_key"),
        "resource_refs": list(normalized.get("resource_refs") or [])[: state.MAX_RESOURCE_REFS],
        "identity": hints.get("identity"),
        "profile": hints.get("profile"),
        "risk_class": normalized.get("risk_class"),
        "state": "active",
        "last_progress_at": isoformat(progress_time),
    }
    sanitized_entry = state.sanitize_active_entry(entry)
    if sanitized_entry is None:
        return {"schema_version": SCHEMA_VERSION, "state": "rejected", "recorded": False}
    agents = [
        item
        for item in registry.get("agents", [])
        if item.get("agent_id") != sanitized_entry["agent_id"]
    ]
    registry["agents"] = [sanitized_entry, *agents]
    state.write_active_registry(repo, registry)
    return sanitized_entry


def snapshot_id_for(request: dict[str, Any], agent_id: str | None, created_at: str) -> str:
    canonical = json.dumps(
        [request.get("request_id"), request.get("affinity_key"), agent_id, created_at],
        sort_keys=True,
    )
    return f"snapshot-{hashlib.sha256(canonical.encode()).hexdigest()[:20]}"


def write_context_snapshot(
    repo: Path | str,
    request: dict[str, Any],
    result: dict[str, Any],
    *,
    agent_id: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = now or utc_now()
    normalized = request if request.get("risk_class") else normalize_delegation_request(request)
    allowed, reason = state.cache_allowed(str(normalized.get("domain") or ""), normalized.get("cache_policy"))
    base = {
        "persisted": False,
        "policy_reason": reason,
        "excluded_content_classes": list(state.EXCLUDED_CONTENT_CLASSES),
    }
    identity_contract = validate_execution_identity(normalized, result)
    if not identity_contract["ok"]:
        return {
            **base,
            "policy_reason": identity_contract["reason"],
            "identity_contract": identity_contract,
        }
    if not allowed:
        return base
    created_at = isoformat(current)
    snapshot_id = snapshot_id_for(normalized, agent_id, created_at)
    payload = state.snapshot_payload(
        normalized,
        result,
        snapshot_id=snapshot_id,
        agent_id=agent_id,
        now=current,
    )
    contract_error = state.snapshot_contract_error(payload) or state.snapshot_temporal_error(
        payload,
        now=current,
    )
    if contract_error:
        return {
            **base,
            "policy_reason": f"invalid_metadata:{contract_error}",
        }
    path = snapshots_dir(repo) / f"{snapshot_id}.json"
    state.atomic_write_json(repo, path, payload)
    _, rejected = state.scan_snapshots(repo, now=current)
    if not path.exists():
        rejection = next(
            (
                entry.split(": ", 1)[1]
                for entry in rejected
                if entry.startswith(f"{path.name}: ")
            ),
            "snapshot pruned after write",
        )
        return {
            **base,
            "policy_reason": f"invalid_metadata:{rejection}",
        }
    return {
        **base,
        "persisted": True,
        "snapshot_id": snapshot_id,
        "path": str(path),
        "snapshot": payload,
    }


def list_context_snapshots(repo: Path | str) -> list[dict[str, Any]]:
    snapshots, _ = state.scan_snapshots(repo)
    return snapshots


def direct_eligible(request: dict[str, Any]) -> bool:
    hints = as_dict(request.get("dispatch_hints"))
    guidance_blocked = any(
        isinstance(source, dict)
        and (
            source.get("source_type") == "blocker"
            or source.get("status") == "blocked"
        )
        for source in request.get("guidance_sources") or []
    )
    return bool(
        request.get("risk_class") == policy.RISK_READ
        and hints.get("direct_allowed")
        and hints.get("read_only")
        and hints.get("bounded")
        and hints.get("single_domain")
        and not hints.get("cross_domain")
        and not hints.get("raw_openapi")
        and not hints.get("large_or_paginated")
        and not hints.get("requires_auth_profile_change")
        and not hints.get("side_effects")
        and not hints.get("explicit_subagent")
        and not guidance_blocked
    )


def validate_execution_identity(
    request: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    hints = as_dict(request.get("dispatch_hints"))
    expected_identity = str(hints.get("identity") or "unknown")
    expected_profile = str(hints.get("profile") or "unknown")
    observed_identity = str(result.get("identity") or "none")
    observed_profile = str(result.get("profile") or "unknown")
    reason: str | None = None
    if expected_identity in {"user", "bot"} and observed_identity != expected_identity:
        reason = f"identity_mismatch:{expected_identity}!={observed_identity}"
    elif expected_profile != "unknown" and observed_profile != expected_profile:
        reason = f"profile_mismatch:{expected_profile}!={observed_profile}"
    return {
        "ok": reason is None,
        "reason": reason,
        "expected_identity": expected_identity,
        "observed_identity": observed_identity,
        "expected_profile": expected_profile,
        "observed_profile": observed_profile,
        "fallback_forbidden": True,
    }


def shares_resources(request: dict[str, Any], candidate: dict[str, Any]) -> bool:
    requested = set(str(item) for item in request.get("resource_refs") or [])
    candidate_values: set[str] = set()
    for item in candidate.get("resource_refs") or []:
        candidate_values.add(str(item.get("id"))) if isinstance(item, dict) else candidate_values.add(str(item))
    return bool(requested and requested.intersection(candidate_values))


def snapshot_freshness_rejection_reason(
    request: dict[str, Any],
    candidate: dict[str, Any],
) -> str | None:
    freshness = as_dict(candidate.get("freshness"))
    if freshness.get("require_refetch") is True:
        return "snapshot freshness require_refetch disables reuse"
    revision = state.bounded_identifier(freshness.get("known_revision_id"))
    timestamp = state.parse_time(
        freshness.get("observed_at") or freshness.get("known_timestamp")
    )
    raw_source = freshness.get("source") or freshness.get("known_source")
    source = state.provenance_source(raw_source, fallback="unknown")
    if not revision:
        return "missing freshness revision"
    if timestamp is None:
        return "missing freshness timestamp"
    if source == "unknown" and str(raw_source or "").strip().lower() != "unknown":
        return "missing freshness source"
    provenance = as_dict(candidate.get("provenance"))
    if (
        state.provenance_source(provenance.get("source_type"), fallback="unknown")
        == "unknown"
        and provenance.get("source_type") != "unknown"
    ):
        return "missing provenance source"
    if state.parse_time(provenance.get("observed_at")) is None:
        return "missing provenance timestamp"

    requested = as_dict(as_dict(request.get("handoff_context")).get("freshness"))
    requested_revision = state.bounded_identifier(requested.get("known_revision_id"))
    if requested_revision and requested_revision != revision:
        return "freshness revision mismatch"
    requested_time = state.parse_time(
        requested.get("observed_at") or requested.get("known_timestamp")
    )
    if requested_time is not None and timestamp < requested_time:
        return "freshness timestamp is older than current request"
    requested_source_raw = requested.get("source") or requested.get("known_source")
    if requested_source_raw:
        requested_source = state.provenance_source(
            requested_source_raw,
            fallback="unknown",
        )
        if requested_source != source:
            return "freshness source mismatch"
    return None


def candidate_rejection_reason(request: dict[str, Any], candidate: dict[str, Any]) -> str | None:
    hints = as_dict(request.get("dispatch_hints"))
    if candidate.get("identity") != hints.get("identity") or candidate.get("profile") != hints.get("profile"):
        return "identity/profile mismatch"
    if request.get("risk_class") != candidate.get("risk_class"):
        if candidate.get("risk_class") == policy.RISK_READ:
            return "read context cannot seed write or unknown operation"
        return "risk classification mismatch"
    if candidate.get("affinity_key") != request.get("affinity_key") and not shares_resources(request, candidate):
        return "resource affinity mismatch"
    if "snapshot_id" in candidate or "provenance" in candidate:
        freshness_reason = snapshot_freshness_rejection_reason(request, candidate)
        if freshness_reason:
            return freshness_reason
    return None


def reconstruct_request_from_snapshot(request: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    reconstructed = json.loads(json.dumps(request))
    handoff = as_dict(reconstructed.get("handoff_context"))
    handoff["known_resources"] = state.sanitize_resources(snapshot.get("resource_refs") or [])
    handoff["prior_evidence_pack"] = {}
    # The current caller's freshness contract is authoritative.
    handoff["freshness"] = as_dict(request.get("handoff_context")).get("freshness", {})
    reconstructed["handoff_context"] = handoff
    return reconstructed


def runtime_boundary() -> dict[str, Any]:
    return {
        "subagent_primitives": "parent_agent_runtime",
        "helper_invokes_subagents": False,
        "fresh_subagent_fork_turns": "none",
        "active_registry_authoritative": False,
    }


def prepare_dispatch_report(
    repo: Path | str,
    payload: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = now or utc_now()
    request = normalize_delegation_request(payload)
    hints = as_dict(request.get("dispatch_hints"))
    registry = state.read_active_registry(repo, now=current)
    snapshots, pruned = state.scan_snapshots(repo, now=current)
    rejected = list(pruned)
    require_refetch = bool(
        as_dict(as_dict(request.get("handoff_context")).get("freshness")).get("require_refetch")
    )
    if require_refetch:
        rejected.append("require_refetch requested current evidence; cached reconstruction disabled")

    active_candidate: dict[str, Any] | None = None
    for candidate in registry.get("agents", []):
        reason = candidate_rejection_reason(request, candidate)
        if reason:
            rejected.append(f"active {candidate.get('agent_id')}: {reason}")
            continue
        active_candidate = candidate
        break

    if active_candidate is not None:
        dispatch = {
            "decision": "reuse_active_candidate",
            "reason": "matching active metadata requires current Codex list_agents confirmation",
            "agent_id": active_candidate.get("agent_id"),
            "requires_runtime_confirmation": True,
            "registry_authoritative": False,
            "guidance_sources": request["guidance_sources"],
            "rejected_candidates": rejected,
        }
    elif direct_eligible(request):
        dispatch = {
            "decision": "direct",
            "reason": "bounded low-risk read with explicit direct eligibility",
            "guidance_sources": request["guidance_sources"],
            "rejected_candidates": rejected,
        }
    else:
        selected: dict[str, Any] | None = None
        if not require_refetch:
            for candidate in snapshots:
                reason = candidate_rejection_reason(request, candidate)
                if reason:
                    rejected.append(f"snapshot {candidate.get('snapshot_id')}: {reason}")
                    continue
                selected = candidate
                break
        if selected is not None:
            dispatch = {
                "decision": "reconstruct_from_cache",
                "reason": "fresh compatible metadata capsule available",
                "snapshot_id": selected.get("snapshot_id"),
                "reconstructed_request": reconstruct_request_from_snapshot(request, selected),
                "fork_turns": "none",
                "guidance_sources": request["guidance_sources"],
                "rejected_candidates": rejected,
            }
        else:
            dispatch = {
                "decision": "fresh_subagent",
                "reason": "operation is not direct-eligible and no confirmed active or reusable metadata exists",
                "fork_turns": "none",
                "requires_runtime_confirmation": False,
                "guidance_sources": request["guidance_sources"],
                "rejected_candidates": rejected,
            }
    return {
        "status": "PASS",
        "request": request,
        "dispatch": dispatch,
        "runtime_boundary": runtime_boundary(),
        "state_paths": state_paths(repo),
    }


def state_paths(repo: Path | str) -> dict[str, str]:
    return {
        "runtime_root": str(runtime_root(repo)),
        "active_registry": str(active_registry_path(repo)),
        "snapshots": str(snapshots_dir(repo)),
    }


def read_request_json(path: str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON input must contain an object")
    return payload


def terminal_result(payload: dict[str, Any]) -> bool:
    status_value = str(payload.get("status") or "").strip().lower()
    progress_state = str(as_dict(payload.get("progress")).get("state") or "").strip().lower()
    return status_value in state.TERMINAL_STATES or progress_state in state.TERMINAL_STATES


def run_cli(argv: list[str] | None = None) -> tuple[int, dict[str, Any]]:
    parser = argparse.ArgumentParser(description="Prepare and maintain FeishuOps metadata-only continuity.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--repo", required=True)
    prepare.add_argument("--request-json", required=True)
    prepare.add_argument("--json", action="store_true")

    active = subparsers.add_parser("record-active")
    active.add_argument("--repo", required=True)
    active.add_argument("--request-json", required=True)
    active.add_argument("--agent-id", required=True)
    active.add_argument("--json", action="store_true")

    result_parser = subparsers.add_parser("record-result")
    result_parser.add_argument("--repo", required=True)
    result_parser.add_argument("--request-json", required=True)
    result_parser.add_argument("--result-json", required=True)
    result_parser.add_argument("--agent-id")
    result_parser.add_argument("--json", action="store_true")

    listing = subparsers.add_parser("list")
    listing.add_argument("--repo", required=True)
    listing.add_argument("--json", action="store_true")

    purge_parser = subparsers.add_parser("purge")
    purge_parser.add_argument("--repo", required=True)
    purge_parser.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "prepare":
        report = prepare_dispatch_report(args.repo, read_request_json(args.request_json))
    elif args.command == "record-active":
        request = normalize_delegation_request(read_request_json(args.request_json))
        entry = record_active_agent(args.repo, agent_id=args.agent_id, request=request)
        report = {"status": "PASS", "active_agent": entry, "state_paths": state_paths(args.repo)}
    elif args.command == "record-result":
        request = normalize_delegation_request(read_request_json(args.request_json))
        raw_result = read_request_json(args.result_json)
        identity_contract = validate_execution_identity(request, raw_result)
        snapshot = (
            write_context_snapshot(
                args.repo,
                request,
                raw_result,
                agent_id=args.agent_id,
            )
            if identity_contract["ok"]
            else {
                "persisted": False,
                "policy_reason": identity_contract["reason"],
                "identity_contract": identity_contract,
                "excluded_content_classes": list(state.EXCLUDED_CONTENT_CLASSES),
            }
        )
        retired = state.retire_active_agent(args.repo, args.agent_id) if terminal_result(raw_result) else False
        report = {
            "status": "PASS" if identity_contract["ok"] else "BLOCKED",
            "result": normalize_agent_result(raw_result),
            "identity_contract": identity_contract,
            "snapshot": snapshot,
            "persisted": snapshot.get("persisted", False),
            "retired": retired,
            "excluded_content_classes": list(state.EXCLUDED_CONTENT_CLASSES),
            "state_paths": state_paths(args.repo),
        }
    elif args.command == "purge":
        report = state.purge(args.repo)
        report["state_paths"] = state_paths(args.repo)
    else:
        snapshots, rejected = state.scan_snapshots(args.repo)
        report = {
            "status": "PASS",
            "active": state.read_active_registry(args.repo),
            "snapshots": snapshots,
            "pruned": rejected,
            "state_paths": state_paths(args.repo),
        }
    return 0, report


def main(argv: list[str] | None = None) -> int:
    exit_code, payload = run_cli(argv)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
