from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workflow_planning_paths import devflow_root, guard_devflow_write
from workflow_state import parse_state


CONTRACT_VERSION = "1.0"
EVALUATOR_VERSION = "1.0"

IMPLEMENTATION_PROVIDER_REQUIRED = "IMPLEMENTATION_PROVIDER_REQUIRED"
IMPLEMENTATION_PROVIDER_NOT_READY = "IMPLEMENTATION_PROVIDER_NOT_READY"
IMPLEMENTATION_PROVIDER_READY = "IMPLEMENTATION_PROVIDER_READY"

REQUIREMENT_KIND = "ImplementationReadinessRequirement"
EVIDENCE_KIND = "ImplementationReadinessEvidence"
RECEIPT_KIND = "ImplementationReadinessReceipt"
OVERRIDE_KIND = "ImplementationProviderOverride"
SAFE_CHANGE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")

NON_SEMANTIC_PLAN_KEYS = frozenset(
    {
        "checked",
        "completed",
        "diagnosticPath",
        "diagnosticPaths",
        "evidencePath",
        "evidencePaths",
        "progress",
        "timestamp",
        "timestamps",
        "updatedAt",
    }
)

ISSUE_PRIORITY = (
    "REQUIREMENT_SCHEMA_UNSUPPORTED",
    "REQUIREMENT_INVALID",
    "REQUIREMENT_DIGEST_MISMATCH",
    "EVIDENCE_SCHEMA_UNSUPPORTED",
    "EVIDENCE_INVALID",
    "EVIDENCE_DIGEST_MISMATCH",
    "EVIDENCE_REQUIREMENT_MISMATCH",
    "PROVIDER_IDENTITY_MISMATCH",
    "CONSUMER_IDENTITY_MISMATCH",
    "CONSUMER_REVISION_MISMATCH",
    "ACTIVE_CHANGE_MISMATCH",
    "SEMANTIC_PLAN_MISMATCH",
    "TARGET_PROFILE_MISMATCH",
    "CAPABILITY_SET_MISMATCH",
    "CAPABILITY_NOT_PASSED",
    "CAPABILITY_RECEIPT_MISSING",
    "REQUIRED_LIMITATION_MISSING",
    "EVIDENCE_STALE",
    "PROVIDER_OVERRIDE_INVALID",
    "ACTIVE_CONTEXT_UNAVAILABLE",
)

NEXT_ACTIONS = {
    "REQUIREMENT_SCHEMA_UNSUPPORTED": "replace-requirement-with-supported-v1",
    "REQUIREMENT_INVALID": "repair-current-requirement",
    "REQUIREMENT_DIGEST_MISMATCH": "re-promote-current-requirement",
    "EVIDENCE_SCHEMA_UNSUPPORTED": "request-supported-v1-evidence",
    "EVIDENCE_INVALID": "request-complete-project-bound-evidence",
    "EVIDENCE_DIGEST_MISMATCH": "request-content-addressed-evidence",
    "EVIDENCE_REQUIREMENT_MISMATCH": "request-evidence-for-current-requirement",
    "PROVIDER_IDENTITY_MISMATCH": "request-evidence-from-selected-provider",
    "CONSUMER_IDENTITY_MISMATCH": "request-evidence-for-current-consumer",
    "CONSUMER_REVISION_MISMATCH": "request-evidence-for-current-consumer-revision",
    "ACTIVE_CHANGE_MISMATCH": "request-evidence-for-active-change",
    "SEMANTIC_PLAN_MISMATCH": "request-evidence-for-current-semantic-plan",
    "TARGET_PROFILE_MISMATCH": "request-evidence-for-selected-target-profile",
    "CAPABILITY_SET_MISMATCH": "request-exact-required-capability-set",
    "CAPABILITY_NOT_PASSED": "remediate-failing-required-capability",
    "CAPABILITY_RECEIPT_MISSING": "request-immutable-capability-receipts",
    "REQUIRED_LIMITATION_MISSING": "record-all-required-limitations",
    "EVIDENCE_STALE": "refresh-project-bound-evidence",
    "PROVIDER_OVERRIDE_INVALID": "repair-named-human-provider-override",
    "ACTIVE_CONTEXT_UNAVAILABLE": "restore-current-consumer-context",
}


class ReadinessError(RuntimeError):
    def __init__(self, code: str, message: str, *, path: Path | None = None):
        super().__init__(message)
        self.code = code
        self.path = path


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def canonical_digest(value: Any) -> str:
    payload = canonical_json(value).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def plan_semantic_digest(value: Any) -> str:
    return canonical_digest(_strip_non_semantic_plan_fields(value))


def _strip_non_semantic_plan_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_non_semantic_plan_fields(item)
            for key, item in sorted(value.items())
            if key not in NON_SEMANTIC_PLAN_KEYS
        }
    if isinstance(value, list):
        return [_strip_non_semantic_plan_fields(item) for item in value]
    return value


def seal_requirement(requirement: dict[str, Any]) -> dict[str, Any]:
    sealed = copy.deepcopy(requirement)
    sealed.pop("semanticInputDigest", None)
    sealed["semanticInputDigest"] = canonical_digest(sealed)
    return sealed


def seal_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    sealed = copy.deepcopy(evidence)
    sealed.pop("evidenceDigest", None)
    sealed["evidenceDigest"] = canonical_digest(sealed)
    return sealed


def seal_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    sealed = copy.deepcopy(receipt)
    sealed.pop("receiptDigest", None)
    digest_input = copy.deepcopy(sealed)
    digest_input.pop("recordedAt", None)
    sealed["receiptDigest"] = canonical_digest(digest_input)
    return sealed


def seal_provider_override(override: dict[str, Any]) -> dict[str, Any]:
    sealed = copy.deepcopy(override)
    sealed.pop("overrideDigest", None)
    sealed["overrideDigest"] = canonical_digest(sealed)
    return sealed


def build_ready_receipt(report: dict[str, Any], *, recorded_at: str) -> dict[str, Any]:
    if report.get("state") != IMPLEMENTATION_PROVIDER_READY or not report.get("ready"):
        raise ReadinessError("readiness_not_ready", "A Ready report is required before writing a receipt")
    bindings = report.get("bindings")
    if not isinstance(bindings, dict) or not bindings:
        raise ReadinessError("readiness_bindings_missing", "The Ready report has no semantic bindings")
    if _parse_time(recorded_at) is None:
        raise ReadinessError("invalid_recorded_at", "Receipt recordedAt must be an offset-aware timestamp")
    return seal_receipt(
        {
            "schemaVersion": CONTRACT_VERSION,
            "kind": RECEIPT_KIND,
            "evaluatorVersion": EVALUATOR_VERSION,
            "state": IMPLEMENTATION_PROVIDER_READY,
            "bindings": copy.deepcopy(bindings),
            "issueCodes": [],
            "nextAction": "continue-with-ordinary-implementation-authority",
            "recordedAt": recorded_at,
        }
    )


def receipt_is_current(receipt: dict[str, Any], report: dict[str, Any]) -> bool:
    if not _valid_receipt_shape(receipt):
        return False
    if receipt.get("schemaVersion") != CONTRACT_VERSION or receipt.get("kind") != RECEIPT_KIND:
        return False
    if receipt.get("evaluatorVersion") != EVALUATOR_VERSION:
        return False
    if receipt.get("state") != IMPLEMENTATION_PROVIDER_READY or receipt.get("issueCodes") != []:
        return False
    if receipt.get("receiptDigest") != seal_receipt(receipt).get("receiptDigest"):
        return False
    return bool(
        report.get("state") == IMPLEMENTATION_PROVIDER_READY
        and report.get("ready")
        and receipt.get("bindings") == report.get("bindings")
    )


