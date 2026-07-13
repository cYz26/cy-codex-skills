from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from workflow_planning_paths import (
    LEGACY_STATE_SUNSET_RELEASE,
    guard_devflow_write,
    legacy_state_path,
    provider_migration_root,
    state_path,
)
from workflow_provider_activation import (
    atomic_write,
    normalized_persisted_selectors,
    provider_lock_payload,
)
from workflow_state import resolve_state
from workflow_provider_profiles import diagnose_provider_selection
from workflow_roadmap_provider import planning_tracking_report
from workflow_provider_registry import default_plugin_root, side_effect_decision


SCHEMA_VERSION = 1
MIGRATION_KIND = "devflow-provider-state-migration"


class ConcurrentTargetDrift(RuntimeError):
    def __init__(self, path: str, expected: dict[str, Any], actual: dict[str, Any]):
        super().__init__(f"concurrent target drift: {path}")
        self.path = path
        self.expected = expected
        self.actual = actual


def plan_provider_migration(
    repo: Path,
    diagnosis: dict[str, Any],
    *,
    current_version: str | None = None,
) -> dict[str, Any]:
    """Return a deterministic migration report without writing any files."""
    return _public_plan(_build_plan(repo, diagnosis, current_version=current_version))


def apply_provider_migration(
    repo: Path,
    diagnosis: dict[str, Any],
    *,
    authorized: bool = False,
    current_version: str | None = None,
) -> dict[str, Any]:
    """Apply a planned provider/state migration after explicit authorization."""
    internal = _build_plan(repo, diagnosis, current_version=current_version)
    planned = _public_plan(internal)
    if not planned["ok"]:
        return planned
    if not internal["operations"]:
        return {**planned, "status": "current", "changed": False}
    side_effect = side_effect_decision(
        default_plugin_root(),
        "canonical.write",
        {"approved_promoter_write_set"} if authorized else set(),
    )
    if not authorized or not side_effect["authorized"]:
        return {
            **planned,
            "ok": False,
            "status": "authorization_required",
            "changed": False,
            "authorization": "file_migration",
            "sideEffect": side_effect,
        }

    repo = Path(repo).resolve()
    migration_id = internal["migrationId"]
    root = provider_migration_root(repo)
    snapshot_root = root / "snapshots" / migration_id
    checkpoint_path = snapshot_root / "preflight-checkpoint.json"
    manifest_path = snapshot_root / "manifest.json"
    report_path = Path(internal["reportPath"])
    guard_devflow_write(repo, checkpoint_path)
    guard_devflow_write(repo, manifest_path)
    guard_devflow_write(repo, report_path)
    if manifest_path.exists():
        return {
            **planned,
            "ok": False,
            "status": "manual_review_required",
            "changed": False,
            "conflicts": ["migration_snapshot_already_exists"],
            "manifestPath": str(manifest_path),
        }

    try:
        checkpoint = _migration_checkpoint(internal)
        atomic_write(checkpoint_path, _json_text(checkpoint))
        manifest_targets = _capture_snapshot(repo, snapshot_root, internal["operations"])
        manifest: dict[str, Any] = {
            "schemaVersion": SCHEMA_VERSION,
            "kind": MIGRATION_KIND,
            "migrationId": migration_id,
            "sunsetRelease": LEGACY_STATE_SUNSET_RELEASE,
            "status": "snapshot_ready",
            "snapshotVerified": True,
            "durableCheckpoint": {
                "path": checkpoint_path.relative_to(repo).as_posix(),
                "sha256": _fingerprint(checkpoint_path)["sha256"],
                "verified": True,
            },
            "targets": manifest_targets,
            "preservedPaths": internal["report"]["preservedPaths"],
            "selection": internal["report"]["selection"],
            "preMigrationProviderState": internal["report"]["preMigrationProviderState"],
        }
        atomic_write(manifest_path, _json_text(manifest))
        atomic_write(report_path, _json_text(internal["report"]))
    except Exception as error:
        return {
            **planned,
            "ok": False,
            "status": "snapshot_failed",
            "changed": False,
            "manifestPath": str(manifest_path),
            "checkpointPath": str(checkpoint_path),
            "snapshotPath": str(snapshot_root),
            "error": f"{type(error).__name__}: {error}",
        }

    try:
        _assert_apply_preconditions(repo, internal["operations"])
        for operation in internal["operations"]:
            _validate_target(repo, operation["target"])
            _assert_target_fingerprint(
                operation["target"],
                operation["before"],
                operation["path"],
            )
            atomic_write(operation["target"], operation["desiredText"])
    except Exception as error:  # a transactional boundary must handle any writer failure
        restored, restore_errors = _restore_pre_apply(repo, manifest_targets)
        manifest["status"] = "apply_failed_restored" if restored else "manual_review_required"
        manifest["applyError"] = f"{type(error).__name__}: {error}"
        manifest["applyFailureReason"] = (
            "concurrent_target_drift"
            if isinstance(error, ConcurrentTargetDrift)
            else "target_write_failed"
        )
        manifest["restoreErrors"] = restore_errors
        manifest["post"] = _target_post_records(repo, manifest_targets)
        atomic_write(manifest_path, _json_text(manifest))
        return {
            **planned,
            "ok": False,
            "status": manifest["status"],
            "changed": False,
            "manifestPath": str(manifest_path),
            "error": manifest["applyError"],
            "reason": manifest["applyFailureReason"],
            "restoreErrors": restore_errors,
        }

    for target in manifest_targets:
        target["post"] = _fingerprint(repo / target["path"])
        if target["post"] != target["plannedPost"]:
            restored, restore_errors = _restore_pre_apply(repo, manifest_targets)
            manifest["status"] = "apply_failed_restored" if restored else "manual_review_required"
            manifest["applyError"] = f"post_write_hash_mismatch: {target['path']}"
            manifest["restoreErrors"] = restore_errors
            atomic_write(manifest_path, _json_text(manifest))
            return {
                **planned,
                "ok": False,
                "status": manifest["status"],
                "changed": False,
                "manifestPath": str(manifest_path),
                "error": manifest["applyError"],
                "restoreErrors": restore_errors,
            }

    manifest["status"] = "applied"
    atomic_write(manifest_path, _json_text(manifest))
    return {
        **planned,
        "ok": True,
        "status": "applied",
        "changed": True,
        "dryRun": False,
        "manifestPath": str(manifest_path),
        "checkpointPath": str(checkpoint_path),
        "snapshotPath": str(snapshot_root),
        "sideEffect": side_effect,
    }


