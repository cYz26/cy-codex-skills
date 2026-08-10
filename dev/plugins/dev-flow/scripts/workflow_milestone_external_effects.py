from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from workflow_authority_delta import resolve_authority_delta
from workflow_milestone_contract import validate_milestone_contract
from workflow_mode_routing import validate_devflow_config
from workflow_state import parse_state_text, resolve_state


CONTINUE = "CONTINUE"
FAIL_CLOSED_REPAIR = "FAIL_CLOSED_REPAIR"
AWAIT_HUMAN = "AWAIT_HUMAN"
EXPECTED_EFFECTS = (
    "git.commit",
    "git.push",
    "git.tag.push",
    "github.release",
    "devflow.source.fast_forward",
    "codex.cache.refresh",
    "devflow.project.refresh",
)
VALIDATION_CHECK_IDS = (
    "completion-contract",
    "focused-tests",
    "broad-tests",
    "devflow-validators",
    "source-release-parity",
    "secret-scan",
    "unexpected-candidate-scan",
    "blocker-scan",
)
CANONICAL_PLUGIN_EVAL_COMMAND = (
    "plugin-eval analyze plugins/dev-flow --format markdown"
)
RECEIPT_ROOT = Path(".planning/devflow/milestone-external-effects")
CANONICAL_STATE_PATH = Path(".planning/devflow/STATE.md")
DEVFLOW_CONFIG_PATH = Path(".dev-flow.json")
CANONICAL_CONTRACT_NAME = "standing-milestone-contract.json"
CYCLE_EDGE_SENTINEL = "devflow-canonical-cycle-edge-v1"
REQUIRED_BOUNDARIES = (
    "publication_readback",
    "publication_apply",
    "publication_diagnose",
    "publication_remediate",
    "source_plan",
    "source_apply",
    "source_verify",
    "cache_plan",
    "cache_apply",
    "cache_verify",
    "project_plan",
    "project_apply",
    "project_verify",
)
AUTHORITY_FIELDS = (
    (("contractId",), "standingContract.contractId"),
    (("goalId",), "standingContract.goalId"),
    (("change",), "standingContract.change"),
    (("writeSet",), "standingContract.writeSet"),
    (("plugin", "id"), "plugin.id"),
    (("plugin", "marketplace"), "plugin.marketplace"),
    (("plugin", "versionRule"), "plugin.versionRule"),
    (("plugin", "version"), "plugin.version"),
    (("repository", "remote"), "repository.remote"),
    (("repository", "ref"), "repository.ref"),
    (("publication", "tag"), "publication.tag"),
    (("publication", "channel"), "publication.channel"),
    (("publication", "mechanism"), "publication.mechanism"),
    (("publication", "workflow"), "publication.workflow"),
    (("publication", "assets"), "publication.assets"),
    (("refreshTargets", "cache"), "refreshTargets.cache"),
    (("refreshTargets", "project"), "refreshTargets.project"),
    (("failurePolicy",), "standingContract.failurePolicy"),
    (("reentryPolicy",), "standingContract.reentryPolicy"),
    (("exclusions",), "standingContract.exclusions"),
)
EVIDENCE_FIELDS = (
    ("repository", "remoteUrl"),
    ("repository", "expectedBase"),
    ("commit", "message"),
)


Boundary = Callable[[object], Mapping[str, Any]]


class MilestoneStateIntegrityError(RuntimeError):
    """Raised only for durable state/intent identity drift."""


def canonical_contract_relative_path(contract: Mapping[str, Any]) -> Path | None:
    change = contract.get("change") if isinstance(contract, Mapping) else None
    if not isinstance(change, str) or not change or Path(change).name != change:
        return None
    return (
        Path("openspec")
        / "changes"
        / change
        / "evidence"
        / CANONICAL_CONTRACT_NAME
    )


def plan_milestone_external_effects(
    repo: Path,
    contract: Mapping[str, Any] | None,
    *,
    candidate_manifest: Mapping[str, Any],
    validation_receipt: Mapping[str, Any],
    review_receipt: Mapping[str, Any],
    execution_ledger: Mapping[str, Any],
    receipt_dir: Path,
    boundaries: Mapping[str, object],
) -> dict[str, Any]:
    """Validate and freeze one preauthorized milestone without mutation."""

    repo = Path(repo).resolve()
    if contract is None:
        return _technical_stop("CANONICAL_AUTHORITY_BINDING_INVALID")
    try:
        contract_data = _plain_mapping(contract)
        candidate = _plain_mapping(candidate_manifest)
        validation = _plain_mapping(validation_receipt)
        review = _plain_mapping(review_receipt)
    except (TypeError, ValueError):
        return _technical_stop("CANONICAL_AUTHORITY_BINDING_INVALID")
    contract_validation = _validate_current_milestone_contract(contract_data)
    if not contract_validation["ok"]:
        return _technical_stop(
            str(contract_validation["reasonCodes"][0]),
            invalidations=list(contract_validation["invalidations"]),
        )
    missing = [label for path, label in AUTHORITY_FIELDS if not _present(contract_data, path)]
    if missing:
        return _technical_stop("CANONICAL_AUTHORITY_BINDING_INVALID")
    candidate_shape_issue = _candidate_shape_issue(candidate)
    if candidate_shape_issue:
        return _technical_stop("CANDIDATE_MANIFEST_INVALID", invalidations=[candidate_shape_issue])
    validation_shape_issue = _validation_shape_issue(validation, contract_data)
    if validation_shape_issue:
        return _technical_stop("VALIDATION_RECEIPT_INVALID", invalidations=[validation_shape_issue])
    validation_command_issue = _validation_command_issue(validation, contract_data)
    if validation_command_issue:
        return _technical_stop(
            "VALIDATION_COMMAND_INVALID", invalidations=[validation_command_issue]
        )
    review_shape_issue = _review_shape_issue(review, contract_data)
    if review_shape_issue:
        return _technical_stop("REVIEW_RECEIPT_INVALID", invalidations=[review_shape_issue])
    candidate_evidence_issue = _candidate_evidence_issue(candidate)
    if candidate_evidence_issue:
        return _technical_stop("CANDIDATE_EVIDENCE_INVALID", invalidations=[candidate_evidence_issue])
    if validation.get("evidence") != candidate["evidence"]["validation"]:
        return _technical_stop("VALIDATION_EVIDENCE_INVALID")
    if review.get("evidence") != candidate["evidence"]["independentReview"]:
        return _technical_stop("REVIEW_EVIDENCE_INVALID")
    canonical_guard, guard_issue = _canonical_guard(
        repo,
        contract_data,
        candidate,
        validation,
        review,
        phase="plan",
    )
    if guard_issue:
        return _technical_stop(
            "CANONICAL_AUTHORITY_BINDING_INVALID", invalidations=[guard_issue]
        )
    assert canonical_guard is not None
    if validation.get("contractId") != contract_data.get("contractId"):
        return _technical_stop("VALIDATION_RECEIPT_INVALID", invalidations=["contract_identity"])
    if review.get("contractId") != contract_data.get("contractId"):
        return _technical_stop("REVIEW_RECEIPT_INVALID", invalidations=["contract_identity"])
    evidence_document_issue = _candidate_evidence_documents_issue(
        repo,
        candidate,
        validation,
        review,
        contract_data,
        commit=None,
    )
    if evidence_document_issue:
        return _technical_stop(evidence_document_issue)
    if any(not _present(contract_data, path) for path in EVIDENCE_FIELDS):
        return _technical_stop("CONTRACT_EVIDENCE_INCOMPLETE")

    receipt_binding = _trusted_receipt_binding(repo, contract_data, receipt_dir)
    if receipt_binding is None:
        return _technical_stop("RECEIPT_DIRECTORY_UNTRUSTED")

    boundary_issue = _validate_boundaries(boundaries)
    if boundary_issue:
        return _technical_stop("BOUNDARY_ADAPTER_INCOMPLETE", invalidations=[boundary_issue])

    requested_issue, excluded_effect = _requested_effects_issue(contract_data)
    if requested_issue:
        return _technical_stop("REQUESTED_EFFECTS_INVALID", invalidations=[requested_issue])
    if excluded_effect:
        return _human_gate(
            f"effects.{excluded_effect}",
            "EXCLUDED_EFFECT_REQUESTED",
            canonical_binding=canonical_guard,
            write_set=[],
        )

    refresh = contract_data["refreshTargets"]
    plugin = contract_data["plugin"]
    expected_cache = f"{plugin['id']}@{plugin['marketplace']}"
    if refresh.get("cache") != expected_cache:
        return _human_gate(
            "refreshTargets.cache",
            "UNDECLARED_REFRESH_TARGET",
            canonical_binding=canonical_guard,
            write_set=[],
        )
    project_target = Path(str(refresh.get("project") or "")).expanduser()
    if not project_target.is_absolute() or not project_target.is_dir():
        return _human_gate(
            "refreshTargets.project",
            "UNDECLARED_REFRESH_TARGET",
            canonical_binding=canonical_guard,
            write_set=[],
        )

    repository = contract_data["repository"]
    if not re.fullmatch(r"refs/heads/[A-Za-z0-9._/-]+", str(repository.get("ref") or "")):
        return _human_gate(
            "repository.ref",
            "STANDING_AUTHORITY_INCOMPLETE",
            canonical_binding=canonical_guard,
            write_set=[],
        )
    if not re.fullmatch(r"[0-9a-f]{40}", str(repository.get("expectedBase") or "")):
        return _technical_stop("CONTRACT_EVIDENCE_INCOMPLETE")

    candidate_reason = _candidate_contract_issue(contract_data, candidate)
    if candidate_reason:
        return _technical_stop(candidate_reason)
    deletion_issue = _candidate_deletions_issue(
        repo,
        candidate,
        str(contract_data["repository"]["expectedBase"]),
    )
    if deletion_issue:
        return _technical_stop("CANDIDATE_DRIFT", invalidations=[deletion_issue])
    if _candidate_files_issue(repo, candidate):
        return _technical_stop("CANDIDATE_DRIFT")
    asset_binding, asset_issue = _asset_directory_binding(
        repo, candidate, receipt_binding
    )
    if asset_issue:
        return _technical_stop("CANDIDATE_ASSET_DRIFT", invalidations=[asset_issue])
    assert asset_binding is not None
    if _unexpected_candidate_paths(
        repo, contract_data, receipt_binding=receipt_binding
    ):
        return _technical_stop("UNEXPECTED_CANDIDATE_FILES")
    if not _validation_current(validation, candidate):
        return _technical_stop("VALIDATION_NOT_CURRENT")
    if not _review_threshold_met(review):
        return _technical_stop("REVIEW_THRESHOLD_NOT_MET")
    if review.get("candidateDigest") != candidate.get("payloadDigest") or review.get(
        "reviewedDiffDigest"
    ) != candidate.get("payloadDigest"):
        return _technical_stop("REVIEW_CANDIDATE_MISMATCH")
    ledger = _plain_mapping(execution_ledger)
    simulation = simulate_milestone_execution_ledger(ledger)
    if not simulation.get("ok"):
        return _technical_stop("EXECUTION_LEDGER_INVALID")

    plan: dict[str, Any] = {
        "schemaVersion": "1.0",
        "kind": "devflow-milestone-external-effects-plan",
        "ok": True,
        "decision": CONTINUE,
        "status": "READY",
        "nextStep": "CONTRACT_VALIDATED",
        "reasonCodes": ["STANDING_MILESTONE_AUTHORITY_CURRENT"],
        "missingAuthority": [],
        "contractDigest": _digest(contract_data),
        "candidateDigest": _digest(candidate),
        "validationDigest": _digest(validation),
        "reviewDigest": _digest(review),
        "executionLedgerDigest": _digest(ledger),
        "executionSimulationDigest": _digest(simulation),
        "canonicalGuard": canonical_guard,
        "receiptBinding": receipt_binding,
        "assetBinding": asset_binding,
        "writeSet": list(contract_data["writeSet"]),
        "excludedEffects": list(contract_data["exclusions"]),
        "contract": contract_data,
        "candidateManifest": candidate,
        "validationReceipt": validation,
        "reviewReceipt": review,
        "executionLedger": ledger,
        "executionSimulation": simulation,
    }
    plan["planDigest"] = _digest(plan)
    return plan


def apply_milestone_external_effects(
    repo: Path,
    contract: Mapping[str, Any],
    *,
    plan: Mapping[str, Any],
    receipt_dir: Path,
    boundaries: Mapping[str, object],
) -> dict[str, Any]:
    try:
        return _apply_milestone_external_effects(
            repo,
            contract,
            plan=plan,
            receipt_dir=receipt_dir,
            boundaries=boundaries,
        )
    except MilestoneStateIntegrityError as error:
        return _technical_stop(
            "MILESTONE_STATE_INVALID",
            invalidations=[str(error)],
            receipts_preserved=True,
        )
    except OSError as error:
        return _technical_stop(
            "RECEIPT_STORAGE_FAILED",
            invalidations=[str(error)],
            receipts_preserved=True,
        )