def promote_requirement(
    repo: Path,
    change_id: str,
    requirement: dict[str, Any],
    active_context: dict[str, Any],
) -> dict[str, Any]:
    plan = plan_requirement_promotion(repo, change_id, requirement, active_context)
    repo = Path(repo).resolve()
    path = Path(plan["path"])
    history_path = Path(plan["historyPath"])
    _create_json_once(repo, history_path, requirement, conflict_code="requirement_history_conflict")
    supersedes = plan.get("supersedesDigest")
    if supersedes:
        status = _replace_current_requirement(
            repo,
            path,
            requirement,
            expected_digest=str(supersedes),
        )
    else:
        status = _create_json_once(repo, path, requirement, conflict_code="requirement_conflict")
    return {**plan, "status": status}


def plan_requirement_promotion(
    repo: Path,
    change_id: str,
    requirement: dict[str, Any],
    active_context: dict[str, Any],
) -> dict[str, Any]:
    repo = Path(repo).resolve()
    root = readiness_change_root(repo, change_id)
    path = root / "requirement.json"
    _assert_trusted_write_path(repo, path)
    if requirement.get("schemaVersion") != CONTRACT_VERSION or requirement.get("kind") != REQUIREMENT_KIND:
        raise ReadinessError("requirement_schema_unsupported", "Only Requirement v1 can be promoted")
    if _validate_requirement(requirement):
        raise ReadinessError("requirement_invalid", "The Requirement is incomplete")
    if requirement.get("semanticInputDigest") != seal_requirement(requirement).get("semanticInputDigest"):
        raise ReadinessError("requirement_digest_mismatch", "The Requirement digest is not current")
    _assert_approved_active_plan(repo, change_id)
    _assert_requirement_context(change_id, requirement, active_context)
    trusted_context = active_context_from_repo(
        repo,
        change_id,
        project_id=str(requirement.get("consumer", {}).get("projectId") or ""),
        target_profile=copy.deepcopy(requirement.get("targetProfile", {})),
        evaluated_at=str(active_context.get("evaluatedAt") or _now_text()),
    )
    _assert_requirement_context(change_id, requirement, trusted_context)
    history_path = root / "requirements" / (
        f"requirement-{str(requirement['semanticInputDigest']).removeprefix('sha256:')}.json"
    )
    _assert_trusted_write_path(repo, history_path)
    supersedes_digest: str | None = None
    current, current_issue = _read_json_document(repo, path)
    if current_issue:
        raise ReadinessError("requirement_conflict", "The current Requirement is unreadable or untrusted")
    if current is not None and canonical_json(current) != canonical_json(requirement):
        if (
            current.get("schemaVersion") != CONTRACT_VERSION
            or current.get("kind") != REQUIREMENT_KIND
            or _validate_requirement(current)
            or current.get("semanticInputDigest")
            != seal_requirement(current).get("semanticInputDigest")
        ):
            raise ReadinessError(
                "requirement_conflict",
                "The current Requirement is invalid and cannot authorize replacement",
            )
        evidence, evidence_issue = _read_json_document(repo, root / "evidence.json")
        current_context = copy.deepcopy(active_context)
        current_context["targetProfile"] = copy.deepcopy(current.get("targetProfile"))
        report = evaluate(current, evidence if not evidence_issue else None, current_context)
        current_receipt, _ = _current_receipt(repo, root, report)
        override, override_issue = _current_provider_override(
            repo,
            root,
            requirement=current,
            active_context=current_context,
            current_receipt=current_receipt,
        )
        if override_issue or override is None:
            raise ReadinessError(
                "requirement_conflict",
                "A different current Requirement requires a valid named-human provider override",
            )
        if requirement.get("provider", {}).get("id") != override.get("newProviderId"):
            raise ReadinessError(
                "provider_override_target_mismatch",
                "The replacement Requirement does not select the override target",
            )
        supersedes_digest = str(current.get("semanticInputDigest") or "")
    return {
        "ok": True,
        "status": "planned",
        "path": str(path),
        "historyPath": str(history_path),
        "requirementDigest": requirement["semanticInputDigest"],
        "supersedesDigest": supersedes_digest,
    }


def inspect_readiness(
    repo: Path,
    change_id: str,
    *,
    active_context: dict[str, Any],
) -> dict[str, Any]:
    repo = Path(repo).resolve()
    root = readiness_change_root(repo, change_id)
    base = root.parent
    try:
        applicable = _readiness_is_applicable(repo, change_id)
    except ReadinessError as error:
        report = _not_ready(["READINESS_APPLICABILITY_INVALID"])
        return _inspection_result(change_id, root, report, False, None, [error.code])
    if not applicable and not (base.is_symlink() if _path_lexists(base) else False):
        return {
            "applicable": False,
            "changeId": change_id,
            "root": str(root),
            "report": None,
            "receiptCurrent": False,
            "receiptPath": None,
            "issues": [],
        }
    try:
        _assert_trusted_existing_path(repo, root, allow_missing=True)
    except ReadinessError as error:
        report = _not_ready(["READINESS_PATH_UNTRUSTED"])
        return _inspection_result(change_id, root, report, False, None, [error.code])

    requirement, requirement_issue = _read_json_document(repo, root / "requirement.json")
    evidence, evidence_issue = _read_json_document(repo, root / "evidence.json")
    if requirement_issue:
        report = _not_ready(["REQUIREMENT_INVALID"])
    elif evidence_issue:
        report = _not_ready(["EVIDENCE_INVALID"])
    else:
        report = evaluate(requirement, evidence, active_context)

    receipt, receipt_path = _current_receipt(repo, root, report)
    receipt_current = receipt is not None
    override, override_issue = _current_provider_override(
        repo,
        root,
        requirement=requirement,
        active_context=active_context,
        current_receipt=receipt,
    )
    if override_issue:
        report = _not_ready(["PROVIDER_OVERRIDE_INVALID"])
        receipt_current = False
    elif override is not None:
        report = _required(
            "PROVIDER_OVERRIDE_REASSESSMENT_REQUIRED",
            "reassess-provider-direction-and-promote-new-requirement",
        )
        receipt_current = False

    issues = [issue for issue in (requirement_issue, evidence_issue, override_issue) if issue]
    return _inspection_result(change_id, root, report, receipt_current, receipt_path, issues)


def inspect_repository_readiness(
    repo: Path,
    change_id: str | None = None,
    *,
    evaluated_at: str | None = None,
) -> dict[str, Any]:
    repo = Path(repo).resolve()
    try:
        selected_change = change_id or _active_change_id(repo)
    except ReadinessError as error:
        base = devflow_root(repo) / "implementation-readiness"
        if not _path_lexists(base):
            return {
                "applicable": False,
                "changeId": None,
                "root": str(base),
                "report": None,
                "receiptCurrent": False,
                "receiptPath": None,
                "issues": [],
            }
        report = _not_ready(["ACTIVE_CONTEXT_UNAVAILABLE"])
        return _inspection_result("unknown", base, report, False, None, [error.code])
    root = readiness_change_root(repo, selected_change)
    requirement, requirement_issue = _read_json_document(repo, root / "requirement.json")
    if requirement_issue:
        report = _not_ready(["REQUIREMENT_INVALID"])
        return _inspection_result(selected_change, root, report, False, None, [requirement_issue])
    if requirement is None:
        context = {
            "consumer": {},
            "activeChange": {"id": selected_change, "semanticPlanDigest": canonical_digest({})},
            "targetProfile": {},
            "evaluatedAt": evaluated_at or _now_text(),
        }
        return inspect_readiness(repo, selected_change, active_context=context)
    try:
        context = active_context_from_repo(
            repo,
            selected_change,
            project_id=str(requirement.get("consumer", {}).get("projectId") or ""),
            target_profile=copy.deepcopy(requirement.get("targetProfile", {})),
            evaluated_at=evaluated_at,
        )
    except ReadinessError as error:
        report = _not_ready(["ACTIVE_CONTEXT_UNAVAILABLE"])
        return _inspection_result(selected_change, root, report, False, None, [error.code])
    return inspect_readiness(repo, selected_change, active_context=context)