def rollback_provider_migration(
    repo: Path,
    manifest_path: Path,
    *,
    authorized: bool = False,
) -> dict[str, Any]:
    """Transactionally restore a canonical migration manifest's pre-apply state."""
    repo = Path(repo).resolve()
    manifest_path = Path(manifest_path).expanduser().resolve()
    side_effect = side_effect_decision(
        default_plugin_root(),
        "destructive.cleanup",
        {"explicit_file_list_and_rollback"} if authorized else set(),
    )
    if not authorized or not side_effect["authorized"]:
        return {
            "ok": False,
            "status": "authorization_required",
            "changed": False,
            "authorization": "explicit_file_list_and_rollback",
            "manifestPath": str(manifest_path),
            "sideEffect": side_effect,
        }

    location_errors, snapshot_root = _canonical_manifest_location(repo, manifest_path)
    if location_errors:
        return {
            "ok": False,
            "status": "manual_review_required",
            "changed": False,
            "conflicts": location_errors,
            "manifestPath": str(manifest_path),
            "sideEffect": side_effect,
        }
    try:
        manifest_text = manifest_path.read_text()
        manifest = json.loads(manifest_text)
    except (OSError, json.JSONDecodeError) as error:
        return {
            "ok": False,
            "status": "manual_review_required",
            "changed": False,
            "conflicts": [f"invalid_rollback_manifest: {error}"],
            "manifestPath": str(manifest_path),
            "sideEffect": side_effect,
        }
    if not isinstance(manifest, dict) or manifest.get("kind") != MIGRATION_KIND:
        return {
            "ok": False,
            "status": "manual_review_required",
            "changed": False,
            "conflicts": ["invalid_rollback_manifest_kind"],
            "manifestPath": str(manifest_path),
            "sideEffect": side_effect,
        }
    if manifest.get("status") == "rolled_back":
        return {
            "ok": True,
            "status": "current",
            "changed": False,
            "manifestPath": str(manifest_path),
            "sideEffect": side_effect,
        }

    manifest_errors, targets = _validate_rollback_manifest(
        repo,
        manifest,
        manifest_path,
        snapshot_root,
    )
    if manifest_errors:
        return {
            "ok": False,
            "status": "manual_review_required",
            "changed": False,
            "reason": "invalid_manifest",
            "conflicts": manifest_errors,
            "manifestPath": str(manifest_path),
            "sideEffect": side_effect,
        }

    conflicts: list[dict[str, Any]] = []
    for record in targets:
        try:
            target = _manifest_target(repo, record)
            expected = record.get("post")
            actual = _fingerprint(target)
        except (AttributeError, TypeError, ValueError) as error:
            conflicts.append({"path": None, "error": f"invalid_manifest_target: {error}"})
            continue
        if not isinstance(expected, dict) or actual != expected:
            conflicts.append({"path": record.get("path"), "expected": expected, "actual": actual})
    if conflicts:
        return {
            "ok": False,
            "status": "manual_review_required",
            "changed": False,
            "reason": "hash_mismatch",
            "conflicts": conflicts,
            "manifestPath": str(manifest_path),
            "sideEffect": side_effect,
        }

    snapshot_conflicts = _restore_source_errors(repo, targets, snapshot_root)
    if snapshot_conflicts:
        return {
            "ok": False,
            "status": "manual_review_required",
            "changed": False,
            "reason": "snapshot_hash_mismatch",
            "conflicts": snapshot_conflicts,
            "manifestPath": str(manifest_path),
            "sideEffect": side_effect,
        }

    post_states = _capture_target_states(repo, targets)
    restored, restore_errors, compensation_errors = _rollback_targets_transactionally(
        repo,
        targets,
        snapshot_root,
        post_states,
    )
    if not restored:
        compensated = not compensation_errors
        concurrent_drift = any("ConcurrentTargetDrift" in item for item in restore_errors)
        return {
            "ok": False,
            "status": (
                "manual_review_required"
                if concurrent_drift or not compensated
                else "rollback_failed_restored"
            ),
            "changed": False,
            "reason": (
                "rollback_concurrent_target_drift"
                if concurrent_drift
                else "rollback_restore_failed"
            ),
            "conflicts": restore_errors,
            "compensationErrors": compensation_errors,
            "manifestPath": str(manifest_path),
            "sideEffect": side_effect,
        }

    expected_provider_state = manifest["preMigrationProviderState"]
    try:
        actual_readiness = _rediagnose_provider_readiness(repo, expected_provider_state)
        expected_readiness = expected_provider_state["readiness"]
        readiness_error = None
    except Exception as error:
        actual_readiness = None
        expected_readiness = expected_provider_state.get("readiness")
        readiness_error = f"{type(error).__name__}: {error}"
    if readiness_error or actual_readiness != expected_readiness:
        compensation_errors = _compensate_rollback_targets(repo, post_states)
        return {
            "ok": False,
            "status": (
                "rollback_failed_restored"
                if not compensation_errors
                else "manual_review_required"
            ),
            "changed": False,
            "reason": "provider_readiness_mismatch",
            "expectedReadiness": expected_readiness,
            "actualReadiness": actual_readiness,
            "diagnosisError": readiness_error,
            "compensationErrors": compensation_errors,
            "manifestPath": str(manifest_path),
            "sideEffect": side_effect,
        }
    manifest["status"] = "rolled_back"
    manifest["rollback"] = {
        "verified": True,
        "restored": [record["path"] for record in targets],
        "hashes": _target_post_records(repo, targets),
    }
    try:
        guard_devflow_write(repo, manifest_path)
        atomic_write(manifest_path, _json_text(manifest))
    except Exception as error:
        compensation_errors = _restore_target_states(repo, post_states)
        manifest_restore_errors: list[str] = []
        try:
            atomic_write(manifest_path, manifest_text)
        except Exception as manifest_error:
            manifest_restore_errors.append(
                f"manifest: {type(manifest_error).__name__}: {manifest_error}"
            )
        compensation_errors.extend(manifest_restore_errors)
        return {
            "ok": False,
            "status": "rollback_failed_restored" if not compensation_errors else "manual_review_required",
            "changed": False,
            "reason": "rollback_manifest_write_failed",
            "conflicts": [f"{type(error).__name__}: {error}"],
            "compensationErrors": compensation_errors,
            "manifestPath": str(manifest_path),
            "sideEffect": side_effect,
        }
    return {
        "ok": True,
        "status": "rolled_back",
        "changed": True,
        "manifestPath": str(manifest_path),
        "restoredPaths": [record["path"] for record in targets],
        "sideEffect": side_effect,
    }


