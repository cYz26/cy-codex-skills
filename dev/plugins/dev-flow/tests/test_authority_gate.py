import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

CANONICAL_GATE_KEY = "sha256:2cc6a57a0565244411648810c196f06166e996cc1649d0f2b2144a7052491856"


class AuthorityGateTests(unittest.TestCase):
    def make_repo(self):
        temporary = tempfile.TemporaryDirectory(prefix="devflow-authority-gate-")
        self.addCleanup(temporary.cleanup)
        repo = Path(temporary.name)
        (repo / ".dev-flow.json").write_text('{"workflow":{"mode":"full-openspec"}}\n')
        (repo / "openspec" / "changes" / "demo").mkdir(parents=True)
        (repo / "openspec" / "changes" / "demo" / "tasks.md").write_text(
            "## Work\n\n- [ ] 1.1 Continue\n"
        )
        state = repo / ".planning" / "devflow" / "STATE.md"
        state.parent.mkdir(parents=True)
        state.write_text(
            """---
workflow_version: 0.4.0
project_mode: brownfield
current_stage: executing
current_change:
  id: demo
  status: executing
gates:
  workflow_initialized: true
  spec_approved: true
  plan_written: true
  tests_baseline_known: true
  implementation_done: false
  verification_passed: false
  state_updated: true
  archive_allowed: false
  release_allowed: false
implementation_readiness:
  required: false
goal_gate:
  id: goal-demo
  required: true
  status: satisfied
  reason: goal-backed-change
  suggested_goal: none
---
# Workflow State

## Current Status

Executing.

## Next Action

Continue.
"""
        )
        return repo, state

    def resolution(self, *, decision="AWAIT_HUMAN", missing=None):
        return {
            "schemaVersion": "1.0",
            "kind": "devflow-authority-delta-resolution",
            "decision": decision,
            "reasonCodes": ["undeclared_public_contract"],
            "missingAuthority": list(
                ["public_contract:demo-output"] if missing is None else missing
            ),
            "invalidations": [],
            "materialDelta": decision == "AWAIT_HUMAN",
            "authorityContractSha256": "sha256:" + "a" * 64,
            "evidenceSha256": "sha256:" + "b" * 64,
            "requestSha256": "sha256:" + "c" * 64,
            "gateKey": CANONICAL_GATE_KEY if decision == "AWAIT_HUMAN" else None,
        }

    def write_authority_artifact(
        self,
        repo,
        recorded,
        *,
        relative="openspec/changes/demo/evidence/authority-grant.json",
        payload_overrides=None,
    ):
        receipt_path = repo / recorded["receiptPath"]
        receipt_bytes = receipt_path.read_bytes()
        receipt = json.loads(receipt_bytes)
        payload = {
            "schemaVersion": "1.0",
            "kind": "devflow-authority-grant",
            "status": "approved",
            "goalId": "goal-demo",
            "changeId": "demo",
            "gateKey": recorded["gateKey"],
            "priorReceiptSha256": "sha256:" + hashlib.sha256(receipt_bytes).hexdigest(),
            "priorAuthorityContractSha256": receipt["authorityContractSha256"],
            "priorEvidenceSha256": receipt["evidenceSha256"],
            "grantedAuthority": receipt["missingAuthority"],
        }
        payload.update(payload_overrides or {})
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        artifact_bytes = (
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        ).encode("utf-8")
        path.write_bytes(artifact_bytes)
        return relative, "sha256:" + hashlib.sha256(artifact_bytes).hexdigest()

    def promotion_proof(
        self,
        repo,
        recorded,
        *,
        resume_stage="executing",
        artifact_path=None,
        artifact_overrides=None,
        **overrides,
    ):
        receipt_path = repo / recorded["receiptPath"]
        receipt_bytes = receipt_path.read_bytes()
        receipt = json.loads(receipt_bytes)
        authority_artifact_path, authority_artifact_sha256 = self.write_authority_artifact(
            repo,
            recorded,
            relative=(
                artifact_path
                or "openspec/changes/demo/evidence/authority-grant.json"
            ),
            payload_overrides=artifact_overrides,
        )
        proof = {
            "schemaVersion": "1.0",
            "kind": "devflow-authority-promotion-proof",
            "decision": "CONTINUE",
            "reasonCodes": ["authority_promotion_current"],
            "missingAuthority": [],
            "materialDelta": False,
            "trusted": True,
            "current": True,
            "evidenceCurrent": True,
            "gateKey": recorded["gateKey"],
            "priorReceiptSha256": "sha256:" + hashlib.sha256(receipt_bytes).hexdigest(),
            "priorMissingAuthority": receipt["missingAuthority"],
            "promotedAuthority": receipt["missingAuthority"],
            "priorAuthorityContractSha256": receipt["authorityContractSha256"],
            "priorEvidenceSha256": receipt["evidenceSha256"],
            "authorityArtifactPath": authority_artifact_path,
            "authorityArtifactSha256": authority_artifact_sha256,
            "goalId": "goal-demo",
            "changeId": "demo",
            "resumeStage": resume_stage,
        }
        proof.update(overrides)
        return proof

    def test_record_atomically_sets_both_markers_and_binds_concrete_authority(self):
        from workflow_authority_gate import record_authority_gate
        from workflow_state import parse_state

        repo, _ = self.make_repo()
        receipt = record_authority_gate(
            repo,
            self.resolution(),
            next_question="May the public demo-output contract be added?",
        )
        state = parse_state(repo)

        self.assertEqual(receipt["status"], "recorded")
        self.assertEqual(state["current_stage"], "awaiting_human")
        self.assertEqual(state["current_change"]["status"], "awaiting_human")
        self.assertEqual(state["authority_gate"]["key"], CANONICAL_GATE_KEY)
        self.assertEqual(
            state["authority_gate"]["missing_authority"],
            ["public_contract:demo-output"],
        )
        receipt_path = repo / receipt["receiptPath"]
        self.assertEqual(json.loads(receipt_path.read_text())["gateKey"], receipt["gateKey"])

    def test_identical_gate_replay_is_read_only_and_reuses_receipt(self):
        from workflow_authority_gate import record_authority_gate

        repo, state_path = self.make_repo()
        first = record_authority_gate(
            repo,
            self.resolution(),
            next_question="May the public demo-output contract be added?",
        )
        before = state_path.read_bytes()
        second = record_authority_gate(
            repo,
            self.resolution(),
            next_question="May the public demo-output contract be added?",
            prior_receipt=repo / first["receiptPath"],
        )

        self.assertEqual(second["status"], "replayed")
        self.assertEqual(second["gateKey"], first["gateKey"])
        self.assertEqual(state_path.read_bytes(), before)

    def test_receipt_first_crash_retries_same_identity_and_activates_once(self):
        from workflow_authority_gate import record_authority_gate
        from workflow_state import parse_state

        repo, state_path = self.make_repo()
        before = state_path.read_bytes()
        receipt_path = (
            repo
            / ".planning"
            / "devflow"
            / "authority-gates"
            / f"{CANONICAL_GATE_KEY.removeprefix('sha256:')}.json"
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "injected crash after authority gate receipt persistence",
        ):
            record_authority_gate(
                repo,
                self.resolution(),
                next_question="May the public demo-output contract be added?",
                _fault_after_receipt_persisted=True,
            )

        self.assertTrue(receipt_path.is_file())
        self.assertEqual(state_path.read_bytes(), before)

        recovered = record_authority_gate(
            repo,
            self.resolution(),
            next_question="May the public demo-output contract be added?",
            prior_receipt=receipt_path,
        )
        active = parse_state(repo)

        self.assertEqual(recovered["status"], "recorded")
        self.assertEqual(active["current_stage"], "awaiting_human")
        self.assertEqual(active["current_change"]["status"], "awaiting_human")
        self.assertEqual(active["authority_gate"]["key"], CANONICAL_GATE_KEY)
        finalized = json.loads(receipt_path.read_text())
        self.assertEqual(finalized["kind"], "devflow-authority-gate-receipt")
        self.assertNotIn("expectedPreGateState", finalized)

        activated = state_path.read_bytes()
        replayed = record_authority_gate(
            repo,
            self.resolution(),
            next_question="May the public demo-output contract be added?",
            prior_receipt=receipt_path,
        )
        self.assertEqual(replayed["status"], "replayed")
        self.assertEqual(state_path.read_bytes(), activated)

    def test_pending_receipt_recovery_rejects_drift_mismatch_and_stale_replay(self):
        from workflow_authority_gate import (
            AuthorityGateError,
            canonical_authority_gate_key_from_resolution,
            clear_authority_gate,
            record_authority_gate,
        )

        question = "May the public demo-output contract be added?"

        repo, state_path = self.make_repo()
        receipt_path = (
            repo
            / ".planning"
            / "devflow"
            / "authority-gates"
            / f"{CANONICAL_GATE_KEY.removeprefix('sha256:')}.json"
        )
        with self.assertRaises(RuntimeError):
            record_authority_gate(
                repo,
                self.resolution(),
                next_question=question,
                _fault_after_receipt_persisted=True,
            )
        pending = json.loads(receipt_path.read_text())
        self.assertEqual(
            pending["kind"],
            "devflow-authority-gate-write-ahead-intent",
        )
        self.assertEqual(pending["expectedPreGateState"]["changeId"], "demo")
        self.assertEqual(pending["expectedPreGateState"]["goalId"], "goal-demo")

        for name, mutate in (
            (
                "receipt-mismatch",
                lambda document, path: document["receipt"].__setitem__(
                    "nextQuestion", "A different question?"
                ),
            ),
            (
                "arbitrary-pre-state",
                lambda document, path: document["expectedPreGateState"].__setitem__(
                    "sha256", "sha256:" + "9" * 64
                ),
            ),
        ):
            with self.subTest(name=name):
                receipt_path.write_text(
                    json.dumps(pending, indent=2, sort_keys=True) + "\n"
                )
                document = json.loads(receipt_path.read_text())
                mutate(document, receipt_path)
                receipt_path.write_text(
                    json.dumps(document, indent=2, sort_keys=True) + "\n"
                )
                before = state_path.read_bytes()
                with self.assertRaises(AuthorityGateError):
                    record_authority_gate(
                        repo,
                        self.resolution(),
                        next_question=question,
                        prior_receipt=receipt_path,
                    )
                self.assertEqual(state_path.read_bytes(), before)

        receipt_path.write_text(json.dumps(pending, indent=2, sort_keys=True) + "\n")
        state_path.write_text(state_path.read_text().replace("Executing.\n", "Drifted.\n"))
        drifted = state_path.read_bytes()
        with self.assertRaises(AuthorityGateError):
            record_authority_gate(
                repo,
                self.resolution(),
                next_question=question,
                prior_receipt=receipt_path,
            )
        self.assertEqual(state_path.read_bytes(), drifted)

        changed_evidence = self.resolution()
        changed_evidence["evidenceSha256"] = "sha256:" + "e" * 64
        changed_evidence["gateKey"] = canonical_authority_gate_key_from_resolution(
            changed_evidence
        )
        with self.assertRaises(AuthorityGateError):
            record_authority_gate(
                repo,
                changed_evidence,
                next_question=question,
                prior_receipt=receipt_path,
            )

        evidence_repo, evidence_state_path = self.make_repo()
        evidence_receipt_path = (
            evidence_repo
            / ".planning"
            / "devflow"
            / "authority-gates"
            / f"{CANONICAL_GATE_KEY.removeprefix('sha256:')}.json"
        )
        with self.assertRaises(RuntimeError):
            record_authority_gate(
                evidence_repo,
                self.resolution(),
                next_question=question,
                _fault_after_receipt_persisted=True,
            )
        evidence_before = evidence_state_path.read_bytes()
        with self.assertRaises(AuthorityGateError):
            record_authority_gate(
                evidence_repo,
                changed_evidence,
                next_question=question,
            )
        changed_receipt_path = (
            evidence_repo
            / ".planning"
            / "devflow"
            / "authority-gates"
            / f"{changed_evidence['gateKey'].removeprefix('sha256:')}.json"
        )
        self.assertTrue(evidence_receipt_path.is_file())
        self.assertFalse(changed_receipt_path.exists())
        self.assertEqual(evidence_state_path.read_bytes(), evidence_before)

        cross_repo, cross_state_path = self.make_repo()
        cross_receipt_path = (
            cross_repo
            / ".planning"
            / "devflow"
            / "authority-gates"
            / f"{CANONICAL_GATE_KEY.removeprefix('sha256:')}.json"
        )
        with self.assertRaises(RuntimeError):
            record_authority_gate(
                cross_repo,
                self.resolution(),
                next_question=question,
                _fault_after_receipt_persisted=True,
            )
        cross_state_path.write_text(
            cross_state_path.read_text().replace("  id: demo", "  id: other-change")
        )
        cross_changed = cross_state_path.read_bytes()
        with self.assertRaises(AuthorityGateError):
            record_authority_gate(
                cross_repo,
                self.resolution(),
                next_question=question,
                prior_receipt=cross_receipt_path,
            )
        self.assertEqual(cross_state_path.read_bytes(), cross_changed)

        stale_repo, stale_state_path = self.make_repo()
        stale_receipt_path = (
            stale_repo
            / ".planning"
            / "devflow"
            / "authority-gates"
            / f"{CANONICAL_GATE_KEY.removeprefix('sha256:')}.json"
        )
        with self.assertRaises(RuntimeError):
            record_authority_gate(
                stale_repo,
                self.resolution(),
                next_question=question,
                _fault_after_receipt_persisted=True,
            )
        stale_pending = stale_receipt_path.read_bytes()
        recorded = record_authority_gate(
            stale_repo,
            self.resolution(),
            next_question=question,
            prior_receipt=stale_receipt_path,
        )
        clear_authority_gate(
            stale_repo,
            gate_key=recorded["gateKey"],
            resolution=self.promotion_proof(stale_repo, recorded),
            resume_stage="executing",
        )
        stale_receipt_path.write_bytes(stale_pending)
        cleared = stale_state_path.read_bytes()
        with self.assertRaises(AuthorityGateError):
            record_authority_gate(
                stale_repo,
                self.resolution(),
                next_question=question,
                prior_receipt=stale_receipt_path,
            )
        self.assertEqual(stale_state_path.read_bytes(), cleared)

    def test_non_human_or_empty_missing_authority_cannot_write_awaiting_state(self):
        from workflow_authority_gate import AuthorityGateError, record_authority_gate

        for resolution in (
            self.resolution(decision="FAIL_CLOSED_REPAIR", missing=[]),
            self.resolution(missing=[]),
        ):
            repo, state_path = self.make_repo()
            before = state_path.read_bytes()
            with self.subTest(decision=resolution["decision"]), self.assertRaises(
                AuthorityGateError
            ):
                record_authority_gate(repo, resolution, next_question="Invalid gate")
            self.assertEqual(state_path.read_bytes(), before)

    def test_material_delta_must_be_strictly_true_before_any_gate_write(self):
        from workflow_authority_gate import AuthorityGateError, record_authority_gate

        repo, state_path = self.make_repo()
        invalid = self.resolution()
        invalid["materialDelta"] = False
        before = state_path.read_bytes()

        with self.assertRaises(AuthorityGateError):
            record_authority_gate(repo, invalid, next_question="Invalid gate")

        self.assertEqual(state_path.read_bytes(), before)
        self.assertFalse((repo / ".planning" / "devflow" / "authority-gates").exists())

    def test_all_three_identity_digests_must_be_non_placeholder_sha256(self):
        from workflow_authority_gate import AuthorityGateError, record_authority_gate

        for field in (
            "authorityContractSha256",
            "evidenceSha256",
            "requestSha256",
        ):
            with self.subTest(field=field):
                repo, state_path = self.make_repo()
                invalid = self.resolution()
                invalid[field] = "none"
                before = state_path.read_bytes()

                with self.assertRaises(AuthorityGateError):
                    record_authority_gate(repo, invalid, next_question="Invalid gate")

                self.assertEqual(state_path.read_bytes(), before)
                self.assertFalse(
                    (repo / ".planning" / "devflow" / "authority-gates").exists()
                )

        from workflow_authority_gate import canonical_authority_gate_key

        repo, state_path = self.make_repo()
        zero_bound = self.resolution()
        zero_bound["evidenceSha256"] = "sha256:" + "0" * 64
        zero_bound["gateKey"] = canonical_authority_gate_key(
            missing_authority=zero_bound["missingAuthority"],
            authority_contract_sha256=zero_bound["authorityContractSha256"],
            evidence_sha256=zero_bound["evidenceSha256"],
            request_sha256=zero_bound["requestSha256"],
        )
        before = state_path.read_bytes()
        with self.assertRaises(AuthorityGateError):
            record_authority_gate(repo, zero_bound, next_question="Invalid gate")
        self.assertEqual(state_path.read_bytes(), before)

    def test_clear_rejects_missing_off_scope_tampered_or_fabricated_authority_artifact(self):
        from workflow_authority_gate import (
            AuthorityGateError,
            clear_authority_gate,
            record_authority_gate,
        )

        for case in (
            "missing",
            "off-scope",
            "tampered",
            "unchanged",
            "fabricated-grant",
            "fabricated-goal",
            "fabricated-change",
        ):
            with self.subTest(case=case):
                repo, state_path = self.make_repo()
                recorded = record_authority_gate(
                    repo,
                    self.resolution(),
                    next_question="May the public demo-output contract be added?",
                )
                proof = self.promotion_proof(repo, recorded)
                artifact = repo / proof["authorityArtifactPath"]
                if case == "missing":
                    artifact.unlink()
                elif case == "off-scope":
                    outside = repo / "other" / "authority-grant.json"
                    outside.parent.mkdir(parents=True)
                    outside.write_bytes(artifact.read_bytes())
                    proof["authorityArtifactPath"] = "other/authority-grant.json"
                    proof["authorityArtifactSha256"] = (
                        "sha256:" + hashlib.sha256(outside.read_bytes()).hexdigest()
                    )
                elif case == "tampered":
                    artifact.write_bytes(artifact.read_bytes() + b"\n")
                elif case == "unchanged":
                    artifact.write_bytes((repo / recorded["receiptPath"]).read_bytes())
                    proof["authorityArtifactSha256"] = (
                        "sha256:" + hashlib.sha256(artifact.read_bytes()).hexdigest()
                    )
                else:
                    payload = json.loads(artifact.read_text())
                    field, value = {
                        "fabricated-grant": (
                            "grantedAuthority",
                            ["other:authority"],
                        ),
                        "fabricated-goal": ("goalId", "other-goal"),
                        "fabricated-change": ("changeId", "other-change"),
                    }[case]
                    payload[field] = value
                    artifact.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
                    proof["authorityArtifactSha256"] = (
                        "sha256:" + hashlib.sha256(artifact.read_bytes()).hexdigest()
                    )
                before = state_path.read_bytes()

                with self.assertRaises(AuthorityGateError):
                    clear_authority_gate(
                        repo,
                        gate_key=recorded["gateKey"],
                        resolution=proof,
                        resume_stage="executing",
                    )

                self.assertEqual(state_path.read_bytes(), before)

    def test_clear_rejects_symlinked_authority_artifact_path_chain(self):
        from workflow_authority_gate import (
            AuthorityGateError,
            clear_authority_gate,
            record_authority_gate,
        )

        for case in ("leaf", "parent"):
            with self.subTest(case=case):
                repo, state_path = self.make_repo()
                recorded = record_authority_gate(
                    repo,
                    self.resolution(),
                    next_question="May the public demo-output contract be added?",
                )
                proof = self.promotion_proof(repo, recorded)
                artifact = repo / proof["authorityArtifactPath"]
                artifact_bytes = artifact.read_bytes()
                if case == "leaf":
                    real = artifact.with_name("authority-grant-real.json")
                    real.write_bytes(artifact_bytes)
                    artifact.unlink()
                    artifact.symlink_to(real.name)
                else:
                    real_parent = repo / "authority-grant-real-parent"
                    real_parent.mkdir()
                    (real_parent / artifact.name).write_bytes(artifact_bytes)
                    artifact.unlink()
                    artifact.parent.rmdir()
                    artifact.parent.symlink_to(real_parent, target_is_directory=True)
                before = state_path.read_bytes()

                with self.assertRaises(AuthorityGateError):
                    clear_authority_gate(
                        repo,
                        gate_key=recorded["gateKey"],
                        resolution=proof,
                        resume_stage="executing",
                    )

                self.assertEqual(state_path.read_bytes(), before)

    def test_compatible_bare_gate_key_is_recomputed_and_normalized(self):
        from workflow_authority_gate import record_authority_gate
        from workflow_state import parse_state

        repo, _ = self.make_repo()
        compatible = self.resolution()
        compatible["gateKey"] = CANONICAL_GATE_KEY.removeprefix("sha256:")

        receipt = record_authority_gate(
            repo,
            compatible,
            next_question="May the public demo-output contract be added?",
        )

        self.assertEqual(receipt["gateKey"], CANONICAL_GATE_KEY)
        self.assertEqual(parse_state(repo)["authority_gate"]["key"], CANONICAL_GATE_KEY)

    def test_well_formed_but_noncanonical_gate_key_is_rejected_without_writes(self):
        from workflow_authority_gate import AuthorityGateError, record_authority_gate

        repo, state_path = self.make_repo()
        invalid = self.resolution()
        invalid["gateKey"] = "sha256:" + "d" * 64
        before = state_path.read_bytes()

        with self.assertRaises(AuthorityGateError):
            record_authority_gate(repo, invalid, next_question="Invalid gate")

        self.assertEqual(state_path.read_bytes(), before)
        self.assertFalse((repo / ".planning" / "devflow" / "authority-gates").exists())

    def test_standing_gate_resolve_record_inspect_replay_and_promotion_clear(self):
        from workflow_authority_delta import resolve_authority_delta
        from workflow_authority_gate import clear_authority_gate, record_authority_gate
        from workflow_continuation import decide_continuation, inspect_authority_gate
        from workflow_state import parse_state

        repo, _ = self.make_repo()
        standing = {
            "schemaVersion": 1,
            "goalId": "goal-demo",
            "changeId": "demo",
            "planDigest": "reviewed-plan-v1",
            "effects": ["git.push"],
            "targets": ["origin:refs/heads/main"],
            "current": True,
        }
        resolution = resolve_authority_delta(
            request={
                "action": "milestone.push",
                "scope": "standing-milestone",
                "writeSet": [],
                "risk": "declared_external",
                "effect": "git.push",
                "target": "origin:refs/heads/other",
                "ownership": "standing-contract",
            },
            authority_envelope={
                "goalId": "goal-demo",
                "changeId": "demo",
                "planDigest": "reviewed-plan-v1",
                "writeSet": [],
                "allowedActions": ["milestone.push"],
                "allowedEffects": [],
                "allowedTargets": [],
                "allowedOwnerships": ["standing-contract"],
                "allowedRisks": ["declared_external"],
            },
            evidence={
                "trusted": True,
                "current": True,
                "complete": True,
                "identityCurrent": True,
            },
            standing_contract=standing,
        )

        receipt = record_authority_gate(
            repo,
            resolution,
            next_question="May the standing milestone target refs/heads/other?",
        )

        self.assertEqual(resolution["decision"], "AWAIT_HUMAN")
        self.assertEqual(
            receipt["gateKey"],
            "sha256:" + str(resolution["gateKey"]),
        )
        self.assertEqual(
            receipt["standingContractDigest"],
            "sha256:" + str(resolution["standingContractDigest"]),
        )
        inspected = inspect_authority_gate(repo, parse_state(repo))
        self.assertTrue(inspected["valid"], inspected)
        self.assertEqual(
            inspected["resolution"]["standingContractDigest"],
            receipt["standingContractDigest"],
        )
        continued_gate = decide_continuation(
            source_valid=True,
            work_remaining=True,
            checkpoint_recommended=False,
            verification_passed=False,
            human_gate=True,
            external_effect_ready=False,
            human_gate_resolution=inspected["resolution"],
        )
        self.assertEqual(continued_gate["action"], "AWAIT_HUMAN")
        self.assertEqual(continued_gate["gateKey"], receipt["gateKey"])

        replayed = record_authority_gate(
            repo,
            resolution,
            next_question="May the standing milestone target refs/heads/other?",
            prior_receipt=repo / receipt["receiptPath"],
        )
        self.assertEqual(replayed["status"], "replayed")
        self.assertEqual(replayed["gateKey"], receipt["gateKey"])
        self.assertEqual(
            replayed["standingContractDigest"],
            receipt["standingContractDigest"],
        )

        cleared = clear_authority_gate(
            repo,
            gate_key=receipt["gateKey"],
            resolution=self.promotion_proof(repo, receipt),
            resume_stage="executing",
        )
        cleared_state = parse_state(repo)
        self.assertEqual(cleared["status"], "cleared")
        self.assertEqual(cleared_state["current_stage"], "executing")
        self.assertEqual(cleared_state["current_change"]["status"], "executing")

    def test_standing_digest_drift_cannot_reuse_a_canonical_gate_key(self):
        from workflow_authority_delta import resolve_authority_delta
        from workflow_authority_gate import AuthorityGateError, record_authority_gate

        repo, state_path = self.make_repo()
        standing = {
            "schemaVersion": 1,
            "goalId": "goal-demo",
            "changeId": "demo",
            "planDigest": "reviewed-plan-v1",
            "effects": ["git.push"],
            "targets": ["origin:refs/heads/main"],
            "current": True,
        }
        resolution = resolve_authority_delta(
            request={
                "action": "milestone.push",
                "scope": "standing-milestone",
                "writeSet": [],
                "risk": "declared_external",
                "effect": "git.push",
                "target": "origin:refs/heads/other",
                "ownership": "standing-contract",
            },
            authority_envelope={
                "goalId": "goal-demo",
                "changeId": "demo",
                "planDigest": "reviewed-plan-v1",
                "writeSet": [],
                "allowedActions": ["milestone.push"],
                "allowedEffects": [],
                "allowedTargets": [],
                "allowedOwnerships": ["standing-contract"],
                "allowedRisks": ["declared_external"],
            },
            evidence={
                "trusted": True,
                "current": True,
                "complete": True,
                "identityCurrent": True,
            },
            standing_contract=standing,
        )
        resolution["standingContractDigest"] = "9" * 64
        before = state_path.read_bytes()

        with self.assertRaises(AuthorityGateError):
            record_authority_gate(
                repo,
                resolution,
                next_question="May the standing milestone target refs/heads/other?",
            )

        self.assertEqual(state_path.read_bytes(), before)
        self.assertFalse((repo / ".planning" / "devflow" / "authority-gates").exists())

    def test_gate_lists_must_be_exact_canonical_unique_string_lists(self):
        from workflow_authority_gate import (
            AuthorityGateError,
            canonical_authority_gate_key,
            record_authority_gate,
        )

        missing = "public_contract:demo-output"
        for candidate in (
            [missing, 7],
            [missing, missing],
            [missing, ""],
            [f" {missing}"],
            [f"{missing} "],
        ):
            with self.subTest(seam="canonical-key", candidate=candidate):
                with self.assertRaises(AuthorityGateError):
                    canonical_authority_gate_key(
                        missing_authority=candidate,  # type: ignore[arg-type]
                        authority_contract_sha256="sha256:" + "a" * 64,
                        evidence_sha256="sha256:" + "b" * 64,
                        request_sha256="sha256:" + "c" * 64,
                    )

        base_values = {
            "missingAuthority": missing,
            "reasonCodes": "undeclared_public_contract",
            "invalidations": "contract:public",
        }
        malformed: list[tuple[str, object]] = []
        for field, value in base_values.items():
            malformed.extend(
                (
                    (field, [value, 7]),
                    (field, [value, value]),
                    (field, [value, ""]),
                    (field, [f" {value}"]),
                    (field, [f"{value} "]),
                )
            )

        for field, value in malformed:
            with self.subTest(seam="recorder", field=field, value=value):
                repo, state_path = self.make_repo()
                invalid = self.resolution()
                invalid[field] = value
                before = state_path.read_bytes()
                with self.assertRaises(AuthorityGateError):
                    record_authority_gate(repo, invalid, next_question="Invalid gate")
                self.assertEqual(state_path.read_bytes(), before)
                self.assertFalse(
                    (repo / ".planning" / "devflow" / "authority-gates").exists()
                )

        repo, state_path = self.make_repo()
        no_reason = self.resolution()
        no_reason["reasonCodes"] = []
        before = state_path.read_bytes()
        with self.assertRaises(AuthorityGateError):
            record_authority_gate(repo, no_reason, next_question="Invalid gate")
        self.assertEqual(state_path.read_bytes(), before)

    def test_central_resolution_with_exact_lists_records_without_normalization(self):
        from workflow_authority_delta import resolve_authority_delta
        from workflow_authority_gate import record_authority_gate

        resolution = resolve_authority_delta(
            request={
                "action": "edit_authority_policy",
                "scope": "approved-slice",
                "writeSet": [],
                "risk": "local_reversible",
                "effect": "local.write",
                "target": "other-project",
                "ownership": "task-owned",
            },
            authority_envelope={
                "goalId": "goal-demo",
                "changeId": "demo",
                "planDigest": "reviewed-plan-v1",
                "writeSet": [],
                "allowedActions": ["edit_authority_policy"],
                "allowedEffects": ["local.write"],
                "allowedTargets": ["dev-flow-source"],
                "allowedOwnerships": ["task-owned"],
                "allowedRisks": ["local_reversible"],
            },
            evidence={
                "trusted": True,
                "current": True,
                "complete": True,
                "identityCurrent": True,
            },
        )
        repo, _ = self.make_repo()

        recorded = record_authority_gate(
            repo,
            resolution,
            next_question="May this slice write to other-project?",
        )

        self.assertEqual(recorded["status"], "recorded")
        self.assertEqual(recorded["missingAuthority"], resolution["missingAuthority"])
        self.assertEqual(recorded["reasonCodes"], resolution["reasonCodes"])
        self.assertEqual(recorded["invalidations"], resolution["invalidations"])

    def test_clear_requires_current_continue_resolution_and_clears_both_markers(self):
        from workflow_authority_gate import clear_authority_gate, record_authority_gate
        from workflow_state import parse_state

        repo, _ = self.make_repo()
        recorded = record_authority_gate(
            repo,
            self.resolution(),
            next_question="May the public demo-output contract be added?",
        )
        cleared = clear_authority_gate(
            repo,
            gate_key=recorded["gateKey"],
            resolution=self.promotion_proof(repo, recorded),
            resume_stage="executing",
        )
        state = parse_state(repo)

        self.assertEqual(cleared["status"], "cleared")
        self.assertEqual(state["current_stage"], "executing")
        self.assertEqual(state["current_change"]["status"], "executing")
        self.assertEqual(state["authority_gate"]["status"], "resolved")
        self.assertEqual(state["authority_gate"]["missing_authority"], [])
        self.assertEqual(
            cleared["authorityArtifactPath"],
            "openspec/changes/demo/evidence/authority-grant.json",
        )
        for field in (
            "authorityArtifactSha256",
            "authorityContractSha256",
            "evidenceSha256",
            "requestSha256",
        ):
            self.assertRegex(str(cleared[field]), r"^sha256:[0-9a-f]{64}$")
        self.assertNotEqual(
            cleared["authorityContractSha256"],
            self.resolution()["authorityContractSha256"],
        )
        self.assertEqual(
            state["authority_gate"]["resolution_digest"],
            cleared["requestSha256"],
        )
        self.assertEqual(
            state["authority_gate"]["evidence_digest"],
            cleared["evidenceSha256"],
        )

    def test_clear_rejects_tampered_active_receipt_without_changing_state(self):
        from workflow_authority_gate import (
            AuthorityGateError,
            clear_authority_gate,
            record_authority_gate,
        )

        repo, state_path = self.make_repo()
        recorded = record_authority_gate(
            repo,
            self.resolution(),
            next_question="May the public demo-output contract be added?",
        )
        proof = self.promotion_proof(repo, recorded)
        receipt_path = repo / recorded["receiptPath"]
        receipt = json.loads(receipt_path.read_text())
        receipt["evidenceSha256"] = "sha256:" + "e" * 64
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        before = state_path.read_bytes()

        with self.assertRaises(AuthorityGateError):
            clear_authority_gate(
                repo,
                gate_key=recorded["gateKey"],
                resolution=proof,
                resume_stage="executing",
            )

        self.assertEqual(state_path.read_bytes(), before)

    def test_clear_rejects_duplicate_receipt_keys_without_changing_state(self):
        from workflow_authority_gate import (
            AuthorityGateError,
            clear_authority_gate,
            record_authority_gate,
        )

        repo, state_path = self.make_repo()
        recorded = record_authority_gate(
            repo,
            self.resolution(),
            next_question="May the public demo-output contract be added?",
        )
        proof = self.promotion_proof(repo, recorded)
        receipt_path = repo / recorded["receiptPath"]
        receipt_path.write_text(
            receipt_path.read_text().replace(
                '  "decision": "AWAIT_HUMAN",\n',
                '  "decision": "AWAIT_HUMAN",\n  "decision": "AWAIT_HUMAN",\n',
                1,
            )
        )
        before = state_path.read_bytes()

        with self.assertRaises(AuthorityGateError):
            clear_authority_gate(
                repo,
                gate_key=recorded["gateKey"],
                resolution=proof,
                resume_stage="executing",
            )

        self.assertEqual(state_path.read_bytes(), before)

    def test_clear_requires_bound_current_authority_promotion_proof(self):
        from workflow_authority_gate import (
            AuthorityGateError,
            clear_authority_gate,
            record_authority_gate,
        )

        mutations = {
            "arbitrary-continue": self.resolution(decision="CONTINUE", missing=[]),
            "untrusted": {"trusted": False},
            "stale": {"current": False},
            "stale-evidence": {"evidenceCurrent": False},
            "wrong-gate": {"gateKey": "sha256:" + "9" * 64},
            "missing-authority-drift": {"priorMissingAuthority": ["other:authority"]},
            "promotion-drift": {"promotedAuthority": ["other:authority"]},
            "prior-authority-drift": {
                "priorAuthorityContractSha256": "sha256:" + "8" * 64
            },
            "unchanged-authority": {"authorityContractSha256": "sha256:" + "a" * 64},
            "fabricated-authority-digest": {
                "authorityContractSha256": "sha256:" + "d" * 64
            },
            "fabricated-evidence-digest": {"evidenceSha256": "sha256:" + "e" * 64},
            "fabricated-request-digest": {"requestSha256": "sha256:" + "f" * 64},
            "prior-evidence-drift": {"priorEvidenceSha256": "sha256:" + "7" * 64},
            "goal-drift": {"goalId": "other-goal"},
            "change-drift": {"changeId": "other-change"},
            "stage-drift": {"resumeStage": "verifying"},
        }

        for name, mutation in mutations.items():
            with self.subTest(name=name):
                repo, state_path = self.make_repo()
                recorded = record_authority_gate(
                    repo,
                    self.resolution(),
                    next_question="May the public demo-output contract be added?",
                )
                proof = (
                    mutation
                    if name == "arbitrary-continue"
                    else self.promotion_proof(repo, recorded, **mutation)
                )
                before = state_path.read_bytes()

                with self.assertRaises(AuthorityGateError):
                    clear_authority_gate(
                        repo,
                        gate_key=recorded["gateKey"],
                        resolution=proof,
                        resume_stage="executing",
                    )

                self.assertEqual(state_path.read_bytes(), before)

    def test_clear_rejects_non_executable_or_unallowlisted_resume_stage(self):
        from workflow_authority_gate import (
            AuthorityGateError,
            clear_authority_gate,
            record_authority_gate,
        )

        for stage in ("awaiting_human", "complete", "arbitrary-stage"):
            with self.subTest(stage=stage):
                repo, state_path = self.make_repo()
                recorded = record_authority_gate(
                    repo,
                    self.resolution(),
                    next_question="May the public demo-output contract be added?",
                )
                before = state_path.read_bytes()

                with self.assertRaises(AuthorityGateError):
                    clear_authority_gate(
                        repo,
                        gate_key=recorded["gateKey"],
                        resolution=self.promotion_proof(
                            repo,
                            recorded,
                            resume_stage=stage,
                        ),
                        resume_stage=stage,
                    )

                self.assertEqual(state_path.read_bytes(), before)

    def test_validator_rejects_mismatched_markers_and_missing_gate_receipt(self):
        from workflow_validate import validate_workflow_state

        repo, state_path = self.make_repo()
        state_path.write_text(
            state_path.read_text()
            .replace("current_stage: executing", "current_stage: awaiting_human")
            .replace("  status: executing", "  status: awaiting_human")
        )
        report = validate_workflow_state(repo)
        self.assertFalse(report["ok"])
        self.assertTrue(any("authority gate" in issue.lower() for issue in report["issues"]))

        state_path.write_text(
            state_path.read_text().replace(
                "  status: awaiting_human", "  status: executing", 1
            )
        )
        mismatch = validate_workflow_state(repo)
        self.assertFalse(mismatch["ok"])
        self.assertTrue(any("markers" in issue.lower() for issue in mismatch["issues"]))


if __name__ == "__main__":
    unittest.main()
