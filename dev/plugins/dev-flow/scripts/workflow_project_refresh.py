from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from legacy_workflow_config import (
    LEGACY_WORKFLOW_FIELD_ALIASES,
    inspect_legacy_workflow_config,
)
from plugin_preflight_hooks import hook_cache_drift_issues
from workflow_contract_control_plane import CONTROL_PLANE_TEMPLATES
from workflow_planning_paths import atomic_write_devflow, guard_devflow_write, plugin_migration_root
from workflow_validate import missing_agents_guidance, validate_workflow_state


PLAN_SCHEMA_VERSION = "1.0"
PLAN_KIND = "devflow-project-refresh-plan"
RESULT_SCHEMA_VERSION = "1.0"
RESULT_KIND = "devflow-project-refresh-result"
RECEIPT_SCHEMA_VERSION = "1.0"
APPLY_RECEIPT_KIND = "devflow-project-refresh-apply-receipt"
VERIFICATION_RECEIPT_KIND = "devflow-project-refresh-verification-receipt"
ROLLBACK_RECEIPT_KIND = "devflow-project-refresh-rollback-receipt"
PROJECT_REFRESH_AUTHORIZATION = "project-refresh-apply"
WORKFLOW_CONFIG_AUTHORIZATION = "workflow-config-migration"
MIGRATION_STEP_REGISTRY = {
    "legacy-selection-v0-to-v1": {
        "from": 0,
        "to": 1,
        "authorization": WORKFLOW_CONFIG_AUTHORIZATION,
        "configTarget": 1,
        "planner": "legacy-selection-v0-to-v1",
        "verifier": "configuration-schema-v1",
    },
    "full-openspec-v1-to-v2": {
        "from": 1,
        "to": 2,
        "authorization": WORKFLOW_CONFIG_AUTHORIZATION,
        "configTarget": 2,
        "planner": "merge-config-target",
        "verifier": "configuration-schema-v2",
    },
}


def plan_project_refresh(
    repo: str | Path,
    plugin_root: str | Path,
    codex_home: str | Path | None = None,
    *,
    _active_transaction_id: str | None = None,
) -> dict[str, Any]:
    """Return a deterministic, read-only refresh plan for one project."""
    del codex_home
    repo_path = Path(repo).expanduser().resolve()
    if not _is_adopted(repo_path):
        plan = {
            "schemaVersion": PLAN_SCHEMA_VERSION,
            "kind": PLAN_KIND,
            "ok": True,
            "status": "not_applicable",
            "repo": str(repo_path),
            "adopted": False,
            "actions": [],
            "readSet": [],
            "writeSet": [],
            "requiredAuthorizations": [],
            "manualActions": [],
            "preservedPaths": [],
            "verification": [],
            "retryability": _retryability("not_applicable"),
            "nextAction": "No DevFlow project-refresh action is applicable.",
        }
        plan["planSha256"] = _plan_digest(plan)
        return plan
    plugin_path = Path(plugin_root).expanduser().resolve()
    contract = _load_refresh_contract(plugin_path)
    if contract["errors"]:
        plan = {
            "schemaVersion": PLAN_SCHEMA_VERSION,
            "kind": PLAN_KIND,
            "ok": False,
            "status": "blocked",
            "repo": str(repo_path),
            "adopted": True,
            "sourceIdentity": contract["identity"],
            "contractErrors": contract["errors"],
            "actions": [],
            "readSet": [],
            "sourceReadSet": contract["sourceReadSet"],
            "writeSet": [],
            "requiredAuthorizations": [],
            "manualActions": [],
            "preservedPaths": [],
            "verification": [],
            "retryability": _retryability("blocked"),
            "nextAction": "Repair the project-refresh contract before planning any project write.",
        }
        plan["planSha256"] = _plan_digest(plan)
        return plan
    config, config_action, config_manual = _inspect_config(repo_path, contract)
    observed_schema = config.get("observedSchema")
    config_baseline_unsupported = config.get("status") == "baseline_unsupported"
    skill_surface = _inspect_managed_skills(repo_path, plugin_path, contract)
    control_surface = _inspect_managed_control_plane(repo_path, plugin_path, contract)
    agents_surface = _inspect_agents_guidance(repo_path, plugin_path, contract)
    legacy_surface = _inspect_legacy_skill_layout(repo_path, contract)
    state_surface = _inspect_migration_state(repo_path, contract, observed_schema)
    recorded_schema = state_surface["summary"].get("recordedProjectSchemaVersion")
    schema_evidence_conflict = bool(
        state_surface["summary"].get("evidenceTrusted")
        and isinstance(observed_schema, int)
        and isinstance(recorded_schema, int)
        and observed_schema != recorded_schema
    )
    if schema_evidence_conflict:
        config["status"] = "baseline_ambiguous"
        config["reason"] = "configuration_state_schema_disagreement"
        config_action = None
    recovery_surface = _inspect_retained_transactions(
        repo_path,
        active_transaction_id=_active_transaction_id,
    )
    actions = [config_action] if config_action else []
    actions.extend(control_surface["actions"])
    actions.extend(skill_surface["actions"])
    actions.extend(agents_surface["actions"])
    manual_actions = [config_manual] if config_manual else []
    manual_actions.extend(control_surface["manualActions"])
    manual_actions.extend(skill_surface["manualActions"])
    manual_actions.extend(agents_surface["manualActions"])
    manual_actions.extend(legacy_surface["manualActions"])
    manual_actions.extend(state_surface["manualActions"])
    manual_actions.extend(recovery_surface["manualActions"])
    if schema_evidence_conflict:
        manual_actions.append(
            {
                "kind": "workflow-config",
                "path": ".dev-flow.json",
                "reason": "configuration_state_schema_disagreement",
            }
        )
    write_set = sorted({str(action["path"]) for action in actions})
    authorizations = sorted({str(action["authorization"]) for action in actions})
    preserved_paths = sorted(
        {
            str(item["path"])
            for item in manual_actions
            if isinstance(item, dict) and item.get("path")
        }
    )
    if schema_evidence_conflict:
        migration_path, path_error = [], "configuration_state_schema_disagreement"
    elif config_baseline_unsupported:
        migration_path, path_error = [], "unsupported_project_schema_marker"
    elif config_manual:
        migration_path, path_error = [], None
    else:
        migration_path, path_error = _resolve_migration_path(observed_schema, contract)
    content_manual = bool(
        config_manual
        or control_surface["manualActions"]
        or skill_surface["manualActions"]
        or agents_surface["manualActions"]
        or legacy_surface["manualActions"]
    )
    if schema_evidence_conflict:
        project_content_status = "baseline_ambiguous"
    elif config_baseline_unsupported:
        project_content_status = "baseline_unsupported"
    elif path_error:
        project_content_status = "baseline_ambiguous" if observed_schema is None else "blocked"
    elif actions:
        project_content_status = "migration_pending"
    elif content_manual:
        project_content_status = "manual_review_required"
    else:
        project_content_status = "current" if config["status"] == "current" else config["status"]
    state_sync_required = (
        project_content_status == "current"
        and state_surface["summary"]["status"] in {"missing", "stale"}
    )
    if state_sync_required:
        authorizations = sorted({*authorizations, PROJECT_REFRESH_AUTHORIZATION})
    if recovery_surface["summary"]["status"] != "current":
        status = "blocked"
    elif state_surface["summary"]["status"] == "manual_review_required":
        status = "blocked"
    elif schema_evidence_conflict:
        status = "baseline_ambiguous"
    elif config_baseline_unsupported:
        status = "blocked"
    elif path_error:
        status = "baseline_ambiguous" if observed_schema is None else "blocked"
    elif actions:
        status = "migration_pending"
    elif content_manual:
        status = "manual_review_required"
    elif state_sync_required:
        status = "migration_pending"
    else:
        status = "current" if config["status"] == "current" else config["status"]
    read_set = sorted(
        {
            ".dev-flow.json",
            *skill_surface["readSet"],
            *control_surface["readSet"],
            *agents_surface["readSet"],
            *legacy_surface["readSet"],
            *state_surface["readSet"],
            *recovery_surface["readSet"],
        }
    )
    plan = {
        "schemaVersion": PLAN_SCHEMA_VERSION,
        "kind": PLAN_KIND,
        "ok": status not in {"baseline_ambiguous", "blocked"},
        "status": status,
        "repo": str(repo_path),
        "adopted": True,
        "sourceIdentity": contract["identity"],
        "contractErrors": [path_error] if path_error else [],
        "projectSchema": {"observed": observed_schema, "target": contract["projectSchemaHead"]},
        "projectContentStatus": project_content_status,
        "migrationPath": migration_path,
        "migrationState": state_surface["summary"],
        "stateSyncRequired": state_sync_required,
        "recovery": recovery_surface["summary"],
        "config": config,
        "managedSkills": skill_surface["summary"],
        "controlPlane": control_surface["summary"],
        "agentsGuidance": agents_surface["summary"],
        "legacySkillLayout": legacy_surface["summary"],
        "actions": actions,
        "readSet": read_set,
        "sourceReadSet": contract["sourceReadSet"],
        "writeSet": write_set,
        "requiredAuthorizations": authorizations,
        "manualActions": manual_actions,
        "preservedPaths": preserved_paths,
        "verification": [
            "configuration-schema",
            "project-migration-sync",
            "managed-path-readback",
            "workflow-validation",
            "cache-drift-diagnosis",
            "agents-disposition",
        ],
        "retryability": _retryability(status),
        "nextAction": (
            "No project refresh action is required."
            if status == "current"
            else (
                "Apply the sealed plan with its named authorization."
                if status == "migration_pending"
                else "Resolve every manual project-refresh item and produce a fresh plan."
            )
        ),
    }
    plan["unrelatedWorktree"] = _unrelated_worktree(
        repo_path,
        {*plan["readSet"], *plan["writeSet"]},
    )
    plan["planSha256"] = _plan_digest(plan)
    return plan


def apply_project_refresh(
    repo: str | Path,
    plugin_root: str | Path,
    *,
    expected_plan: str,
    authorizations: set[str] | None = None,
    selected_actions: set[str] | None = None,
    fault_injection: str | None = None,
    codex_home: str | Path | None = None,
) -> dict[str, Any]:
    """Apply one sealed project-refresh plan after fail-closed recomputation."""
    repo_path = Path(repo).expanduser().resolve()
    plugin_path = Path(plugin_root).expanduser().resolve()
    current = plan_project_refresh(repo_path, plugin_path, codex_home)
    if current["planSha256"] != expected_plan:
        return _result(
            current,
            ok=False,
            status="plan_stale",
            next_action="Produce and review a fresh project-refresh plan.",
        )
    if not current["ok"] or current["status"] in {"blocked", "baseline_ambiguous"}:
        return _result(
            current,
            ok=False,
            status="blocked",
            next_action=current["nextAction"],
        )

    action_ids = [str(action["id"]) for action in current["actions"]]
    if len(action_ids) != len(set(action_ids)):
        result = _result(
            current,
            ok=False,
            status="blocked",
            next_action="Repair duplicate action identifiers and produce a fresh plan.",
        )
        result["conflicts"] = ["duplicate_action_id"]
        return result
    action_map = {str(action["id"]): action for action in current["actions"]}
    selected_ids = set(action_map) if selected_actions is None else set(selected_actions)
    unknown = sorted(selected_ids - set(action_map))
    if unknown:
        result = _result(
            current,
            ok=False,
            status="blocked",
            next_action="Select only action IDs present in the sealed plan.",
        )
        result["conflicts"] = [f"unknown_action:{item}" for item in unknown]
        return result
    selected = _ordered_selected_actions(action_map, selected_ids)
    remaining_actions = [action for action_id, action in action_map.items() if action_id not in selected_ids]
    incomplete = bool(remaining_actions or current.get("manualActions"))
    required_for_selection = {str(action["authorization"]) for action in selected}
    if not selected and current.get("stateSyncRequired"):
        required_for_selection.add(PROJECT_REFRESH_AUTHORIZATION)
    missing = sorted(required_for_selection - set(authorizations or set()))
    if missing:
        result = _result(
            current,
            ok=False,
            status="authorization_required",
            next_action="Supply every named authorization for the selected actions.",
        )
        result["missingAuthorizations"] = missing
        return result
    conflicts = _preflight_actions(repo_path, selected)
    if conflicts:
        result = _result(
            current,
            ok=False,
            status="blocked",
            next_action="Resolve every preflight conflict and produce a fresh plan.",
        )
        result["conflicts"] = conflicts
        return result
    if not selected and not current.get("stateSyncRequired"):
        status = "current" if current["status"] == "current" else current["status"]
        result = _result(
            current,
            ok=status == "current",
            status=status,
            next_action=(
                "No selected project-refresh action required a write."
                if status == "current"
                else "Select and authorize a dependency-closed action set or resolve the manual items."
            ),
        )
        result["remainingAuthorizations"] = sorted(
            {str(action["authorization"]) for action in current["actions"]}
        )
        result["manualActions"] = list(current.get("manualActions", []))
        return result

    runtime = plugin_migration_root(repo_path)
    runtime_existed = runtime.exists()
    transactions_root = runtime / "transactions"
    transactions_existed = transactions_root.exists()
    receipts_root = runtime / "receipts"
    receipts_existed = receipts_root.exists()
    transaction_id = uuid.uuid4().hex
    transaction_root = transactions_root / transaction_id
    stage_root = transaction_root / "stage"
    receipt_path = runtime / "receipts" / f"apply-{transaction_id}.json"
    verification_receipt_path = runtime / "receipts" / f"verification-{transaction_id}.json"
    guard_devflow_write(repo_path, transaction_root / "contract.json")
    guard_devflow_write(repo_path, receipt_path)
    guard_devflow_write(repo_path, verification_receipt_path)
    state_path = runtime / "state.json"
    state_before_fingerprint = _fingerprint(state_path)
    state_before = _read_optional_json(state_path)
    receipt_reference = receipt_path.relative_to(repo_path).as_posix()
    planned_action_set_sha256 = _planned_action_set_digest(
        current,
        selected,
        authorizations or set(),
        state_before,
        state_before_fingerprint,
        receipt_reference,
    )
    transaction_contract = {
        "schemaVersion": "1.0",
        "kind": "devflow-project-refresh-transaction",
        "transactionId": transaction_id,
        "planSha256": current["planSha256"],
        "repo": str(repo_path),
        "selectedActions": [str(action["id"]) for action in selected],
        "actions": selected,
        "authorizations": sorted(authorizations or set()),
        "sourceIdentity": current.get("sourceIdentity"),
        "stateBefore": state_before,
        "stateBeforeFingerprint": state_before_fingerprint,
        "plannedActionSetSha256": planned_action_set_sha256,
        "applyReceiptPath": receipt_reference,
        "retention": "cleanup-after-terminal-receipt",
    }
    transaction_root.mkdir(parents=True, exist_ok=False)
    atomic_write_devflow(
        repo_path,
        transaction_root / "contract.json",
        _json_text(transaction_contract),
    )
    stage_root.mkdir()
    promoted: list[dict[str, Any]] = []
    state_written = False
    verification: dict[str, Any] = {}
    written_receipts: list[Path] = []
    try:
        staged = _stage_actions(repo_path, plugin_path, stage_root, selected)
        for index, item in enumerate(staged):
            if fault_injection == f"promotion:{item['action']['id']}":
                raise OSError("injected promotion failure")
            try:
                _promote_action(repo_path, item)
            except Exception:
                target = _project_target(repo_path, str(item["action"]["path"]))
                if _fingerprint(target) == item["action"].get("afterFingerprint"):
                    promoted.append(item["action"])
                raise
            promoted.append(item["action"])
            if fault_injection == f"after-promotion:{index}":
                raise OSError("injected post-promotion failure")
        verification = _verify_actions(
            repo_path,
            promoted,
            plugin_root=plugin_path,
            codex_home=Path(codex_home).expanduser().resolve() if codex_home is not None else None,
            require_complete=not incomplete,
            allow_state_sync_pending=not incomplete,
            active_transaction_id=transaction_id,
        )
        if fault_injection in {"verification", "rollback"}:
            verification = {"ok": False, "issues": ["injected_verification_failure"]}
        if not verification["ok"]:
            raise ProjectRefreshVerificationError(verification["issues"])
        completion_status = "incomplete" if incomplete else "current"
        verification_receipt_reference = verification_receipt_path.relative_to(
            repo_path
        ).as_posix()
        action_set_sha256 = _apply_action_set_digest(
            current,
            selected,
            authorizations or set(),
            state_before,
            state_before_fingerprint,
            verification,
            "available",
            receipt_reference,
            verification_receipt_reference,
            completion_status,
        )
        next_state = _next_migration_state(
            state_before,
            current,
            selected,
            receipt_reference,
            action_set_sha256,
            incomplete=incomplete,
        )
        atomic_write_devflow(repo_path, state_path, _json_text(next_state))
        state_written = True
        receipt = _apply_receipt(
            current,
            selected,
            authorizations or set(),
            receipt_path,
            state_before,
            state_before_fingerprint,
            _fingerprint(state_path),
            verification,
            action_set_sha256,
            status="applied_incomplete" if incomplete else "applied_and_verified",
            verification_receipt_path=verification_receipt_reference,
        )
        verification_receipt = _verification_receipt(
            current,
            selected,
            authorizations or set(),
            state_before,
            state_before_fingerprint,
            verification,
            _fingerprint(state_path),
            action_set_sha256,
            receipt_reference,
            verification_receipt_reference,
            incomplete=incomplete,
        )
        atomic_write_devflow(repo_path, verification_receipt_path, _json_text(verification_receipt))
        written_receipts.append(verification_receipt_path)
        atomic_write_devflow(repo_path, receipt_path, _json_text(receipt))
        written_receipts.append(receipt_path)
    except Exception as error:
        for written_receipt in written_receipts:
            try:
                written_receipt.unlink()
            except OSError:
                pass
        if not receipts_existed:
            try:
                receipts_root.rmdir()
            except OSError:
                pass
        rollback = _rollback_promoted(
            repo_path,
            promoted,
            state_path,
            state_before,
            state_written=state_written,
            fail=fault_injection == "rollback",
        )
        if rollback["ok"]:
            _cleanup_transaction_root(
                transaction_root,
                transactions_existed=transactions_existed,
                runtime_existed=runtime_existed,
            )
            result = _result(
                current,
                ok=False,
                status="verification_failed_rolled_back",
                next_action="Inspect the failure and produce a fresh plan before retrying.",
            )
            result["rollbackStatus"] = "complete"
            result["error"] = type(error).__name__
            result["verification"] = verification
            return result
        result = _result(
            current,
            ok=False,
            status="rollback_failed",
            next_action="Preserve recovery evidence and repair the retained transaction manually.",
        )
        result["rollbackStatus"] = "failed"
        result["error"] = type(error).__name__
        result["rollbackIssues"] = rollback["issues"]
        result["retainedTransactionPath"] = transaction_root.relative_to(repo_path).as_posix()
        return result
    _cleanup_transaction_root(
        transaction_root,
        transactions_existed=transactions_existed,
        runtime_existed=runtime_existed,
    )
    result = _result(
        current,
        ok=True,
        status="applied_incomplete" if incomplete else "applied_and_verified",
        next_action=(
            "Review the receipt, resolve every remaining authorization or manual item, and replan."
            if incomplete
            else "Review the receipt and continue with the next approved refresh item."
        ),
    )
    result["changedPaths"] = sorted(str(action["path"]) for action in selected)
    result["rollbackStatus"] = "available"
    result["receiptPath"] = str(receipt_path)
    result["verificationReceiptPath"] = str(verification_receipt_path)
    result["verification"] = verification
    result["remainingAuthorizations"] = sorted(
        {str(action["authorization"]) for action in remaining_actions}
    )
    result["manualActions"] = list(current.get("manualActions", []))
    return result


