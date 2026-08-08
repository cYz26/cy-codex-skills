from __future__ import annotations

import hashlib
import json
from pathlib import Path
import uuid
from typing import Any

from .core import (
    CommandRunner,
    FleetError,
    SCHEMA_VERSION,
    _atomic_write,
    canonical_bytes,
    digest_value,
    read_trusted_bytes,
    runtime_inventory,
    tree_digest,
    trusted_path,
)
from .adapters import prepare_project_adapters, project_lock
from .sync import (
    _bytes_digest,
    _marketplace_identity,
    _plugin_source,
    _plugin_source_identity,
    _read_json,
    _resolve_marketplace_source,
    _validate_profile,
)


def apply_sync(plan: dict[str, Any], *, state_dir: Path) -> dict[str, Any]:
    state_dir = trusted_path(
        state_dir,
        label="fleet state directory",
        status="invalid_request",
    )
    receipt_dir = state_dir / "receipts"
    results: list[dict[str, Any]] = []
    non_reversible: list[dict[str, Any]] = []
    lock_change: dict[str, Any] | None = None
    before_identities = _empty_identity_snapshot()
    identities = _empty_identity_snapshot()
    project_results: list[dict[str, Any]] = []
    manual_actions: list[dict[str, Any]] = []
    receipt_path = receipt_dir / f"sync-{uuid.uuid4().hex}.json"
    status = "internal_failure"
    error_detail: str | None = None

    try:
        if not plan.get("ok"):
            raise FleetError("a blocked plan cannot be applied", status="blocked")
        _assert_bound_files(plan)
        manifest, _ = _read_json(Path(plan["paths"]["manifest"]), "manifest")
        lock, lock_before_bytes = _read_json(Path(plan["paths"]["lock"]), "lock")
        device, _ = _read_json(Path(plan["paths"]["device"]), "device overlay")
        codex_home = Path(plan["paths"]["codexHome"])
        profile = _validate_profile(manifest, lock, device, codex_home)
        expected_runtime = plan["bindings"]["runtime"]
        expected_sources = plan["bindings"]["sourceIdentities"]
        initial_runtime = _assert_stage_state(
            plan,
            profile,
            codex_home=codex_home,
            expected_runtime=expected_runtime,
            expected_sources=expected_sources,
        )
        before_identities = _layer_identity_snapshot(
            profile,
            runtime=initial_runtime,
            codex_home=codex_home,
            source_identities=expected_sources,
        )
        identities = before_identities
        runner = CommandRunner(codex_home=codex_home, timeout=600)

        for action in plan["actions"]:
            if action["kind"] != "marketplace-upgrade":
                continue
            stage_runtime = _assert_stage_state(
                plan,
                profile,
                codex_home=codex_home,
                expected_runtime=expected_runtime,
                expected_sources=expected_sources,
            )
            command = [
                "codex",
                "plugin",
                "marketplace",
                "upgrade",
                action["marketplace"],
                "--json",
            ]
            response = runner.json(command)
            result = _command_result(action, command, response)
            results.append(result)
            non_reversible.append(
                {
                    "kind": "marketplace-upgrade",
                    "marketplace": action["marketplace"],
                    "reason": "current Codex CLI exposes no receipt-bound snapshot rollback",
                }
            )
            observed_runtime = runtime_inventory(codex_home=codex_home)
            observed_sources = _current_source_identities(profile, observed_runtime)
            identities = _layer_identity_snapshot(
                profile,
                runtime=observed_runtime,
                codex_home=codex_home,
                source_identities=observed_sources,
            )
            _assert_runtime_effect_is_bounded(
                before=stage_runtime,
                after=observed_runtime,
                allowed_marketplaces={action["marketplace"]},
                allowed_plugins={
                    plugin["selector"]
                    for plugin in profile["plugins"]
                    if plugin["marketplace"] == action["marketplace"]
                },
                context=f"marketplace upgrade {action['marketplace']}",
            )
            _assert_marketplace_effect_is_bounded(
                profile,
                marketplace=action["marketplace"],
                before=expected_sources,
                after=observed_sources,
            )
            expected_runtime = digest_value(observed_runtime)
            expected_sources = observed_sources

        for action in plan["actions"]:
            if action["kind"] != "plugin-install":
                continue
            stage_runtime = _assert_stage_state(
                plan,
                profile,
                codex_home=codex_home,
                expected_runtime=expected_runtime,
                expected_sources=expected_sources,
            )
            command = ["codex", "plugin", "add", action["selector"], "--json"]
            response = runner.json(command)
            results.append(_command_result(action, command, response))
            non_reversible.append(
                {
                    "kind": "plugin-install",
                    "selector": action["selector"],
                    "reason": "current Codex CLI exposes no receipt-bound installed-cache downgrade",
                }
            )
            observed_runtime = runtime_inventory(codex_home=codex_home)
            observed_sources = _current_source_identities(profile, observed_runtime)
            identities = _layer_identity_snapshot(
                profile,
                runtime=observed_runtime,
                codex_home=codex_home,
                source_identities=observed_sources,
            )
            _assert_runtime_effect_is_bounded(
                before=stage_runtime,
                after=observed_runtime,
                allowed_marketplaces=set(),
                allowed_plugins={action["selector"]},
                context=f"plugin installation {action['selector']}",
            )
            if observed_sources != expected_sources:
                raise FleetError(
                    "marketplace or plugin source changed during plugin installation",
                    status="stale_plan",
                )
            expected_runtime = digest_value(observed_runtime)

        final_runtime = _assert_stage_state(
            plan,
            profile,
            codex_home=codex_home,
            expected_runtime=expected_runtime,
            expected_sources=expected_sources,
        )
        identities, next_lock = _verify_global_identities(
            profile=profile,
            current_lock=lock,
            runtime=final_runtime,
            codex_home=codex_home,
            advance_lock=bool(plan["advanceLock"]),
        )
        for plugin in profile["plugins"]:
            results.append(
                {
                    "id": f"cache-verify:{plugin['selector']}",
                    "kind": "cache-verify",
                    "status": "verified",
                    "selector": plugin["selector"],
                    "identity": identities["plugins"][plugin["selector"]],
                }
            )

        project_plan_actions = [
            action for action in plan["actions"] if action["kind"] == "project-plan"
        ]
        prepared_projects = prepare_project_adapters(
            project_plan_actions,
            identities=identities,
            codex_home=codex_home,
        )
        for item in prepared_projects:
            action = item["action"]
            adapter = item["adapter"]
            current_runtime = _assert_stage_state(
                plan,
                profile,
                codex_home=codex_home,
                expected_runtime=expected_runtime,
                expected_sources=expected_sources,
            )
            current_identities, _ = _verify_global_identities(
                profile=profile,
                current_lock=lock,
                runtime=current_runtime,
                codex_home=codex_home,
                advance_lock=bool(plan["advanceLock"]),
            )
            if current_identities != identities:
                raise FleetError(
                    "verified global identity changed before project apply",
                    status="stale_plan",
                )
            with project_lock(
                state_dir,
                profile=plan["profile"],
                project_id=action["projectId"],
            ):
                project_result = adapter.apply_and_verify(item["prepared"])
            project_result.update(
                {
                    "projectId": action["projectId"],
                    "projectPath": action["projectPath"],
                    "selector": action["selector"],
                    "adapter": action["adapter"],
                }
            )
            project_results.append(project_result)
            for manual in project_result["manualActions"]:
                manual_actions.append(
                    {
                        **manual,
                        "projectId": action["projectId"],
                        "selector": action["selector"],
                        "adapter": action["adapter"],
                    }
                )
            results.extend(
                [
                    {
                        "id": f"project-plan:{action['projectId']}:{action['selector']}",
                        "kind": "project-plan",
                        "status": "sealed",
                        "projectId": action["projectId"],
                        "selector": action["selector"],
                        "planSha256": project_result["planSha256"],
                    },
                    {
                        "id": f"project-apply:{action['projectId']}:{action['selector']}",
                        "kind": "project-apply",
                        "status": project_result["status"],
                        "projectId": action["projectId"],
                        "selector": action["selector"],
                    },
                    {
                        "id": f"project-verify:{action['projectId']}:{action['selector']}",
                        "kind": "project-verify",
                        "status": project_result["status"],
                        "projectId": action["projectId"],
                        "selector": action["selector"],
                    },
                ]
            )
            if project_result["status"] == "adapter_verification_failed":
                raise FleetError(
                    project_result.get("error") or "project Adapter verification failed",
                    status="adapter_verification_failed",
                )

        lock_after_bytes = canonical_bytes(next_lock)
        if plan["advanceLock"]:
            current_runtime = _assert_stage_state(
                plan,
                profile,
                codex_home=codex_home,
                expected_runtime=expected_runtime,
                expected_sources=expected_sources,
            )
            current_identities, current_next_lock = _verify_global_identities(
                profile=profile,
                current_lock=lock,
                runtime=current_runtime,
                codex_home=codex_home,
                advance_lock=True,
            )
            if current_identities != identities or current_next_lock != next_lock:
                raise FleetError(
                    "verified global identity changed before lock promotion",
                    status="stale_plan",
                )
            _atomic_write(Path(plan["paths"]["lock"]), lock_after_bytes, mode=0o644)
            results.append(
                {
                    "id": "lock-promote",
                    "kind": "lock-promote",
                    "status": "updated" if lock_after_bytes != lock_before_bytes else "unchanged",
                }
            )
        elif lock_after_bytes != lock_before_bytes:
            raise FleetError("locked apply resolved an identity outside the lock", status="identity_mismatch")
        lock_change = {
            "path": plan["paths"]["lock"],
            "changed": lock_after_bytes != lock_before_bytes,
            "beforeSha256": _bytes_digest(lock_before_bytes),
            "afterSha256": _bytes_digest(lock_after_bytes),
            "beforeContent": lock_before_bytes.decode("utf-8"),
            "afterContent": lock_after_bytes.decode("utf-8"),
        }
        changed_managed_files = sorted(
            {
                path
                for item in project_results
                for path in item.get("changedPaths", [])
            }
            | ({lock_change["path"]} if lock_change["changed"] else set())
        )
        status = "applied_with_manual_actions" if manual_actions else "applied_and_verified"
        ok = True
    except FleetError as error:
        status = error.status
        error_detail = str(error)
        ok = False
        if lock_change is None:
            try:
                current_lock_bytes = read_trusted_bytes(
                    Path(plan["paths"]["lock"]),
                    label="current lock after failed apply",
                    status="stale_plan",
                )
            except FleetError:
                current_lock_bytes = b""
            lock_change = {
                "path": plan["paths"]["lock"],
                "changed": False,
                "beforeSha256": plan["bindings"]["lock"],
                "afterSha256": _bytes_digest(current_lock_bytes),
                "beforeContent": None,
                "afterContent": None,
            }
        changed_managed_files = sorted(
            {
                path
                for item in project_results
                for path in item.get("changedPaths", [])
            }
        )

    restart_required = any(item["kind"] == "plugin-install" for item in results)
    restart = {
        "required": restart_required,
        "scope": "codex-session",
        "guidance": (
            "Start a new Codex session after reviewing this successful receipt."
            if ok and restart_required
            else (
                "Do not treat a restart as recovery; inspect this failed receipt and create a fresh plan."
                if restart_required
                else "No Codex session restart is required by this receipt."
            )
        ),
    }
    receipt: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "kind": "codex-fleet-receipt",
        "ok": ok,
        "status": status,
        "planSha256": plan["planSha256"],
        "plan": plan,
        "paths": plan["paths"],
        "advanceLock": bool(plan["advanceLock"]),
        "results": results,
        "beforeIdentities": before_identities,
        "afterIdentities": identities,
        "identities": identities,
        "projectResults": project_results,
        "changedManagedFiles": changed_managed_files,
        "lockChange": lock_change,
        "nonReversibleEffects": non_reversible,
        "manualActions": manual_actions,
        "restartRequired": restart_required,
        "restart": restart,
    }
    if error_detail is not None:
        receipt["error"] = error_detail
    receipt["receiptSha256"] = digest_value(receipt)
    _atomic_write(receipt_path, canonical_bytes(receipt), mode=0o600)

    report: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "kind": "codex-fleet-sync-result",
        "ok": ok,
        "status": status,
        "apply": True,
        "advanceLock": bool(plan["advanceLock"]),
        "planSha256": plan["planSha256"],
        "actions": plan["actions"],
        "receiptPath": str(receipt_path),
        "results": results,
        "beforeIdentities": before_identities,
        "afterIdentities": identities,
        "identities": identities,
        "nonReversibleEffects": non_reversible,
        "manualActions": manual_actions,
        "projectResults": project_results,
        "changedManagedFiles": changed_managed_files,
        "restartRequired": receipt["restartRequired"],
        "restart": restart,
        "lockSha256": lock_change["afterSha256"],
        "nextAction": (
            (
                "Review named manual project actions, then start a new Codex session."
                if manual_actions
                else "Start a new Codex session so the verified plugin cache is loaded."
            )
            if ok
            else "Inspect the receipt, correct the failure, and create a fresh sync plan."
        ),
    }
    if error_detail is not None:
        report["error"] = error_detail
    return report


