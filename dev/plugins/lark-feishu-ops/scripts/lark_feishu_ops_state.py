#!/usr/bin/env python3
"""Bounded metadata-only continuity state for Lark Feishu Ops."""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


RUNTIME_ROOT = Path(".dev-flow") / "lark-feishu-ops" / "agent-context"
ACTIVE_REGISTRY = "active_agents.json"
SNAPSHOT_DIR = "snapshots"
SCHEMA_VERSION = "2.0"
MAX_SNAPSHOTS = 64
MAX_RESOURCE_REFS = 32
MAX_STRING_BYTES = 256
MAX_FILE_BYTES = 32 * 1024
MAX_TTL_SECONDS = 24 * 60 * 60
MAX_CLOCK_SKEW_SECONDS = 5 * 60
ACTIVE_IDLE_SECONDS = 30 * 60
SENSITIVE_DOMAINS = frozenset(
    {
        "approval",
        "attendance",
        "auth",
        "contact",
        "im",
        "mail",
        "minutes",
        "note",
        "okr",
        "profile",
        "vc",
    }
)
TERMINAL_STATES = frozenset({"blocked", "cancelled", "complete", "completed", "failed", "pass"})

RESOURCE_FIELDS = (
    "type",
    "id",
    "revision",
    "revision_id",
    "sheet_id",
    "table_id",
    "chat_id",
    "message_id",
    "event_id",
    "meeting_id",
    "task_id",
    "approval_id",
)
FRESHNESS_FIELDS = (
    "known_revision_id",
    "known_timestamp",
    "known_source",
    "observed_at",
    "source",
    "require_refetch",
)
ACTIVE_ENTRY_FIELDS = frozenset(
    {
        "schema_version",
        "agent_id",
        "request_id",
        "action",
        "domain",
        "affinity_key",
        "resource_refs",
        "identity",
        "profile",
        "risk_class",
        "state",
        "last_progress_at",
    }
)
SNAPSHOT_FIELDS = frozenset(
    {
        "schema_version",
        "snapshot_id",
        "agent_id",
        "request_id",
        "action",
        "domain",
        "affinity_key",
        "identity",
        "profile",
        "risk_class",
        "resource_refs",
        "freshness",
        "provenance",
        "provenance_classifications",
        "created_at",
        "expires_at",
    }
)
PROVENANCE_FIELDS = frozenset({"source_type", "observed_at"})
PROVENANCE_SOURCE_TYPES = frozenset(
    {
        "cli_embedded_skill",
        "cli_help",
        "cli_schema",
        "lark_cli",
        "openapi",
        "unknown",
    }
)
IDENTITY_VALUES = frozenset({"bot", "mixed", "none", "user"})
RISK_VALUES = frozenset({"high-risk-write", "read", "unknown", "write"})
METADATA_IDENTIFIER = re.compile(r"^[A-Za-z0-9._:/=@+-]{1,256}$")
SENSITIVE_METADATA_MARKERS = (
    "access_token",
    "app_secret",
    "authorization",
    "bearer",
    "client_secret",
    "credential",
    "password",
    "private_key",
    "refresh_token",
    "secret",
    "token",
)
EXCLUDED_CONTENT_CLASSES = [
    "authentication_material",
    "cli_secret_arguments",
    "document_content",
    "table_rows",
    "mail_bodies",
    "contact_data",
    "raw_evidence",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat(value: datetime | str | None) -> str:
    if value is None:
        value = utc_now()
    if isinstance(value, str):
        parsed = parse_time(value)
        return parsed.isoformat().replace("+00:00", "Z") if parsed else bounded_string(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
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


def bounded_string(value: Any, max_bytes: int = MAX_STRING_BYTES) -> str:
    encoded = str(value or "").encode("utf-8")
    if len(encoded) <= max_bytes:
        return encoded.decode("utf-8")
    return encoded[:max_bytes].decode("utf-8", errors="ignore")


def bounded_identifier(value: Any, fallback: str = "") -> str:
    candidate = bounded_string(value).strip()
    lowered = candidate.lower().replace("-", "_")
    if not candidate or not METADATA_IDENTIFIER.fullmatch(candidate):
        return fallback
    if any(marker in lowered for marker in SENSITIVE_METADATA_MARKERS):
        return fallback
    return candidate


def provenance_source(value: Any, fallback: str = "lark_cli") -> str:
    candidate = str(value or "").strip().lower().replace("-", "_")
    return candidate if candidate in PROVENANCE_SOURCE_TYPES else fallback


def canonical_timestamp(value: Any) -> str | None:
    if isinstance(value, datetime):
        return isoformat(value)
    parsed = parse_time(value)
    return isoformat(parsed) if parsed is not None else None


def _contained(repo: Path | str, path: Path) -> bool:
    base = Path(repo).expanduser().resolve()
    try:
        path.absolute().relative_to(base)
    except ValueError:
        return False
    return True


def _reject_symlink_components(repo: Path | str, path: Path) -> None:
    base = Path(repo).expanduser().resolve()
    if not _contained(base, path):
        raise ValueError("continuity path escapes repository")
    current = base
    relative = path.absolute().relative_to(base)
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise RuntimeError(f"continuity path contains symlink: {current}")


def ensure_runtime(repo: Path | str) -> None:
    root = runtime_root(repo)
    directory = snapshots_dir(repo)
    _reject_symlink_components(repo, root)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    _reject_symlink_components(repo, directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        root.chmod(0o700)
        directory.chmod(0o700)
    except OSError:
        pass


def atomic_write_json(repo: Path | str, path: Path, payload: Any) -> None:
    ensure_runtime(repo)
    _reject_symlink_components(repo, path)
    if path.exists() and (path.is_symlink() or not path.is_file()):
        raise RuntimeError(f"refusing unsafe continuity target: {path}")
    data = serialized_json_bytes(payload)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("continuity metadata exceeds 32 KiB limit")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
        path.chmod(0o600)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        temporary_path.unlink(missing_ok=True)
        raise


def serialized_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def serialized_json_size(payload: Any) -> int:
    return len(serialized_json_bytes(payload))


def safe_unlink(repo: Path | str, path: Path) -> bool:
    _reject_symlink_components(repo, path.parent)
    if path.is_symlink():
        path.unlink(missing_ok=True)
        return True
    if path.exists() and path.is_file():
        path.unlink()
        return True
    return False


def read_json_file(repo: Path | str, path: Path, default: Any) -> Any:
    try:
        _reject_symlink_components(repo, path)
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            return default
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError, ValueError):
        return default
    return payload


def sanitize_resource(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    resource: dict[str, Any] = {}
    for key in RESOURCE_FIELDS:
        value = item.get(key)
        if isinstance(value, (str, int)) and str(value):
            candidate = bounded_identifier(value)
            if candidate:
                resource[key] = candidate
    if "id" not in resource:
        for key in RESOURCE_FIELDS[4:]:
            if key in resource:
                resource["id"] = resource[key]
                break
    if not resource.get("id"):
        return None
    resource.setdefault("type", "resource")
    return resource


def sanitize_resources(items: Iterable[Any]) -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        resource = sanitize_resource(item)
        if resource is None:
            continue
        key = json.dumps(resource, sort_keys=True, ensure_ascii=False)
        if key in seen:
            continue
        seen.add(key)
        resources.append(resource)
        if len(resources) >= MAX_RESOURCE_REFS:
            break
    return resources


def sanitize_active_entry(entry: Any) -> dict[str, Any] | None:
    if not isinstance(entry, dict) or entry.get("schema_version") != SCHEMA_VERSION:
        return None
    agent_id = bounded_identifier(entry.get("agent_id"))
    request_id = bounded_identifier(entry.get("request_id"))
    action = bounded_identifier(entry.get("action"))
    domain = bounded_identifier(entry.get("domain"))
    affinity = bounded_identifier(entry.get("affinity_key"))
    progress = canonical_timestamp(entry.get("last_progress_at"))
    if not all((agent_id, request_id, action, domain, affinity, progress)):
        return None
    resource_refs: list[str] = []
    for item in entry.get("resource_refs") or []:
        value = item.get("id") if isinstance(item, dict) else item
        candidate = bounded_identifier(value)
        if candidate and candidate not in resource_refs:
            resource_refs.append(candidate)
        if len(resource_refs) >= MAX_RESOURCE_REFS:
            break
    identity = str(entry.get("identity") or "user")
    risk = str(entry.get("risk_class") or "unknown")
    return {
        "schema_version": SCHEMA_VERSION,
        "agent_id": agent_id,
        "request_id": request_id,
        "action": action,
        "domain": domain,
        "affinity_key": affinity,
        "resource_refs": resource_refs,
        "identity": identity if identity in IDENTITY_VALUES else "user",
        "profile": bounded_identifier(entry.get("profile"), "default"),
        "risk_class": risk if risk in RISK_VALUES else "unknown",
        "state": "active",
        "last_progress_at": progress,
    }


def resource_revisions(resources: Iterable[dict[str, Any]]) -> set[str]:
    return {
        str(resource[key])
        for resource in resources
        for key in ("revision", "revision_id")
        if isinstance(resource, dict) and resource.get(key) not in (None, "")
    }


def sanitize_freshness(
    value: Any,
    *,
    allowed_revisions: set[str] | None = None,
    default_observed_at: datetime | str | None = None,
    default_source: str | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        value = {}
    result: dict[str, Any] = {}
    if isinstance(value.get("require_refetch"), bool):
        result["require_refetch"] = value["require_refetch"]
    revisions = allowed_revisions or set()
    requested_revision = bounded_identifier(value.get("known_revision_id"))
    if revisions and requested_revision in revisions:
        result["known_revision_id"] = requested_revision
    elif requested_revision:
        result["known_revision_id"] = requested_revision
    for key in ("known_timestamp", "observed_at"):
        timestamp = canonical_timestamp(value.get(key))
        if timestamp:
            result[key] = timestamp
    if not any(key in result for key in ("known_timestamp", "observed_at")):
        timestamp = canonical_timestamp(default_observed_at)
        if timestamp:
            result["observed_at"] = timestamp
    for key in ("known_source", "source"):
        raw = value.get(key)
        if raw in (None, ""):
            continue
        candidate = provenance_source(raw, fallback="unknown")
        if candidate != "unknown" or str(raw).strip().lower() == "unknown":
            result[key] = candidate
    if not any(key in result for key in ("known_source", "source")) and default_source:
        result["source"] = provenance_source(default_source)
    return result


def cache_allowed(domain: str, policy: Any) -> tuple[bool, str]:
    normalized = str(policy or "enabled").strip().lower().replace("_", "-")
    if domain in SENSITIVE_DOMAINS:
        return False, "sensitive_domain_default"
    if normalized in {"disabled", "none", "no-cache", "off", "false"} or policy is False:
        return False, "cache_policy_disabled"
    return True, "enabled"


def snapshot_payload(
    request: dict[str, Any],
    result: dict[str, Any],
    *,
    snapshot_id: str,
    agent_id: str | None,
    now: datetime,
) -> dict[str, Any]:
    handoff = request.get("handoff_context") if isinstance(request.get("handoff_context"), dict) else {}
    update = result.get("context_cache_update") if isinstance(result.get("context_cache_update"), dict) else {}
    request_resources = handoff.get("known_resources") if isinstance(handoff.get("known_resources"), list) else []
    result_resources = update.get("resource_refs") if isinstance(update.get("resource_refs"), list) else []
    resources = sanitize_resources([*request_resources, *result_resources])
    revisions = resource_revisions(resources)
    freshness = sanitize_freshness(
        update.get("freshness"),
        allowed_revisions=revisions,
    )
    ttl_value = (
        (update.get("freshness") or {}).get("ttl_seconds")
        if isinstance(update.get("freshness"), dict)
        else None
    )
    try:
        ttl_seconds = max(1, min(int(ttl_value or MAX_TTL_SECONDS), MAX_TTL_SECONDS))
    except (TypeError, ValueError):
        ttl_seconds = MAX_TTL_SECONDS
    provenance_input = (
        update.get("provenance")
        if isinstance(update.get("provenance"), dict)
        else {}
    )
    source_type = provenance_source(
        provenance_input.get("source_type"),
        fallback="unknown",
    )
    observed_at = canonical_timestamp(provenance_input.get("observed_at"))
    provenance = (
        {"source_type": source_type, "observed_at": observed_at}
        if source_type != "unknown" and observed_at
        else {}
    )
    hints = request.get("dispatch_hints") if isinstance(request.get("dispatch_hints"), dict) else {}
    return {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": bounded_identifier(snapshot_id),
        "agent_id": (bounded_identifier(agent_id) or None) if agent_id else None,
        "request_id": bounded_identifier(request.get("request_id")),
        "action": bounded_identifier(request.get("action")),
        "domain": bounded_identifier(request.get("domain")),
        "affinity_key": bounded_identifier(request.get("affinity_key")),
        "identity": (
            str(hints.get("identity"))
            if str(hints.get("identity")) in IDENTITY_VALUES
            else "user"
        ),
        "profile": bounded_identifier(hints.get("profile"), "default"),
        "risk_class": (
            str(request.get("risk_class"))
            if str(request.get("risk_class")) in RISK_VALUES
            else "unknown"
        ),
        "resource_refs": resources,
        "freshness": freshness,
        "provenance": provenance,
        "provenance_classifications": [source_type] if provenance else [],
        "created_at": isoformat(now),
        "expires_at": isoformat(now + timedelta(seconds=ttl_seconds)),
    }


def values_within_bounds(value: Any) -> bool:
    if isinstance(value, str):
        return len(value.encode("utf-8")) <= MAX_STRING_BYTES
    if isinstance(value, list):
        return len(value) <= MAX_RESOURCE_REFS and all(
            values_within_bounds(item) for item in value
        )
    if isinstance(value, dict):
        return all(
            isinstance(key, str)
            and len(key.encode("utf-8")) <= MAX_STRING_BYTES
            and values_within_bounds(item)
            for key, item in value.items()
        )
    return value is None or isinstance(value, (bool, int, float))


def snapshot_contract_error(payload: dict[str, Any]) -> str | None:
    missing_fields = SNAPSHOT_FIELDS.difference(payload)
    if missing_fields:
        if "expires_at" in missing_fields:
            return "missing expires_at"
        if "freshness" in missing_fields:
            return "missing freshness"
        if "provenance" in missing_fields:
            return "missing provenance"
        return f"missing snapshot fields: {', '.join(sorted(missing_fields))}"
    if set(payload).difference(SNAPSHOT_FIELDS):
        return "unexpected snapshot fields"
    for key in ("snapshot_id", "request_id", "action", "domain", "affinity_key"):
        value = payload.get(key)
        if not isinstance(value, str) or not value or bounded_identifier(value) != value:
            return f"invalid {key}"
    agent_id = payload.get("agent_id")
    if agent_id is not None and (
        not isinstance(agent_id, str)
        or not agent_id
        or bounded_identifier(agent_id) != agent_id
    ):
        return "invalid agent_id"
    if payload.get("identity") not in IDENTITY_VALUES:
        return "invalid identity"
    profile = payload.get("profile")
    if not isinstance(profile, str) or bounded_identifier(profile) != profile:
        return "invalid profile"
    if payload.get("risk_class") not in RISK_VALUES:
        return "invalid risk_class"
    for key in ("created_at", "expires_at"):
        value = payload.get(key)
        if not isinstance(value, str) or canonical_timestamp(value) != value:
            return f"invalid {key}"
    created_at = parse_time(payload.get("created_at"))
    expires_at = parse_time(payload.get("expires_at"))
    if created_at is None or expires_at is None or expires_at <= created_at:
        return "invalid snapshot ttl ordering"
    if expires_at - created_at > timedelta(seconds=MAX_TTL_SECONDS):
        return "snapshot ttl exceeds 24 hours"
    resources = payload.get("resource_refs")
    if not isinstance(resources, list) or sanitize_resources(resources) != resources:
        return "invalid resource metadata"
    freshness = payload.get("freshness")
    if not isinstance(freshness, dict) or not set(freshness).issubset(FRESHNESS_FIELDS):
        return "missing or invalid freshness"
    if "require_refetch" in freshness and not isinstance(
        freshness.get("require_refetch"), bool
    ):
        return "invalid freshness require_refetch"
    if freshness.get("require_refetch") is True:
        return "freshness require_refetch forbids persistence"
    for key in ("known_timestamp", "observed_at"):
        if key in freshness and canonical_timestamp(freshness.get(key)) != freshness.get(key):
            return f"invalid freshness {key}"
    for key in ("known_source", "source"):
        if key in freshness and provenance_source(
            freshness.get(key), fallback="unknown"
        ) != freshness.get(key):
            return f"invalid freshness {key}"
    revisions = resource_revisions(resources)
    revision = bounded_identifier(freshness.get("known_revision_id"))
    if not revision or (revisions and revision not in revisions):
        return "missing or mismatched freshness revision"
    timestamp = canonical_timestamp(
        freshness.get("observed_at") or freshness.get("known_timestamp")
    )
    if timestamp is None:
        return "missing freshness timestamp"
    raw_source = freshness.get("source") or freshness.get("known_source")
    source = provenance_source(raw_source, fallback="unknown")
    if source == "unknown":
        return "missing freshness source"
    provenance = payload.get("provenance")
    if not isinstance(provenance, dict) or set(provenance) != PROVENANCE_FIELDS:
        return "missing or invalid provenance"
    source_type = provenance_source(provenance.get("source_type"), fallback="unknown")
    if source_type == "unknown":
        return "invalid provenance source"
    if canonical_timestamp(provenance.get("observed_at")) is None:
        return "missing provenance timestamp"
    classifications = payload.get("provenance_classifications")
    if (
        not isinstance(classifications, list)
        or classifications != [source_type]
    ):
        return "invalid provenance classifications"
    if not values_within_bounds(payload):
        return "snapshot value limits exceeded"
    if serialized_json_size(payload) > MAX_FILE_BYTES:
        return "snapshot exceeds 32 KiB total limit"
    return None


def snapshot_temporal_error(payload: dict[str, Any], *, now: datetime) -> str | None:
    future_limit = now + timedelta(seconds=MAX_CLOCK_SKEW_SECONDS)
    created = parse_time(payload.get("created_at"))
    if created is None or created > future_limit:
        return "future created_at"
    freshness = payload.get("freshness")
    if isinstance(freshness, dict):
        for key in ("known_timestamp", "observed_at"):
            timestamp = parse_time(freshness.get(key)) if key in freshness else None
            if timestamp is not None and timestamp > future_limit:
                return f"future freshness {key}"
    provenance = payload.get("provenance")
    if isinstance(provenance, dict):
        observed_at = parse_time(provenance.get("observed_at"))
        if observed_at is not None and observed_at > future_limit:
            return "future provenance observed_at"
    return None


def valid_snapshot(repo: Path | str, path: Path, *, now: datetime) -> tuple[dict[str, Any] | None, str | None]:
    try:
        _reject_symlink_components(repo, path)
        if path.is_symlink() or not path.is_file():
            return None, "unsafe snapshot"
        if path.stat().st_size > MAX_FILE_BYTES:
            return None, "oversized snapshot"
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError, ValueError):
        return None, "malformed snapshot"
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        return None, "legacy or invalid schema"
    contract_error = snapshot_contract_error(payload)
    if contract_error:
        return None, contract_error
    temporal_error = snapshot_temporal_error(payload, now=now)
    if temporal_error:
        return None, temporal_error
    expires = parse_time(payload.get("expires_at"))
    if expires is None:
        return None, "missing expires_at"
    if expires <= now:
        return None, "expired snapshot"
    return payload, None


def scan_snapshots(repo: Path | str, *, now: datetime | None = None) -> tuple[list[dict[str, Any]], list[str]]:
    current = now or utc_now()
    directory = snapshots_dir(repo)
    if directory.is_symlink():
        raise RuntimeError("snapshot directory cannot be a symlink")
    if not directory.exists():
        return [], []
    snapshots: list[tuple[Path, dict[str, Any]]] = []
    rejected: list[str] = []
    for path in sorted(directory.glob("*.json")):
        payload, reason = valid_snapshot(repo, path, now=current)
        if payload is None:
            safe_unlink(repo, path)
            rejected.append(f"{path.name}: {reason}")
        else:
            snapshots.append((path, payload))
    snapshots.sort(
        key=lambda item: parse_time(item[1].get("created_at"))
        or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    for path, _ in snapshots[MAX_SNAPSHOTS:]:
        safe_unlink(repo, path)
        rejected.append(f"{path.name}: snapshot count limit")
    return [payload for _, payload in snapshots[:MAX_SNAPSHOTS]], rejected


def read_active_registry(repo: Path | str, *, now: datetime | None = None) -> dict[str, Any]:
    current = now or utc_now()
    path = active_registry_path(repo)
    payload = read_json_file(repo, path, {})
    agents = payload.get("agents") if isinstance(payload, dict) and isinstance(payload.get("agents"), list) else []
    retained: list[dict[str, Any]] = []
    for raw_entry in agents:
        entry = sanitize_active_entry(raw_entry)
        if entry is None:
            continue
        progress = parse_time(entry.get("last_progress_at"))
        if progress is None or current - progress > timedelta(seconds=ACTIVE_IDLE_SECONDS):
            continue
        retained.append(entry)
    registry = bounded_active_registry(retained)
    retained = registry["agents"]
    registry_shape_current = (
        isinstance(payload, dict)
        and set(payload) == {"schema_version", "agents"}
        and payload.get("schema_version") == SCHEMA_VERSION
    )
    if (retained != agents or not registry_shape_current) and (path.exists() or retained):
        atomic_write_json(repo, path, registry)
    return registry


def write_active_registry(repo: Path | str, registry: dict[str, Any]) -> None:
    agents = registry.get("agents") if isinstance(registry.get("agents"), list) else []
    sanitized = [entry for item in agents if (entry := sanitize_active_entry(item)) is not None]
    payload = bounded_active_registry(sanitized)
    atomic_write_json(repo, active_registry_path(repo), payload)


def bounded_active_registry(agents: Iterable[dict[str, Any]]) -> dict[str, Any]:
    retained: list[dict[str, Any]] = []
    for entry in agents:
        if len(retained) >= MAX_SNAPSHOTS:
            break
        candidate = {
            "schema_version": SCHEMA_VERSION,
            "agents": [*retained, entry],
        }
        if serialized_json_size(candidate) > MAX_FILE_BYTES:
            break
        retained.append(entry)
    return {"schema_version": SCHEMA_VERSION, "agents": retained}


def retire_active_agent(repo: Path | str, agent_id: str | None) -> bool:
    if not agent_id:
        return False
    registry = read_active_registry(repo)
    before = registry.get("agents", [])
    after = [entry for entry in before if entry.get("agent_id") != agent_id]
    if after == before:
        return False
    registry["agents"] = after
    write_active_registry(repo, registry)
    return True


def purge(repo: Path | str) -> dict[str, Any]:
    purged: list[str] = []
    directory = snapshots_dir(repo)
    if directory.exists() and not directory.is_symlink():
        for path in sorted(directory.glob("*.json")):
            if safe_unlink(repo, path):
                purged.append(str(path))
    registry = active_registry_path(repo)
    if registry.exists() and safe_unlink(repo, registry):
        purged.append(str(registry))
    return {"status": "PASS", "purged": purged, "purged_count": len(purged)}