def _build_plan(
    repo: Path,
    diagnosis: dict[str, Any],
    *,
    current_version: str | None,
) -> dict[str, Any]:
    repo = Path(repo).resolve()
    conflicts: list[str] = []
    selection = diagnosis.get("selection")
    if not isinstance(selection, dict):
        selection = {}
        conflicts.append("provider_diagnosis_selection_missing")
    profile = selection.get("effectiveMethodologyProfile")
    roadmap = selection.get("effectiveRoadmapProvider")
    selection_errors = selection.get("configErrors", [])
    if isinstance(selection_errors, list):
        conflicts.extend(f"provider_selection_conflict: {error}" for error in selection_errors)
    if profile not in {"core", "lean-matt", "strict-superpowers"}:
        conflicts.append("invalid_methodology_profile")
    if roadmap not in {"none", "gsd"}:
        conflicts.append("invalid_roadmap_provider")
    if diagnosis.get("ok") is not True:
        reasons = diagnosis.get("blockingReasons", [])
        blocking_reasons = (
            [
                reason
                for reason in reasons
                if not str(reason).startswith("core: project skill routing ")
            ]
            if isinstance(reasons, list)
            else []
        )
        if blocking_reasons:
            conflicts.extend(f"provider_not_ready: {reason}" for reason in blocking_reasons)
        elif not isinstance(reasons, list):
            conflicts.append("provider_not_ready")
    if diagnosis.get("methodologyReady") is False:
        conflicts.append("methodology_provider_not_ready")
    if diagnosis.get("roadmapReady") is False:
        conflicts.append("roadmap_provider_not_ready")
    providers = diagnosis.get("providers", {})
    for provider in diagnosis.get("selectedProviders", []):
        report = providers.get(provider, {}) if isinstance(providers, dict) else {}
        if not isinstance(report, dict) or report.get("ready") is not True:
            status = report.get("status", "missing_diagnosis") if isinstance(report, dict) else "missing_diagnosis"
            conflicts.append(f"selected_provider_not_ready: {provider}: {status}")

    try:
        pre_migration_provider_state = _pre_migration_provider_state(diagnosis)
    except (TypeError, ValueError) as error:
        pre_migration_provider_state = {}
        conflicts.append(f"provider_diagnosis_identity_invalid: {error}")

    state_resolution = resolve_state(repo, current_version=current_version)
    active_work = _active_work_conflicts(state_resolution.get("data", {}))
    conflicts.extend(active_work)

    desired: list[dict[str, Any]] = []
    config_path = repo / ".dev-flow.json"
    try:
        config_text = _render_provider_config(config_path, diagnosis)
    except (OSError, json.JSONDecodeError, KeyError, ValueError, TypeError) as error:
        conflicts.append(f"invalid_provider_config: {error}")
    else:
        desired.append(_operation(repo, config_path, config_text, "rewrite", "devflow", "devflow"))

    lock_path = repo / ".planning" / "devflow" / "providers.lock.json"
    lock_text = _json_text(provider_lock_payload(diagnosis))
    desired.append(_operation(repo, lock_path, lock_text, "rewrite", "none-or-devflow", "devflow"))

    namespaced_state = state_path(repo)
    legacy = legacy_state_path(repo)
    if not namespaced_state.exists() and legacy.exists():
        resolution = resolve_state(repo, current_version=current_version)
        if resolution["status"] == "legacy_read_only":
            desired.append(
                _operation(
                    repo,
                    namespaced_state,
                    legacy.read_text(),
                    "copy",
                    "legacy-devflow",
                    "devflow",
                    source=legacy,
                )
            )
        elif resolution["status"] == "legacy_expired":
            conflicts.append("legacy_state_compatibility_expired")
        else:
            conflicts.append(f"root_state_{resolution['status']}")

    for item in desired:
        try:
            _validate_target(repo, item["target"])
        except ValueError as error:
            conflicts.append(f"invalid_migration_target: {error}")
    operations = [item for item in desired if item["before"] != item["after"]]
    public_operations = [_public_operation(item) for item in operations]
    provider_details = diagnosis.get("providers", {})
    gsd_details = provider_details.get("gsd", {}) if isinstance(provider_details, dict) else {}
    tracking = gsd_details.get("tracking") if roadmap == "gsd" and isinstance(gsd_details, dict) else None
    if not isinstance(tracking, dict):
        tracking = planning_tracking_report(
            repo,
            [item["path"] for item in public_operations],
            roadmap_provider="none",
            commit_docs=False,
        )
    status = "blocked" if conflicts else ("planned" if operations else "current")
    report_body: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "kind": MIGRATION_KIND,
        "status": status,
        "sunsetRelease": LEGACY_STATE_SUNSET_RELEASE,
        "selection": {
            "methodologyProfile": profile,
            "roadmapProvider": roadmap,
            "source": selection.get("selectionSource"),
            "evidence": list(selection.get("inferenceEvidence", [])),
        },
        "preMigrationProviderState": pre_migration_provider_state,
        "operations": public_operations,
        "conflicts": conflicts,
        "tracking": tracking,
        "approvals": {
            "fileMigration": {"required": bool(operations), "authorized": False},
            "dependencyActivation": {"required": False, "authorized": False, "separate": True},
        },
        "snapshotPlan": {
            "created": False,
            "targets": [item["path"] for item in public_operations],
        },
        "durableCheckpointPlan": {
            "created": False,
            "requiredBeforeApply": True,
            "recordsPlanAndPreMigrationHashes": True,
        },
        "rollbackPlan": {
            "created": False,
            "hashGuarded": True,
            "onMismatch": "manual_review_required",
        },
        "preservedPaths": _preserved_paths(repo),
    }
    plan_digest = _digest_bytes(_canonical_json(report_body).encode())
    migration_id = plan_digest[:16]
    report_body["planDigest"] = plan_digest
    report_path = provider_migration_root(repo) / "reports" / f"{migration_id}.json"
    snapshot_path = provider_migration_root(repo) / "snapshots" / migration_id
    report_body["snapshotPlan"]["path"] = str(snapshot_path)
    report_body["durableCheckpointPlan"]["path"] = str(snapshot_path / "preflight-checkpoint.json")
    report_body["rollbackPlan"]["manifestPath"] = str(snapshot_path / "manifest.json")
    report_body["reportPath"] = str(report_path)
    return {
        "ok": not conflicts,
        "status": status,
        "dryRun": True,
        "changed": False,
        "sunsetRelease": LEGACY_STATE_SUNSET_RELEASE,
        "migrationId": migration_id,
        "reportPath": str(report_path),
        "snapshotPath": str(snapshot_path),
        "operations": operations,
        "conflicts": conflicts,
        "report": report_body,
    }


