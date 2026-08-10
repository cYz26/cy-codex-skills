from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA_VERSION = 1

CONTINUE = "CONTINUE"
CONTINUE_WITH_MINIMAL_GUARD = "CONTINUE_WITH_MINIMAL_GUARD"
DEFER_AND_CONTINUE = "DEFER_AND_CONTINUE"
WAIT_OWNER = "WAIT_OWNER"
AUTO_CLEAN = "AUTO_CLEAN"
FAIL_CLOSED_REPAIR = "FAIL_CLOSED_REPAIR"
AWAIT_HUMAN = "AWAIT_HUMAN"

DECISIONS = frozenset(
    {
        CONTINUE,
        CONTINUE_WITH_MINIMAL_GUARD,
        DEFER_AND_CONTINUE,
        WAIT_OWNER,
        AUTO_CLEAN,
        FAIL_CLOSED_REPAIR,
        AWAIT_HUMAN,
    }
)

UNKNOWN_TOKENS = frozenset({"", "unknown", "ambiguous", "unresolved", "none"})
OWNERSHIP_CLASSES = frozenset(
    {
        "task-owned",
        "review-contract",
        "standing-contract",
        "user-workstation",
        "repository",
    }
)
RISK_CLASSES = frozenset(
    {
        "local_reversible",
        "read-only",
        "reversible",
        "external",
        "declared_external",
        "bounded",
    }
)
TECHNICAL_EVIDENCE_FIELDS = (
    "trusted",
    "current",
    "complete",
    "identityCurrent",
)
REQUIRED_CLEANUP_TRUE = (
    "registered",
    "taskOwned",
    "ownerExited",
    "exactPaths",
    "identityCurrent",
)
REQUIRED_CLEANUP_FALSE = (
    "recursive",
    "source",
    "userContent",
    "historicalReceipt",
    "persistentEvidence",
)
CLEANUP_FIELDS = frozenset((*REQUIRED_CLEANUP_TRUE, *REQUIRED_CLEANUP_FALSE))
MODEL_EFFECT_PREFIX = "model."
STANDING_EXECUTION_FIELDS = (
    "taskId",
    "provider",
    "model",
    "credentialPolicy",
    "costPolicy",
    "serial",
)
REQUEST_EXECUTION_FIELDS = (*STANDING_EXECUTION_FIELDS, "attemptId")
SUPPORTED_COST_POLICIES = frozenset({"record_actual_no_currency_gate"})