def load_canonical_requirement(repo: Path, change_id: str) -> dict[str, Any]:
    repo = Path(repo).resolve()
    requirement, issue = _read_json_document(
        repo,
        readiness_change_root(repo, change_id) / "requirement.json",
    )
    if issue or requirement is None:
        raise ReadinessError(
            "requirement_missing_or_untrusted",
            "The canonical Requirement is missing, invalid, or untrusted",
        )
    return requirement


def repository_mutation_gate(
    repo: Path,
    *,
    ordinary_authority: bool,
    change_id: str | None = None,
    evaluated_at: str | None = None,
) -> dict[str, Any]:
    repo = Path(repo).resolve()
    try:
        selected_change = change_id or _active_change_id(repo)
    except ReadinessError as error:
        base = devflow_root(repo) / "implementation-readiness"
        if not _path_lexists(base) and not _state_requires_readiness(repo):
            issues = [] if ordinary_authority else ["ORDINARY_IMPLEMENTATION_AUTHORITY_REQUIRED"]
            return {
                "applicable": False,
                "allowed": ordinary_authority,
                "readinessState": None,
                "receiptCurrent": False,
                "ordinaryAuthority": ordinary_authority,
                "issueCodes": issues,
                "nextAction": (
                    "continue-with-ordinary-implementation-authority"
                    if ordinary_authority
                    else "resolve-ordinary-implementation-authority"
                ),
            }
        return {
            "applicable": True,
            "allowed": False,
            "readinessState": IMPLEMENTATION_PROVIDER_NOT_READY,
            "receiptCurrent": False,
            "ordinaryAuthority": ordinary_authority,
            "issueCodes": ["ACTIVE_CONTEXT_UNAVAILABLE"],
            "nextAction": NEXT_ACTIONS["ACTIVE_CONTEXT_UNAVAILABLE"],
            "inspection": {"applicable": True, "issues": [error.code]},
        }
    inspection = inspect_repository_readiness(repo, selected_change, evaluated_at=evaluated_at)
    if not inspection["applicable"]:
        issues = [] if ordinary_authority else ["ORDINARY_IMPLEMENTATION_AUTHORITY_REQUIRED"]
        return {
            "applicable": False,
            "allowed": ordinary_authority,
            "readinessState": None,
            "receiptCurrent": False,
            "ordinaryAuthority": ordinary_authority,
            "issueCodes": issues,
            "nextAction": (
                "continue-with-ordinary-implementation-authority"
                if ordinary_authority
                else "resolve-ordinary-implementation-authority"
            ),
        }
    requirement, issue = _read_json_document(repo, readiness_change_root(repo, selected_change) / "requirement.json")
    if issue or requirement is None:
        report = inspection["report"]
        return {
            "applicable": True,
            "allowed": False,
            "readinessState": report.get("state"),
            "receiptCurrent": False,
            "ordinaryAuthority": ordinary_authority,
            "issueCodes": list(report.get("issueCodes", [])),
            "nextAction": report.get("nextAction"),
            "inspection": inspection,
        }
    try:
        context = active_context_from_repo(
            repo,
            selected_change,
            project_id=str(requirement["consumer"]["projectId"]),
            target_profile=copy.deepcopy(requirement["targetProfile"]),
            evaluated_at=evaluated_at,
        )
    except (KeyError, TypeError, ReadinessError):
        report = inspection["report"]
        return {
            "applicable": True,
            "allowed": False,
            "readinessState": report.get("state"),
            "receiptCurrent": False,
            "ordinaryAuthority": ordinary_authority,
            "issueCodes": list(report.get("issueCodes", [])),
            "nextAction": report.get("nextAction"),
            "inspection": inspection,
        }
    return mutation_gate(
        repo,
        selected_change,
        ordinary_authority=ordinary_authority,
        active_context=context,
    )


def active_context_from_repo(
    repo: Path,
    change_id: str,
    *,
    project_id: str,
    target_profile: dict[str, Any],
    evaluated_at: str | None = None,
) -> dict[str, Any]:
    repo = Path(repo).resolve()
    active_change = _active_change_id(repo)
    if active_change != change_id:
        raise ReadinessError("active_change_mismatch", "Requested readiness change is not the active change")
    if not project_id:
        raise ReadinessError("consumer_identity_missing", "Consumer project id is missing")
    return {
        "consumer": {
            "projectId": project_id,
            "rootIdentity": consumer_root_identity(repo),
            "revision": consumer_revision(repo),
        },
        "activeChange": {
            "id": change_id,
            "semanticPlanDigest": semantic_plan_digest_from_repo(repo, change_id),
        },
        "targetProfile": copy.deepcopy(target_profile),
        "evaluatedAt": evaluated_at or _now_text(),
    }


def consumer_root_identity(repo: Path) -> str:
    root = Path(repo).resolve()
    return canonical_digest({"kind": "resolved-project-root", "path": root.as_posix()})


def consumer_revision(repo: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=Path(repo).resolve(),
        text=True,
        capture_output=True,
        check=False,
    )
    revision = result.stdout.strip()
    if result.returncode != 0 or not re.fullmatch(r"[0-9a-fA-F]{40,64}", revision):
        raise ReadinessError("consumer_revision_unavailable", "Consumer Git revision is unavailable")
    return f"git:{revision.lower()}"


def semantic_plan_digest_from_repo(repo: Path, change_id: str) -> str:
    repo = Path(repo).resolve()
    change_root = repo / "openspec" / "changes" / change_id
    _assert_trusted_existing_path(repo, change_root)
    paths = [change_root / "proposal.md", change_root / "design.md", change_root / "tasks.md"]
    paths.extend(sorted((change_root / "specs").rglob("spec.md")))
    if not all(_path_lexists(path) for path in paths[:3]) or len(paths) < 4:
        raise ReadinessError("semantic_plan_incomplete", "Active OpenSpec semantic plan is incomplete")
    semantic_files: dict[str, str] = {}
    for path in paths:
        _assert_trusted_existing_path(repo, path)
        try:
            text = path.read_text()
        except (OSError, UnicodeError) as error:
            raise ReadinessError(
                "semantic_plan_unreadable",
                "Active OpenSpec semantic plan is unreadable",
                path=path,
            ) from error
        relative = path.relative_to(change_root).as_posix()
        semantic_files[relative] = _normalize_semantic_plan_text(text, tasks=path.name == "tasks.md")
    return canonical_digest(semantic_files)