def _assert_bound_files(plan: dict[str, Any]) -> None:
    for name in ("manifest", "lock", "device"):
        path = Path(plan["paths"][name])
        content = read_trusted_bytes(
            path,
            label=f"bound {name}",
            status="stale_plan",
        )
        if _bytes_digest(content) != plan["bindings"][name]:
            raise FleetError(f"bound {name} changed after planning", status="stale_plan")
    for project_id, expected in plan["bindings"]["projectMarkers"].items():
        marker = Path(plan["bindings"]["projectPaths"][project_id]) / ".codex-fleet" / "project.json"
        content = read_trusted_bytes(
            marker,
            label=f"bound project marker {project_id}",
            status="stale_plan",
        )
        if _bytes_digest(content) != expected:
            raise FleetError(f"bound project marker changed: {project_id}", status="stale_plan")


def _current_source_identities(
    profile: dict[str, Any], runtime: dict[str, Any]
) -> dict[str, Any]:
    runtime_marketplaces = {item["name"]: item for item in runtime["marketplaces"]}
    actual: dict[str, Any] = {}
    for marketplace in profile["marketplaces"]:
        observed = runtime_marketplaces.get(marketplace["name"])
        if observed is None:
            raise FleetError(f"marketplace disappeared: {marketplace['name']}", status="stale_plan")
        actual[f"marketplace:{marketplace['name']}"] = _marketplace_identity(observed, marketplace)
    for plugin in profile["plugins"]:
        observed = runtime_marketplaces[plugin["marketplace"]]
        source = _plugin_source(Path(observed["root"]), plugin["name"])
        actual[f"plugin:{plugin['selector']}"] = _plugin_source_identity(source)
    return actual