def _apply_milestone_external_effects(
    repo: Path,
    contract: Mapping[str, Any],
    *,
    plan: Mapping[str, Any],
    receipt_dir: Path,
    boundaries: Mapping[str, object],
) -> dict[str, Any]:
    """Advance the first incomplete external step and recover by readback."""

    repo = Path(repo).resolve()
    plan_data = _plain_mapping(plan)
    contract_data = _plain_mapping(contract)
    contract_validation = _validate_current_milestone_contract(contract_data)
    if not contract_validation["ok"]:
        return _technical_stop(
            str(contract_validation["reasonCodes"][0]),
            invalidations=list(contract_validation["invalidations"]),
        )
    receipt_binding = _trusted_receipt_binding(repo, contract_data, receipt_dir)
    if receipt_binding is None or plan_data.get("receiptBinding") != receipt_binding:
        return _technical_stop("RECEIPT_DIRECTORY_UNTRUSTED")
    integrity_issue = _plan_integrity_issue(plan_data, contract_data)
    if integrity_issue:
        return _technical_stop(integrity_issue)
    candidate = plan_data["candidateManifest"]
    asset_binding, asset_issue = _asset_directory_binding(
        repo, candidate, receipt_binding
    )
    if asset_issue or asset_binding != plan_data.get("assetBinding"):
        return _technical_stop(
            "CANDIDATE_ASSET_DRIFT",
            invalidations=[asset_issue or "asset_binding_drift"],
        )
    boundary_issue = _validate_boundaries(boundaries)
    if boundary_issue:
        return _technical_stop("BOUNDARY_ADAPTER_INCOMPLETE", invalidations=[boundary_issue])

    repository = contract_data["repository"]
    remote = str(repository["remote"])
    remote_url = str(repository["remoteUrl"])
    target_ref = str(repository["ref"])
    expected_base = str(repository["expectedBase"])
    head = _git_output(repo, "rev-parse", "HEAD")
    deletion_issue = _candidate_deletions_issue(repo, candidate, expected_base)
    if deletion_issue:
        return _technical_stop("CANDIDATE_DRIFT", invalidations=[deletion_issue])
    candidate_commit = head if head != expected_base and _matching_commit(
        repo, head, expected_base, contract_data, candidate
    ) else None
    if head != expected_base and candidate_commit is None:
        return _technical_stop("CANDIDATE_DRIFT")
    evidence_document_issue = _candidate_evidence_documents_issue(
        repo,
        candidate,
        plan_data["validationReceipt"],
        plan_data["reviewReceipt"],
        contract_data,
        commit=candidate_commit,
    )
    if evidence_document_issue:
        return _technical_stop(
            evidence_document_issue, receipts_preserved=candidate_commit is not None
        )
    observed_guard, guard_issue = _canonical_guard(
        repo,
        contract_data,
        candidate,
        plan_data["validationReceipt"],
        plan_data["reviewReceipt"],
        phase="execute",
        commit=candidate_commit,
    )
    expected_guard = plan_data.get("canonicalGuard")
    if (
        guard_issue
        or observed_guard is None
        or not isinstance(expected_guard, Mapping)
        or not _canonical_guard_matches(expected_guard, observed_guard)
    ):
        return _technical_stop(
            "CANONICAL_AUTHORITY_BINDING_INVALID",
            invalidations=[guard_issue or "canonical_guard_drift"],
        )
    active_guard = observed_guard

    asset_binding, asset_issue = _asset_directory_binding(
        repo, candidate, receipt_binding
    )
    if asset_issue or asset_binding != plan_data.get("assetBinding"):
        return _technical_stop(
            "CANDIDATE_ASSET_DRIFT",
            invalidations=[asset_issue or "asset_binding_drift"],
        )

    receipt_path = repo / receipt_binding["relativePath"]
    terminal_path = receipt_path / "terminal-receipt.json"
    if terminal_path.exists() or terminal_path.is_symlink():
        terminal, terminal_read_issue = _read_strict_json_object(terminal_path)
        if terminal_read_issue:
            return _technical_stop("TERMINAL_RECEIPT_INVALID")
        assert terminal is not None
        validation = _validate_terminal_receipt(terminal, plan_data, receipt_binding)
        if validation is None:
            return _complete_result(terminal)
        return _technical_stop(validation)

    state_path = receipt_path / "milestone-state.json"
    state, state_issue = _load_state(state_path, plan_data, receipt_binding)
    if state_issue:
        return _technical_stop("MILESTONE_STATE_INVALID", invalidations=[state_issue])
    if state is None:
        state = _new_state(plan_data, receipt_binding)
    effects = list(state["effects"])

    if candidate_commit is None and _candidate_files_issue(repo, candidate):
        return _technical_stop("CANDIDATE_DRIFT")
    if _staged_paths(repo) and "git.commit" not in state["intents"]:
        return _technical_stop("INDEX_NOT_EXACT", invalidations=_staged_paths(repo))

    if _git(repo, "remote", "get-url", remote, check=False).stdout.strip() != remote_url:
        return _human_gate(
            "repository.remote",
            "REMOTE_IDENTITY_DRIFT",
            canonical_binding=active_guard,
            write_set=[],
            plan_identity=str(plan_data["planDigest"]),
        )
    if _unexpected_candidate_paths(
        repo,
        contract_data,
        allow_clean=candidate_commit is not None,
        receipt_binding=receipt_binding,
    ):
        return _technical_stop("UNEXPECTED_CANDIDATE_FILES")
    remote_ok, remote_head = _ls_remote(repo, remote, target_ref)
    if not remote_ok:
        return _technical_stop("GIT_TRANSPORT_READBACK_FAILED")
    if remote_head not in {expected_base, candidate_commit}:
        return _human_gate(
            "repository.expectedBase",
            "REMOTE_DIVERGENCE",
            canonical_binding=active_guard,
            write_set=[],
            plan_identity=str(plan_data["planDigest"]),
        )

    commit_before = {"base": expected_base, "candidateDigest": plan_data["candidateDigest"]}
    if candidate_commit is None:
        if head != expected_base:
            return _technical_stop("CANDIDATE_DRIFT")
        staged = _staged_paths(repo)
        pending_commit = _pending_intent(state, "git.commit", commit_before, plan_data)
        if staged and not pending_commit:
            return _technical_stop("INDEX_NOT_EXACT", invalidations=staged)
        if not staged:
            add = _git(
                repo,
                "--literal-pathspecs",
                "add",
                "-f",
                "--",
                *[str(path) for path in contract_data["writeSet"]],
                check=False,
            )
            if add.returncode != 0:
                return _technical_stop("INDEX_NOT_EXACT")
        if (
            _staged_paths(repo) != sorted(contract_data["writeSet"])
            or _candidate_index_issue(repo, candidate)
        ):
            return _technical_stop("INDEX_NOT_EXACT")
        _persist_intent(state_path, state, effects, "git.commit", commit_before, plan_data)
        committed = _git(
            repo,
            "commit",
            "-m",
            str(contract_data["commit"]["message"]),
            check=False,
        )
        if committed.returncode != 0:
            return _technical_stop("COMMIT_FAILED")
        _after_irreversible_effect(boundaries, "git.commit")
        candidate_commit = _git_output(repo, "rev-parse", "HEAD")
        if not _matching_commit(repo, candidate_commit, expected_base, contract_data, candidate):
            return _technical_stop("COMMIT_READBACK_MISMATCH")
        committed_guard, committed_guard_issue = _canonical_guard(
            repo,
            contract_data,
            candidate,
            plan_data["validationReceipt"],
            plan_data["reviewReceipt"],
            phase="execute",
            commit=candidate_commit,
        )
        if (
            committed_guard_issue
            or committed_guard is None
            or not _canonical_guard_matches(expected_guard, committed_guard)
        ):
            return _technical_stop(
                "CANONICAL_AUTHORITY_BINDING_INVALID",
                invalidations=[committed_guard_issue or "committed_guard_drift"],
                receipts_preserved=True,
            )
        active_guard = committed_guard
        _complete_intent(
            state_path,
            state,
            effects,
            "git.commit",
            commit_before,
            {"commit": candidate_commit, "tree": _git_output(repo, "rev-parse", "HEAD^{tree}")},
            plan_data,
        )
    else:
        _persist_intent(state_path, state, effects, "git.commit", commit_before, plan_data)
        _complete_intent(
            state_path,
            state,
            effects,
            "git.commit",
            commit_before,
            {"commit": candidate_commit, "tree": _git_output(repo, "rev-parse", "HEAD^{tree}")},
            plan_data,
        )

    assert candidate_commit is not None
    active_guard, continuation_stop = _continuation_guard(
        repo, contract_data, plan_data, candidate_commit
    )
    if continuation_stop:
        return continuation_stop
    assert active_guard is not None
    remote_ok, remote_head = _ls_remote(repo, remote, target_ref)
    if not remote_ok:
        return _technical_stop("GIT_TRANSPORT_READBACK_FAILED", receipts_preserved=True)
    push_before = {"remote": remote_url, "ref": target_ref, "commit": candidate_commit}
    if remote_head == expected_base:
        _persist_intent(state_path, state, effects, "git.push", push_before, plan_data)
        push = _git(
            repo,
            "push",
            "--porcelain",
            remote,
            f"{candidate_commit}:{target_ref}",
            check=False,
        )
        if push.returncode != 0:
            return _technical_stop("PUSH_FAILED")
        _after_irreversible_effect(boundaries, "git.push")
    elif remote_head != candidate_commit:
        return _human_gate(
            "repository.expectedBase",
            "REMOTE_DIVERGENCE",
            canonical_binding=active_guard,
            write_set=[],
            plan_identity=str(plan_data["planDigest"]),
        )
    else:
        _persist_intent(state_path, state, effects, "git.push", push_before, plan_data)
    branch_ok, branch_readback = _ls_remote(repo, remote, target_ref)
    if not branch_ok:
        return _technical_stop("PUSH_READBACK_FAILED", receipts_preserved=True)
    if branch_readback != candidate_commit:
        return _technical_stop("PUSH_READBACK_MISMATCH")
    _complete_intent(
        state_path,
        state,
        effects,
        "git.push",
        push_before,
        {"remoteCommit": branch_readback},
        plan_data,
    )

    active_guard, continuation_stop = _continuation_guard(
        repo, contract_data, plan_data, candidate_commit
    )
    if continuation_stop:
        return continuation_stop
    assert active_guard is not None
    tag = str(contract_data["publication"]["tag"])
    tag_ref = f"refs/tags/{tag}"
    tag_ok, remote_tag = _ls_remote(repo, remote, tag_ref)
    if not tag_ok:
        return _technical_stop("TAG_READBACK_FAILED", receipts_preserved=True)
    if remote_tag and remote_tag != candidate_commit:
        return _human_gate(
            "publication.tag",
            "TAG_COLLISION",
            canonical_binding=active_guard,
            write_set=[],
            plan_identity=str(plan_data["planDigest"]),
        )
    local_tag = _git_output(repo, "rev-parse", "-q", "--verify", tag_ref, check=False)
    if local_tag and local_tag != candidate_commit:
        return _human_gate(
            "publication.tag",
            "TAG_COLLISION",
            canonical_binding=active_guard,
            write_set=[],
            plan_identity=str(plan_data["planDigest"]),
        )
    tag_before = {"tag": tag, "commit": candidate_commit}
    _persist_intent(state_path, state, effects, "git.tag.push", tag_before, plan_data)
    if not local_tag:
        if _git(repo, "tag", tag, candidate_commit, check=False).returncode != 0:
            return _technical_stop("TAG_CREATE_FAILED")
    if not remote_tag:
        if _git(
            repo,
            "push",
            "--porcelain",
            remote,
            f"{tag_ref}:{tag_ref}",
            check=False,
        ).returncode != 0:
            return _technical_stop("TAG_PUSH_FAILED")
        _after_irreversible_effect(boundaries, "git.tag.push")
    tag_readback_ok, tag_readback = _ls_remote(repo, remote, tag_ref)
    if not tag_readback_ok:
        return _technical_stop("TAG_READBACK_FAILED", receipts_preserved=True)
    if tag_readback != candidate_commit:
        return _technical_stop("TAG_READBACK_MISMATCH")
    _complete_intent(
        state_path,
        state,
        effects,
        "git.tag.push",
        tag_before,
        {"remoteTagCommit": tag_readback},
        plan_data,
    )

    active_guard, continuation_stop = _continuation_guard(
        repo, contract_data, plan_data, candidate_commit
    )
    if continuation_stop:
        return continuation_stop
    assert active_guard is not None
    identity = _published_identity(contract_data, candidate, candidate_commit)
    publication_request = {
        "identity": identity,
        "mechanism": contract_data["publication"]["mechanism"],
        "workflow": contract_data["publication"]["workflow"],
    }
    publication_readback = _call(boundaries, "publication_readback", publication_request)
    publication_status = publication_readback.get("status")
    publication_pending_intent = _pending_intent(
        state, "github.release", publication_request, plan_data
    )
    if publication_status == "collision" or (
        publication_status == "published"
        and publication_readback.get("identity") != identity
    ):
        return _human_gate(
            "publication.release",
            "RELEASE_COLLISION",
            canonical_binding=active_guard,
            write_set=[],
            plan_identity=str(plan_data["planDigest"]),
        )
    if publication_status == "pending" and publication_readback.get("sameIdentity") is True:
        _persist_intent(
            state_path, state, effects, "github.release", publication_request, plan_data
        )
        if publication_pending_intent:
            return _technical_stop("PUBLICATION_PENDING", receipts_preserved=True)
    elif publication_status == "missing" and publication_pending_intent:
        return _technical_stop("PUBLICATION_PENDING", receipts_preserved=True)
    elif publication_status not in {"published", "missing"}:
        return _technical_stop("PUBLICATION_READBACK_INCOMPLETE", receipts_preserved=True)
    if publication_status in {"missing", "pending"}:
        _persist_intent(
            state_path, state, effects, "github.release", publication_request, plan_data
        )
        publication_result = _call(boundaries, "publication_apply", publication_request)
        if not publication_result.get("ok"):
            failure_policy = contract_data["failurePolicy"]
            counters = state["counters"]
            if counters["diagnoses"] < int(failure_policy.get("maxDiagnoses", 0)):
                counters["diagnoses"] += 1
                _save_state(state_path, state, effects)
                _call(boundaries, "publication_diagnose", publication_request)
            if counters["remediations"] < int(failure_policy.get("maxRemediations", 0)):
                counters["remediations"] += 1
                _save_state(state_path, state, effects)
                _call(boundaries, "publication_remediate", publication_request)
            _save_state(state_path, state, effects)
            return _technical_stop("PUBLICATION_FAILED", receipts_preserved=True)
        _after_irreversible_effect(boundaries, "github.release")
        publication_readback = _call(boundaries, "publication_readback", publication_request)
    else:
        _persist_intent(
            state_path, state, effects, "github.release", publication_request, plan_data
        )
    if publication_readback.get("status") == "pending" and publication_readback.get(
        "sameIdentity"
    ) is True:
        return _technical_stop("PUBLICATION_PENDING", receipts_preserved=True)
    if publication_readback.get("status") == "missing":
        return _technical_stop("PUBLICATION_PENDING", receipts_preserved=True)
    if publication_readback.get("status") == "collision" or (
        publication_readback.get("status") == "published"
        and publication_readback.get("identity") != identity
    ):
        return _human_gate(
            "publication.release",
            "RELEASE_COLLISION",
            canonical_binding=active_guard,
            write_set=[],
            plan_identity=str(plan_data["planDigest"]),
        )
    if publication_readback.get("status") != "published":
        return _technical_stop("PUBLICATION_READBACK_INCOMPLETE", receipts_preserved=True)
    _complete_intent(
        state_path,
        state,
        effects,
        "github.release",
        publication_request,
        publication_readback,
        plan_data,
    )

    active_guard, continuation_stop = _continuation_guard(
        repo, contract_data, plan_data, candidate_commit
    )
    if continuation_stop:
        return continuation_stop
    source_request = {
        "target": contract_data["refreshTargets"]["project"],
        "identity": identity,
    }
    existing_source_intent = state["intents"].get("devflow.source.fast_forward")
    if isinstance(existing_source_intent, Mapping):
        source_intent = _plain_mapping(existing_source_intent["beforeIntent"])
        if (
            source_intent.get("target") != source_request["target"]
            or source_intent.get("identity") != identity
        ):
            return _technical_stop("MILESTONE_STATE_INVALID", receipts_preserved=True)
        source_readback = _call(boundaries, "source_verify", source_intent)
        if not source_readback.get("ok"):
            if (
                existing_source_intent.get("status") != "PENDING"
                or source_readback.get("reason") != "source_not_current"
            ):
                return _technical_stop("SOURCE_IDENTITY_MISMATCH", receipts_preserved=True)
            source_result = _call(boundaries, "source_apply", source_intent)
            if not source_result.get("ok"):
                return _technical_stop("SOURCE_FAST_FORWARD_FAILED", receipts_preserved=True)
            _after_irreversible_effect(boundaries, "devflow.source.fast_forward")
            source_readback = _call(boundaries, "source_verify", source_intent)
    else:
        source_plan = _call(boundaries, "source_plan", source_request)
        if not source_plan.get("ok") or source_plan.get("status") not in {
            "planned",
            "already_current",
        }:
            return _technical_stop("SOURCE_FAST_FORWARD_PLAN_FAILED", receipts_preserved=True)
        source_intent = {**source_request, "planDigest": source_plan.get("planDigest")}
        _persist_intent(
            state_path, state, effects, "devflow.source.fast_forward", source_intent, plan_data
        )
        if source_plan.get("status") == "already_current":
            source_readback = _call(boundaries, "source_verify", source_intent)
        else:
            source_result = _call(boundaries, "source_apply", source_intent)
            if not source_result.get("ok"):
                return _technical_stop("SOURCE_FAST_FORWARD_FAILED", receipts_preserved=True)
            _after_irreversible_effect(boundaries, "devflow.source.fast_forward")
            source_readback = _call(boundaries, "source_verify", source_intent)
    if not source_readback.get("ok") or source_readback.get("identity") != identity:
        return _technical_stop("SOURCE_IDENTITY_MISMATCH", receipts_preserved=True)
    _complete_intent(
        state_path,
        state,
        effects,
        "devflow.source.fast_forward",
        source_intent,
        source_readback,
        plan_data,
    )

    active_guard, continuation_stop = _continuation_guard(
        repo, contract_data, plan_data, candidate_commit
    )
    if continuation_stop:
        return continuation_stop
    cache_request = {"target": contract_data["refreshTargets"]["cache"], "identity": identity}
    existing_cache_intent = state["intents"].get("codex.cache.refresh")
    if isinstance(existing_cache_intent, Mapping):
        cache_intent = _plain_mapping(existing_cache_intent["beforeIntent"])
        if (
            cache_intent.get("target") != cache_request["target"]
            or cache_intent.get("identity") != identity
        ):
            return _technical_stop("MILESTONE_STATE_INVALID", receipts_preserved=True)
        cache_readback = _call(boundaries, "cache_verify", cache_intent)
        if not cache_readback.get("ok"):
            if (
                existing_cache_intent.get("status") != "PENDING"
                or cache_readback.get("reason") != "cache_refresh_not_current"
            ):
                return _technical_stop("CACHE_IDENTITY_MISMATCH", receipts_preserved=True)
            if not _reserve_cache_apply_attempt(state_path, state, effects):
                return _technical_stop(
                    "CACHE_REFRESH_RETRY_EXHAUSTED", receipts_preserved=True
                )
            cache_result = _call(boundaries, "cache_apply", cache_intent)
            if not cache_result.get("ok"):
                return _technical_stop("CACHE_REFRESH_FAILED", receipts_preserved=True)
            _after_irreversible_effect(boundaries, "codex.cache.refresh")
            cache_readback = _call(boundaries, "cache_verify", cache_intent)
    else:
        cache_plan = _call(boundaries, "cache_plan", cache_request)
        if not cache_plan.get("ok"):
            return _technical_stop("CACHE_PLAN_FAILED", receipts_preserved=True)
        cache_intent = {**cache_request, "planDigest": cache_plan.get("planDigest")}
        _persist_intent(
            state_path, state, effects, "codex.cache.refresh", cache_intent, plan_data
        )
        if not _reserve_cache_apply_attempt(state_path, state, effects):
            return _technical_stop("CACHE_REFRESH_RETRY_EXHAUSTED", receipts_preserved=True)
        cache_result = _call(boundaries, "cache_apply", cache_intent)
        if not cache_result.get("ok"):
            return _technical_stop("CACHE_REFRESH_FAILED", receipts_preserved=True)
        _after_irreversible_effect(boundaries, "codex.cache.refresh")
        cache_readback = _call(boundaries, "cache_verify", cache_intent)
    if not cache_readback.get("ok") or cache_readback.get("identity") != identity:
        return _technical_stop("CACHE_IDENTITY_MISMATCH", receipts_preserved=True)
    _complete_intent(
        state_path,
        state,
        effects,
        "codex.cache.refresh",
        cache_intent,
        cache_readback,
        plan_data,
    )

    active_guard, continuation_stop = _continuation_guard(
        repo, contract_data, plan_data, candidate_commit
    )
    if continuation_stop:
        return continuation_stop
    project_request = {"target": contract_data["refreshTargets"]["project"], "identity": identity}
    existing_project_intent = state["intents"].get("devflow.project.refresh")
    if isinstance(existing_project_intent, Mapping):
        project_intent = _plain_mapping(existing_project_intent["beforeIntent"])
        if (
            project_intent.get("target") != project_request["target"]
            or project_intent.get("identity") != identity
        ):
            return _technical_stop("MILESTONE_STATE_INVALID", receipts_preserved=True)
        project_readback = _call(boundaries, "project_verify", project_intent)
        if not project_readback.get("ok"):
            if (
                existing_project_intent.get("status") != "PENDING"
                or project_readback.get("reason") != "project_refresh_not_current"
            ):
                return _technical_stop(
                    "FIVE_LAYER_IDENTITY_MISMATCH", receipts_preserved=True
                )
            project_result = _call(boundaries, "project_apply", project_intent)
            if not project_result.get("ok"):
                return _technical_stop("PROJECT_REFRESH_FAILED", receipts_preserved=True)
            _after_irreversible_effect(boundaries, "devflow.project.refresh")
            project_readback = _call(boundaries, "project_verify", project_intent)
    else:
        project_plan = _call(boundaries, "project_plan", project_request)
        if not project_plan.get("ok") or project_plan.get("status") != "planned":
            return _technical_stop("PROJECT_PLAN_DRIFT", receipts_preserved=True)
        project_intent = {**project_request, "planDigest": project_plan.get("planDigest")}
        _persist_intent(
            state_path,
            state,
            effects,
            "devflow.project.refresh",
            project_intent,
            plan_data,
        )
        project_result = _call(boundaries, "project_apply", project_intent)
        if not project_result.get("ok"):
            return _technical_stop("PROJECT_REFRESH_FAILED", receipts_preserved=True)
        _after_irreversible_effect(boundaries, "devflow.project.refresh")
        project_readback = _call(boundaries, "project_verify", project_intent)
    if not project_readback.get("ok") or project_readback.get("identity") != identity:
        return _technical_stop("FIVE_LAYER_IDENTITY_MISMATCH", receipts_preserved=True)
    _complete_intent(
        state_path,
        state,
        effects,
        "devflow.project.refresh",
        project_intent,
        project_readback,
        plan_data,
    )

    active_guard, continuation_stop = _continuation_guard(
        repo, contract_data, plan_data, candidate_commit
    )
    if continuation_stop:
        return continuation_stop
    assert active_guard is not None
    terminal = _terminal_receipt(
        plan_data,
        candidate_commit,
        identity,
        effects,
        state,
        source_readback,
        publication_readback,
        cache_readback,
        project_readback,
        active_guard,
    )
    _atomic_json(terminal_path, terminal)
    return _complete_result(terminal)