def _public_plan(internal: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in internal.items()
        if key not in {"operations"}
    } | {
        "operations": [_public_operation(item) for item in internal["operations"]],
    }


def _operation(
    repo: Path,
    target: Path,
    desired_text: str,
    action: str,
    current_owner: str,
    target_owner: str,
    *,
    source: Path | None = None,
) -> dict[str, Any]:
    target = Path(target).absolute()
    result = {
        "path": target.relative_to(repo).as_posix(),
        "target": target,
        "action": action,
        "currentOwner": current_owner,
        "targetOwner": target_owner,
        "before": _fingerprint(target),
        "after": _fingerprint_text(desired_text),
        "desiredText": desired_text,
    }
    if source is not None:
        result["source"] = Path(source).resolve().relative_to(repo).as_posix()
        result["sourceHash"] = _fingerprint(source)
    return result


def _public_operation(operation: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in operation.items()
        if key not in {"target", "desiredText"}
    }


def _render_provider_config(path: Path, diagnosis: dict[str, Any]) -> str:
    current: dict[str, Any] = {}
    if path.exists():
        loaded = json.loads(path.read_text())
        if not isinstance(loaded, dict):
            raise ValueError("provider config must be a JSON object")
        current = loaded
    selection = diagnosis["selection"]
    workflow = current.get("workflow") if isinstance(current.get("workflow"), dict) else {}
    workflow = dict(workflow)
    workflow["methodology_profile"] = selection["effectiveMethodologyProfile"]
    workflow["roadmap_provider"] = selection["effectiveRoadmapProvider"]
    selectors = normalized_persisted_selectors(diagnosis)
    if selectors:
        workflow["provider_selectors"] = selectors
    workflow["roadmap_bindings"] = dict(selection.get("roadmapBindings", {}))
    current["workflow"] = workflow
    return _json_text(current)


