#!/usr/bin/env python3
"""Preflight and context audit for the Lark Feishu Ops plugin."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import lark_feishu_ops_policy as policy
import lark_feishu_ops_runtime as runtime


HOME = Path.home()
SKILL_LOCK = HOME / ".agents" / ".skill-lock.json"
GLOBAL_SKILLS_DIR = HOME / ".agents" / "skills"
PREFERRED_PROJECT_SKILL = "lark-feishu-ops"
UPDATE_CHECK_POLICIES = {"daily", "always", "never"}


def run_command(command: list[str], timeout: int = 30) -> dict[str, Any]:
    """Patchable command seam retained for doctor callers and tests."""

    return runtime.run_command(command, timeout=timeout)


def parse_json_output(result: dict[str, Any]) -> Any | None:
    return runtime.parse_json_output(result)


def compact_result(result: dict[str, Any], *, max_output: int = 1200) -> dict[str, Any]:
    return runtime.compact_result(result, max_output=max_output)


def _json_runner(command: list[str], timeout: int) -> dict[str, Any]:
    return run_command(command, timeout=timeout)


def _contract_summary(contract: dict[str, Any]) -> dict[str, Any]:
    """Keep JSON diagnostics while excluding command payload bodies."""

    return {
        "ok": bool(contract.get("ok")),
        "command": contract.get("command"),
        "exit_code": contract.get("exit_code"),
        "errors": list(contract.get("errors") or []),
        "stderr_present": bool(contract.get("stderr")),
    }


def local_date(now: datetime | None = None) -> str:
    current = now or datetime.now().astimezone()
    return current.date().isoformat()


def default_update_cache_path() -> Path:
    cache_home = os.environ.get("XDG_CACHE_HOME")
    root = Path(cache_home).expanduser() if cache_home else HOME / ".cache"
    return root / "lark-feishu-ops" / "update-check.json"


def read_update_check_cache(cache_path: Path | str | None = None) -> dict[str, Any] | None:
    path = Path(cache_path).expanduser() if cache_path is not None else default_update_cache_path()
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def write_update_check_cache(
    payload: dict[str, Any], cache_path: Path | str | None = None
) -> dict[str, Any]:
    path = Path(cache_path).expanduser() if cache_path is not None else default_update_cache_path()
    record = {
        "checked_local_date": local_date(),
        "checked_at": datetime.now().astimezone().isoformat(),
        "action": payload.get("action"),
        "current_version": payload.get("current_version"),
        "latest_version": payload.get("latest_version"),
        "ok": payload.get("ok", True),
        "payload": payload,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        record["cache_path"] = str(path)
        record["write_ok"] = True
    except OSError as exc:
        record["cache_path"] = str(path)
        record["write_ok"] = False
        record["write_error"] = str(exc)
    return record


def current_update_cache(cache_path: Path | str | None = None) -> dict[str, Any] | None:
    record = read_update_check_cache(cache_path)
    if not record or record.get("checked_local_date") != local_date():
        return None
    payload = record.get("payload")
    if not isinstance(payload, dict):
        payload = {
            "action": record.get("action"),
            "ok": record.get("ok"),
            "current_version": record.get("current_version"),
            "latest_version": record.get("latest_version"),
        }
        record["payload"] = payload
    return record


def update_cache_matches_detected_cli(
    record: dict[str, Any],
    check: dict[str, Any],
) -> bool:
    payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
    cached_version = runtime.parse_version(
        payload.get("current_version") or record.get("current_version")
    )
    detected_version = runtime.parse_version(check.get("version"))
    return bool(
        cached_version
        and detected_version
        and cached_version == detected_version
    )


def update_payload_requires_confirmation(payload: Any) -> bool:
    return isinstance(payload, dict) and payload.get("action") not in (
        None,
        "already_up_to_date",
    )


def update_payload_needs_skills_sync(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    skills_status = payload.get("skills_status")
    return isinstance(skills_status, dict) and skills_status.get("in_sync") is False


def build_update_action(
    payload: dict[str, Any], executable: str = "lark-cli"
) -> dict[str, Any]:
    return {
        "type": "lark_cli_update",
        "requires_confirmation": True,
        "command": [executable, "update", "--json"],
        "current_version": payload.get("current_version"),
        "latest_version": payload.get("latest_version"),
        "followup_command": [
            "python3",
            "plugins/lark-feishu-ops/scripts/lark_feishu_ops_sync.py",
            "--after-cli-update",
            "--json",
        ],
    }


def build_skills_sync_action(
    payload: dict[str, Any], executable: str = "lark-cli"
) -> dict[str, Any]:
    skills_status = payload.get("skills_status")
    if not isinstance(skills_status, dict):
        skills_status = {}
    skipped_deleted = skills_status.get("skipped_deleted")
    if not isinstance(skipped_deleted, list):
        skipped_deleted = []
    return {
        "type": "lark_cli_skills_sync",
        "requires_confirmation": True,
        "command": [executable, "update", "--json"],
        "current_version": skills_status.get("current"),
        "target_version": skills_status.get("target"),
        "official_count": skills_status.get("official"),
        "updated_count": skills_status.get("updated"),
        "skipped_deleted": skipped_deleted,
        "followup_command": [
            "python3",
            "plugins/lark-feishu-ops/scripts/lark_feishu_ops_sync.py",
            "--after-cli-update",
            "--json",
        ],
    }


def load_skill_lock_sources() -> dict[str, Any]:
    if not SKILL_LOCK.is_file():
        return {}
    try:
        payload = json.loads(SKILL_LOCK.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    skills = payload.get("skills")
    if not isinstance(skills, dict):
        return {}
    return {
        name: dict(item)
        for name, item in skills.items()
        if isinstance(name, str) and isinstance(item, dict)
    }


def _source_metadata(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        return {"source": value, "sourceType": None, "sourceUrl": None}
    if isinstance(value, dict):
        return {
            "source": value.get("source"),
            "sourceType": value.get("sourceType"),
            "sourceUrl": value.get("sourceUrl"),
        }
    return {"source": None, "sourceType": None, "sourceUrl": None}


def _well_known_source_matches(name: str, metadata: dict[str, Any]) -> bool:
    if metadata.get("source") != "open.feishu.cn" or metadata.get("sourceType") != "well-known":
        return False
    source_url = metadata.get("sourceUrl")
    if not isinstance(source_url, str):
        return False
    parsed = urlparse(source_url)
    expected_prefix = f"/.well-known/skills/{name}/"
    return (
        parsed.scheme == "https"
        and parsed.hostname == "open.feishu.cn"
        and parsed.path.startswith(expected_prefix)
    )


def is_official_lark_skill(item: dict[str, Any], sources: dict[str, Any]) -> bool:
    name = item.get("name")
    if not isinstance(name, str) or not name.startswith("lark-"):
        return False
    metadata = _source_metadata(sources.get(name))
    return metadata.get("source") == "larksuite/cli" or _well_known_source_matches(
        name, metadata
    )


def normalize_agents(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item).strip().lower() for item in value if str(item).strip()}


def read_skill_frontmatter_name(skill_file: Path) -> str | None:
    try:
        lines = skill_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            return None
        if stripped.startswith("name:"):
            value = stripped.split(":", 1)[1].strip()
            return value.strip("\"'") or None
    return None


def project_skill_record(skill_file: Path) -> dict[str, Any]:
    skill_dir = skill_file.parent
    name = read_skill_frontmatter_name(skill_file) or skill_dir.name
    return {
        "name": name,
        "directory": skill_dir.name,
        "path": str(skill_file),
        "source": "project",
    }


def _repo_search_roots(start: Path) -> tuple[Path, list[Path]]:
    requested = start.expanduser().resolve()
    if requested.is_file():
        requested = requested.parent
    roots: list[Path] = []
    current = requested
    while True:
        roots.append(current)
        if (current / ".git").exists():
            return current, roots
        if current.parent == current:
            break
        current = current.parent
    return requested, [requested]


def _unsafe_skill_record(path: Path, reason: str, source: str) -> dict[str, Any]:
    return {
        "name": path.name,
        "directory": path.name,
        "path": str(path),
        "source": source,
        "unsafe_reason": reason,
    }


def _scan_project_skill_root(
    skills_root: Path, source: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    safe: list[dict[str, Any]] = []
    unsafe: list[dict[str, Any]] = []
    if not skills_root.exists() and not skills_root.is_symlink():
        return safe, unsafe
    if skills_root.is_symlink():
        unsafe.append(_unsafe_skill_record(skills_root, "symlink_root", source))
        return safe, unsafe
    if not skills_root.is_dir():
        unsafe.append(_unsafe_skill_record(skills_root, "non_directory_root", source))
        return safe, unsafe

    try:
        root_resolved = skills_root.resolve(strict=True)
        children = sorted(skills_root.iterdir(), key=lambda item: item.name)
    except OSError:
        unsafe.append(_unsafe_skill_record(skills_root, "unreadable_root", source))
        return safe, unsafe

    for child in children:
        directory_lark = child.name.startswith("lark-")
        if child.is_symlink():
            if directory_lark:
                unsafe.append(_unsafe_skill_record(child, "symlink", source))
            continue
        if not child.is_dir():
            if directory_lark:
                unsafe.append(_unsafe_skill_record(child, "non_directory", source))
            continue
        skill_file = child / "SKILL.md"
        if skill_file.is_symlink():
            unsafe.append(_unsafe_skill_record(child, "symlink_skill_file", source))
            continue
        if not skill_file.is_file():
            if directory_lark:
                unsafe.append(_unsafe_skill_record(child, "missing_regular_skill_file", source))
            continue
        try:
            resolved_file = skill_file.resolve(strict=True)
            resolved_file.relative_to(root_resolved)
        except (OSError, ValueError):
            unsafe.append(_unsafe_skill_record(child, "path_escape", source))
            continue
        record = project_skill_record(skill_file)
        if not (
            str(record["name"]).startswith("lark-")
            or str(record["directory"]).startswith("lark-")
        ):
            continue
        record["root"] = str(skills_root)
        record["source"] = source
        safe.append(record)
    return safe, unsafe


def audit_project_lark_skills(repo: Path | str) -> dict[str, Any]:
    repo_root, search_roots = _repo_search_roots(Path(repo))
    current: list[dict[str, Any]] = []
    legacy: list[dict[str, Any]] = []
    unsafe: list[dict[str, Any]] = []
    current_roots: list[str] = []
    legacy_roots: list[str] = []

    for root in search_roots:
        current_root = root / ".agents" / "skills"
        legacy_root = root / ".codex" / "skills"
        current_roots.append(str(current_root))
        legacy_roots.append(str(legacy_root))
        safe_current, unsafe_current = _scan_project_skill_root(current_root, "project-current")
        safe_legacy, unsafe_legacy = _scan_project_skill_root(legacy_root, "project-legacy")
        current.extend(safe_current)
        legacy.extend(safe_legacy)
        unsafe.extend(unsafe_current)
        unsafe.extend(unsafe_legacy)

    seen: dict[str, str] = {}
    trusted_current: list[dict[str, Any]] = []
    trusted_legacy: list[dict[str, Any]] = []
    for record in [*current, *legacy]:
        name = str(record["name"])
        if name in seen:
            duplicate = dict(record)
            duplicate["unsafe_reason"] = "duplicate"
            duplicate["duplicate_of"] = seen[name]
            unsafe.append(duplicate)
            continue
        seen[name] = str(record["path"])
        if record.get("source") == "project-current":
            trusted_current.append(record)
        else:
            trusted_legacy.append(record)

    preferred = [
        item
        for item in trusted_current
        if item["name"] == PREFERRED_PROJECT_SKILL
        or item["directory"] == PREFERRED_PROJECT_SKILL
    ]
    scattered = [item for item in trusted_current if item not in preferred]
    actions = [
        {
            "id": f"remove-project-lark-skill-{item['directory']}",
            "type": "remove_project_lark_skill",
            "title": f"Remove project-local scattered Lark skill {item['name']}",
            "skill": item["name"],
            "path": str(Path(str(item["path"])).parent),
            "reason": (
                "Project-local scattered lark-* skills increase main-agent context; "
                "route Feishu/Lark operations through lark-feishu-ops instead."
            ),
            "safety": "advisory",
            "requiresAuthorization": True,
        }
        for item in scattered
    ]

    recommendations: list[str] = []
    if scattered:
        recommendations.append(
            "Remove or disable project-local scattered lark-* skills from the main-agent "
            "context and route Feishu/Lark work through lark-feishu-ops."
        )
        if not preferred:
            recommendations.append(
                "Add or enable lark-feishu-ops as the single project-local Feishu/Lark entry point."
            )
    elif preferred:
        recommendations.append(
            "Project-local lark-feishu-ops route is present; no scattered project Lark skill cleanup is needed."
        )
    else:
        recommendations.append(
            "No project-local current Lark skills found; keep Feishu/Lark operations routed "
            "through lark-feishu-ops when needed."
        )
    if trusted_legacy:
        recommendations.append(
            "Legacy .codex/skills Lark entries are reported separately; migrate only after explicit approval."
        )
    if unsafe:
        recommendations.append(
            "Unsafe, duplicate, or escaping project skill entries were not trusted; inspect them manually."
        )

    suggested_configuration = {
        "preferred_entrypoint": PREFERRED_PROJECT_SKILL,
        "main_agent_policy": "Keep scattered official lark-* skills out of the project-local main-agent context.",
        "dispatch_policy": (
            "Use direct main-agent lark-cli for bounded low-risk reads; escalate side effects, "
            "cross-domain work, auth/profile complexity, raw OpenAPI, broad pagination, and "
            "explicit FeishuOps requests to FeishuOps."
        ),
        "subagent_policy": (
            "FeishuOps lazy-loads official lark-* guidance only when the dispatch policy chooses "
            "subagent execution."
        ),
        "project_skill_state": (
            "scattered_present"
            if scattered
            else "preferred_present"
            if preferred
            else "legacy_or_unsafe_present"
            if trusted_legacy or unsafe
            else "no_project_lark_skills"
        ),
    }

    return {
        "status": "WARN" if scattered or trusted_legacy or unsafe else "PASS",
        "repo": str(repo_root),
        "requested_path": str(Path(repo).expanduser().resolve()),
        "skills_dir": str(repo_root / ".agents" / "skills"),
        "current_skills_roots": current_roots,
        "legacy_skills_roots": legacy_roots,
        "project_lark_feishu_ops": preferred,
        "project_scattered_lark_skills": scattered,
        "legacy_project_lark_skills": trusted_legacy,
        "unsafe_project_lark_skills": unsafe,
        "suggested_configuration": suggested_configuration,
        "recommendations": recommendations,
        "actions": actions,
    }


def _inventory_lark_cli() -> list[dict[str, Any]]:
    preferred = shutil.which("lark-cli")
    if preferred and not Path(preferred).expanduser().is_file():
        # Preserve the historical injectable lookup seam used by API callers.
        return runtime.inventory_executables(preferred=preferred, path_value="")
    return runtime.inventory_executables(preferred=preferred)


def check_lark_cli(
    skip_update_check: bool,
    offline: bool,
    update_check_policy: str = "daily",
    force_update_check: bool = False,
    cache_path: Path | str | None = None,
) -> dict[str, Any]:
    if update_check_policy not in UPDATE_CHECK_POLICIES:
        raise ValueError(f"unsupported update_check_policy: {update_check_policy}")

    inventory = _inventory_lark_cli()
    canonical = inventory[0] if inventory else None
    canonical_invocation = (
        runtime.invocation_for(canonical) if canonical is not None else None
    )
    check: dict[str, Any] = {
        "status": "PASS" if canonical else "FAIL",
        "path": canonical.get("path") if canonical else None,
        "canonical_executable": canonical.get("path") if canonical else None,
        "canonical_invocation": canonical_invocation,
        "executables": inventory,
        "version": None,
        "version_check": None,
        "doctor": None,
        "auth_status": None,
        "embedded_skills": None,
        "domain_readiness": None,
        "update_check": None,
        "update_action": None,
        "skills_sync_action": None,
        "recommendations": [],
    }

    if canonical is None:
        check["recommendations"].append(
            "Install lark-cli first. See https://github.com/larksuite/cli for official installation options."
        )
        return check

    run_lark_cli_version_check(check)
    run_lark_cli_doctor_check(check, offline=offline)
    run_lark_cli_auth_status_check(check)
    if canonical.get("exists"):
        run_lark_cli_embedded_skills_check(check)
    run_lark_cli_update_check(
        check,
        skip_update_check=skip_update_check,
        offline=offline,
        update_check_policy=update_check_policy,
        force_update_check=force_update_check,
        cache_path=cache_path,
    )
    return check


def warn_lark_cli_check(check: dict[str, Any], recommendation: str) -> None:
    check["status"] = "WARN" if check["status"] == "PASS" else check["status"]
    if recommendation not in check["recommendations"]:
        check["recommendations"].append(recommendation)


def run_lark_cli_version_check(check: dict[str, Any]) -> None:
    versions: set[str] = set()
    records = check.get("executables") or []
    for index, record in enumerate(records):
        invocation = runtime.invocation_for(record)
        result = run_command([invocation, "--version"], timeout=15)
        parsed = runtime.parse_version(result.get("stdout")) if result.get("ok") else None
        record["version"] = parsed
        record["version_check"] = compact_result(result, max_output=240)
        if parsed:
            versions.add(parsed)
        elif index == 0:
            check["status"] = "FAIL"
        else:
            warn_lark_cli_check(
                check,
                f"Could not verify reachable secondary lark-cli at {record.get('path')}.",
            )
    if records:
        check["version"] = records[0].get("version")
        check["version_check"] = records[0].get("version_check")
    if len(versions) > 1:
        warn_lark_cli_check(
            check,
            "Reachable lark-cli executables have divergent versions; align them with the canonical executable.",
        )


def run_lark_cli_doctor_check(check: dict[str, Any], *, offline: bool) -> None:
    invocation = str(check.get("canonical_invocation") or "lark-cli")
    command = [invocation, "doctor"]
    if offline:
        command.append("--offline")
    result = run_command(command, timeout=30)
    check["doctor"] = {
        "command": result.get("command"),
        "ok": result.get("ok"),
        "exit_code": result.get("exit_code"),
        "stderr_present": bool(result.get("stderr")),
        "output_redacted": True,
    }
    if not result.get("ok"):
        warn_lark_cli_check(
            check,
            f"Run `{invocation} doctor` and repair local config/auth issues before platform writes.",
        )


def run_lark_cli_auth_status_check(check: dict[str, Any]) -> None:
    invocation = str(check.get("canonical_invocation") or "lark-cli")
    result = run_command([invocation, "auth", "status"], timeout=20)
    check["auth_status"] = {
        "command": result.get("command"),
        "ok": result.get("ok"),
        "exit_code": result.get("exit_code"),
        "stderr_present": bool(result.get("stderr")),
        "output_redacted": True,
    }
    if not result.get("ok"):
        warn_lark_cli_check(
            check,
            f"Run `{invocation} auth status` and complete login/scope setup before protected operations.",
        )


def _skill_names(payload: Any) -> list[str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("skills"), list):
        return []
    names = {
        item.get("name")
        for item in payload["skills"]
        if isinstance(item, dict)
        and isinstance(item.get("name"), str)
        and item["name"].startswith("lark-")
    }
    return sorted(names)


def run_lark_cli_embedded_skills_check(check: dict[str, Any]) -> None:
    invocation = str(check.get("canonical_invocation") or "lark-cli")
    list_contract = runtime.run_json_command(
        [invocation, "skills", "list", "--json"],
        required_fields=("skills", "count"),
        require_ok_envelope=True,
        timeout=30,
        runner=_json_runner,
    )
    list_errors = list(list_contract.get("errors") or [])
    payload = list_contract.get("payload")
    if isinstance(payload, dict):
        if not isinstance(payload.get("skills"), list):
            list_errors.append("schema:skills_list_required")
        if not isinstance(payload.get("count"), int):
            list_errors.append("schema:count_integer_required")
    names = _skill_names(payload) if not list_errors else []

    read_contract = runtime.run_json_command(
        [invocation, "skills", "read", "lark-doc", "--json"],
        required_fields=("skill", "path", "content", "guidance"),
        require_ok_envelope=False,
        timeout=30,
        runner=_json_runner,
    )
    read_errors = list(read_contract.get("errors") or [])
    read_payload = read_contract.get("payload")
    if isinstance(read_payload, dict):
        if read_payload.get("skill") != "lark-doc":
            read_errors.append("schema:skill_must_equal_lark-doc")
        for field in ("path", "content", "guidance"):
            if not isinstance(read_payload.get(field), str):
                read_errors.append(f"schema:{field}_string_required")

    coverage = policy.guidance_coverage(set(names))
    unmapped = coverage["unmapped_embedded_skills"]
    missing = coverage["missing_embedded_skills"]
    status = "PASS" if not list_errors and not read_errors and not unmapped and not missing else "WARN"
    check["embedded_skills"] = {
        "status": status,
        "count": len(names),
        "skills": names,
        "list_check": {
            **_contract_summary(list_contract),
            "errors": list_errors,
        },
        "representative_read": {
            **_contract_summary(read_contract),
            "errors": read_errors,
            "skill": read_payload.get("skill") if isinstance(read_payload, dict) else None,
            "path": read_payload.get("path") if isinstance(read_payload, dict) else None,
            "content_redacted": True,
            "guidance_present": bool(
                isinstance(read_payload, dict) and read_payload.get("guidance")
            ),
        },
    }
    check["domain_readiness"] = coverage
    if status != "PASS":
        reasons: list[str] = []
        if list_errors or read_errors:
            reasons.append("required JSON command schema validation failed")
        if missing:
            reasons.append("mapped embedded skills are missing")
        if unmapped:
            reasons.append("unmapped embedded skills were discovered")
        warn_lark_cli_check(
            check,
            "Embedded skill readiness needs attention: " + "; ".join(reasons) + ".",
        )


def _validate_cached_update_payload(payload: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["json_object_required"]
    if payload.get("ok") is not True:
        errors.append("ok_true_required")
    if not isinstance(payload.get("action"), str):
        errors.append("missing_required_field:action")
    return errors


def run_lark_cli_update_check(
    check: dict[str, Any],
    *,
    skip_update_check: bool,
    offline: bool,
    update_check_policy: str,
    force_update_check: bool,
    cache_path: Path | str | None,
) -> None:
    if skip_update_check or offline or update_check_policy == "never":
        record_skipped_update_check(check, update_check_policy)
        return

    cached = None if force_update_check or update_check_policy == "always" else current_update_cache(cache_path)
    if cached is not None and not update_cache_matches_detected_cli(cached, check):
        cached = None
    if cached is not None:
        update_payload = cached["payload"]
        check["update_check"] = cached_update_check_report(
            cached, update_check_policy, cache_path
        )
        if not check["update_check"]["ok"]:
            warn_lark_cli_check(
                check,
                "Cached update check failed semantic validation; run a fresh JSON update check.",
            )
            return
    else:
        update_payload = run_fresh_update_check(check, update_check_policy, cache_path)
        if update_payload is None:
            return

    invocation = str(check.get("canonical_invocation") or "lark-cli")
    if update_payload_requires_confirmation(update_payload):
        warn_lark_cli_check(
            check,
            f"Run `{invocation} update` only after explicit confirmation; it is a high-risk-write command.",
        )
        check["update_action"] = build_update_action(update_payload, invocation)
    elif update_payload_needs_skills_sync(update_payload):
        warn_lark_cli_check(
            check,
            (
                "official Lark skill guidance is out of sync with the lark-cli binary. "
                f"Run `{invocation} update --json` only after explicit confirmation if you "
                "want FeishuOps lazy skill guidance refreshed; direct lark-cli operations "
                "can still use CLI help and schema fallback."
            ),
        )
        check["skills_sync_action"] = build_skills_sync_action(update_payload, invocation)


def record_skipped_update_check(check: dict[str, Any], update_check_policy: str) -> None:
    check["update_check"] = {
        "skipped": True,
        "reason": "offline, skip_update_check, or never policy requested",
        "policy": update_check_policy,
    }
    invocation = str(check.get("canonical_invocation") or "lark-cli")
    check["recommendations"].append(
        f"Keep lark-cli updated; run `{invocation} update --check --json` periodically."
    )


def cached_update_check_report(
    cached: dict[str, Any],
    update_check_policy: str,
    cache_path: Path | str | None,
) -> dict[str, Any]:
    payload = cached["payload"]
    errors = _validate_cached_update_payload(payload)
    return {
        "cached": True,
        "policy": update_check_policy,
        "cache_path": str(
            Path(cache_path).expanduser() if cache_path else default_update_cache_path()
        ),
        "ok": not errors,
        "exit_code": 0,
        "payload": payload,
        "errors": errors,
        "stderr": "",
    }


def run_fresh_update_check(
    check: dict[str, Any],
    update_check_policy: str,
    cache_path: Path | str | None,
) -> Any | None:
    invocation = str(check.get("canonical_invocation") or "lark-cli")
    result = run_command([invocation, "update", "--check", "--json"], timeout=45)
    contract = runtime.validate_json_result(
        result,
        required_fields=("action",),
        require_ok_envelope=True,
    )
    payload = contract.get("payload")
    check["update_check"] = {
        "command": result.get("command"),
        "cached": False,
        "policy": update_check_policy,
        "ok": bool(contract.get("ok")),
        "exit_code": result.get("exit_code"),
        "payload": payload,
        "errors": list(contract.get("errors") or []),
        "stderr": str(result.get("stderr") or "")[:1200],
    }
    if contract.get("ok") and isinstance(payload, dict):
        check["update_check"]["cache"] = write_update_check_cache(payload, cache_path)
        return payload

    warn_lark_cli_check(
        check,
        f"Could not complete a valid JSON update check; retry `{invocation} update --check --json` later.",
    )
    return None


def list_global_skills() -> dict[str, Any]:
    npx_path = shutil.which("npx")
    if npx_path is None:
        return {
            "status": "WARN",
            "npx_path": None,
            "raw": None,
            "skills": [],
            "error": "`npx` not found; optional installer/global audit unavailable.",
        }
    result = run_command(["npx", "skills", "ls", "-g", "--json"], timeout=60)
    payload = parse_json_output(result)
    if not result.get("ok") or not isinstance(payload, list):
        return {
            "status": "WARN",
            "npx_path": npx_path,
            "raw": compact_result(result),
            "skills": [],
            "error": "Could not parse `npx skills ls -g --json`.",
        }
    return {
        "status": "PASS",
        "npx_path": npx_path,
        "raw": compact_result(result, max_output=200),
        "skills": payload,
        "error": None,
    }


def audit_global_lark_skills() -> dict[str, Any]:
    listing = list_global_skills()
    sources = load_skill_lock_sources()
    exposed: list[dict[str, Any]] = []
    official: list[dict[str, Any]] = []
    unverified: list[dict[str, Any]] = []
    codex_effective: list[dict[str, Any]] = []

    for item in listing.get("skills", []):
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name.startswith("lark-"):
            continue
        metadata = _source_metadata(sources.get(name))
        record = {
            "name": name,
            "path": item.get("path"),
            "agents": item.get("agents", []),
            **metadata,
        }
        exposed.append(record)
        if is_official_lark_skill(item, sources):
            official.append(record)
            if "codex" in normalize_agents(item.get("agents")):
                codex_effective.append(record)
        else:
            unverified.append(record)

    unavailable_optional = listing.get("status") != "PASS" and not listing.get("npx_path")
    if unavailable_optional:
        status = "PASS"
    elif listing.get("status") != "PASS" or codex_effective or unverified:
        status = "WARN"
    else:
        status = "PASS"

    if codex_effective:
        recommendation = (
            "Unload verified official lark-* skills from Codex and route Feishu/Lark work "
            "through the plugin subagent."
        )
    elif unverified:
        recommendation = (
            "Unverified global lark-* exposure is present; inspect provenance before trusting or removing it."
        )
    elif unavailable_optional:
        recommendation = (
            "npx is optional for runtime readiness; global skills exposure could not be inspected."
        )
    else:
        recommendation = "No verified official lark-* skills are globally active for Codex."

    return {
        "status": status,
        "exposed_global_lark_skills": exposed,
        "official_global_lark_skills": official,
        "codex_effective_official_lark_skills": codex_effective,
        "unverified_global_lark_skills": unverified,
        "recommendation": recommendation,
        "listing": {
            "status": listing.get("status"),
            "availability": "optional_unavailable" if unavailable_optional else "available",
            "npx_path": listing.get("npx_path"),
            "error": listing.get("error"),
        },
    }


def apply_codex_global_unload(targets: list[dict[str, Any]]) -> dict[str, Any]:
    if shutil.which("npx") is None:
        return {
            "status": "FAIL",
            "operations": [],
            "error": "`npx` not found; cannot unload skills.",
        }
    operations: list[dict[str, Any]] = []
    for target in targets:
        name = target.get("name")
        if not isinstance(name, str) or not name:
            continue
        command = ["npx", "skills", "remove", "-g", "-a", "codex", "-s", name, "-y"]
        result = run_command(command, timeout=90)
        operations.append(compact_result(result, max_output=1600))
    after = audit_global_lark_skills()
    still_effective = after.get("codex_effective_official_lark_skills") or []
    status = "PASS" if not still_effective and all(op.get("ok") for op in operations) else "FAIL"
    return {"status": status, "operations": operations, "verification": after}


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    lark_cli = check_lark_cli(
        args.skip_update_check,
        args.offline,
        update_check_policy=args.update_check_policy,
        force_update_check=args.force_update_check,
        cache_path=args.update_cache_path,
    )
    global_audit = audit_global_lark_skills()
    project_audit = audit_project_lark_skills(args.repo) if getattr(args, "repo", None) else None

    remediation = None
    if args.apply_codex_global_unload:
        remediation = apply_codex_global_unload(
            global_audit["codex_effective_official_lark_skills"]
        )
        global_audit = audit_global_lark_skills()

    statuses = [lark_cli["status"], global_audit["status"]]
    if project_audit is not None:
        statuses.append(project_audit["status"])
    if remediation is not None:
        statuses.append(remediation["status"])

    if "FAIL" in statuses:
        overall = "FAIL"
    elif args.strict and any(status != "PASS" for status in statuses):
        overall = "FAIL"
    elif any(status != "PASS" for status in statuses):
        overall = "WARN"
    else:
        overall = "PASS"

    recommendations: list[str] = []
    recommendations.extend(lark_cli.get("recommendations", []))
    if global_audit["codex_effective_official_lark_skills"]:
        recommendations.append(
            "Run this doctor with `--apply-codex-global-unload`, then start a new Codex thread."
        )
    elif args.apply_codex_global_unload:
        recommendations.append("Global official lark-* skills are no longer active for Codex.")
    recommendations.append(global_audit["recommendation"])
    if project_audit is not None:
        recommendations.extend(project_audit.get("recommendations", []))

    checks = {"lark_cli": lark_cli, "global_lark_skills": global_audit}
    if project_audit is not None:
        checks["project_lark_skills"] = project_audit
    return {
        "status": overall,
        "checks": checks,
        "remediation": remediation,
        "recommendations": recommendations,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Lark Feishu Ops dependencies and context load.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    parser.add_argument("--strict", action="store_true", help="Fail if any warning remains.")
    parser.add_argument("--repo", help="Repository path to inspect for project-local Lark skills.")
    parser.add_argument("--offline", action="store_true", help="Skip network-sensitive checks.")
    parser.add_argument("--skip-update-check", action="store_true", help="Skip lark-cli update check.")
    parser.add_argument(
        "--update-check-policy",
        choices=sorted(UPDATE_CHECK_POLICIES),
        default="daily",
        help="How often to run `lark-cli update --check --json`.",
    )
    parser.add_argument("--force-update-check", action="store_true", help="Bypass the daily update-check cache.")
    parser.add_argument("--update-cache-path", help=argparse.SUPPRESS)
    parser.add_argument(
        "--apply-codex-global-unload",
        action="store_true",
        help="Remove verified official global lark-* skills from Codex only, then verify.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"status: {report['status']}")
        for recommendation in report.get("recommendations", []):
            print(f"- {recommendation}")
    return 0 if report["status"] == "PASS" or (report["status"] == "WARN" and not args.strict) else 1


if __name__ == "__main__":
    raise SystemExit(main())
