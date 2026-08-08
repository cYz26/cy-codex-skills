import json
import copy
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator, ValidationError


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = PLUGIN_ROOT / "schemas"
FIXTURE_ROOT = PLUGIN_ROOT / "fixtures" / "implementation-readiness"
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from workflow_implementation_readiness import (
    IMPLEMENTATION_PROVIDER_NOT_READY,
    IMPLEMENTATION_PROVIDER_READY,
    IMPLEMENTATION_PROVIDER_REQUIRED,
    active_context_from_repo,
    canonical_digest,
    build_ready_receipt,
    evaluate,
    inspect_readiness,
    inspect_repository_readiness,
    mutation_gate,
    plan_semantic_digest,
    promote_requirement,
    record_provider_override,
    ReadinessError,
    receipt_is_current,
    repository_mutation_gate,
    seal_evidence,
    seal_provider_override,
    seal_receipt,
    seal_requirement,
    write_ready_receipt,
)
from workflow_agent_task_contract import validate_agent_task_contract_file
from workflow_archive_policy import archive_status
from workflow_compact_recovery import handle_compact_recovery_event
from workflow_continuation import (
    AWAIT_HUMAN,
    CHECKPOINT_AND_CONTINUE,
    CONTINUE_NEXT_ITEM,
    continuation_decision,
)
from workflow_release_verification import (
    PROJECT_REFRESH_REVISION3_REQUIRED_INPUTS,
    PROJECT_REFRESH_REVISION4_REQUIRED_INPUTS,
    PROJECT_REFRESH_REVISION5_REQUIRED_INPUTS,
    PROJECT_REFRESH_REVISION6_REQUIRED_INPUTS,
    PROJECT_REFRESH_REVISION7_REQUIRED_INPUTS,
    PROJECT_REFRESH_REVISION8_REQUIRED_INPUTS,
    PROJECT_REFRESH_REVISION9_REQUIRED_INPUTS,
    analyze_project_refresh_impact,
    release_promotion_readiness,
)
from workflow_validate import validate_workflow_state
from workflow_verification import record_verification


class ImplementationReadinessSchemaTests(unittest.TestCase):
    CASES = (
        (
            "implementation-readiness-requirement-v1.schema.json",
            "valid-requirement-v1.json",
            "invalid-requirement-v2.json",
        ),
        (
            "implementation-readiness-evidence-v1.schema.json",
            "valid-evidence-v1.json",
            "invalid-evidence-missing-capabilities-v1.json",
        ),
        (
            "implementation-readiness-receipt-v1.schema.json",
            "valid-receipt-v1.json",
            "invalid-receipt-not-ready-v1.json",
        ),
        (
            "implementation-readiness-provider-override-v1.schema.json",
            "valid-provider-override-v1.json",
            "invalid-provider-override-anonymous-v1.json",
        ),
    )

    def test_v1_schemas_accept_valid_and_reject_invalid_fixtures(self):
        for schema_name, valid_name, invalid_name in self.CASES:
            with self.subTest(schema=schema_name):
                schema = json.loads((SCHEMA_ROOT / schema_name).read_text())
                validator = Draft202012Validator(schema)
                validator.validate(json.loads((FIXTURE_ROOT / valid_name).read_text()))
                with self.assertRaises(ValidationError):
                    validator.validate(json.loads((FIXTURE_ROOT / invalid_name).read_text()))


class ContractFixtures:
    def contract(self):
        requirement = json.loads((FIXTURE_ROOT / "valid-requirement-v1.json").read_text())
        evidence = json.loads((FIXTURE_ROOT / "valid-evidence-v1.json").read_text())
        requirement = seal_requirement(requirement)
        evidence["requirementDigest"] = requirement["semanticInputDigest"]
        evidence = seal_evidence(evidence)
        context = {
            "consumer": copy.deepcopy(requirement["consumer"]),
            "activeChange": copy.deepcopy(requirement["activeChange"]),
            "targetProfile": copy.deepcopy(requirement["targetProfile"]),
            "evaluatedAt": "2026-08-07T08:45:00Z",
        }
        return requirement, evidence, context