def _assert_stage_state(
    plan: dict[str, Any],
    profile: dict[str, Any],
    *,
    codex_home: Path,
    expected_runtime: str,
    expected_sources: dict[str, Any],
) -> dict[str, Any]:
    _assert_bound_files(plan)
    runtime = runtime_inventory(codex_home=codex_home)
    if digest_value(runtime) != expected_runtime:
        raise FleetError("runtime inventory changed before a mutating stage", status="stale_plan")
    try:
        current_sources = _current_source_identities(profile, runtime)
    except FleetError as error:
        raise FleetError(
            f"source identity became unavailable before a mutating stage: {error}",
            status="stale_plan",
        ) from error
    if current_sources != expected_sources:
        raise FleetError(
            "marketplace or plugin source identity changed before a mutating stage",
            status="stale_plan",
        )
    return runtime


def _assert_marketplace_effect_is_bounded(
    profile: dict[str, Any],
    *,
    marketplace: str,
    before: dict[str, Any],
    after: dict[str, Any],
) -> None:
    allowed = {f"marketplace:{marketplace}"}
    allowed.update(
        f"plugin:{plugin['selector']}"
        for plugin in profile["plugins"]
        if plugin["marketplace"] == marketplace
    )
    unexpected = sorted(
        key for key in set(before).union(after) if key not in allowed and before.get(key) != after.get(key)
    )
    if unexpected:
        raise FleetError(
            "marketplace upgrade changed unrelated source identities: " + ", ".join(unexpected),
            status="stale_plan",
        )