class ProjectRefreshVerificationError(RuntimeError):
    def __init__(self, issues: list[str]):
        self.issues = list(issues)
        super().__init__("; ".join(self.issues))


def verify_project_refresh(
    repo: str | Path,
    plugin_root: str | Path,
    receipt: str | Path,
    codex_home: str | Path | None = None,
) -> dict[str, Any]:
    repo_path = Path(repo).expanduser().resolve()
    plugin_path = Path(plugin_root).expanduser().resolve()
    receipt_path = _receipt_path(repo_path, receipt)
    document = _read_receipt(receipt_path)
    codex_home_path = (
        Path(codex_home).expanduser().resolve() if codex_home is not None else None
    )
    receipt_kind = document.get("kind")
    if receipt_kind == APPLY_RECEIPT_KIND:
        receipt_issues = _validate_apply_receipt(repo_path, receipt_path, document)
        receipt_incomplete = document.get("status") != "applied_and_verified"
    elif receipt_kind == VERIFICATION_RECEIPT_KIND:
        receipt_issues = _validate_verification_receipt(repo_path, receipt_path, document)
        receipt_incomplete = document.get("completionStatus") != "current"
    else:
        receipt_issues = ["receipt_kind_invalid"]
        receipt_incomplete = True
    if receipt_issues:
        return {
            "schemaVersion": RESULT_SCHEMA_VERSION,
            "kind": RESULT_KIND,
            "ok": False,
            "status": "verification_failed",
            "repo": str(repo_path),
            "codexHome": str(codex_home_path) if codex_home_path is not None else None,
            "receiptPath": str(receipt_path),
            "issues": receipt_issues,
            "completionIssues": [],
            "retryability": _retryability("verification_failed"),
            "nextAction": "Use only an intact project-refresh receipt created for this repository.",
        }
    current = plan_project_refresh(repo_path, plugin_path, codex_home_path)
    issues: list[str] = []
    if current.get("sourceIdentity") != document.get("sourceIdentity"):
        issues.append("source_identity_changed")
    actions = document.get("actions") if isinstance(document.get("actions"), list) else []
    action_verification = _verify_actions(
        repo_path,
        actions,
        plugin_root=plugin_path,
        codex_home=codex_home_path,
        require_complete=not receipt_incomplete,
        allow_state_sync_pending=True,
    )
    issues.extend(action_verification["issues"])
    state_path = plugin_migration_root(repo_path) / "state.json"
    if _fingerprint(state_path) != document.get("stateAfterFingerprint"):
        issues.append("migration_state_changed")
    completion_issues: list[str] = []
    if receipt_incomplete:
        completion_issues.append("apply_receipt_incomplete")
    receipt_bound_state_only = bool(
        current.get("projectContentStatus") == "current"
        and current.get("stateSyncRequired")
        and not current.get("actions")
        and not current.get("manualActions")
        and current.get("recovery", {}).get("status") == "current"
    )
    if current.get("status") != "current" and not receipt_bound_state_only:
        completion_issues.append(f"project_status:{current.get('status')}")
    verified = not issues and not completion_issues
    return {
        "schemaVersion": RESULT_SCHEMA_VERSION,
        "kind": RESULT_KIND,
        "ok": verified,
        "status": (
            "verified"
            if verified
            else ("verified_incomplete" if not issues and completion_issues else "verification_failed")
        ),
        "repo": str(repo_path),
        "codexHome": str(codex_home_path) if codex_home_path is not None else None,
        "receiptPath": str(receipt_path),
        "issues": sorted(set(issues)),
        "completionIssues": sorted(set(completion_issues)),
        "verification": action_verification,
        "retryability": _retryability(
            "verified" if verified else ("verified_incomplete" if not issues else "verification_failed")
        ),
        "nextAction": (
            "No verification repair is required."
            if verified
            else "Resolve verification or manual items before claiming project refresh completion."
        ),
    }


def rollback_project_refresh(
    repo: str | Path,
    plugin_root: str | Path,
    receipt: str | Path,
    *,
    apply: bool = False,
) -> dict[str, Any]:
    del plugin_root
    repo_path = Path(repo).expanduser().resolve()
    receipt_path = _receipt_path(repo_path, receipt)
    document = _read_receipt(receipt_path, APPLY_RECEIPT_KIND)
    if not apply:
        return {
            "schemaVersion": RESULT_SCHEMA_VERSION,
            "kind": RESULT_KIND,
            "ok": False,
            "status": "authorization_required",
            "repo": str(repo_path),
            "changedPaths": [],
            "retryability": _retryability("authorization_required"),
            "nextAction": "Rerun rollback with explicit apply authorization.",
        }
    receipt_issues = _validate_apply_receipt(repo_path, receipt_path, document)
    if receipt_issues:
        return {
            "schemaVersion": RESULT_SCHEMA_VERSION,
            "kind": RESULT_KIND,
            "ok": False,
            "status": "rollback_blocked",
            "repo": str(repo_path),
            "changedPaths": [],
            "issues": receipt_issues,
            "retryability": _retryability("rollback_blocked"),
            "nextAction": "Use only the intact apply receipt created for this repository.",
        }
    actions = document.get("actions") if isinstance(document.get("actions"), list) else []
    issues: list[str] = []
    for action in actions:
        target = _project_target(repo_path, str(action.get("path") or ""))
        if _fingerprint(target) != action.get("afterFingerprint"):
            issues.append(f"post_apply_edit:{action.get('path')}")
    state_path = plugin_migration_root(repo_path) / "state.json"
    if _fingerprint(state_path) != document.get("stateAfterFingerprint"):
        issues.append("post_apply_edit:migration_state")
    if issues:
        return {
            "schemaVersion": RESULT_SCHEMA_VERSION,
            "kind": RESULT_KIND,
            "ok": False,
            "status": "rollback_blocked",
            "repo": str(repo_path),
            "changedPaths": [],
            "issues": issues,
            "retryability": _retryability("rollback_blocked"),
            "nextAction": "Preserve post-apply edits and review rollback manually.",
        }
    rollback = _rollback_promoted(
        repo_path,
        actions,
        state_path,
        document.get("stateBefore"),
        state_written=True,
        fail=False,
    )
    if not rollback["ok"]:
        return {
            "schemaVersion": RESULT_SCHEMA_VERSION,
            "kind": RESULT_KIND,
            "ok": False,
            "status": "rollback_failed",
            "repo": str(repo_path),
            "changedPaths": rollback["changedPaths"],
            "issues": rollback["issues"],
            "retryability": _retryability("rollback_failed"),
            "nextAction": "Preserve recovery evidence and complete rollback manually.",
        }
    rollback_id = uuid.uuid4().hex
    rollback_path = plugin_migration_root(repo_path) / "receipts" / f"rollback-{rollback_id}.json"
    rollback_receipt = {
        "schemaVersion": RECEIPT_SCHEMA_VERSION,
        "kind": ROLLBACK_RECEIPT_KIND,
        "createdAt": _now_iso(),
        "repo": str(repo_path),
        "applyReceiptPath": receipt_path.relative_to(repo_path).as_posix(),
        "changedPaths": sorted(str(action["path"]) for action in actions),
        "status": "rolled_back",
    }
    atomic_write_devflow(repo_path, rollback_path, _json_text(rollback_receipt))
    return {
        "schemaVersion": RESULT_SCHEMA_VERSION,
        "kind": RESULT_KIND,
        "ok": True,
        "status": "rolled_back",
        "repo": str(repo_path),
        "changedPaths": rollback_receipt["changedPaths"],
        "receiptPath": str(rollback_path),
        "retryability": _retryability("rolled_back"),
        "nextAction": "Produce a fresh plan before any subsequent project refresh.",
    }


def _result(
    plan: dict[str, Any],
    *,
    ok: bool,
    status: str,
    next_action: str,
) -> dict[str, Any]:
    return {
        "schemaVersion": RESULT_SCHEMA_VERSION,
        "kind": RESULT_KIND,
        "ok": ok,
        "status": status,
        "repo": plan["repo"],
        "planSha256": plan["planSha256"],
        "changedPaths": [],
        "preservedPaths": list(plan.get("preservedPaths", [])),
        "rollbackStatus": "not_started",
        "receiptPath": None,
        "retryability": _retryability(status),
        "nextAction": next_action,
    }


def _retryability(status: str) -> str:
    if status in {"current", "not_applicable", "applied_and_verified", "verified", "rolled_back"}:
        return "not_needed"
    if status == "authorization_required":
        return "after_authorization"
    if status in {"rollback_failed"}:
        return "manual_recovery_required"
    if status in {"plan_stale", "verification_failed_rolled_back"}:
        return "after_replan"
    if status in {"invalid_request"}:
        return "after_correction"
    return "after_remediation"


def _ordered_selected_actions(
    action_map: dict[str, dict[str, Any]],
    selected_ids: set[str],
) -> list[dict[str, Any]]:
    ordered: list[dict[str, Any]] = []
    pending = set(selected_ids)
    while pending:
        ready = sorted(
            identifier
            for identifier in pending
            if set(map(str, action_map[identifier].get("dependencies", []))) <= (selected_ids - pending)
        )
        if not ready:
            return [action_map[identifier] for identifier in sorted(selected_ids)]
        for identifier in ready:
            ordered.append(action_map[identifier])
            pending.remove(identifier)
    return ordered


def _preflight_actions(repo: Path, actions: list[dict[str, Any]]) -> list[str]:
    repo = Path(repo).expanduser().resolve()
    issues: list[str] = []
    raw_identifiers = [str(action.get("id")) for action in actions]
    identifiers = set(raw_identifiers)
    if len(raw_identifiers) != len(identifiers):
        issues.append("duplicate_action_id")
    paths: list[tuple[str, Path]] = []
    for action in actions:
        identifier = str(action.get("id") or "")
        kind = str(action.get("kind") or "")
        relative = str(action.get("path") or "")
        if kind not in {"create_file", "replace_json", "create_symlink", "replace_symlink"}:
            issues.append(f"unknown_operation:{identifier}")
            continue
        if action.get("ownership") not in {
            "devflow-workflow-config",
            "devflow-create-if-absent",
            "devflow-managed-project-skill",
            "human-merge-candidate",
        }:
            issues.append(f"ownership_ambiguous:{identifier}")
        try:
            target = _project_target(repo, relative)
        except ValueError as error:
            issues.append(f"invalid_path:{identifier}:{error}")
            continue
        paths.append((identifier, Path(relative)))
        if _fingerprint(target) != action.get("beforeFingerprint"):
            issues.append(f"before_fingerprint_changed:{identifier}")
        dependencies = action.get("dependencies")
        dependencies = dependencies if isinstance(dependencies, list) else []
        missing_dependencies = sorted(set(map(str, dependencies)) - identifiers)
        issues.extend(f"missing_dependency:{identifier}:{item}" for item in missing_dependencies)
        rollback = action.get("rollback")
        if not isinstance(rollback, dict):
            issues.append(f"rollback_missing:{identifier}")
        elif kind == "replace_json" and rollback.get("kind") != "git_blob":
            issues.append(f"rollback_incomplete:{identifier}")
        elif kind == "replace_json" and not _git_rollback_is_available(repo, action):
            issues.append(f"rollback_source_unavailable:{identifier}")
        elif kind in {"create_file", "create_symlink"} and rollback.get("kind") != "remove_if_created":
            issues.append(f"rollback_incomplete:{identifier}")
        elif kind == "replace_symlink" and rollback.get("kind") != "restore_symlink":
            issues.append(f"rollback_incomplete:{identifier}")
        source = action.get("source")
        if not isinstance(source, dict):
            issues.append(f"source_missing:{identifier}")
        elif kind in {"create_symlink", "replace_symlink"}:
            raw_source = source.get("target")
            if (
                source.get("kind") != "symlink"
                or not isinstance(raw_source, str)
                or not _trusted_skill_source(Path(raw_source))
            ):
                issues.append(f"source_untrusted:{identifier}")
        parents = rollback.get("pruneEmptyParents", []) if isinstance(rollback, dict) else []
        if not isinstance(parents, list):
            issues.append(f"rollback_parents_invalid:{identifier}")
        else:
            for parent in parents:
                try:
                    parent_path = _project_target(repo, str(parent))
                except ValueError:
                    issues.append(f"rollback_parent_invalid:{identifier}:{parent}")
                    continue
                if parent_path.exists() or parent_path.is_symlink():
                    issues.append(f"planned_parent_now_exists:{identifier}:{parent}")
    for index, (first_id, first) in enumerate(paths):
        for second_id, second in paths[index + 1 :]:
            if first == second or first in second.parents or second in first.parents:
                issues.append(f"path_overlap:{first_id}:{second_id}")
    return sorted(set(issues))


