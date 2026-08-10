from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
import re
from typing import Any

from workflow_authority_delta import resolve_authority_delta
from workflow_milestone_contract import (
    SUPPORTED_EFFECTS,
    validate_milestone_contract,
)


CONTINUE = "CONTINUE"
FAIL_CLOSED_REPAIR = "FAIL_CLOSED_REPAIR"
AWAIT_HUMAN = "AWAIT_HUMAN"


def resolve_standing_milestone(
    repo: Path,
    state: Mapping[str, Any],
    *,
    requested_effect: str | None = None,
    requested_target: str | None = None,
) -> dict[str, Any]:
    """Resolve standing milestone authority without mutating repository state."""

    repo = Path(repo).resolve()
    standing = state.get("standing_milestone")
    standing_data = standing if isinstance(standing, Mapping) else {}
    status = str(standing_data.get("status") or "inactive").strip()
    effect_raw = requested_effect if isinstance(requested_effect, str) else ""
    target_raw = requested_target if isinstance(requested_target, str) else ""
    request_invalidations = _request_invalidations(requested_effect, requested_target)
    effect = effect_raw.strip()
    target = target_raw.strip()
    if request_invalidations:
        return _result(
            decision=FAIL_CLOSED_REPAIR,
            status=status,
            reason_codes=["STANDING_REQUEST_INVALID"],
            invalidations=request_invalidations,
            requested_effect=effect_raw,
            requested_target=target_raw,
        )
    if status == "inactive":
        authority_resolution = _standing_authority_resolution(
            state,
            requested_effect=effect,
            requested_target=target,
        )
        return _result(
            decision=str(authority_resolution["decision"]),
            status=status,
            reason_codes=["STANDING_AUTHORITY_MISSING"],
            requested_effect=effect,
            requested_target=target,
            authority_resolution=authority_resolution,
        )
    if status not in {"declared", "current"}:
        return _result(
            decision=FAIL_CLOSED_REPAIR,
            status=status,
            reason_codes=["STANDING_MILESTONE_STATUS_INVALID"],
            invalidations=["standing_milestone.status"],
            requested_effect=effect,
            requested_target=target,
        )
    loaded = _load_bound_contract(repo, state, standing_data)
    if loaded.get("error"):
        return _result(
            decision=FAIL_CLOSED_REPAIR,
            status=status,
            reason_codes=[str(loaded["error"])],
            invalidations=[str(loaded["invalidation"])],
            requested_effect=effect,
            requested_target=target,
            contract_path=loaded.get("contractPath"),
            contract_sha256=loaded.get("contractSha256"),
        )
    contract = loaded["contract"]
    contract_validation = validate_milestone_contract(
        contract,
        project_target_available=_project_target_available(contract),
    )
    if not contract_validation["ok"]:
        return _result(
            decision=FAIL_CLOSED_REPAIR,
            status=status,
            reason_codes=list(contract_validation["reasonCodes"]),
            invalidations=list(contract_validation["invalidations"]),
            requested_effect=effect,
            requested_target=target,
            **_contract_result_fields(loaded),
        )
    loaded = {**loaded, "contractValidation": contract_validation}
    if status == "declared":
        resolved_target = _effect_target(loaded, effect)
        authority_resolution = _standing_authority_resolution(
            state,
            requested_effect=effect,
            requested_target=target,
            loaded=loaded,
            evidence_current=effect == "release.promote_local",
        )
        if authority_resolution["decision"] == AWAIT_HUMAN:
            reason = (
                "EFFECT_OUTSIDE_STANDING_CONTRACT"
                if resolved_target is None
                else "TARGET_OUTSIDE_STANDING_CONTRACT"
            )
            return _result(
                decision=AWAIT_HUMAN,
                status=status,
                reason_codes=[reason],
                requested_effect=effect,
                requested_target=target,
                resolved_target=resolved_target,
                authority_resolution=authority_resolution,
                **_contract_result_fields(loaded),
            )
        if effect == "release.promote_local":
            return _result(
                decision=str(authority_resolution["decision"]),
                status=status,
                reason_codes=["STANDING_MILESTONE_DECLARED_LOCAL_PROMOTION"],
                requested_effect=effect,
                requested_target=target,
                resolved_target=resolved_target,
                authority_resolution=authority_resolution,
                **_contract_result_fields(loaded),
            )
        return _result(
            decision=str(authority_resolution["decision"]),
            status=status,
            reason_codes=["STANDING_MILESTONE_NOT_CURRENT"],
            invalidations=["standing_milestone.status"],
            requested_effect=effect,
            requested_target=target,
            authority_resolution=authority_resolution,
            **_contract_result_fields(loaded),
        )
    if status == "current":
        evidence_digests = _frozen_evidence_digests(standing_data)
        invalidations = [
            f"standing_milestone.{name}"
            for name, value in evidence_digests.items()
            if not _is_sha256(value)
        ]
        if invalidations:
            return _result(
                decision=FAIL_CLOSED_REPAIR,
                status=status,
                reason_codes=["FROZEN_EVIDENCE_INCOMPLETE"],
                invalidations=invalidations,
                requested_effect=effect,
                requested_target=target,
                frozen_evidence_digests=evidence_digests,
                **_contract_result_fields(loaded),
            )
        if effect == "release.promote_local":
            return _result(
                decision=FAIL_CLOSED_REPAIR,
                status=status,
                reason_codes=["LOCAL_PROMOTION_AFTER_CANDIDATE_FREEZE"],
                invalidations=["standing_milestone.status"],
                requested_effect=effect,
                requested_target=target,
                frozen_evidence_digests=evidence_digests,
                **_contract_result_fields(loaded),
            )
        resolved_target = _effect_target(loaded, effect)
        authority_resolution = _standing_authority_resolution(
            state,
            requested_effect=effect,
            requested_target=target,
            loaded=loaded,
        )
        if authority_resolution["decision"] == AWAIT_HUMAN:
            reason = (
                "EFFECT_OUTSIDE_STANDING_CONTRACT"
                if resolved_target is None
                else "TARGET_OUTSIDE_STANDING_CONTRACT"
            )
            return _result(
                decision=AWAIT_HUMAN,
                status=status,
                reason_codes=[reason],
                requested_effect=effect,
                requested_target=target,
                resolved_target=resolved_target,
                frozen_evidence_digests=evidence_digests,
                authority_resolution=authority_resolution,
                **_contract_result_fields(loaded),
            )
        return _result(
            decision=str(authority_resolution["decision"]),
            status=status,
            reason_codes=["STANDING_MILESTONE_AUTHORITY_CURRENT"],
            requested_effect=effect,
            requested_target=target,
            resolved_target=resolved_target,
            authority_current=True,
            frozen_evidence_digests=evidence_digests,
            authority_resolution=authority_resolution,
            **_contract_result_fields(loaded),
        )
    return _result(
        decision=FAIL_CLOSED_REPAIR,
        status=status,
        reason_codes=["STANDING_CONTRACT_NOT_VALIDATED"],
        invalidations=["standing_milestone.status"],
        requested_effect=effect,
        requested_target=target,
    )


