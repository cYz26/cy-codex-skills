from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

try:
    from workflow_authority_delta import resolve_authority_delta
except ModuleNotFoundError as error:
    if error.name != "workflow_authority_delta":
        raise
    resolve_authority_delta = None
    RESOLVER_IMPORT_ERROR = error
else:
    RESOLVER_IMPORT_ERROR = None


DECISIONS = (
    "CONTINUE",
    "CONTINUE_WITH_MINIMAL_GUARD",
    "DEFER_AND_CONTINUE",
    "WAIT_OWNER",
    "AUTO_CLEAN",
    "FAIL_CLOSED_REPAIR",
    "AWAIT_HUMAN",
)

RESULT_KEYS = {
    "schemaVersion",
    "decision",
    "reasonCodes",
    "missingAuthority",
    "invalidations",
    "materialDelta",
    "requestDigest",
    "authorityDigest",
    "evidenceDigest",
    "standingContractDigest",
    "gateKey",
}


def approved_request(**overrides: object) -> dict[str, object]:
    request: dict[str, object] = {
        "action": "edit_authority_policy",
        "scope": "approved-slice",
        "writeSet": ["dev/plugins/dev-flow/scripts/workflow_authority_delta.py"],
        "risk": "local_reversible",
        "effect": "local.write",
        "target": "dev-flow-source",
        "ownership": "task-owned",
        "guardRequired": False,
        "deferralApproved": False,
    }
    request.update(overrides)
    return request


def approved_envelope(**overrides: object) -> dict[str, object]:
    envelope: dict[str, object] = {
        "goalId": "goal-authority-delta",
        "changeId": "centralize-devflow-authority-delta",
        "planDigest": "plan-authority-delta-v1",
        "writeSet": ["dev/plugins/dev-flow/scripts/workflow_authority_delta.py"],
        "allowedActions": [
            "edit_authority_policy",
            "refresh_derived_evidence",
            "run_independent_review",
        ],
        "allowedEffects": ["local.write", "read-only.review"],
        "allowedTargets": ["dev-flow-source", "change-evidence"],
        "allowedOwnerships": ["task-owned", "review-contract"],
        "allowedRisks": ["local_reversible", "read-only"],
    }
    envelope.update(overrides)
    return envelope


def current_evidence(**overrides: object) -> dict[str, object]:
    evidence: dict[str, object] = {
        "trusted": True,
        "current": True,
        "complete": True,
        "identityCurrent": True,
        "ownerActive": False,
        "deterministicRepairAvailable": True,
    }
    evidence.update(overrides)
    return evidence


def standing_milestone(**overrides: object) -> dict[str, object]:
    contract: dict[str, object] = {
        "schemaVersion": 1,
        "goalId": "goal-authority-delta",
        "changeId": "centralize-devflow-authority-delta",
        "planDigest": "plan-authority-delta-v1",
        "effects": ["git.commit", "git.push", "github.release", "plugin.refresh"],
        "targets": [
            "origin:refs/heads/main",
            "dev-flow-v0.4.0",
            "dev-flow@cy-codex-skills",
        ],
        "current": True,
    }
    contract.update(overrides)
    return contract


def standing_model_execution(**overrides: object) -> dict[str, object]:
    execution: dict[str, object] = {
        "taskId": "PLATFORM-E50:5.13",
        "provider": "openai-responses",
        "model": "gpt-5.6-sol/max/default",
        "credentialPolicy": "existing_auth_only",
        "costPolicy": "record_actual_no_currency_gate",
        "serial": True,
    }
    execution.update(overrides)
    return execution


def model_request(*, attempt_id: str = "g51-r3-attempt-1", **overrides: object) -> dict[str, object]:
    request_overrides: dict[str, object] = {
        "action": "run_model_evaluation",
        "writeSet": [".planning/devflow/verification/PLATFORM-E50"],
        "risk": "declared_external",
        "effect": "model.invoke",
        "target": "task:PLATFORM-E50:5.13",
        "execution": {
            **standing_model_execution(),
            "attemptId": attempt_id,
        },
    }
    request_overrides.update(overrides)
    return approved_request(**request_overrides)


def model_envelope(**overrides: object) -> dict[str, object]:
    envelope_overrides: dict[str, object] = {
        "writeSet": [".planning/devflow/verification/PLATFORM-E50"],
        "allowedActions": ["run_model_evaluation"],
        "allowedEffects": ["model.invoke"],
        "allowedTargets": ["task:PLATFORM-E50:5.13"],
        "allowedRisks": ["declared_external"],
        "standingExecution": standing_model_execution(),
    }
    envelope_overrides.update(overrides)
    return approved_envelope(**envelope_overrides)