def _capture_snapshot(
    repo: Path,
    snapshot_root: Path,
    operations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for index, operation in enumerate(operations):
        target = operation["target"]
        _validate_target(repo, target)
        pre = dict(operation["before"])
        snapshot_path: Path | None = None
        if pre["exists"]:
            snapshot_path = snapshot_root / "files" / f"{index:02d}-{target.name}"
            guard_devflow_write(repo, snapshot_path)
            atomic_write(snapshot_path, target.read_text())
            snapshot_hash = _fingerprint(snapshot_path)
            if snapshot_hash["sha256"] != pre["sha256"] or snapshot_hash["size"] != pre["size"]:
                raise RuntimeError(f"snapshot hash mismatch: {operation['path']}")
            pre["snapshotPath"] = snapshot_path.relative_to(repo).as_posix()
        targets.append(
            {
                "path": operation["path"],
                "action": operation["action"],
                "pre": pre,
                "plannedPost": dict(operation["after"]),
                "post": None,
            }
        )
    return targets


def _migration_checkpoint(internal: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "kind": f"{MIGRATION_KIND}-preflight-checkpoint",
        "migrationId": internal["migrationId"],
        "planDigest": internal["report"]["planDigest"],
        "selection": internal["report"]["selection"],
        "preMigrationProviderState": internal["report"]["preMigrationProviderState"],
        "conflicts": list(internal["conflicts"]),
        "targets": [
            {
                "path": operation["path"],
                "before": operation["before"],
                "plannedAfter": operation["after"],
            }
            for operation in internal["operations"]
        ],
    }


def _pre_migration_provider_state(diagnosis: dict[str, Any]) -> dict[str, Any]:
    selection = diagnosis.get("selection")
    if not isinstance(selection, dict):
        raise ValueError("provider diagnosis selection missing")
    codex_home_value = selection.get("codexHome")
    if not isinstance(codex_home_value, str) or not codex_home_value.strip():
        raise ValueError("provider diagnosis CODEX_HOME identity missing")
    codex_home = Path(codex_home_value).expanduser().resolve()
    core_plugin_root_value = diagnosis.get("corePluginRoot") or default_plugin_root()
    core_plugin_root = Path(core_plugin_root_value).expanduser().resolve()
    selected = sorted(
        provider
        for provider in diagnosis.get("selectedProviders", [])
        if isinstance(provider, str)
    )
    providers = diagnosis.get("providers", {})
    provider_readiness: dict[str, Any] = {}
    identity_keys = (
        "ready",
        "status",
        "root",
        "runtime",
        "version",
        "manifestDigest",
        "runtimeSha256",
        "contentIdentitySha256",
        "contentManifestSha256",
        "sourceIdentity",
        "skillHashes",
        "agentHashes",
    )
    for provider in selected:
        report = providers.get(provider, {}) if isinstance(providers, dict) else {}
        if not isinstance(report, dict):
            report = {}
        provider_readiness[provider] = _json_clone(
            {key: report.get(key) for key in identity_keys if key in report}
        )
    capabilities = diagnosis.get("capabilities", {})
    if not isinstance(capabilities, dict):
        capabilities = {}
    triggered = sorted(
        capability
        for capability, record in capabilities.items()
        if isinstance(capability, str)
        and isinstance(record, dict)
        and record.get("triggered") is True
    )
    diagnostic_selection = _json_clone(
        {
            "effectiveMethodologyProfile": selection.get("effectiveMethodologyProfile"),
            "effectiveRoadmapProvider": selection.get("effectiveRoadmapProvider"),
            "configErrors": list(selection.get("configErrors") or []),
            "providerSelectors": dict(selection.get("providerSelectors") or {}),
            "roadmapBindings": dict(selection.get("roadmapBindings") or {}),
            "providerLock": dict(selection.get("providerLock") or {}),
        }
    )
    provider_lock = diagnostic_selection.get("providerLock")
    if not isinstance(provider_lock, dict) or not provider_lock.get("providers"):
        diagnostic_selection["providerLock"] = provider_lock_payload(diagnosis)
    return {
        "codexHome": {
            "path": str(codex_home),
            "pathSha256": _digest_bytes(str(codex_home).encode()),
        },
        "corePluginRoot": {
            "path": str(core_plugin_root),
            "pathSha256": _digest_bytes(str(core_plugin_root).encode()),
        },
        "diagnosticSelection": diagnostic_selection,
        "triggeredCapabilities": triggered,
        "readiness": {
            "ok": diagnosis.get("ok") is True,
            "coreReady": diagnosis.get("coreReady"),
            "methodologyReady": diagnosis.get("methodologyReady"),
            "roadmapReady": diagnosis.get("roadmapReady"),
            "goalReady": diagnosis.get("goalReady"),
            "selectedProviders": selected,
            "providers": provider_readiness,
        },
    }


def _json_clone(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, sort_keys=True))
    except (TypeError, ValueError) as error:
        raise ValueError(f"provider diagnosis is not JSON serializable: {error}") from error