def _normalize_semantic_plan_text(text: str, *, tasks: bool) -> str:
    lines: list[str] = []
    for raw_line in text.replace("\r\n", "\n").splitlines():
        line = raw_line.rstrip()
        if re.match(r"^\s*(?:[-*]\s+)?(?:updated(?: at)?|timestamp|evidence(?: path)?):", line, re.IGNORECASE):
            continue
        if tasks:
            line = re.sub(r"^(\s*[-+*]\s+)\[[ xX]\]", r"\1[ ]", line)
        lines.append(line)
    return "\n".join(lines).strip() + "\n"


def _active_change_id(repo: Path) -> str:
    change_id = str(parse_state(Path(repo).resolve()).get("current_change", {}).get("id") or "")
    if not SAFE_CHANGE_ID.fullmatch(change_id):
        raise ReadinessError("active_change_missing", "DevFlow state has no path-safe active change")
    return change_id


def _state_requires_readiness(repo: Path) -> bool:
    state = parse_state(Path(repo).resolve())
    readiness = state.get("implementation_readiness")
    if readiness is None:
        return False
    if not isinstance(readiness, dict) or set(readiness) - {"required"}:
        raise ReadinessError(
            "readiness_applicability_invalid",
            "DevFlow state has an invalid implementation_readiness section",
        )
    required = readiness.get("required")
    if not isinstance(required, bool):
        raise ReadinessError(
            "readiness_applicability_invalid",
            "DevFlow state implementation_readiness.required must be boolean",
        )
    return required


def _readiness_is_applicable(repo: Path, change_id: str) -> bool:
    repo = Path(repo).resolve()
    root = readiness_change_root(repo, change_id)
    state = parse_state(repo)
    readiness = state.get("implementation_readiness")
    if readiness is None:
        return _path_lexists(root)
    required = _state_requires_readiness(repo)
    active_change = str(state.get("current_change", {}).get("id") or "")
    if required and active_change != change_id:
        raise ReadinessError(
            "active_change_mismatch",
            "Implementation readiness is required only for the current active change",
        )
    if not required and _path_lexists(root):
        raise ReadinessError(
            "readiness_applicability_conflict",
            "Readiness artifacts exist while DevFlow state marks the gate not required",
        )
    return required


def _assert_approved_active_plan(repo: Path, change_id: str) -> None:
    state = parse_state(Path(repo).resolve())
    change = state.get("current_change")
    gates = state.get("gates")
    if (
        not isinstance(change, dict)
        or change.get("id") != change_id
        or not isinstance(gates, dict)
        or gates.get("spec_approved") is not True
        or gates.get("plan_written") is not True
        or not _state_requires_readiness(repo)
    ):
        raise ReadinessError(
            "approved_active_plan_required",
            "Requirement promotion requires an approved active plan that explicitly requires implementation readiness",
        )


def _now_text() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_ready_receipt(
    repo: Path,
    change_id: str,
    report: dict[str, Any],
    *,
    recorded_at: str,
) -> dict[str, Any]:
    repo = Path(repo).resolve()
    root = readiness_change_root(repo, change_id)
    receipt = build_ready_receipt(report, recorded_at=recorded_at)
    digest = str(receipt["receiptDigest"])
    path = root / "receipts" / f"receipt-{digest.removeprefix('sha256:')}.json"
    _assert_trusted_write_path(repo, path)
    if _path_lexists(path):
        existing, issue = _read_json_document(repo, path)
        if issue or existing is None or not receipt_is_current(existing, report):
            raise ReadinessError(
                "receipt_conflict",
                "A different or invalid receipt already owns the digest path",
                path=path,
            )
        return {"ok": True, "status": "existing", "path": str(path), "receiptDigest": digest}
    status = _create_json_once(repo, path, receipt, conflict_code="receipt_conflict")
    return {"ok": True, "status": status, "path": str(path), "receiptDigest": digest}


def plan_ready_receipt(
    repo: Path,
    change_id: str,
    report: dict[str, Any],
    *,
    recorded_at: str,
) -> dict[str, Any]:
    repo = Path(repo).resolve()
    receipt = build_ready_receipt(report, recorded_at=recorded_at)
    digest = str(receipt["receiptDigest"])
    path = readiness_change_root(repo, change_id) / "receipts" / f"receipt-{digest.removeprefix('sha256:')}.json"
    _assert_trusted_write_path(repo, path)
    return {
        "ok": True,
        "status": "planned",
        "path": str(path),
        "receiptDigest": digest,
        "receipt": receipt,
    }


def record_provider_override(
    repo: Path,
    change_id: str,
    override: dict[str, Any],
    active_context: dict[str, Any],
) -> dict[str, Any]:
    plan = plan_provider_override(repo, change_id, override, active_context)
    path = Path(plan["path"])
    status = _create_json_once(Path(repo).resolve(), path, override, conflict_code="provider_override_conflict")
    return {**plan, "status": status}


def plan_provider_override(
    repo: Path,
    change_id: str,
    override: dict[str, Any],
    active_context: dict[str, Any],
) -> dict[str, Any]:
    repo = Path(repo).resolve()
    root = readiness_change_root(repo, change_id)
    requirement, requirement_issue = _read_json_document(repo, root / "requirement.json")
    if requirement_issue or requirement is None:
        raise ReadinessError("requirement_missing", "A current Requirement is required before override")
    report = evaluate(requirement, None, active_context)
    current_receipt, _ = _current_receipt(repo, root, report)
    if current_receipt is None:
        evidence, evidence_issue = _read_json_document(repo, root / "evidence.json")
        if not evidence_issue:
            current_report = evaluate(requirement, evidence, active_context)
            current_receipt, _ = _current_receipt(repo, root, current_report)
    status = _provider_override_status(
        override,
        requirement=requirement,
        active_context=active_context,
        current_receipt=current_receipt,
    )
    if status != "current":
        raise ReadinessError("provider_override_invalid", "Provider override is not current and complete")
    existing_override, existing_issue = _current_provider_override(
        repo,
        root,
        requirement=requirement,
        active_context=active_context,
        current_receipt=current_receipt,
    )
    if existing_issue:
        raise ReadinessError("provider_override_invalid", "Existing provider override state is invalid")
    if (
        existing_override is not None
        and existing_override.get("overrideDigest") != override.get("overrideDigest")
    ):
        raise ReadinessError(
            "provider_override_conflict",
            "A different current provider override already requires reassessment",
        )
    path = root / "overrides" / (
        f"override-{str(override['overrideDigest']).removeprefix('sha256:')}.json"
    )
    _assert_trusted_write_path(repo, path)
    return {
        "ok": True,
        "status": "planned",
        "path": str(path),
        "overrideDigest": override["overrideDigest"],
    }


