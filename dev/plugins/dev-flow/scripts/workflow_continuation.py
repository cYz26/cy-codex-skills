from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from workflow_paths import rel, repo_path
from workflow_implementation_readiness import repository_mutation_gate
from workflow_state import parse_state


CONTINUE_NEXT_ITEM = "CONTINUE_NEXT_ITEM"
CHECKPOINT_AND_CONTINUE = "CHECKPOINT_AND_CONTINUE"
VERIFY_ACTIVE_CHANGE = "VERIFY_ACTIVE_CHANGE"
FAIL_CLOSED_REPAIR = "FAIL_CLOSED_REPAIR"
AWAIT_HUMAN = "AWAIT_HUMAN"
READY_FOR_EXTERNAL_EFFECT = "READY_FOR_EXTERNAL_EFFECT"
COMPLETE = "COMPLETE"

AUTOMATIC_CONTINUATION_ACTIONS = frozenset(
    {CONTINUE_NEXT_ITEM, CHECKPOINT_AND_CONTINUE, VERIFY_ACTIVE_CHANGE}
)
VALID_STOP_ACTIONS = frozenset(
    {FAIL_CLOSED_REPAIR, AWAIT_HUMAN, READY_FOR_EXTERNAL_EFFECT, COMPLETE}
)
HUMAN_GATE_STATE = "awaiting_human"
EXTERNAL_EFFECT_STATUSES = frozenset({"pending", "authorization_required"})

INCOMPLETE_LEDGER_STATUSES = frozenset(
    {"todo", "in_progress", "planned", "executing", "review", "blocked"}
)
COMPLETE_LEDGER_STATUSES = frozenset({"done", "skipped_with_reason"})
MALFORMED_LEDGER_STATUS = "__malformed__"
MARKDOWN_TABLE_SEPARATOR = re.compile(r"^:?-{3,}:?$")
SAFE_CHANGE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
VALID_TASK_CHECKBOX = re.compile(r"^\s*[-+*]\s+\[([ xX])\]\s+\S.*$")
POSSIBLE_TASK_CHECKBOX = re.compile(r"^\s*[-+*]\s+\[[^]]*\]")
FENCE_START = re.compile(r"^\s*(`{3,}|~{3,})")