def _validate_pre_migration_provider_state(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError("provider state must be an object")
    codex_home = value.get("codexHome")
    if not isinstance(codex_home, dict):
        raise ValueError("CODEX_HOME identity missing")
    path = codex_home.get("path")
    path_sha = codex_home.get("pathSha256")
    if not isinstance(path, str) or not Path(path).is_absolute():
        raise ValueError("CODEX_HOME path must be absolute")
    if not _is_sha256(path_sha) or path_sha != _digest_bytes(str(Path(path).resolve()).encode()):
        raise ValueError("CODEX_HOME identity hash mismatch")
    core_plugin_root = value.get("corePluginRoot")
    if not isinstance(core_plugin_root, dict):
        raise ValueError("core plugin root identity missing")
    plugin_path = core_plugin_root.get("path")
    plugin_path_sha = core_plugin_root.get("pathSha256")
    if not isinstance(plugin_path, str) or not Path(plugin_path).is_absolute():
        raise ValueError("core plugin root path must be absolute")
    if (
        not _is_sha256(plugin_path_sha)
        or plugin_path_sha != _digest_bytes(str(Path(plugin_path).resolve()).encode())
    ):
        raise ValueError("core plugin root identity hash mismatch")
    selection = value.get("diagnosticSelection")
    if not isinstance(selection, dict):
        raise ValueError("diagnostic selection missing")
    if selection.get("effectiveMethodologyProfile") not in {
        "core",
        "lean-matt",
        "strict-superpowers",
    }:
        raise ValueError("diagnostic methodology profile invalid")
    if selection.get("effectiveRoadmapProvider") not in {"none", "gsd"}:
        raise ValueError("diagnostic roadmap provider invalid")
    triggered = value.get("triggeredCapabilities")
    if not isinstance(triggered, list) or any(not isinstance(item, str) for item in triggered):
        raise ValueError("triggered capabilities invalid")
    readiness = value.get("readiness")
    if not isinstance(readiness, dict) or not isinstance(readiness.get("providers"), dict):
        raise ValueError("readiness record missing")


def _rediagnose_provider_readiness(
    repo: Path,
    provider_state: dict[str, Any],
) -> dict[str, Any]:
    _validate_pre_migration_provider_state(provider_state)
    codex_home = Path(provider_state["codexHome"]["path"]).resolve()
    core_plugin_root = Path(provider_state["corePluginRoot"]["path"]).resolve()
    selection = _json_clone(provider_state["diagnosticSelection"])
    selection["codexHome"] = str(codex_home)
    diagnosis = diagnose_provider_selection(
        selection,
        repo,
        codex_home,
        triggered_capabilities=provider_state["triggeredCapabilities"],
        core_plugin_root=core_plugin_root,
    )
    return _pre_migration_provider_state(diagnosis)["readiness"]


def _active_work_conflicts(state: dict[str, Any]) -> list[str]:
    conflicts: list[str] = []
    if not isinstance(state, dict):
        return conflicts
    for key, label in (("current_phase", "phase"), ("current_change", "change")):
        value = state.get(key, {})
        if not isinstance(value, dict):
            continue
        identifier = value.get("id")
        status = str(value.get("status") or "").lower()
        if identifier not in (None, "", "none") and status not in {"complete", "completed", "archived", "shipped"}:
            conflicts.append(f"active_conflicting_{label}: {identifier}")
    return conflicts


def _canonical_manifest_location(repo: Path, manifest_path: Path) -> tuple[list[str], Path]:
    snapshots_root = (provider_migration_root(repo) / "snapshots").resolve()
    snapshot_root = manifest_path.parent
    errors: list[str] = []
    try:
        guard_devflow_write(repo, manifest_path)
    except Exception as error:
        errors.append(f"manifest_outside_provider_migration_root: {error}")
        return errors, snapshot_root
    if (
        manifest_path.name != "manifest.json"
        or snapshot_root.parent != snapshots_root
        or not re.fullmatch(r"[0-9a-f]{16}", snapshot_root.name)
    ):
        errors.append("manifest_not_at_canonical_snapshot_location")
    return errors, snapshot_root


def _validate_rollback_manifest(
    repo: Path,
    manifest: dict[str, Any],
    manifest_path: Path,
    snapshot_root: Path,
) -> tuple[list[str], list[dict[str, Any]]]:
    errors: list[str] = []
    if manifest.get("schemaVersion") != SCHEMA_VERSION:
        errors.append("unsupported_rollback_manifest_schema")
    migration_id = manifest.get("migrationId")
    if migration_id != snapshot_root.name:
        errors.append("manifest_migration_id_does_not_match_snapshot_directory")
    if manifest.get("status") != "applied":
        errors.append(f"rollback_manifest_status_not_applied: {manifest.get('status')}")
    provider_state = manifest.get("preMigrationProviderState")
    try:
        _validate_pre_migration_provider_state(provider_state)
    except (TypeError, ValueError) as error:
        errors.append(f"invalid_pre_migration_provider_state: {error}")

    checkpoint_record = manifest.get("durableCheckpoint")
    checkpoint_payload: dict[str, Any] | None = None
    if not isinstance(checkpoint_record, dict) or checkpoint_record.get("verified") is not True:
        errors.append("durable_checkpoint_attestation_missing")
    else:
        expected_checkpoint = snapshot_root / "preflight-checkpoint.json"
        try:
            checkpoint = _contained_manifest_path(
                repo,
                checkpoint_record.get("path"),
                snapshot_root,
                expected=expected_checkpoint,
                label="checkpoint",
            )
            if checkpoint.is_symlink():
                raise ValueError("checkpoint must not be a symlink")
            checkpoint_fingerprint = _fingerprint(checkpoint)
            expected_sha = checkpoint_record.get("sha256")
            if not _is_sha256(expected_sha) or checkpoint_fingerprint.get("sha256") != expected_sha:
                raise ValueError("checkpoint hash does not match manifest")
            loaded = json.loads(checkpoint.read_text())
            if not isinstance(loaded, dict):
                raise ValueError("checkpoint must be a JSON object")
            checkpoint_payload = loaded
            if loaded.get("kind") != f"{MIGRATION_KIND}-preflight-checkpoint":
                raise ValueError("checkpoint kind mismatch")
            if loaded.get("migrationId") != migration_id:
                raise ValueError("checkpoint migration id mismatch")
            plan_digest = loaded.get("planDigest")
            if not _is_sha256(plan_digest) or not str(plan_digest).startswith(str(migration_id)):
                raise ValueError("checkpoint plan digest mismatch")
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
            errors.append(f"invalid_durable_checkpoint: {error}")

    raw_targets = manifest.get("targets")
    targets: list[dict[str, Any]] = []
    if not isinstance(raw_targets, list) or not raw_targets:
        errors.append("rollback_targets_missing")
        return errors, targets
    seen: set[str] = set()
    for index, record in enumerate(raw_targets):
        if not isinstance(record, dict):
            errors.append(f"invalid_manifest_target[{index}]: target must be an object")
            continue
        path = record.get("path")
        try:
            target = _manifest_target(repo, record)
            if path in seen:
                raise ValueError("duplicate manifest target")
            seen.add(str(path))
            if record.get("action") not in {"rewrite", "copy"}:
                raise ValueError("invalid migration action")
            pre = record.get("pre")
            planned_post = record.get("plannedPost")
            post = record.get("post")
            _validate_fingerprint(pre, "pre")
            _validate_fingerprint(planned_post, "plannedPost")
            _validate_fingerprint(post, "post")
            if post != planned_post:
                raise ValueError("post fingerprint does not match planned post")
            if pre.get("exists"):
                snapshot = _snapshot_path(repo, pre, snapshot_root)
                if snapshot.is_symlink() or snapshot.parent != snapshot_root / "files":
                    raise ValueError("snapshot path is outside migration snapshot files")
            elif "snapshotPath" in pre:
                raise ValueError("absent pre-state must not declare a snapshot")
            if target == manifest_path:
                raise ValueError("manifest cannot be a rollback target")
            targets.append(record)
        except (AttributeError, OSError, TypeError, ValueError) as error:
            errors.append(f"invalid_manifest_target[{index}]: {error}")

    if checkpoint_payload is not None:
        if checkpoint_payload.get("preMigrationProviderState") != provider_state:
            errors.append("provider_state_does_not_match_durable_checkpoint")
        checkpoint_targets = checkpoint_payload.get("targets")
        expected_targets = [
            {
                "path": record.get("path"),
                "before": {
                    key: record.get("pre", {}).get(key)
                    for key in ("exists", "sha256", "size")
                },
                "plannedAfter": record.get("plannedPost"),
            }
            for record in targets
        ]
        if checkpoint_targets != expected_targets:
            errors.append("manifest_targets_do_not_match_durable_checkpoint")
    return errors, targets


def _contained_manifest_path(
    repo: Path,
    relative: Any,
    snapshot_root: Path,
    *,
    expected: Path | None = None,
    label: str,
) -> Path:
    if not isinstance(relative, str):
        raise ValueError(f"{label} path missing")
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError(f"{label} path escapes repository")
    candidate = repo / relative_path
    if candidate.is_symlink() or candidate.parent.is_symlink():
        raise ValueError(f"{label} path must not use a symlink")
    path = candidate.resolve()
    try:
        path.relative_to(snapshot_root)
    except ValueError as error:
        raise ValueError(f"{label} path is outside migration snapshot") from error
    if expected is not None and path != expected:
        raise ValueError(f"{label} path is not canonical")
    return path


def _validate_fingerprint(value: Any, label: str) -> None:
    if not isinstance(value, dict) or set(value) - {"exists", "sha256", "size", "snapshotPath"}:
        raise ValueError(f"{label} fingerprint shape is invalid")
    exists = value.get("exists")
    size = value.get("size")
    sha = value.get("sha256")
    if not isinstance(exists, bool) or not isinstance(size, int) or size < 0:
        raise ValueError(f"{label} fingerprint values are invalid")
    if exists:
        if not _is_sha256(sha):
            raise ValueError(f"{label} fingerprint sha256 is invalid")
    elif sha is not None or size != 0:
        raise ValueError(f"{label} absent fingerprint is invalid")


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _plain_fingerprint(value: dict[str, Any]) -> dict[str, Any]:
    return {key: value.get(key) for key in ("exists", "sha256", "size")}


def _assert_target_fingerprint(
    target: Path,
    expected: dict[str, Any],
    path: str,
) -> None:
    normalized_expected = _plain_fingerprint(expected)
    actual = _fingerprint(target)
    if actual != normalized_expected:
        raise ConcurrentTargetDrift(path, normalized_expected, actual)


def _assert_apply_preconditions(repo: Path, operations: list[dict[str, Any]]) -> None:
    for operation in operations:
        target = _manifest_target(repo, operation)
        _assert_target_fingerprint(target, operation["before"], operation["path"])


def _restore_pre_apply(repo: Path, targets: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    for record in reversed(targets):
        try:
            target = _manifest_target(repo, record)
            pre = record["pre"]
            actual = _fingerprint(target)
            expected_pre = _plain_fingerprint(pre)
            if actual == expected_pre:
                continue
            if actual != record["plannedPost"]:
                raise ConcurrentTargetDrift(record["path"], record["plannedPost"], actual)
            if pre.get("exists"):
                snapshot = _snapshot_path(repo, pre)
                snapshot_fingerprint = _fingerprint(snapshot)
                if snapshot_fingerprint["sha256"] != pre.get("sha256"):
                    raise RuntimeError(f"snapshot hash mismatch: {record['path']}")
                atomic_write(target, snapshot.read_text())
            elif target.exists() or target.is_symlink():
                target.unlink()
            if _fingerprint(target) != expected_pre:
                raise RuntimeError(f"restored hash mismatch: {record['path']}")
        except Exception as error:  # keep restoring independent targets, then report every failure
            errors.append(f"{record.get('path')}: {type(error).__name__}: {error}")
    return not errors, errors


def _capture_target_states(repo: Path, targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    states: list[dict[str, Any]] = []
    for record in targets:
        target = _manifest_target(repo, record)
        fingerprint = _fingerprint(target)
        states.append(
            {
                "record": record,
                "fingerprint": fingerprint,
                "text": target.read_text() if fingerprint["exists"] else None,
            }
        )
    return states


def _rollback_targets_transactionally(
    repo: Path,
    targets: list[dict[str, Any]],
    snapshot_root: Path,
    post_states: list[dict[str, Any]],
) -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    try:
        for state in post_states:
            record = state["record"]
            _assert_target_fingerprint(
                _manifest_target(repo, record),
                state["fingerprint"],
                record["path"],
            )
        for record in reversed(targets):
            expected_post = next(
                state["fingerprint"]
                for state in post_states
                if state["record"]["path"] == record["path"]
            )
            _assert_target_fingerprint(
                _manifest_target(repo, record),
                expected_post,
                record["path"],
            )
            _restore_target_to_pre(repo, record, snapshot_root)
    except Exception as error:
        errors.append(f"{record.get('path')}: {type(error).__name__}: {error}")
        return False, errors, _compensate_rollback_targets(repo, post_states)
    return True, errors, []


def _restore_target_to_pre(repo: Path, record: dict[str, Any], snapshot_root: Path) -> None:
    target = _manifest_target(repo, record)
    pre = record["pre"]
    if pre.get("exists"):
        snapshot = _snapshot_path(repo, pre, snapshot_root)
        atomic_write(target, snapshot.read_text())
    elif target.exists() or target.is_symlink():
        target.unlink()
    expected = {key: pre.get(key) for key in ("exists", "sha256", "size")}
    if _fingerprint(target) != expected:
        raise RuntimeError(f"restored hash mismatch: {record['path']}")


def _restore_target_states(repo: Path, states: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for state in states:
        record = state["record"]
        try:
            target = _manifest_target(repo, record)
            expected = state["fingerprint"]
            if expected["exists"]:
                atomic_write(target, state["text"])
            elif target.exists() or target.is_symlink():
                target.unlink()
            if _fingerprint(target) != expected:
                raise RuntimeError("post-migration compensation hash mismatch")
        except Exception as error:
            errors.append(f"{record.get('path')}: {type(error).__name__}: {error}")
    return errors


def _compensate_rollback_targets(repo: Path, states: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for state in reversed(states):
        record = state["record"]
        try:
            target = _manifest_target(repo, record)
            expected_post = state["fingerprint"]
            actual = _fingerprint(target)
            if actual == expected_post:
                continue
            expected_pre = _plain_fingerprint(record["pre"])
            if actual != expected_pre:
                raise ConcurrentTargetDrift(record["path"], expected_pre, actual)
            if expected_post["exists"]:
                atomic_write(target, state["text"])
            elif target.exists() or target.is_symlink():
                target.unlink()
            if _fingerprint(target) != expected_post:
                raise RuntimeError("post-migration compensation hash mismatch")
        except Exception as error:
            errors.append(f"{record.get('path')}: {type(error).__name__}: {error}")
    return errors


def _restore_source_errors(
    repo: Path,
    targets: list[dict[str, Any]],
    snapshot_root: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    for record in targets:
        try:
            _manifest_target(repo, record)
            pre = record.get("pre")
            if not isinstance(pre, dict):
                raise ValueError("pre-migration fingerprint missing")
            if pre.get("exists"):
                snapshot = _snapshot_path(repo, pre, snapshot_root)
                expected = {key: pre.get(key) for key in ("exists", "sha256", "size")}
                if _fingerprint(snapshot) != expected:
                    raise RuntimeError("snapshot fingerprint does not match manifest")
        except (AttributeError, OSError, TypeError, ValueError, RuntimeError) as error:
            path = record.get("path") if isinstance(record, dict) else None
            errors.append(f"{path}: {type(error).__name__}: {error}")
    return errors


def _target_post_records(repo: Path, targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"path": record["path"], "fingerprint": _fingerprint(_manifest_target(repo, record))}
        for record in targets
    ]


def _manifest_target(repo: Path, record: dict[str, Any]) -> Path:
    relative = record.get("path")
    if not isinstance(relative, str):
        raise ValueError("manifest target path missing")
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError("manifest target path escapes repository")
    target = repo / relative_path
    _validate_target(repo, target)
    return target


def _snapshot_path(
    repo: Path,
    pre: dict[str, Any],
    snapshot_root: Path | None = None,
) -> Path:
    relative = pre.get("snapshotPath")
    if not isinstance(relative, str):
        raise ValueError("snapshot path missing")
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError("snapshot path escapes provider migration root")
    candidate = repo / relative_path
    if candidate.is_symlink() or candidate.parent.is_symlink():
        raise ValueError("snapshot path must not use a symlink")
    path = candidate.resolve()
    allowed_root = (
        Path(snapshot_root).resolve()
        if snapshot_root is not None
        else (provider_migration_root(repo) / "snapshots").resolve()
    )
    try:
        path.relative_to(allowed_root)
    except ValueError as error:
        if snapshot_root is not None:
            raise ValueError("snapshot path is outside migration snapshot") from error
        raise ValueError("snapshot path escapes provider migration root") from error
    return path


def _validate_target(repo: Path, target: Path) -> None:
    repo = Path(repo).resolve()
    target = Path(target).absolute()
    allowed = {
        (repo / ".dev-flow.json").absolute(),
        state_path(repo).absolute(),
        (repo / ".planning" / "devflow" / "providers.lock.json").absolute(),
    }
    if target not in allowed:
        raise ValueError(f"migration target is not owned by DevFlow: {target}")
    if target.is_symlink():
        raise ValueError(f"migration target must not be a symlink: {target}")
    try:
        target.parent.resolve().relative_to(repo)
    except ValueError as error:
        raise ValueError(f"migration target parent escapes repository: {target}") from error
    if target != (repo / ".dev-flow.json").absolute():
        guard_devflow_write(repo, target)


def _preserved_paths(repo: Path) -> list[str]:
    candidates = [
        repo / ".planning" / "STATE.md",
        repo / ".planning" / "ROADMAP.md",
        repo / ".planning" / "PROJECT.md",
        repo / ".planning" / "phases",
        repo / ".planning" / "codebase",
        repo / ".agents" / "skills",
        repo / "AGENTS.md.generated",
    ]
    return [path.relative_to(repo).as_posix() for path in candidates if path.exists() or path.is_symlink()]


def _fingerprint(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {"exists": False, "sha256": None, "size": 0}
    data = path.read_bytes()
    return {"exists": True, "sha256": _digest_bytes(data), "size": len(data)}


def _fingerprint_text(text: str) -> dict[str, Any]:
    data = text.encode()
    return {"exists": True, "sha256": _digest_bytes(data), "size": len(data)}


def _digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _json_text(value: Any) -> str:
    return f"{json.dumps(value, indent=2, sort_keys=True)}\n"


plan_migration = plan_provider_migration
apply_migration = apply_provider_migration
rollback_migration = rollback_provider_migration