def mutation_gate(
    repo: Path,
    change_id: str,
    *,
    ordinary_authority: bool,
    active_context: dict[str, Any],
) -> dict[str, Any]:
    inspection = inspect_readiness(repo, change_id, active_context=active_context)
    if not inspection["applicable"]:
        issues = [] if ordinary_authority else ["ORDINARY_IMPLEMENTATION_AUTHORITY_REQUIRED"]
        return {
            "applicable": False,
            "allowed": ordinary_authority,
            "readinessState": None,
            "receiptCurrent": False,
            "ordinaryAuthority": ordinary_authority,
            "issueCodes": issues,
            "nextAction": (
                "continue-with-ordinary-implementation-authority"
                if ordinary_authority
                else "resolve-ordinary-implementation-authority"
            ),
        }

    report = inspection["report"]
    issues = list(report.get("issueCodes", []))
    if report.get("state") == IMPLEMENTATION_PROVIDER_READY and not inspection["receiptCurrent"]:
        issues.append("READINESS_RECEIPT_MISSING")
    if not ordinary_authority:
        issues.append("ORDINARY_IMPLEMENTATION_AUTHORITY_REQUIRED")
    allowed = bool(
        report.get("state") == IMPLEMENTATION_PROVIDER_READY
        and inspection["receiptCurrent"]
        and ordinary_authority
    )
    next_action = report.get("nextAction")
    if "READINESS_RECEIPT_MISSING" in issues:
        next_action = "write-current-readiness-receipt"
    if report.get("state") == IMPLEMENTATION_PROVIDER_READY and not ordinary_authority:
        next_action = "resolve-ordinary-implementation-authority"
    return {
        "applicable": True,
        "allowed": allowed,
        "readinessState": report.get("state"),
        "receiptCurrent": bool(inspection["receiptCurrent"]),
        "ordinaryAuthority": ordinary_authority,
        "issueCodes": list(dict.fromkeys(issues)),
        "nextAction": next_action,
        "inspection": inspection,
    }


def readiness_change_root(repo: Path, change_id: str) -> Path:
    if not isinstance(change_id, str) or not SAFE_CHANGE_ID.fullmatch(change_id):
        raise ReadinessError("invalid_change_id", "Readiness change id is not path safe")
    return devflow_root(Path(repo).resolve()) / "implementation-readiness" / change_id


def _inspection_result(
    change_id: str,
    root: Path,
    report: dict[str, Any],
    receipt_current: bool,
    receipt_path: Path | None,
    issues: list[str],
) -> dict[str, Any]:
    return {
        "applicable": True,
        "changeId": change_id,
        "root": str(root),
        "report": report,
        "receiptCurrent": receipt_current,
        "receiptPath": str(receipt_path) if receipt_path else None,
        "issues": issues,
    }


def _current_receipt(
    repo: Path,
    root: Path,
    report: dict[str, Any],
) -> tuple[dict[str, Any] | None, Path | None]:
    receipts = root / "receipts"
    if not _path_lexists(receipts):
        return None, None
    try:
        _assert_trusted_existing_path(repo, receipts)
    except ReadinessError:
        return None, None
    current: list[tuple[dict[str, Any], Path]] = []
    for path in sorted(receipts.glob("receipt-*.json")):
        receipt, issue = _read_json_document(repo, path)
        if issue or receipt is None:
            continue
        if receipt_is_current(receipt, report):
            current.append((receipt, path))
    if len(current) != 1:
        return None, None
    return current[0]


def _current_provider_override(
    repo: Path,
    root: Path,
    *,
    requirement: dict[str, Any] | None,
    active_context: dict[str, Any],
    current_receipt: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, str | None]:
    paths: list[Path] = []
    legacy = root / "provider-override.json"
    if _path_lexists(legacy):
        paths.append(legacy)
    override_root = root / "overrides"
    if _path_lexists(override_root):
        try:
            _assert_trusted_existing_path(repo, override_root)
        except ReadinessError:
            return None, "provider_override_untrusted"
        paths.extend(sorted(override_root.glob("override-*.json")))
    current: list[dict[str, Any]] = []
    for path in paths:
        override, issue = _read_json_document(repo, path)
        if issue or override is None:
            return None, "provider_override_unreadable"
        status = _provider_override_status(
            override,
            requirement=requirement,
            active_context=active_context,
            current_receipt=current_receipt,
        )
        if status == "invalid":
            return None, "provider_override_invalid"
        if status == "current":
            current.append(override)
    if len(current) > 1:
        return None, "provider_override_ambiguous"
    return (current[0], None) if current else (None, None)


def _provider_override_status(
    override: dict[str, Any],
    *,
    requirement: dict[str, Any] | None,
    active_context: dict[str, Any],
    current_receipt: dict[str, Any] | None,
) -> str:
    if not isinstance(requirement, dict):
        return "invalid"
    if not _valid_override_shape(override):
        return "invalid"
    invalidates = override.get("invalidates")
    if not isinstance(invalidates, dict):
        return "invalid"
    requirement_digest = requirement.get("semanticInputDigest")
    invalidated_requirements = invalidates.get("requirementDigests")
    if not isinstance(invalidated_requirements, list):
        return "invalid"
    if requirement_digest not in invalidated_requirements:
        return "historical"
    if override.get("schemaVersion") != CONTRACT_VERSION or override.get("kind") != OVERRIDE_KIND:
        return "invalid"
    if override.get("overrideDigest") != seal_provider_override(override).get("overrideDigest"):
        return "invalid"
    named_human = override.get("namedHuman")
    if not isinstance(named_human, dict) or not named_human.get("id") or not named_human.get("displayName"):
        return "invalid"
    project = override.get("project")
    consumer = active_context.get("consumer", {})
    if not isinstance(project, dict) or project.get("id") != consumer.get("projectId"):
        return "invalid"
    if project.get("rootIdentity") != consumer.get("rootIdentity"):
        return "invalid"
    if override.get("activeChange") != active_context.get("activeChange"):
        return "invalid"
    if override.get("previousProviderId") != requirement.get("provider", {}).get("id"):
        return "invalid"
    if override.get("newProviderId") == override.get("previousProviderId"):
        return "invalid"
    if not isinstance(override.get("reason"), str) or not override.get("reason", "").strip():
        return "invalid"
    if _parse_time(override.get("decidedAt")) is None or override.get("reassessmentRequired") is not True:
        return "invalid"
    if current_receipt is not None:
        invalidated_receipts = invalidates.get("receiptDigests")
        if (
            not isinstance(invalidated_receipts, list)
            or current_receipt.get("receiptDigest") not in invalidated_receipts
        ):
            return "invalid"
    return "current"


def _assert_requirement_context(
    change_id: str,
    requirement: dict[str, Any],
    context: dict[str, Any],
) -> None:
    expected_consumer = requirement["consumer"]
    current_consumer = context.get("consumer", {})
    if any(current_consumer.get(key) != expected_consumer.get(key) for key in ("projectId", "rootIdentity")):
        raise ReadinessError("consumer_identity_mismatch", "Requirement consumer identity is not current")
    if current_consumer.get("revision") != expected_consumer.get("revision"):
        raise ReadinessError("consumer_revision_mismatch", "Requirement consumer revision is not current")
    expected_change = requirement["activeChange"]
    if expected_change.get("id") != change_id or context.get("activeChange", {}).get("id") != change_id:
        raise ReadinessError("active_change_mismatch", "Requirement is not bound to the active change")
    if context.get("activeChange", {}).get("semanticPlanDigest") != expected_change.get("semanticPlanDigest"):
        raise ReadinessError("semantic_plan_mismatch", "Requirement semantic plan is not current")
    if context.get("targetProfile") != requirement.get("targetProfile"):
        raise ReadinessError("target_profile_mismatch", "Requirement target profile is not current")