def _result(
    *,
    decision: str,
    status: str,
    reason_codes: list[str],
    missing_authority: list[str] | None = None,
    invalidations: list[str] | None = None,
    material_delta: bool = False,
    requested_effect: str,
    requested_target: str,
    resolved_target: str | None = None,
    contract_path: object = None,
    contract_sha256: object = None,
    contract_digest: object = None,
    frozen_evidence_digests: Mapping[str, str] | None = None,
    contract: Mapping[str, Any] | None = None,
    authority_current: bool = False,
    authority_resolution: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if authority_resolution is not None:
        decision = str(authority_resolution.get("decision") or "")
        missing_authority = list(authority_resolution.get("missingAuthority") or [])
        material_delta = authority_resolution.get("materialDelta") is True
    missing = list(dict.fromkeys(missing_authority or [])) if decision == AWAIT_HUMAN else []
    if decision == AWAIT_HUMAN and not missing:
        raise ValueError("AWAIT_HUMAN requires concrete missing authority")
    if decision == AWAIT_HUMAN and authority_resolution is None:
        raise ValueError("standing Human Gates require a central authority resolution")
    gate_key = authority_resolution.get("gateKey") if authority_resolution is not None else None
    result = {
        "schemaVersion": 1,
        "decision": decision,
        "reasonCodes": list(dict.fromkeys(reason_codes)),
        "missingAuthority": missing,
        "invalidations": list(dict.fromkeys(invalidations or [])),
        "materialDelta": bool(material_delta),
        "gateKey": gate_key,
        "status": status,
        "authorityCurrent": bool(authority_current),
        "requestedEffect": requested_effect,
        "requestedTarget": requested_target,
        "resolvedTarget": resolved_target,
        "contractPath": contract_path,
        "contractSha256": contract_sha256,
        "contractDigest": contract_digest,
        "frozenEvidenceDigests": dict(frozen_evidence_digests or {}),
        "contract": dict(contract) if contract is not None else None,
    }
    if authority_resolution is not None:
        for field in (
            "requestDigest",
            "authorityDigest",
            "evidenceDigest",
            "standingContractDigest",
        ):
            result[field] = authority_resolution.get(field)
    return result


def _standing_authority_resolution(
    state: Mapping[str, Any],
    *,
    requested_effect: str,
    requested_target: str,
    loaded: Mapping[str, Any] | None = None,
    evidence_current: bool = True,
) -> dict[str, object]:
    goal = state.get("goal_gate")
    change = state.get("current_change")
    goal_id = str(goal.get("id") if isinstance(goal, Mapping) else "")
    change_id = str(change.get("id") if isinstance(change, Mapping) else "")
    action = f"standing_milestone:{requested_effect or 'unspecified'}"
    standing_contract: dict[str, object] | None = None
    allowed_effects: list[str] = []
    allowed_targets: list[str] = []
    resolver_effect = requested_effect
    resolver_target = requested_target

    if loaded is None:
        resolver_effect = requested_effect or "standing-milestone-contract"
        resolver_target = requested_target or "standing-milestone-contract"
        allowed_effects.append(resolver_effect)
        allowed_targets.append(resolver_target)
        plan_digest = "standing-milestone-contract-missing"
    else:
        contract = loaded["contract"]
        plan_digest = str(loaded["contractDigest"])
        derived_target = _effect_target(loaded, requested_effect)
        resolver_target = requested_target or derived_target or ""
        effects = sorted(
            effect
            for effect in SUPPORTED_EFFECTS
            if _effect_target(loaded, effect) is not None
        )
        targets = sorted(
            {
                target
                for effect in effects
                if (target := _effect_target(loaded, effect)) is not None
            }
        )
        if requested_effect not in effects and requested_target:
            allowed_targets.append(requested_target)
        standing_contract = {
            "schemaVersion": 1,
            "goalId": goal_id,
            "changeId": change_id,
            "planDigest": plan_digest,
            "effects": effects,
            "targets": targets,
            "current": True,
        }

    return resolve_authority_delta(
        request={
            "action": action,
            "scope": "standing-milestone",
            "writeSet": [],
            "risk": "declared_external",
            "effect": resolver_effect,
            "target": resolver_target,
            "ownership": "standing-contract",
        },
        authority_envelope={
            "goalId": goal_id,
            "changeId": change_id,
            "planDigest": plan_digest,
            "writeSet": [],
            "allowedActions": [action],
            "allowedEffects": allowed_effects,
            "allowedTargets": allowed_targets,
            "allowedOwnerships": ["standing-contract"],
            "allowedRisks": ["declared_external"],
        },
        evidence={
            "trusted": True,
            "current": evidence_current,
            "complete": True,
            "identityCurrent": True,
        },
        standing_contract=standing_contract,
    )


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _frozen_evidence_digests(standing: Mapping[str, Any]) -> dict[str, str]:
    return {
        name: str(standing.get(name, standing.get(_camel_case(name))) or "").strip()
        for name in ("candidate_digest", "validation_digest", "review_digest")
    }


def _camel_case(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in tail)


def _is_sha256(value: object) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", str(value or "")))


def _request_invalidations(
    requested_effect: object,
    requested_target: object,
) -> list[str]:
    invalidations: list[str] = []
    if requested_effect is not None:
        if (
            not isinstance(requested_effect, str)
            or not requested_effect
            or requested_effect != requested_effect.strip()
            or not re.fullmatch(
                r"[a-z][a-z0-9]*(?:[._-][a-z0-9_-]+)+",
                requested_effect,
            )
        ):
            invalidations.append("request.effect")
    if requested_target is not None:
        if (
            not isinstance(requested_target, str)
            or not requested_target
            or requested_target != requested_target.strip()
            or any(character in requested_target for character in ("\x00", "\r", "\n"))
        ):
            invalidations.append("request.target")
    if (
        isinstance(requested_effect, str)
        and requested_effect
        and requested_effect == requested_effect.strip()
        and requested_effect not in SUPPORTED_EFFECTS
        and requested_target is None
    ):
        invalidations.append("request.target")
    if requested_effect is None and requested_target is not None:
        invalidations.append("request.effect")
    return list(dict.fromkeys(invalidations))


def _effect_target(loaded: Mapping[str, Any], effect: str) -> str | None:
    validation = loaded.get("contractValidation")
    if not isinstance(validation, Mapping) or validation.get("ok") is not True:
        return None
    targets = validation.get("effectTargets")
    if not isinstance(targets, Mapping):
        return None
    target = targets.get(effect)
    return str(target) if isinstance(target, str) and target else None


def _project_target_available(contract: Mapping[str, Any]) -> bool:
    refresh = contract.get("refreshTargets")
    if not isinstance(refresh, Mapping):
        return False
    project = refresh.get("project")
    if not isinstance(project, str) or not project:
        return False
    path = Path(project)
    return path.is_absolute() and path.is_dir() and not path.is_symlink()


def _contract_result_fields(loaded: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_path": loaded["contractPath"],
        "contract_sha256": loaded["contractSha256"],
        "contract_digest": loaded["contractDigest"],
        "contract": loaded["contract"],
    }


def _load_bound_contract(
    repo: Path,
    state: Mapping[str, Any],
    standing: Mapping[str, Any],
) -> dict[str, Any]:
    raw_path = standing.get("contract_path", standing.get("contractPath"))
    if not isinstance(raw_path, str) or not raw_path.strip():
        return {"error": "STANDING_CONTRACT_PATH_MISSING", "invalidation": "contract.path"}
    relative = Path(raw_path)
    if relative.is_absolute() or ".." in relative.parts:
        return {"error": "STANDING_CONTRACT_PATH_UNTRUSTED", "invalidation": "contract.path"}
    current_change = state.get("current_change")
    current_change_id = (
        current_change.get("id") if isinstance(current_change, Mapping) else None
    )
    if not _canonical_contract_path(relative, str(current_change_id or "")):
        return {
            "error": "STANDING_CONTRACT_PATH_UNTRUSTED",
            "invalidation": "contract.path",
            "contractPath": raw_path,
        }
    path = repo / relative
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(repo)
    except (FileNotFoundError, OSError, ValueError):
        return {
            "error": "STANDING_CONTRACT_PATH_UNTRUSTED",
            "invalidation": "contract.path",
            "contractPath": raw_path,
        }
    if path.is_symlink() or not resolved.is_file():
        return {
            "error": "STANDING_CONTRACT_PATH_UNTRUSTED",
            "invalidation": "contract.path",
            "contractPath": raw_path,
        }
    try:
        payload = resolved.read_bytes()
    except OSError:
        return {
            "error": "STANDING_CONTRACT_READ_FAILED",
            "invalidation": "contract.file",
            "contractPath": raw_path,
        }
    actual_sha256 = hashlib.sha256(payload).hexdigest()
    expected_sha256 = standing.get("contract_sha256", standing.get("contractSha256"))
    if expected_sha256 != actual_sha256:
        return {
            "error": "STANDING_CONTRACT_SHA256_DRIFT",
            "invalidation": "contract.sha256",
            "contractPath": raw_path,
            "contractSha256": actual_sha256,
        }
    try:
        contract = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_mapping_without_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return {
            "error": "STANDING_CONTRACT_INVALID_JSON",
            "invalidation": "contract.document",
            "contractPath": raw_path,
            "contractSha256": actual_sha256,
        }
    if not isinstance(contract, dict):
        return {
            "error": "STANDING_CONTRACT_INVALID_DOCUMENT",
            "invalidation": "contract.document",
            "contractPath": raw_path,
            "contractSha256": actual_sha256,
        }
    goal_gate = state.get("goal_gate")
    goal_id = goal_gate.get("id") if isinstance(goal_gate, Mapping) else None
    expected_goal = standing.get("goal_id", standing.get("goalId", goal_id))
    expected_change = standing.get("change_id", standing.get("changeId", current_change_id))
    if contract.get("goalId") != expected_goal or goal_id != expected_goal:
        return {
            "error": "STANDING_CONTRACT_GOAL_DRIFT",
            "invalidation": "contract.goalId",
            "contractPath": raw_path,
            "contractSha256": actual_sha256,
        }
    if contract.get("change") != expected_change or current_change_id != expected_change:
        return {
            "error": "STANDING_CONTRACT_CHANGE_DRIFT",
            "invalidation": "contract.change",
            "contractPath": raw_path,
            "contractSha256": actual_sha256,
        }
    plugin = contract.get("plugin")
    if not isinstance(plugin, Mapping) or not isinstance(plugin.get("id"), str):
        return {
            "error": "STANDING_CONTRACT_INVALID_DOCUMENT",
            "invalidation": "contract.plugin.id",
            "contractPath": raw_path,
            "contractSha256": actual_sha256,
        }
    return {
        "contract": contract,
        "contractPath": raw_path,
        "contractSha256": actual_sha256,
        "contractDigest": _digest(contract),
    }


def _mapping_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _canonical_contract_path(relative: Path, change_id: str) -> bool:
    parts = relative.parts
    if len(parts) >= 5 and parts[:2] == ("openspec", "changes"):
        return bool(change_id and parts[2] == change_id and parts[-1].endswith(".json"))
    if len(parts) >= 4 and parts[:2] == (".planning", "devflow"):
        return bool(
            parts[2] in {"milestone-external-effects", "standing-milestones"}
            and parts[-1].endswith(".json")
        )
    return False
