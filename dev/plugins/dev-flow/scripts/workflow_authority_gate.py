from __future__ import annotations

import hashlib
import json
import re
import stat
from pathlib import Path
from typing import Any, Mapping

from workflow_authority_delta import canonical_authority_gate_digest
from workflow_paths import rel
from workflow_planning_paths import atomic_write_devflow, devflow_root
from workflow_state import parse_state, parse_state_text, trusted_repo_regular_file, update_state


SHA256_KEY = re.compile(r"sha256:[0-9a-f]{64}")
SHA256_VALUE = re.compile(r"(?:sha256:)?([0-9a-f]{64})")
EXECUTABLE_RESUME_STAGES = frozenset(
    {"planning", "executing", "verifying", "review_or_archive", "external_effects"}
)


class AuthorityGateError(RuntimeError):
    """Raised when a caller attempts to persist a non-authority stop as a gate."""


def record_authority_gate(
    repo: Path,
    resolution: Mapping[str, Any],
    *,
    next_question: str,
    prior_receipt: Path | None = None,
    _fault_after_receipt_persisted: bool = False,
) -> dict[str, Any]:
    repo = Path(repo).resolve()
    normalized = _validated_gate_resolution(resolution)
    question = str(next_question).strip()
    if not question or "\n" in question:
        raise AuthorityGateError("authority gate requires one concrete next question")

    receipt_path = _receipt_path(repo, normalized["gateKey"])
    expected = {
        "schemaVersion": "1.0",
        "kind": "devflow-authority-gate-receipt",
        "status": "recorded",
        "gateKey": normalized["gateKey"],
        "decision": "AWAIT_HUMAN",
        "reasonCodes": normalized["reasonCodes"],
        "missingAuthority": normalized["missingAuthority"],
        "invalidations": normalized["invalidations"],
        "materialDelta": normalized["materialDelta"],
        "authorityContractSha256": normalized["authorityContractSha256"],
        "evidenceSha256": normalized["evidenceSha256"],
        "requestSha256": normalized["requestSha256"],
        "nextQuestion": question,
        "receiptPath": rel(repo, receipt_path),
    }
    if normalized["standingContractDigest"] is not None:
        expected["standingContractDigest"] = normalized["standingContractDigest"]

    existing_receipt = _read_existing_receipt(
        repo,
        receipt_path,
        prior_receipt=prior_receipt,
    )
    if existing_receipt is not None:
        if _is_pending_gate_intent(existing_receipt):
            return _recover_pending_gate_intent(
                repo,
                receipt_path,
                existing_receipt,
                expected,
            )
        if existing_receipt != expected:
            raise AuthorityGateError(
                "existing authority gate receipt does not match this request"
            )
        state = parse_state(repo)
        _require_active_matching_state(state, normalized["gateKey"])
        _require_trusted_active_receipt(
            repo,
            state,
            normalized["gateKey"],
            existing_receipt,
        )
        replay = dict(existing_receipt)
        replay["status"] = "replayed"
        return replay

    _require_no_other_pending_gate_intent(repo, receipt_path)
    state, pre_gate_identity = _current_state_and_identity(repo)
    _require_gate_can_activate(state, normalized["gateKey"])
    intent = {
        "schemaVersion": "1.0",
        "kind": "devflow-authority-gate-write-ahead-intent",
        "status": "pending",
        "receipt": expected,
        "expectedPreGateState": pre_gate_identity,
    }
    atomic_write_devflow(
        repo,
        receipt_path,
        json.dumps(intent, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
    )
    if _fault_after_receipt_persisted:
        raise RuntimeError("injected crash after authority gate receipt persistence")
    _activate_gate_state(repo, expected)
    _finalize_gate_receipt(repo, receipt_path, expected)
    return expected


def _activate_gate_state(repo: Path, receipt: Mapping[str, Any]) -> None:
    update_state(
        repo,
        current_stage="awaiting_human",
        change_status="awaiting_human",
        authority_gate_key=receipt["gateKey"],
        authority_gate_status="active",
        authority_gate_resolution_digest=receipt["requestSha256"],
        authority_gate_evidence_digest=receipt["evidenceSha256"],
        authority_gate_next_question=receipt["nextQuestion"],
        authority_gate_missing_authority=receipt["missingAuthority"],
        status_text="Execution is awaiting one concrete authority decision.",
        next_action=receipt["nextQuestion"],
    )


def _finalize_gate_receipt(
    repo: Path,
    receipt_path: Path,
    receipt: Mapping[str, Any],
) -> None:
    atomic_write_devflow(
        repo,
        receipt_path,
        json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
    )


def _recover_pending_gate_intent(
    repo: Path,
    receipt_path: Path,
    intent: Mapping[str, Any],
    expected_receipt: dict[str, Any],
) -> dict[str, Any]:
    _require_matching_pending_intent(intent, expected_receipt)
    pre_gate_identity = intent["expectedPreGateState"]
    state, current_identity = _current_state_and_identity(repo)
    gate_key = expected_receipt["gateKey"]

    if current_identity == pre_gate_identity:
        _require_gate_can_activate(state, gate_key)
        _activate_gate_state(repo, expected_receipt)
    else:
        _require_active_matching_state(state, gate_key)
        _require_same_goal_change(state, pre_gate_identity)
        _require_trusted_active_receipt(
            repo,
            state,
            gate_key,
            expected_receipt,
        )

    _finalize_gate_receipt(repo, receipt_path, expected_receipt)
    return expected_receipt


def clear_authority_gate(
    repo: Path,
    *,
    gate_key: str,
    resolution: Mapping[str, Any],
    resume_stage: str,
) -> dict[str, Any]:
    repo = Path(repo).resolve()
    state = parse_state(repo)
    _require_active_matching_state(state, gate_key)
    stage = str(resume_stage).strip()
    if stage not in EXECUTABLE_RESUME_STAGES:
        raise AuthorityGateError("resume stage is not an allowlisted executable stage")

    receipt_path = _receipt_path(repo, gate_key)
    try:
        receipt_bytes = receipt_path.read_bytes()
        receipt = json.loads(
            receipt_bytes.decode("utf-8"),
            object_pairs_hook=_json_mapping_without_duplicate_keys,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise AuthorityGateError("authority gate receipt is missing or unreadable") from error
    if not isinstance(receipt, dict) or receipt.get("gateKey") != gate_key:
        raise AuthorityGateError("authority gate receipt identity does not match")
    _require_trusted_active_receipt(repo, state, gate_key, receipt)
    promotion = _require_current_authority_promotion(
        repo,
        state,
        receipt,
        receipt_sha256=f"sha256:{hashlib.sha256(receipt_bytes).hexdigest()}",
        gate_key=gate_key,
        resolution=resolution,
        resume_stage=stage,
    )

    update_state(
        repo,
        current_stage=stage,
        change_status=stage,
        authority_gate_key=gate_key,
        authority_gate_status="resolved",
        authority_gate_resolution_digest=promotion["requestSha256"],
        authority_gate_evidence_digest=promotion["evidenceSha256"],
        authority_gate_next_question="none",
        authority_gate_missing_authority=[],
        status_text="The authority gate is resolved and execution may resume.",
        next_action="Continue the approved execution slice.",
    )
    return {
        "schemaVersion": "1.0",
        "kind": "devflow-authority-gate-clearance",
        "status": "cleared",
        "gateKey": gate_key,
        "resumeStage": stage,
        "receiptPath": rel(repo, receipt_path),
        **promotion,
    }


def _require_current_authority_promotion(
    repo: Path,
    state: Mapping[str, Any],
    receipt: Mapping[str, Any],
    *,
    receipt_sha256: str,
    gate_key: str,
    resolution: Mapping[str, Any],
    resume_stage: str,
) -> dict[str, str]:
    if (
        resolution.get("schemaVersion") != "1.0"
        or resolution.get("kind") != "devflow-authority-promotion-proof"
        or str(resolution.get("decision") or "")
        not in {"CONTINUE", "CONTINUE_WITH_MINIMAL_GUARD", "AUTO_CLEAN"}
        or resolution.get("materialDelta") is not False
    ):
        raise AuthorityGateError("authority gate clearance proof classification is invalid")
    for compatibility_marker in ("trusted", "current", "evidenceCurrent"):
        if (
            compatibility_marker in resolution
            and resolution.get(compatibility_marker) is not True
        ):
            raise AuthorityGateError(
                "authority gate clearance compatibility markers cannot report stale evidence"
            )
    if resolution.get("missingAuthority") != []:
        raise AuthorityGateError("resolved authority gate cannot retain missing authority")
    if not _string_list(resolution.get("reasonCodes")):
        raise AuthorityGateError("authority gate clearance requires concrete reason codes")
    if _normalize_sha256(resolution.get("gateKey")) != gate_key:
        raise AuthorityGateError("authority promotion proof is bound to another gate")
    if _normalize_sha256(resolution.get("priorReceiptSha256")) != receipt_sha256:
        raise AuthorityGateError("authority promotion proof is bound to another receipt")

    prior_missing = _string_list(receipt.get("missingAuthority"))
    if (
        _string_list(resolution.get("priorMissingAuthority")) != prior_missing
        or _string_list(resolution.get("promotedAuthority")) != prior_missing
    ):
        raise AuthorityGateError("authority promotion does not cover the prior missing authority")

    prior_authority = _required_digest_value(receipt, "authorityContractSha256")
    if (
        _normalize_sha256(resolution.get("priorAuthorityContractSha256"))
        != prior_authority
    ):
        raise AuthorityGateError("authority promotion prior authority digest does not match")
    prior_evidence = _required_digest_value(receipt, "evidenceSha256")
    if _normalize_sha256(resolution.get("priorEvidenceSha256")) != prior_evidence:
        raise AuthorityGateError("authority promotion prior evidence digest does not match")
    goal = state.get("goal_gate")
    change = state.get("current_change")
    goal_id = goal.get("id") if isinstance(goal, Mapping) else None
    goal_status = goal.get("status") if isinstance(goal, Mapping) else None
    change_id = change.get("id") if isinstance(change, Mapping) else None
    if (
        str(goal_id or "") in {"", "none", "unknown"}
        or str(goal_status or "") not in {"active", "approved", "current", "satisfied"}
        or resolution.get("goalId") != goal_id
        or resolution.get("changeId") != change_id
    ):
        raise AuthorityGateError("authority promotion does not match the current Goal and change")
    if resolution.get("resumeStage") != resume_stage:
        raise AuthorityGateError("authority promotion does not bind the requested resume stage")

    artifact = _load_authority_artifact(
        repo,
        change_id=str(change_id),
        resolution=resolution,
    )
    artifact_document = artifact["document"]
    if (
        artifact_document.get("schemaVersion") != "1.0"
        or artifact_document.get("kind") != "devflow-authority-grant"
        or artifact_document.get("status") != "approved"
        or artifact_document.get("goalId") != goal_id
        or artifact_document.get("changeId") != change_id
        or _normalize_sha256(artifact_document.get("gateKey")) != gate_key
        or _normalize_sha256(artifact_document.get("priorReceiptSha256"))
        != receipt_sha256
        or _normalize_sha256(
            artifact_document.get("priorAuthorityContractSha256")
        )
        != prior_authority
        or _normalize_sha256(artifact_document.get("priorEvidenceSha256"))
        != prior_evidence
        or _string_list(artifact_document.get("grantedAuthority")) != prior_missing
        or artifact_document.get("grantedAuthority") != prior_missing
    ):
        raise AuthorityGateError(
            "authority artifact does not contain the exact current Goal/change grant"
        )

    identity = {
        "path": artifact["path"],
        "sha256": artifact["sha256"],
    }
    authority_digest = _canonical_sha256(
        {
            "schemaVersion": 1,
            "kind": "devflow-promoted-authority",
            "goalId": goal_id,
            "changeId": change_id,
            "gateKey": gate_key,
            "priorAuthorityContractSha256": prior_authority,
            "grantedAuthority": prior_missing,
            "authorityArtifact": identity,
        }
    )
    if authority_digest == prior_authority:
        raise AuthorityGateError("authority artifact did not change the authority contract")
    evidence_digest = _canonical_sha256(
        {
            "schemaVersion": 1,
            "kind": "devflow-authority-promotion-evidence",
            "goalId": goal_id,
            "changeId": change_id,
            "gateKey": gate_key,
            "priorReceiptSha256": receipt_sha256,
            "priorEvidenceSha256": prior_evidence,
            "authorityArtifact": identity,
        }
    )
    request_digest = _canonical_sha256(
        {
            "schemaVersion": 1,
            "kind": "devflow-authority-clearance-request",
            "gateKey": gate_key,
            "resumeStage": resume_stage,
            "authorityContractSha256": authority_digest,
            "evidenceSha256": evidence_digest,
            "authorityArtifact": identity,
        }
    )
    for expected, keys in (
        (authority_digest, ("authorityContractSha256", "authorityDigest")),
        (evidence_digest, ("evidenceSha256", "evidenceDigest")),
        (request_digest, ("requestSha256", "requestDigest")),
    ):
        supplied = [resolution.get(key) for key in keys if key in resolution]
        if supplied and any(_normalize_sha256(value) != expected for value in supplied):
            raise AuthorityGateError(
                "caller-supplied authority promotion digest does not match canonical evidence"
            )
    return {
        "authorityArtifactPath": str(artifact["path"]),
        "authorityArtifactSha256": str(artifact["sha256"]),
        "authorityContractSha256": authority_digest,
        "evidenceSha256": evidence_digest,
        "requestSha256": request_digest,
    }


def _load_authority_artifact(
    repo: Path,
    *,
    change_id: str,
    resolution: Mapping[str, Any],
) -> dict[str, Any]:
    raw_path = resolution.get("authorityArtifactPath")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise AuthorityGateError("authority promotion requires authorityArtifactPath")
    relative = Path(raw_path)
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or raw_path != relative.as_posix()
        or "\n" in raw_path
        or "\x00" in raw_path
    ):
        raise AuthorityGateError("authority artifact path is not exact and repository-relative")
    parts = relative.parts
    under_change = (
        len(parts) >= 4
        and parts[:2] == ("openspec", "changes")
        and parts[2] == change_id
    )
    active_ledger = parts == ("TASK_LEDGER.md",)
    if not under_change and not active_ledger:
        raise AuthorityGateError("authority artifact is outside the active change or ledger")

    cursor = repo
    final_stat = None
    try:
        for part in parts:
            cursor = cursor / part
            final_stat = cursor.lstat()
            if stat.S_ISLNK(final_stat.st_mode):
                raise AuthorityGateError("authority artifact path contains a symlink")
    except FileNotFoundError as error:
        raise AuthorityGateError("authority artifact is missing") from error
    except OSError as error:
        raise AuthorityGateError("authority artifact path cannot be trusted") from error
    if final_stat is None or not stat.S_ISREG(final_stat.st_mode):
        raise AuthorityGateError("authority artifact is not a regular file")
    try:
        artifact_bytes = cursor.read_bytes()
    except OSError as error:
        raise AuthorityGateError("authority artifact cannot be read") from error
    actual_sha256 = f"sha256:{hashlib.sha256(artifact_bytes).hexdigest()}"
    expected_sha256 = _normalize_sha256(resolution.get("authorityArtifactSha256"))
    if expected_sha256 != actual_sha256:
        raise AuthorityGateError("authority artifact SHA-256 does not match")
    document = _parse_authority_artifact(artifact_bytes, allow_fence=active_ledger)
    return {
        "path": relative.as_posix(),
        "sha256": actual_sha256,
        "document": document,
    }


def _parse_authority_artifact(
    artifact_bytes: bytes,
    *,
    allow_fence: bool,
) -> dict[str, Any]:
    try:
        text = artifact_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise AuthorityGateError("authority artifact is not UTF-8") from error
    try:
        value = json.loads(text, object_pairs_hook=_json_mapping_without_duplicate_keys)
    except (json.JSONDecodeError, ValueError):
        value = None
    if isinstance(value, dict):
        return value
    if not allow_fence:
        raise AuthorityGateError("authority artifact is not a structured JSON grant")
    blocks = re.findall(
        r"(?ms)^```devflow-authority-grant[ \t]*\r?\n(.*?)\r?\n```[ \t]*$",
        text,
    )
    if len(blocks) != 1:
        raise AuthorityGateError("TASK_LEDGER.md must contain one authority grant block")
    try:
        value = json.loads(
            blocks[0],
            object_pairs_hook=_json_mapping_without_duplicate_keys,
        )
    except (json.JSONDecodeError, ValueError) as error:
        raise AuthorityGateError("TASK_LEDGER.md authority grant block is invalid") from error
    if not isinstance(value, dict):
        raise AuthorityGateError("authority artifact grant must be a JSON object")
    return value


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _validated_gate_resolution(resolution: Mapping[str, Any]) -> dict[str, Any]:
    if str(resolution.get("decision") or "") != "AWAIT_HUMAN":
        raise AuthorityGateError("only AWAIT_HUMAN may create an authority gate")
    if resolution.get("materialDelta") is not True:
        raise AuthorityGateError("AWAIT_HUMAN requires a material authority delta")
    missing = _string_list(resolution.get("missingAuthority"))
    if not missing:
        raise AuthorityGateError("AWAIT_HUMAN requires concrete missing authority")
    reason_codes = _string_list(resolution.get("reasonCodes"))
    if not reason_codes:
        raise AuthorityGateError("AWAIT_HUMAN requires concrete reason codes")
    invalidations = _string_list(resolution.get("invalidations"))
    authority_digest = _required_digest_value(
        resolution, "authorityContractSha256", "authorityDigest"
    )
    evidence_digest = _required_digest_value(
        resolution, "evidenceSha256", "evidenceDigest"
    )
    request_digest = _required_digest_value(
        resolution, "requestSha256", "requestDigest"
    )
    standing_digest = _optional_digest_value(
        resolution, "standingContractSha256", "standingContractDigest"
    )
    gate_key = canonical_authority_gate_key_from_resolution(resolution)
    supplied_gate_key = _normalize_sha256(resolution.get("gateKey"))
    if supplied_gate_key != gate_key:
        raise AuthorityGateError(
            "authority gate key does not match the canonical authority inputs"
        )
    return {
        "gateKey": gate_key,
        "reasonCodes": reason_codes,
        "missingAuthority": missing,
        "invalidations": invalidations,
        "materialDelta": True,
        "authorityContractSha256": authority_digest,
        "evidenceSha256": evidence_digest,
        "requestSha256": request_digest,
        "standingContractDigest": standing_digest,
    }


def _string_list(value: Any) -> list[str]:
    """Require an exact canonical unique list without repairing caller input."""

    if not isinstance(value, list):
        raise AuthorityGateError("authority gate lists must be exact list[str] values")
    result: list[str] = []
    for item in value:
        if (
            not isinstance(item, str)
            or not item
            or item != item.strip()
            or item in result
        ):
            raise AuthorityGateError(
                "authority gate lists must contain unique non-empty trimmed strings"
            )
        result.append(item)
    return result


def _digest_value(resolution: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = str(resolution.get(key) or "")
        if re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}", value):
            return value if value.startswith("sha256:") else f"sha256:{value}"
    return "none"


def _normalize_sha256(value: object) -> str | None:
    match = SHA256_VALUE.fullmatch(str(value or ""))
    return f"sha256:{match.group(1)}" if match else None


def _optional_digest_value(resolution: Mapping[str, Any], *keys: str) -> str | None:
    present = [resolution.get(key) for key in keys if resolution.get(key) is not None]
    if not present:
        return None
    normalized = _normalize_sha256(present[0])
    if normalized in {None, f"sha256:{'0' * 64}"}:
        label = keys[0] if keys else "digest"
        raise AuthorityGateError(f"authority gate requires a valid optional {label}")
    if any(_normalize_sha256(value) != normalized for value in present[1:]):
        raise AuthorityGateError("authority gate standing contract digests disagree")
    return normalized


def canonical_authority_gate_key(
    *,
    missing_authority: list[str],
    authority_contract_sha256: str,
    evidence_sha256: str,
    request_sha256: str,
    standing_contract_sha256: str | None = None,
) -> str:
    missing = _string_list(missing_authority)
    if not missing:
        raise AuthorityGateError("canonical authority gate key requires missing authority")
    digests = (
        _normalize_sha256(authority_contract_sha256),
        _normalize_sha256(evidence_sha256),
        _normalize_sha256(request_sha256),
    )
    if any(value is None for value in digests):
        raise AuthorityGateError("canonical authority gate key requires three SHA-256 bindings")
    authority_digest, evidence_digest, request_digest = digests
    standing_digest = (
        _normalize_sha256(standing_contract_sha256)
        if standing_contract_sha256 is not None
        else None
    )
    if standing_contract_sha256 is not None and standing_digest is None:
        raise AuthorityGateError("canonical authority gate key has invalid standing contract digest")
    digest = canonical_authority_gate_digest(
        missing_authority=missing,
        request_digest=str(request_digest),
        authority_digest=str(authority_digest),
        evidence_digest=str(evidence_digest),
        standing_contract_digest=(
            str(standing_digest) if standing_digest is not None else None
        ),
    )
    return f"sha256:{digest}"


def canonical_authority_gate_key_from_resolution(
    resolution: Mapping[str, Any],
) -> str:
    """Compute a gate key from every canonical identity, including standing."""

    missing = _string_list(resolution.get("missingAuthority"))
    if not missing:
        raise AuthorityGateError("canonical authority gate key requires missing authority")
    reason_codes = _string_list(resolution.get("reasonCodes"))
    if not reason_codes:
        raise AuthorityGateError("canonical authority gate key requires reason codes")
    _string_list(resolution.get("invalidations"))
    authority_digest = _required_digest_value(
        resolution, "authorityContractSha256", "authorityDigest"
    )
    evidence_digest = _required_digest_value(
        resolution, "evidenceSha256", "evidenceDigest"
    )
    request_digest = _required_digest_value(
        resolution, "requestSha256", "requestDigest"
    )
    standing_digest = _optional_digest_value(
        resolution, "standingContractSha256", "standingContractDigest"
    )
    return canonical_authority_gate_key(
        missing_authority=missing,
        authority_contract_sha256=authority_digest,
        evidence_sha256=evidence_digest,
        request_sha256=request_digest,
        standing_contract_sha256=standing_digest,
    )


def _required_digest_value(resolution: Mapping[str, Any], *keys: str) -> str:
    value = _digest_value(resolution, *keys)
    if value in {"none", f"sha256:{'0' * 64}"}:
        label = keys[0] if keys else "digest"
        raise AuthorityGateError(f"authority gate requires a non-placeholder {label}")
    return value


def _resolution_digest(resolution: Mapping[str, Any]) -> str:
    return _digest_value(resolution, "requestSha256", "requestDigest")


def _receipt_path(repo: Path, gate_key: str) -> Path:
    if not SHA256_KEY.fullmatch(str(gate_key)):
        raise AuthorityGateError("invalid authority gate key")
    return devflow_root(repo) / "authority-gates" / f"{gate_key.removeprefix('sha256:')}.json"


def _read_existing_receipt(
    repo: Path,
    expected_path: Path,
    *,
    prior_receipt: Path | None,
) -> dict[str, Any] | None:
    if prior_receipt is not None:
        declared_path = Path(prior_receipt)
        if not declared_path.is_absolute():
            declared_path = repo / declared_path
        if declared_path.resolve() != expected_path.resolve():
            raise AuthorityGateError(
                "prior receipt path does not match the deterministic gate key"
            )
    if not expected_path.exists():
        if expected_path.is_symlink():
            raise AuthorityGateError("authority gate receipt path is untrusted")
        if prior_receipt is not None:
            raise AuthorityGateError("declared prior authority gate receipt is missing")
        return None
    if not trusted_repo_regular_file(repo, expected_path):
        raise AuthorityGateError("authority gate receipt path is untrusted")
    try:
        existing = json.loads(
            expected_path.read_text(),
            object_pairs_hook=_json_mapping_without_duplicate_keys,
        )
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise AuthorityGateError("existing authority gate receipt is unreadable") from error
    if not isinstance(existing, dict):
        raise AuthorityGateError("existing authority gate receipt is not a JSON object")
    return existing


def _is_pending_gate_intent(value: Mapping[str, Any]) -> bool:
    return (
        value.get("schemaVersion") == "1.0"
        and value.get("kind") == "devflow-authority-gate-write-ahead-intent"
        and value.get("status") == "pending"
    )


def _require_no_other_pending_gate_intent(repo: Path, expected_path: Path) -> None:
    root = expected_path.parent
    if not root.exists():
        return
    if root.is_symlink() or not root.is_dir():
        raise AuthorityGateError("authority gate receipt root is untrusted")
    for candidate in sorted(root.iterdir()):
        if candidate == expected_path or not re.fullmatch(
            r"[0-9a-f]{64}\.json", candidate.name
        ):
            continue
        if candidate.is_symlink() or not candidate.is_file():
            raise AuthorityGateError("authority gate receipt path is untrusted")
        try:
            value = json.loads(
                candidate.read_text(),
                object_pairs_hook=_json_mapping_without_duplicate_keys,
            )
        except (OSError, json.JSONDecodeError, ValueError) as error:
            raise AuthorityGateError(
                "existing authority gate receipt is unreadable"
            ) from error
        if isinstance(value, Mapping) and _is_pending_gate_intent(value):
            raise AuthorityGateError(
                "another pending authority gate intent must recover or fail closed first"
            )


def _require_matching_pending_intent(
    intent: Mapping[str, Any],
    expected_receipt: Mapping[str, Any],
) -> None:
    if set(intent) != {
        "schemaVersion",
        "kind",
        "status",
        "receipt",
        "expectedPreGateState",
    }:
        raise AuthorityGateError("pending authority gate intent fields are invalid")
    if intent.get("receipt") != expected_receipt:
        raise AuthorityGateError(
            "pending authority gate intent does not match this exact request"
        )
    identity = intent.get("expectedPreGateState")
    if not isinstance(identity, Mapping) or set(identity) != {
        "sha256",
        "currentStage",
        "changeId",
        "changeStatus",
        "goalId",
        "goalStatus",
        "authorityGateKey",
        "authorityGateStatus",
    }:
        raise AuthorityGateError("pending authority gate pre-state identity is invalid")
    if _normalize_sha256(identity.get("sha256")) != identity.get("sha256"):
        raise AuthorityGateError("pending authority gate pre-state SHA-256 is invalid")
    for key in (
        "currentStage",
        "changeId",
        "changeStatus",
        "goalId",
        "goalStatus",
        "authorityGateKey",
        "authorityGateStatus",
    ):
        value = identity.get(key)
        if not isinstance(value, str) or not value or value != value.strip():
            raise AuthorityGateError("pending authority gate pre-state fields are invalid")


def _current_state_and_identity(repo: Path) -> tuple[dict[str, Any], dict[str, str]]:
    path = devflow_root(repo) / "STATE.md"
    if not trusted_repo_regular_file(repo, path):
        raise AuthorityGateError("canonical DevFlow STATE is missing or untrusted")
    try:
        raw = path.read_bytes()
        state = parse_state_text(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError) as error:
        raise AuthorityGateError("canonical DevFlow STATE is unreadable") from error

    change = state.get("current_change")
    goal = state.get("goal_gate", {})
    gate = state.get("authority_gate", {})
    if not isinstance(change, Mapping):
        raise AuthorityGateError("canonical DevFlow STATE lacks change identity")
    if not isinstance(goal, Mapping):
        raise AuthorityGateError("canonical DevFlow STATE Goal identity is malformed")
    if not isinstance(gate, Mapping):
        raise AuthorityGateError("canonical DevFlow STATE authority gate is malformed")

    identity = {
        "sha256": f"sha256:{hashlib.sha256(raw).hexdigest()}",
        "currentStage": str(state.get("current_stage") or ""),
        "changeId": str(change.get("id") or "none"),
        "changeStatus": str(change.get("status") or "none"),
        "goalId": str(goal.get("id") or "none"),
        "goalStatus": str(goal.get("status") or "not_required"),
        "authorityGateKey": str(gate.get("key") or "none"),
        "authorityGateStatus": str(gate.get("status") or "inactive"),
    }
    if not identity["currentStage"]:
        raise AuthorityGateError("canonical DevFlow STATE Goal/change identity is incomplete")
    return state, identity


def _require_same_goal_change(
    state: Mapping[str, Any],
    pre_gate_identity: Mapping[str, Any],
) -> None:
    change = state.get("current_change")
    goal = state.get("goal_gate", {})
    if not isinstance(change, Mapping) or not isinstance(goal, Mapping):
        raise AuthorityGateError("active authority gate lacks valid Goal/change identity")
    if (
        str(change.get("id") or "") != pre_gate_identity.get("changeId")
        or str(goal.get("id") or "none") != pre_gate_identity.get("goalId")
        or str(goal.get("status") or "not_required")
        != pre_gate_identity.get("goalStatus")
    ):
        raise AuthorityGateError(
            "pending authority gate intent belongs to another Goal or change"
        )


def _require_gate_can_activate(state: Mapping[str, Any], gate_key: str) -> None:
    stage_awaiting = str(state.get("current_stage") or "") == "awaiting_human"
    change = state.get("current_change", {})
    status_awaiting = bool(
        isinstance(change, Mapping) and str(change.get("status") or "") == "awaiting_human"
    )
    if stage_awaiting != status_awaiting:
        raise AuthorityGateError("existing awaiting_human markers disagree")
    gate = state.get("authority_gate", {})
    if isinstance(gate, Mapping) and str(gate.get("status") or "") == "active":
        raise AuthorityGateError(
            "another active authority gate must be resolved before recording a new gate"
        )
    if (
        isinstance(gate, Mapping)
        and str(gate.get("status") or "") == "resolved"
        and str(gate.get("key") or "") == gate_key
    ):
        raise AuthorityGateError("resolved authority gate cannot replay a stale pending intent")
    if stage_awaiting:
        raise AuthorityGateError("awaiting_human state has no current authority gate receipt")


def _require_active_matching_state(state: Mapping[str, Any], gate_key: str) -> None:
    change = state.get("current_change", {})
    gate = state.get("authority_gate", {})
    if not (
        str(state.get("current_stage") or "") == "awaiting_human"
        and isinstance(change, Mapping)
        and str(change.get("status") or "") == "awaiting_human"
        and isinstance(gate, Mapping)
        and str(gate.get("status") or "") == "active"
        and str(gate.get("key") or "") == gate_key
    ):
        raise AuthorityGateError("authority gate state is not active for this gate key")


def _require_trusted_active_receipt(
    repo: Path,
    state: Mapping[str, Any],
    gate_key: str,
    receipt: Mapping[str, Any],
) -> None:
    gate = state.get("authority_gate", {})
    if not isinstance(gate, Mapping):
        raise AuthorityGateError("authority gate state mapping is missing")
    if (
        receipt.get("schemaVersion") != "1.0"
        or receipt.get("kind") != "devflow-authority-gate-receipt"
        or receipt.get("status") != "recorded"
        or receipt.get("decision") != "AWAIT_HUMAN"
        or receipt.get("materialDelta") is not True
    ):
        raise AuthorityGateError("authority gate receipt classification is invalid")
    reasons = _string_list(receipt.get("reasonCodes"))
    missing = _string_list(receipt.get("missingAuthority"))
    invalidations = _string_list(receipt.get("invalidations"))
    if not reasons or reasons != receipt.get("reasonCodes"):
        raise AuthorityGateError("authority gate receipt reason codes are invalid")
    if not missing or missing != receipt.get("missingAuthority"):
        raise AuthorityGateError("authority gate receipt missing authority is invalid")
    if invalidations != receipt.get("invalidations"):
        raise AuthorityGateError("authority gate receipt invalidations are invalid")
    authority_digest = _required_digest_value(receipt, "authorityContractSha256")
    evidence_digest = _required_digest_value(receipt, "evidenceSha256")
    request_digest = _required_digest_value(receipt, "requestSha256")
    expected_gate_key = canonical_authority_gate_key_from_resolution(receipt)
    if gate_key != expected_gate_key or receipt.get("gateKey") != expected_gate_key:
        raise AuthorityGateError("authority gate receipt key is not canonical")
    if gate.get("missing_authority") != missing:
        raise AuthorityGateError("authority gate receipt missing authority does not match state")
    if _normalize_sha256(gate.get("resolution_digest")) != request_digest:
        raise AuthorityGateError("authority gate request digest does not match state")
    if _normalize_sha256(gate.get("evidence_digest")) != evidence_digest:
        raise AuthorityGateError("authority gate evidence digest does not match state")
    question = receipt.get("nextQuestion")
    if (
        not isinstance(question, str)
        or not question.strip()
        or "\n" in question
        or gate.get("next_question") != question
    ):
        raise AuthorityGateError("authority gate next question does not match state")
    receipt_path = _receipt_path(repo, gate_key)
    if receipt.get("receiptPath") != rel(repo, receipt_path):
        raise AuthorityGateError("authority gate receipt path does not match its key")


def _json_mapping_without_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result