def _read_json_document(repo: Path, path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not _path_lexists(path):
        return None, None
    try:
        _assert_trusted_existing_path(repo, path)
        value = json.loads(path.read_text())
    except (ReadinessError, OSError, UnicodeError, json.JSONDecodeError):
        return None, "document_unreadable"
    if not isinstance(value, dict):
        return None, "document_invalid"
    return value, None


def _create_json_once(
    repo: Path,
    path: Path,
    payload: dict[str, Any],
    *,
    conflict_code: str,
) -> str:
    _assert_trusted_write_path(repo, path)
    content = f"{json.dumps(payload, indent=2, sort_keys=True)}\n"
    if _path_lexists(path):
        existing, issue = _read_json_document(repo, path)
        if issue or canonical_json(existing) != canonical_json(payload):
            raise ReadinessError(conflict_code, "Canonical readiness path already has different content", path=path)
        return "existing"
    path.parent.mkdir(parents=True, exist_ok=True)
    _assert_trusted_write_path(repo, path)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise ReadinessError(
                conflict_code,
                "Canonical readiness path was created concurrently",
                path=path,
            ) from error
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        temporary.unlink(missing_ok=True)
    return "created"


def _replace_current_requirement(
    repo: Path,
    path: Path,
    payload: dict[str, Any],
    *,
    expected_digest: str,
) -> str:
    _assert_trusted_write_path(repo, path)
    lock = path.parent / ".requirement-promotion.lock"
    _assert_trusted_write_path(repo, lock)
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise ReadinessError(
            "requirement_promotion_in_progress",
            "Another Requirement promotion owns the guarded replacement lock",
            path=lock,
        ) from error
    os.close(descriptor)
    temporary: Path | None = None
    try:
        current, issue = _read_json_document(repo, path)
        if (
            issue
            or current is None
            or current.get("semanticInputDigest") != expected_digest
        ):
            raise ReadinessError(
                "requirement_conflict",
                "The current Requirement changed after the replacement plan",
                path=path,
            )
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "w") as handle:
            handle.write(f"{json.dumps(payload, indent=2, sort_keys=True)}\n")
            handle.flush()
            os.fsync(handle.fileno())
        _assert_trusted_write_path(repo, path)
        os.replace(temporary, path)
        temporary = None
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)
    return "replaced"


def _assert_trusted_write_path(repo: Path, path: Path) -> None:
    _assert_trusted_existing_path(repo, path.parent, allow_missing=True)
    try:
        guard_devflow_write(repo, path)
    except Exception as error:
        raise ReadinessError(
            "untrusted_readiness_path",
            "Readiness write path is not DevFlow-owned",
            path=path,
        ) from error
    if _path_lexists(path) and path.is_symlink():
        raise ReadinessError("untrusted_readiness_path", "Readiness write target cannot be a symlink", path=path)


def _assert_trusted_existing_path(repo: Path, path: Path, *, allow_missing: bool = False) -> None:
    repo = Path(repo).resolve()
    candidate = Path(path).absolute()
    try:
        relative = candidate.relative_to(repo)
    except ValueError as error:
        raise ReadinessError(
            "path_outside_repo",
            "Readiness path is outside the consumer root",
            path=candidate,
        ) from error
    current = repo
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ReadinessError("untrusted_readiness_path", "Readiness path contains a symlink", path=current)
        if not _path_lexists(current):
            if allow_missing:
                return
            raise ReadinessError("readiness_path_missing", "Readiness path does not exist", path=current)


def _path_lexists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def evaluate(
    requirement: dict[str, Any] | None,
    evidence: dict[str, Any] | None,
    active_context: dict[str, Any],
) -> dict[str, Any]:
    if requirement is None:
        return _required("IMPLEMENTATION_REQUIREMENT_MISSING", "promote-approved-provider-requirement")
    if requirement.get("schemaVersion") != CONTRACT_VERSION or requirement.get("kind") != REQUIREMENT_KIND:
        return _not_ready(["REQUIREMENT_SCHEMA_UNSUPPORTED"])

    requirement_issues = _validate_requirement(requirement)
    if requirement_issues:
        return _not_ready(requirement_issues)
    if requirement.get("semanticInputDigest") != seal_requirement(requirement)["semanticInputDigest"]:
        return _not_ready(["REQUIREMENT_DIGEST_MISMATCH"])

    if evidence is None:
        return _required("IMPLEMENTATION_EVIDENCE_MISSING", "request-project-bound-provider-evidence")
    if evidence.get("schemaVersion") != CONTRACT_VERSION or evidence.get("kind") != EVIDENCE_KIND:
        return _not_ready(["EVIDENCE_SCHEMA_UNSUPPORTED"])

    evidence_issues = _validate_evidence(evidence)
    if evidence_issues:
        return _not_ready(evidence_issues)
    if evidence.get("evidenceDigest") != seal_evidence(evidence)["evidenceDigest"]:
        return _not_ready(["EVIDENCE_DIGEST_MISMATCH"])
    if not _valid_active_context(active_context):
        return _not_ready(["ACTIVE_CONTEXT_UNAVAILABLE"])

    issues: list[str] = []
    requirement_digest = str(requirement["semanticInputDigest"])
    if evidence.get("requirementDigest") != requirement_digest:
        issues.append("EVIDENCE_REQUIREMENT_MISMATCH")
    if evidence["provider"].get("id") != requirement["provider"].get("id"):
        issues.append("PROVIDER_IDENTITY_MISMATCH")

    _compare_consumer(requirement, evidence, active_context, issues)
    _compare_change(requirement, evidence, active_context, issues)
    _compare_target(requirement, evidence, active_context, issues)
    _compare_capabilities(requirement, evidence, issues)

    required_limitations = set(requirement.get("requiredLimitations", []))
    evidence_limitations = set(evidence.get("limitations", []))
    if not required_limitations.issubset(evidence_limitations):
        issues.append("REQUIRED_LIMITATION_MISSING")
    if _evidence_is_stale(requirement, evidence, active_context):
        issues.append("EVIDENCE_STALE")

    if issues:
        return _not_ready(issues)

    bindings = readiness_bindings(requirement, evidence, active_context)
    return {
        "schemaVersion": CONTRACT_VERSION,
        "evaluatorVersion": EVALUATOR_VERSION,
        "state": IMPLEMENTATION_PROVIDER_READY,
        "ready": True,
        "issueCodes": [],
        "nextAction": "continue-with-ordinary-implementation-authority",
        "bindings": bindings,
    }


def readiness_bindings(
    requirement: dict[str, Any],
    evidence: dict[str, Any],
    active_context: dict[str, Any],
) -> dict[str, str]:
    capabilities = sorted(item["id"] for item in requirement["requiredCapabilities"])
    return {
        "requirementDigest": str(requirement["semanticInputDigest"]),
        "evidenceDigest": str(evidence["evidenceDigest"]),
        "activeContextDigest": canonical_digest(_semantic_active_context(active_context)),
        "semanticPlanDigest": str(active_context["activeChange"]["semanticPlanDigest"]),
        "providerArtifactDigest": str(evidence["provider"]["digest"]),
        "consumerRootIdentity": str(active_context["consumer"]["rootIdentity"]),
        "consumerRevision": str(active_context["consumer"]["revision"]),
        "targetProfileDigest": str(active_context["targetProfile"]["digest"]),
        "capabilitySetDigest": canonical_digest(capabilities),
    }


def _semantic_active_context(active_context: dict[str, Any]) -> dict[str, Any]:
    return {
        "consumer": copy.deepcopy(active_context.get("consumer")),
        "activeChange": copy.deepcopy(active_context.get("activeChange")),
        "targetProfile": copy.deepcopy(active_context.get("targetProfile")),
    }


def _required(issue: str, next_action: str) -> dict[str, Any]:
    return {
        "schemaVersion": CONTRACT_VERSION,
        "evaluatorVersion": EVALUATOR_VERSION,
        "state": IMPLEMENTATION_PROVIDER_REQUIRED,
        "ready": False,
        "issueCodes": [issue],
        "nextAction": next_action,
        "bindings": {},
    }