def _stage_actions(
    repo: Path,
    plugin_root: Path,
    stage_root: Path,
    actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    staged: list[dict[str, Any]] = []
    contract = _load_refresh_contract(plugin_root)
    for index, action in enumerate(actions):
        stage = stage_root / f"{index:04d}-{action['id']}"
        target = _project_target(repo, str(action["path"]))
        if action["kind"] in {"create_symlink", "replace_symlink"}:
            source = action["source"]["target"]
            stage.symlink_to(source, target_is_directory=True)
        else:
            content = _action_content(repo, plugin_root, contract, action)
            stage.write_bytes(content)
            mode = (
                stat.S_IMODE(target.stat().st_mode)
                if target.exists() and not target.is_symlink()
                else 0o644
            )
            stage.chmod(mode)
        if _fingerprint(stage) != action.get("afterFingerprint"):
            raise ValueError(f"staged fingerprint mismatch: {action['id']}")
        staged.append({"action": action, "stage": stage})
    return staged


def _action_content(
    repo: Path,
    plugin_root: Path,
    contract: dict[str, Any],
    action: dict[str, Any],
) -> bytes:
    identifier = str(action["id"])
    source_descriptor = action.get("source")
    source_descriptor = source_descriptor if isinstance(source_descriptor, dict) else {}
    source_kind = source_descriptor.get("kind")
    if source_kind == "current_config_target" or identifier == "create-current-workflow-config":
        adapter = contract["adapter"]
        target_version = str(contract["projectSchemaHead"])
        relative = adapter["configTargets"][target_version]
        source = _source_path(plugin_root, relative)
        if source is None or source.is_symlink() or not source.is_file():
            raise ValueError("current config target is unavailable")
        return source.read_bytes()
    if source_kind in {"pure_migration_path", "pure_migration_step"} or identifier == "legacy-selection-v0-to-v1":
        raw_steps = source_descriptor.get("steps")
        step_ids = (
            list(map(str, raw_steps))
            if isinstance(raw_steps, list) and raw_steps
            else [str(source_descriptor.get("id") or identifier)]
        )
        path = _project_target(repo, str(action["path"]))
        payload = json.loads(path.read_text())
        if not isinstance(payload, dict):
            raise ValueError("legacy config root is not an object")
        migrated = _apply_config_migration_steps(payload, step_ids, contract)
        return _json_text(migrated).encode()
    if source_kind in {"plugin_file", "rendered_plugin_template"}:
        relative = source_descriptor.get("path")
        if not isinstance(relative, str):
            raise ValueError(f"source path missing: {identifier}")
        source = _source_path(plugin_root, relative)
        if source is None or source.is_symlink() or not source.is_file():
            raise ValueError(f"source file is unavailable: {identifier}")
        content = source.read_text()
        if source_kind == "rendered_plugin_template":
            values = source_descriptor.get("values")
            if not isinstance(values, dict):
                raise ValueError(f"template values missing: {identifier}")
            for key, value in sorted(values.items()):
                content = content.replace("{{" + str(key) + "}}", str(value))
        return content.encode()
    raise ValueError(f"unknown action content: {identifier}")


def _promote_action(repo: Path, staged: dict[str, Any]) -> None:
    action = staged["action"]
    stage = Path(staged["stage"])
    target = _project_target(repo, str(action["path"]))
    if _fingerprint(target) != action.get("beforeFingerprint"):
        raise OSError(f"target changed after preflight: {action['id']}")
    target.parent.mkdir(parents=True, exist_ok=True)
    os.replace(stage, target)
    if _fingerprint(target) != action.get("afterFingerprint"):
        raise OSError(f"promoted fingerprint mismatch: {action['id']}")


def _verify_actions(
    repo: Path,
    actions: list[dict[str, Any]],
    *,
    plugin_root: Path | None = None,
    codex_home: Path | None = None,
    require_complete: bool = False,
    allow_state_sync_pending: bool = False,
    active_transaction_id: str | None = None,
) -> dict[str, Any]:
    issues: list[str] = []
    check_results: list[dict[str, Any]] = []
    for action in actions:
        path = _project_target(repo, str(action.get("path") or ""))
        if _fingerprint(path) != action.get("afterFingerprint"):
            issues.append(f"managed_path_mismatch:{action.get('id')}")
            continue
        if action.get("path") == ".dev-flow.json":
            try:
                payload = json.loads(path.read_text())
            except (OSError, UnicodeError, json.JSONDecodeError):
                issues.append("configuration_schema_invalid")
                continue
            workflow = payload.get("workflow") if isinstance(payload, dict) else None
            recognized, _ = _legacy_inputs(payload if isinstance(payload, dict) else {})
            if not isinstance(workflow, dict) or workflow.get("mode") != "full-openspec":
                issues.append("configuration_mode_invalid")
            if recognized:
                issues.append("retired_configuration_fields_remain")
    check_results.append(
        {
            "name": "managed-path-readback",
            "status": "passed" if not issues else "failed",
            "issues": list(issues),
        }
    )
    non_blocking: list[str] = []
    if plugin_root is not None:
        post_plan = plan_project_refresh(
            repo,
            plugin_root,
            codex_home,
            _active_transaction_id=active_transaction_id,
        )
        remaining_selected = sorted(
            {str(action["id"]) for action in actions}
            & {str(action["id"]) for action in post_plan.get("actions", [])}
        )
        sync_issues = [f"selected_action_still_pending:{identifier}" for identifier in remaining_selected]
        state_only_pending = bool(
            allow_state_sync_pending
            and post_plan.get("projectContentStatus") == "current"
            and post_plan.get("stateSyncRequired")
        )
        if require_complete and post_plan.get("status") != "current" and not state_only_pending:
            sync_issues.append(f"project_status:{post_plan.get('status')}")
        if require_complete:
            issues.extend(sync_issues)
        else:
            non_blocking.extend(sync_issues)
        check_results.append(
            {
                "name": "project-migration-sync",
                "status": "passed" if not sync_issues else ("failed" if require_complete else "incomplete"),
                "issues": sync_issues,
            }
        )
        agents_status = post_plan.get("agentsGuidance", {}).get("status", "not_applicable")
        agents_issues = [] if agents_status in {"unchanged", "not_applicable"} else [f"agents:{agents_status}"]
        if require_complete:
            issues.extend(agents_issues)
        else:
            non_blocking.extend(agents_issues)
        check_results.append(
            {
                "name": "agents-disposition",
                "status": "passed" if not agents_issues else ("failed" if require_complete else "incomplete"),
                "issues": agents_issues,
            }
        )
        contract = _load_refresh_contract(plugin_root)
        workflow_contract_present = bool(
            contract.get("projectLocalSkills")
            or contract.get("managedFiles")
            or contract.get("agentsGuidance")
        )
        if workflow_contract_present:
            workflow = validate_workflow_state(repo, plugin_root=plugin_root, codex_home=codex_home)
            workflow_issues = [str(item) for item in workflow.get("issues", [])]
            if require_complete:
                issues.extend(f"workflow_validation:{item}" for item in workflow_issues)
            else:
                non_blocking.extend(f"workflow_validation:{item}" for item in workflow_issues)
            check_results.append(
                {
                    "name": "workflow-validation",
                    "status": (
                        "passed"
                        if not workflow_issues
                        else ("failed" if require_complete else "incomplete")
                    ),
                    "issues": workflow_issues,
                }
            )
            cache_issues = hook_cache_drift_issues(plugin_root, codex_home=codex_home)
            if require_complete:
                issues.extend(f"cache_drift:{item}" for item in cache_issues)
            else:
                non_blocking.extend(f"cache_drift:{item}" for item in cache_issues)
            check_results.append(
                {
                    "name": "cache-drift-diagnosis",
                    "status": "passed" if not cache_issues else ("failed" if require_complete else "incomplete"),
                    "issues": cache_issues,
                }
            )
        else:
            check_results.extend(
                [
                    {"name": "workflow-validation", "status": "not_applicable", "issues": []},
                    {"name": "cache-drift-diagnosis", "status": "not_applicable", "issues": []},
                ]
            )
    return {
        "ok": not issues,
        "issues": sorted(set(issues)),
        "nonBlockingIssues": sorted(set(non_blocking)),
        "checks": [
            "configuration-schema",
            "managed-path-readback",
            "project-migration-sync",
            "workflow-validation",
            "cache-drift-diagnosis",
            "agents-disposition",
        ],
        "checkResults": check_results,
    }


def _next_migration_state(
    state_before: dict[str, Any] | None,
    plan: dict[str, Any],
    selected_actions: list[dict[str, Any]],
    receipt_reference: str,
    action_set_sha256: str,
    *,
    incomplete: bool,
) -> dict[str, Any]:
    state = json.loads(json.dumps(state_before)) if state_before is not None else {}
    state["schemaVersion"] = "2.0"
    plugins = state.get("plugins")
    if not isinstance(plugins, dict):
        plugins = {}
        state["plugins"] = plugins
    identity = plan["sourceIdentity"]
    name = str(identity["plugin"])
    prior = plugins.get(name)
    prior = prior if isinstance(prior, dict) else {}
    applied = set(map(str, prior.get("appliedMigrationIds", [])))
    selected_ids = {str(action["id"]) for action in selected_actions}
    selected_migration_ids: set[str] = set()
    for action in selected_actions:
        source = action.get("source")
        source = source if isinstance(source, dict) else {}
        if source.get("kind") == "pure_migration_path" and isinstance(source.get("steps"), list):
            selected_migration_ids.update(map(str, source["steps"]))
        elif source.get("kind") == "pure_migration_step":
            selected_migration_ids.add(str(source.get("id") or action["id"]))
    applied.update(
        identifier
        for identifier in map(str, plan.get("migrationPath", []))
        if identifier in selected_migration_ids
    )
    observed_schema = plan.get("projectSchema", {}).get("observed")
    config_selected = bool(selected_migration_ids) or (
        "create-current-workflow-config" in selected_ids
    )
    project_schema_version = identity["projectSchemaHead"] if config_selected else observed_schema
    plugins[name] = {
        **prior,
        "version": identity["pluginVersion"],
        "pluginVersion": identity["pluginVersion"],
        "engineSchemaVersion": identity["engineSchemaVersion"],
        "projectSchemaVersion": project_schema_version,
        "refreshContractRevision": identity["refreshContractRevision"],
        "refreshContractDigest": identity["refreshContractDigest"],
        "appliedMigrationIds": sorted(applied),
        "lastVerifiedReceipt": receipt_reference,
        "lastApplyActionSetSha256": action_set_sha256,
        "lastSyncedAt": _now_iso(),
        "refreshStatus": "incomplete" if incomplete else "current",
    }
    return state


def _apply_receipt(
    plan: dict[str, Any],
    actions: list[dict[str, Any]],
    authorizations: set[str],
    receipt_path: Path,
    state_before: dict[str, Any] | None,
    state_before_fingerprint: dict[str, Any],
    state_after_fingerprint: dict[str, Any],
    verification: dict[str, Any],
    action_set_sha256: str,
    *,
    status: str,
    verification_receipt_path: str,
) -> dict[str, Any]:
    receipt = {
        "schemaVersion": RECEIPT_SCHEMA_VERSION,
        "kind": APPLY_RECEIPT_KIND,
        "createdAt": _now_iso(),
        "repo": plan["repo"],
        "status": status,
        "planSha256": plan["planSha256"],
        "sourceIdentity": plan["sourceIdentity"],
        "projectSchema": plan["projectSchema"],
        "migrationPath": plan["migrationPath"],
        "actions": actions,
        "authorizations": sorted(authorizations),
        "changedPaths": sorted(str(action["path"]) for action in actions),
        "preservedPaths": list(plan.get("preservedPaths", [])),
        "stateBefore": state_before,
        "stateBeforeFingerprint": state_before_fingerprint,
        "stateAfterFingerprint": state_after_fingerprint,
        "verification": verification,
        "verificationReceiptPath": verification_receipt_path,
        "actionSetSha256": action_set_sha256,
        "rollbackStatus": "available",
        "receiptPath": receipt_path.relative_to(Path(plan["repo"])).as_posix(),
        "valuesRedacted": True,
    }
    receipt["receiptEvidenceSha256"] = _receipt_evidence_digest(receipt)
    return receipt


def _planned_action_set_digest(
    plan: dict[str, Any],
    actions: list[dict[str, Any]],
    authorizations: set[str],
    state_before: dict[str, Any] | None,
    state_before_fingerprint: dict[str, Any],
    receipt_reference: str,
) -> str:
    payload = {
        "repo": plan["repo"],
        "planSha256": plan["planSha256"],
        "sourceIdentity": plan.get("sourceIdentity"),
        "projectSchema": plan.get("projectSchema"),
        "migrationPath": plan.get("migrationPath", []),
        "actions": actions,
        "authorizations": sorted(authorizations),
        "changedPaths": sorted(str(action["path"]) for action in actions),
        "preservedPaths": list(plan.get("preservedPaths", [])),
        "stateBefore": state_before,
        "stateBeforeFingerprint": state_before_fingerprint,
        "receiptPath": receipt_reference,
        "phase": "planned",
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _apply_action_set_digest(
    plan: dict[str, Any],
    actions: list[dict[str, Any]],
    authorizations: set[str],
    state_before: dict[str, Any] | None,
    state_before_fingerprint: dict[str, Any],
    verification: dict[str, Any],
    rollback_status: str,
    apply_receipt_reference: str,
    verification_receipt_reference: str,
    completion_status: str,
) -> str:
    payload = {
        "repo": plan["repo"],
        "planSha256": plan["planSha256"],
        "sourceIdentity": plan.get("sourceIdentity"),
        "projectSchema": plan.get("projectSchema"),
        "migrationPath": plan.get("migrationPath", []),
        "actions": actions,
        "authorizations": sorted(authorizations),
        "changedPaths": sorted(str(action["path"]) for action in actions),
        "preservedPaths": list(plan.get("preservedPaths", [])),
        "stateBefore": state_before,
        "stateBeforeFingerprint": state_before_fingerprint,
        "verification": verification,
        "rollbackStatus": rollback_status,
        "applyReceiptPath": apply_receipt_reference,
        "verificationReceiptPath": verification_receipt_reference,
        "completionStatus": completion_status,
        "phase": "verified",
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _receipt_evidence_digest(document: dict[str, Any]) -> str:
    payload = {
        key: value
        for key, value in document.items()
        if key != "receiptEvidenceSha256"
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _verification_receipt(
    plan: dict[str, Any],
    actions: list[dict[str, Any]],
    authorizations: set[str],
    state_before: dict[str, Any] | None,
    state_before_fingerprint: dict[str, Any],
    verification: dict[str, Any],
    state_after_fingerprint: dict[str, Any],
    action_set_sha256: str,
    apply_receipt_path: str,
    receipt_path: str,
    *,
    incomplete: bool,
) -> dict[str, Any]:
    receipt = {
        "schemaVersion": RECEIPT_SCHEMA_VERSION,
        "kind": VERIFICATION_RECEIPT_KIND,
        "createdAt": _now_iso(),
        "repo": plan["repo"],
        "status": "verified",
        "completionStatus": "incomplete" if incomplete else "current",
        "planSha256": plan["planSha256"],
        "sourceIdentity": plan["sourceIdentity"],
        "projectSchema": plan["projectSchema"],
        "migrationPath": plan["migrationPath"],
        "actions": actions,
        "authorizations": sorted(authorizations),
        "changedPaths": sorted(str(action["path"]) for action in actions),
        "preservedPaths": list(plan.get("preservedPaths", [])),
        "stateBefore": state_before,
        "stateBeforeFingerprint": state_before_fingerprint,
        "stateAfterFingerprint": state_after_fingerprint,
        "actionSetSha256": action_set_sha256,
        "verification": verification,
        "rollbackStatus": "available",
        "applyReceiptPath": apply_receipt_path,
        "receiptPath": receipt_path,
        "valuesRedacted": True,
    }
    receipt["receiptEvidenceSha256"] = _receipt_evidence_digest(receipt)
    return receipt


def _rollback_promoted(
    repo: Path,
    actions: list[dict[str, Any]],
    state_path: Path,
    state_before: dict[str, Any] | None,
    *,
    state_written: bool,
    fail: bool,
) -> dict[str, Any]:
    if fail:
        return {"ok": False, "issues": ["injected_rollback_failure"], "changedPaths": []}
    issues: list[str] = []
    changed: list[str] = []
    if state_written:
        try:
            if state_before is None:
                if state_path.exists() or state_path.is_symlink():
                    state_path.unlink()
            else:
                atomic_write_devflow(repo, state_path, _json_text(state_before))
            changed.append(state_path.relative_to(repo).as_posix())
        except (OSError, ValueError) as error:
            issues.append(f"state_rollback_failed:{type(error).__name__}")
    for action in reversed(actions):
        relative = str(action.get("path") or "")
        target = _project_target(repo, relative)
        rollback = action.get("rollback")
        try:
            if not isinstance(rollback, dict):
                raise ValueError("rollback metadata missing")
            if _fingerprint(target) != action.get("afterFingerprint"):
                raise ValueError("promoted path changed before rollback")
            if rollback.get("kind") == "remove_if_created":
                target.unlink()
            elif rollback.get("kind") == "git_blob":
                content = _git_rollback_bytes(repo, action)
                _atomic_project_write(target, content, int(rollback.get("mode") or 0o644))
                if _fingerprint(target) != action.get("beforeFingerprint"):
                    raise ValueError("restored fingerprint mismatch")
            elif rollback.get("kind") == "restore_symlink":
                raw_target = rollback.get("target")
                if not isinstance(raw_target, str):
                    raise ValueError("symlink rollback target missing")
                temporary = target.parent / f".devflow-refresh-{uuid.uuid4().hex}"
                temporary.symlink_to(raw_target, target_is_directory=True)
                os.replace(temporary, target)
                if _fingerprint(target) != action.get("beforeFingerprint"):
                    raise ValueError("restored symlink fingerprint mismatch")
            else:
                raise ValueError("unsupported rollback kind")
            for parent in rollback.get("pruneEmptyParents", []):
                try:
                    _project_target(repo, str(parent)).rmdir()
                except OSError:
                    pass
            changed.append(relative)
        except (OSError, ValueError, subprocess.CalledProcessError) as error:
            issues.append(f"path_rollback_failed:{relative}:{type(error).__name__}")
    return {"ok": not issues, "issues": issues, "changedPaths": sorted(changed)}


def _cleanup_transaction_root(
    transaction_root: Path,
    *,
    transactions_existed: bool,
    runtime_existed: bool,
) -> None:
    shutil.rmtree(transaction_root, ignore_errors=True)
    transactions_root = transaction_root.parent
    runtime = transactions_root.parent
    if not transactions_existed:
        try:
            transactions_root.rmdir()
        except OSError:
            pass
    if not runtime_existed:
        try:
            runtime.rmdir()
        except OSError:
            pass


def _git_rollback_is_available(repo: Path, action: dict[str, Any]) -> bool:
    try:
        content = _git_rollback_bytes(repo, action)
    except (OSError, ValueError, subprocess.CalledProcessError):
        return False
    return _bytes_fingerprint(content) == action.get("beforeFingerprint")


def _git_rollback_bytes(repo: Path, action: dict[str, Any]) -> bytes:
    rollback = action["rollback"]
    commit = str(rollback["commit"])
    expected_blob = str(rollback["blob"])
    relative = str(action["path"])
    actual_blob = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", f"{commit}:{relative}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if actual_blob != expected_blob:
        raise ValueError("rollback blob identity changed")
    return subprocess.run(
        ["git", "-C", str(repo), "show", f"{commit}:{relative}"],
        check=True,
        capture_output=True,
    ).stdout


def _atomic_project_write(path: Path, payload: bytes, mode: int) -> None:
    temporary = path.parent / f".devflow-refresh-{uuid.uuid4().hex}"
    try:
        temporary.write_bytes(payload)
        temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        if temporary.exists() or temporary.is_symlink():
            temporary.unlink()


def apply_verified_skill_tree_transaction(
    repo: str | Path,
    operations: list[dict[str, Any]],
    *,
    replace_path: Callable[[Path, Path], Any] | None = None,
) -> dict[str, Any]:
    """Promote verified project-local Skill trees through the central executor."""
    repo_path = Path(repo).expanduser().resolve()
    replace = replace_path or (lambda source, target: os.replace(source, target))
    issues: list[str] = []
    normalized: list[dict[str, Any]] = []
    seen_targets: set[str] = set()
    for operation in operations:
        identifier = str(operation.get("id") or "")
        skill = str(operation.get("skill") or "")
        relative = (Path(".agents") / "skills" / skill).as_posix()
        if not identifier or not skill or Path(skill).name != skill or relative in seen_targets:
            issues.append(f"verified_tree_identity_invalid:{identifier or skill}")
            continue
        seen_targets.add(relative)
        try:
            target = _project_target(repo_path, relative)
        except ValueError:
            issues.append(f"verified_tree_path_untrusted:{skill}")
            continue
        before = _tree_fingerprint(target)
        if before["kind"] not in {"absent", "tree", "symlink"}:
            issues.append(f"verified_tree_target_untrusted:{skill}")
        if before["kind"] != "absent" and not bool(operation.get("replace")):
            issues.append(f"verified_tree_target_exists:{skill}")
        files = operation.get("files")
        if not isinstance(files, dict) or "SKILL.md" not in files:
            issues.append(f"verified_tree_payload_invalid:{skill}")
            continue
        normalized_files: dict[str, dict[str, Any]] = {}
        for raw_relative, raw_record in files.items():
            requested = Path(str(raw_relative))
            normalized_relative = requested.as_posix()
            if (
                requested.is_absolute()
                or not requested.parts
                or ".." in requested.parts
                or not isinstance(raw_record, dict)
                or not isinstance(raw_record.get("content"), bytes)
                or not isinstance(raw_record.get("mode"), int)
            ):
                issues.append(f"verified_tree_file_invalid:{skill}:{raw_relative}")
                continue
            if normalized_relative in normalized_files:
                issues.append(f"verified_tree_file_duplicate:{skill}:{normalized_relative}")
                continue
            normalized_files[normalized_relative] = {
                "content": raw_record["content"],
                "mode": int(raw_record["mode"]) & 0o777,
            }
        normalized_paths = [Path(relative) for relative in normalized_files]
        for index, first in enumerate(normalized_paths):
            for second in normalized_paths[index + 1 :]:
                if first in second.parents or second in first.parents:
                    issues.append(f"verified_tree_file_overlap:{skill}:{first}:{second}")
        expected = _tree_payload_fingerprint(normalized_files)
        declared = operation.get("expectedSha256")
        if not isinstance(declared, dict):
            issues.append(f"verified_tree_source_digest_missing:{skill}")
        else:
            actual_hashes = {
                relative_path: hashlib.sha256(record["content"]).hexdigest()
                for relative_path, record in normalized_files.items()
            }
            if actual_hashes != {str(key): str(value) for key, value in declared.items()}:
                issues.append(f"verified_tree_source_digest_mismatch:{skill}")
        normalized.append(
            {
                "id": identifier,
                "skill": skill,
                "path": relative,
                "target": target,
                "before": before,
                "after": expected,
                "files": normalized_files,
            }
        )
    if issues:
        return {
            "ok": False,
            "status": "blocked",
            "changedPaths": [],
            "rolledBack": False,
            "rollbackStatus": "not_started",
            "issues": sorted(set(issues)),
        }
    transaction_id = uuid.uuid4().hex
    transaction_parent = plugin_migration_root(repo_path) / "verified-tree-transactions"
    root = transaction_parent / transaction_id
    try:
        guard_devflow_write(repo_path, root / "contract.json")
    except (OSError, RuntimeError, ValueError) as error:
        return {
            "ok": False,
            "status": "blocked",
            "changedPaths": [],
            "rolledBack": False,
            "rollbackStatus": "not_started",
            "issues": [f"verified_tree_transaction_root_untrusted:{type(error).__name__}"],
        }
    created_parents = _missing_transaction_parents(repo_path, transaction_parent)
    identifiers = {item["id"] for item in normalized}
    if identifiers and all(identifier.startswith("install-matt-skill:") for identifier in identifiers):
        stage_root = root / f".devflow-matt-stage-{transaction_id}"
        backup_root = root / f".devflow-matt-backup-{transaction_id}"
        item_paths = {
            item["skill"]: {
                "stage": stage_root / f".devflow-matt-stage-{item['skill']}-{transaction_id}",
                "backup": backup_root / f".devflow-matt-backup-{item['skill']}-{transaction_id}",
            }
            for item in normalized
        }
    elif identifiers and all("openspec" in identifier for identifier in identifiers):
        stage_root = root / f".devflow-openspec-stage-{transaction_id}"
        backup_root = root / f".devflow-openspec-backup-{transaction_id}"
        item_paths = {
            item["skill"]: {
                "stage": stage_root / item["skill"],
                "backup": backup_root / item["skill"],
            }
            for item in normalized
        }
    else:
        stage_root = root / "stage"
        backup_root = root / "backup"
        item_paths = {
            item["skill"]: {
                "stage": stage_root / item["skill"],
                "backup": backup_root / item["skill"],
            }
            for item in normalized
        }
    promoted: list[dict[str, Any]] = []
    try:
        root.mkdir(parents=True, exist_ok=False)
        atomic_write_devflow(
            repo_path,
            root / "contract.json",
            _json_text(
                {
                    "schemaVersion": "1.0",
                    "kind": "devflow-verified-skill-tree-transaction",
                    "transactionId": transaction_id,
                    "operations": [
                        {
                            "id": item["id"],
                            "path": item["path"],
                            "beforeFingerprint": item["before"],
                            "afterFingerprint": item["after"],
                            "files": sorted(item["files"]),
                        }
                        for item in normalized
                    ],
                }
            ),
        )
        stage_root.mkdir()
        backup_root.mkdir()
        for item in normalized:
            staged = item_paths[item["skill"]]["stage"]
            staged.mkdir()
            for relative, record in sorted(item["files"].items()):
                target_file = staged.joinpath(*Path(relative).parts)
                target_file.parent.mkdir(parents=True, exist_ok=True)
                target_file.write_bytes(record["content"])
                target_file.chmod(record["mode"])
            if _tree_fingerprint(staged) != item["after"]:
                raise OSError(f"verified tree stage mismatch: {item['skill']}")
        for item in normalized:
            target = _project_target(repo_path, item["path"])
            if _tree_fingerprint(target) != item["before"]:
                raise OSError(f"verified tree target changed: {item['skill']}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target = _project_target(repo_path, item["path"])
            backup = item_paths[item["skill"]]["backup"]
            record = {**item, "backup": backup, "hadBefore": item["before"]["kind"] != "absent"}
            if record["hadBefore"]:
                replace(target, backup)
            promoted.append(record)
            replace(item_paths[item["skill"]]["stage"], target)
            if _tree_fingerprint(target) != item["after"]:
                raise OSError(f"verified tree promotion mismatch: {item['skill']}")
    except (OSError, RuntimeError, ValueError, shutil.Error) as error:
        rollback_errors: list[str] = []
        for item in reversed(promoted):
            target = item["target"]
            backup = item["backup"]
            try:
                _remove_central_path(target)
                if item["hadBefore"]:
                    if not (backup.exists() or backup.is_symlink()):
                        raise OSError(f"verified tree backup missing: {item['skill']}")
                    replace(backup, target)
                    if _tree_fingerprint(target) != item["before"]:
                        raise OSError(f"verified tree rollback mismatch: {item['skill']}")
            except (OSError, ValueError, shutil.Error) as rollback_error:
                rollback_errors.append(str(rollback_error))
        if rollback_errors:
            return {
                "ok": False,
                "status": "transaction-rollback-failed",
                "changedPaths": sorted(
                    item["path"]
                    for item in normalized
                    if _tree_fingerprint(item["target"]) != item["before"]
                ),
                "rolledBack": False,
                "rollbackStatus": "backup-retained",
                "error": str(error),
                "rollbackErrors": rollback_errors,
                "retainedTransactionPath": root.relative_to(repo_path).as_posix(),
                "retainedBackupPath": backup_root.relative_to(repo_path).as_posix(),
            }
        shutil.rmtree(root, ignore_errors=True)
        _prune_created_transaction_parents(created_parents)
        return {
            "ok": False,
            "status": "transaction-rolled-back",
            "changedPaths": [],
            "rolledBack": True,
            "rollbackStatus": "complete",
            "error": str(error),
        }
    shutil.rmtree(root, ignore_errors=True)
    _prune_created_transaction_parents(created_parents)
    return {
        "ok": True,
        "status": "applied",
        "changedPaths": sorted(item["path"] for item in normalized),
        "rolledBack": False,
        "rollbackStatus": "available",
    }


def apply_managed_skill_link(
    repo: str | Path,
    skill: str,
    source: str | Path,
    *,
    replace_existing: bool,
    trusted_root: str | Path | None = None,
    replace_path: Callable[[Path, Path], Any] | None = None,
) -> dict[str, Any]:
    repo_path = Path(repo).expanduser().resolve()
    raw_source = Path(source).expanduser()
    source_path = raw_source.resolve(strict=False)
    if trusted_root is not None:
        raw_root = Path(trusted_root).expanduser()
        resolved_root = raw_root.resolve(strict=False)
        if raw_root.is_symlink():
            return {"ok": False, "status": "source-untrusted", "changedPaths": []}
        try:
            source_path.relative_to(resolved_root)
            raw_source.relative_to(raw_root)
        except ValueError:
            return {"ok": False, "status": "source-untrusted", "changedPaths": []}
        cursor = raw_source
        while cursor != raw_root:
            if cursor.is_symlink():
                return {"ok": False, "status": "source-untrusted", "changedPaths": []}
            cursor = cursor.parent
    if not _trusted_skill_source(source_path):
        return {"ok": False, "status": "source-untrusted", "changedPaths": []}
    relative = (Path(".agents") / "skills" / skill).as_posix()
    try:
        target = _project_target(repo_path, relative)
    except ValueError:
        return {"ok": False, "status": "target-untrusted", "changedPaths": []}
    before = _fingerprint(target)
    if before["kind"] not in {"absent", "symlink"}:
        return {"ok": False, "status": "source-conflict", "changedPaths": []}
    if before["kind"] == "symlink" and not replace_existing:
        return {"ok": False, "status": "source-conflict", "changedPaths": []}
    replace = replace_path or (lambda left, right: os.replace(left, right))
    transaction_id = uuid.uuid4().hex
    transaction_parent = plugin_migration_root(repo_path) / "verified-tree-transactions"
    root = transaction_parent / transaction_id
    try:
        guard_devflow_write(repo_path, root / "contract.json")
    except (OSError, RuntimeError, ValueError):
        return {"ok": False, "status": "target-untrusted", "changedPaths": []}
    created_parents = _missing_transaction_parents(repo_path, transaction_parent)
    stage = root / "stage-link"
    backup = root / "backup-link"
    promoted = False
    try:
        root.mkdir(parents=True, exist_ok=False)
        atomic_write_devflow(
            repo_path,
            root / "contract.json",
            _json_text(
                {
                    "schemaVersion": "1.0",
                    "kind": "devflow-managed-skill-link-transaction",
                    "transactionId": transaction_id,
                    "path": relative,
                    "source": str(source_path),
                    "beforeFingerprint": before,
                    "afterFingerprint": _symlink_fingerprint(str(source_path)),
                }
            ),
        )
        stage.symlink_to(source_path, target_is_directory=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        target = _project_target(repo_path, relative)
        if _fingerprint(target) != before:
            raise OSError("managed Skill link target changed")
        if before["kind"] == "symlink":
            replace(target, backup)
        promoted = True
        replace(stage, target)
        if _fingerprint(target) != _symlink_fingerprint(str(source_path)):
            raise OSError("managed Skill link promotion mismatch")
    except (OSError, RuntimeError, ValueError) as error:
        rollback_errors: list[str] = []
        if promoted:
            try:
                _remove_central_path(target)
                if before["kind"] == "symlink":
                    replace(backup, target)
                    if _fingerprint(target) != before:
                        raise OSError("managed Skill link rollback mismatch")
            except OSError as rollback_error:
                rollback_errors.append(str(rollback_error))
        if rollback_errors:
            return {
                "ok": False,
                "status": "transaction-rollback-failed",
                "changedPaths": [relative] if _fingerprint(target) != before else [],
                "error": str(error),
                "rollbackErrors": rollback_errors,
                "retainedTransactionPath": root.relative_to(repo_path).as_posix(),
            }
        shutil.rmtree(root, ignore_errors=True)
        _prune_created_transaction_parents(created_parents)
        return {"ok": False, "status": "transaction-rolled-back", "changedPaths": [], "error": str(error)}
    shutil.rmtree(root, ignore_errors=True)
    _prune_created_transaction_parents(created_parents)
    return {
        "ok": True,
        "status": "refreshed-link" if before["kind"] == "symlink" else "linked",
        "changedPaths": [relative],
    }


def _tree_payload_fingerprint(files: dict[str, dict[str, Any]]) -> dict[str, str]:
    records = [
        {
            "path": relative,
            "mode": int(record["mode"]) & 0o777,
            "sha256": hashlib.sha256(record["content"]).hexdigest(),
        }
        for relative, record in sorted(files.items())
    ]
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    return {"kind": "tree", "sha256": hashlib.sha256(encoded).hexdigest()}


def _tree_fingerprint(root: Path) -> dict[str, str]:
    if root.is_symlink():
        return {"kind": "symlink", "sha256": hashlib.sha256(str(root.readlink()).encode()).hexdigest()}
    if not root.exists():
        return {"kind": "absent", "sha256": hashlib.sha256(b"").hexdigest()}
    if not root.is_dir():
        return {"kind": "non_regular", "sha256": hashlib.sha256(b"").hexdigest()}
    files: dict[str, dict[str, Any]] = {}
    try:
        paths = list(root.rglob("*"))
    except OSError:
        return {"kind": "unreadable", "sha256": hashlib.sha256(b"").hexdigest()}
    for path in paths:
        if path.is_symlink() or (not path.is_file() and not path.is_dir()):
            return {"kind": "untrusted", "sha256": hashlib.sha256(b"").hexdigest()}
        if path.is_file():
            try:
                files[path.relative_to(root).as_posix()] = {
                    "content": path.read_bytes(),
                    "mode": stat.S_IMODE(path.stat().st_mode),
                }
            except OSError:
                return {"kind": "unreadable", "sha256": hashlib.sha256(b"").hexdigest()}
    return _tree_payload_fingerprint(files)


def _remove_central_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)


def _missing_transaction_parents(repo: Path, transaction_parent: Path) -> list[Path]:
    candidates = [
        repo / ".planning",
        repo / ".planning" / "devflow",
        plugin_migration_root(repo),
        transaction_parent,
    ]
    return [path for path in candidates if not path.exists() and not path.is_symlink()]


def _prune_created_transaction_parents(created: list[Path]) -> None:
    for parent in reversed(created):
        try:
            parent.rmdir()
        except OSError:
            pass


def _project_target(repo: Path, relative: str) -> Path:
    requested = Path(relative)
    if requested.is_absolute() or not requested.parts or ".." in requested.parts:
        raise ValueError("project path is not a safe relative path")
    target = repo.joinpath(*requested.parts)
    cursor = repo
    for segment in requested.parts[:-1]:
        cursor = cursor / segment
        if cursor.is_symlink():
            raise ValueError("project path has a symlink parent")
        if cursor.exists() and not cursor.is_dir():
            raise ValueError("project path has a non-directory parent")
    try:
        target.parent.resolve().relative_to(repo)
    except (OSError, ValueError) as error:
        raise ValueError("project path escapes repository") from error
    return target


def _inspect_migration_state(
    repo: Path,
    contract: dict[str, Any],
    observed_schema: int | None,
) -> dict[str, Any]:
    relative = ".planning/devflow/plugin-project-migration/state.json"
    try:
        path = _project_target(repo, relative)
    except ValueError:
        return {
            "summary": {
                "path": relative,
                "status": "manual_review_required",
                "reason": "migration_state_untrusted_ancestry",
            },
            "manualActions": [
                {
                    "kind": "project-refresh-state",
                    "path": relative,
                    "reason": "migration_state_untrusted_ancestry",
                }
            ],
            "readSet": [relative],
        }
    fingerprint = _fingerprint(path)
    if fingerprint["kind"] == "absent":
        return {
            "summary": {"path": relative, "status": "missing", "fingerprint": fingerprint},
            "manualActions": [],
            "readSet": [relative],
        }
    if fingerprint["kind"] != "file":
        reason = "migration_state_not_trusted_regular_file"
        return {
            "summary": {
                "path": relative,
                "status": "manual_review_required",
                "reason": reason,
                "fingerprint": fingerprint,
            },
            "manualActions": [{"kind": "project-refresh-state", "path": relative, "reason": reason}],
            "readSet": [relative],
        }
    try:
        document = _read_optional_json(path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        reason = "migration_state_invalid"
        return {
            "summary": {
                "path": relative,
                "status": "manual_review_required",
                "reason": reason,
                "fingerprint": fingerprint,
            },
            "manualActions": [{"kind": "project-refresh-state", "path": relative, "reason": reason}],
            "readSet": [relative],
        }
    assert document is not None
    identity = contract["identity"]
    plugins = document.get("plugins")
    entry = plugins.get(identity["plugin"]) if isinstance(plugins, dict) else None
    entry = entry if isinstance(entry, dict) else {}
    expected = {
        "pluginVersion": identity["pluginVersion"],
        "engineSchemaVersion": identity["engineSchemaVersion"],
        "projectSchemaVersion": observed_schema,
        "refreshContractRevision": identity["refreshContractRevision"],
        "refreshContractDigest": identity["refreshContractDigest"],
        "refreshStatus": "current",
    }
    mismatches = [key for key, value in expected.items() if entry.get(key) != value]
    receipt_relative = entry.get("lastVerifiedReceipt")
    receipt_trusted = False
    read_set = [relative]
    if isinstance(receipt_relative, str) and receipt_relative:
        read_set.append(receipt_relative)
        try:
            receipt_path = _receipt_path(repo, receipt_relative)
            receipt = _read_receipt(receipt_path, APPLY_RECEIPT_KIND)
            receipt_issues = _validate_apply_receipt(repo, receipt_path, receipt)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RuntimeError):
            receipt_issues = ["last_verified_receipt_untrusted"]
        if receipt_issues:
            mismatches.append("lastVerifiedReceipt")
        else:
            receipt_trusted = True
    else:
        mismatches.append("lastVerifiedReceipt")
    status = "current" if document.get("schemaVersion") == "2.0" and not mismatches else "stale"
    return {
        "summary": {
            "path": relative,
            "status": status,
            "schemaVersion": str(document.get("schemaVersion") or "unknown"),
            "fingerprint": fingerprint,
            "mismatchedFields": sorted(set(mismatches)),
            "lastVerifiedReceipt": receipt_relative if isinstance(receipt_relative, str) else None,
            "recordedProjectSchemaVersion": entry.get("projectSchemaVersion"),
            "evidenceTrusted": bool(
                document.get("schemaVersion") == "2.0"
                and isinstance(entry.get("projectSchemaVersion"), int)
                and receipt_trusted
            ),
        },
        "manualActions": [],
        "readSet": read_set,
    }


def _inspect_retained_transactions(
    repo: Path,
    *,
    active_transaction_id: str | None = None,
) -> dict[str, Any]:
    roots = (
        ".planning/devflow/plugin-project-migration/transactions",
        ".planning/devflow/plugin-project-migration/verified-tree-transactions",
    )
    retained: list[str] = []
    read_set: list[str] = list(roots)
    for relative in roots:
        try:
            root = _project_target(repo, relative)
        except ValueError:
            retained.append(relative)
            continue
        if not root.exists() and not root.is_symlink():
            continue
        if root.is_symlink() or not root.is_dir():
            retained.append(relative)
            continue
        try:
            entries = sorted(
                path.relative_to(repo).as_posix()
                for path in root.iterdir()
                if not (
                    relative.endswith("/transactions")
                    and path.name == active_transaction_id
                )
            )
        except OSError:
            retained.append(relative)
            continue
        retained.extend(entries)
        read_set.extend(entries)
    retained = sorted(set(retained))
    if not retained:
        return {
            "summary": {"status": "current", "retainedPaths": []},
            "manualActions": [],
            "readSet": read_set,
        }
    return {
        "summary": {"status": "recovery_required", "retainedPaths": retained},
        "manualActions": [
            {
                "kind": "project-refresh-recovery",
                "path": item,
                "reason": "retained_transaction_requires_recovery",
            }
            for item in retained
        ],
        "readSet": sorted(set(read_set)),
    }


def _read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"state path is not a regular file: {path}")
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"state root is not an object: {path}")
    return payload


def _receipt_path(repo: Path, receipt: str | Path) -> Path:
    root = plugin_migration_root(repo) / "receipts"
    candidate = Path(receipt).expanduser()
    if not candidate.is_absolute():
        candidate = repo / candidate
    candidate = candidate.resolve(strict=False)
    try:
        candidate.relative_to(root.resolve(strict=False))
    except ValueError as error:
        raise ValueError("receipt path is outside the project-refresh receipt root") from error
    guard_devflow_write(repo, candidate)
    return candidate


def _read_receipt(path: Path, expected_kind: str | None = None) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("receipt is not a trusted regular file")
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict) or (
        expected_kind is not None and payload.get("kind") != expected_kind
    ):
        raise ValueError("receipt kind is invalid")
    return payload


def _validate_apply_receipt(
    repo: Path,
    path: Path,
    document: dict[str, Any],
    *,
    expected_kind: str = APPLY_RECEIPT_KIND,
    allowed_statuses: set[str] | None = None,
    action_receipt_reference: str | None = None,
    state_receipt_reference: str | None = None,
) -> list[str]:
    issues: list[str] = []
    if document.get("kind") != expected_kind:
        issues.append("receipt_kind_invalid")
    if document.get("schemaVersion") != RECEIPT_SCHEMA_VERSION:
        issues.append("receipt_schema_invalid")
    if document.get("repo") != str(repo):
        issues.append("receipt_repo_mismatch")
    raw_receipt_path = document.get("receiptPath")
    if not isinstance(raw_receipt_path, str):
        issues.append("receipt_path_missing")
    else:
        recorded = Path(raw_receipt_path).expanduser()
        if not recorded.is_absolute():
            recorded = repo / recorded
        if recorded.resolve(strict=False) != path.resolve(strict=False):
            issues.append("receipt_path_mismatch")
    plan_sha = document.get("planSha256")
    if (
        not isinstance(plan_sha, str)
        or not plan_sha.startswith("sha256:")
        or len(plan_sha) != 71
        or any(character not in "0123456789abcdef" for character in plan_sha[7:])
    ):
        issues.append("receipt_plan_digest_invalid")
    statuses = allowed_statuses or {"applied_and_verified", "applied_incomplete"}
    if document.get("status") not in statuses:
        issues.append("receipt_status_invalid")
    if document.get("valuesRedacted") is not True:
        issues.append("receipt_redaction_marker_missing")
    if document.get("receiptEvidenceSha256") != _receipt_evidence_digest(document):
        issues.append("receipt_evidence_digest_mismatch")
    verification = document.get("verification")
    if not isinstance(verification, dict) or verification.get("ok") is not True:
        issues.append("receipt_verification_invalid")
    rollback_status = document.get("rollbackStatus")
    if rollback_status != "available":
        issues.append("receipt_rollback_status_invalid")
    if expected_kind == APPLY_RECEIPT_KIND:
        completion_status = {
            "applied_and_verified": "current",
            "applied_incomplete": "incomplete",
        }.get(document.get("status"))
        raw_verification_path = document.get("verificationReceiptPath")
    else:
        completion_status = document.get("completionStatus")
        raw_verification_path = document.get("receiptPath")
    if completion_status not in {"current", "incomplete"}:
        issues.append("receipt_completion_status_invalid")
    verification_reference: str | None = None
    if not isinstance(raw_verification_path, str):
        issues.append("receipt_verification_path_missing")
    else:
        try:
            verification_reference = (
                _receipt_path(repo, raw_verification_path).relative_to(repo).as_posix()
            )
        except ValueError:
            issues.append("receipt_verification_path_invalid")
    state_before = document.get("stateBefore")
    state_before_fingerprint = document.get("stateBeforeFingerprint")
    if not _valid_fingerprint(state_before_fingerprint):
        issues.append("receipt_state_before_fingerprint_invalid")
    elif state_before is None and state_before_fingerprint.get("kind") != "absent":
        issues.append("receipt_state_before_binding_mismatch")
    elif isinstance(state_before, dict) and state_before_fingerprint.get("kind") != "file":
        issues.append("receipt_state_before_binding_mismatch")
    elif state_before is not None and not isinstance(state_before, dict):
        issues.append("receipt_state_before_invalid")
    actions = document.get("actions")
    if not isinstance(actions, list):
        return sorted(set([*issues, "receipt_actions_invalid"]))
    authorizations = document.get("authorizations")
    authorization_set = set(map(str, authorizations)) if isinstance(authorizations, list) else set()
    if not isinstance(authorizations, list):
        issues.append("receipt_authorizations_invalid")
    receipt_reference = action_receipt_reference or path.relative_to(repo).as_posix()
    digest_plan = {
        "repo": document.get("repo"),
        "planSha256": document.get("planSha256"),
        "sourceIdentity": document.get("sourceIdentity"),
        "projectSchema": document.get("projectSchema"),
        "migrationPath": document.get("migrationPath", []),
        "preservedPaths": document.get("preservedPaths", []),
    }
    expected_action_set_sha256 = _apply_action_set_digest(
        digest_plan,
        [item for item in actions if isinstance(item, dict)],
        authorization_set,
        document.get("stateBefore"),
        document.get("stateBeforeFingerprint"),
        verification if isinstance(verification, dict) else {},
        str(rollback_status or ""),
        receipt_reference,
        verification_reference or "",
        str(completion_status or ""),
    )
    if document.get("actionSetSha256") != expected_action_set_sha256:
        issues.append("receipt_action_set_digest_mismatch")
    identifiers: set[str] = set()
    paths: list[tuple[str, Path]] = []
    for raw_action in actions:
        if not isinstance(raw_action, dict):
            issues.append("receipt_action_invalid")
            continue
        identifier = str(raw_action.get("id") or "")
        if not identifier or identifier in identifiers:
            issues.append("receipt_action_id_invalid_or_duplicate")
        identifiers.add(identifier)
        kind = str(raw_action.get("kind") or "")
        relative = str(raw_action.get("path") or "")
        try:
            _project_target(repo, relative)
            relative_path = Path(relative)
            paths.append((identifier, relative_path))
        except ValueError:
            issues.append(f"receipt_action_path_invalid:{identifier}")
            continue
        ownership = str(raw_action.get("ownership") or "")
        authorization = str(raw_action.get("authorization") or "")
        rollback = raw_action.get("rollback")
        rollback = rollback if isinstance(rollback, dict) else {}
        before = raw_action.get("beforeFingerprint")
        after = raw_action.get("afterFingerprint")
        if not _valid_fingerprint(before) or not _valid_fingerprint(after):
            issues.append(f"receipt_action_fingerprint_invalid:{identifier}")
        if authorization not in authorization_set:
            issues.append(f"receipt_action_authorization_unbound:{identifier}")
        expected_path = False
        if ownership == "devflow-workflow-config":
            expected_path = relative == ".dev-flow.json"
            if authorization != WORKFLOW_CONFIG_AUTHORIZATION:
                issues.append(f"receipt_action_authorization_invalid:{identifier}")
        elif ownership == "devflow-create-if-absent":
            expected_path = relative in CONTROL_PLANE_TEMPLATES
            if authorization != PROJECT_REFRESH_AUTHORIZATION:
                issues.append(f"receipt_action_authorization_invalid:{identifier}")
        elif ownership == "human-merge-candidate":
            expected_path = relative == "AGENTS.md.generated"
            if authorization != PROJECT_REFRESH_AUTHORIZATION:
                issues.append(f"receipt_action_authorization_invalid:{identifier}")
        elif ownership == "devflow-managed-project-skill":
            expected_path = (
                len(relative_path.parts) == 3
                and relative_path.parts[:2] == (".agents", "skills")
            )
            if authorization != PROJECT_REFRESH_AUTHORIZATION:
                issues.append(f"receipt_action_authorization_invalid:{identifier}")
        if not expected_path:
            issues.append(f"receipt_action_path_invalid:{identifier}")
        expected_rollback = {
            "create_file": "remove_if_created",
            "create_symlink": "remove_if_created",
            "replace_json": "git_blob",
            "replace_symlink": "restore_symlink",
        }.get(kind)
        if expected_rollback is None or rollback.get("kind") != expected_rollback:
            issues.append(f"receipt_action_rollback_invalid:{identifier}")
        if kind in {"create_file", "create_symlink"} and (
            not isinstance(before, dict) or before.get("kind") != "absent"
        ):
            issues.append(f"receipt_action_preimage_invalid:{identifier}")
        if kind == "replace_json" and (
            ownership != "devflow-workflow-config"
            or not isinstance(before, dict)
            or before.get("kind") != "file"
            or not isinstance(after, dict)
            or after.get("kind") != "file"
        ):
            issues.append(f"receipt_action_operation_invalid:{identifier}")
        if kind in {"create_symlink", "replace_symlink"} and (
            ownership != "devflow-managed-project-skill"
            or not isinstance(after, dict)
            or after.get("kind") != "symlink"
        ):
            issues.append(f"receipt_action_operation_invalid:{identifier}")
        if kind == "create_file" and (
            not isinstance(after, dict) or after.get("kind") != "file"
        ):
            issues.append(f"receipt_action_operation_invalid:{identifier}")
        dependencies = raw_action.get("dependencies")
        if not isinstance(dependencies, list):
            issues.append(f"receipt_action_dependencies_invalid:{identifier}")
    for raw_action in actions:
        if not isinstance(raw_action, dict):
            continue
        identifier = str(raw_action.get("id") or "")
        dependencies = raw_action.get("dependencies")
        if isinstance(dependencies, list):
            for dependency in set(map(str, dependencies)) - identifiers:
                issues.append(f"receipt_action_dependency_missing:{identifier}:{dependency}")
    for index, (first_id, first) in enumerate(paths):
        for second_id, second in paths[index + 1 :]:
            if first == second or first in second.parents or second in first.parents:
                issues.append(f"receipt_action_path_overlap:{first_id}:{second_id}")
    changed_paths = document.get("changedPaths")
    expected_changed = sorted(
        str(action.get("path")) for action in actions if isinstance(action, dict)
    )
    if not isinstance(changed_paths, list) or sorted(map(str, changed_paths)) != expected_changed:
        issues.append("receipt_changed_paths_mismatch")
    state_path = plugin_migration_root(repo) / "state.json"
    state_after = document.get("stateAfterFingerprint")
    if not _valid_fingerprint(state_after):
        issues.append("receipt_state_fingerprint_invalid")
    elif _fingerprint(state_path) != state_after:
        issues.append("receipt_state_fingerprint_mismatch")
    try:
        state = _read_optional_json(state_path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        state = None
    source_identity = document.get("sourceIdentity")
    plugin_name = source_identity.get("plugin") if isinstance(source_identity, dict) else None
    plugins = state.get("plugins") if isinstance(state, dict) else None
    state_entry = plugins.get(plugin_name) if isinstance(plugins, dict) and isinstance(plugin_name, str) else None
    if not isinstance(state_entry, dict):
        issues.append("receipt_state_binding_missing")
    else:
        expected_state_reference = state_receipt_reference or receipt_reference
        if state_entry.get("lastVerifiedReceipt") != expected_state_reference:
            issues.append("receipt_state_path_binding_mismatch")
        if state_entry.get("lastApplyActionSetSha256") != expected_action_set_sha256:
            issues.append("receipt_state_action_binding_mismatch")
    return sorted(set(issues))


def _validate_verification_receipt(
    repo: Path,
    path: Path,
    document: dict[str, Any],
) -> list[str]:
    issues: list[str] = []
    raw_apply_path = document.get("applyReceiptPath")
    apply_reference: str | None = None
    if not isinstance(raw_apply_path, str):
        issues.append("receipt_apply_path_missing")
    else:
        try:
            apply_reference = _receipt_path(repo, raw_apply_path).relative_to(repo).as_posix()
        except ValueError:
            issues.append("receipt_apply_path_invalid")
    issues.extend(
        _validate_apply_receipt(
            repo,
            path,
            document,
            expected_kind=VERIFICATION_RECEIPT_KIND,
            allowed_statuses={"verified"},
            action_receipt_reference=apply_reference,
            state_receipt_reference=apply_reference,
        )
    )
    if document.get("completionStatus") not in {"current", "incomplete"}:
        issues.append("receipt_completion_status_invalid")
    verification = document.get("verification")
    if not isinstance(verification, dict) or verification.get("ok") is not True:
        issues.append("receipt_verification_invalid")
    if document.get("rollbackStatus") != "available":
        issues.append("receipt_rollback_status_invalid")
    return sorted(set(issues))


def _valid_fingerprint(value: Any) -> bool:
    return bool(
        isinstance(value, dict)
        and value.get("kind") in {"absent", "file", "symlink", "non_regular", "unreadable"}
        and isinstance(value.get("sha256"), str)
        and len(value["sha256"]) == 64
        and all(character in "0123456789abcdef" for character in value["sha256"])
    )


def _json_text(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_adopted(repo: Path) -> bool:
    markers = (".dev-flow.json", ".planning/devflow/STATE.md", "openspec/config.yaml")
    for relative in markers:
        try:
            path = _project_target(repo, relative)
        except ValueError:
            continue
        if path.exists() and not path.is_symlink() and path.is_file():
            return True
    return False


def _inspect_managed_skills(
    repo: Path,
    plugin_root: Path,
    contract: dict[str, Any],
) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    manual: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    read_set: list[str] = []
    plugin_name = str(contract["identity"]["plugin"])
    for skill in contract["projectLocalSkills"]:
        relative = (Path(".agents") / "skills" / skill).as_posix()
        read_set.append(relative)
        try:
            target = _project_target(repo, relative)
        except ValueError:
            reason = "target_has_untrusted_ancestry"
            items.append({"skill": skill, "path": relative, "status": "manual_only", "reason": reason})
            manual.append({"kind": "project-local-skill", "path": relative, "reason": reason})
            continue
        sources = _project_skill_sources(repo, plugin_root, plugin_name, skill)
        source = sources[0]
        if not _trusted_skill_source(source):
            reason = "missing_or_untrusted_source"
            items.append({"skill": skill, "path": relative, "status": "manual_only", "reason": reason})
            manual.append({"kind": "project-local-skill", "path": relative, "reason": reason})
            continue
        before = _fingerprint(target)
        if target.is_symlink():
            try:
                current = target.resolve() in {item.resolve() for item in sources}
            except OSError:
                current = False
            if current:
                items.append({"skill": skill, "path": relative, "status": "current"})
                continue
            action = _symlink_action(
                repo,
                identifier=f"refresh-project-skill:{skill}",
                kind="replace_symlink",
                relative=relative,
                source=source,
                before=before,
                rollback={"kind": "restore_symlink", "target": str(target.readlink())},
            )
            actions.append(action)
            items.append({"skill": skill, "path": relative, "status": "stale_link"})
            continue
        if target.exists():
            reason = "target_exists_not_symlink"
            items.append({"skill": skill, "path": relative, "status": "manual_only", "reason": reason})
            manual.append({"kind": "project-local-skill", "path": relative, "reason": reason})
            continue
        actions.append(
            _symlink_action(
                repo,
                identifier=f"install-project-skill:{skill}",
                kind="create_symlink",
                relative=relative,
                source=source,
                before=before,
                rollback={"kind": "remove_if_created"},
            )
        )
        items.append({"skill": skill, "path": relative, "status": "missing"})
    if manual:
        status = "manual_review_required"
    elif actions:
        status = "migration_pending"
    else:
        status = "current"
    return {
        "actions": actions,
        "manualActions": manual,
        "readSet": read_set,
        "summary": {"status": status, "items": items},
    }


def _inspect_managed_control_plane(
    repo: Path,
    plugin_root: Path,
    contract: dict[str, Any],
) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    manual: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    read_set: list[str] = []
    for relative in contract["managedFiles"]:
        read_set.append(relative)
        target = repo / relative
        template = CONTROL_PLANE_TEMPLATES[relative]
        source_relative = (Path("assets") / "templates" / template).as_posix()
        source = _source_path(plugin_root, source_relative)
        if target.is_symlink() or (target.exists() and not target.is_file()):
            reason = "managed_file_ownership_ambiguous"
            items.append({"path": relative, "status": "manual_only", "reason": reason})
            manual.append({"kind": "control-plane-file", "path": relative, "reason": reason})
            continue
        if target.exists():
            items.append({"path": relative, "status": "current"})
            continue
        if source is None or source.is_symlink() or not source.is_file():
            reason = "missing_or_untrusted_template"
            items.append({"path": relative, "status": "manual_only", "reason": reason})
            manual.append({"kind": "control-plane-file", "path": relative, "reason": reason})
            continue
        content = source.read_bytes()
        actions.append(
            _file_create_action(
                repo,
                identifier=f"create-control-plane:{relative}",
                relative=relative,
                content=content,
                source={"kind": "plugin_file", "path": source_relative},
                ownership="devflow-create-if-absent",
            )
        )
        items.append({"path": relative, "status": "missing"})
    if manual:
        status = "manual_review_required"
    elif actions:
        status = "migration_pending"
    else:
        status = "current" if read_set else "not_applicable"
    return {
        "actions": actions,
        "manualActions": manual,
        "readSet": read_set,
        "summary": {"status": status, "items": items},
    }


def _inspect_agents_guidance(
    repo: Path,
    plugin_root: Path,
    contract: dict[str, Any],
) -> dict[str, Any]:
    guidance = contract.get("agentsGuidance")
    if not isinstance(guidance, dict):
        return {
            "actions": [],
            "manualActions": [],
            "readSet": [],
            "summary": {"status": "not_applicable", "missingMarkers": []},
        }
    active_relative = str(guidance["activePath"])
    candidate_relative = str(guidance["candidatePath"])
    active = repo / active_relative
    candidate = repo / candidate_relative
    if active.is_symlink() or (active.exists() and not active.is_file()):
        reason = "active_agents_ownership_ambiguous"
        return {
            "actions": [],
            "manualActions": [{"kind": "agents-guidance", "path": active_relative, "reason": reason}],
            "readSet": [active_relative, candidate_relative],
            "summary": {"status": "manual_review_required", "missingMarkers": []},
        }
    try:
        active_text = active.read_text() if active.exists() else ""
    except (OSError, UnicodeError):
        reason = "active_agents_unreadable"
        return {
            "actions": [],
            "manualActions": [{"kind": "agents-guidance", "path": active_relative, "reason": reason}],
            "readSet": [active_relative, candidate_relative],
            "summary": {"status": "manual_review_required", "missingMarkers": []},
        }
    missing = missing_agents_guidance(active_text)
    if not missing:
        return {
            "actions": [],
            "manualActions": [],
            "readSet": [active_relative, candidate_relative],
            "summary": {"status": "unchanged", "missingMarkers": []},
        }
    source_relative = str(guidance["template"])
    source = _source_path(plugin_root, source_relative)
    if source is None or source.is_symlink() or not source.is_file():
        reason = "missing_or_untrusted_agents_template"
        return {
            "actions": [],
            "manualActions": [{"kind": "agents-guidance", "path": active_relative, "reason": reason}],
            "readSet": [active_relative, candidate_relative],
            "summary": {"status": "manual_review_required", "missingMarkers": missing},
        }
    candidate_content = source.read_text().replace("{{project_mode}}", _project_mode(repo)).encode()
    manual = [
        {
            "kind": "agents-guidance-merge",
            "path": active_relative,
            "candidatePath": candidate_relative,
            "reason": "agents_merge_required",
        }
    ]
    actions: list[dict[str, Any]] = []
    status = "agents_merge_required"
    if candidate.is_symlink() or (candidate.exists() and not candidate.is_file()):
        status = "candidate_conflict"
        manual.append(
            {"kind": "agents-guidance", "path": candidate_relative, "reason": "candidate_ownership_ambiguous"}
        )
    elif candidate.exists():
        if _fingerprint(candidate) != _bytes_fingerprint(candidate_content):
            status = "candidate_conflict"
            manual.append(
                {"kind": "agents-guidance", "path": candidate_relative, "reason": "candidate_content_conflict"}
            )
    else:
        actions.append(
            _file_create_action(
                repo,
                identifier="create-agents-merge-candidate",
                relative=candidate_relative,
                content=candidate_content,
                source={
                    "kind": "rendered_plugin_template",
                    "path": source_relative,
                    "values": {"project_mode": _project_mode(repo)},
                },
                ownership="human-merge-candidate",
            )
        )
    return {
        "actions": actions,
        "manualActions": manual,
        "readSet": [active_relative, candidate_relative],
        "summary": {"status": status, "missingMarkers": missing},
    }


def _inspect_legacy_skill_layout(repo: Path, contract: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, str]] = []
    try:
        root = _project_target(repo, ".codex/skills")
    except ValueError:
        root = None
        items.append(
            {
                "kind": "legacy-project-skill",
                "path": ".codex/skills",
                "reason": "legacy_root_untrusted_ancestry",
            }
        )
    if root is not None and root.exists() and not root.is_symlink() and root.is_dir():
        for skill_file in sorted(root.glob("*/SKILL.md")):
            skill = skill_file.parent.name
            reason = (
                "legacy_managed_skill_preserved"
                if skill in contract["projectLocalSkills"]
                else "custom_legacy_skill_preserved"
            )
            items.append(
                {
                    "kind": "legacy-project-skill",
                    "path": skill_file.parent.relative_to(repo).as_posix(),
                    "reason": reason,
                }
            )
    elif root is not None and (root.exists() or root.is_symlink()):
        items.append({"kind": "legacy-project-skill", "path": ".codex/skills", "reason": "legacy_root_ambiguous"})
    inspection = inspect_legacy_workflow_config(repo)
    known = {(item["path"], item["reason"]) for item in items}
    for artifact in inspection.get("artifacts", []):
        if not isinstance(artifact, dict) or not artifact.get("path"):
            continue
        item = {
            "kind": str(artifact.get("kind") or "legacy-project-artifact"),
            "path": str(artifact["path"]),
            "reason": str(artifact.get("reason") or "legacy_content_preserved"),
        }
        if (item["path"], item["reason"]) not in known:
            items.append(item)
            known.add((item["path"], item["reason"]))
    for conflict in inspection.get("conflicts", []):
        if not isinstance(conflict, dict) or not conflict.get("path"):
            continue
        item = {
            "kind": "legacy-project-conflict",
            "path": str(conflict["path"]),
            "reason": str(conflict.get("reason") or "legacy_content_conflict"),
        }
        if (item["path"], item["reason"]) not in known:
            items.append(item)
            known.add((item["path"], item["reason"]))
    items.sort(key=lambda item: (item["path"], item["reason"]))
    read_set = sorted({".codex/skills", *(item["path"] for item in items)})
    return {
        "actions": [],
        "manualActions": items,
        "readSet": read_set,
        "summary": {
            "status": "manual_review_required" if items else "current",
            "items": items,
            "inspectorStatus": inspection.get("status"),
            "valuesRedacted": True,
        },
    }


def _file_create_action(
    repo: Path,
    *,
    identifier: str,
    relative: str,
    content: bytes,
    source: dict[str, Any],
    ownership: str,
) -> dict[str, Any]:
    return {
        "id": identifier,
        "kind": "create_file",
        "path": relative,
        "beforeFingerprint": _fingerprint(repo / relative),
        "afterFingerprint": _bytes_fingerprint(content),
        "authorization": PROJECT_REFRESH_AUTHORIZATION,
        "dependencies": [],
        "ownership": ownership,
        "source": source,
        "rollback": {"kind": "remove_if_created", "pruneEmptyParents": _missing_parent_paths(repo, relative)},
        "verification": ["managed-path-readback"],
    }


def _symlink_action(
    repo: Path,
    *,
    identifier: str,
    kind: str,
    relative: str,
    source: Path,
    before: dict[str, str],
    rollback: dict[str, Any],
) -> dict[str, Any]:
    rollback = dict(rollback)
    rollback["pruneEmptyParents"] = _missing_parent_paths(repo, relative)
    return {
        "id": identifier,
        "kind": kind,
        "path": relative,
        "beforeFingerprint": before,
        "afterFingerprint": _symlink_fingerprint(str(source)),
        "authorization": PROJECT_REFRESH_AUTHORIZATION,
        "dependencies": [],
        "ownership": "devflow-managed-project-skill",
        "source": {"kind": "symlink", "target": str(source)},
        "rollback": rollback,
        "verification": ["managed-path-readback", "trusted-skill-source"],
    }


def _project_skill_sources(repo: Path, plugin_root: Path, plugin_name: str, skill: str) -> list[Path]:
    release_root = (repo / "plugins" / plugin_name).resolve()
    packaged = plugin_root / "skills" / skill
    if plugin_root.resolve() != release_root:
        return [packaged]
    development = repo / "dev" / "plugins" / plugin_name / "skills" / skill
    if _trusted_skill_source(development):
        return [development, packaged]
    return [packaged]


def _trusted_skill_source(source: Path) -> bool:
    if not source.is_absolute():
        return False
    try:
        if source.resolve(strict=True) != source:
            return False
        skill_file = source / "SKILL.md"
        if skill_file.resolve(strict=True) != skill_file:
            return False
    except OSError:
        return False
    return source.is_dir() and skill_file.is_file()


def _missing_parent_paths(repo: Path, relative: str) -> list[str]:
    target = repo / relative
    missing: list[str] = []
    cursor = target.parent
    while cursor != repo and cursor.is_relative_to(repo):
        if not cursor.exists() and not cursor.is_symlink():
            missing.append(cursor.relative_to(repo).as_posix())
        cursor = cursor.parent
    return sorted(missing, key=lambda item: len(Path(item).parts), reverse=True)


def _project_mode(repo: Path) -> str:
    return "brownfield" if any((repo / name).exists() for name in ("src", "app", "lib", "openspec")) else "greenfield"


def _load_refresh_contract(plugin_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    adapter_path = plugin_root / ".codex-plugin" / "project-migration.json"
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    try:
        adapter = json.loads(adapter_path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError):
        adapter = {}
        errors.append("contract_manifest_unreadable")
    try:
        plugin_manifest = json.loads(manifest_path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError):
        plugin_manifest = {}
        errors.append("plugin_manifest_unreadable")

    schema_version = str(adapter.get("schemaVersion") or "unknown")
    engine_schema = str(adapter.get("engineSchemaVersion") or "unknown")
    project_schema = adapter.get("projectSchema")
    refresh_contract = adapter.get("refreshContract")
    if schema_version != "2.0":
        errors.append("unsupported_contract_schema")
    if engine_schema != "2.0":
        errors.append("unsupported_engine_schema")
    if not isinstance(project_schema, dict):
        project_schema = {}
        errors.append("project_schema_missing")
    if not isinstance(refresh_contract, dict):
        refresh_contract = {}
        errors.append("refresh_contract_missing")

    head = project_schema.get("head")
    minimum = project_schema.get("minimumSupported")
    if not isinstance(head, int) or not isinstance(minimum, int) or minimum < 0 or head < minimum:
        errors.append("project_schema_range_invalid")
        head = head if isinstance(head, int) else 0
        minimum = minimum if isinstance(minimum, int) else 0

    steps = adapter.get("migrationSteps")
    steps = steps if isinstance(steps, list) else []
    graph_errors = _validate_migration_graph(steps, minimum, head)
    errors.extend(graph_errors)

    config_targets = adapter.get("configTargets")
    config_targets = config_targets if isinstance(config_targets, dict) else {}
    normalized_config_targets: dict[int, dict[str, Any]] = {}
    for raw_version, raw_relative in config_targets.items():
        if not isinstance(raw_version, str) or not raw_version.isdigit():
            errors.append("config_target_version_invalid")
            continue
        version = int(raw_version)
        if not isinstance(raw_relative, str):
            errors.append(f"config_target_path_invalid:{raw_version}")
            continue
        source = _source_path(plugin_root, raw_relative)
        if source is None or source.is_symlink() or not source.is_file():
            errors.append(f"config_target_untrusted:{raw_version}")
            continue
        try:
            target_bytes = source.read_bytes()
            target_payload = json.loads(target_bytes)
        except (OSError, UnicodeError, json.JSONDecodeError):
            errors.append(f"config_target_invalid:{raw_version}")
            continue
        if not isinstance(target_payload, dict):
            errors.append(f"config_target_invalid:{raw_version}")
            continue
        normalized_config_targets[version] = {
            "path": raw_relative,
            "bytes": target_bytes,
            "payload": target_payload,
        }
    target_relative = config_targets.get(str(head))
    if not isinstance(target_relative, str):
        errors.append("current_config_target_missing")
    elif not _trusted_source_file(plugin_root, target_relative):
        errors.append("current_config_target_untrusted")
    elif head not in normalized_config_targets:
        errors.append("current_config_target_invalid")

    project_skills = adapter.get("projectLocalSkills")
    if not isinstance(project_skills, list):
        project_skills = []
        errors.append("project_local_skills_invalid")
    normalized_skills: list[str] = []
    for skill in project_skills:
        if (
            not isinstance(skill, str)
            or not skill
            or Path(skill).name != skill
            or skill in normalized_skills
        ):
            errors.append("project_local_skill_invalid_or_duplicate")
            continue
        normalized_skills.append(skill)

    managed_files = adapter.get("managedFiles")
    if not isinstance(managed_files, list):
        managed_files = []
        errors.append("managed_files_invalid")
    normalized_managed: list[str] = []
    for relative in managed_files:
        if (
            not isinstance(relative, str)
            or relative not in CONTROL_PLANE_TEMPLATES
            or relative in normalized_managed
        ):
            errors.append("managed_file_invalid_or_duplicate")
            continue
        normalized_managed.append(relative)

    agents_guidance = adapter.get("agentsGuidance")
    if agents_guidance is not None:
        expected_guidance = {
            "activePath": "AGENTS.md",
            "candidatePath": "AGENTS.md.generated",
            "template": "assets/templates/AGENTS.md.template",
        }
        if not isinstance(agents_guidance, dict) or agents_guidance != expected_guidance:
            errors.append("agents_guidance_contract_invalid")
            agents_guidance = None
        elif not _trusted_source_file(plugin_root, expected_guidance["template"]):
            errors.append("agents_guidance_template_untrusted")

    tracked_inputs = refresh_contract.get("trackedInputs")
    tracked_inputs = tracked_inputs if isinstance(tracked_inputs, list) else []
    source_read_set: list[str] = []
    input_digests: list[dict[str, str]] = []
    seen_inputs: set[str] = set()
    for raw_relative in tracked_inputs:
        if not isinstance(raw_relative, str) or raw_relative in seen_inputs:
            errors.append("refresh_input_invalid_or_duplicate")
            continue
        seen_inputs.add(raw_relative)
        source_read_set.append(raw_relative)
        payload = _refresh_input_bytes(plugin_root, raw_relative)
        if payload is None:
            errors.append(f"refresh_input_untrusted:{raw_relative}")
            continue
        digest = hashlib.sha256(payload).hexdigest()
        input_digests.append({"path": raw_relative, "sha256": digest})

    tracked_inputs_sha256 = hashlib.sha256(
        json.dumps(
            sorted(input_digests, key=lambda item: item["path"]),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()

    digest_payload = {
        "manifest": adapter,
        "inputs": sorted(input_digests, key=lambda item: item["path"]),
    }
    digest = "sha256:" + hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    revision = refresh_contract.get("revision")
    if not isinstance(revision, int) or revision < 1:
        errors.append("refresh_contract_revision_invalid")
        revision = 0
    identity = {
        "plugin": str(adapter.get("plugin") or plugin_manifest.get("name") or plugin_root.name),
        "pluginVersion": str(plugin_manifest.get("version") or "unknown"),
        "contractSchemaVersion": schema_version,
        "engineSchemaVersion": engine_schema,
        "projectSchemaHead": head,
        "minimumSupportedProjectSchema": minimum,
        "refreshContractRevision": revision,
        "refreshContractDigest": digest,
    }
    return {
        "adapter": adapter,
        "identity": identity,
        "errors": sorted(set(errors)),
        "projectSchemaHead": head,
        "minimumSupported": minimum,
        "steps": steps,
        "configTargets": normalized_config_targets,
        "sourceReadSet": sorted(source_read_set),
        "inputDigests": sorted(input_digests, key=lambda item: item["path"]),
        "trackedInputsSha256": tracked_inputs_sha256,
        "projectLocalSkills": normalized_skills,
        "managedFiles": normalized_managed,
        "agentsGuidance": agents_guidance,
    }


def project_refresh_contract_snapshot(plugin_root: str | Path) -> dict[str, Any]:
    root = Path(plugin_root).expanduser().resolve()
    contract = _load_refresh_contract(root)
    return {
        "ok": not contract["errors"],
        "pluginRoot": str(root),
        "identity": contract["identity"],
        "errors": list(contract["errors"]),
        "sourceReadSet": list(contract["sourceReadSet"]),
        "inputDigests": list(contract["inputDigests"]),
        "trackedInputsSha256": contract["trackedInputsSha256"],
    }


def _validate_migration_graph(steps: list[Any], minimum: int, head: int) -> list[str]:
    errors: list[str] = []
    identifiers: set[str] = set()
    outgoing: dict[int, dict[str, Any]] = {}
    incoming: set[int] = set()
    for raw_step in steps:
        if not isinstance(raw_step, dict):
            errors.append("migration_step_invalid")
            continue
        identifier = raw_step.get("id")
        source = raw_step.get("from")
        target = raw_step.get("to")
        if not isinstance(identifier, str) or not identifier or identifier in identifiers:
            errors.append("migration_step_duplicate_or_missing_id")
        else:
            identifiers.add(identifier)
            registered = MIGRATION_STEP_REGISTRY.get(identifier)
            if registered is None:
                errors.append(f"migration_step_registry_unknown:{identifier}")
            elif any(
                raw_step.get(key) != registered[key]
                for key in ("from", "to", "authorization", "configTarget")
            ):
                errors.append(f"migration_step_registry_mismatch:{identifier}")
        if not isinstance(source, int) or not isinstance(target, int):
            errors.append("migration_step_version_invalid")
            continue
        if source in outgoing:
            errors.append("migration_graph_fork")
        else:
            outgoing[source] = raw_step
        if target in incoming:
            errors.append("migration_graph_merge")
        incoming.add(target)
        if source < minimum or target > head:
            errors.append("migration_step_out_of_range")
        if target <= source:
            errors.append("migration_graph_cycle")

    cursor = minimum
    visited: set[int] = set()
    used_ids: set[str] = set()
    while cursor < head:
        if cursor in visited:
            errors.append("migration_graph_cycle")
            break
        visited.add(cursor)
        step = outgoing.get(cursor)
        if step is None:
            errors.append("migration_graph_gap")
            break
        used_ids.add(str(step.get("id")))
        cursor = int(step["to"])
    if cursor != head:
        errors.append("migration_graph_no_route_to_head")
    if identifiers - used_ids:
        errors.append("migration_graph_unreachable_step")
    return sorted(set(errors))


def _resolve_migration_path(
    observed: int | None,
    contract: dict[str, Any],
) -> tuple[list[str], str | None]:
    if observed is None:
        return [], "baseline_ambiguous"
    minimum = int(contract["minimumSupported"])
    head = int(contract["projectSchemaHead"])
    if observed < minimum or observed > head:
        return [], "baseline_unsupported"
    outgoing = {
        int(step["from"]): step
        for step in contract["steps"]
        if isinstance(step, dict) and isinstance(step.get("from"), int)
    }
    path: list[str] = []
    cursor = observed
    visited: set[int] = set()
    while cursor < head:
        if cursor in visited or cursor not in outgoing:
            return [], "migration_path_unavailable"
        visited.add(cursor)
        step = outgoing[cursor]
        path.append(str(step["id"]))
        cursor = int(step["to"])
    return path, None


def _source_path(plugin_root: Path, relative: str) -> Path | None:
    requested = Path(relative)
    if requested.is_absolute() or not requested.parts or ".." in requested.parts:
        return None
    candidate = plugin_root.joinpath(*requested.parts)
    try:
        resolved = candidate.resolve(strict=False)
        resolved.relative_to(plugin_root)
    except (OSError, ValueError):
        return None
    if candidate.exists() or candidate.is_symlink():
        try:
            if candidate.resolve(strict=True) != candidate:
                return None
        except OSError:
            return None
    return candidate


def _refresh_input_bytes(plugin_root: Path, relative: str) -> bytes | None:
    requested = Path(relative)
    if requested.is_absolute() or not requested.parts or ".." in requested.parts:
        return None
    archive = plugin_root / "scripts" / "devflow_runtime.pyz"
    if requested.parts[0] == "scripts" and requested.suffix == ".py" and archive.is_file():
        try:
            with zipfile.ZipFile(archive) as package:
                return package.read(requested.name)
        except (OSError, KeyError, zipfile.BadZipFile):
            return None
    source = _source_path(plugin_root, relative)
    if source is None or source.is_symlink() or not source.is_file():
        return None
    try:
        return source.read_bytes()
    except OSError:
        return None


def _trusted_source_file(plugin_root: Path, relative: str) -> bool:
    source = _source_path(plugin_root, relative)
    return bool(source is not None and not source.is_symlink() and source.is_file())


def _contains_config_target(actual: Any, target: Any) -> bool:
    if isinstance(target, dict):
        return isinstance(actual, dict) and all(
            key in actual and _contains_config_target(actual[key], value)
            for key, value in target.items()
        )
    if isinstance(target, list):
        return (
            isinstance(actual, list)
            and len(actual) == len(target)
            and all(
                _contains_config_target(actual_item, target_item)
                for actual_item, target_item in zip(actual, target)
            )
        )
    return actual == target


def _merge_config_target(actual: Any, target: Any) -> Any:
    if not isinstance(target, dict):
        return json.loads(json.dumps(target))
    merged = json.loads(json.dumps(actual)) if isinstance(actual, dict) else {}
    for key, value in target.items():
        merged[key] = _merge_config_target(merged.get(key), value)
    return merged


def _apply_config_migration_steps(
    payload: dict[str, Any],
    step_ids: list[str],
    contract: dict[str, Any],
) -> dict[str, Any]:
    migrated = json.loads(json.dumps(payload))
    for step_id in step_ids:
        registry = MIGRATION_STEP_REGISTRY.get(step_id)
        if registry is None:
            raise ValueError(f"unknown migration step: {step_id}")
        planner = registry.get("planner")
        if planner == "legacy-selection-v0-to-v1":
            migrated = _migrate_legacy_config(migrated)
        elif planner == "merge-config-target":
            target_version = int(registry["configTarget"])
            target = contract["configTargets"].get(target_version)
            if not isinstance(target, dict) or not isinstance(target.get("payload"), dict):
                raise ValueError(f"migration target unavailable: {step_id}")
            migrated = _merge_config_target(migrated, target["payload"])
        else:
            raise ValueError(f"unknown migration planner: {step_id}")
    return migrated


def _plan_config_migration_action(
    repo: Path,
    path: Path,
    payload: dict[str, Any],
    report: dict[str, Any],
    contract: dict[str, Any],
    observed_schema: int,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    migration_path, path_error = _resolve_migration_path(observed_schema, contract)
    if path_error or not migration_path:
        report["status"] = "manual_only"
        return None, _manual_config_action(path, path_error or "migration_step_unavailable")
    preimage = _trusted_git_preimage(repo, path)
    if preimage is None:
        report["status"] = "manual_only"
        return None, _manual_config_action(path, "recoverable_preimage_unavailable")
    try:
        transformed = _apply_config_migration_steps(payload, migration_path, contract)
    except (KeyError, TypeError, ValueError):
        report["status"] = "manual_only"
        return None, _manual_config_action(path, "migration_step_unavailable")
    steps_by_id = {
        str(step.get("id")): step
        for step in contract["steps"]
        if isinstance(step, dict) and step.get("id")
    }
    authorizations = {
        str(steps_by_id[step_id].get("authorization") or "")
        for step_id in migration_path
        if step_id in steps_by_id
    }
    if len(authorizations) != 1 or "" in authorizations:
        report["status"] = "manual_only"
        return None, _manual_config_action(path, "migration_authorization_ambiguous")
    verifiers = sorted(
        {
            str(MIGRATION_STEP_REGISTRY[step_id]["verifier"])
            for step_id in migration_path
        }
    )
    action_id = (
        migration_path[0]
        if len(migration_path) == 1
        else f"workflow-config-migration-v{observed_schema}-to-v{contract['projectSchemaHead']}"
    )
    action = {
        "id": action_id,
        "kind": "replace_json",
        "path": ".dev-flow.json",
        "beforeFingerprint": report["fingerprint"],
        "afterFingerprint": _bytes_fingerprint(_json_text(transformed).encode()),
        "authorization": next(iter(authorizations)),
        "dependencies": [],
        "ownership": "devflow-workflow-config",
        "source": {"kind": "pure_migration_path", "steps": migration_path},
        "rollback": {"kind": "git_blob", **preimage},
        "verification": verifiers,
    }
    return action, None


def _inspect_config(
    repo: Path,
    contract: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
    path = repo / ".dev-flow.json"
    if path.is_symlink() or not path.is_file():
        status_name = "manual_only" if path.exists() or path.is_symlink() else "missing"
        report = {
            "path": ".dev-flow.json",
            "status": status_name,
            "valuesRedacted": True,
            "fingerprint": _fingerprint(path),
        }
        if status_name == "missing":
            report["status"] = "migration_pending"
            report["observedSchema"] = 0
            target = contract["configTargets"][contract["projectSchemaHead"]]["bytes"]
            action = {
                "id": "create-current-workflow-config",
                "kind": "create_file",
                "path": ".dev-flow.json",
                "beforeFingerprint": report["fingerprint"],
                "afterFingerprint": _bytes_fingerprint(target),
                "authorization": WORKFLOW_CONFIG_AUTHORIZATION,
                "dependencies": [],
                "ownership": "devflow-workflow-config",
                "source": {"kind": "current_config_target"},
                "rollback": {
                    "kind": "remove_if_created",
                    "pruneEmptyParents": _missing_parent_paths(repo, ".dev-flow.json"),
                },
                "verification": ["configuration-schema"],
            }
            return report, action, None
        return report, None, _manual_config_action(path, "config_not_regular_file")
    try:
        mode = path.stat().st_mode
    except OSError:
        mode = 0
    if not mode & (stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH):
        report = {
            "path": ".dev-flow.json",
            "status": "manual_only",
            "valuesRedacted": True,
            "fingerprint": _fingerprint(path),
        }
        return report, None, _manual_config_action(path, "config_unreadable")
    try:
        payload = json.loads(path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError):
        return ({
            "path": ".dev-flow.json",
            "status": "baseline_ambiguous",
            "valuesRedacted": True,
            "fingerprint": _fingerprint(path),
        }, None, None)
    if not isinstance(payload, dict):
        return ({
            "path": ".dev-flow.json",
            "status": "baseline_ambiguous",
            "valuesRedacted": True,
            "fingerprint": _fingerprint(path),
        }, None, None)
    explicit_schema: int | None = None
    if "projectContract" in payload:
        marker = payload.get("projectContract")
        known_schemas = set(contract["configTargets"])
        if not isinstance(marker, int) or isinstance(marker, bool) or marker not in known_schemas:
            return ({
                "path": ".dev-flow.json",
                "status": "baseline_unsupported",
                "observedSchema": marker if isinstance(marker, int) and not isinstance(marker, bool) else None,
                "reason": "unsupported_project_schema_marker",
                "valuesRedacted": True,
                "fingerprint": _fingerprint(path),
            }, None, _manual_config_action(path, "unsupported_project_schema_marker"))
        explicit_schema = marker
    workflow = payload.get("workflow") if isinstance(payload, dict) else None
    recognized, conflict_reasons = _legacy_inputs(payload)
    if recognized and explicit_schema is not None:
        return ({
            "path": ".dev-flow.json",
            "status": "baseline_ambiguous",
            "observedSchema": explicit_schema,
            "reason": "schema_marker_legacy_conflict",
            "valuesRedacted": True,
            "fingerprint": _fingerprint(path),
            "recognizedInputs": recognized,
            "conflicts": ["schema_marker_legacy_conflict", *conflict_reasons],
        }, None, None)
    if recognized:
        report = {
            "path": ".dev-flow.json",
            "status": "migration_pending" if not conflict_reasons else "manual_only",
            "observedSchema": 0,
            "valuesRedacted": True,
            "fingerprint": _fingerprint(path),
            "recognizedInputs": recognized,
            "conflicts": conflict_reasons,
        }
        if conflict_reasons or not isinstance(workflow, (dict, type(None))):
            reason = conflict_reasons[0] if conflict_reasons else "workflow_not_object"
            return report, None, _manual_config_action(path, reason)
        action, manual = _plan_config_migration_action(
            repo,
            path,
            payload,
            report,
            contract,
            0,
        )
        return report, action, manual
    candidate_versions = (
        [explicit_schema]
        if explicit_schema is not None
        else sorted(contract["configTargets"], reverse=True)
    )
    matched_schema = next(
        (
            version
            for version in candidate_versions
            if _contains_config_target(
                payload,
                contract["configTargets"][version]["payload"],
            )
        ),
        None,
    )
    if matched_schema is not None:
        report = {
            "path": ".dev-flow.json",
            "status": (
                "current"
                if matched_schema == contract["projectSchemaHead"]
                else "migration_pending"
            ),
            "observedSchema": matched_schema,
            "valuesRedacted": True,
            "fingerprint": _fingerprint(path),
            "recognizedInputs": [],
            "conflicts": [],
        }
        if matched_schema == contract["projectSchemaHead"]:
            return report, None, None
        action, manual = _plan_config_migration_action(
            repo,
            path,
            payload,
            report,
            contract,
            matched_schema,
        )
        return report, action, manual
    return ({
        "path": ".dev-flow.json",
        "status": "baseline_ambiguous",
        "valuesRedacted": True,
        "fingerprint": _fingerprint(path),
    }, None, None)


def _legacy_inputs(payload: dict[str, Any]) -> tuple[list[dict[str, str]], list[str]]:
    workflow = payload.get("workflow")
    workflow = workflow if isinstance(workflow, dict) else {}
    recognized: list[dict[str, str]] = []
    conflicts: list[str] = []
    for canonical, aliases in LEGACY_WORKFLOW_FIELD_ALIASES.items():
        values: list[Any] = []
        for prefix, container in (("", payload), ("workflow.", workflow)):
            for alias in aliases:
                if alias not in container:
                    continue
                value = container[alias]
                values.append(value)
                recognized.append(
                    {
                        "field": f"{prefix}{alias}",
                        "valueType": _json_type(value),
                    }
                )
        if len({_canonical_json(value) for value in values}) > 1:
            conflicts.append(f"conflicting_legacy_{canonical}")
    recognized.sort(key=lambda item: item["field"])
    return recognized, conflicts


def _migrate_legacy_config(payload: dict[str, Any]) -> dict[str, Any]:
    migrated = json.loads(json.dumps(payload))
    workflow = migrated.get("workflow")
    if workflow is None:
        workflow = {}
        migrated["workflow"] = workflow
    for aliases in LEGACY_WORKFLOW_FIELD_ALIASES.values():
        for alias in aliases:
            migrated.pop(alias, None)
            workflow.pop(alias, None)
    workflow["mode"] = "full-openspec"
    return migrated


def _trusted_git_preimage(repo: Path, path: Path) -> dict[str, Any] | None:
    relative = path.relative_to(repo).as_posix()
    try:
        inside = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--is-inside-work-tree"],
            check=True,
            capture_output=True,
            text=True,
        )
        if inside.stdout.strip() != "true":
            return None
        subprocess.run(
            ["git", "-C", str(repo), "ls-files", "--error-unmatch", "--", relative],
            check=True,
            capture_output=True,
            text=True,
        )
        dirty = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain=v1", "--", relative],
            check=True,
            capture_output=True,
            text=True,
        )
        if dirty.stdout.strip():
            return None
        commit = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        blob = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", f"HEAD:{relative}"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return {"commit": commit, "blob": blob, "mode": stat.S_IMODE(path.stat().st_mode)}


def _manual_config_action(path: Path, reason: str) -> dict[str, str]:
    return {
        "kind": "workflow-config-migration",
        "path": path.name,
        "reason": reason,
    }


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "number"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _unrelated_worktree(repo: Path, managed_paths: set[str]) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain=v1", "--untracked-files=all"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    unrelated: set[str] = set()
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        raw_path = line[3:]
        candidates = raw_path.split(" -> ") if " -> " in raw_path else [raw_path]
        for candidate in candidates:
            normalized = candidate.strip().strip('"')
            if not _path_is_managed(normalized, managed_paths):
                unrelated.add(normalized)
    return sorted(unrelated)


def _path_is_managed(path: str, managed_paths: set[str]) -> bool:
    requested = Path(path)
    for managed in managed_paths:
        managed_path = Path(managed)
        if requested == managed_path:
            return True
        if managed_path in requested.parents or requested in managed_path.parents:
            return True
    return False


def _fingerprint(path: Path) -> dict[str, str]:
    if path.is_symlink():
        return {"kind": "symlink", "sha256": hashlib.sha256(str(path.readlink()).encode()).hexdigest()}
    if not path.exists():
        return {"kind": "absent", "sha256": hashlib.sha256(b"").hexdigest()}
    if not path.is_file():
        return {"kind": "non_regular", "sha256": hashlib.sha256(b"").hexdigest()}
    try:
        payload = path.read_bytes()
    except OSError:
        return {"kind": "unreadable", "sha256": hashlib.sha256(b"").hexdigest()}
    return {"kind": "file", "sha256": hashlib.sha256(payload).hexdigest()}


def _bytes_fingerprint(payload: bytes) -> dict[str, str]:
    return {"kind": "file", "sha256": hashlib.sha256(payload).hexdigest()}


def _symlink_fingerprint(target: str) -> dict[str, str]:
    return {"kind": "symlink", "sha256": hashlib.sha256(target.encode()).hexdigest()}


def _plan_digest(plan: dict[str, Any]) -> str:
    excluded = {"planSha256", "unrelatedWorktree"}
    payload = {key: value for key, value in plan.items() if key not in excluded}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()