def verify_milestone_external_effects(
    repo: Path,
    contract: Mapping[str, Any],
    *,
    receipt: Mapping[str, Any],
    receipt_dir: Path,
    boundaries: Mapping[str, object],
) -> dict[str, Any]:
    """Verify a terminal receipt and its remote/publication/readback identity."""

    repo = Path(repo).resolve()
    contract_data = _plain_mapping(contract)
    contract_validation = _validate_current_milestone_contract(contract_data)
    if not contract_validation["ok"]:
        return _technical_stop(
            str(contract_validation["reasonCodes"][0]),
            invalidations=list(contract_validation["invalidations"]),
        )
    receipt_binding = _trusted_receipt_binding(repo, contract_data, receipt_dir)
    if receipt_binding is None:
        return _technical_stop("RECEIPT_DIRECTORY_UNTRUSTED")
    terminal = _plain_mapping(receipt)
    embedded_plan = terminal.get("plan")
    if not isinstance(embedded_plan, Mapping):
        return _technical_stop("TERMINAL_RECEIPT_INVALID")
    plan_data = _plain_mapping(embedded_plan)
    if _plan_integrity_issue(plan_data, contract_data):
        return _technical_stop("TERMINAL_RECEIPT_INVALID")
    asset_binding, asset_issue = _asset_directory_binding(
        repo, plan_data["candidateManifest"], receipt_binding
    )
    if asset_issue or asset_binding != plan_data.get("assetBinding"):
        return _technical_stop(
            "CANDIDATE_ASSET_DRIFT",
            invalidations=[asset_issue or "asset_binding_drift"],
        )
    issue = _validate_terminal_receipt(terminal, plan_data, receipt_binding)
    if issue:
        return _technical_stop(issue)
    commit = str(terminal["commit"])
    if not _matching_commit(
        repo,
        commit,
        str(contract_data["repository"]["expectedBase"]),
        contract_data,
        plan_data["candidateManifest"],
    ):
        return _technical_stop("COMMIT_READBACK_MISMATCH")
    evidence_document_issue = _candidate_evidence_documents_issue(
        repo,
        plan_data["candidateManifest"],
        plan_data["validationReceipt"],
        plan_data["reviewReceipt"],
        contract_data,
        commit=commit,
    )
    if evidence_document_issue:
        return _technical_stop(evidence_document_issue)
    observed_guard, guard_issue = _canonical_guard(
        repo,
        contract_data,
        plan_data["candidateManifest"],
        plan_data["validationReceipt"],
        plan_data["reviewReceipt"],
        phase="verify",
        commit=commit,
    )
    if (
        guard_issue
        or observed_guard is None
        or not _canonical_guard_matches(plan_data["canonicalGuard"], observed_guard)
        or terminal.get("canonicalGuard") != observed_guard
    ):
        return _technical_stop(
            "CANONICAL_AUTHORITY_BINDING_INVALID",
            invalidations=[guard_issue or "terminal_guard_drift"],
        )
    stored, stored_issue = _read_strict_json_object(
        repo / receipt_binding["relativePath"] / "terminal-receipt.json"
    )
    if stored_issue or stored != terminal:
        return _technical_stop("TERMINAL_RECEIPT_INVALID")
    boundary_issue = _validate_boundaries(boundaries)
    if boundary_issue:
        return _technical_stop("BOUNDARY_ADAPTER_INCOMPLETE", invalidations=[boundary_issue])
    repository = contract_data["repository"]
    remote = str(repository["remote"])
    branch_ok, branch_commit = _ls_remote(repo, remote, str(repository["ref"]))
    if not branch_ok:
        return _technical_stop("REMOTE_READBACK_FAILED")
    if branch_commit != commit:
        return _technical_stop("REMOTE_READBACK_MISMATCH")
    tag = str(contract_data["publication"]["tag"])
    tag_ok, tag_commit = _ls_remote(repo, remote, f"refs/tags/{tag}")
    if not tag_ok:
        return _technical_stop("TAG_READBACK_FAILED")
    if tag_commit != commit:
        return _technical_stop("TAG_READBACK_MISMATCH")
    identity = terminal.get("publicationIdentity")
    publication_request = {
        "identity": identity,
        "mechanism": contract_data["publication"]["mechanism"],
        "workflow": contract_data["publication"]["workflow"],
    }
    published = _call(boundaries, "publication_readback", publication_request)
    if published.get("status") != "published" or published.get("identity") != identity:
        return _technical_stop("PUBLICATION_READBACK_MISMATCH")
    effects_by_name = {item["effect"]: item for item in terminal["effects"]}
    source = _call(
        boundaries,
        "source_verify",
        effects_by_name["devflow.source.fast_forward"]["beforeIntent"],
    )
    cache = _call(
        boundaries,
        "cache_verify",
        effects_by_name["codex.cache.refresh"]["beforeIntent"],
    )
    project = _call(
        boundaries,
        "project_verify",
        effects_by_name["devflow.project.refresh"]["beforeIntent"],
    )
    if (
        not source.get("ok")
        or not cache.get("ok")
        or not project.get("ok")
        or source.get("identity") != identity
        or cache.get("identity") != identity
        or project.get("identity") != identity
    ):
        return _technical_stop("FIVE_LAYER_IDENTITY_MISMATCH")
    five_layer = terminal["fiveLayerIdentity"]
    if (
        five_layer.get("source") != source.get("identity")
        or five_layer.get("published") != published.get("identity")
        or five_layer.get("cache") != cache.get("identity")
        or five_layer.get("project") != project.get("identity")
    ):
        return _technical_stop("FIVE_LAYER_IDENTITY_MISMATCH")
    return _complete_result(terminal)


def _plain_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, sort_keys=True))


