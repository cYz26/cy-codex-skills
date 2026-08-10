import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import devflow_stop_hook
from devflow_stop_hook import continuation_stop_check
from workflow_compact_policy import resolve_continuation_required
from workflow_continuation import (
    AWAIT_HUMAN,
    CHECKPOINT_AND_CONTINUE,
    COMPLETE,
    CONTINUE_NEXT_ITEM,
    FAIL_CLOSED_REPAIR,
    READY_FOR_EXTERNAL_EFFECT,
    VERIFY_ACTIVE_CHANGE,
    decide_continuation,
    continuation_decision,
    execution_source,
    is_explicit_human_gate,
)


class ContinuousExecutionContractTests(unittest.TestCase):
    def make_repo(self, change_id="demo-change", verification_passed=False):
        repo = Path(tempfile.mkdtemp(prefix="devflow-continuation-"))
        (repo / ".planning" / "devflow").mkdir(parents=True)
        (repo / "openspec" / "changes" / change_id).mkdir(parents=True)
        (repo / ".planning" / "devflow" / "STATE.md").write_text(
            f"""---
workflow_version: 0.3.0
project_mode: brownfield
current_stage: executing
current_change:
  id: {change_id}
  status: executing
goal_gate:
  id: goal-{change_id}
  required: true
  status: satisfied
gates:
  verification_passed: {str(verification_passed).lower()}
context_management:
  compact_recommended: false
  compact_status: not_needed
---
# Workflow State

## Current Status

Executing approved work.

## Next Action

Continue the active task.
"""
        )
        return repo

    def bind_current_standing_contract(self, repo):
        project_target = repo / "source-project"
        project_target.mkdir()
        asset_expectation = (
            "openspec/changes/demo-change/evidence/release-assets.json"
        )
        contract = {
            "schemaVersion": "1.0",
            "contractId": "demo-standing-v1",
            "goalId": "goal-demo-change",
            "goal": "Complete the demo standing milestone.",
            "change": "demo-change",
            "milestone": "demo-standing-v1",
            "plugin": {
                "id": "dev-flow",
                "marketplace": "cy-codex-skills",
                "versionRule": "checked-in",
                "version": "0.4.0",
            },
            "repository": {
                "remote": "origin",
                "remoteUrl": "git@example.invalid:dev-flow.git",
                "ref": "refs/heads/main",
                "expectedBase": "a" * 40,
            },
            "commit": {"message": "feat(dev-flow): demo standing milestone"},
            "publication": {
                "tag": "dev-flow-v0.4.0",
                "channel": "stable",
                "mechanism": "github_actions",
                "workflow": ".github/workflows/publish-dev-flow.yml",
                "assetExpectation": asset_expectation,
                "assets": ["dev-flow-0.4.0.zip"],
            },
            "requestedEffects": [
                "git.commit",
                "git.push",
                "git.tag.push",
                "github.release",
                "devflow.source.fast_forward",
                "codex.cache.refresh",
                "devflow.project.refresh",
            ],
            "writeSet": [
                "dev/plugins/dev-flow/.codex-plugin/plugin.json",
                asset_expectation,
            ],
            "refreshTargets": {
                "cache": "dev-flow@cy-codex-skills",
                "project": str(project_target),
            },
            "failurePolicy": {
                "preserveCommit": True,
                "preserveTag": True,
                "maxDiagnoses": 1,
                "maxRemediations": 1,
                "allowAlternatePublication": False,
            },
            "reentryPolicy": {
                "sameIdentityOnly": True,
                "resume": "first_incomplete_step",
                "duplicateEffects": False,
            },
            "exclusions": [
                "archive",
                "force-push",
                "game-dev-plugins",
                "merge",
                "pr",
                "rebase",
                "unnamed-consumer",
                "unnamed-plugin",
                "unrelated-release",
            ],
        }
        relative = "openspec/changes/demo-change/evidence/standing-contract.json"
        payload = json.dumps(contract, sort_keys=True, separators=(",", ":"))
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload)
        digest = hashlib.sha256(payload.encode()).hexdigest()
        state_path = repo / ".planning" / "devflow" / "STATE.md"
        state_path.write_text(
            state_path.read_text().replace(
                "gates:\n",
                "standing_milestone:\n"
                "  status: current\n"
                f"  contract_path: {relative}\n"
                f"  contract_sha256: {digest}\n"
                "  goal_id: goal-demo-change\n"
                "  change_id: demo-change\n"
                f"  candidate_digest: {'b' * 64}\n"
                f"  validation_digest: {'c' * 64}\n"
                f"  review_digest: {'d' * 64}\n"
                "gates:\n",
                1,
            )
        )
        return contract

    def record_human_gate(self, repo):
        from workflow_authority_gate import (
            canonical_authority_gate_key,
            record_authority_gate,
        )

        authority_digest = "sha256:" + "a" * 64
        evidence_digest = "sha256:" + "b" * 64
        request_digest = "sha256:" + "c" * 64
        missing = ["public_contract_choice"]
        gate_key = canonical_authority_gate_key(
            missing_authority=missing,
            authority_contract_sha256=authority_digest,
            evidence_sha256=evidence_digest,
            request_sha256=request_digest,
        )
        return record_authority_gate(
            repo,
            {
                "decision": "AWAIT_HUMAN",
                "reasonCodes": ["public_contract_authority_missing"],
                "missingAuthority": missing,
                "invalidations": [],
                "materialDelta": True,
                "authorityContractSha256": authority_digest,
                "evidenceSha256": evidence_digest,
                "requestSha256": request_digest,
                "gateKey": gate_key,
            },
            next_question="Choose the public compatibility behavior.",
        )

    def test_pure_decision_exposes_technical_repair_without_fabricating_a_human_gate(self):
        cases = [
            (
                AWAIT_HUMAN,
                dict(
                    source_valid=True,
                    work_remaining=True,
                    checkpoint_recommended=True,
                    verification_passed=False,
                    human_gate=True,
                    external_effect_ready=False,
                    human_gate_resolution={
                        "decision": "AWAIT_HUMAN",
                        "reasonCodes": ["public_contract_authority_missing"],
                        "missingAuthority": ["public_contract_choice"],
                        "invalidations": [],
                        "materialDelta": True,
                        "authorityContractSha256": "sha256:" + "a" * 64,
                        "evidenceSha256": "sha256:" + "b" * 64,
                        "requestSha256": "sha256:" + "c" * 64,
                        "gateKey": "sha256:f09b933872881622a275f5b1475d5068b7a1d77933f94ca5960fe2a4cd3f234f",
                    },
                ),
            ),
            (
                FAIL_CLOSED_REPAIR,
                dict(
                    source_valid=False,
                    work_remaining=True,
                    checkpoint_recommended=False,
                    verification_passed=False,
                    human_gate=False,
                    external_effect_ready=False,
                ),
            ),
            (
                CHECKPOINT_AND_CONTINUE,
                dict(
                    source_valid=True,
                    work_remaining=True,
                    checkpoint_recommended=True,
                    verification_passed=False,
                    human_gate=False,
                    external_effect_ready=False,
                ),
            ),
            (
                CONTINUE_NEXT_ITEM,
                dict(
                    source_valid=True,
                    work_remaining=True,
                    checkpoint_recommended=False,
                    verification_passed=False,
                    human_gate=False,
                    external_effect_ready=False,
                ),
            ),
            (
                VERIFY_ACTIVE_CHANGE,
                dict(
                    source_valid=True,
                    work_remaining=False,
                    checkpoint_recommended=False,
                    verification_passed=False,
                    human_gate=False,
                    external_effect_ready=False,
                ),
            ),
            (
                READY_FOR_EXTERNAL_EFFECT,
                dict(
                    source_valid=True,
                    work_remaining=False,
                    checkpoint_recommended=False,
                    verification_passed=True,
                    human_gate=False,
                    external_effect_ready=True,
                ),
            ),
            (
                COMPLETE,
                dict(
                    source_valid=True,
                    work_remaining=False,
                    checkpoint_recommended=False,
                    verification_passed=True,
                    human_gate=False,
                    external_effect_ready=False,
                ),
            ),
        ]

        observed = set()
        for expected, signals in cases:
            with self.subTest(expected=expected):
                decision = decide_continuation(**signals)
                self.assertEqual(decision["action"], expected)
                observed.add(decision["action"])

        self.assertEqual(
            observed,
            {
                AWAIT_HUMAN,
                CHECKPOINT_AND_CONTINUE,
                COMPLETE,
                CONTINUE_NEXT_ITEM,
                FAIL_CLOSED_REPAIR,
                READY_FOR_EXTERNAL_EFFECT,
                VERIFY_ACTIVE_CHANGE,
            },
        )

    def test_malformed_human_gate_resolution_is_a_technical_repair(self):
        common = {
            "source_valid": True,
            "work_remaining": False,
            "checkpoint_recommended": False,
            "verification_passed": True,
            "external_effect_ready": True,
        }
        malformed_external = decide_continuation(
            **common,
            human_gate=False,
            external_effect_resolution={
                "decision": "AWAIT_HUMAN",
                "reasonCodes": [],
                "missingAuthority": [],
                "materialDelta": False,
                "gateKey": None,
            },
        )
        malformed_recorded = decide_continuation(
            **{**common, "external_effect_ready": False},
            human_gate=True,
            human_gate_resolution=None,
        )
        unbound_external = decide_continuation(
            **common,
            human_gate=False,
            external_effect_resolution={
                "decision": "AWAIT_HUMAN",
                "reasonCodes": ["target_authority_missing"],
                "missingAuthority": ["target:origin:refs/heads/other"],
                "materialDelta": True,
                "gateKey": "sha256:" + "a" * 64,
            },
        )

        self.assertEqual(malformed_external["action"], FAIL_CLOSED_REPAIR)
        self.assertEqual(malformed_recorded["action"], FAIL_CLOSED_REPAIR)
        self.assertEqual(unbound_external["action"], FAIL_CLOSED_REPAIR)

    def test_external_gate_binding_never_synthesizes_missing_resolver_digests(self):
        from workflow_continuation import bind_external_authority_resolution

        canonical = {
            "decision": "AWAIT_HUMAN",
            "reasonCodes": ["target_outside_authority_envelope"],
            "missingAuthority": ["target:origin:refs/heads/other"],
            "invalidations": [],
            "materialDelta": True,
            "authorityDigest": "a" * 64,
            "evidenceDigest": "b" * 64,
            "requestDigest": "c" * 64,
        }
        cases: tuple[tuple[str, ...], ...] = (
            ("authorityDigest",),
            ("evidenceDigest",),
            ("requestDigest",),
            ("authorityDigest", "evidenceDigest", "requestDigest"),
        )

        for omitted in cases:
            with self.subTest(omitted=omitted):
                candidate = {
                    key: value for key, value in canonical.items() if key not in omitted
                }
                bound = bind_external_authority_resolution(
                    {},
                    candidate,
                    requested_effect="git.push",
                    requested_target="origin:refs/heads/other",
                    release_status="authorization_required",
                )
                routed = decide_continuation(
                    source_valid=True,
                    work_remaining=False,
                    checkpoint_recommended=False,
                    verification_passed=True,
                    human_gate=False,
                    external_effect_ready=True,
                    external_effect_resolution=bound,
                )

                self.assertNotIn("gateKey", bound)
                self.assertEqual(routed["action"], FAIL_CLOSED_REPAIR)

        bound = bind_external_authority_resolution(
            {},
            canonical,
            requested_effect="git.push",
            requested_target="origin:refs/heads/other",
            release_status="authorization_required",
        )
        routed = decide_continuation(
            source_valid=True,
            work_remaining=False,
            checkpoint_recommended=False,
            verification_passed=True,
            human_gate=False,
            external_effect_ready=True,
            external_effect_resolution=bound,
        )

        self.assertRegex(str(bound.get("gateKey")), r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(routed["action"], AWAIT_HUMAN)

    def test_active_openspec_tasks_take_precedence_over_complete_fallback_ledger(self):
        repo = self.make_repo()
        (repo / "openspec" / "changes" / "demo-change" / "tasks.md").write_text(
            "## Work\n\n- [x] 1.1 First item\n- [ ] 1.2 Second item\n"
        )
        (repo / "TASK_LEDGER.md").write_text(
            "| Task | Status |\n| --- | --- |\n| Legacy | done |\n"
        )

        source = execution_source(repo)

        self.assertEqual(source["kind"], "openspec")
        self.assertEqual(source["path"], "openspec/changes/demo-change/tasks.md")
        self.assertTrue(source["valid"])
        self.assertEqual(source["total"], 2)
        self.assertEqual(source["incomplete"], 1)

    def test_fallback_ledger_retains_strict_status_contract(self):
        repo = self.make_repo(change_id="none")
        (repo / "TASK_LEDGER.md").write_text(
            "| Task | Review Gate | Status |\n"
            "| --- | --- | --- |\n"
            "| First | schema \\| contract | done |\n"
            "| Second | none | in_progress |\n"
        )

        source = execution_source(repo)

        self.assertEqual(source["kind"], "task_ledger")
        self.assertTrue(source["valid"])
        self.assertEqual(source["total"], 2)
        self.assertEqual(source["incomplete"], 1)

    def test_openspec_parser_ignores_fenced_examples_and_fails_closed_on_malformed_tasks(self):
        repo = self.make_repo()
        tasks = repo / "openspec" / "changes" / "demo-change" / "tasks.md"
        tasks.write_text(
            "## Work\n\n```markdown\n- [ ] example only\n```\n\n- [x] 1.1 Real item\n"
        )

        source = execution_source(repo)

        self.assertTrue(source["valid"])
        self.assertEqual(source["total"], 1)
        self.assertEqual(source["incomplete"], 0)

        tasks.write_text("## Work\n\n- [?] ambiguous item\n")
        malformed = execution_source(repo)

        self.assertFalse(malformed["valid"])
        self.assertTrue(any("malformed" in issue for issue in malformed["issues"]))
        self.assertEqual(
            decide_continuation(
                source_valid=malformed["valid"],
                work_remaining=True,
                checkpoint_recommended=False,
                verification_passed=False,
                human_gate=False,
                external_effect_ready=False,
            )["action"],
            FAIL_CLOSED_REPAIR,
        )

    def test_unsafe_active_change_id_fails_closed_without_path_escape(self):
        repo = self.make_repo()
        state = repo / ".planning" / "devflow" / "STATE.md"
        state.write_text(state.read_text().replace("id: demo-change", "id: ../../outside"))

        source = execution_source(repo)

        self.assertFalse(source["valid"])
        self.assertEqual(source["kind"], "openspec")
        self.assertTrue(any("change id" in issue for issue in source["issues"]))

    def test_human_gate_requires_both_markers_and_concrete_gate_receipt(self):
        from workflow_state import parse_state

        repo = self.make_repo()
        self.record_human_gate(repo)
        self.assertTrue(
            is_explicit_human_gate(
                parse_state(repo),
                repo,
            )
        )
        self.assertFalse(
            is_explicit_human_gate(
                {
                    "current_stage": "review",
                    "current_change": {"status": "awaiting_human"},
                }
            )
        )

    def test_marker_only_awaiting_state_is_a_technical_repair_stop(self):
        repo = self.make_repo()
        tasks = repo / "openspec" / "changes" / "demo-change" / "tasks.md"
        tasks.write_text("## Work\n\n- [ ] 1.1 Waiting decision\n")
        state = repo / ".planning" / "devflow" / "STATE.md"
        state.write_text(
            state.read_text()
            .replace("current_stage: executing", "current_stage: awaiting_human")
            .replace("status: executing", "status: awaiting_human")
            .replace(
                "gates:\n",
                "authority_gate:\n"
                "  key: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
                "  status: active\n"
                "  resolution_digest: sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc\n"
                "  evidence_digest: sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\n"
                "  missing_authority:\n"
                "    - public_contract_choice\n"
                "gates:\n",
            )
        )

        check = continuation_stop_check(repo)

        self.assertTrue(check["ok"])
        self.assertEqual(check["action"], FAIL_CLOSED_REPAIR)
        self.assertIn("receipt", check["detail"].lower())

    def test_tampered_receipt_or_state_digest_is_a_technical_repair_stop(self):
        cases = ("receipt", "state", "duplicate-key")
        for kind in cases:
            with self.subTest(kind=kind):
                repo = self.make_repo()
                tasks = repo / "openspec" / "changes" / "demo-change" / "tasks.md"
                tasks.write_text("## Work\n\n- [ ] 1.1 Waiting decision\n")
                recorded = self.record_human_gate(repo)
                state_path = repo / ".planning" / "devflow" / "STATE.md"
                receipt_path = repo / recorded["receiptPath"]
                if kind == "receipt":
                    import json

                    receipt = json.loads(receipt_path.read_text())
                    receipt["evidenceSha256"] = "sha256:" + "e" * 64
                    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
                elif kind == "state":
                    state_path.write_text(
                        state_path.read_text().replace(
                            "evidence_digest: sha256:" + "b" * 64,
                            "evidence_digest: sha256:" + "e" * 64,
                        )
                    )
                else:
                    receipt_path.write_text(
                        receipt_path.read_text().replace(
                            '  "decision": "AWAIT_HUMAN",\n',
                            '  "decision": "AWAIT_HUMAN",\n  "decision": "AWAIT_HUMAN",\n',
                            1,
                        )
                    )
                tracked = (tasks, state_path, receipt_path)
                before = {path: path.read_bytes() for path in tracked}

                check = continuation_stop_check(repo)

                self.assertTrue(check["ok"])
                self.assertEqual(check["action"], FAIL_CLOSED_REPAIR)
                self.assertNotIn("missingAuthority", check)
                self.assertNotIn("gateKey", check)
                self.assertEqual(before, {path: path.read_bytes() for path in tracked})

    def test_invalid_execution_source_precedes_an_otherwise_valid_human_gate(self):
        repo = self.make_repo()
        tasks = repo / "openspec" / "changes" / "demo-change" / "tasks.md"
        tasks.write_text("## Work\n\n- [?] malformed\n")
        self.record_human_gate(repo)

        check = continuation_stop_check(repo)

        self.assertTrue(check["ok"])
        self.assertEqual(check["action"], FAIL_CLOSED_REPAIR)
        self.assertIn("execution source", check["detail"].lower())
        self.assertNotIn("missingAuthority", check)
        self.assertFalse(
            is_explicit_human_gate(
                {
                    "current_stage": "awaiting_human",
                    "current_change": {"status": "awaiting_human"},
                }
            )
        )

    def test_current_standing_milestone_keeps_external_effect_action_automatic(self):
        result = decide_continuation(
            source_valid=True,
            work_remaining=False,
            checkpoint_recommended=False,
            verification_passed=True,
            human_gate=False,
            external_effect_ready=True,
            external_effect_resolution={
                "decision": "CONTINUE",
                "missingAuthority": [],
                "materialDelta": False,
            },
        )

        self.assertEqual(result["action"], READY_FOR_EXTERNAL_EFFECT)
        self.assertTrue(result["continuationRequired"])
        self.assertFalse(result["stopAllowed"])
        self.assertNotIn("request", result["nextAction"].lower())

    def test_declared_and_current_standing_grants_select_the_correct_next_effect(self):
        for status, effect, target in (
            ("declared", "release.promote_local", "plugins/dev-flow"),
            ("current", "git.commit", None),
        ):
            with self.subTest(status=status):
                repo = self.make_repo(verification_passed=True)
                tasks = repo / "openspec" / "changes" / "demo-change" / "tasks.md"
                tasks.write_text("## Work\n\n- [x] 1.1 Complete\n")
                state_path = repo / ".planning" / "devflow" / "STATE.md"
                state_path.write_text(
                    state_path.read_text().replace(
                        "gates:\n",
                        f"standing_milestone:\n  status: {status}\ngates:\n",
                    )
                )
                with mock.patch(
                    "workflow_standing_milestone.resolve_standing_milestone",
                    return_value={
                        "decision": "CONTINUE",
                        "missingAuthority": [],
                        "materialDelta": False,
                        "reasonCodes": ["standing_milestone_authority_current"],
                    },
                ) as resolver:
                    check = continuation_stop_check(repo, release_status="pending")

                self.assertEqual(check["action"], READY_FOR_EXTERNAL_EFFECT)
                resolver.assert_called_once_with(
                    repo.resolve(),
                    mock.ANY,
                    requested_effect=effect,
                    requested_target=target,
                )

    def test_real_current_standing_contract_derives_commit_target_for_continuation(self):
        repo = self.make_repo(verification_passed=True)
        tasks = repo / "openspec" / "changes" / "demo-change" / "tasks.md"
        tasks.write_text("## Work\n\n- [x] 1.1 Complete\n")
        self.bind_current_standing_contract(repo)

        check = continuation_decision(repo, release_status="pending")

        self.assertEqual(check["action"], READY_FOR_EXTERNAL_EFFECT, check)
        standing = check["standingMilestoneResolution"]
        self.assertEqual(standing["decision"], "CONTINUE")
        self.assertEqual(standing["requestedEffect"], "git.commit")
        self.assertEqual(standing["requestedTarget"], "")
        self.assertEqual(standing["resolvedTarget"], "origin:refs/heads/main")
        self.assertEqual(standing["missingAuthority"], [])

    def test_inactive_standing_milestone_preserves_concrete_missing_authority(self):
        from workflow_authority_gate import canonical_authority_gate_key

        repo = self.make_repo(verification_passed=True)
        tasks = repo / "openspec" / "changes" / "demo-change" / "tasks.md"
        tasks.write_text("## Work\n\n- [x] 1.1 Complete\n")
        tracked = [tasks, repo / ".planning" / "devflow" / "STATE.md"]
        before = {path: path.read_bytes() for path in tracked}

        check = continuation_stop_check(repo, release_status="pending")

        self.assertTrue(check["ok"])
        self.assertEqual(check["action"], AWAIT_HUMAN)
        self.assertEqual(
            check["missingAuthority"],
            ["standing_milestone.contract"],
        )
        self.assertIn("STANDING_AUTHORITY_MISSING", check["reasonCodes"])
        self.assertNotIn("separately authorized", check["detail"].lower())
        resolution = check["authorityResolution"]
        for field in (
            "authorityContractSha256",
            "evidenceSha256",
            "requestSha256",
        ):
            self.assertRegex(str(resolution[field]), r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(
            check["gateKey"],
            canonical_authority_gate_key(
                missing_authority=check["missingAuthority"],
                authority_contract_sha256=resolution["authorityContractSha256"],
                evidence_sha256=resolution["evidenceSha256"],
                request_sha256=resolution["requestSha256"],
            ),
        )
        self.assertEqual(before, {path: path.read_bytes() for path in tracked})

    def test_stop_check_blocks_between_items_and_routes_closed_tasks_to_verification(self):
        repo = self.make_repo()
        tasks = repo / "openspec" / "changes" / "demo-change" / "tasks.md"
        tasks.write_text("## Work\n\n- [x] 1.1 First\n- [ ] 1.2 Second\n")

        between = continuation_stop_check(repo)

        self.assertFalse(between["ok"])
        self.assertEqual(between["action"], CONTINUE_NEXT_ITEM)
        self.assertEqual(between["executionSource"]["kind"], "openspec")

        tasks.write_text("## Work\n\n- [x] 1.1 First\n- [x] 1.2 Second\n")
        verification = continuation_stop_check(repo)

        self.assertFalse(verification["ok"])
        self.assertEqual(verification["action"], VERIFY_ACTIVE_CHANGE)

    def test_stop_check_allows_explicit_human_gate_and_is_read_only(self):
        repo = self.make_repo()
        tasks = repo / "openspec" / "changes" / "demo-change" / "tasks.md"
        tasks.write_text("## Work\n\n- [ ] 1.1 Waiting decision\n")
        state = repo / ".planning" / "devflow" / "STATE.md"
        receipt = self.record_human_gate(repo)
        receipt_path = repo / receipt["receiptPath"]
        before = {path: path.read_bytes() for path in (tasks, state, receipt_path)}

        check = continuation_stop_check(repo)

        self.assertTrue(check["ok"])
        self.assertEqual(check["action"], AWAIT_HUMAN)
        self.assertEqual(check["missingAuthority"], ["public_contract_choice"])
        self.assertEqual(check["reasonCodes"], ["public_contract_authority_missing"])
        self.assertEqual(check["gateKey"], receipt["gateKey"])
        self.assertEqual(
            before,
            {path: path.read_bytes() for path in (tasks, state, receipt_path)},
        )

    def test_aggregate_stop_hook_uses_continuation_as_the_primary_mid_work_gate(self):
        repo = self.make_repo()
        tasks = repo / "openspec" / "changes" / "demo-change" / "tasks.md"
        tasks.write_text("## Work\n\n- [x] 1.1 First\n- [ ] 1.2 Second\n")

        with mock.patch.object(
            devflow_stop_hook,
            "context_health_check",
            return_value={"risk": "low", "decision": "continue"},
        ), mock.patch.object(
            devflow_stop_hook,
            "release_promotion_run_gate",
            return_value={"status": "not_applicable", "message": "not applicable"},
        ):
            report = devflow_stop_hook.run_stop_checks(repo)

        self.assertFalse(report["ok"])
        self.assertEqual(report["failedChecks"], ["execution_continuation"])
        continuation = next(item for item in report["checks"] if item["id"] == "execution_continuation")
        self.assertEqual(continuation["action"], CONTINUE_NEXT_ITEM)
        verification = next(item for item in report["checks"] if item["id"] == "verification")
        self.assertEqual(verification["status"], "not_applicable")

    def test_aggregate_stop_hook_allows_real_human_and_external_effect_boundaries(self):
        human_repo = self.make_repo()
        human_tasks = human_repo / "openspec" / "changes" / "demo-change" / "tasks.md"
        human_tasks.write_text("## Work\n\n- [ ] 1.1 Waiting decision\n")
        self.record_human_gate(human_repo)

        verified_repo = self.make_repo(verification_passed=True)
        verified_tasks = verified_repo / "openspec" / "changes" / "demo-change" / "tasks.md"
        verified_tasks.write_text("## Work\n\n- [x] 1.1 Complete\n")

        for repo, release_status, expected in (
            (human_repo, "not_applicable", AWAIT_HUMAN),
            (verified_repo, "pending", AWAIT_HUMAN),
        ):
            with self.subTest(expected=expected), mock.patch.object(
                devflow_stop_hook,
                "context_health_check",
                return_value={"risk": "low", "decision": "continue"},
            ), mock.patch.object(
                devflow_stop_hook,
                "release_promotion_run_gate",
                return_value={"status": release_status, "message": release_status},
            ) as gate:
                report = devflow_stop_hook.run_stop_checks(repo)

            self.assertTrue(report["ok"], report)
            continuation = next(
                item for item in report["checks"] if item["id"] == "execution_continuation"
            )
            self.assertEqual(continuation["action"], expected)
            gate.assert_called_once_with(repo.resolve(), apply=False)

    def test_public_guidance_defines_the_enclosing_loop_and_real_human_gates(self):
        root = PLUGIN_ROOT.parents[2]
        surfaces = {
            "project-orchestrator": (
                PLUGIN_ROOT / "skills" / "project-orchestrator" / "SKILL.md",
                ["auto-until-terminal", "execute -> evidence -> decide -> continue", "phase label"],
            ),
            "execute-task": (
                PLUGIN_ROOT / "skills" / "execute-task" / "SKILL.md",
                ["completion receipt", "Return to `project-orchestrator`", "does not end the user request"],
            ),
            "checkpoint-compact": (
                PLUGIN_ROOT / "skills" / "checkpoint-compact" / "SKILL.md",
                ["phase label", "CHECKPOINT_AND_CONTINUE"],
            ),
            "verify-and-archive": (
                PLUGIN_ROOT / "skills" / "verify-and-archive" / "SKILL.md",
                ["active-change verification is not overall completion", "READY_FOR_EXTERNAL_EFFECT"],
            ),
            "feature-intake": (
                PLUGIN_ROOT / "skills" / "feature-intake" / "SKILL.md",
                ["execution policy", "auto-until-terminal"],
            ),
            "ai-native-tech-plan": (
                PLUGIN_ROOT / "skills" / "ai-native-tech-plan" / "SKILL.md",
                ["Continuation Policy", "genuine Human Gate"],
            ),
            "root AGENTS": (
                root / "AGENTS.md",
                ["## Continuous Execution", "auto-until-terminal", "A phase label is not a Human Gate"],
            ),
            "generated AGENTS": (
                PLUGIN_ROOT / "assets" / "templates" / "AGENTS.md.template",
                ["## Continuous Execution", "auto-until-terminal", "A phase label is not a Human Gate"],
            ),
            "root policy": (
                root / "ENGINEERING_POLICY.md",
                ["## Continuous Execution", "active Full OpenSpec task list"],
            ),
            "generated policy": (
                PLUGIN_ROOT / "assets" / "templates" / "ENGINEERING_POLICY.md.template",
                ["## Continuous Execution", "active Full OpenSpec task list"],
            ),
            "hook contract": (
                PLUGIN_ROOT / "docs" / "hook-contract.md",
                ["active Full OpenSpec task list", "execution continuation outcome"],
            ),
        }

        for name, (path, phrases) in surfaces.items():
            text = " ".join(path.read_text().split()).lower()
            for phrase in phrases:
                with self.subTest(surface=name, phrase=phrase):
                    self.assertIn(" ".join(phrase.split()).lower(), text)

    def test_public_guidance_separates_standing_model_authority_from_attempt_receipts(self):
        root = PLUGIN_ROOT.parents[2]
        surfaces = (
            root / "AGENTS.md",
            root / "ENGINEERING_POLICY.md",
            PLUGIN_ROOT / "assets" / "templates" / "AGENTS.md.template",
            PLUGIN_ROOT / "assets" / "templates" / "ENGINEERING_POLICY.md.template",
            PLUGIN_ROOT / "skills" / "feature-intake" / "SKILL.md",
            PLUGIN_ROOT / "skills" / "execute-task" / "SKILL.md",
            PLUGIN_ROOT / "skills" / "project-orchestrator" / "SKILL.md",
            PLUGIN_ROOT / "skills" / "ai-native-tech-plan" / "SKILL.md",
        )

        for path in surfaces:
            text = " ".join(path.read_text().split()).lower()
            for phrase in (
                "standing goal execution authority",
                "one-use attempt receipt",
                "record actual monetary cost",
                "defer_and_continue",
            ):
                with self.subTest(path=path, phrase=phrase):
                    self.assertIn(phrase, text)

    def test_review_and_handoff_labels_continue_unless_explicitly_terminal(self):
        for stage in (None, "", "review", "review_or_archive", "handoff", "new_thread"):
            with self.subTest(stage=stage):
                self.assertTrue(resolve_continuation_required(stage))

        self.assertFalse(resolve_continuation_required("review_or_archive", explicit=False))
        self.assertFalse(resolve_continuation_required("completed"))
        self.assertTrue(resolve_continuation_required("completed", explicit=True))


if __name__ == "__main__":
    unittest.main()