def cleanup_request(*, owner_exited: bool = True, **overrides: object) -> dict[str, object]:
    candidate = ".planning/devflow/tmp/authority-delta-run/output.json"
    cleanup = {
        "registered": True,
        "taskOwned": True,
        "ownerExited": owner_exited,
        "exactPaths": True,
        "recursive": False,
        "identityCurrent": True,
        "source": False,
        "userContent": False,
        "historicalReceipt": False,
        "persistentEvidence": False,
    }
    cleanup.update(copy.deepcopy(overrides.pop("cleanup", {})))
    request_overrides: dict[str, object] = {
        "action": "cleanup_task_output",
        "writeSet": [candidate],
        "effect": "local.cleanup",
        "target": candidate,
        "cleanup": cleanup,
    }
    request_overrides.update(overrides)
    return approved_request(**request_overrides)


def cleanup_envelope() -> dict[str, object]:
    candidate = ".planning/devflow/tmp/authority-delta-run/output.json"
    return approved_envelope(
        writeSet=[candidate],
        allowedActions=["cleanup_task_output"],
        allowedEffects=["local.cleanup"],
        allowedTargets=[candidate],
    )


class AuthorityDeltaPolicyTests(unittest.TestCase):
    maxDiff = None

    def resolve(
        self,
        *,
        request: dict[str, object] | None = None,
        authority_envelope: dict[str, object] | None = None,
        evidence: dict[str, object] | None = None,
        standing_contract: dict[str, object] | None = None,
    ) -> dict[str, object]:
        self.assertIsNotNone(
            resolve_authority_delta,
            f"public resolver is unavailable: {RESOLVER_IMPORT_ERROR}",
        )
        result = resolve_authority_delta(  # type: ignore[misc]
            request=approved_request() if request is None else request,
            authority_envelope=(
                approved_envelope() if authority_envelope is None else authority_envelope
            ),
            evidence=current_evidence() if evidence is None else evidence,
            standing_contract=standing_contract,
        )
        self.assertIsInstance(result, dict)
        self.assertEqual(set(result), RESULT_KEYS)
        self.assertEqual(result["schemaVersion"], 1)
        self.assertIn(result["decision"], DECISIONS)
        self.assertEqual(sum(result["decision"] == item for item in DECISIONS), 1)
        self.assertIsInstance(result["reasonCodes"], list)
        self.assertTrue(result["reasonCodes"])
        self.assertEqual(len(result["reasonCodes"]), len(set(result["reasonCodes"])))
        self.assertIsInstance(result["missingAuthority"], list)
        self.assertIsInstance(result["invalidations"], list)
        self.assertIsInstance(result["materialDelta"], bool)
        for field in ("requestDigest", "authorityDigest", "evidenceDigest"):
            self.assertRegex(str(result[field]), r"^[0-9a-f]{64}$")
        if standing_contract is None:
            self.assertIsNone(result["standingContractDigest"])
        else:
            self.assertRegex(str(result["standingContractDigest"]), r"^[0-9a-f]{64}$")
        return result

    def assert_not_human_gate(self, result: dict[str, object]) -> None:
        self.assertNotEqual(result["decision"], "AWAIT_HUMAN")
        self.assertEqual(result["missingAuthority"], [])
        self.assertIsNone(result["gateKey"])

    def assert_human_gate(self, result: dict[str, object], concrete_term: str) -> None:
        self.assertEqual(result["decision"], "AWAIT_HUMAN")
        missing = result["missingAuthority"]
        self.assertTrue(missing)
        self.assertTrue(all(isinstance(item, str) and item.strip() for item in missing))
        self.assertIn(concrete_term, json.dumps(missing, sort_keys=True))
        self.assertRegex(str(result["gateKey"]), r"^[0-9a-f]{64}$")

    def test_versioned_result_contract_continues_an_approved_action(self) -> None:
        result = self.resolve()

        self.assertEqual(result["decision"], "CONTINUE")
        self.assertFalse(result["materialDelta"])
        self.assertEqual(result["invalidations"], [])
        self.assert_not_human_gate(result)

    def test_in_scope_local_repairs_and_derived_work_do_not_reopen_authority(self) -> None:
        cases = (
            approved_request(action="edit_authority_policy"),
            approved_request(
                action="refresh_derived_evidence",
                writeSet=["openspec/changes/centralize-devflow-authority-delta/evidence/run.json"],
                target="change-evidence",
            ),
            approved_request(
                action="run_independent_review",
                writeSet=[],
                effect="read-only.review",
                target="dev-flow-source",
                risk="read-only",
                ownership="review-contract",
            ),
        )

        for request in cases:
            with self.subTest(action=request["action"]):
                envelope = approved_envelope()
                if request["action"] == "refresh_derived_evidence":
                    envelope["writeSet"] = request["writeSet"]
                result = self.resolve(request=request, authority_envelope=envelope)
                self.assertEqual(result["decision"], "CONTINUE")
                self.assert_not_human_gate(result)

    def test_one_bounded_guard_is_explicitly_eligible(self) -> None:
        result = self.resolve(request=approved_request(guardRequired=True))

        self.assertEqual(result["decision"], "CONTINUE_WITH_MINIMAL_GUARD")
        self.assertFalse(result["materialDelta"])
        self.assert_not_human_gate(result)

    def test_approved_nonblocking_deferral_continues(self) -> None:
        result = self.resolve(request=approved_request(deferralApproved=True))

        self.assertEqual(result["decision"], "DEFER_AND_CONTINUE")
        self.assertFalse(result["materialDelta"])
        self.assert_not_human_gate(result)

    def test_active_owner_waits_without_deleting_or_creating_a_gate(self) -> None:
        result = self.resolve(
            request=cleanup_request(owner_exited=False),
            authority_envelope=cleanup_envelope(),
            evidence=current_evidence(ownerActive=True),
        )

        self.assertEqual(result["decision"], "WAIT_OWNER")
        self.assert_not_human_gate(result)

    def test_cleanup_safety_defects_precede_owner_wait(self) -> None:
        cases = (
            {"registered": False},
            {"taskOwned": False},
            {"exactPaths": False},
            {"identityCurrent": False},
            {"source": True},
            {"userContent": True},
            {"historicalReceipt": True},
            {"persistentEvidence": True},
            {"recursive": True},
        )

        for cleanup_override in cases:
            with self.subTest(cleanup=cleanup_override):
                result = self.resolve(
                    request=cleanup_request(
                        owner_exited=False,
                        cleanup=cleanup_override,
                    ),
                    authority_envelope=cleanup_envelope(),
                    evidence=current_evidence(ownerActive=True),
                )

                self.assertEqual(result["decision"], "FAIL_CLOSED_REPAIR")
                self.assert_not_human_gate(result)

    def test_owner_wait_requires_consistent_trusted_owner_state(self) -> None:
        cases = (
            (False, False),
            (True, True),
            (None, False),
        )

        for owner_active, owner_exited in cases:
            with self.subTest(owner_active=owner_active, owner_exited=owner_exited):
                result = self.resolve(
                    request=cleanup_request(owner_exited=owner_exited),
                    authority_envelope=cleanup_envelope(),
                    evidence=current_evidence(ownerActive=owner_active),
                )

                self.assertEqual(result["decision"], "FAIL_CLOSED_REPAIR")
                self.assertIn("cleanup:owner_state_ambiguous", result["invalidations"])
                self.assert_not_human_gate(result)

    def test_exact_owner_exited_task_output_auto_cleans(self) -> None:
        result = self.resolve(
            request=cleanup_request(),
            authority_envelope=cleanup_envelope(),
        )

        self.assertEqual(result["decision"], "AUTO_CLEAN")
        self.assertFalse(result["materialDelta"])
        self.assert_not_human_gate(result)

    def test_incomplete_or_drifted_technical_evidence_requires_repair_not_human(self) -> None:
        cases = (
            current_evidence(complete=False),
            current_evidence(current=False),
            current_evidence(identityCurrent=False),
            current_evidence(trusted=False),
        )

        for evidence in cases:
            with self.subTest(evidence=evidence):
                result = self.resolve(evidence=evidence)
                self.assertEqual(result["decision"], "FAIL_CLOSED_REPAIR")
                self.assertFalse(result["materialDelta"])
                self.assert_not_human_gate(result)

    def test_unknown_ownership_or_risk_names_the_concrete_missing_authority(self) -> None:
        cases = (
            (approved_request(ownership="unknown"), "ownership"),
            (approved_request(risk="unknown"), "risk"),
        )

        for request, expected_term in cases:
            with self.subTest(term=expected_term):
                result = self.resolve(request=request)
                self.assert_human_gate(result, expected_term)
                self.assertTrue(result["materialDelta"])

    def test_authority_envelope_requires_strict_ownership_and_risk_domains(self) -> None:
        cases: tuple[tuple[str, str, object, str], ...] = (
            (
                "missing ownerships",
                "allowedOwnerships",
                None,
                "envelope_allowed_ownerships_invalid",
            ),
            (
                "ownerships are not a list",
                "allowedOwnerships",
                "task-owned",
                "envelope_allowed_ownerships_invalid",
            ),
            (
                "ownerships contain a non-string",
                "allowedOwnerships",
                ["task-owned", 7],
                "envelope_allowed_ownerships_invalid",
            ),
            (
                "ownerships contain an unsupported class",
                "allowedOwnerships",
                ["task-owned", "caller-invented-owner"],
                "envelope_allowed_ownerships_invalid",
            ),
            (
                "missing risks",
                "allowedRisks",
                None,
                "envelope_allowed_risks_invalid",
            ),
            (
                "risks are not a list",
                "allowedRisks",
                {"local_reversible": True},
                "envelope_allowed_risks_invalid",
            ),
            (
                "risks contain a non-string",
                "allowedRisks",
                ["local_reversible", False],
                "envelope_allowed_risks_invalid",
            ),
            (
                "risks contain an unsupported class",
                "allowedRisks",
                ["local_reversible", "caller-invented-risk"],
                "envelope_allowed_risks_invalid",
            ),
        )

        for name, field, value, reason_code in cases:
            with self.subTest(name=name):
                envelope = approved_envelope()
                if value is None:
                    envelope.pop(field)
                else:
                    envelope[field] = value
                result = self.resolve(authority_envelope=envelope)

                self.assertEqual(result["decision"], "FAIL_CLOSED_REPAIR")
                self.assertIn(reason_code, result["reasonCodes"])
                self.assert_not_human_gate(result)

    def test_uncovered_known_ownership_or_risk_precedes_convenience_routes(self) -> None:
        cases = (
            (
                "ownership before guard and deferral",
                approved_request(
                    ownership="review-contract",
                    guardRequired=True,
                    deferralApproved=True,
                ),
                approved_envelope(allowedOwnerships=["task-owned"]),
                current_evidence(),
                "ownership:review-contract",
                "ownership_outside_authority_envelope",
            ),
            (
                "risk before guard and deferral",
                approved_request(
                    risk="read-only",
                    guardRequired=True,
                    deferralApproved=True,
                ),
                approved_envelope(allowedRisks=["local_reversible"]),
                current_evidence(),
                "risk:read-only",
                "risk_outside_authority_envelope",
            ),
            (
                "ownership before repair owner wait and cleanup",
                cleanup_request(
                    owner_exited=False,
                    ownership="review-contract",
                    guardRequired=True,
                    deferralApproved=True,
                ),
                cleanup_envelope() | {"allowedOwnerships": ["task-owned"]},
                current_evidence(complete=False, ownerActive=True),
                "ownership:review-contract",
                "ownership_outside_authority_envelope",
            ),
        )

        for name, request, envelope, evidence, missing, reason_code in cases:
            with self.subTest(name=name):
                result = self.resolve(
                    request=request,
                    authority_envelope=envelope,
                    evidence=evidence,
                )

                self.assert_human_gate(result, missing)
                self.assertTrue(result["materialDelta"])
                self.assertIn(reason_code, result["reasonCodes"])

    def test_malformed_bound_input_domains_are_technical_failures(self) -> None:
        cases = (
            (
                "missing goal identity",
                approved_request(),
                approved_envelope(goalId=""),
                current_evidence(),
                None,
                "authority_identity_goal_invalid",
            ),
            (
                "malformed plan identity",
                approved_request(),
                approved_envelope(planDigest={"digest": "not-a-token"}),
                current_evidence(),
                None,
                "authority_identity_plan_invalid",
            ),
            (
                "missing change identity",
                approved_request(),
                approved_envelope(changeId="unknown"),
                current_evidence(),
                None,
                "authority_identity_change_invalid",
            ),
            (
                "missing action identity",
                approved_request(action=""),
                approved_envelope(),
                current_evidence(),
                None,
                "request_action_invalid",
            ),
            (
                "malformed effect identity",
                approved_request(effect={"name": "local.write"}),
                approved_envelope(),
                current_evidence(),
                None,
                "request_effect_invalid",
            ),
            (
                "malformed target identity",
                approved_request(target=["dev-flow-source"]),
                approved_envelope(),
                current_evidence(),
                None,
                "request_target_malformed",
            ),
            (
                "malformed ownership identity",
                approved_request(ownership={"class": "task-owned"}),
                approved_envelope(),
                current_evidence(),
                None,
                "request_ownership_malformed",
            ),
            (
                "malformed risk identity",
                approved_request(risk=["local_reversible"]),
                approved_envelope(),
                current_evidence(),
                None,
                "request_risk_malformed",
            ),
            (
                "malformed evidence mapping",
                approved_request(),
                approved_envelope(),
                ["trusted"],
                None,
                "evidence_mapping_required",
            ),
            (
                "malformed standing effects",
                approved_request(
                    action="milestone.push",
                    scope="standing-milestone",
                    writeSet=[],
                    risk="declared_external",
                    effect="git.push",
                    target="origin:refs/heads/main",
                    ownership="standing-contract",
                ),
                approved_envelope(
                    writeSet=[],
                    allowedActions=["milestone.push"],
                    allowedEffects=[],
                    allowedTargets=[],
                ),
                current_evidence(),
                standing_milestone(effects={"git.push": True}),
                "standing_effects_invalid",
            ),
            (
                "malformed envelope effects",
                approved_request(),
                approved_envelope(allowedEffects=["local.write", 7]),
                current_evidence(),
                None,
                "envelope_allowed_effects_invalid",
            ),
        )

        for name, request, envelope, evidence, standing, reason_code in cases:
            with self.subTest(name=name):
                result = self.resolve(
                    request=request,
                    authority_envelope=envelope,
                    evidence=evidence,  # type: ignore[arg-type]
                    standing_contract=standing,
                )
                self.assertEqual(result["decision"], "FAIL_CLOSED_REPAIR")
                self.assertIn(reason_code, result["reasonCodes"])
                self.assert_not_human_gate(result)

    def test_malformed_write_sets_never_collapse_to_empty_authority(self) -> None:
        malformed_values: tuple[object, ...] = (
            None,
            {"path": True},
            7,
            "dev/plugins/dev-flow/scripts/workflow_authority_delta.py",
            ["dev/plugins/dev-flow/scripts/workflow_authority_delta.py", 7],
            [""],
        )

        for location in ("request", "envelope"):
            for value in malformed_values:
                with self.subTest(location=location, value=value):
                    request = approved_request()
                    envelope = approved_envelope()
                    if location == "request":
                        request["writeSet"] = value
                    else:
                        envelope["writeSet"] = value
                    result = self.resolve(request=request, authority_envelope=envelope)

                    self.assertEqual(result["decision"], "FAIL_CLOSED_REPAIR")
                    self.assertIn(f"{location}_write_set_invalid", result["reasonCodes"])
                    self.assert_not_human_gate(result)

    def test_supported_ownership_and_risk_domains_are_explicit(self) -> None:
        for ownership in (
            "task-owned",
            "review-contract",
            "standing-contract",
            "user-workstation",
            "repository",
        ):
            with self.subTest(ownership=ownership):
                result = self.resolve(
                    request=approved_request(ownership=ownership),
                    authority_envelope=approved_envelope(
                        allowedOwnerships=[ownership],
                    ),
                )
                self.assertEqual(result["decision"], "CONTINUE")

        for risk in (
            "local_reversible",
            "read-only",
            "reversible",
            "bounded",
        ):
            with self.subTest(risk=risk):
                result = self.resolve(
                    request=approved_request(risk=risk),
                    authority_envelope=approved_envelope(allowedRisks=[risk]),
                )
                self.assertEqual(result["decision"], "CONTINUE")

        for risk in ("external", "declared_external"):
            with self.subTest(risk=risk):
                result = self.resolve(
                    request=approved_request(risk=risk),
                    authority_envelope=approved_envelope(allowedRisks=[risk]),
                )
                self.assert_human_gate(result, "standing_milestone.contract")
                self.assertNotIn(f"risk:{risk}", result["missingAuthority"])

        for field, value in (
            ("ownership", "caller-invented-owner"),
            ("risk", "caller-invented-risk"),
        ):
            with self.subTest(field=field):
                result = self.resolve(request=approved_request(**{field: value}))
                self.assert_human_gate(result, value)

    def test_missing_target_is_a_concrete_authority_delta_not_a_technical_gate(self) -> None:
        result = self.resolve(request=approved_request(target=""))

        self.assert_human_gate(result, "target:unspecified")

    def test_destructive_cleanup_requires_a_sealed_mapping(self) -> None:
        request = cleanup_request(effect="destructive.cleanup")
        envelope = cleanup_envelope()
        envelope["allowedEffects"] = ["destructive.cleanup"]
        mixed_cleanup = copy.deepcopy(request["cleanup"])
        self.assertIsInstance(mixed_cleanup, dict)
        mixed_cleanup["taskOwned"] = "yes"
        extra_field_cleanup = copy.deepcopy(request["cleanup"])
        self.assertIsInstance(extra_field_cleanup, dict)
        extra_field_cleanup["unexpectedProof"] = True

        cases: tuple[tuple[str, object], ...] = (
            ("missing", None),
            ("string", "approved"),
            ("list", ["registered"]),
            ("mixed", mixed_cleanup),
            ("extra-field", extra_field_cleanup),
        )
        for name, cleanup in cases:
            with self.subTest(name=name):
                candidate = copy.deepcopy(request)
                if cleanup is None:
                    candidate.pop("cleanup")
                else:
                    candidate["cleanup"] = cleanup
                result = self.resolve(request=candidate, authority_envelope=envelope)

                self.assertEqual(result["decision"], "FAIL_CLOSED_REPAIR")
                self.assert_not_human_gate(result)
                self.assertTrue(
                    any(code.startswith("cleanup_") for code in result["reasonCodes"]),
                    result,
                )

    def test_guard_or_deferral_cannot_launder_undeclared_material_effects(self) -> None:
        for flag in ("guardRequired", "deferralApproved"):
            with self.subTest(flag=flag):
                result = self.resolve(
                    request=approved_request(
                        action="install_dependency",
                        writeSet=[],
                        risk="external",
                        effect="dependency.install_update",
                        target="global-workstation",
                        ownership="user-workstation",
                        **{flag: True},
                    ),
                    authority_envelope=approved_envelope(
                        writeSet=[],
                        allowedActions=[],
                        allowedEffects=[],
                        allowedTargets=[],
                        allowedOwnerships=["user-workstation"],
                        allowedRisks=["external"],
                    ),
                )

                self.assert_human_gate(result, "dependency.install_update")

    def test_contextual_side_effect_adapter_cannot_launder_a_different_effect(self) -> None:
        from workflow_side_effect_policy import side_effect_decision

        result = side_effect_decision(
            PLUGIN_ROOT,
            "git.commit",
            request=approved_request(effect="local.write"),
            authority_envelope=approved_envelope(),
            evidence=current_evidence(),
        )

        self.assertFalse(result["authorized"])
        self.assertEqual(
            result["authorityResolution"]["decision"],
            "FAIL_CLOSED_REPAIR",
        )
        self.assertIn(
            "request_policy_effect_mismatch",
            result["authorityResolution"]["reasonCodes"],
        )

    def test_contextual_side_effect_adapter_routes_standing_model_execution(self) -> None:
        from workflow_side_effect_policy import side_effect_decision

        result = side_effect_decision(
            PLUGIN_ROOT,
            "model.invoke",
            request=model_request(),
            authority_envelope=model_envelope(),
            evidence=current_evidence(actualCostUsd="17.42"),
        )

        self.assertTrue(result["authorized"])
        self.assertEqual(result["reason"], "authority_delta_resolved")
        self.assertEqual(result["authorityResolution"]["decision"], "CONTINUE")
        self.assert_not_human_gate(result["authorityResolution"])

    def test_contextual_side_effect_adapter_does_not_execute_deferred_work(self) -> None:
        from workflow_side_effect_policy import side_effect_decision

        result = side_effect_decision(
            PLUGIN_ROOT,
            "model.invoke",
            request=model_request(deferralApproved=True),
            authority_envelope=model_envelope(),
            evidence=current_evidence(actualCostUsd="0.00"),
        )

        self.assertFalse(result["authorized"])
        self.assertEqual(result["reason"], "authority_delta_not_resolved")
        self.assertEqual(
            result["authorityResolution"]["decision"],
            "DEFER_AND_CONTINUE",
        )
        self.assert_not_human_gate(result["authorityResolution"])

    def test_model_invoke_rejects_unbound_legacy_authorization_token(self) -> None:
        from workflow_side_effect_policy import side_effect_decision

        result = side_effect_decision(
            PLUGIN_ROOT,
            "model.invoke",
            {"current_standing_goal_execution_authority"},
        )

        self.assertFalse(result["authorized"])
        self.assertEqual(result["reason"], "authority_context_required")

    def test_material_target_delta_beats_cleanup_guard_deferral_and_repair(self) -> None:
        request = cleanup_request(
            guardRequired=True,
            deferralApproved=True,
            target="other-project",
        )
        result = self.resolve(
            request=request,
            authority_envelope=cleanup_envelope(),
            evidence=current_evidence(complete=False, ownerActive=True),
        )

        self.assert_human_gate(result, "other-project")
        self.assertTrue(result["materialDelta"])

    def test_precedence_is_total_and_exclusive(self) -> None:
        cases = (
            (
                "material delta",
                cleanup_request(target="other-project", guardRequired=True, deferralApproved=True),
                cleanup_envelope(),
                current_evidence(complete=False, ownerActive=True),
                "AWAIT_HUMAN",
            ),
            (
                "technical repair",
                cleanup_request(owner_exited=False, guardRequired=True, deferralApproved=True),
                cleanup_envelope(),
                current_evidence(complete=False, ownerActive=True),
                "FAIL_CLOSED_REPAIR",
            ),
            (
                "owner wait",
                cleanup_request(owner_exited=False, guardRequired=True, deferralApproved=True),
                cleanup_envelope(),
                current_evidence(ownerActive=True),
                "WAIT_OWNER",
            ),
            (
                "auto clean",
                cleanup_request(guardRequired=True, deferralApproved=True),
                cleanup_envelope(),
                current_evidence(),
                "AUTO_CLEAN",
            ),
            (
                "minimal guard",
                approved_request(guardRequired=True, deferralApproved=True),
                approved_envelope(),
                current_evidence(),
                "CONTINUE_WITH_MINIMAL_GUARD",
            ),
            (
                "deferral",
                approved_request(deferralApproved=True),
                approved_envelope(),
                current_evidence(),
                "DEFER_AND_CONTINUE",
            ),
            (
                "continue",
                approved_request(),
                approved_envelope(),
                current_evidence(),
                "CONTINUE",
            ),
        )

        for name, request, envelope, evidence, expected in cases:
            with self.subTest(name=name):
                result = self.resolve(
                    request=request,
                    authority_envelope=envelope,
                    evidence=evidence,
                )
                self.assertEqual(result["decision"], expected)

    def test_standing_milestone_covers_declared_commit_push_release_and_refresh(self) -> None:
        contract = standing_milestone()
        for action, effect, target in (
            ("milestone.commit", "git.commit", "origin:refs/heads/main"),
            ("milestone.push", "git.push", "origin:refs/heads/main"),
            ("milestone.publish", "github.release", "dev-flow-v0.4.0"),
            ("milestone.refresh", "plugin.refresh", "dev-flow@cy-codex-skills"),
        ):
            with self.subTest(action=action):
                request = approved_request(
                    action=action,
                    scope="standing-milestone",
                    writeSet=[],
                    risk="declared_external",
                    effect=effect,
                    target=target,
                    ownership="standing-contract",
                )
                envelope = approved_envelope(
                    writeSet=[],
                    allowedActions=[action],
                    allowedEffects=[],
                    allowedTargets=[],
                    allowedOwnerships=["standing-contract"],
                    allowedRisks=["declared_external"],
                )
                result = self.resolve(
                    request=request,
                    authority_envelope=envelope,
                    standing_contract=contract,
                )
                self.assertEqual(result["decision"], "CONTINUE")
                self.assert_not_human_gate(result)

    def test_standing_contract_identity_drift_invalidates_authority(self) -> None:
        request = approved_request(
            action="milestone.push",
            scope="standing-milestone",
            writeSet=[],
            risk="declared_external",
            effect="git.push",
            target="origin:refs/heads/main",
            ownership="standing-contract",
        )
        envelope = approved_envelope(
            writeSet=[],
            allowedActions=["milestone.push"],
            allowedEffects=[],
            allowedTargets=[],
            allowedOwnerships=["standing-contract"],
            allowedRisks=["declared_external"],
        )
        result = self.resolve(
            request=request,
            authority_envelope=envelope,
            standing_contract=standing_milestone(planDigest="different-reviewed-plan"),
        )

        self.assert_human_gate(result, "plan")
        self.assertTrue(result["materialDelta"])
        self.assertTrue(result["invalidations"])

    def test_standing_model_execution_does_not_require_release_milestone_authority(self) -> None:
        result = self.resolve(
            request=model_request(),
            authority_envelope=model_envelope(),
            evidence=current_evidence(actualCostUsd="17.42"),
        )

        self.assertEqual(result["decision"], "CONTINUE")
        self.assertIsNone(result["standingContractDigest"])
        self.assert_not_human_gate(result)

    def test_attempt_receipt_lifecycle_does_not_consume_standing_human_authority(self) -> None:
        envelope = model_envelope()
        first = self.resolve(
            request=model_request(attempt_id="g51-r3-attempt-1"),
            authority_envelope=envelope,
        )
        consumed = self.resolve(
            request=model_request(attempt_id="g51-r3-attempt-1"),
            authority_envelope=envelope,
            evidence=current_evidence(current=False, complete=False),
        )
        second = self.resolve(
            request=model_request(attempt_id="g51-r3-attempt-2"),
            authority_envelope=envelope,
        )

        self.assertEqual(first["decision"], "CONTINUE")
        self.assertEqual(consumed["decision"], "FAIL_CLOSED_REPAIR")
        self.assertEqual(second["decision"], "CONTINUE")
        self.assertEqual(first["authorityDigest"], second["authorityDigest"])
        self.assertNotEqual(first["requestDigest"], second["requestDigest"])
        for result in (first, consumed, second):
            self.assert_not_human_gate(result)

    def test_stable_model_execution_delta_names_exact_missing_authority(self) -> None:
        cases = (
            ("taskId", "OTHER:1"),
            ("provider", "other-provider"),
            ("model", "other-model"),
            ("credentialPolicy", "new-credential-privilege"),
            ("costPolicy", "new-spending-envelope"),
            ("serial", False),
        )

        for field, value in cases:
            with self.subTest(field=field):
                request = model_request()
                execution = dict(request["execution"])
                execution[field] = value
                request["execution"] = execution
                result = self.resolve(
                    request=request,
                    authority_envelope=model_envelope(),
                )

                self.assert_human_gate(result, f"execution:{field}")

    def test_malformed_model_execution_identity_is_a_technical_repair(self) -> None:
        malformed_request = model_request()
        malformed_request.pop("execution")
        malformed_envelope = model_envelope()
        malformed_envelope["standingExecution"] = {
            "taskId": "PLATFORM-E50:5.13",
        }

        for request, envelope in (
            (malformed_request, model_envelope()),
            (model_request(attempt_id=""), model_envelope()),
            (model_request(), malformed_envelope),
        ):
            with self.subTest(request=request, envelope=envelope):
                result = self.resolve(request=request, authority_envelope=envelope)
                self.assertEqual(result["decision"], "FAIL_CLOSED_REPAIR")
                self.assert_not_human_gate(result)

    def test_nonblocking_model_adjacent_optimization_defers_and_continues(self) -> None:
        result = self.resolve(
            request=model_request(deferralApproved=True),
            authority_envelope=model_envelope(),
        )

        self.assertEqual(result["decision"], "DEFER_AND_CONTINUE")
        self.assert_not_human_gate(result)

    def test_undeclared_legacy_external_effect_remains_default_denied(self) -> None:
        request = approved_request(
            action="legacy.provider.install",
            scope="legacy",
            writeSet=[],
            risk="external",
            effect="dependency.install_update",
            target="global-workstation",
            ownership="user-workstation",
        )
        envelope = approved_envelope(
            writeSet=[],
            allowedActions=[],
            allowedEffects=[],
            allowedTargets=[],
            allowedOwnerships=["user-workstation"],
            allowedRisks=["external"],
        )
        result = self.resolve(request=request, authority_envelope=envelope)

        self.assert_human_gate(result, "dependency.install_update")
        self.assertTrue(result["materialDelta"])

    def test_only_await_human_can_have_missing_authority_or_gate_key(self) -> None:
        non_human_results = (
            self.resolve(),
            self.resolve(request=approved_request(guardRequired=True)),
            self.resolve(request=approved_request(deferralApproved=True)),
            self.resolve(
                request=cleanup_request(owner_exited=False),
                authority_envelope=cleanup_envelope(),
                evidence=current_evidence(ownerActive=True),
            ),
            self.resolve(request=cleanup_request(), authority_envelope=cleanup_envelope()),
            self.resolve(evidence=current_evidence(complete=False)),
        )
        for result in non_human_results:
            with self.subTest(decision=result["decision"]):
                self.assert_not_human_gate(result)

        human = self.resolve(request=approved_request(ownership="unknown"))
        self.assert_human_gate(human, "ownership")

    def test_canonical_digests_and_gate_keys_are_stable_across_mapping_order(self) -> None:
        request = approved_request(
            action="publish_unnamed_target",
            writeSet=[],
            effect="github.release",
            target="other-channel",
            risk="external",
        )
        envelope = approved_envelope(
            writeSet=[],
            allowedActions=[],
            allowedEffects=[],
            allowedTargets=[],
            allowedRisks=["external"],
        )
        evidence = current_evidence()
        contract = standing_milestone()

        first = self.resolve(
            request=request,
            authority_envelope=envelope,
            evidence=evidence,
            standing_contract=contract,
        )
        second = self.resolve(
            request=dict(reversed(tuple(request.items()))),
            authority_envelope=dict(reversed(tuple(envelope.items()))),
            evidence=dict(reversed(tuple(evidence.items()))),
            standing_contract=dict(reversed(tuple(contract.items()))),
        )

        self.assertEqual(first, second)
        self.assert_human_gate(first, "other-channel")

    def test_each_bound_identity_invalidates_the_resolution_digest(self) -> None:
        baseline = self.resolve()

        changed_request = approved_request(action="refresh_derived_evidence")
        changed_envelope = approved_envelope(planDigest="plan-authority-delta-v2")
        changed_evidence = current_evidence(identityCurrent=False)

        request_result = self.resolve(request=changed_request)
        envelope_result = self.resolve(authority_envelope=changed_envelope)
        evidence_result = self.resolve(evidence=changed_evidence)

        self.assertNotEqual(baseline["requestDigest"], request_result["requestDigest"])
        self.assertNotEqual(baseline["authorityDigest"], envelope_result["authorityDigest"])
        self.assertNotEqual(baseline["evidenceDigest"], evidence_result["evidenceDigest"])

    def test_cleanup_ambiguity_is_preserved_and_fails_closed(self) -> None:
        request = cleanup_request(
            ownership="unknown",
            cleanup={"registered": False, "taskOwned": False},
        )
        result = self.resolve(
            request=request,
            authority_envelope=cleanup_envelope(),
            evidence=current_evidence(deterministicRepairAvailable=False),
        )

        self.assert_human_gate(result, "ownership")
        self.assertNotEqual(result["decision"], "AUTO_CLEAN")


if __name__ == "__main__":
    unittest.main()