def _assert_runtime_effect_is_bounded(
    *,
    before: dict[str, Any],
    after: dict[str, Any],
    allowed_marketplaces: set[str],
    allowed_plugins: set[str],
    context: str,
) -> None:
    unexpected: list[str] = []
    for name in ("schemaVersion", "codexHome"):
        if before.get(name) != after.get(name):
            unexpected.append(name)

    before_marketplaces = {item["name"]: item for item in before["marketplaces"]}
    after_marketplaces = {item["name"]: item for item in after["marketplaces"]}
    for name in sorted(set(before_marketplaces).union(after_marketplaces)):
        if name not in allowed_marketplaces and before_marketplaces.get(name) != after_marketplaces.get(name):
            unexpected.append(f"marketplace:{name}")

    before_plugins = {item["selector"]: item for item in before["plugins"]}
    after_plugins = {item["selector"]: item for item in after["plugins"]}
    for selector in sorted(set(before_plugins).union(after_plugins)):
        if selector not in allowed_plugins and before_plugins.get(selector) != after_plugins.get(selector):
            unexpected.append(f"plugin:{selector}")

    if unexpected:
        raise FleetError(
            f"{context} changed unrelated runtime identities: {', '.join(unexpected)}",
            status="stale_plan",
        )


def _empty_identity_snapshot() -> dict[str, dict[str, Any]]:
    return {"marketplaces": {}, "plugins": {}, "caches": {}}