class ImplementationReadinessEvaluatorTests(ContractFixtures, unittest.TestCase):

    def test_three_state_matrix_is_fail_closed(self):
        requirement, evidence, context = self.contract()

        missing_requirement = evaluate(None, None, context)
        missing_evidence = evaluate(requirement, None, context)
        ready = evaluate(requirement, evidence, context)

        self.assertEqual(missing_requirement["state"], IMPLEMENTATION_PROVIDER_REQUIRED)
        self.assertEqual(missing_requirement["issueCodes"], ["IMPLEMENTATION_REQUIREMENT_MISSING"])
        self.assertEqual(missing_evidence["state"], IMPLEMENTATION_PROVIDER_REQUIRED)
        self.assertEqual(missing_evidence["issueCodes"], ["IMPLEMENTATION_EVIDENCE_MISSING"])
        self.assertEqual(ready["state"], IMPLEMENTATION_PROVIDER_READY)
        self.assertEqual(ready["issueCodes"], [])
        self.assertEqual(ready["nextAction"], "continue-with-ordinary-implementation-authority")

    def test_unknown_schema_and_exact_binding_mismatches_are_not_ready(self):
        requirement, evidence, context = self.contract()

        unknown = copy.deepcopy(requirement)
        unknown["schemaVersion"] = "2.0"
        report = evaluate(unknown, evidence, context)
        self.assertEqual(report["state"], IMPLEMENTATION_PROVIDER_NOT_READY)
        self.assertEqual(report["issueCodes"], ["REQUIREMENT_SCHEMA_UNSUPPORTED"])

        cases = {
            "provider": ("PROVIDER_IDENTITY_MISMATCH", lambda item: item["provider"].update(id="provider.other")),
            "consumer-revision": (
                "CONSUMER_REVISION_MISMATCH",
                lambda item: item["consumer"].update(revision="git:2222222222222222222222222222222222222222"),
            ),
            "active-change": (
                "ACTIVE_CHANGE_MISMATCH",
                lambda item: item["activeChange"].update(id="other-change"),
            ),
            "semantic-plan": (
                "SEMANTIC_PLAN_MISMATCH",
                lambda item: item["activeChange"].update(
                    semanticPlanDigest="sha256:7777777777777777777777777777777777777777777777777777777777777777"
                ),
            ),
            "target": (
                "TARGET_PROFILE_MISMATCH",
                lambda item: item["targetProfile"].update(
                    digest="sha256:8888888888888888888888888888888888888888888888888888888888888888"
                ),
            ),
            "capability-failed": (
                "CAPABILITY_NOT_PASSED",
                lambda item: item["capabilities"][0].update(status="failed"),
            ),
            "extra-positive-capability": (
                "CAPABILITY_SET_MISMATCH",
                lambda item: item["capabilities"].append(
                    {
                        "id": "extra",
                        "status": "passed",
                        "validator": {"id": "validator.extra", "version": "1.0"},
                        "receipt": {
                            "id": "extra-receipt",
                            "digest": "sha256:9999999999999999999999999999999999999999999999999999999999999999",
                        },
                    }
                ),
            ),
            "missing-limitation": (
                "REQUIRED_LIMITATION_MISSING",
                lambda item: item.update(limitations=[]),
            ),
        }
        for label, (expected_code, mutate) in cases.items():
            with self.subTest(label=label):
                changed = copy.deepcopy(evidence)
                mutate(changed)
                changed = seal_evidence(changed)
                report = evaluate(requirement, changed, context)
                self.assertEqual(report["state"], IMPLEMENTATION_PROVIDER_NOT_READY, report)
                self.assertIn(expected_code, report["issueCodes"], report)
                self.assertIsInstance(report["nextAction"], str)
                self.assertTrue(report["nextAction"])

    def test_unknown_document_claims_and_incomplete_context_fail_closed(self):
        requirement, evidence, context = self.contract()
        extra_requirement = copy.deepcopy(requirement)
        extra_requirement["selectedByDiscovery"] = True
        extra_requirement = seal_requirement(extra_requirement)
        extra_evidence = copy.deepcopy(evidence)
        extra_evidence["platformPassed"] = True
        extra_evidence = seal_evidence(extra_evidence)
        incomplete_context = copy.deepcopy(context)
        incomplete_context["targetProfile"].pop("digest")

        requirement_report = evaluate(extra_requirement, evidence, context)
        evidence_report = evaluate(requirement, extra_evidence, context)
        context_report = evaluate(requirement, evidence, incomplete_context)

        self.assertEqual(requirement_report["issueCodes"], ["REQUIREMENT_INVALID"])
        self.assertEqual(evidence_report["issueCodes"], ["EVIDENCE_INVALID"])
        self.assertEqual(context_report["issueCodes"], ["ACTIVE_CONTEXT_UNAVAILABLE"])

    def test_expired_evidence_is_not_ready(self):
        requirement, evidence, context = self.contract()
        issued = datetime(2026, 8, 7, 6, 0, tzinfo=timezone.utc)
        evidence["binding"] = {
            "immutable": False,
            "issuedAt": issued.isoformat().replace("+00:00", "Z"),
            "validUntil": (issued + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        }
        evidence = seal_evidence(evidence)

        report = evaluate(requirement, evidence, context)

        self.assertEqual(report["state"], IMPLEMENTATION_PROVIDER_NOT_READY)
        self.assertIn("EVIDENCE_STALE", report["issueCodes"])

    def test_digest_is_canonical_and_plan_progress_is_non_semantic(self):
        self.assertEqual(
            canonical_digest({"b": 2, "a": 1}),
            "sha256:43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777",
        )
        pending = {
            "title": "Deliver capability",
            "tasks": [{"id": "1", "summary": "Do exact work", "completed": False}],
            "updatedAt": "2026-08-07T08:00:00Z",
            "evidencePath": ".planning/devflow/verification/one.md",
        }
        complete = copy.deepcopy(pending)
        complete["tasks"][0]["completed"] = True
        complete["updatedAt"] = "2026-08-07T09:00:00Z"
        complete["evidencePath"] = ".planning/devflow/verification/two.md"
        changed = copy.deepcopy(complete)
        changed["tasks"][0]["summary"] = "Do different work"

        self.assertEqual(plan_semantic_digest(pending), plan_semantic_digest(complete))
        self.assertNotEqual(plan_semantic_digest(complete), plan_semantic_digest(changed))

    def test_receipt_and_override_digests_are_content_addressed(self):
        requirement, evidence, context = self.contract()
        report = evaluate(requirement, evidence, context)
        receipt = build_ready_receipt(report, recorded_at="2026-08-07T08:50:00Z")
        override = json.loads((FIXTURE_ROOT / "valid-provider-override-v1.json").read_text())
        override["invalidates"]["requirementDigests"] = [requirement["semanticInputDigest"]]
        override["invalidates"]["receiptDigests"] = [receipt["receiptDigest"]]
        override = seal_provider_override(override)

        changed_receipt = copy.deepcopy(receipt)
        changed_receipt["recordedAt"] = "2026-08-07T09:00:00Z"
        changed_override = copy.deepcopy(override)
        changed_override["reason"] = "The named owner recorded a different decision."
        changed_override = seal_provider_override(changed_override)

        self.assertEqual(receipt["state"], IMPLEMENTATION_PROVIDER_READY)
        self.assertEqual(receipt["receiptDigest"], changed_receipt["receiptDigest"])
        self.assertNotEqual(override["overrideDigest"], changed_override["overrideDigest"])

    def test_schema_invalid_receipt_never_becomes_current(self):
        requirement, evidence, context = self.contract()
        report = evaluate(requirement, evidence, context)
        receipt = build_ready_receipt(report, recorded_at="2026-08-07T08:50:00Z")
        receipt["nextAction"] = "skip-all-ordinary-gates"
        receipt = seal_receipt(receipt)

        self.assertFalse(receipt_is_current(receipt, report))


class ImplementationReadinessRepositoryTests(ContractFixtures, unittest.TestCase):
    def make_repo(
        self,
        *,
        readiness_required: bool = True,
        spec_approved: bool = True,
        plan_written: bool = True,
    ):
        repo = Path(tempfile.mkdtemp(prefix="devflow-readiness-repo-"))
        self.addCleanup(lambda: shutil.rmtree(repo, ignore_errors=True))
        change_id = "deliver-capability-alpha"
        (repo / ".planning" / "devflow").mkdir(parents=True)
        (repo / "openspec" / "changes" / change_id / "specs" / "readiness").mkdir(parents=True)
        (repo / "openspec" / "config.yaml").write_text("schema: spec-driven\n")
        (repo / "openspec" / "changes" / change_id / "proposal.md").write_text(
            "## Why\nDeliver exact work.\n"
        )
        (repo / "openspec" / "changes" / change_id / "design.md").write_text(
            "## Design\nUse one contract.\n"
        )
        (repo / "openspec" / "changes" / change_id / "tasks.md").write_text(
            "- [ ] Implement exact work.\n"
        )
        (repo / "openspec" / "changes" / change_id / "specs" / "readiness" / "spec.md").write_text(
            "## Requirement\nImplementation is project-bound.\n"
        )
        (repo / ".planning" / "devflow" / "STATE.md").write_text(
            f"""---
workflow_version: 0.3.0
project_mode: brownfield
current_stage: executing
current_change:
  id: {change_id}
  status: executing
gates:
  spec_approved: {str(spec_approved).lower()}
  plan_written: {str(plan_written).lower()}
implementation_readiness:
  required: {str(readiness_required).lower()}
---
# State
"""
        )
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "-c", "user.name=DevFlow", "-c", "user.email=devflow@example.com", "commit", "-m", "fixture"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        return repo

    def repository_contract(self, repo: Path):
        requirement = json.loads((FIXTURE_ROOT / "valid-requirement-v1.json").read_text())
        context = active_context_from_repo(
            repo,
            "deliver-capability-alpha",
            project_id="consumer.alpha",
            target_profile=requirement["targetProfile"],
            evaluated_at="2026-08-07T08:45:00Z",
        )
        requirement["consumer"] = copy.deepcopy(context["consumer"])
        requirement["activeChange"] = copy.deepcopy(context["activeChange"])
        requirement = seal_requirement(requirement)
        evidence = json.loads((FIXTURE_ROOT / "valid-evidence-v1.json").read_text())
        evidence["requirementDigest"] = requirement["semanticInputDigest"]
        evidence["consumer"] = copy.deepcopy(context["consumer"])
        evidence["activeChange"] = copy.deepcopy(context["activeChange"])
        evidence["targetProfile"] = copy.deepcopy(context["targetProfile"])
        evidence = seal_evidence(evidence)
        return requirement, evidence, context

    def test_missing_direction_is_not_applicable_and_does_not_select_provider(self):
        repo = self.make_repo(readiness_required=False)
        _, _, context = self.repository_contract(repo)
        before = sorted(path.relative_to(repo).as_posix() for path in repo.rglob("*"))

        inspection = inspect_repository_readiness(repo, "deliver-capability-alpha")
        gate = repository_mutation_gate(
            repo,
            change_id="deliver-capability-alpha",
            ordinary_authority=True,
        )

        self.assertFalse(inspection["applicable"])
        self.assertFalse(gate["applicable"])
        self.assertTrue(gate["allowed"])
        self.assertEqual(
            sorted(path.relative_to(repo).as_posix() for path in repo.rglob("*")),
            before,
        )

    def test_required_state_without_requirement_fails_closed(self):
        repo = self.make_repo(readiness_required=True)

        inspection = inspect_repository_readiness(repo, "deliver-capability-alpha")
        gate = repository_mutation_gate(
            repo,
            change_id="deliver-capability-alpha",
            ordinary_authority=True,
        )

        self.assertTrue(inspection["applicable"])
        self.assertEqual(inspection["report"]["state"], IMPLEMENTATION_PROVIDER_REQUIRED)
        self.assertEqual(
            inspection["report"]["issueCodes"],
            ["IMPLEMENTATION_REQUIREMENT_MISSING"],
        )
        self.assertFalse(gate["allowed"])

    def test_requirement_promotion_requires_approved_active_plan(self):
        repo = self.make_repo(spec_approved=False)
        requirement, _, context = self.repository_contract(repo)

        with self.assertRaises(ReadinessError) as blocked:
            promote_requirement(repo, "deliver-capability-alpha", requirement, context)

        self.assertEqual(blocked.exception.code, "approved_active_plan_required")

    def test_existing_direction_requires_current_project_bound_evidence(self):
        repo = self.make_repo()
        requirement, _, context = self.repository_contract(repo)
        promote_requirement(repo, "deliver-capability-alpha", requirement, context)

        inspection = inspect_readiness(
            repo,
            "deliver-capability-alpha",
            active_context=context,
        )
        gate = mutation_gate(
            repo,
            "deliver-capability-alpha",
            ordinary_authority=True,
            active_context=context,
        )

        self.assertEqual(inspection["report"]["state"], IMPLEMENTATION_PROVIDER_REQUIRED)
        self.assertEqual(inspection["report"]["issueCodes"], ["IMPLEMENTATION_EVIDENCE_MISSING"])
        self.assertFalse(gate["allowed"])

    def test_explicit_promotion_loader_receipt_and_ordinary_authority_compose(self):
        repo = self.make_repo()
        requirement, evidence, context = self.repository_contract(repo)

        absent = inspect_readiness(repo, "deliver-capability-alpha", active_context=context)
        self.assertTrue(absent["applicable"])
        self.assertEqual(absent["report"]["state"], IMPLEMENTATION_PROVIDER_REQUIRED)

        promoted = promote_requirement(repo, "deliver-capability-alpha", requirement, context)
        readiness_root = repo / ".planning" / "devflow" / "implementation-readiness" / "deliver-capability-alpha"
        (readiness_root / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
        before_receipt = inspect_readiness(repo, "deliver-capability-alpha", active_context=context)
        blocked_without_receipt = mutation_gate(
            repo,
            "deliver-capability-alpha",
            ordinary_authority=True,
            active_context=context,
        )

        receipt_result = write_ready_receipt(
            repo,
            "deliver-capability-alpha",
            before_receipt["report"],
            recorded_at="2026-08-07T08:50:00Z",
        )
        first_bytes = Path(receipt_result["path"]).read_bytes()
        repeated = write_ready_receipt(
            repo,
            "deliver-capability-alpha",
            before_receipt["report"],
            recorded_at="2026-08-07T09:00:00Z",
        )
        after_receipt = inspect_readiness(repo, "deliver-capability-alpha", active_context=context)
        allowed = mutation_gate(
            repo,
            "deliver-capability-alpha",
            ordinary_authority=True,
            active_context=context,
        )
        ordinary_block = mutation_gate(
            repo,
            "deliver-capability-alpha",
            ordinary_authority=False,
            active_context=context,
        )

        self.assertEqual(promoted["status"], "created")
        self.assertEqual(before_receipt["report"]["state"], IMPLEMENTATION_PROVIDER_READY)
        self.assertFalse(before_receipt["receiptCurrent"])
        self.assertFalse(blocked_without_receipt["allowed"])
        self.assertIn("READINESS_RECEIPT_MISSING", blocked_without_receipt["issueCodes"])
        self.assertEqual(receipt_result["status"], "created")
        self.assertEqual(repeated["status"], "existing")
        self.assertEqual(Path(repeated["path"]).read_bytes(), first_bytes)
        self.assertTrue(after_receipt["receiptCurrent"])
        self.assertTrue(allowed["allowed"], allowed)
        self.assertFalse(ordinary_block["allowed"])
        self.assertIn("ORDINARY_IMPLEMENTATION_AUTHORITY_REQUIRED", ordinary_block["issueCodes"])

    def test_named_human_override_invalidates_current_requirement_and_receipt(self):
        repo = self.make_repo()
        requirement, evidence, context = self.repository_contract(repo)
        promote_requirement(repo, "deliver-capability-alpha", requirement, context)
        readiness_root = repo / ".planning" / "devflow" / "implementation-readiness" / "deliver-capability-alpha"
        (readiness_root / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
        ready = inspect_readiness(repo, "deliver-capability-alpha", active_context=context)
        receipt = write_ready_receipt(
            repo,
            "deliver-capability-alpha",
            ready["report"],
            recorded_at="2026-08-07T08:50:00Z",
        )
        receipt_document = json.loads(Path(receipt["path"]).read_text())
        override = json.loads((FIXTURE_ROOT / "valid-provider-override-v1.json").read_text())
        override["project"] = {
            "id": requirement["consumer"]["projectId"],
            "rootIdentity": requirement["consumer"]["rootIdentity"],
        }
        override["activeChange"] = copy.deepcopy(requirement["activeChange"])
        override["previousProviderId"] = requirement["provider"]["id"]
        override["invalidates"] = {
            "requirementDigests": [requirement["semanticInputDigest"]],
            "receiptDigests": [receipt_document["receiptDigest"]],
        }
        override = seal_provider_override(override)
        recorded = record_provider_override(
            repo,
            "deliver-capability-alpha",
            override,
            context,
        )

        invalidated = inspect_readiness(repo, "deliver-capability-alpha", active_context=context)

        self.assertEqual(recorded["status"], "created")
        self.assertEqual(invalidated["report"]["state"], IMPLEMENTATION_PROVIDER_REQUIRED)
        self.assertEqual(
            invalidated["report"]["issueCodes"],
            ["PROVIDER_OVERRIDE_REASSESSMENT_REQUIRED"],
        )
        self.assertFalse(invalidated["receiptCurrent"])
        self.assertEqual(invalidated["report"]["nextAction"], "reassess-provider-direction-and-promote-new-requirement")

    def test_not_ready_override_can_promote_a_new_requirement_cycle(self):
        repo = self.make_repo()
        requirement, _, context = self.repository_contract(repo)
        promote_requirement(repo, "deliver-capability-alpha", requirement, context)
        override = json.loads((FIXTURE_ROOT / "valid-provider-override-v1.json").read_text())
        override["project"] = {
            "id": requirement["consumer"]["projectId"],
            "rootIdentity": requirement["consumer"]["rootIdentity"],
        }
        override["activeChange"] = copy.deepcopy(requirement["activeChange"])
        override["previousProviderId"] = requirement["provider"]["id"]
        override["newProviderId"] = "provider.beta"
        override["invalidates"] = {
            "requirementDigests": [requirement["semanticInputDigest"]],
            "receiptDigests": [],
        }
        override = seal_provider_override(override)

        recorded = record_provider_override(
            repo,
            "deliver-capability-alpha",
            override,
            context,
        )
        reassessment = inspect_readiness(
            repo,
            "deliver-capability-alpha",
            active_context=context,
        )
        replacement = copy.deepcopy(requirement)
        replacement["requirementId"] = "requirement-beta"
        replacement["provider"]["id"] = "provider.beta"
        replacement = seal_requirement(replacement)
        promoted = promote_requirement(
            repo,
            "deliver-capability-alpha",
            replacement,
            context,
        )
        next_cycle = inspect_readiness(
            repo,
            "deliver-capability-alpha",
            active_context=context,
        )
        readiness_root = repo / ".planning" / "devflow" / "implementation-readiness" / "deliver-capability-alpha"

        self.assertEqual(recorded["status"], "created")
        self.assertEqual(
            reassessment["report"]["issueCodes"],
            ["PROVIDER_OVERRIDE_REASSESSMENT_REQUIRED"],
        )
        self.assertEqual(promoted["status"], "replaced")
        self.assertEqual(promoted["supersedesDigest"], requirement["semanticInputDigest"])
        self.assertTrue(Path(promoted["historyPath"]).is_file())
        self.assertTrue(Path(recorded["path"]).is_file())
        self.assertEqual(next_cycle["report"]["state"], IMPLEMENTATION_PROVIDER_REQUIRED)
        self.assertEqual(next_cycle["report"]["issueCodes"], ["IMPLEMENTATION_EVIDENCE_MISSING"])
        self.assertEqual(
            json.loads((readiness_root / "requirement.json").read_text())["provider"]["id"],
            "provider.beta",
        )

    def test_requirement_replacement_without_current_override_is_rejected(self):
        repo = self.make_repo()
        requirement, _, context = self.repository_contract(repo)
        promote_requirement(repo, "deliver-capability-alpha", requirement, context)
        replacement = copy.deepcopy(requirement)
        replacement["provider"]["id"] = "provider.beta"
        replacement = seal_requirement(replacement)

        with self.assertRaises(ReadinessError) as blocked:
            promote_requirement(
                repo,
                "deliver-capability-alpha",
                replacement,
                context,
            )

        self.assertEqual(blocked.exception.code, "requirement_conflict")

    def test_path_confinement_and_consumer_identity_fail_closed(self):
        repo = self.make_repo()
        requirement, _, context = self.repository_contract(repo)
        wrong_context = copy.deepcopy(context)
        wrong_context["consumer"]["rootIdentity"] = (
            "sha256:7777777777777777777777777777777777777777777777777777777777777777"
        )

        with self.assertRaises(ReadinessError) as invalid_change:
            promote_requirement(repo, "../escape", requirement, context)
        self.assertEqual(invalid_change.exception.code, "invalid_change_id")

        with self.assertRaises(ReadinessError) as wrong_consumer:
            promote_requirement(repo, "deliver-capability-alpha", requirement, wrong_context)
        self.assertEqual(wrong_consumer.exception.code, "consumer_identity_mismatch")

        outside = Path(tempfile.mkdtemp(prefix="devflow-readiness-outside-"))
        self.addCleanup(lambda: shutil.rmtree(outside, ignore_errors=True))
        readiness = repo / ".planning" / "devflow" / "implementation-readiness"
        readiness.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ReadinessError) as symlinked_parent:
            promote_requirement(repo, "deliver-capability-alpha", requirement, context)
        self.assertEqual(symlinked_parent.exception.code, "untrusted_readiness_path")

    def test_operator_cli_promotes_explicit_requirement_and_writes_only_ready_receipt(self):
        repo = self.make_repo()
        change_id = "deliver-capability-alpha"
        base_requirement = json.loads((FIXTURE_ROOT / "valid-requirement-v1.json").read_text())
        target_profile = copy.deepcopy(base_requirement["targetProfile"])
        context = active_context_from_repo(
            repo,
            change_id,
            project_id="consumer.alpha",
            target_profile=target_profile,
            evaluated_at="2026-08-07T08:45:00Z",
        )
        requirement = copy.deepcopy(base_requirement)
        requirement["consumer"] = copy.deepcopy(context["consumer"])
        requirement["activeChange"] = copy.deepcopy(context["activeChange"])
        requirement["targetProfile"] = copy.deepcopy(context["targetProfile"])
        requirement = seal_requirement(requirement)
        candidate = repo / "candidate-requirement.json"
        candidate.write_text(json.dumps(requirement, indent=2) + "\n")
        cli = SCRIPTS / "implementation_readiness.py"

        dry_run = subprocess.run(
            [
                sys.executable,
                str(cli),
                "promote",
                "--repo",
                str(repo),
                "--change-id",
                change_id,
                "--requirement",
                str(candidate),
                "--evaluated-at",
                "2026-08-07T08:45:00Z",
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
        self.assertEqual(json.loads(dry_run.stdout)["status"], "planned")
        readiness_root = repo / ".planning" / "devflow" / "implementation-readiness" / change_id
        self.assertFalse((readiness_root / "requirement.json").exists())

        applied = subprocess.run(
            [
                sys.executable,
                str(cli),
                "promote",
                "--repo",
                str(repo),
                "--change-id",
                change_id,
                "--requirement",
                str(candidate),
                "--evaluated-at",
                "2026-08-07T08:45:00Z",
                "--apply",
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(applied.returncode, 0, applied.stderr)
        self.assertEqual(json.loads(applied.stdout)["status"], "created")

        evidence = json.loads((FIXTURE_ROOT / "valid-evidence-v1.json").read_text())
        evidence["requirementDigest"] = requirement["semanticInputDigest"]
        evidence["consumer"] = copy.deepcopy(context["consumer"])
        evidence["activeChange"] = copy.deepcopy(context["activeChange"])
        evidence["targetProfile"] = copy.deepcopy(context["targetProfile"])
        evidence = seal_evidence(evidence)
        (readiness_root / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")

        before = subprocess.run(
            [
                sys.executable,
                str(cli),
                "inspect",
                "--repo",
                str(repo),
                "--change-id",
                change_id,
                "--evaluated-at",
                "2026-08-07T08:45:00Z",
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(before.returncode, 0, before.stderr)
        self.assertEqual(json.loads(before.stdout)["report"]["state"], IMPLEMENTATION_PROVIDER_READY)
        self.assertFalse(json.loads(before.stdout)["receiptCurrent"])

        receipt = subprocess.run(
            [
                sys.executable,
                str(cli),
                "write-receipt",
                "--repo",
                str(repo),
                "--change-id",
                change_id,
                "--evaluated-at",
                "2026-08-07T08:45:00Z",
                "--recorded-at",
                "2026-08-07T08:50:00Z",
                "--apply",
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(receipt.returncode, 0, receipt.stderr)
        self.assertEqual(json.loads(receipt.stdout)["status"], "created")

        after = subprocess.run(
            [
                sys.executable,
                str(cli),
                "inspect",
                "--repo",
                str(repo),
                "--change-id",
                change_id,
                "--evaluated-at",
                "2026-08-07T08:45:00Z",
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(after.returncode, 0, after.stderr)
        self.assertTrue(json.loads(after.stdout)["receiptCurrent"])


class ImplementationReadinessLifecycleTests(ContractFixtures, unittest.TestCase):
    VALID_CONTRACT = """# Agent Task Contract

## Goal
Implement the delegated source change and report the verified result.

## Worker ID
`worker-alpha`

## Scope
Allowed write set for worker `worker-alpha` only:
- `src/worker.py`
Forbidden: do not modify release assets, OpenSpec, `.planning/devflow/STATE.md`,
or any path outside the named write set.

## Constraints
Preserve public behavior and stop before expanding the approved scope.

## Verification
Run `python3 -m unittest tests.test_worker`.

## Evidence
Report changed files, commands, test results, unverified areas, and risk notes.

## Human Gate
Wait for review before expanding scope, changing dependencies, skipping
validation, or continuing after a failing test.
"""

    def make_repo(self, *, ready: bool, verification_passed: bool = False):
        repo = Path(tempfile.mkdtemp(prefix="devflow-readiness-lifecycle-"))
        self.addCleanup(lambda: shutil.rmtree(repo, ignore_errors=True))
        change_id = "deliver-capability-alpha"
        (repo / "src").mkdir(parents=True)
        (repo / "src" / "app.py").write_text("VALUE = 1\n")
        (repo / "AGENTS.md").write_text("# Project rules\n")
        (repo / ".dev-flow.json").write_text(
            json.dumps({"projectContract": 2, "workflow": {"mode": "full-openspec"}, "hook": {"mode": "block"}})
        )
        (repo / "openspec" / "changes" / change_id / "specs" / "readiness").mkdir(parents=True)
        (repo / "openspec" / "config.yaml").write_text("schema: spec-driven\n")
        (repo / "openspec" / "changes" / change_id / "proposal.md").write_text("## Why\nDeliver exact work.\n")
        (repo / "openspec" / "changes" / change_id / "design.md").write_text("## Design\nUse one contract.\n")
        (repo / "openspec" / "changes" / change_id / "tasks.md").write_text("- [ ] Implement exact work.\n")
        (repo / "openspec" / "changes" / change_id / "specs" / "readiness" / "spec.md").write_text(
            "## Requirement\nImplementation is project-bound.\n"
        )
        (repo / ".planning" / "devflow").mkdir(parents=True)
        (repo / ".planning" / "devflow" / "STATE.md").write_text(
            f"""---
workflow_version: 0.3.0
project_mode: brownfield
current_stage: executing
current_change:
  id: {change_id}
  status: executing
gates:
  workflow_initialized: true
  spec_approved: true
  plan_written: true
  tests_baseline_known: true
  implementation_done: false
  verification_passed: {'true' if verification_passed else 'false'}
  state_updated: true
  archive_allowed: false
  release_allowed: false
implementation_readiness:
  required: true
context_management:
  compact_status: not_needed
goal_gate:
  required: false
  status: not_required
context_health:
  goal_summary: none
---
# State
"""
        )
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "-c", "user.name=DevFlow", "-c", "user.email=devflow@example.com", "commit", "-m", "fixture"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        base_requirement = json.loads((FIXTURE_ROOT / "valid-requirement-v1.json").read_text())
        context = active_context_from_repo(
            repo,
            change_id,
            project_id="consumer.alpha",
            target_profile=base_requirement["targetProfile"],
            evaluated_at="2026-08-07T08:45:00Z",
        )
        requirement = copy.deepcopy(base_requirement)
        requirement["consumer"] = copy.deepcopy(context["consumer"])
        requirement["activeChange"] = copy.deepcopy(context["activeChange"])
        requirement = seal_requirement(requirement)
        promote_requirement(repo, change_id, requirement, context)
        if ready:
            evidence = json.loads((FIXTURE_ROOT / "valid-evidence-v1.json").read_text())
            evidence["requirementDigest"] = requirement["semanticInputDigest"]
            evidence["consumer"] = copy.deepcopy(context["consumer"])
            evidence["activeChange"] = copy.deepcopy(context["activeChange"])
            evidence = seal_evidence(evidence)
            root = repo / ".planning" / "devflow" / "implementation-readiness" / change_id
            (root / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
            report = inspect_readiness(repo, change_id, active_context=context)["report"]
            write_ready_receipt(repo, change_id, report, recorded_at="2026-08-07T08:50:00Z")
        return repo, change_id

    def run_pre_edit(self, repo: Path, path: str):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "pre_edit_policy.py")],
            input=json.dumps({"cwd": str(repo), "tool_input": {"file_path": str(repo / path)}}),
            text=True,
            capture_output=True,
            check=False,
        )

    def test_unresolved_readiness_blocks_every_governed_lifecycle_transition(self):
        repo, change_id = self.make_repo(ready=False)
        contract = repo / "worker-contract.md"
        contract.write_text(self.VALID_CONTRACT)

        pre_edit = self.run_pre_edit(repo, "src/app.py")
        planning_edit = self.run_pre_edit(repo, f"openspec/changes/{change_id}/tasks.md")
        continuation = continuation_decision(repo)
        validation = validate_workflow_state(repo)
        delegation = validate_agent_task_contract_file(contract, repo=repo)
        verification = record_verification(repo, "python3 -m unittest", "pass")
        release = release_promotion_readiness(repo, "dev-flow", require_authorization=False)
        archive = archive_status(repo, change_id)

        self.assertIn("implementation readiness", pre_edit.stdout.lower())
        self.assertEqual(planning_edit.stdout.strip(), "")
        self.assertEqual(continuation["action"], CHECKPOINT_AND_CONTINUE)
        self.assertFalse(continuation["stopAllowed"])
        self.assertIn("awaiting_human", continuation["nextAction"])
        self.assertFalse(validation["ok"], validation)
        self.assertTrue(any("implementation readiness" in issue.lower() for issue in validation["issues"]))
        self.assertFalse(delegation["ok"], delegation)
        self.assertTrue(any("implementation_readiness" in issue for issue in delegation["errors"]))
        self.assertEqual(verification["result"], "blocked")
        self.assertIn("implementation_readiness", release["blockers"])
        self.assertIn("implementation_provider_not_ready", {item["code"] for item in archive["risks"]})

        state_path = repo / ".planning" / "devflow" / "STATE.md"
        state_path.write_text(
            state_path.read_text()
            .replace("current_stage: executing", "current_stage: awaiting_human")
            .replace("  status: executing", "  status: awaiting_human")
        )
        persisted = continuation_decision(repo)
        self.assertEqual(persisted["action"], AWAIT_HUMAN)
        self.assertTrue(persisted["stopAllowed"])

    def test_validation_preserves_readiness_error_code(self):
        repo, _ = self.make_repo(ready=False)
        error = ReadinessError("sentinel_readiness_code", "Sentinel readiness failure")

        with mock.patch("workflow_validate.inspect_repository_readiness", side_effect=error):
            validation = validate_workflow_state(repo)

        self.assertEqual(
            validation["implementationReadiness"]["issues"],
            ["sentinel_readiness_code"],
        )

    def test_current_ready_receipt_preserves_existing_ordinary_gate_behavior(self):
        repo, _ = self.make_repo(ready=True)

        pre_edit = self.run_pre_edit(repo, "src/app.py")
        continuation = continuation_decision(repo)
        validation = validate_workflow_state(repo)

        self.assertEqual(pre_edit.stdout.strip(), "")
        self.assertEqual(continuation["action"], CONTINUE_NEXT_ITEM)
        self.assertFalse(any("implementation readiness" in issue.lower() for issue in validation["issues"]))

    def test_post_compact_records_completion_but_blocks_resume_into_product_writes(self):
        repo, _ = self.make_repo(ready=False)
        state_path = repo / ".planning" / "devflow" / "STATE.md"
        state_path.write_text(
            state_path.read_text().replace(
                "  compact_status: not_needed\n",
                "  last_checkpoint_id: readiness-checkpoint\n"
                "  last_checkpoint_file: .planning/devflow/checkpoints/readiness-checkpoint.md\n"
                "  compact_status: pending\n"
                "  last_compact_result_file: none\n"
                "  compact_source: checkpoint\n"
                "  compact_updated_at: none\n"
                "  compact_skip_reason: none\n"
                "  compact_error: none\n",
            )
        )
        checkpoint = repo / ".planning" / "devflow" / "checkpoints" / "readiness-checkpoint.md"
        checkpoint.parent.mkdir(parents=True)
        checkpoint.write_text(
            "---\ncheckpoint_id: readiness-checkpoint\ncompact_status: pending\n---\n\n# Checkpoint\n"
        )

        report = handle_compact_recovery_event(
            repo,
            "post_compact",
            {"trigger": "manual", "session_id": "session-alpha"},
        )

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["action"], "compact_completed_readiness_blocked")
        self.assertFalse(report["continuationAllowed"])
        self.assertTrue(report["implementationReadiness"]["applicable"])

    def test_task_execution_cli_requires_ready_receipt_and_ordinary_authority(self):
        blocked_repo, blocked_change = self.make_repo(ready=False)
        ready_repo, ready_change = self.make_repo(ready=True)
        cli = SCRIPTS / "implementation_readiness.py"

        blocked = subprocess.run(
            [
                sys.executable,
                str(cli),
                "check-mutation",
                "--repo",
                str(blocked_repo),
                "--change-id",
                blocked_change,
                "--ordinary-authority",
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        ordinary_missing = subprocess.run(
            [
                sys.executable,
                str(cli),
                "check-mutation",
                "--repo",
                str(ready_repo),
                "--change-id",
                ready_change,
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        allowed = subprocess.run(
            [
                sys.executable,
                str(cli),
                "check-mutation",
                "--repo",
                str(ready_repo),
                "--change-id",
                ready_change,
                "--ordinary-authority",
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(blocked.returncode, 2)
        self.assertFalse(json.loads(blocked.stdout)["allowed"])
        self.assertEqual(ordinary_missing.returncode, 2)
        self.assertIn("ORDINARY_IMPLEMENTATION_AUTHORITY_REQUIRED", json.loads(ordinary_missing.stdout)["issueCodes"])
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        self.assertTrue(json.loads(allowed.stdout)["allowed"])


class ImplementationReadinessRegressionTests(unittest.TestCase):
    def test_revision_ten_retains_schema_eight_and_refresh_inputs(self):
        manifest = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "project-migration.json").read_text()
        )
        refresh = manifest["refreshContract"]
        tracked = set(refresh["trackedInputs"])
        release_root = PLUGIN_ROOT.parents[2] / "plugins" / "dev-flow"

        self.assertEqual(manifest["projectSchema"]["head"], 8)
        self.assertEqual(refresh["revision"], 10)
        self.assertEqual(refresh["evidence"]["schemaDecision"], "managed-refresh")
        self.assertLessEqual(PROJECT_REFRESH_REVISION3_REQUIRED_INPUTS, tracked)
        self.assertLessEqual(PROJECT_REFRESH_REVISION4_REQUIRED_INPUTS, tracked)
        self.assertLessEqual(PROJECT_REFRESH_REVISION5_REQUIRED_INPUTS, tracked)
        self.assertLessEqual(PROJECT_REFRESH_REVISION6_REQUIRED_INPUTS, tracked)
        self.assertLessEqual(PROJECT_REFRESH_REVISION7_REQUIRED_INPUTS, tracked)
        self.assertLessEqual(PROJECT_REFRESH_REVISION8_REQUIRED_INPUTS, tracked)
        self.assertLessEqual(PROJECT_REFRESH_REVISION9_REQUIRED_INPUTS, tracked)
        for version in (1, 2, 3, 4, 5, 6, 7):
            relative = Path("assets") / "project-refresh" / f"config-v{version}.json"
            with self.subTest(config=relative.as_posix()):
                self.assertEqual(
                    (PLUGIN_ROOT / relative).read_bytes(),
                    (release_root / relative).read_bytes(),
                )
        impact = analyze_project_refresh_impact(
            PLUGIN_ROOT,
            release_root,
            expected_change="add-codex-fleet-sync",
        )
        self.assertTrue(impact["ok"], impact)
        expected_status = (
            "current"
            if impact["sourceRevision"] == impact["baselineRevision"]
            else "changed_covered"
        )
        self.assertEqual(impact["status"], expected_status)
        self.assertEqual(impact["configSensitiveChanges"], [])

    def test_project_refresh_revision_three_compatibility_matrix_has_live_proofs(self):
        matrix = json.loads((FIXTURE_ROOT / "project-refresh-cases-v3.json").read_text())
        self.assertEqual(matrix["refreshContractRevision"], 3)
        self.assertEqual(matrix["projectSchemaHead"], 2)
        self.assertEqual(matrix["schemaDecision"], "managed-refresh")
        self.assertEqual(
            {item["id"] for item in matrix["cases"]},
            {
                "current-schema-2",
                "stale-project-skill-link",
                "missing-project-direction",
                "existing-project-direction",
                "brownfield-generated-guidance",
                "ambiguous-baseline",
                "no-automatic-provider-selection",
            },
        )
        proof_text = "\n".join(
            path.read_text()
            for path in (
                PLUGIN_ROOT / "tests" / "test_implementation_readiness.py",
                PLUGIN_ROOT / "tests" / "test_plugin_project_migration.py",
                PLUGIN_ROOT / "tests" / "test_project_refresh.py",
            )
        )
        for case in matrix["cases"]:
            with self.subTest(case=case["id"]):
                self.assertIn(f"def {case['proof']}", proof_text)

    def test_new_contract_surface_stays_domain_neutral_and_does_not_restore_retired_routing(self):
        targets = [
            SCRIPTS / "workflow_implementation_readiness.py",
            *sorted(SCHEMA_ROOT.glob("implementation-readiness-*.schema.json")),
            *sorted(FIXTURE_ROOT.glob("*.json")),
        ]
        self.assertTrue(targets[0].is_file(), "the readiness deep module must exist")
        text = "\n".join(path.read_text().lower() for path in targets)
        forbidden = (
            "godot",
            "gamedev",
            "workshop",
            "mini-game",
            "minigame",
            "methodology" + "_provider",
            "roadmap" + "_provider",
            "provider" + "_profiles",
            "provider" + "_profile",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, text)


if __name__ == "__main__":
    unittest.main()