def _not_ready(issues: list[str]) -> dict[str, Any]:
    normalized = _ordered_issues(issues)
    first = normalized[0] if normalized else "EVIDENCE_INVALID"
    return {
        "schemaVersion": CONTRACT_VERSION,
        "evaluatorVersion": EVALUATOR_VERSION,
        "state": IMPLEMENTATION_PROVIDER_NOT_READY,
        "ready": False,
        "issueCodes": normalized,
        "nextAction": NEXT_ACTIONS.get(first, "repair-implementation-readiness-inputs"),
        "bindings": {},
    }


def _ordered_issues(issues: list[str]) -> list[str]:
    unique = set(issues)
    ordered = [code for code in ISSUE_PRIORITY if code in unique]
    ordered.extend(sorted(unique.difference(ordered)))
    return ordered


def _validate_requirement(requirement: dict[str, Any]) -> list[str]:
    required = {
        "schemaVersion",
        "kind",
        "requirementId",
        "provider",
        "consumer",
        "activeChange",
        "targetProfile",
        "requiredCapabilities",
        "acceptedEvidence",
        "requiredLimitations",
        "semanticInputDigest",
    }
    if set(requirement) != required:
        return ["REQUIREMENT_INVALID"]
    provider = requirement.get("provider")
    if not _exact_mapping(provider, {"id", "policy", "fallbackPolicy"}):
        return ["REQUIREMENT_INVALID"]
    if (
        not _is_stable_id(provider.get("id"))
        or provider.get("policy") != "project-selected"
        or provider.get("fallbackPolicy") != "named-human-override-only"
    ):
        return ["REQUIREMENT_INVALID"]
    if not _valid_consumer(requirement.get("consumer")):
        return ["REQUIREMENT_INVALID"]
    if not _valid_active_change(requirement.get("activeChange")):
        return ["REQUIREMENT_INVALID"]
    if not _valid_target_profile(requirement.get("targetProfile")):
        return ["REQUIREMENT_INVALID"]
    capabilities = requirement.get("requiredCapabilities")
    if not isinstance(capabilities, list) or not capabilities:
        return ["REQUIREMENT_INVALID"]
    capability_ids = [item.get("id") for item in capabilities if isinstance(item, dict)]
    if len(capability_ids) != len(capabilities) or len(set(capability_ids)) != len(capability_ids):
        return ["REQUIREMENT_INVALID"]
    if any(
        not _exact_mapping(item, {"id", "evidenceType"})
        or not _is_stable_id(item.get("id"))
        or item.get("evidenceType") != "validator-receipt"
        for item in capabilities
    ):
        return ["REQUIREMENT_INVALID"]
    accepted = requirement.get("acceptedEvidence")
    if not _exact_mapping(
        accepted,
        {"schemaVersion", "maximumAgeSeconds", "requireImmutableReceipts"},
    ):
        return ["REQUIREMENT_INVALID"]
    maximum_age = accepted.get("maximumAgeSeconds")
    if (
        accepted.get("schemaVersion") != CONTRACT_VERSION
        or not isinstance(maximum_age, int)
        or isinstance(maximum_age, bool)
        or maximum_age < 1
        or accepted.get("requireImmutableReceipts") is not True
    ):
        return ["REQUIREMENT_INVALID"]
    limitations = requirement.get("requiredLimitations")
    if not _valid_string_set(limitations, allow_empty=False):
        return ["REQUIREMENT_INVALID"]
    if not _is_stable_id(requirement.get("requirementId")) or not _is_digest(
        requirement.get("semanticInputDigest")
    ):
        return ["REQUIREMENT_INVALID"]
    return []


def _validate_evidence(evidence: dict[str, Any]) -> list[str]:
    allowed = {
        "schemaVersion",
        "kind",
        "evidenceId",
        "requirementDigest",
        "provider",
        "consumer",
        "activeChange",
        "targetProfile",
        "capabilities",
        "limitations",
        "binding",
        "evidenceDigest",
        "providerDetails",
    }
    required = allowed - {"providerDetails"}
    if not required.issubset(evidence) or not set(evidence).issubset(allowed):
        return ["EVIDENCE_INVALID"]
    provider = evidence.get("provider")
    if not _exact_mapping(provider, {"id", "artifactId", "version", "revision", "digest"}):
        return ["EVIDENCE_INVALID"]
    if (
        not _is_stable_id(provider.get("id"))
        or not _is_stable_id(provider.get("artifactId"))
        or not _nonempty_string(provider.get("version"))
        or not _nonempty_string(provider.get("revision"))
        or not _is_digest(provider.get("digest"))
    ):
        return ["EVIDENCE_INVALID"]
    if not _valid_consumer(evidence.get("consumer")):
        return ["EVIDENCE_INVALID"]
    if not _valid_active_change(evidence.get("activeChange")):
        return ["EVIDENCE_INVALID"]
    if not _valid_target_profile(evidence.get("targetProfile")):
        return ["EVIDENCE_INVALID"]
    capabilities = evidence.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        return ["EVIDENCE_INVALID"]
    capability_ids = [item.get("id") for item in capabilities if isinstance(item, dict)]
    if len(capability_ids) != len(capabilities) or len(set(capability_ids)) != len(capability_ids):
        return ["EVIDENCE_INVALID"]
    for item in capabilities:
        if not _exact_mapping(item, {"id", "status", "validator", "receipt"}):
            return ["EVIDENCE_INVALID"]
        validator = item.get("validator")
        receipt = item.get("receipt")
        if (
            not _is_stable_id(item.get("id"))
            or item.get("status") not in {"passed", "failed"}
            or not _exact_mapping(validator, {"id", "version"})
            or not _is_stable_id(validator.get("id"))
            or not _nonempty_string(validator.get("version"))
            or not _exact_mapping(receipt, {"id", "digest"})
            or not _is_stable_id(receipt.get("id"))
            or not _is_digest(receipt.get("digest"))
        ):
            return ["EVIDENCE_INVALID"]
    if not _valid_string_set(evidence.get("limitations"), allow_empty=True):
        return ["EVIDENCE_INVALID"]
    binding = evidence.get("binding")
    if not _valid_evidence_binding(binding):
        return ["EVIDENCE_INVALID"]
    if "providerDetails" in evidence and not isinstance(evidence.get("providerDetails"), dict):
        return ["EVIDENCE_INVALID"]
    if (
        not _is_stable_id(evidence.get("evidenceId"))
        or not _is_digest(evidence.get("requirementDigest"))
        or not _is_digest(evidence.get("evidenceDigest"))
    ):
        return ["EVIDENCE_INVALID"]
    return []


def _valid_active_context(context: Any) -> bool:
    return bool(
        isinstance(context, dict)
        and _valid_consumer(context.get("consumer"))
        and _valid_active_change(context.get("activeChange"))
        and _valid_target_profile(context.get("targetProfile"))
        and _parse_time(context.get("evaluatedAt")) is not None
    )


def _valid_consumer(value: Any) -> bool:
    return bool(
        _exact_mapping(value, {"projectId", "rootIdentity", "revision"})
        and _is_stable_id(value.get("projectId"))
        and _is_digest(value.get("rootIdentity"))
        and _nonempty_string(value.get("revision"))
    )


def _valid_active_change(value: Any) -> bool:
    return bool(
        _exact_mapping(value, {"id", "semanticPlanDigest"})
        and _is_stable_id(value.get("id"))
        and _is_digest(value.get("semanticPlanDigest"))
    )