def _layer_identity_snapshot(
    profile: dict[str, Any],
    *,
    runtime: dict[str, Any],
    codex_home: Path,
    source_identities: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    snapshot = _empty_identity_snapshot()
    for marketplace in profile["marketplaces"]:
        key = f"marketplace:{marketplace['name']}"
        identity = source_identities.get(key)
        if not isinstance(identity, dict):
            raise FleetError(f"source identity is unavailable: {key}", status="stale_plan")
        snapshot["marketplaces"][marketplace["name"]] = dict(identity)

    runtime_plugins = {item["selector"]: item for item in runtime["plugins"]}
    for plugin in profile["plugins"]:
        selector = plugin["selector"]
        source_key = f"plugin:{selector}"
        source_identity = source_identities.get(source_key)
        if not isinstance(source_identity, dict):
            raise FleetError(f"source identity is unavailable: {source_key}", status="stale_plan")
        snapshot["plugins"][selector] = dict(source_identity)
        installed = runtime_plugins.get(selector)
        version = installed.get("version") if isinstance(installed, dict) else None
        if not isinstance(version, str) or not version:
            snapshot["caches"][selector] = {"available": False, "version": None}
            continue
        cache = (
            codex_home
            / "plugins"
            / "cache"
            / plugin["marketplace"]
            / plugin["name"]
            / version
        )
        try:
            snapshot["caches"][selector] = {
                "available": True,
                "version": version,
                "treeSha256": tree_digest(cache),
            }
        except FleetError as error:
            snapshot["caches"][selector] = {
                "available": False,
                "version": version,
                "status": error.status,
            }
    return snapshot


def _verify_global_identities(
    *,
    profile: dict[str, Any],
    current_lock: dict[str, Any],
    runtime: dict[str, Any],
    codex_home: Path,
    advance_lock: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    runtime_marketplaces = {item["name"]: item for item in runtime["marketplaces"]}
    runtime_plugins = {item["selector"]: item for item in runtime["plugins"]}
    marketplace_identities: dict[str, Any] = {}
    plugin_identities: dict[str, Any] = {}
    cache_identities: dict[str, Any] = {}
    for marketplace in profile["marketplaces"]:
        observed = runtime_marketplaces.get(marketplace["name"])
        if observed is None:
            raise FleetError(f"marketplace missing after apply: {marketplace['name']}", status="identity_mismatch")
        expected_source = _resolve_marketplace_source(marketplace, profile["deviceMarketplaces"])
        if observed["sourceType"] != marketplace["sourceType"] or observed["source"] != expected_source:
            raise FleetError(
                f"marketplace source changed during apply: {marketplace['name']}",
                status="identity_mismatch",
            )
        identity = _marketplace_identity(observed, marketplace)
        if not advance_lock and identity != current_lock["marketplaces"][marketplace["name"]]:
            raise FleetError(
                f"locked marketplace identity changed during apply: {marketplace['name']}",
                status="identity_mismatch",
            )
        marketplace_identities[marketplace["name"]] = identity

    for plugin in profile["plugins"]:
        selector = plugin["selector"]
        installed = runtime_plugins.get(selector)
        if installed is None:
            raise FleetError(f"plugin is not installed and enabled after apply: {selector}", status="identity_mismatch")
        source = _plugin_source(Path(runtime_marketplaces[plugin["marketplace"]]["root"]), plugin["name"])
        source_identity = _plugin_source_identity(source)
        if installed["version"] != source_identity["version"]:
            raise FleetError(f"installed plugin version differs from source: {selector}", status="identity_mismatch")
        cache = (
            codex_home
            / "plugins"
            / "cache"
            / plugin["marketplace"]
            / plugin["name"]
            / installed["version"]
        )
        cache_content_identity = {
            "version": installed["version"],
            "treeSha256": tree_digest(cache),
        }
        if cache_content_identity != source_identity:
            raise FleetError(f"installed cache differs from marketplace source: {selector}", status="identity_mismatch")
        if not advance_lock and source_identity != current_lock["plugins"][selector]:
            raise FleetError(f"locked plugin identity changed during apply: {selector}", status="identity_mismatch")
        plugin_identities[selector] = source_identity
        cache_identities[selector] = {"available": True, **cache_content_identity}

    next_lock = {
        "schemaVersion": SCHEMA_VERSION,
        "manifestSha256": current_lock["manifestSha256"],
        "marketplaces": marketplace_identities,
        "plugins": plugin_identities,
    }
    return {
        "marketplaces": marketplace_identities,
        "plugins": plugin_identities,
        "caches": cache_identities,
    }, next_lock


def _command_result(
    action: dict[str, Any], command: list[str], response: dict[str, Any]
) -> dict[str, Any]:
    return {
        "id": action["id"],
        "kind": action["kind"],
        "status": "succeeded",
        "command": command[1:],
        "response": _bounded_response(response),
    }


def _bounded_response(response: dict[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(response, sort_keys=True, ensure_ascii=False).encode("utf-8")
    if len(encoded) <= 4096:
        return response
    return {
        "truncated": True,
        "byteLength": len(encoded),
        "sha256": "sha256:" + hashlib.sha256(encoded).hexdigest(),
    }