def resolve_authority_delta(
    *,
    request: Mapping[str, object],
    authority_envelope: Mapping[str, object],
    evidence: Mapping[str, object],
    standing_contract: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Resolve one proposed action without mutating state or performing effects.

    The resolver deliberately consumes plain mappings. Evidence gatherers and
    mutation adapters stay outside this module so every workflow surface shares
    the same deterministic classification and can test it without filesystem,
    process, Git, credential, or network access.
    """

    request_data = canonical_mapping(request)
    authority_data = canonical_mapping(authority_envelope)
    evidence_data = canonical_mapping(evidence)
    standing_data = (
        canonical_mapping(standing_contract) if standing_contract is not None else None
    )

    request_digest = document_digest(request_data)
    authority_digest = document_digest(authority_data)
    evidence_digest = document_digest(evidence_data)
    standing_digest = document_digest(standing_data) if standing_data is not None else None

    domain_reason_codes, domain_invalidations = validate_input_domains(
        request=request,
        request_data=request_data,
        authority_envelope=authority_envelope,
        authority_data=authority_data,
        evidence=evidence,
        evidence_data=evidence_data,
        standing_contract=standing_contract,
        standing_data=standing_data,
    )
    if domain_reason_codes:
        return resolution(
            decision=FAIL_CLOSED_REPAIR,
            reason_codes=domain_reason_codes,
            missing_authority=[],
            invalidations=domain_invalidations,
            material_delta=False,
            request_digest=request_digest,
            authority_digest=authority_digest,
            evidence_digest=evidence_digest,
            standing_digest=standing_digest,
        )

    missing_authority: list[str] = []
    invalidations: list[str] = []
    reason_codes: list[str] = []

    action = token(request_data.get("action"))
    effect = token(request_data.get("effect"))
    target = token(request_data.get("target"))
    ownership = token(request_data.get("ownership"))
    risk = token(request_data.get("risk"))
    allowed_ownerships = string_set(authority_data.get("allowedOwnerships"))
    allowed_risks = string_set(authority_data.get("allowedRisks"))

    if is_unknown_token(ownership):
        missing_authority.append(f"ownership:{ownership or 'unspecified'}")
        reason_codes.append("ownership_authority_unknown")
    elif ownership not in OWNERSHIP_CLASSES:
        missing_authority.append(f"ownership:{ownership}")
        reason_codes.append("ownership_class_unsupported")
    elif ownership not in allowed_ownerships:
        missing_authority.append(f"ownership:{ownership}")
        reason_codes.append("ownership_outside_authority_envelope")
    if is_unknown_token(risk):
        missing_authority.append(f"risk:{risk or 'unspecified'}")
        reason_codes.append("material_risk_authority_unknown")
    elif risk not in RISK_CLASSES:
        missing_authority.append(f"risk:{risk}")
        reason_codes.append("risk_class_unsupported")
    elif risk not in allowed_risks:
        missing_authority.append(f"risk:{risk}")
        reason_codes.append("risk_outside_authority_envelope")

    model_execution_requested = effect.startswith(MODEL_EFFECT_PREFIX)
    execution_missing = execution_missing_authority(request_data, authority_data)
    if execution_missing:
        missing_authority.extend(execution_missing)
        reason_codes.append("standing_execution_authority_delta")

    standing_requested = uses_standing_contract(
        request_data,
        standing_data,
        authority_data,
    )
    standing_current = False
    if standing_requested:
        if standing_data is None:
            invalidations.append("standing_contract:missing")
            reason_codes.append("standing_contract_missing")
        else:
            standing_current, standing_invalidations = validate_standing_identity(
                authority_data,
                standing_data,
            )
            invalidations.extend(standing_invalidations)
            if standing_invalidations:
                reason_codes.append("standing_contract_identity_invalid")

    allowed_actions = string_set(authority_data.get("allowedActions"))
    allowed_effects = string_set(authority_data.get("allowedEffects"))
    allowed_targets = string_set(authority_data.get("allowedTargets"))
    allowed_write_set = string_set(authority_data.get("writeSet"))
    requested_write_set = string_set(request_data.get("writeSet"))

    if not action or action not in allowed_actions:
        missing_authority.append(f"action:{action or 'unspecified'}")
        reason_codes.append("action_outside_authority_envelope")

    uncovered_writes = sorted(requested_write_set - allowed_write_set)
    if uncovered_writes:
        missing_authority.extend(f"write_set:{path}" for path in uncovered_writes)
        reason_codes.append("write_set_outside_authority_envelope")

    standing_effects = (
        string_set((standing_data or {}).get("effects")) if standing_current else set()
    )
    standing_targets = (
        string_set((standing_data or {}).get("targets")) if standing_current else set()
    )
    effect_covered = bool(effect and (effect in allowed_effects or effect in standing_effects))
    target_covered = bool(target and (target in allowed_targets or target in standing_targets))

    if not effect_covered:
        missing_authority.append(f"effect:{effect or 'unspecified'}")
        reason_codes.append("effect_outside_authority_envelope")
    if not target_covered:
        missing_authority.append(f"target:{target or 'unspecified'}")
        reason_codes.append("target_outside_authority_envelope")

    if invalidations:
        for invalidation in invalidations:
            missing_authority.append(authority_for_invalidation(invalidation))

    missing_authority = unique_strings(missing_authority)
    invalidations = unique_strings(invalidations)
    reason_codes = unique_strings(reason_codes)

    # Material authority/risk deltas precede repair, owner, cleanup, guard, and
    # deferral. This is the fail-closed boundary that prevents a convenient
    # technical route from laundering a changed target or permission.
    if missing_authority:
        return resolution(
            decision=AWAIT_HUMAN,
            reason_codes=reason_codes or ["concrete_authority_missing"],
            missing_authority=missing_authority,
            invalidations=invalidations,
            material_delta=True,
            request_digest=request_digest,
            authority_digest=authority_digest,
            evidence_digest=evidence_digest,
            standing_digest=standing_digest,
        )

    technical_failures = [
        field
        for field in TECHNICAL_EVIDENCE_FIELDS
        if evidence_data.get(field) is not True
    ]
    if technical_failures:
        return resolution(
            decision=FAIL_CLOSED_REPAIR,
            reason_codes=[f"technical_evidence_{field}_required" for field in technical_failures],
            missing_authority=[],
            invalidations=[f"evidence:{field}" for field in technical_failures],
            material_delta=False,
            request_digest=request_digest,
            authority_digest=authority_digest,
            evidence_digest=evidence_digest,
            standing_digest=standing_digest,
        )

    cleanup = request_data.get("cleanup")
    if isinstance(cleanup, Mapping):
        cleanup_issues = [
            issue for issue in cleanup_ineligibility(cleanup) if issue != "ownerExited"
        ]
        if cleanup_issues:
            return resolution(
                decision=FAIL_CLOSED_REPAIR,
                reason_codes=[f"cleanup_{issue}" for issue in cleanup_issues],
                missing_authority=[],
                invalidations=[f"cleanup:{issue}" for issue in cleanup_issues],
                material_delta=False,
                request_digest=request_digest,
                authority_digest=authority_digest,
                evidence_digest=evidence_digest,
                standing_digest=standing_digest,
            )
        owner_active = evidence_data.get("ownerActive")
        owner_exited = cleanup.get("ownerExited")
        if owner_active is True and owner_exited is False:
            return resolution(
                decision=WAIT_OWNER,
                reason_codes=["cleanup_owner_active"],
                missing_authority=[],
                invalidations=[],
                material_delta=False,
                request_digest=request_digest,
                authority_digest=authority_digest,
                evidence_digest=evidence_digest,
                standing_digest=standing_digest,
            )
        if owner_active is not False or owner_exited is not True:
            return resolution(
                decision=FAIL_CLOSED_REPAIR,
                reason_codes=["cleanup_owner_state_ambiguous"],
                missing_authority=[],
                invalidations=["cleanup:owner_state_ambiguous"],
                material_delta=False,
                request_digest=request_digest,
                authority_digest=authority_digest,
                evidence_digest=evidence_digest,
                standing_digest=standing_digest,
            )
        return resolution(
            decision=AUTO_CLEAN,
            reason_codes=["exact_task_owned_cleanup_eligible"],
            missing_authority=[],
            invalidations=[],
            material_delta=False,
            request_digest=request_digest,
            authority_digest=authority_digest,
            evidence_digest=evidence_digest,
            standing_digest=standing_digest,
        )

    if request_data.get("guardRequired") is True:
        return resolution(
            decision=CONTINUE_WITH_MINIMAL_GUARD,
            reason_codes=["bounded_guard_required"],
            missing_authority=[],
            invalidations=[],
            material_delta=False,
            request_digest=request_digest,
            authority_digest=authority_digest,
            evidence_digest=evidence_digest,
            standing_digest=standing_digest,
        )

    if request_data.get("deferralApproved") is True:
        return resolution(
            decision=DEFER_AND_CONTINUE,
            reason_codes=["nonblocking_deferral_approved"],
            missing_authority=[],
            invalidations=[],
            material_delta=False,
            request_digest=request_digest,
            authority_digest=authority_digest,
            evidence_digest=evidence_digest,
            standing_digest=standing_digest,
        )

    return resolution(
        decision=CONTINUE,
        reason_codes=[
            "standing_milestone_authority_current"
            if standing_requested
            else (
                "standing_goal_execution_authority_current"
                if model_execution_requested
                else "approved_authority_envelope_current"
            )
        ],
        missing_authority=[],
        invalidations=[],
        material_delta=False,
        request_digest=request_digest,
        authority_digest=authority_digest,
        evidence_digest=evidence_digest,
        standing_digest=standing_digest,
    )


def uses_standing_contract(
    request: Mapping[str, Any],
    standing_contract: Mapping[str, Any] | None,
    authority_envelope: Mapping[str, Any],
) -> bool:
    effect = token(request.get("effect"))
    target = token(request.get("target"))
    scope = token(request.get("scope"))
    risk = token(request.get("risk"))
    external_markers = ("git.", "github.", "plugin.", "cache.", "project.", "release.")
    standing_explicitly_matches = bool(
        standing_contract is not None
        and (
            effect in string_set(standing_contract.get("effects"))
            or target in string_set(standing_contract.get("targets"))
        )
    )
    if effect.startswith(MODEL_EFFECT_PREFIX) and scope != "standing-milestone":
        # Model execution uses the Goal-bound standingExecution envelope. Its
        # attempt receipt is deliberately separate from the release-oriented
        # Standing Milestone Contract used for Git/publication/refresh effects.
        return standing_explicitly_matches
    return bool(
        scope == "standing-milestone"
        or risk in {"external", "declared_external"}
        or effect.startswith(external_markers)
        or standing_explicitly_matches
    )


def execution_missing_authority(
    request: Mapping[str, Any],
    authority_envelope: Mapping[str, Any],
) -> list[str]:
    """Return stable execution dimensions outside the Goal envelope.

    Input-shape defects are handled earlier by validate_input_domains. The
    attemptId is intentionally absent from the human authority comparison.
    """

    if not token(request.get("effect")).startswith(MODEL_EFFECT_PREFIX):
        return []
    requested = request.get("execution")
    standing = authority_envelope.get("standingExecution")
    if not isinstance(requested, Mapping):
        return []
    if not isinstance(standing, Mapping):
        return ["execution:standingExecution"]
    return [
        f"execution:{field}"
        for field in STANDING_EXECUTION_FIELDS
        if requested.get(field) != standing.get(field)
    ]


def validate_input_domains(
    *,
    request: object,
    request_data: Mapping[str, Any],
    authority_envelope: object,
    authority_data: Mapping[str, Any],
    evidence: object,
    evidence_data: Mapping[str, Any],
    standing_contract: object,
    standing_data: Mapping[str, Any] | None,
) -> tuple[list[str], list[str]]:
    """Validate technical input shape before classifying missing authority.

    Unknown ownership, risk, and target facts are intentionally left for the
    authority classification below. Malformed containers and missing canonical
    action/Goal/change/plan identities are repair stops, not Human Gates.
    """

    reasons: list[str] = []
    invalidations: list[str] = []

    for label, raw, canonical in (
        ("request", request, request_data),
        ("authority", authority_envelope, authority_data),
        ("evidence", evidence, evidence_data),
    ):
        if not isinstance(raw, Mapping) or "__invalid_input_mapping__" in canonical:
            reasons.append(f"{label}_mapping_required")
            invalidations.append(f"{label}:mapping")

    if reasons:
        return unique_strings(reasons), unique_strings(invalidations)

    for field, label in (
        ("goalId", "goal"),
        ("changeId", "change"),
        ("planDigest", "plan"),
    ):
        if not valid_identity_token(authority_data.get(field)):
            reasons.append(f"authority_identity_{label}_invalid")
            invalidations.append(f"authority:{label}")

    for field in ("action", "effect"):
        if not valid_identity_token(request_data.get(field)):
            reasons.append(f"request_{field}_invalid")
            invalidations.append(f"request:{field}")

    if "policyEffect" in request_data:
        policy_effect = request_data.get("policyEffect")
        if not valid_identity_token(policy_effect):
            reasons.append("request_policy_effect_invalid")
            invalidations.append("request:policyEffect")
        elif policy_effect != request_data.get("effect"):
            reasons.append("request_policy_effect_mismatch")
            invalidations.append("request:policyEffect")

    target_value = request_data.get("target")
    if target_value is not None and (
        not isinstance(target_value, str)
        or (bool(target_value) and target_value != target_value.strip())
    ):
        reasons.append("request_target_malformed")
        invalidations.append("request:target")

    for field in ("ownership", "risk"):
        value = request_data.get(field)
        if value is not None and (
            not isinstance(value, str)
            or (bool(value) and value != value.strip())
        ):
            reasons.append(f"request_{field}_malformed")
            invalidations.append(f"request:{field}")

    scope = request_data.get("scope")
    if scope is not None and not valid_identity_token(scope):
        reasons.append("request_scope_invalid")
        invalidations.append("request:scope")

    collection_fields = (
        (request_data, "writeSet", "request_write_set_invalid", "request:writeSet"),
        (authority_data, "writeSet", "envelope_write_set_invalid", "authority:writeSet"),
        (
            authority_data,
            "allowedActions",
            "envelope_allowed_actions_invalid",
            "authority:allowedActions",
        ),
        (
            authority_data,
            "allowedEffects",
            "envelope_allowed_effects_invalid",
            "authority:allowedEffects",
        ),
        (
            authority_data,
            "allowedTargets",
            "envelope_allowed_targets_invalid",
            "authority:allowedTargets",
        ),
        (
            authority_data,
            "allowedOwnerships",
            "envelope_allowed_ownerships_invalid",
            "authority:allowedOwnerships",
        ),
        (
            authority_data,
            "allowedRisks",
            "envelope_allowed_risks_invalid",
            "authority:allowedRisks",
        ),
    )
    for mapping, field, reason, invalidation in collection_fields:
        if strict_string_list(mapping.get(field)) is None:
            reasons.append(reason)
            invalidations.append(invalidation)

    allowed_ownerships = strict_string_list(authority_data.get("allowedOwnerships"))
    if allowed_ownerships is not None and any(
        ownership not in OWNERSHIP_CLASSES for ownership in allowed_ownerships
    ):
        reasons.append("envelope_allowed_ownerships_invalid")
        invalidations.append("authority:allowedOwnerships")

    allowed_risks = strict_string_list(authority_data.get("allowedRisks"))
    if allowed_risks is not None and any(risk not in RISK_CLASSES for risk in allowed_risks):
        reasons.append("envelope_allowed_risks_invalid")
        invalidations.append("authority:allowedRisks")

    for field in ("guardRequired", "deferralApproved"):
        if field in request_data and not isinstance(request_data.get(field), bool):
            reasons.append(f"request_{field}_invalid")
            invalidations.append(f"request:{field}")

    model_execution = token(request_data.get("effect")).startswith(MODEL_EFFECT_PREFIX)
    if model_execution:
        request_execution = request_data.get("execution")
        if not isinstance(request_execution, Mapping):
            reasons.append("request_execution_mapping_required")
            invalidations.append("request:execution")
        else:
            execution_reasons, execution_invalidations = validate_execution_identity(
                request_execution,
                request_side=True,
            )
            reasons.extend(execution_reasons)
            invalidations.extend(execution_invalidations)

        if "standingExecution" in authority_data:
            standing_execution = authority_data.get("standingExecution")
            if not isinstance(standing_execution, Mapping):
                reasons.append("standing_execution_mapping_required")
                invalidations.append("authority:standingExecution")
            else:
                execution_reasons, execution_invalidations = validate_execution_identity(
                    standing_execution,
                    request_side=False,
                )
                reasons.extend(execution_reasons)
                invalidations.extend(execution_invalidations)

    cleanup_present = "cleanup" in request_data
    destructive_cleanup = token(request_data.get("effect")) == "destructive.cleanup"
    if (cleanup_present or destructive_cleanup) and not isinstance(
        request_data.get("cleanup"), Mapping
    ):
        reasons.append("cleanup_mapping_required")
        invalidations.append("cleanup:mapping")
    elif cleanup_present or destructive_cleanup:
        cleanup = request_data.get("cleanup")
        if isinstance(cleanup, Mapping) and set(cleanup) != CLEANUP_FIELDS:
            reasons.append("cleanup_fields_invalid")
            invalidations.append("cleanup:fields")

    if standing_contract is not None:
        if not isinstance(standing_contract, Mapping) or standing_data is None or (
            "__invalid_input_mapping__" in standing_data
        ):
            reasons.append("standing_mapping_required")
            invalidations.append("standing_contract:mapping")
        else:
            if standing_data.get("schemaVersion") != 1:
                reasons.append("standing_schema_version_invalid")
                invalidations.append("standing_contract:schemaVersion")
            for field, label in (
                ("goalId", "goal"),
                ("changeId", "change"),
                ("planDigest", "plan"),
            ):
                if not valid_identity_token(standing_data.get(field)):
                    reasons.append(f"standing_identity_{label}_invalid")
                    invalidations.append(f"standing_contract:{label}")
            for field in ("effects", "targets"):
                if strict_string_list(standing_data.get(field)) is None:
                    reasons.append(f"standing_{field}_invalid")
                    invalidations.append(f"standing_contract:{field}")
            if not isinstance(standing_data.get("current"), bool):
                reasons.append("standing_current_invalid")
                invalidations.append("standing_contract:current")

    return unique_strings(reasons), unique_strings(invalidations)


def validate_execution_identity(
    execution: Mapping[str, Any],
    *,
    request_side: bool,
) -> tuple[list[str], list[str]]:
    expected_fields = REQUEST_EXECUTION_FIELDS if request_side else STANDING_EXECUTION_FIELDS
    prefix = "request" if request_side else "authority"
    reasons: list[str] = []
    invalidations: list[str] = []
    if set(execution) != set(expected_fields):
        reasons.append(f"{prefix}_execution_fields_invalid")
        invalidations.append(f"{prefix}:execution.fields")
        return reasons, invalidations
    for field in expected_fields:
        value = execution.get(field)
        if field == "serial":
            if not isinstance(value, bool):
                reasons.append(f"{prefix}_execution_{field}_invalid")
                invalidations.append(f"{prefix}:execution.{field}")
        elif not valid_identity_token(value):
            reasons.append(f"{prefix}_execution_{field}_invalid")
            invalidations.append(f"{prefix}:execution.{field}")
    if not request_side and execution.get("costPolicy") not in SUPPORTED_COST_POLICIES:
        reasons.append(f"{prefix}_execution_cost_policy_unsupported")
        invalidations.append(f"{prefix}:execution.costPolicy")
    return unique_strings(reasons), unique_strings(invalidations)


def validate_standing_identity(
    authority_envelope: Mapping[str, Any],
    standing_contract: Mapping[str, Any],
) -> tuple[bool, list[str]]:
    invalidations: list[str] = []
    if standing_contract.get("current") is not True:
        invalidations.append("standing_contract:current")
    for field, label in (
        ("goalId", "goal"),
        ("changeId", "change"),
        ("planDigest", "plan"),
    ):
        if standing_contract.get(field) != authority_envelope.get(field):
            invalidations.append(f"standing_contract:{label}")
    return not invalidations, unique_strings(invalidations)


def authority_for_invalidation(invalidation: str) -> str:
    _, _, identity = invalidation.partition(":")
    if identity == "missing":
        return "standing_milestone.contract"
    return f"standing_authority:{identity or 'identity'}"


def cleanup_ineligibility(cleanup: Mapping[str, Any]) -> list[str]:
    issues = [field for field in REQUIRED_CLEANUP_TRUE if cleanup.get(field) is not True]
    issues.extend(field for field in REQUIRED_CLEANUP_FALSE if cleanup.get(field) is not False)
    return unique_strings(issues)


def resolution(
    *,
    decision: str,
    reason_codes: list[str],
    missing_authority: list[str],
    invalidations: list[str],
    material_delta: bool,
    request_digest: str,
    authority_digest: str,
    evidence_digest: str,
    standing_digest: str | None,
) -> dict[str, object]:
    if decision not in DECISIONS:
        raise ValueError(f"unknown authority decision: {decision}")
    missing = unique_strings(missing_authority) if decision == AWAIT_HUMAN else []
    gate_key = None
    if decision == AWAIT_HUMAN:
        if not missing:
            raise ValueError("AWAIT_HUMAN requires concrete missing authority")
        gate_key = canonical_authority_gate_digest(
            missing_authority=missing,
            request_digest=request_digest,
            authority_digest=authority_digest,
            evidence_digest=evidence_digest,
            standing_contract_digest=standing_digest,
        )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "decision": decision,
        "reasonCodes": unique_strings(reason_codes) or ["fail_closed_unspecified"],
        "missingAuthority": missing,
        "invalidations": unique_strings(invalidations),
        "materialDelta": bool(material_delta),
        "requestDigest": request_digest,
        "authorityDigest": authority_digest,
        "evidenceDigest": evidence_digest,
        "standingContractDigest": standing_digest,
        "gateKey": gate_key,
    }


def canonical_mapping(value: Mapping[str, object] | None) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        return {"__invalid_input_mapping__": type(value).__name__}
    try:
        return json.loads(canonical_json(value))
    except (TypeError, ValueError):
        return {"__invalid_input_mapping__": "non_json_mapping"}


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def document_digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def string_set(value: object) -> set[str]:
    values = strict_string_list(value)
    return set(values or [])


def strict_string_list(value: object) -> list[str] | None:
    if not isinstance(value, list):
        return None
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip() or item != item.strip():
            return None
        if item in result:
            return None
        result.append(item)
    return result


def valid_identity_token(value: object) -> bool:
    return bool(
        isinstance(value, str)
        and value == value.strip()
        and not is_unknown_token(value)
    )


def is_unknown_token(value: object) -> bool:
    return str(value or "").strip().lower() in UNKNOWN_TOKENS


def canonical_authority_gate_digest(
    *,
    missing_authority: list[str],
    request_digest: str,
    authority_digest: str,
    evidence_digest: str,
    standing_contract_digest: str | None,
) -> str:
    """Return the sole unprefixed canonical gate-key digest."""

    return document_digest(
        {
            "schemaVersion": SCHEMA_VERSION,
            "decision": AWAIT_HUMAN,
            "missingAuthority": unique_strings(missing_authority),
            "requestDigest": request_digest.removeprefix("sha256:"),
            "authorityDigest": authority_digest.removeprefix("sha256:"),
            "evidenceDigest": evidence_digest.removeprefix("sha256:"),
            "standingContractDigest": (
                standing_contract_digest.removeprefix("sha256:")
                if standing_contract_digest is not None
                else None
            ),
        }
    )


def unique_strings(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def token(value: object) -> str:
    return str(value or "").strip()