def decide_continuation(
    *,
    source_valid: bool,
    work_remaining: bool,
    checkpoint_recommended: bool,
    verification_passed: bool,
    human_gate: bool,
    external_effect_ready: bool,
    human_gate_resolution: Optional[dict[str, Any]] = None,
    external_effect_resolution: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Return one deterministic continuation outcome from explicit signals."""
    if not source_valid:
        return decision(
            FAIL_CLOSED_REPAIR,
            "the canonical execution source is invalid or ambiguous",
            "Repair or revalidate the canonical execution source inside the "
            "approved contract; do not persist a Human Gate unless concrete "
            "authority is missing.",
        )
    if human_gate:
        if not _is_concrete_human_resolution(human_gate_resolution):
            return decision(
                FAIL_CLOSED_REPAIR,
                "the recorded Human Gate lacks a trusted concrete authority resolution",
                "Repair the gate receipt and bound digests; do not present a generic Human Gate.",
            )
        result = decision(
            AWAIT_HUMAN,
            "an explicit Human Gate is recorded",
            "Present the one concrete question and wait for the human decision.",
        )
        if human_gate_resolution:
            return {
                **result,
                "authorityResolution": dict(human_gate_resolution),
                "missingAuthority": list(
                    human_gate_resolution.get("missingAuthority", [])
                ),
                "gateKey": human_gate_resolution.get("gateKey"),
                "reasonCodes": list(human_gate_resolution.get("reasonCodes", [])),
            }
        return result
    if work_remaining and checkpoint_recommended:
        return decision(
            CHECKPOINT_AND_CONTINUE,
            "approved work remains and a durable checkpoint is recommended",
            "Write and validate the checkpoint, then continue with the next approved item.",
        )
    if work_remaining:
        return decision(
            CONTINUE_NEXT_ITEM,
            "approved executable work remains",
            "Return to project-orchestrator and execute the next dependency-ready item.",
        )
    if not verification_passed:
        return decision(
            VERIFY_ACTIVE_CHANGE,
            "the active execution source is closed but current verification is missing",
            "Run current-change review and verification before any completion claim.",
        )
    if external_effect_ready:
        authority_decision = str((external_effect_resolution or {}).get("decision") or "")
        if authority_decision == AWAIT_HUMAN:
            authority_resolution = dict(external_effect_resolution or {})
            if not _is_concrete_human_resolution(authority_resolution):
                return {
                    **decision(
                        FAIL_CLOSED_REPAIR,
                        "the external authority resolution is incomplete or malformed",
                        "Repair the resolver evidence; do not present or persist a generic Human Gate.",
                    ),
                    "authorityResolution": authority_resolution,
                }
            return {
                **decision(
                    AWAIT_HUMAN,
                    "the external effect requires concrete authority not present in the current contract",
                    "Present the one concrete missing-authority question and wait.",
                ),
                "authorityResolution": authority_resolution,
                "missingAuthority": list(
                    authority_resolution.get("missingAuthority", [])
                ),
                "gateKey": authority_resolution.get("gateKey"),
                "reasonCodes": list(authority_resolution.get("reasonCodes", [])),
            }
        if authority_decision == FAIL_CLOSED_REPAIR:
            return {
                **decision(
                    FAIL_CLOSED_REPAIR,
                    "external-effect evidence is incomplete or drifted",
                    "Repair or refresh the bound evidence for the same authorized identity before mutation.",
                ),
                "authorityResolution": dict(external_effect_resolution or {}),
            }
        if authority_decision == "CONTINUE":
            return {
                **decision(
                    READY_FOR_EXTERNAL_EFFECT,
                    "the verified effect is covered by a current standing milestone contract",
                    "Execute the next declared milestone effect and record its readback receipt.",
                    continuation_required=True,
                    stop_allowed=False,
                ),
                "authorityResolution": dict(external_effect_resolution or {}),
            }
        return decision(
            READY_FOR_EXTERNAL_EFFECT,
            "verified work reached a separately authorized external-effect boundary",
            "Present the exact external effect and request its existing explicit authorization.",
        )
    return decision(
        COMPLETE,
        "the active execution source is closed and required verification is current",
        "Prepare the overall completion claim with fresh evidence and residual risks.",
    )


def decision(
    action: str,
    reason: str,
    next_action: str,
    *,
    continuation_required: Optional[bool] = None,
    stop_allowed: Optional[bool] = None,
) -> dict[str, Any]:
    return {
        "action": action,
        "reason": reason,
        "nextAction": next_action,
        "continuationRequired": (
            action in AUTOMATIC_CONTINUATION_ACTIONS
            if continuation_required is None
            else continuation_required
        ),
        "stopAllowed": action in VALID_STOP_ACTIONS if stop_allowed is None else stop_allowed,
    }


def generated_artifact_orchestration(
    repo: Path,
    contract: dict[str, Any],
    manifest: dict[str, Any],
    proposed_plan: dict[str, Any] | None,
    *,
    prior_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from workflow_generated_artifacts import (
        AUTO_CLEAN,
        HUMAN_GATE,
        RETAIN,
        WAIT_OWNER,
        apply_cleanup,
        plan_cleanup,
        validate_terminal_cleanup,
    )
    if prior_receipt is not None and proposed_plan is not None:
        terminal_errors = validate_terminal_cleanup(
            repo,
            contract,
            manifest,
            proposed_plan,
            prior_receipt,
        )
        if not terminal_errors:
            resolution = generated_artifact_authority_resolution(
                proposed_plan,
                contract,
            )
            return {
                "decision": AUTO_CLEAN,
                "action": "APPLY_GENERATED_ARTIFACT_CLEANUP",
                "status": "complete",
                "applyAllowed": True,
                "requiresExplicitApply": True,
                "applySafeguardSupplied": False,
                "receiptRequired": True,
                "receipt": prior_receipt,
                "replayed": True,
                "awaitingHumanWritten": False,
                "authorityResolution": resolution,
                "reasons": ["terminal_cleanup_receipt_valid"],
                "plan": proposed_plan,
            }

    fresh_plan = plan_cleanup(repo, contract, manifest)
    if proposed_plan is not None and proposed_plan != fresh_plan:
        return {
            "decision": FAIL_CLOSED_REPAIR,
            "action": FAIL_CLOSED_REPAIR,
            "status": "blocked",
            "applyAllowed": False,
            "requiresExplicitApply": True,
            "applySafeguardSupplied": False,
            "receiptRequired": False,
            "receipt": None,
            "awaitingHumanWritten": False,
            "reasons": ["stale_or_self_authored_plan"],
            "plan": fresh_plan,
        }

    artifact_decision = fresh_plan["decision"]
    if artifact_decision == HUMAN_GATE:
        return {
            "decision": FAIL_CLOSED_REPAIR,
            "action": FAIL_CLOSED_REPAIR,
            "status": "blocked",
            "applyAllowed": False,
            "requiresExplicitApply": True,
            "applySafeguardSupplied": False,
            "receiptRequired": False,
            "receipt": None,
            "awaitingHumanWritten": False,
            "reasons": list(fresh_plan["reasons"]),
            "plan": fresh_plan,
        }
    if artifact_decision == AUTO_CLEAN:
        resolution = generated_artifact_authority_resolution(fresh_plan, contract)
        if resolution["decision"] != AUTO_CLEAN:
            return {
                "decision": FAIL_CLOSED_REPAIR,
                "action": FAIL_CLOSED_REPAIR,
                "status": "blocked",
                "applyAllowed": False,
                "requiresExplicitApply": True,
                "applySafeguardSupplied": False,
                "receiptRequired": False,
                "receipt": None,
                "awaitingHumanWritten": False,
                "authorityResolution": resolution,
                "reasons": list(resolution["reasonCodes"]),
                "plan": fresh_plan,
            }
        receipt = apply_cleanup(
            repo,
            contract,
            manifest,
            fresh_plan,
            prior_receipt=prior_receipt,
        )
        terminal_errors = validate_terminal_cleanup(
            repo,
            contract,
            manifest,
            fresh_plan,
            receipt,
        )
        if terminal_errors:
            return {
                "decision": FAIL_CLOSED_REPAIR,
                "action": FAIL_CLOSED_REPAIR,
                "status": "blocked",
                "applyAllowed": False,
                "requiresExplicitApply": True,
                "applySafeguardSupplied": True,
                "receiptRequired": True,
                "receipt": receipt,
                "awaitingHumanWritten": False,
                "authorityResolution": resolution,
                "reasons": terminal_errors,
                "plan": fresh_plan,
            }
        return {
            "decision": AUTO_CLEAN,
            "action": "APPLY_GENERATED_ARTIFACT_CLEANUP",
            "status": "complete",
            "applyAllowed": True,
            "requiresExplicitApply": True,
            "applySafeguardSupplied": prior_receipt is None,
            "receiptRequired": True,
            "receipt": receipt,
            "replayed": prior_receipt is not None and receipt == prior_receipt,
            "awaitingHumanWritten": False,
            "authorityResolution": resolution,
            "reasons": list(fresh_plan["reasons"]),
            "plan": fresh_plan,
        }
    routes = {
        WAIT_OWNER: ("WAIT_OWNER", False, False),
        RETAIN: ("RECORD_RETENTION", False, False),
    }
    action, apply_allowed, receipt_required = routes[artifact_decision]
    return {
        "decision": artifact_decision,
        "action": action,
        "applyAllowed": apply_allowed,
        "requiresExplicitApply": True,
        "applySafeguardSupplied": False,
        "receiptRequired": receipt_required,
        "receipt": None,
        "awaitingHumanWritten": False,
        "reasons": list(fresh_plan["reasons"]),
        "plan": fresh_plan,
    }


def generated_artifact_authority_resolution(
    plan: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    from workflow_authority_delta import resolve_authority_delta

    entries = [str(path) for path in plan.get("entries", [])]
    return resolve_authority_delta(
        request={
            "action": "generated_artifact_cleanup",
            "effect": "destructive.cleanup",
            "target": "task_owned_generated_artifacts",
            "scope": "approved-slice",
            "ownership": "task-owned",
            "risk": "reversible",
            "writeSet": entries,
            "cleanup": {
                "registered": True,
                "taskOwned": True,
                "ownerExited": True,
                "exactPaths": True,
                "identityCurrent": True,
                "recursive": False,
                "source": False,
                "userContent": False,
                "historicalReceipt": False,
                "persistentEvidence": False,
            },
        },
        authority_envelope={
            "goalId": str(contract.get("taskId") or "generated-artifact-lifecycle"),
            "changeId": str(contract.get("runId") or "generated-artifact-lifecycle"),
            "planDigest": str(plan.get("contractSha256") or "current"),
            "allowedActions": ["generated_artifact_cleanup"],
            "allowedEffects": ["destructive.cleanup"],
            "allowedTargets": ["task_owned_generated_artifacts"],
            "allowedOwnerships": ["task-owned"],
            "allowedRisks": ["reversible"],
            "writeSet": entries,
        },
        evidence={
            "trusted": True,
            "current": True,
            "complete": True,
            "identityCurrent": True,
            "ownerActive": False,
        },
    )


def continuation_decision(
    repo: Path,
    *,
    state: Optional[dict[str, Any]] = None,
    release_status: Optional[str] = None,
) -> dict[str, Any]:
    repo = repo_path(repo)
    current_state = state if state is not None else parse_state(repo)
    source = execution_source(repo, state=current_state)
    has_source = source["kind"] != "none"
    recorded_verification = bool(current_state.get("gates", {}).get("verification_passed"))
    effective_verification = recorded_verification if has_source else True
    context = current_state.get("context_management", {})
    checkpoint_recommended = bool(context.get("compact_recommended")) or context.get(
        "compact_status"
    ) == "pending"
    external_effect_ready = recorded_verification and str(release_status or "") in EXTERNAL_EFFECT_STATUSES
    authority_gate_validation = inspect_authority_gate(repo, current_state)
    standing = current_state.get("standing_milestone", {})
    external_effect_resolution = None
    if external_effect_ready:
        from workflow_standing_milestone import resolve_standing_milestone

        standing_status = (
            str(standing.get("status") or "inactive")
            if isinstance(standing, dict)
            else "inactive"
        )
        requested_effect = (
            "release.promote_local" if standing_status == "declared" else "git.commit"
        )
        external_effect_resolution = resolve_standing_milestone(
            repo,
            current_state,
            requested_effect=requested_effect,
            requested_target="plugins/dev-flow" if standing_status == "declared" else None,
        )
        external_effect_resolution = bind_external_authority_resolution(
            current_state,
            external_effect_resolution,
            requested_effect=requested_effect,
            requested_target=(
                "plugins/dev-flow" if standing_status == "declared" else None
            ),
            release_status=release_status,
        )
    if authority_gate_validation["status"] == "invalid":
        result = decision(
            FAIL_CLOSED_REPAIR,
            str(authority_gate_validation["reason"]),
            "Repair the authority gate state/receipt identity; do not write or present a new Human Gate.",
        )
    else:
        result = decide_continuation(
            source_valid=bool(source["valid"]),
            work_remaining=bool(source["incomplete"]),
            checkpoint_recommended=checkpoint_recommended,
            verification_passed=effective_verification,
            human_gate=bool(authority_gate_validation["valid"]),
            external_effect_ready=external_effect_ready,
            human_gate_resolution=authority_gate_validation.get("resolution"),
            external_effect_resolution=external_effect_resolution,
        )
    readiness = repository_mutation_gate(repo, ordinary_authority=True)
    if (
        result["action"] in AUTOMATIC_CONTINUATION_ACTIONS
        and readiness["applicable"]
        and not readiness["allowed"]
    ):
        result = decision(
            FAIL_CLOSED_REPAIR,
            "implementation readiness evidence blocks governed execution without proving missing authority",
            (
                "Perform the same-provider readiness diagnosis or evidence repair allowed by the "
                f"approved plan; do not persist a Human Gate. Required remediation: {readiness['nextAction']}"
            ),
        )
    return {
        **result,
        "executionSource": source,
        "implementationReadiness": readiness,
        "standingMilestoneResolution": external_effect_resolution,
        "authorityGateValidation": authority_gate_validation,
    }


def is_explicit_human_gate(
    state: dict[str, Any],
    repo: Path | None = None,
) -> bool:
    if repo is None:
        return False
    return bool(inspect_authority_gate(repo_path(repo), state)["valid"])


def inspect_authority_gate(repo: Path, state: dict[str, Any]) -> dict[str, Any]:
    repo = repo_path(repo)
    change = state.get("current_change", {})
    status = change.get("status") if isinstance(change, dict) else None
    gate = state.get("authority_gate", {})
    missing_authority = gate.get("missing_authority", []) if isinstance(gate, dict) else []
    gate_key = gate.get("key") if isinstance(gate, dict) else None
    stage_awaiting = normalize_token(state.get("current_stage")) == HUMAN_GATE_STATE
    change_awaiting = normalize_token(status) == HUMAN_GATE_STATE
    active = normalize_token(gate.get("status") if isinstance(gate, dict) else None) == "active"
    attempted = stage_awaiting or change_awaiting or active
    if not attempted:
        return {
            "status": "inactive",
            "valid": False,
            "reason": "no active authority gate is recorded",
            "resolution": None,
        }

    issues: list[str] = []
    if not stage_awaiting or not change_awaiting:
        issues.append("awaiting_human markers disagree")
    if not active:
        issues.append("authority gate status is not active")
    if not isinstance(gate_key, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", gate_key):
        issues.append("authority gate key is missing or malformed")
    normalized_missing = _unique_nonempty_strings(missing_authority)
    if not normalized_missing or normalized_missing != missing_authority:
        issues.append("authority gate missing authority is absent or noncanonical")
    state_resolution_digest = _normalized_sha256(
        gate.get("resolution_digest") if isinstance(gate, dict) else None
    )
    state_evidence_digest = _normalized_sha256(
        gate.get("evidence_digest") if isinstance(gate, dict) else None
    )
    if state_resolution_digest is None:
        issues.append("authority gate resolution digest is missing or malformed")
    if state_evidence_digest is None:
        issues.append("authority gate evidence digest is missing or malformed")

    receipt: dict[str, Any] | None = None
    receipt_path: Path | None = None
    if isinstance(gate_key, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", gate_key):
        receipt_path = (
            repo
            / ".planning"
            / "devflow"
            / "authority-gates"
            / f"{gate_key.removeprefix('sha256:')}.json"
        )
        if trusted_regular_file(repo, receipt_path):
            try:
                candidate = json.loads(
                    receipt_path.read_text(),
                    object_pairs_hook=_json_mapping_without_duplicate_keys,
                )
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
                issues.append("authority gate receipt is unreadable")
            else:
                if isinstance(candidate, dict):
                    receipt = candidate
                else:
                    issues.append("authority gate receipt is not a mapping")
        else:
            issues.append("authority gate receipt is missing or untrusted")

    resolution: dict[str, Any] | None = None
    if receipt is not None and receipt_path is not None:
        receipt_issues = _authority_gate_receipt_issues(
            repo,
            receipt_path,
            receipt,
            gate_key=str(gate_key),
            state_gate=gate if isinstance(gate, dict) else {},
            state_missing=normalized_missing,
            state_resolution_digest=state_resolution_digest,
            state_evidence_digest=state_evidence_digest,
        )
        issues.extend(receipt_issues)
        if not receipt_issues:
            resolution = {
                "decision": "AWAIT_HUMAN",
                "reasonCodes": list(receipt["reasonCodes"]),
                "missingAuthority": list(receipt["missingAuthority"]),
                "invalidations": list(receipt["invalidations"]),
                "materialDelta": True,
                "gateKey": receipt["gateKey"],
                "authorityContractSha256": receipt["authorityContractSha256"],
                "evidenceSha256": receipt["evidenceSha256"],
                "requestSha256": receipt["requestSha256"],
                "receiptPath": receipt["receiptPath"],
            }
            if "standingContractDigest" in receipt:
                resolution["standingContractDigest"] = receipt["standingContractDigest"]

    if issues:
        return {
            "status": "invalid",
            "valid": False,
            "reason": "; ".join(dict.fromkeys(issues)),
            "reasonCodes": ["AUTHORITY_GATE_RECEIPT_INVALID"],
            "resolution": None,
        }
    return {
        "status": "valid",
        "valid": True,
        "reason": "active authority gate receipt and state identity match",
        "reasonCodes": list(resolution["reasonCodes"] if resolution else []),
        "resolution": resolution,
    }


def _authority_gate_receipt_issues(
    repo: Path,
    receipt_path: Path,
    receipt: dict[str, Any],
    *,
    gate_key: str,
    state_gate: dict[str, Any],
    state_missing: list[str],
    state_resolution_digest: str | None,
    state_evidence_digest: str | None,
) -> list[str]:
    expected_keys = {
        "schemaVersion",
        "kind",
        "status",
        "gateKey",
        "decision",
        "reasonCodes",
        "missingAuthority",
        "invalidations",
        "materialDelta",
        "authorityContractSha256",
        "evidenceSha256",
        "requestSha256",
        "nextQuestion",
        "receiptPath",
    }
    issues: list[str] = []
    allowed_key_sets = (expected_keys, expected_keys | {"standingContractDigest"})
    if set(receipt) not in allowed_key_sets:
        issues.append("authority gate receipt fields do not match the trusted contract")
    if (
        receipt.get("schemaVersion") != "1.0"
        or receipt.get("kind") != "devflow-authority-gate-receipt"
        or receipt.get("status") != "recorded"
        or receipt.get("decision") != "AWAIT_HUMAN"
        or receipt.get("materialDelta") is not True
    ):
        issues.append("authority gate receipt classification is invalid")
    reason_codes = _unique_nonempty_strings(receipt.get("reasonCodes"))
    missing = _unique_nonempty_strings(receipt.get("missingAuthority"))
    invalidations = _unique_nonempty_strings(receipt.get("invalidations"))
    if not reason_codes or reason_codes != receipt.get("reasonCodes"):
        issues.append("authority gate receipt reason codes are absent or noncanonical")
    if not missing or missing != receipt.get("missingAuthority") or missing != state_missing:
        issues.append("authority gate receipt missing authority does not match state")
    if invalidations != receipt.get("invalidations"):
        issues.append("authority gate receipt invalidations are noncanonical")
    authority_digest = _normalized_sha256(receipt.get("authorityContractSha256"))
    evidence_digest = _normalized_sha256(receipt.get("evidenceSha256"))
    request_digest = _normalized_sha256(receipt.get("requestSha256"))
    if None in {authority_digest, evidence_digest, request_digest}:
        issues.append("authority gate receipt identity digests are missing or malformed")
    if evidence_digest != state_evidence_digest or request_digest != state_resolution_digest:
        issues.append("authority gate receipt digests do not match current state")
    if receipt.get("gateKey") != gate_key:
        issues.append("authority gate receipt key does not match current state")
    if all(value is not None for value in (authority_digest, evidence_digest, request_digest)):
        from workflow_authority_gate import (
            AuthorityGateError,
            canonical_authority_gate_key_from_resolution,
        )

        try:
            expected_gate_key = canonical_authority_gate_key_from_resolution(receipt)
        except AuthorityGateError:
            issues.append("authority gate receipt canonical inputs are invalid")
        else:
            if gate_key != expected_gate_key:
                issues.append("authority gate receipt key does not match canonical inputs")
    expected_receipt_path = rel(repo, receipt_path)
    if receipt.get("receiptPath") != expected_receipt_path:
        issues.append("authority gate receipt path does not match its gate key")
    question = receipt.get("nextQuestion")
    if not isinstance(question, str) or not question.strip() or "\n" in question:
        issues.append("authority gate receipt next question is invalid")
    if state_gate.get("next_question") != question:
        issues.append("authority gate next question does not match current state")
    return issues


def _unique_nonempty_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return list(
        dict.fromkeys(
            item.strip()
            for item in value
            if isinstance(item, str) and item.strip()
        )
    )


def _normalized_sha256(value: object) -> str | None:
    match = re.fullmatch(r"(?:sha256:)?([0-9a-f]{64})", str(value or ""))
    if not match or match.group(1) == "0" * 64:
        return None
    return f"sha256:{match.group(1)}"


def _is_concrete_human_resolution(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    missing = _unique_nonempty_strings(value.get("missingAuthority"))
    reasons = _unique_nonempty_strings(value.get("reasonCodes"))
    gate_key = str(value.get("gateKey") or "")
    from workflow_authority_gate import (
        AuthorityGateError,
        canonical_authority_gate_key_from_resolution,
    )

    try:
        expected_gate_key = canonical_authority_gate_key_from_resolution(value)
    except AuthorityGateError:
        return False
    return bool(
        value.get("decision") == AWAIT_HUMAN
        and value.get("materialDelta") is True
        and missing
        and missing == value.get("missingAuthority")
        and reasons
        and reasons == value.get("reasonCodes")
        and _normalized_sha256(gate_key) == expected_gate_key
    )


def bind_external_authority_resolution(
    state: dict[str, Any],
    resolution: dict[str, Any],
    *,
    requested_effect: str,
    requested_target: str | None,
    release_status: str | None,
) -> dict[str, Any]:
    bound = dict(resolution)
    if bound.get("decision") != AWAIT_HUMAN or bound.get("materialDelta") is not True:
        return bound
    missing = _unique_nonempty_strings(bound.get("missingAuthority"))
    reasons = _unique_nonempty_strings(bound.get("reasonCodes"))
    invalidations = _unique_nonempty_strings(bound.get("invalidations"))
    if (
        not missing
        or missing != bound.get("missingAuthority")
        or not reasons
        or reasons != bound.get("reasonCodes")
        or invalidations != bound.get("invalidations")
    ):
        return bound
    authority_digest = _first_sha256(
        bound,
        "authorityContractSha256",
        "authorityDigest",
    )
    evidence_digest = _first_sha256(
        bound,
        "evidenceSha256",
        "evidenceDigest",
    )
    request_digest = _first_sha256(
        bound,
        "requestSha256",
        "requestDigest",
    )
    if None in {authority_digest, evidence_digest, request_digest}:
        return bound
    canonical_bound = {
        **bound,
        "reasonCodes": reasons,
        "missingAuthority": missing,
        "authorityContractSha256": authority_digest,
        "evidenceSha256": evidence_digest,
        "requestSha256": request_digest,
    }
    from workflow_authority_gate import (
        AuthorityGateError,
        canonical_authority_gate_key_from_resolution,
    )

    try:
        gate_key = canonical_authority_gate_key_from_resolution(canonical_bound)
    except AuthorityGateError:
        return bound

    return {
        **canonical_bound,
        "gateKey": gate_key,
    }


def _first_sha256(value: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        normalized = _normalized_sha256(value.get(key))
        if normalized is not None:
            return normalized
    return None


def _json_mapping_without_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def normalize_token(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def execution_source(repo: Path, state: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    repo = repo_path(repo)
    current_state = state if state is not None else parse_state(repo)
    change = current_state.get("current_change", {})
    change_id = str(change.get("id") or "none") if isinstance(change, dict) else "none"
    if change_id not in {"", "none"}:
        if not SAFE_CHANGE_ID.fullmatch(change_id):
            return source_report(
                "openspec",
                f"openspec/changes/{change_id}/tasks.md",
                valid=False,
                issues=["active OpenSpec change id is unsafe or malformed"],
            )
        tasks = repo / "openspec" / "changes" / change_id / "tasks.md"
        if not trusted_regular_file(repo, tasks):
            return source_report(
                "openspec",
                rel(repo, tasks),
                valid=False,
                issues=["active OpenSpec tasks file is missing or untrusted"],
            )
        try:
            return openspec_execution_source(repo, tasks, tasks.read_text())
        except (OSError, UnicodeError):
            return source_report(
                "openspec",
                rel(repo, tasks),
                valid=False,
                issues=["active OpenSpec tasks file is unreadable"],
            )

    ledger = repo / "TASK_LEDGER.md"
    if not ledger.exists():
        return source_report("none", "none", valid=True)
    if not trusted_regular_file(repo, ledger):
        return source_report(
            "task_ledger",
            "TASK_LEDGER.md",
            valid=False,
            issues=["fallback task ledger is untrusted"],
        )
    try:
        return ledger_execution_source(repo, ledger, ledger.read_text())
    except (OSError, UnicodeError):
        return source_report(
            "task_ledger",
            "TASK_LEDGER.md",
            valid=False,
            issues=["fallback task ledger is unreadable"],
        )


def trusted_regular_file(repo: Path, path: Path) -> bool:
    try:
        relative = path.absolute().relative_to(repo.resolve())
    except ValueError:
        return False
    current = repo.resolve()
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return False
    return current.is_file()


def openspec_execution_source(repo: Path, path: Path, text: str) -> dict[str, Any]:
    total = 0
    incomplete = 0
    issues: list[str] = []
    fence: Optional[str] = None
    for line_number, line in enumerate(text.splitlines(), start=1):
        marker = FENCE_START.match(line)
        if marker:
            token = marker.group(1)
            kind = token[0]
            if fence is None:
                fence = kind
            elif fence == kind:
                fence = None
            continue
        if fence is not None:
            continue
        checkbox = VALID_TASK_CHECKBOX.match(line)
        if checkbox:
            total += 1
            if checkbox.group(1) == " ":
                incomplete += 1
            continue
        if POSSIBLE_TASK_CHECKBOX.match(line):
            issues.append(f"malformed task checkbox at line {line_number}")
    if fence is not None:
        issues.append("unterminated fenced block in active OpenSpec tasks")
    if total == 0:
        issues.append("active OpenSpec tasks contain no valid task checkboxes")
    return source_report(
        "openspec",
        rel(repo, path),
        valid=not issues,
        total=total,
        incomplete=incomplete,
        issues=issues,
    )


def ledger_execution_source(repo: Path, path: Path, text: str) -> dict[str, Any]:
    statuses = markdown_table_column_values(text, "status")
    unknown = sorted(
        {
            status
            for status in statuses
            if status not in INCOMPLETE_LEDGER_STATUSES and status not in COMPLETE_LEDGER_STATUSES
        }
    )
    issues: list[str] = []
    if not statuses:
        issues.append("fallback task ledger contains no task statuses")
    if unknown:
        issues.append(f"fallback task ledger has invalid task statuses: {', '.join(unknown)}")
    incomplete = sum(status in INCOMPLETE_LEDGER_STATUSES for status in statuses)
    return source_report(
        "task_ledger",
        rel(repo, path),
        valid=not issues,
        total=len(statuses),
        incomplete=incomplete,
        issues=issues,
        invalid_statuses=unknown,
    )


def source_report(
    kind: str,
    path: str,
    *,
    valid: bool,
    total: int = 0,
    incomplete: int = 0,
    issues: Optional[list[str]] = None,
    invalid_statuses: Optional[list[str]] = None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "path": path,
        "valid": valid,
        "total": total,
        "incomplete": incomplete,
        "complete": total - incomplete,
        "issues": list(issues or []),
        "invalidStatuses": list(invalid_statuses or []),
    }


def markdown_table_column_values(text: str, column_name: str) -> list[str]:
    """Return normalized values from a named column in Markdown tables only."""
    lines = text.splitlines()
    values: list[str] = []
    index = 0
    wanted = column_name.strip().lower()
    while index + 1 < len(lines):
        header = markdown_table_cells(lines[index])
        separator = markdown_table_cells(lines[index + 1])
        if (
            wanted not in header
            or len(separator) != len(header)
            or not all(MARKDOWN_TABLE_SEPARATOR.fullmatch(cell) for cell in separator)
        ):
            index += 1
            continue

        column_index = header.index(wanted)
        index += 2
        while index < len(lines):
            row = markdown_table_cells(lines[index])
            if not row:
                break
            if len(row) != len(header):
                values.append(MALFORMED_LEDGER_STATUS)
                break
            values.append(row[column_index])
            index += 1
    return values


def markdown_table_cells(line: str) -> list[str]:
    stripped = line.strip()
    if "|" not in stripped:
        return []
    cells: list[str] = []
    current: list[str] = []
    index = 0
    while index < len(stripped):
        character = stripped[index]
        if character == "\\" and index + 1 < len(stripped) and stripped[index + 1] == "|":
            current.append("|")
            index += 2
            continue
        if character == "|":
            cells.append("".join(current))
            current = []
        else:
            current.append(character)
        index += 1
    cells.append("".join(current))
    if stripped.startswith("|"):
        cells = cells[1:]
    if stripped.endswith("|"):
        cells = cells[:-1]
    return [cell.strip().lower() for cell in cells]