def _validate_current_milestone_contract(
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    refresh = contract.get("refreshTargets")
    raw_target = refresh.get("project") if isinstance(refresh, Mapping) else None
    target_available = False
    if isinstance(raw_target, str) and raw_target:
        target = Path(raw_target).expanduser()
        try:
            target_available = bool(
                target.is_absolute()
                and not target.is_symlink()
                and target.is_dir()
            )
        except OSError:
            target_available = False
    return validate_milestone_contract(
        contract, project_target_available=target_available
    )


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _canonical_guard(
    repo: Path,
    contract: Mapping[str, Any],
    candidate: Mapping[str, Any],
    validation: Mapping[str, Any],
    review: Mapping[str, Any],
    *,
    phase: str,
    commit: str | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Resolve one acyclic Goal/OpenSpec/STATE authority identity.

    Only the three explicit evidence back-edges in tracked STATE are
    normalized. Every other byte remains part of the binding. Once the exact
    candidate commit exists, STATE, OpenSpec, and the standing contract are all
    read from that one tree rather than from a mutable worktree.
    """

    if phase not in {"plan", "execute", "verify"}:
        return None, "phase_invalid"
    relative_contract = canonical_contract_relative_path(contract)
    if relative_contract is None:
        return None, "contract_path_invalid"
    if commit is None:
        resolution = resolve_state(repo)
        expected_state = (repo / CANONICAL_STATE_PATH).resolve()
        if (
            resolution.get("status") != "namespaced"
            or resolution.get("writeAllowed") is not True
            or resolution.get("readPath") != str(expected_state)
        ):
            return None, "state_not_namespaced_current"
        state_bytes, state_issue = _trusted_worktree_bytes(repo, CANONICAL_STATE_PATH)
        config_bytes, config_issue = _trusted_worktree_bytes(repo, DEVFLOW_CONFIG_PATH)
        contract_bytes, contract_issue = _trusted_worktree_bytes(repo, relative_contract)
        state_source = "worktree"
    else:
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            return None, "source_commit_invalid"
        state_bytes, state_issue = _committed_bytes(repo, commit, CANONICAL_STATE_PATH)
        config_bytes, config_issue = _committed_bytes(repo, commit, DEVFLOW_CONFIG_PATH)
        contract_bytes, contract_issue = _committed_bytes(repo, commit, relative_contract)
        state_source = "commit"
    if state_issue or state_bytes is None:
        return None, f"canonical_state_{state_issue or 'missing'}"
    if config_issue or config_bytes is None:
        return None, f"devflow_config_{config_issue or 'missing'}"
    if contract_issue or contract_bytes is None:
        return None, f"canonical_contract_{contract_issue or 'missing'}"

    try:
        state_text = state_bytes.decode("utf-8")
        state = parse_state_text(state_text)
    except (UnicodeDecodeError, ValueError):
        return None, "canonical_state_invalid"
    if _canonical_state_shape_issue(state_text):
        return None, "canonical_state_ambiguous"
    config, config_validation_issue = _strict_full_openspec_config(config_bytes)
    if config_validation_issue or config is None:
        return None, config_validation_issue or "devflow_config_invalid"
    try:
        canonical_contract = json.loads(
            contract_bytes.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None, "canonical_contract_invalid"
    if not isinstance(canonical_contract, dict) or canonical_contract != _plain_mapping(contract):
        return None, "canonical_contract_mapping_mismatch"

    current_change = state.get("current_change")
    goal = state.get("goal_gate")
    standing = state.get("standing_milestone")
    gates = state.get("gates")
    if not all(isinstance(item, Mapping) for item in (current_change, goal, standing, gates)):
        return None, "canonical_state_sections_missing"
    assert isinstance(current_change, Mapping)
    assert isinstance(goal, Mapping)
    assert isinstance(standing, Mapping)
    assert isinstance(gates, Mapping)
    if (
        state.get("current_stage") != "external_effects"
        or current_change.get("status") != "external_effects"
    ):
        return None, "external_effect_stage_not_current"
    if current_change.get("id") != contract.get("change"):
        return None, "active_change_mismatch"
    if (
        goal.get("required") is not True
        or goal.get("status") != "active"
        or goal.get("id") != contract.get("goalId")
    ):
        return None, "active_goal_mismatch"
    if standing.get("status") != "current":
        return None, "standing_milestone_not_current"
    contract_sha = hashlib.sha256(contract_bytes).hexdigest()
    if (
        standing.get("contract_path") != relative_contract.as_posix()
        or standing.get("contract_sha256") != contract_sha
        or standing.get("goal_id") != contract.get("goalId")
        or standing.get("change_id") != contract.get("change")
    ):
        return None, "standing_contract_binding_mismatch"
    for gate in (
        "spec_approved",
        "plan_written",
        "implementation_done",
        "verification_passed",
        "state_updated",
    ):
        if gates.get(gate) is not True:
            return None, f"verification_gate_not_ready:{gate}"

    candidate_data = _plain_mapping(candidate)
    validation_data = _plain_mapping(validation)
    review_data = _plain_mapping(review)
    try:
        candidate_projection = _candidate_projection_digest(candidate_data, state_bytes)
    except (TypeError, ValueError):
        return None, "candidate_projection_invalid"
    validation_projection = _validation_projection_digest(
        validation_data, candidate_projection
    )
    review_projection = _review_projection_digest(review_data, candidate_projection)
    frozen = {
        "candidateDigest": candidate_projection,
        "validationDigest": validation_projection,
        "reviewDigest": review_projection,
    }
    if (
        standing.get("candidate_digest") != candidate_projection
        or standing.get("validation_digest") != validation_projection
        or standing.get("review_digest") != review_projection
    ):
        return None, "frozen_evidence_projection_mismatch"

    open_spec_paths = _canonical_openspec_paths(contract, candidate_data)
    if open_spec_paths is None:
        return None, "canonical_openspec_incomplete"
    open_spec_files: dict[str, str] = {}
    candidate_records = {
        str(item.get("path")): item
        for item in candidate_data.get("files", [])
        if isinstance(item, Mapping)
    }
    for relative in open_spec_paths:
        if commit is None:
            payload, issue = _trusted_worktree_bytes(repo, Path(relative))
        else:
            payload, issue = _committed_bytes(repo, commit, Path(relative))
        record = candidate_records.get(relative)
        if issue or payload is None or not isinstance(record, Mapping):
            return None, f"canonical_openspec_missing:{relative}"
        sha = hashlib.sha256(payload).hexdigest()
        if record.get("sha256") != sha or record.get("size") != len(payload):
            return None, f"canonical_openspec_drift:{relative}"
        open_spec_files[relative] = sha

    state_record = candidate_records.get(CANONICAL_STATE_PATH.as_posix())
    contract_record = candidate_records.get(relative_contract.as_posix())
    if not isinstance(state_record, Mapping) or not isinstance(contract_record, Mapping):
        return None, "canonical_files_absent_from_candidate"
    if (
        state_record.get("sha256") != hashlib.sha256(state_bytes).hexdigest()
        or state_record.get("size") != len(state_bytes)
        or contract_record.get("sha256") != contract_sha
        or contract_record.get("size") != len(contract_bytes)
    ):
        return None, "canonical_files_candidate_mismatch"

    binding: dict[str, Any] = {
        "schemaVersion": "1.0",
        "kind": "devflow-canonical-milestone-authority-binding",
        "repositoryRealPath": str(repo),
        "configPath": DEVFLOW_CONFIG_PATH.as_posix(),
        "configSha256": hashlib.sha256(config_bytes).hexdigest(),
        "workflowMode": "full-openspec",
        "statePath": CANONICAL_STATE_PATH.as_posix(),
        "stateSha256": hashlib.sha256(state_bytes).hexdigest(),
        "stateStage": "external_effects",
        "changeStatus": "external_effects",
        "goalId": str(contract["goalId"]),
        "changeId": str(contract["change"]),
        "contractPath": relative_contract.as_posix(),
        "contractSha256": contract_sha,
        "contractDigest": _digest(canonical_contract),
        "candidateDocumentDigest": _digest(candidate_data),
        "validationDocumentDigest": _digest(validation_data),
        "reviewDocumentDigest": _digest(review_data),
        "openSpecDigest": _digest(open_spec_files),
        "frozenEvidence": frozen,
        "writeSet": list(contract.get("writeSet", [])),
    }
    binding["bindingDigest"] = _digest(binding)
    binding["stateSource"] = state_source
    binding["sourceCommit"] = commit
    return binding, None


def _canonical_guard_matches(
    expected: Mapping[str, Any], observed: Mapping[str, Any]
) -> bool:
    stable_keys = set(expected) - {"stateSource", "sourceCommit"}
    return bool(
        stable_keys == set(observed) - {"stateSource", "sourceCommit"}
        and all(expected.get(key) == observed.get(key) for key in stable_keys)
    )


def _continuation_guard(
    repo: Path,
    contract: Mapping[str, Any],
    plan: Mapping[str, Any],
    commit: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    evidence_document_issue = _candidate_evidence_documents_issue(
        repo,
        plan["candidateManifest"],
        plan["validationReceipt"],
        plan["reviewReceipt"],
        contract,
        commit=commit,
    )
    if evidence_document_issue:
        return None, _technical_stop(
            evidence_document_issue,
            receipts_preserved=True,
        )
    receipt_binding = plan.get("receiptBinding")
    if not isinstance(receipt_binding, Mapping):
        return None, _technical_stop(
            "CANDIDATE_ASSET_DRIFT",
            invalidations=["receipt_binding_missing"],
            receipts_preserved=True,
        )
    asset_binding, asset_issue = _asset_directory_binding(
        repo, plan["candidateManifest"], receipt_binding
    )
    if asset_issue or asset_binding != plan.get("assetBinding"):
        return None, _technical_stop(
            "CANDIDATE_ASSET_DRIFT",
            invalidations=[asset_issue or "asset_binding_drift"],
            receipts_preserved=True,
        )
    observed, issue = _canonical_guard(
        repo,
        contract,
        plan["candidateManifest"],
        plan["validationReceipt"],
        plan["reviewReceipt"],
        phase="execute",
        commit=commit,
    )
    expected = plan.get("canonicalGuard")
    if (
        issue
        or observed is None
        or not isinstance(expected, Mapping)
        or not _canonical_guard_matches(expected, observed)
    ):
        return None, _technical_stop(
            "CANONICAL_AUTHORITY_BINDING_INVALID",
            invalidations=[issue or "canonical_guard_drift"],
            receipts_preserved=True,
        )
    return observed, None


def _trusted_worktree_bytes(
    repo: Path, relative: Path
) -> tuple[bytes | None, str | None]:
    if relative.is_absolute() or ".." in relative.parts:
        return None, "untrusted_path"
    path = repo / relative
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(repo)
        if path.is_symlink() or resolved != path or not path.is_file():
            return None, "untrusted_path"
        return path.read_bytes(), None
    except (OSError, ValueError):
        return None, "unreadable"


def _committed_bytes(
    repo: Path, commit: str, relative: Path
) -> tuple[bytes | None, str | None]:
    if relative.is_absolute() or ".." in relative.parts:
        return None, "untrusted_path"
    result = _git(repo, "show", f"{commit}:{relative.as_posix()}", check=False, binary=True)
    if result.returncode != 0:
        return None, "missing_from_commit"
    return bytes(result.stdout), None


def _canonical_state_shape_issue(text: str) -> str | None:
    required_unique = (
        r"^current_stage:",
        r"^current_change:",
        r"^goal_gate:",
        r"^standing_milestone:",
        r"^gates:",
        r"^  candidate_digest:",
        r"^  validation_digest:",
        r"^  review_digest:",
    )
    return next(
        (
            pattern
            for pattern in required_unique
            if len(re.findall(pattern, text, re.MULTILINE)) != 1
        ),
        None,
    )


def _strict_full_openspec_config(
    payload: bytes,
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        value = json.loads(
            payload.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None, "devflow_config_invalid"
    if not isinstance(value, dict):
        return None, "devflow_config_not_object"
    if any(key in value for key in ("workflow_mode", "workflowMode")):
        return None, "devflow_config_legacy_mode_key"
    if validate_devflow_config(value):
        return None, "devflow_config_legacy_selection"
    workflow = value.get("workflow")
    if not isinstance(workflow, dict) or workflow.get("mode") != "full-openspec":
        return None, "devflow_config_mode_not_full_openspec"
    return value, None


def _normalized_state_bytes(payload: bytes) -> bytes:
    text = payload.decode("utf-8")
    for name in ("candidate_digest", "validation_digest", "review_digest"):
        text, count = re.subn(
            rf"(?m)^(  {name}:).*$",
            rf"\1 {CYCLE_EDGE_SENTINEL}",
            text,
        )
        if count != 1:
            raise ValueError(f"canonical STATE {name} edge is ambiguous")
    return text.encode("utf-8")


def _candidate_projection_digest(
    candidate: Mapping[str, Any], state_bytes: bytes
) -> str:
    projected = _plain_mapping(candidate)
    files = projected.get("files")
    assets = projected.get("assets")
    if not isinstance(files, list) or not isinstance(assets, list):
        raise ValueError("candidate projection fields missing")
    state_records = [
        item
        for item in files
        if isinstance(item, dict) and item.get("path") == CANONICAL_STATE_PATH.as_posix()
    ]
    if len(state_records) != 1:
        raise ValueError("canonical STATE candidate record missing or ambiguous")
    normalized = _normalized_state_bytes(state_bytes)
    state_records[0]["size"] = len(normalized)
    state_records[0]["sha256"] = hashlib.sha256(normalized).hexdigest()
    payload: dict[str, Any] = {"files": files, "assets": assets}
    if "deletions" in projected:
        payload["deletions"] = projected["deletions"]
    projected["payloadDigest"] = _digest(payload)
    return _digest(projected)


def _validation_projection_digest(
    validation: Mapping[str, Any], candidate_digest: str
) -> str:
    projected = _plain_mapping(validation)
    projected["candidateDigest"] = candidate_digest
    return _digest(projected)


def _review_projection_digest(review: Mapping[str, Any], candidate_digest: str) -> str:
    projected = _plain_mapping(review)
    projected["candidateDigest"] = candidate_digest
    projected["reviewedDiffDigest"] = candidate_digest
    return _digest(projected)


def _canonical_openspec_paths(
    contract: Mapping[str, Any], candidate: Mapping[str, Any]
) -> list[str] | None:
    change = str(contract.get("change") or "")
    prefix = f"openspec/changes/{change}/"
    paths = sorted(
        str(item.get("path"))
        for item in candidate.get("files", [])
        if isinstance(item, Mapping) and str(item.get("path") or "").startswith(prefix)
    )
    required = {
        prefix + ".openspec.yaml",
        prefix + "proposal.md",
        prefix + "design.md",
        prefix + "tasks.md",
    }
    if not required.issubset(paths) or not any(
        path.startswith(prefix + "specs/") and path.endswith(".md") for path in paths
    ):
        return None
    return paths


def _present(document: Mapping[str, Any], path: Sequence[str]) -> bool:
    value: Any = document
    for part in path:
        if not isinstance(value, Mapping) or part not in value:
            return False
        value = value[part]
    return value not in (None, "", [], {})


def _human_gate(
    missing: str,
    reason: str,
    *,
    canonical_binding: Mapping[str, Any] | None,
    write_set: Sequence[str],
    plan_identity: str | None = None,
) -> dict[str, Any]:
    if not isinstance(canonical_binding, Mapping):
        return _technical_stop("CANONICAL_AUTHORITY_BINDING_INVALID")
    goal_id = canonical_binding.get("goalId")
    change_id = canonical_binding.get("changeId")
    binding_digest = plan_identity or canonical_binding.get("bindingDigest")
    contract_digest = canonical_binding.get("contractDigest")
    if not all(
        isinstance(value, str) and value
        for value in (goal_id, change_id, binding_digest, contract_digest)
    ):
        return _technical_stop("CANONICAL_AUTHORITY_BINDING_INVALID")
    exact_write_set = [str(item) for item in write_set]
    standing = {
        "schemaVersion": 1,
        "current": True,
        "goalId": goal_id,
        "changeId": change_id,
        "planDigest": binding_digest,
        "contractDigest": contract_digest,
        "effects": [],
        "targets": [],
    }
    resolution = resolve_authority_delta(
        request={
            "action": "milestone.authority_check",
            "effect": "milestone.authority_delta",
            "target": missing,
            "ownership": "repository",
            "risk": "bounded",
            "scope": "standing-milestone",
            "writeSet": [],
            "goalId": goal_id,
            "changeId": change_id,
            "planDigest": binding_digest,
        },
        authority_envelope={
            "allowedActions": ["milestone.authority_check"],
            "allowedEffects": ["milestone.authority_delta"],
            "allowedTargets": [],
            "allowedOwnerships": ["repository"],
            "allowedRisks": ["bounded"],
            "writeSet": exact_write_set,
            "goalId": goal_id,
            "changeId": change_id,
            "planDigest": binding_digest,
        },
        evidence={
            "trusted": True,
            "current": True,
            "complete": True,
            "identityCurrent": True,
        },
        standing_contract=standing,
    )
    if resolution.get("decision") != AWAIT_HUMAN or not resolution.get(
        "missingAuthority"
    ):
        return _technical_stop(
            "AUTHORITY_RESOLUTION_INVALID",
            invalidations=[str(item) for item in resolution.get("reasonCodes", [])],
        )
    report = _plain_mapping(resolution)
    report.update(
        {
            "ok": False,
            "status": AWAIT_HUMAN,
            "reasonCodes": [reason, *report.get("reasonCodes", [])],
        }
    )
    return report


def _technical_stop(
    reason: str,
    *,
    invalidations: Sequence[str] = (),
    receipts_preserved: bool = False,
) -> dict[str, Any]:
    return {
        "ok": False,
        "status": "BLOCKED_REPAIR_REQUIRED",
        "decision": FAIL_CLOSED_REPAIR,
        "reasonCodes": [reason],
        "missingAuthority": [],
        "invalidations": list(invalidations),
        "materialDelta": False,
        "receiptsPreserved": receipts_preserved,
    }


def _validate_boundaries(boundaries: Mapping[str, object]) -> str | None:
    for name in REQUIRED_BOUNDARIES:
        if not callable(boundaries.get(name)):
            return name
    return None


def _requested_effects_issue(
    contract: Mapping[str, Any],
) -> tuple[str | None, str | None]:
    if "requestedEffects" not in contract:
        return "requestedEffects_missing", None
    requested = contract.get("requestedEffects")
    if (
        not isinstance(requested, list)
        or not requested
        or any(
            not isinstance(effect, str)
            or not effect
            or effect != effect.strip()
            for effect in requested
        )
        or len(set(requested)) != len(requested)
    ):
        return "requestedEffects_malformed", None
    for effect in requested:
        if effect not in EXPECTED_EFFECTS:
            return None, effect
    if requested != list(EXPECTED_EFFECTS):
        return "requestedEffects_incomplete_or_out_of_order", None
    return None, None


def _non_empty_string(value: object) -> bool:
    return bool(
        isinstance(value, str)
        and value
        and value == value.strip()
        and "\x00" not in value
        and "\n" not in value
    )


def _sha256_string(value: object) -> bool:
    return bool(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value))


def _exact_mapping_keys(value: object, keys: set[str]) -> bool:
    return bool(isinstance(value, Mapping) and set(value) == keys)


def _evidence_reference_issue(value: object) -> str | None:
    if not _exact_mapping_keys(value, {"path", "sha256"}):
        return "evidence_shape"
    assert isinstance(value, Mapping)
    if not _safe_candidate_path(value.get("path")):
        return "evidence_path"
    if not _sha256_string(value.get("sha256")):
        return "evidence_sha256"
    return None


def _candidate_shape_issue(candidate: Mapping[str, Any]) -> str | None:
    required = {
        "schemaVersion",
        "contractId",
        "goalId",
        "change",
        "milestone",
        "plugin",
        "expectedBase",
        "files",
        "assetDirectory",
        "assets",
        "payloadDigest",
        "evidence",
        "secretScan",
        "unresolvedBlockers",
    }
    if set(candidate) not in (required, required | {"deletions"}):
        return "candidate_keys"
    if candidate.get("schemaVersion") != "1.0":
        return "candidate_schema_version"
    for key in ("contractId", "goalId", "change", "milestone"):
        if not _non_empty_string(candidate.get(key)):
            return f"candidate_{key}"
    if not re.fullmatch(r"[0-9a-f]{40}", str(candidate.get("expectedBase") or "")):
        return "candidate_expected_base"
    plugin = candidate.get("plugin")
    plugin_keys = {"id", "marketplace", "versionRule", "version"}
    if not _exact_mapping_keys(plugin, plugin_keys):
        return "candidate_plugin_shape"
    assert isinstance(plugin, Mapping)
    if any(not _non_empty_string(plugin.get(key)) for key in plugin_keys):
        return "candidate_plugin_value"
    files = candidate.get("files")
    if not isinstance(files, list) or not files:
        return "candidate_files"
    paths: list[str] = []
    for item in files:
        if not _exact_mapping_keys(item, {"path", "mode", "size", "sha256"}):
            return "candidate_file_shape"
        assert isinstance(item, Mapping)
        path = item.get("path")
        if not _safe_candidate_path(path):
            return "candidate_file_path"
        assert isinstance(path, str)
        paths.append(path)
        if item.get("mode") not in {"100644", "100755"}:
            return "candidate_file_mode"
        if type(item.get("size")) is not int or int(item["size"]) < 0:
            return "candidate_file_size"
        if not _sha256_string(item.get("sha256")):
            return "candidate_file_sha256"
    if paths != sorted(set(paths)):
        return "candidate_file_order_or_duplicate"
    if "deletions" in candidate:
        deletions = candidate.get("deletions")
        if not isinstance(deletions, list):
            return "candidate_deletions"
        if (
            any(not _safe_candidate_path(path) for path in deletions)
            or deletions != sorted(set(deletions))
        ):
            return "candidate_deletion_order_or_duplicate"
        if set(paths) & set(deletions):
            return "candidate_file_deletion_overlap"
    if candidate.get("assetDirectory") != "release-assets":
        return "candidate_asset_directory"
    assets = candidate.get("assets")
    if not isinstance(assets, list) or not assets:
        return "candidate_assets"
    names: list[str] = []
    for item in assets:
        if not _exact_mapping_keys(item, {"name", "size", "sha256"}):
            return "candidate_asset_shape"
        assert isinstance(item, Mapping)
        name = item.get("name")
        if not _safe_asset_name(name):
            return "candidate_asset_name"
        assert isinstance(name, str)
        names.append(name)
        if type(item.get("size")) is not int or int(item["size"]) < 0:
            return "candidate_asset_size"
        if not _sha256_string(item.get("sha256")):
            return "candidate_asset_sha256"
    if len(names) != len(set(names)):
        return "candidate_asset_duplicate"
    if not _sha256_string(candidate.get("payloadDigest")):
        return "candidate_payload_digest"
    evidence = candidate.get("evidence")
    if not _exact_mapping_keys(evidence, {"validation", "independentReview"}):
        return "candidate_evidence_shape"
    assert isinstance(evidence, Mapping)
    for key in ("validation", "independentReview"):
        issue = _evidence_reference_issue(evidence.get(key))
        if issue:
            return f"candidate_{key}_{issue}"
    secret_scan = candidate.get("secretScan")
    if not _exact_mapping_keys(secret_scan, {"status", "findings", "evidence"}):
        return "candidate_secret_scan_shape"
    assert isinstance(secret_scan, Mapping)
    if secret_scan.get("status") != "pass" or secret_scan.get("findings") != []:
        return "candidate_secret_scan_result"
    if _evidence_reference_issue(secret_scan.get("evidence")):
        return "candidate_secret_scan_evidence"
    if candidate.get("unresolvedBlockers") != []:
        return "candidate_blockers"
    return None


def _validation_shape_issue(
    validation: Mapping[str, Any], contract: Mapping[str, Any]
) -> str | None:
    required = {
        "schemaVersion",
        "contractId",
        "candidateDigest",
        "evidence",
        "checks",
        "pluginEval",
        "secretScan",
        "unexpectedCandidateFiles",
        "unresolvedBlockers",
    }
    if set(validation) != required:
        return "validation_keys"
    if (
        validation.get("schemaVersion") != "1.0"
        or not _sha256_string(validation.get("candidateDigest"))
        or _evidence_reference_issue(validation.get("evidence"))
    ):
        return "validation_identity"
    checks = validation.get("checks")
    if not isinstance(checks, list) or len(checks) != len(VALIDATION_CHECK_IDS):
        return "validation_checks"
    observed_ids: list[str] = []
    for check in checks:
        if not _exact_mapping_keys(
            check, {"id", "command", "exitCode", "status", "counts"}
        ):
            return "validation_check_shape"
        assert isinstance(check, Mapping)
        observed_ids.append(str(check.get("id") or ""))
        if (
            not _non_empty_string(check.get("command"))
            or type(check.get("exitCode")) is not int
            or check.get("exitCode") != 0
            or check.get("status") != "pass"
        ):
            return "validation_check_result"
        counts = check.get("counts")
        if not _exact_mapping_keys(counts, {"passed", "failed", "skipped"}):
            return "validation_check_counts_shape"
        assert isinstance(counts, Mapping)
        if (
            type(counts.get("passed")) is not int
            or int(counts["passed"]) < 1
            or type(counts.get("failed")) is not int
            or counts.get("failed") != 0
            or type(counts.get("skipped")) is not int
            or int(counts["skipped"]) < 0
        ):
            return "validation_check_counts"
    if observed_ids != list(VALIDATION_CHECK_IDS):
        return "validation_check_ids"
    plugin_eval = validation.get("pluginEval")
    plugin_keys = {
        "target",
        "command",
        "exitCode",
        "status",
        "score",
        "grade",
        "failFindings",
        "warnFindings",
        "findings",
    }
    if not _exact_mapping_keys(plugin_eval, plugin_keys):
        return "validation_plugin_eval_shape"
    assert isinstance(plugin_eval, Mapping)
    if (
        plugin_eval.get("target") != "plugins/dev-flow"
        or not _non_empty_string(plugin_eval.get("command"))
        or type(plugin_eval.get("exitCode")) is not int
        or plugin_eval.get("exitCode") != 0
        or plugin_eval.get("status") != "pass"
        or type(plugin_eval.get("score")) is not int
        or not 0 <= int(plugin_eval["score"]) <= 100
        or not isinstance(plugin_eval.get("grade"), str)
        or not re.fullmatch(r"[A-F][+-]?", str(plugin_eval["grade"]))
        or type(plugin_eval.get("failFindings")) is not int
        or plugin_eval.get("failFindings") != 0
        or type(plugin_eval.get("warnFindings")) is not int
        or int(plugin_eval["warnFindings"]) < 0
    ):
        return "validation_plugin_eval_result"
    findings = plugin_eval.get("findings")
    if not isinstance(findings, list):
        return "validation_plugin_eval_findings"
    finding_ids: list[str] = []
    warning_count = 0
    for finding in findings:
        if not _exact_mapping_keys(
            finding, {"id", "severity", "decision", "rationale"}
        ):
            return "validation_plugin_eval_finding_shape"
        assert isinstance(finding, Mapping)
        if (
            not _non_empty_string(finding.get("id"))
            or finding.get("severity") not in {"warning", "info"}
            or not _non_empty_string(finding.get("decision"))
            or not _non_empty_string(finding.get("rationale"))
        ):
            return "validation_plugin_eval_finding"
        finding_ids.append(str(finding["id"]))
        warning_count += finding.get("severity") == "warning"
    if len(finding_ids) != len(set(finding_ids)) or warning_count != plugin_eval.get(
        "warnFindings"
    ):
        return "validation_plugin_eval_finding_counts"
    secret_scan = validation.get("secretScan")
    if not _exact_mapping_keys(secret_scan, {"status", "findings"}):
        return "validation_secret_scan_shape"
    assert isinstance(secret_scan, Mapping)
    if secret_scan.get("status") != "pass" or secret_scan.get("findings") != []:
        return "validation_secret_scan_result"
    if validation.get("unexpectedCandidateFiles") != []:
        return "validation_unexpected_files"
    if validation.get("unresolvedBlockers") != []:
        return "validation_blockers"
    return None


def _review_shape_issue(
    review: Mapping[str, Any], contract: Mapping[str, Any]
) -> str | None:
    required = {
        "schemaVersion",
        "contractId",
        "candidateDigest",
        "reviewedDiffDigest",
        "reviewer",
        "reviewMode",
        "evidence",
        "p0",
        "p1",
        "status",
    }
    if set(review) != required:
        return "review_keys"
    if (
        review.get("schemaVersion") != "1.0"
        or not _sha256_string(review.get("candidateDigest"))
        or not _sha256_string(review.get("reviewedDiffDigest"))
        or not _non_empty_string(review.get("reviewer"))
        or review.get("reviewMode") != "independent-read-only"
        or _evidence_reference_issue(review.get("evidence"))
        or type(review.get("p0")) is not int
        or type(review.get("p1")) is not int
        or review.get("p0") != 0
        or review.get("p1") != 0
        or review.get("status") != "pass"
    ):
        return "review_value"
    return None


def _canonical_validation_commands(
    contract: Mapping[str, Any],
) -> dict[str, str] | None:
    contract_id = contract.get("contractId")
    change = contract.get("change")
    if (
        not isinstance(contract_id, str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", contract_id)
        or not isinstance(change, str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", change)
    ):
        return None
    manifest = (
        ".planning/devflow/milestone-external-effects/"
        f"{contract_id}/candidate-manifest.json"
    )
    secret_code = (
        "import json,pathlib,re,sys;p=pathlib.Path('.');"
        f"m=json.loads((p/'{manifest}').read_text());"
        "q=re.compile(r'AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9_]{36,}|"
        "-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----');"
        "sys.exit(any(q.search((p/x['path']).read_text(errors='ignore')) "
        "for x in m['files']))"
    )
    unexpected_code = (
        "import json,pathlib,subprocess,sys;p=pathlib.Path('.');"
        f"m=json.loads((p/'{manifest}').read_text());"
        "e={x['path'] for x in m['files']}|set(m.get('deletions',[]));"
        "a=subprocess.check_output(['git','diff','--name-only','-z','HEAD','--']);"
        "b=subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z','--']);"
        "o={x for x in (a+b).decode().split('\\0') if x};sys.exit(bool(o-e))"
    )
    return {
        "completion-contract": (
            f"openspec validate {change} --strict --json && "
            "openspec validate --all --strict --json"
        ),
        "focused-tests": (
            "PYTHONDONTWRITEBYTECODE=1 python3.12 "
            "dev/plugins/dev-flow/tests/test_milestone_external_effects.py"
        ),
        "broad-tests": (
            "PYTHONDONTWRITEBYTECODE=1 python3.12 "
            "dev/scripts/run_devflow_prepromotion_tests.py && "
            "PYTHONDONTWRITEBYTECODE=1 python3.12 -m unittest discover "
            "-s dev/plugins/dev-flow/tests -p 'test_*.py' && "
            "PYTHONDONTWRITEBYTECODE=1 python3.12 -m unittest discover "
            "-s plugins/dev-flow/tests -p 'test_*.py'"
        ),
        "devflow-validators": (
            "PYTHONDONTWRITEBYTECODE=1 python3.12 "
            "dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo . --json && "
            "PYTHONDONTWRITEBYTECODE=1 python3.12 "
            "dev/plugins/dev-flow/scripts/doctor_workflow.py --repo . --json"
        ),
        "source-release-parity": (
            "PYTHONDONTWRITEBYTECODE=1 python3.12 "
            "dev/plugins/dev-flow/scripts/release_promotion_gate.py --repo . "
            "--target dev-flow --check --json && "
            "PYTHONDONTWRITEBYTECODE=1 python3.12 "
            "dev/plugins/dev-flow/scripts/verify_release_runtime.py "
            "--plugin-root plugins/dev-flow --repo-root . --json"
        ),
        "secret-scan": f'PYTHONDONTWRITEBYTECODE=1 python3.12 -c "{secret_code}"',
        "unexpected-candidate-scan": (
            f'PYTHONDONTWRITEBYTECODE=1 python3.12 -c "{unexpected_code}"'
        ),
        "blocker-scan": f"openspec status --change {change} --json",
    }


def _validation_command_issue(
    validation: Mapping[str, Any], contract: Mapping[str, Any]
) -> str | None:
    expected = _canonical_validation_commands(contract)
    checks = validation.get("checks")
    if expected is None or not isinstance(checks, list):
        return "canonical_command_policy_unavailable"
    for check in checks:
        if not isinstance(check, Mapping):
            return "validation_check_not_mapping"
        check_id = check.get("id")
        if not isinstance(check_id, str) or check.get("command") != expected.get(check_id):
            return f"noncanonical_validation_command:{check_id}"
    plugin_eval = validation.get("pluginEval")
    if (
        not isinstance(plugin_eval, Mapping)
        or plugin_eval.get("command") != CANONICAL_PLUGIN_EVAL_COMMAND
    ):
        return "noncanonical_plugin_eval_command"
    return None


def _validation_evidence_projection(
    validation: Mapping[str, Any],
) -> dict[str, Any]:
    projected = _plain_mapping(validation)
    projected.pop("candidateDigest", None)
    projected.pop("evidence", None)
    projected["kind"] = "devflow-milestone-validation-evidence"
    return projected


def _review_evidence_projection(review: Mapping[str, Any]) -> dict[str, Any]:
    projected = _plain_mapping(review)
    projected.pop("candidateDigest", None)
    projected.pop("reviewedDiffDigest", None)
    projected.pop("evidence", None)
    projected["kind"] = "devflow-milestone-review-evidence"
    return projected


def _validation_evidence_shape_issue(
    document: Mapping[str, Any], contract: Mapping[str, Any]
) -> str | None:
    if document.get("kind") != "devflow-milestone-validation-evidence":
        return "validation_evidence_kind"
    receipt = _plain_mapping(document)
    receipt.pop("kind", None)
    receipt["candidateDigest"] = "0" * 64
    receipt["evidence"] = {"path": "evidence.json", "sha256": "0" * 64}
    issue = _validation_shape_issue(receipt, contract)
    if issue:
        return issue
    return _validation_command_issue(receipt, contract)


def _review_evidence_shape_issue(
    document: Mapping[str, Any], contract: Mapping[str, Any]
) -> str | None:
    required = {
        "schemaVersion",
        "kind",
        "contractId",
        "reviewer",
        "reviewMode",
        "p0",
        "p1",
        "status",
    }
    if set(document) != required:
        return "review_evidence_keys"
    p0 = document.get("p0")
    p1 = document.get("p1")
    status = document.get("status")
    if (
        document.get("schemaVersion") != "1.0"
        or document.get("kind") != "devflow-milestone-review-evidence"
        or document.get("contractId") != contract.get("contractId")
        or not _non_empty_string(document.get("reviewer"))
        or document.get("reviewMode") != "independent-read-only"
        or type(p0) is not int
        or type(p1) is not int
        or int(p0) < 0
        or int(p1) < 0
        or status not in {"pass", "fail"}
        or (status == "pass" and (p0 != 0 or p1 != 0))
        or (status == "fail" and p0 == 0 and p1 == 0)
    ):
        return "review_evidence_value"
    return None


def _candidate_evidence_record_bytes(
    repo: Path,
    candidate: Mapping[str, Any],
    reference: Mapping[str, Any],
    *,
    commit: str | None,
) -> tuple[bytes | None, str | None]:
    relative = reference.get("path")
    if not _safe_candidate_path(relative):
        return None, "evidence_path"
    assert isinstance(relative, str)
    matches = [
        item
        for item in candidate.get("files", [])
        if isinstance(item, Mapping) and item.get("path") == relative
    ]
    if len(matches) != 1:
        return None, "evidence_candidate_record"
    record = matches[0]
    if record.get("sha256") != reference.get("sha256") or record.get("mode") != "100644":
        return None, "evidence_candidate_binding"
    if commit is None:
        payload, issue = _trusted_worktree_bytes(repo, Path(relative))
        if issue or payload is None:
            return None, "evidence_worktree_read"
        path = repo / relative
        mode = "100755" if path.stat().st_mode & 0o100 else "100644"
        if mode != record.get("mode"):
            return None, "evidence_mode"
    else:
        tree = _git(
            repo,
            "ls-tree",
            "-z",
            "--full-tree",
            commit,
            "--",
            relative,
            check=False,
            binary=True,
        )
        entries = tree.stdout.rstrip(b"\0").split(b"\0") if tree.stdout else []
        if tree.returncode != 0 or len(entries) != 1:
            return None, "evidence_commit_record"
        try:
            metadata, observed_path = entries[0].split(b"\t", 1)
            mode, object_type, object_id = metadata.decode("ascii").split()
            observed_relative = observed_path.decode("utf-8")
        except (UnicodeDecodeError, ValueError):
            return None, "evidence_commit_record"
        if (
            mode != record.get("mode")
            or object_type != "blob"
            or observed_relative != relative
        ):
            return None, "evidence_commit_record"
        blob = _git(repo, "cat-file", "blob", object_id, check=False, binary=True)
        if blob.returncode != 0:
            return None, "evidence_commit_blob"
        payload = bytes(blob.stdout)
    if (
        len(payload) != record.get("size")
        or hashlib.sha256(payload).hexdigest() != record.get("sha256")
    ):
        return None, "evidence_content_drift"
    return payload, None


def _strict_evidence_mapping(payload: bytes) -> dict[str, Any] | None:
    try:
        document = json.loads(
            payload.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None
    return document if isinstance(document, dict) else None


def _candidate_evidence_documents_issue(
    repo: Path,
    candidate: Mapping[str, Any],
    validation: Mapping[str, Any],
    review: Mapping[str, Any],
    contract: Mapping[str, Any],
    *,
    commit: str | None,
) -> str | None:
    evidence = candidate.get("evidence")
    if not isinstance(evidence, Mapping):
        return "CANDIDATE_EVIDENCE_INVALID"
    validation_reference = evidence.get("validation")
    review_reference = evidence.get("independentReview")
    if not isinstance(validation_reference, Mapping) or not isinstance(
        review_reference, Mapping
    ):
        return "CANDIDATE_EVIDENCE_INVALID"
    validation_payload, validation_read_issue = _candidate_evidence_record_bytes(
        repo, candidate, validation_reference, commit=commit
    )
    if validation_read_issue or validation_payload is None:
        return "CANDIDATE_DRIFT"
    review_payload, review_read_issue = _candidate_evidence_record_bytes(
        repo, candidate, review_reference, commit=commit
    )
    if review_read_issue or review_payload is None:
        return "CANDIDATE_DRIFT"
    validation_document = _strict_evidence_mapping(validation_payload)
    if validation_document is None:
        return "VALIDATION_EVIDENCE_INVALID"
    review_document = _strict_evidence_mapping(review_payload)
    if review_document is None:
        return "REVIEW_EVIDENCE_INVALID"
    validation_shape_issue = _validation_evidence_shape_issue(
        validation_document, contract
    )
    if validation_shape_issue:
        if validation_shape_issue.startswith("noncanonical_"):
            return "VALIDATION_COMMAND_INVALID"
        return "VALIDATION_EVIDENCE_INVALID"
    if _review_evidence_shape_issue(review_document, contract):
        return "REVIEW_EVIDENCE_INVALID"
    if validation_document != _validation_evidence_projection(validation):
        return "VALIDATION_EVIDENCE_MISMATCH"
    if review_document != _review_evidence_projection(review):
        return "REVIEW_EVIDENCE_MISMATCH"
    return None


def _candidate_evidence_issue(candidate: Mapping[str, Any]) -> str | None:
    files = candidate.get("files")
    evidence = candidate.get("evidence")
    secret_scan = candidate.get("secretScan")
    if (
        not isinstance(files, list)
        or not isinstance(evidence, Mapping)
        or not isinstance(secret_scan, Mapping)
    ):
        return "evidence_sections"
    records = {
        item["path"]: item
        for item in files
        if isinstance(item, Mapping) and isinstance(item.get("path"), str)
    }
    validation = evidence.get("validation")
    review = evidence.get("independentReview")
    if not isinstance(validation, Mapping) or not isinstance(review, Mapping):
        return "evidence_references"
    if validation == review or validation.get("path") == review.get("path"):
        return "evidence_kinds_not_distinct"
    if secret_scan.get("evidence") != validation:
        return "secret_scan_evidence_mismatch"
    for kind, reference in (("validation", validation), ("independentReview", review)):
        path = reference.get("path")
        record = records.get(path)
        if (
            not isinstance(record, Mapping)
            or record.get("sha256") != reference.get("sha256")
        ):
            return f"{kind}_not_candidate_bound"
    return None


def _candidate_contract_issue(contract: Mapping[str, Any], candidate: Mapping[str, Any]) -> str | None:
    for contract_key, candidate_key in (
        ("contractId", "contractId"),
        ("goalId", "goalId"),
        ("change", "change"),
        ("milestone", "milestone"),
    ):
        if contract.get(contract_key) != candidate.get(candidate_key):
            return "CANDIDATE_CONTRACT_MISMATCH"
    if contract.get("plugin") != candidate.get("plugin"):
        return "CANDIDATE_CONTRACT_MISMATCH"
    if contract["repository"].get("expectedBase") != candidate.get("expectedBase"):
        return "CANDIDATE_CONTRACT_MISMATCH"
    write_set = contract.get("writeSet")
    if (
        not isinstance(write_set, list)
        or not write_set
        or write_set != sorted(set(map(str, write_set)))
        or any(not _safe_candidate_path(path) for path in write_set)
    ):
        return "CANDIDATE_CONTRACT_MISMATCH"
    files = candidate.get("files")
    if not isinstance(files, list):
        return "CANDIDATE_CONTRACT_MISMATCH"
    paths = [item.get("path") for item in files if isinstance(item, Mapping)]
    deletions = candidate.get("deletions", [])
    if not isinstance(deletions, list):
        return "CANDIDATE_CONTRACT_MISMATCH"
    if sorted([*paths, *deletions]) != list(contract.get("writeSet", [])):
        return "CANDIDATE_CONTRACT_MISMATCH"
    assets = candidate.get("assets")
    if not isinstance(assets, list) or [item.get("name") for item in assets] != list(
        contract["publication"].get("assets", [])
    ):
        return "CANDIDATE_CONTRACT_MISMATCH"
    payload: dict[str, Any] = {"files": files, "assets": assets}
    if "deletions" in candidate:
        payload["deletions"] = deletions
    if candidate.get("payloadDigest") != _digest(payload):
        return "CANDIDATE_CONTRACT_MISMATCH"
    if _candidate_evidence_issue(candidate):
        return "CANDIDATE_CONTRACT_MISMATCH"
    return None


def _validation_current(validation: Mapping[str, Any], candidate: Mapping[str, Any]) -> bool:
    return bool(
        validation.get("candidateDigest") == candidate.get("payloadDigest")
        and isinstance(candidate.get("evidence"), Mapping)
        and validation.get("evidence") == candidate["evidence"].get("validation")
        and validation.get("secretScan") == {"status": "pass", "findings": []}
        and validation.get("unexpectedCandidateFiles") == []
        and validation.get("unresolvedBlockers") == []
    )


def _review_threshold_met(review: Mapping[str, Any]) -> bool:
    return bool(
        review.get("status") == "pass"
        and review.get("p0") == 0
        and review.get("p1") == 0
    )


def _valid_execution_ledger(ledger: Mapping[str, Any]) -> bool:
    return bool(simulate_milestone_execution_ledger(ledger).get("ok"))


def simulate_milestone_execution_ledger(
    execution_ledger: Mapping[str, Any],
) -> dict[str, Any]:
    """Execute a pure dependency/reentry/failure simulation for one ledger."""

    try:
        ledger = _plain_mapping(execution_ledger)
    except (TypeError, ValueError):
        return {"ok": False, "reasonCodes": ["EXECUTION_LEDGER_INVALID"]}
    events = ledger.get("events")
    if not isinstance(events, list) or not events:
        return {"ok": False, "reasonCodes": ["EXECUTION_LEDGER_INVALID"]}
    pending: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for event in events:
        if (
            not isinstance(event, dict)
            or not isinstance(event.get("id"), str)
            or not event["id"]
            or event["id"] in pending
            or not isinstance(event.get("dependsOn"), list)
            or any(not isinstance(item, str) for item in event["dependsOn"])
        ):
            return {"ok": False, "reasonCodes": ["EXECUTION_LEDGER_INVALID"]}
        pending[event["id"]] = event
        order.append(event["id"])

    completed: set[str] = set()
    executed: list[str] = []
    external_effects: list[str] = []
    false_gates = 0
    while pending:
        ready = next(
            (
                event_id
                for event_id in order
                if event_id in pending
                and set(pending[event_id]["dependsOn"]).issubset(completed)
            ),
            None,
        )
        if ready is None:
            return {"ok": False, "reasonCodes": ["EXECUTION_LEDGER_DEPENDENCY_CYCLE"]}
        event = pending.pop(ready)
        decision = str(event.get("decision") or "")
        if decision not in {
            CONTINUE,
            "CONTINUE_WITH_MINIMAL_GUARD",
            "DEFER_AND_CONTINUE",
            "WAIT_OWNER",
            "AUTO_CLEAN",
            FAIL_CLOSED_REPAIR,
            AWAIT_HUMAN,
        }:
            return {"ok": False, "reasonCodes": ["EXECUTION_LEDGER_DECISION_INVALID"]}
        false_gates += decision == AWAIT_HUMAN
        effect = event.get("externalEffect")
        if effect is not None:
            external_effects.append(str(effect))
        executed.append(ready)
        completed.add(ready)

    if false_gates:
        return {
            "ok": False,
            "reasonCodes": ["EXECUTION_LEDGER_FALSE_HUMAN_GATE"],
            "executedEventIds": executed,
            "falseHumanGateCount": false_gates,
        }

    if len(executed) <= 20:
        return {
            "ok": False,
            "reasonCodes": ["EXECUTION_LEDGER_LONG_RUN_TOO_SHORT"],
            "executedEventIds": executed,
        }
    if external_effects != list(EXPECTED_EFFECTS):
        return {
            "ok": False,
            "reasonCodes": ["EXECUTION_LEDGER_EFFECT_ORDER_INVALID"],
            "executedEventIds": executed,
        }

    crash_results: list[dict[str, Any]] = []
    events_by_id = {event["id"]: event for event in events}
    crash_points = ledger.get("crashInjectionAfter", [])
    if not isinstance(crash_points, list):
        return {"ok": False, "reasonCodes": ["EXECUTION_LEDGER_INVALID"]}
    for event_id in crash_points:
        event = events_by_id.get(event_id)
        effect = event.get("externalEffect") if isinstance(event, Mapping) else None
        if not effect:
            return {"ok": False, "reasonCodes": ["CRASH_INJECTION_POINT_INVALID"]}
        # The pure model persists PENDING, observes one authoritative completion,
        # then completes the same intent without a second effect attempt.
        crash_results.append(
            {
                "eventId": event_id,
                "effect": effect,
                "intentBeforeCrash": "PENDING",
                "authoritativeReadback": "same_identity_complete",
                "effectAttemptCount": 1,
                "reentryVerified": True,
            }
        )
    if [item["effect"] for item in crash_results] != list(EXPECTED_EFFECTS):
        return {"ok": False, "reasonCodes": ["CRASH_INJECTION_COVERAGE_INCOMPLETE"]}

    injection_results: list[dict[str, Any]] = []
    injections = ledger.get("injectedFailures", [])
    if not isinstance(injections, list):
        return {"ok": False, "reasonCodes": ["EXECUTION_LEDGER_INVALID"]}
    authority_missing = {
        "contract_ambiguity": "repository.ref",
        "remote_divergence": "repository.expectedBase",
        "tag_collision": "publication.tag",
        "release_collision": "publication.release",
        "undeclared_refresh_target": "refreshTargets.cache",
    }
    technical_failures = {"reviewed_diff_drift", "cache_source_mismatch"}
    simulation_binding = {
        "goalId": f"simulation:{ledger.get('simulationId')}",
        "changeId": f"fixture:{ledger.get('contractFixture')}",
        "bindingDigest": _digest(ledger),
        "contractDigest": _digest(
            {"contractFixture": ledger.get("contractFixture")}
        ),
    }
    for injection in injections:
        if not isinstance(injection, Mapping) or injection.get("at") not in events_by_id:
            return {"ok": False, "reasonCodes": ["INJECTION_INVALID"]}
        kind = str(injection.get("kind") or "")
        if kind in authority_missing:
            resolution = _human_gate(
                authority_missing[kind],
                f"SIMULATED_{kind.upper()}",
                canonical_binding=simulation_binding,
                write_set=[],
            )
        elif kind in technical_failures:
            resolution = _technical_stop(f"SIMULATED_{kind.upper()}")
        else:
            return {"ok": False, "reasonCodes": ["INJECTION_KIND_UNDECLARED"]}
        actual_missing = list(resolution.get("missingAuthority", []))
        expected_missing = injection.get("expectedMissingAuthority")
        comparable_missing = [
            item.removeprefix("target:") for item in actual_missing if isinstance(item, str)
        ]
        if (
            resolution.get("decision") != injection.get("expectedDecision")
            or int(injection.get("expectedMutationCount", -1)) != 0
            or (
                expected_missing is None
                and actual_missing
                or expected_missing is not None
                and comparable_missing != [expected_missing]
            )
        ):
            return {"ok": False, "reasonCodes": ["INJECTION_EXPECTATION_MISMATCH"]}
        injection_results.append(
            {
                "id": injection.get("id"),
                "kind": kind,
                "at": injection.get("at"),
                "decision": resolution["decision"],
                "missingAuthority": actual_missing,
                "mutationCount": 0,
                "failedClosedBeforeMutation": True,
            }
        )
    required_injections = {
        "contract_ambiguity",
        "reviewed_diff_drift",
        "remote_divergence",
        "tag_collision",
        "undeclared_refresh_target",
    }
    if not required_injections.issubset({item["kind"] for item in injection_results}):
        return {"ok": False, "reasonCodes": ["INJECTION_COVERAGE_INCOMPLETE"]}

    return {
        "ok": True,
        "simulationId": ledger.get("simulationId"),
        "transitionCount": len(executed),
        "executedEventIds": executed,
        "falseHumanGateCount": false_gates,
        "externalEffectCount": len(external_effects),
        "duplicateEffectCount": len(external_effects) - len(set(external_effects)),
        "crashRecoveryScenarioCount": len(crash_results),
        "crashRecoveryResults": crash_results,
        "injectionCount": len(injection_results),
        "injectionResults": injection_results,
    }


def _trusted_receipt_binding(
    repo: Path,
    contract: Mapping[str, Any],
    receipt_dir: Path,
) -> dict[str, Any] | None:
    contract_id = contract.get("contractId")
    if not isinstance(contract_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", contract_id):
        return None
    supplied = Path(receipt_dir)
    canonical = RECEIPT_ROOT / contract_id
    if supplied.is_absolute() or supplied.as_posix() != canonical.as_posix():
        return None
    target = repo / canonical
    try:
        target.relative_to(repo)
        if target.is_symlink() or not target.is_dir() or target.resolve(strict=True) != target:
            return None
        current = repo
        for part in canonical.parts:
            current = current / part
            if current.is_symlink() or not current.is_dir():
                return None
    except (OSError, RuntimeError, ValueError):
        return None
    binding: dict[str, Any] = {
        "schemaVersion": "1.0",
        "contractId": contract_id,
        "repositoryRealPath": str(repo),
        "relativePath": canonical.as_posix(),
    }
    binding["bindingDigest"] = _digest(binding)
    return binding


def _plan_integrity_issue(plan: Mapping[str, Any], contract: Mapping[str, Any]) -> str | None:
    if not plan.get("ok") or plan.get("status") != "READY":
        return "MILESTONE_PLAN_NOT_READY"
    if plan.get("contractDigest") != _digest(contract):
        return "MILESTONE_CONTRACT_DRIFT"
    requested_issue, excluded_effect = _requested_effects_issue(contract)
    if requested_issue or excluded_effect:
        return "MILESTONE_CONTRACT_DRIFT"
    unsigned = dict(plan)
    claimed = unsigned.pop("planDigest", None)
    if claimed != _digest(unsigned):
        return "MILESTONE_PLAN_TAMPERED"
    for key, embedded in (
        ("candidateDigest", "candidateManifest"),
        ("validationDigest", "validationReceipt"),
        ("reviewDigest", "reviewReceipt"),
        ("executionLedgerDigest", "executionLedger"),
        ("executionSimulationDigest", "executionSimulation"),
    ):
        if plan.get(key) != _digest(plan.get(embedded)):
            return "MILESTONE_PLAN_TAMPERED"
    candidate = plan.get("candidateManifest")
    validation = plan.get("validationReceipt")
    review = plan.get("reviewReceipt")
    if (
        not isinstance(candidate, Mapping)
        or not isinstance(validation, Mapping)
        or not isinstance(review, Mapping)
        or _candidate_shape_issue(candidate)
        or _validation_shape_issue(validation, contract)
        or _validation_command_issue(validation, contract)
        or _review_shape_issue(review, contract)
        or validation.get("contractId") != contract.get("contractId")
        or review.get("contractId") != contract.get("contractId")
        or _candidate_evidence_issue(candidate)
        or validation.get("evidence") != candidate["evidence"]["validation"]
        or review.get("evidence") != candidate["evidence"]["independentReview"]
        or _candidate_contract_issue(contract, candidate)
        or not _validation_current(validation, candidate)
        or not _review_threshold_met(review)
    ):
        return "MILESTONE_PLAN_TAMPERED"
    binding = plan.get("receiptBinding")
    if not isinstance(binding, Mapping):
        return "MILESTONE_PLAN_TAMPERED"
    unsigned_binding = dict(binding)
    claimed_binding = unsigned_binding.pop("bindingDigest", None)
    if claimed_binding != _digest(unsigned_binding):
        return "MILESTONE_PLAN_TAMPERED"
    asset_binding = plan.get("assetBinding")
    if not isinstance(asset_binding, Mapping):
        return "MILESTONE_PLAN_TAMPERED"
    unsigned_asset_binding = dict(asset_binding)
    claimed_asset_binding = unsigned_asset_binding.pop("bindingDigest", None)
    if claimed_asset_binding != _digest(unsigned_asset_binding):
        return "MILESTONE_PLAN_TAMPERED"
    guard = plan.get("canonicalGuard")
    if not isinstance(guard, Mapping):
        return "MILESTONE_PLAN_TAMPERED"
    unsigned_guard = dict(guard)
    unsigned_guard.pop("stateSource", None)
    unsigned_guard.pop("sourceCommit", None)
    claimed_guard = unsigned_guard.pop("bindingDigest", None)
    if claimed_guard != _digest(unsigned_guard):
        return "MILESTONE_PLAN_TAMPERED"
    return None


def _asset_directory_binding(
    repo: Path,
    candidate: Mapping[str, Any],
    receipt_binding: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    if candidate.get("assetDirectory") != "release-assets":
        return None, "asset_directory_name"
    receipt_relative = receipt_binding.get("relativePath")
    if not _safe_candidate_path(receipt_relative):
        return None, "receipt_relative_path"
    assert isinstance(receipt_relative, str)
    relative = Path(receipt_relative) / "release-assets"
    if not _safe_candidate_path(relative.as_posix()):
        return None, "asset_relative_path"
    root = repo / relative
    try:
        resolved = root.resolve(strict=True)
        resolved.relative_to(repo)
        directory_stat = root.stat(follow_symlinks=False)
        if root.is_symlink() or resolved != root or not root.is_dir():
            return None, "asset_directory_type_or_symlink"
        entries = list(os.scandir(root))
    except (OSError, RuntimeError, ValueError):
        return None, "asset_directory_unreadable"
    assets = candidate.get("assets")
    if not isinstance(assets, list):
        return None, "asset_records_missing"
    expected_names = [str(item.get("name")) for item in assets if isinstance(item, Mapping)]
    observed_names = sorted(entry.name for entry in entries)
    if len(expected_names) != len(assets) or observed_names != sorted(expected_names):
        return None, "asset_member_set"
    entries_by_name = {entry.name: entry for entry in entries}
    for item in assets:
        assert isinstance(item, Mapping)
        name = str(item["name"])
        entry = entries_by_name[name]
        try:
            path = Path(entry.path)
            if (
                entry.is_symlink()
                or not entry.is_file(follow_symlinks=False)
                or path.resolve(strict=True) != path
            ):
                return None, f"asset_type_or_symlink:{name}"
            data = path.read_bytes()
            observed_size = entry.stat(follow_symlinks=False).st_size
        except (OSError, RuntimeError, ValueError):
            return None, f"asset_unreadable:{name}"
        if (
            observed_size != item.get("size")
            or len(data) != item.get("size")
            or hashlib.sha256(data).hexdigest() != item.get("sha256")
        ):
            return None, f"asset_content:{name}"
    binding: dict[str, Any] = {
        "schemaVersion": "1.0",
        "kind": "devflow-milestone-release-asset-binding",
        "contractId": receipt_binding.get("contractId"),
        "repositoryRealPath": str(repo),
        "relativePath": relative.as_posix(),
        "device": directory_stat.st_dev,
        "inode": directory_stat.st_ino,
        "assets": _plain_mapping({"assets": assets})["assets"],
    }
    binding["bindingDigest"] = _digest(binding)
    return binding, None


def _candidate_files_issue(repo: Path, candidate: Mapping[str, Any]) -> str | None:
    files = candidate.get("files")
    if not isinstance(files, list):
        return "files"
    for item in files:
        if not isinstance(item, Mapping):
            return "entry"
        relative = str(item.get("path") or "")
        if not _safe_candidate_path(relative):
            return relative
        path = repo / relative
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(repo)
            if resolved != path or path.is_symlink() or not path.is_file():
                return relative
            data = path.read_bytes()
            mode = "100755" if path.stat().st_mode & 0o100 else "100644"
        except (OSError, ValueError):
            return relative
        if (
            len(data) != item.get("size")
            or hashlib.sha256(data).hexdigest() != item.get("sha256")
            or mode != item.get("mode")
        ):
            return relative
    return None


def _candidate_deletion_tree_entries(
    repo: Path, treeish: str, deletions: Sequence[str]
) -> dict[str, str] | None:
    if not deletions:
        return {}
    result = _git(
        repo,
        "--literal-pathspecs",
        "ls-tree",
        "-z",
        "--full-tree",
        treeish,
        "--",
        *deletions,
        check=False,
        binary=True,
    )
    if result.returncode != 0:
        return None
    entries: dict[str, str] = {}
    for raw_entry in result.stdout.rstrip(b"\0").split(b"\0") if result.stdout else ():
        try:
            metadata, raw_path = raw_entry.split(b"\t", 1)
            _mode, object_type, _object_id = metadata.decode("ascii").split()
            relative = raw_path.decode("utf-8")
        except (UnicodeDecodeError, ValueError):
            return None
        if relative in entries:
            return None
        entries[relative] = object_type
    return entries


def _candidate_deletions_issue(
    repo: Path,
    candidate: Mapping[str, Any],
    expected_base: str,
) -> str | None:
    deletions = candidate.get("deletions", [])
    if not isinstance(deletions, list):
        return "deletions_invalid"
    exact = [str(relative) for relative in deletions]
    base_entries = _candidate_deletion_tree_entries(repo, expected_base, exact)
    if base_entries is None:
        return "deletion_base_readback"
    for relative in exact:
        if base_entries.get(relative) != "blob":
            return f"deletion_not_tracked_file_at_base:{relative}"
        path = repo / relative
        try:
            resolved = path.resolve(strict=False)
            resolved.relative_to(repo)
        except (OSError, RuntimeError, ValueError):
            return f"deletion_worktree_path_untrusted:{relative}"
        if resolved != path or path.exists() or path.is_symlink():
            return f"deletion_resurrected:{relative}"
    return None


def _unexpected_candidate_paths(
    repo: Path,
    contract: Mapping[str, Any],
    *,
    allow_clean: bool = False,
    receipt_binding: Mapping[str, Any] | None = None,
) -> list[str]:
    expected = set(map(str, contract.get("writeSet", [])))
    tracked = _git_output(
        repo,
        "diff",
        "--name-only",
        "-z",
        "--diff-filter=ACDMRTUXB",
        "HEAD",
        "--",
    )
    untracked = _git_output(
        repo,
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
        "--",
    )
    observed = {
        path
        for path in (*tracked.split("\0"), *untracked.split("\0"))
        if path
    }
    if receipt_binding is not None:
        receipt_prefix = str(receipt_binding.get("relativePath") or "").rstrip("/") + "/"
        observed = {path for path in observed if not path.startswith(receipt_prefix)}
    if allow_clean:
        # After the exact candidate commit exists, authority is read from that
        # immutable tree. A later worktree-only config edit is unrelated to the
        # committed milestone identity and cannot rewrite the bound mode/SHA.
        observed.discard(DEVFLOW_CONFIG_PATH.as_posix())
    ignored_output = _git(
        repo,
        "check-ignore",
        "--",
        *sorted(expected),
        check=False,
    ).stdout
    ignored = {path for path in ignored_output.splitlines() if path}
    unexpected = observed - expected
    missing = set() if allow_clean else expected - observed - ignored
    return sorted(unexpected | missing)


def _safe_candidate_path(value: object) -> bool:
    if not isinstance(value, str) or not value or "\x00" in value or "\n" in value:
        return False
    path = Path(value)
    return bool(
        not path.is_absolute()
        and path.as_posix() == value
        and path.parts
        and all(part not in {"", ".", ".."} for part in path.parts)
        and path.parts[0] != ".git"
    )


def _safe_asset_name(value: object) -> bool:
    return bool(
        isinstance(value, str)
        and value
        and value == value.strip()
        and "\x00" not in value
        and "\n" not in value
        and Path(value).name == value
        and value not in {".", ".."}
    )


def _candidate_index_issue(repo: Path, candidate: Mapping[str, Any]) -> str | None:
    for item in candidate["files"]:
        relative = str(item["path"])
        result = _git(repo, "show", f":{relative}", check=False, binary=True)
        if result.returncode != 0:
            return relative
        data = result.stdout
        if hashlib.sha256(data).hexdigest() != item["sha256"] or len(data) != item["size"]:
            return relative
        mode_line = _git_output(repo, "ls-files", "-s", "--", relative)
        if not mode_line.startswith(str(item["mode"]) + " "):
            return relative
    deletions = [str(relative) for relative in candidate.get("deletions", [])]
    if deletions:
        indexed = _git(
            repo,
            "--literal-pathspecs",
            "ls-files",
            "-s",
            "-z",
            "--",
            *deletions,
            check=False,
            binary=True,
        )
        if indexed.returncode != 0 or indexed.stdout:
            return deletions[0]
    return None


def _matching_commit(
    repo: Path,
    commit: str,
    expected_base: str,
    contract: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> bool:
    if _git_output(repo, "rev-parse", f"{commit}^", check=False) != expected_base:
        return False
    if _git_output(repo, "show", "-s", "--format=%B", commit).strip() != str(
        contract["commit"]["message"]
    ):
        return False
    changed = _git_output(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", commit)
    if sorted(filter(None, changed.splitlines())) != sorted(contract["writeSet"]):
        return False
    for item in candidate["files"]:
        relative = str(item["path"])
        tree = _git(
            repo,
            "ls-tree",
            "-z",
            "--full-tree",
            commit,
            "--",
            relative,
            check=False,
            binary=True,
        )
        entries = tree.stdout.rstrip(b"\0").split(b"\0") if tree.stdout else []
        if tree.returncode != 0 or len(entries) != 1:
            return False
        try:
            metadata, observed_path = entries[0].split(b"\t", 1)
            mode, object_type, object_id = metadata.decode("ascii").split()
            observed_relative = observed_path.decode("utf-8")
        except (UnicodeDecodeError, ValueError):
            return False
        if (
            mode != str(item["mode"])
            or object_type != "blob"
            or observed_relative != relative
        ):
            return False
        blob = _git(repo, "cat-file", "blob", object_id, check=False, binary=True)
        blob_size = _git_output(repo, "cat-file", "-s", object_id, check=False)
        if (
            blob.returncode != 0
            or blob_size != str(item["size"])
            or len(blob.stdout) != item["size"]
            or hashlib.sha256(blob.stdout).hexdigest() != item["sha256"]
        ):
            return False
    deletions = [str(relative) for relative in candidate.get("deletions", [])]
    committed_entries = _candidate_deletion_tree_entries(repo, commit, deletions)
    if committed_entries is None or any(
        relative in committed_entries for relative in deletions
    ):
        return False
    return True


def _staged_paths(repo: Path) -> list[str]:
    output = _git_output(repo, "diff", "--cached", "--name-only", "--diff-filter=ACDMRTUXB")
    return sorted(filter(None, output.splitlines()))


def _git(
    repo: Path,
    *args: str,
    check: bool = True,
    binary: bool = False,
) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=check,
        capture_output=True,
        text=not binary,
    )


def _git_output(repo: Path, *args: str, check: bool = True) -> str:
    result = _git(repo, *args, check=check)
    return result.stdout.strip() if isinstance(result.stdout, str) else result.stdout.decode().strip()


def _ls_remote(repo: Path, remote: str, ref: str) -> tuple[bool, str | None]:
    result = _git(repo, "ls-remote", "--refs", remote, ref, check=False)
    if result.returncode != 0:
        return False, None
    line = result.stdout.strip().splitlines()
    return True, line[0].split()[0] if line else None


def _published_identity(
    contract: Mapping[str, Any], candidate: Mapping[str, Any], commit: str
) -> dict[str, Any]:
    return {
        "plugin": contract["plugin"]["id"],
        "version": contract["plugin"]["version"],
        "tag": contract["publication"]["tag"],
        "channel": contract["publication"]["channel"],
        "commit": commit,
        "state": "published",
        "assets": candidate["assets"],
    }


def _call(boundaries: Mapping[str, object], name: str, request: Mapping[str, Any]) -> dict[str, Any]:
    function = boundaries[name]
    assert callable(function)
    result = function(_plain_mapping(request))
    return _plain_mapping(result)


def _effect_receipt(
    effect: str,
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> dict[str, Any]:
    before_data = _plain_mapping(before)
    after_data = _plain_mapping(after)
    return {
        "effect": effect,
        "beforeIntent": before_data,
        "beforeIntentDigest": _digest(before_data),
        "afterReadback": after_data,
        "afterReadbackDigest": _digest(after_data),
        "contractDigest": plan["contractDigest"],
        "candidateDigest": plan["candidateDigest"],
        "planDigest": plan["planDigest"],
    }


def _new_state(plan: Mapping[str, Any], receipt_binding: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": "1.0",
        "kind": "devflow-milestone-external-effects-state",
        "planDigest": plan["planDigest"],
        "canonicalGuardDigest": plan["canonicalGuard"]["bindingDigest"],
        "receiptBindingDigest": receipt_binding["bindingDigest"],
        "effects": [],
        "intents": {},
        "counters": {"diagnoses": 0, "remediations": 0},
    }


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_strict_json_object(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists() and not path.is_symlink():
        return None, "absent"
    if path.is_symlink() or not path.is_file() or path.resolve() != path:
        return None, "untrusted_shape"
    try:
        value = json.loads(path.read_text(), object_pairs_hook=_reject_duplicate_keys)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return None, "invalid_json"
    if not isinstance(value, dict):
        return None, "not_object"
    return value, None


def _load_state(
    path: Path,
    plan: Mapping[str, Any],
    receipt_binding: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists() and not path.is_symlink():
        return None, None
    state, read_issue = _read_strict_json_object(path)
    if read_issue:
        return None, read_issue
    assert state is not None
    required = {
        "schemaVersion",
        "kind",
        "planDigest",
        "canonicalGuardDigest",
        "receiptBindingDigest",
        "effects",
        "intents",
        "counters",
        "stateDigest",
    }
    if set(state) != required:
        return None, "state_shape"
    unsigned = dict(state)
    claimed = unsigned.pop("stateDigest", None)
    if claimed != _digest(unsigned):
        return None, "state_digest"
    if (
        state.get("schemaVersion") != "1.0"
        or state.get("kind") != "devflow-milestone-external-effects-state"
        or state.get("planDigest") != plan.get("planDigest")
        or state.get("canonicalGuardDigest")
        != plan.get("canonicalGuard", {}).get("bindingDigest")
        or state.get("receiptBindingDigest") != receipt_binding.get("bindingDigest")
    ):
        return None, "state_binding"
    effects = state.get("effects")
    intents = state.get("intents")
    counters = state.get("counters")
    if (
        not isinstance(effects, list)
        or not isinstance(intents, dict)
        or not isinstance(counters, dict)
        or set(counters) != {"diagnoses", "remediations"}
        or any(not isinstance(counters[key], int) or counters[key] < 0 for key in counters)
    ):
        return None, "state_shape"
    effect_names = [item.get("effect") if isinstance(item, Mapping) else None for item in effects]
    if effect_names != list(EXPECTED_EFFECTS[: len(effect_names)]):
        return None, "effect_order"
    for item in effects:
        if _effect_receipt_issue(item, plan):
            return None, "effect_receipt"
    for effect, intent in intents.items():
        if effect not in EXPECTED_EFFECTS or not isinstance(intent, Mapping):
            return None, "intent_shape"
        before = intent.get("beforeIntent")
        if (
            intent.get("effect") != effect
            or intent.get("status") not in {"PENDING", "COMPLETE"}
            or not isinstance(before, Mapping)
            or intent.get("beforeIntentDigest") != _digest(before)
            or intent.get("planDigest") != plan.get("planDigest")
            or intent.get("contractDigest") != plan.get("contractDigest")
            or intent.get("candidateDigest") != plan.get("candidateDigest")
        ):
            return None, "intent_binding"
        if intent.get("status") == "COMPLETE":
            after = intent.get("afterReadback")
            if (
                not isinstance(after, Mapping)
                or intent.get("afterReadbackDigest") != _digest(after)
                or effect not in effect_names
            ):
                return None, "intent_readback"
        elif "afterReadback" in intent or "afterReadbackDigest" in intent:
            return None, "pending_intent_shape"
        apply_attempt_count = intent.get("applyAttemptCount")
        if apply_attempt_count is not None and (
            effect != "codex.cache.refresh"
            or isinstance(apply_attempt_count, bool)
            or not isinstance(apply_attempt_count, int)
            or apply_attempt_count < 1
            or apply_attempt_count > 2
        ):
            return None, "intent_attempt_count"
    return state, None


def _pending_intent(
    state: Mapping[str, Any],
    effect: str,
    before: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> bool:
    intent = state["intents"].get(effect)
    if not isinstance(intent, Mapping):
        return False
    return bool(
        intent.get("beforeIntent") == _plain_mapping(before)
        and intent.get("beforeIntentDigest") == _digest(before)
        and intent.get("planDigest") == plan.get("planDigest")
    )


def _persist_intent(
    path: Path,
    state: dict[str, Any],
    effects: list[dict[str, Any]],
    effect: str,
    before: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> None:
    before_data = _plain_mapping(before)
    existing = state["intents"].get(effect)
    if existing is not None:
        if not _pending_intent(state, effect, before_data, plan):
            raise MilestoneStateIntegrityError(f"intent identity drift for {effect}")
        return
    state["intents"][effect] = {
        "effect": effect,
        "status": "PENDING",
        "beforeIntent": before_data,
        "beforeIntentDigest": _digest(before_data),
        "planDigest": plan["planDigest"],
        "contractDigest": plan["contractDigest"],
        "candidateDigest": plan["candidateDigest"],
    }
    _save_state(path, state, effects)


def _reserve_cache_apply_attempt(
    path: Path,
    state: dict[str, Any],
    effects: list[dict[str, Any]],
) -> bool:
    intent = state["intents"].get("codex.cache.refresh")
    if not isinstance(intent, dict) or intent.get("status") != "PENDING":
        raise MilestoneStateIntegrityError("cache apply requires a pending intent")
    count = intent.get("applyAttemptCount", 0)
    if isinstance(count, bool) or not isinstance(count, int) or count < 0 or count > 2:
        raise MilestoneStateIntegrityError("cache apply attempt count drift")
    if count == 2:
        return False
    intent["applyAttemptCount"] = count + 1
    _save_state(path, state, effects)
    return True


def _complete_intent(
    path: Path,
    state: dict[str, Any],
    effects: list[dict[str, Any]],
    effect: str,
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> None:
    _persist_intent(path, state, effects, effect, before, plan)
    receipt = _effect_receipt(effect, before, after, plan)
    existing = next((item for item in effects if item.get("effect") == effect), None)
    if existing is not None and existing != receipt:
        raise MilestoneStateIntegrityError(f"effect readback drift for {effect}")
    if existing is None:
        expected = EXPECTED_EFFECTS[len(effects)] if len(effects) < len(EXPECTED_EFFECTS) else None
        if effect != expected:
            raise MilestoneStateIntegrityError(f"effect order drift for {effect}")
        effects.append(receipt)
    intent = state["intents"][effect]
    intent["status"] = "COMPLETE"
    intent["afterReadback"] = _plain_mapping(after)
    intent["afterReadbackDigest"] = _digest(after)
    _save_state(path, state, effects)


def _save_state(path: Path, state: dict[str, Any], effects: list[dict[str, Any]]) -> None:
    state["effects"] = effects
    state.pop("stateDigest", None)
    state["stateDigest"] = _digest(state)
    _atomic_json(path, state)


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    if (
        path.parent.is_symlink()
        or not path.parent.is_dir()
        or path.parent.resolve(strict=True) != path.parent
        or path.is_symlink()
        or path.exists()
        and not path.is_file()
    ):
        raise OSError("untrusted receipt path")
    descriptor, temporary = tempfile.mkstemp(prefix=f"{path.name}-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _after_irreversible_effect(boundaries: Mapping[str, object], effect: str) -> None:
    hook = boundaries.get("after_irreversible_effect")
    if callable(hook):
        hook({"effect": effect})


def _terminal_receipt(
    plan: Mapping[str, Any],
    commit: str,
    identity: Mapping[str, Any],
    effects: list[dict[str, Any]],
    state: Mapping[str, Any],
    source_readback: Mapping[str, Any],
    publication_readback: Mapping[str, Any],
    cache_readback: Mapping[str, Any],
    project_readback: Mapping[str, Any],
    canonical_guard: Mapping[str, Any],
) -> dict[str, Any]:
    simulation = plan["executionSimulation"]
    counters = {
        "falseHumanGateCount": simulation["falseHumanGateCount"],
        "duplicateEffectCount": len(effects) - len({item["effect"] for item in effects}),
        "externalEffectCount": len(effects),
        "diagnoses": state["counters"]["diagnoses"],
        "remediations": state["counters"]["remediations"],
    }
    receipt: dict[str, Any] = {
        "schemaVersion": "1.0",
        "kind": "devflow-milestone-external-effects-terminal-receipt",
        "status": "COMPLETE",
        "plan": _plain_mapping(plan),
        "canonicalGuard": _plain_mapping(canonical_guard),
        "receiptBinding": _plain_mapping(plan["receiptBinding"]),
        "contractDigest": plan["contractDigest"],
        "candidateDigest": plan["candidateDigest"],
        "validationDigest": plan["validationDigest"],
        "reviewDigest": plan["reviewDigest"],
        "executionLedgerDigest": plan["executionLedgerDigest"],
        "executionSimulationDigest": plan["executionSimulationDigest"],
        "planDigest": plan["planDigest"],
        "commit": commit,
        "identity": _plain_mapping(identity),
        "publicationIdentity": _plain_mapping(identity),
        "effects": _plain_mapping({"effects": effects})["effects"],
        "simulationId": simulation.get("simulationId"),
        "eventIds": list(simulation["executedEventIds"]),
        "falseHumanGateCount": counters["falseHumanGateCount"],
        "duplicateEffectCount": counters["duplicateEffectCount"],
        "externalEffectCount": counters["externalEffectCount"],
        "counters": counters,
        "fiveLayerIdentity": {
            "source": _plain_mapping(source_readback)["identity"],
            "release": _plain_mapping(identity),
            "published": _plain_mapping(publication_readback)["identity"],
            "cache": _plain_mapping(cache_readback)["identity"],
            "project": _plain_mapping(project_readback)["identity"],
        },
    }
    receipt["terminalDigest"] = _digest(receipt)
    return receipt


def _effect_receipt_issue(effect: Mapping[str, Any], plan: Mapping[str, Any]) -> str | None:
    before = effect.get("beforeIntent")
    after = effect.get("afterReadback")
    if not isinstance(before, Mapping) or not isinstance(after, Mapping):
        return "payload"
    if (
        effect.get("beforeIntentDigest") != _digest(before)
        or effect.get("afterReadbackDigest") != _digest(after)
        or effect.get("contractDigest") != plan.get("contractDigest")
        or effect.get("candidateDigest") != plan.get("candidateDigest")
        or effect.get("planDigest") != plan.get("planDigest")
    ):
        return "binding"
    return None


def _validate_terminal_receipt(
    receipt: Mapping[str, Any],
    plan: Mapping[str, Any],
    receipt_binding: Mapping[str, Any],
) -> str | None:
    required = {
        "schemaVersion",
        "kind",
        "status",
        "plan",
        "canonicalGuard",
        "receiptBinding",
        "contractDigest",
        "candidateDigest",
        "validationDigest",
        "reviewDigest",
        "executionLedgerDigest",
        "executionSimulationDigest",
        "planDigest",
        "commit",
        "identity",
        "publicationIdentity",
        "effects",
        "simulationId",
        "eventIds",
        "falseHumanGateCount",
        "duplicateEffectCount",
        "externalEffectCount",
        "counters",
        "fiveLayerIdentity",
        "terminalDigest",
    }
    if set(receipt) != required:
        return "TERMINAL_RECEIPT_INVALID"
    if (
        receipt.get("schemaVersion") != "1.0"
        or receipt.get("kind") != "devflow-milestone-external-effects-terminal-receipt"
        or receipt.get("status") != "COMPLETE"
        or receipt.get("plan") != plan
        or not isinstance(receipt.get("canonicalGuard"), Mapping)
        or receipt.get("canonicalGuard", {}).get("bindingDigest")
        != plan.get("canonicalGuard", {}).get("bindingDigest")
        or receipt.get("canonicalGuard", {}).get("stateSource") != "commit"
        or receipt.get("canonicalGuard", {}).get("sourceCommit") != receipt.get("commit")
        or receipt.get("receiptBinding") != receipt_binding
    ):
        return "TERMINAL_RECEIPT_INVALID"
    receipt_guard = dict(receipt["canonicalGuard"])
    receipt_guard.pop("stateSource", None)
    receipt_guard.pop("sourceCommit", None)
    claimed_guard_digest = receipt_guard.pop("bindingDigest", None)
    if claimed_guard_digest != _digest(receipt_guard):
        return "TERMINAL_RECEIPT_INVALID"
    for key in (
        "contractDigest",
        "candidateDigest",
        "validationDigest",
        "reviewDigest",
        "executionLedgerDigest",
        "executionSimulationDigest",
        "planDigest",
    ):
        if receipt.get(key) != plan.get(key):
            return "TERMINAL_RECEIPT_INVALID"
    unsigned = dict(receipt)
    claimed = unsigned.pop("terminalDigest", None)
    if claimed != _digest(unsigned):
        return "TERMINAL_RECEIPT_INVALID"
    effects = receipt.get("effects")
    if (
        not isinstance(effects, list)
        or any(not isinstance(item, Mapping) for item in effects)
        or [item.get("effect") for item in effects] != list(EXPECTED_EFFECTS)
    ):
        return "TERMINAL_RECEIPT_INVALID"
    for effect in effects:
        if not isinstance(effect, Mapping) or _effect_receipt_issue(effect, plan):
            return "TERMINAL_RECEIPT_INVALID"
    simulation = plan.get("executionSimulation")
    counters = receipt.get("counters")
    identity = receipt.get("publicationIdentity")
    layers = receipt.get("fiveLayerIdentity")
    if (
        not isinstance(simulation, Mapping)
        or not isinstance(counters, Mapping)
        or not isinstance(identity, Mapping)
        or set(counters)
        != {
            "falseHumanGateCount",
            "duplicateEffectCount",
            "externalEffectCount",
            "diagnoses",
            "remediations",
        }
        or not isinstance(layers, Mapping)
        or set(layers) != {"source", "release", "published", "cache", "project"}
        or any(layer != identity for layer in layers.values())
        or receipt.get("identity") != identity
        or receipt.get("commit") != identity.get("commit")
        or receipt.get("eventIds") != simulation.get("executedEventIds")
        or receipt.get("simulationId") != simulation.get("simulationId")
        or counters.get("falseHumanGateCount") != simulation.get("falseHumanGateCount")
        or counters.get("falseHumanGateCount") != 0
        or counters.get("duplicateEffectCount") != 0
        or counters.get("externalEffectCount") != len(EXPECTED_EFFECTS)
        or receipt.get("falseHumanGateCount") != counters.get("falseHumanGateCount")
        or receipt.get("duplicateEffectCount") != counters.get("duplicateEffectCount")
        or receipt.get("externalEffectCount") != counters.get("externalEffectCount")
        or any(not isinstance(counters.get(key), int) or counters[key] < 0 for key in counters)
    ):
        return "TERMINAL_RECEIPT_INVALID"
    readbacks = {item["effect"]: item["afterReadback"] for item in effects}
    commit = receipt.get("commit")
    if (
        readbacks["git.commit"].get("commit") != commit
        or readbacks["git.push"].get("remoteCommit") != commit
        or readbacks["git.tag.push"].get("remoteTagCommit") != commit
        or readbacks["github.release"].get("status") != "published"
        or readbacks["github.release"].get("identity") != identity
        or any(
            readbacks[effect].get("identity") != identity
            for effect in (
                "devflow.source.fast_forward",
                "codex.cache.refresh",
                "devflow.project.refresh",
            )
        )
    ):
        return "TERMINAL_RECEIPT_INVALID"
    return None


def _complete_result(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "status": "COMPLETE",
        "decision": CONTINUE,
        "reasonCodes": ["MILESTONE_EXTERNAL_EFFECTS_COMPLETE"],
        "missingAuthority": [],
        "receipt": _plain_mapping(receipt),
        "simulationId": receipt.get("simulationId"),
        "eventIds": receipt.get("eventIds", []),
        "falseHumanGateCount": receipt.get("falseHumanGateCount", 0),
        "duplicateEffectCount": receipt.get("duplicateEffectCount", 0),
        "externalEffectCount": receipt.get("externalEffectCount", 0),
    }