def _valid_target_profile(value: Any) -> bool:
    return bool(
        _exact_mapping(value, {"id", "digest"})
        and _is_stable_id(value.get("id"))
        and _is_digest(value.get("digest"))
    )


def _valid_evidence_binding(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if value.get("immutable") is True:
        return set(value) == {"immutable"}
    return bool(
        value.get("immutable") is False
        and set(value) == {"immutable", "issuedAt", "validUntil"}
        and _parse_time(value.get("issuedAt")) is not None
        and _parse_time(value.get("validUntil")) is not None
    )


def _valid_receipt_shape(receipt: Any) -> bool:
    required = {
        "schemaVersion",
        "kind",
        "evaluatorVersion",
        "state",
        "bindings",
        "issueCodes",
        "nextAction",
        "recordedAt",
        "receiptDigest",
    }
    bindings = receipt.get("bindings") if isinstance(receipt, dict) else None
    binding_keys = {
        "requirementDigest",
        "evidenceDigest",
        "activeContextDigest",
        "semanticPlanDigest",
        "providerArtifactDigest",
        "consumerRootIdentity",
        "consumerRevision",
        "targetProfileDigest",
        "capabilitySetDigest",
    }
    return bool(
        isinstance(receipt, dict)
        and set(receipt) == required
        and _exact_mapping(bindings, binding_keys)
        and all(
            _is_digest(bindings.get(key))
            for key in binding_keys - {"consumerRevision"}
        )
        and _nonempty_string(bindings.get("consumerRevision"))
        and receipt.get("issueCodes") == []
        and receipt.get("nextAction") == "continue-with-ordinary-implementation-authority"
        and _parse_time(receipt.get("recordedAt")) is not None
        and _is_digest(receipt.get("receiptDigest"))
    )


def _valid_override_shape(override: Any) -> bool:
    required = {
        "schemaVersion",
        "kind",
        "overrideId",
        "namedHuman",
        "project",
        "activeChange",
        "previousProviderId",
        "newProviderId",
        "reason",
        "decidedAt",
        "invalidates",
        "reassessmentRequired",
        "overrideDigest",
    }
    if not isinstance(override, dict) or set(override) != required:
        return False
    named_human = override.get("namedHuman")
    project = override.get("project")
    invalidates = override.get("invalidates")
    return bool(
        _is_stable_id(override.get("overrideId"))
        and _exact_mapping(named_human, {"id", "displayName"})
        and _is_stable_id(named_human.get("id"))
        and _nonempty_string(named_human.get("displayName"))
        and _exact_mapping(project, {"id", "rootIdentity"})
        and _is_stable_id(project.get("id"))
        and _is_digest(project.get("rootIdentity"))
        and _valid_active_change(override.get("activeChange"))
        and _is_stable_id(override.get("previousProviderId"))
        and _is_stable_id(override.get("newProviderId"))
        and _nonempty_string(override.get("reason"))
        and _parse_time(override.get("decidedAt")) is not None
        and _exact_mapping(invalidates, {"requirementDigests", "receiptDigests"})
        and _valid_digest_set(invalidates.get("requirementDigests"), allow_empty=False)
        and _valid_digest_set(invalidates.get("receiptDigests"), allow_empty=True)
        and override.get("reassessmentRequired") is True
        and _is_digest(override.get("overrideDigest"))
    )


def _exact_mapping(value: Any, keys: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == keys


def _valid_string_set(value: Any, *, allow_empty: bool) -> bool:
    return bool(
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(_nonempty_string(item) for item in value)
        and len(value) == len(set(value))
    )


def _valid_digest_set(value: Any, *, allow_empty: bool) -> bool:
    return bool(
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(_is_digest(item) for item in value)
        and len(value) == len(set(value))
    )


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_stable_id(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]*", value))


def _compare_consumer(
    requirement: dict[str, Any],
    evidence: dict[str, Any],
    context: dict[str, Any],
    issues: list[str],
) -> None:
    expected = requirement["consumer"]
    actual = evidence["consumer"]
    current = context.get("consumer", {})
    identity_keys = ("projectId", "rootIdentity")
    if any(actual.get(key) != expected.get(key) or current.get(key) != expected.get(key) for key in identity_keys):
        issues.append("CONSUMER_IDENTITY_MISMATCH")
    if actual.get("revision") != expected.get("revision") or current.get("revision") != expected.get("revision"):
        issues.append("CONSUMER_REVISION_MISMATCH")


def _compare_change(
    requirement: dict[str, Any],
    evidence: dict[str, Any],
    context: dict[str, Any],
    issues: list[str],
) -> None:
    expected = requirement["activeChange"]
    actual = evidence["activeChange"]
    current = context.get("activeChange", {})
    if actual.get("id") != expected.get("id") or current.get("id") != expected.get("id"):
        issues.append("ACTIVE_CHANGE_MISMATCH")
    if (
        actual.get("semanticPlanDigest") != expected.get("semanticPlanDigest")
        or current.get("semanticPlanDigest") != expected.get("semanticPlanDigest")
    ):
        issues.append("SEMANTIC_PLAN_MISMATCH")


def _compare_target(
    requirement: dict[str, Any],
    evidence: dict[str, Any],
    context: dict[str, Any],
    issues: list[str],
) -> None:
    expected = requirement["targetProfile"]
    actual = evidence["targetProfile"]
    current = context.get("targetProfile", {})
    if actual != expected or current != expected:
        issues.append("TARGET_PROFILE_MISMATCH")


def _compare_capabilities(
    requirement: dict[str, Any],
    evidence: dict[str, Any],
    issues: list[str],
) -> None:
    expected_ids = [item.get("id") for item in requirement["requiredCapabilities"]]
    evidence_items = evidence.get("capabilities", [])
    actual_ids = [item.get("id") for item in evidence_items if isinstance(item, dict)]
    if sorted(actual_ids) != sorted(expected_ids) or len(actual_ids) != len(set(actual_ids)):
        issues.append("CAPABILITY_SET_MISMATCH")
    for item in evidence_items:
        if not isinstance(item, dict) or item.get("id") not in expected_ids:
            continue
        if item.get("status") != "passed":
            issues.append("CAPABILITY_NOT_PASSED")
        validator = item.get("validator")
        receipt = item.get("receipt")
        if (
            not isinstance(validator, dict)
            or not validator.get("id")
            or not validator.get("version")
            or not isinstance(receipt, dict)
            or not receipt.get("id")
            or not _is_digest(receipt.get("digest"))
        ):
            issues.append("CAPABILITY_RECEIPT_MISSING")


def _evidence_is_stale(
    requirement: dict[str, Any],
    evidence: dict[str, Any],
    context: dict[str, Any],
) -> bool:
    binding = evidence.get("binding", {})
    if binding.get("immutable") is True:
        return False
    if binding.get("immutable") is not False:
        return True
    issued = _parse_time(binding.get("issuedAt"))
    valid_until = _parse_time(binding.get("validUntil"))
    evaluated = _parse_time(context.get("evaluatedAt"))
    if issued is None or valid_until is None or evaluated is None:
        return True
    if not issued <= evaluated <= valid_until:
        return True
    maximum_age = requirement.get("acceptedEvidence", {}).get("maximumAgeSeconds")
    if not isinstance(maximum_age, int) or maximum_age < 1:
        return True
    return (evaluated - issued).total_seconds() > maximum_age


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _is_digest(value: Any) -> bool:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        return False
    suffix = value.removeprefix("sha256:")
    return len(suffix) == 64 and all(character in "0123456789abcdef" for character in suffix)
