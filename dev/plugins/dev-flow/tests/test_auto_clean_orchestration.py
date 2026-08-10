from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
CLI = SCRIPTS / "generated_artifact_lifecycle.py"
sys.path.insert(0, str(SCRIPTS))


class AutoCleanOrchestrationSupport:
    def make_repo(self) -> Path:
        temporary = tempfile.TemporaryDirectory(prefix="df-auto-clean-", dir="/tmp")
        self.addCleanup(temporary.cleanup)
        repo = Path(temporary.name)
        subprocess.run(
            ["git", "init", "-q"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
        return repo

    def persist_contract(self, repo: Path, contract: dict[str, object]) -> Path:
        from workflow_generated_artifacts import (
            canonical_document_bytes,
            contract_document_path,
        )

        path = contract_document_path(repo, contract)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical_document_bytes(contract))
        return path

    def prepare(self, repo: Path, **overrides: object) -> dict[str, object]:
        from workflow_generated_artifacts import prepare_contract

        values: dict[str, object] = {
            "repo": repo,
            "task_id": "task-auto-clean",
            "run_id": "run-1",
            "owner_id": "main",
            "owner_pid": 999_999_999,
            "command": ["python3", "build.py", "--output", "artifact"],
            "isolated_roots": [".devflow-generated/task-auto-clean/run-1"],
            "adjacent_outputs": [],
            "retention": "cleanup",
            "contract_id": "contract-auto-clean",
            "now_ns": 1_700_000_000_000_000_000,
        }
        values.update(overrides)
        contract = prepare_contract(**values)
        self.persist_contract(repo, contract)
        return contract

    def create_output(
        self,
        repo: Path,
        contract: dict[str, object],
        *,
        name: str = "build/output.bin",
        content: bytes = b"task-owned-output",
    ) -> Path:
        scope = contract["scopes"][0]
        root_value = scope["path"] if scope["kind"] == "isolated_root" else scope["parent"]
        path = repo / str(root_value) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def observe(self, repo: Path, contract: dict[str, object]) -> dict[str, object]:
        from workflow_generated_artifacts import observe_artifacts

        return observe_artifacts(repo, contract, exit_code=0)

    def ready_cleanup(
        self,
        repo: Path,
        **contract_overrides: object,
    ) -> tuple[dict[str, object], dict[str, object], dict[str, object], Path]:
        from workflow_generated_artifacts import plan_cleanup

        contract = self.prepare(repo, **contract_overrides)
        artifact = self.create_output(repo, contract)
        manifest = self.observe(repo, contract)
        plan = plan_cleanup(repo, contract, manifest)
        self.assertEqual(plan["decision"], "AUTO_CLEAN", plan)
        return contract, manifest, plan, artifact

    def write_state(self, repo: Path) -> tuple[Path, bytes]:
        path = repo / ".planning" / "devflow" / "STATE.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        content = (
            "# DevFlow State\n\n"
            "current_stage: executing\n"
            "current_change:\n"
            "  id: centralize-devflow-authority-delta\n"
            "  status: executing\n"
        ).encode()
        path.write_bytes(content)
        return path, content

    def assert_state_unchanged(self, path: Path, before: bytes) -> None:
        self.assertEqual(path.read_bytes(), before)
        self.assertNotIn(b"awaiting_human", path.read_bytes())

    def orchestrate(
        self,
        repo: Path,
        contract: dict[str, object],
        manifest: dict[str, object],
        proposed_plan: dict[str, object] | None,
        *,
        prior_receipt: dict[str, object] | None = None,
    ) -> dict[str, object]:
        from workflow_continuation import generated_artifact_orchestration

        if prior_receipt is None:
            return generated_artifact_orchestration(
                repo,
                contract,
                manifest,
                proposed_plan,
            )
        try:
            return generated_artifact_orchestration(
                repo,
                contract,
                manifest,
                proposed_plan,
                prior_receipt=prior_receipt,
            )
        except TypeError as error:
            self.fail(
                "trusted cleanup orchestration does not expose receipt-bound replay: "
                f"{error}"
            )

    def assert_repair_stop(
        self,
        result: dict[str, object],
        *,
        reason: str,
    ) -> None:
        self.assertEqual(result.get("decision"), "FAIL_CLOSED_REPAIR", result)
        self.assertEqual(result.get("action"), "FAIL_CLOSED_REPAIR", result)
        self.assertFalse(result.get("applyAllowed"), result)
        self.assertIsNone(result.get("receipt"), result)
        self.assertNotEqual(result.get("action"), "AWAIT_HUMAN", result)
        self.assertIn(reason, json.dumps(result.get("reasons", []), sort_keys=True))

    def write_document(self, path: Path, document: dict[str, object]) -> None:
        from workflow_generated_artifacts import canonical_document_bytes

        path.write_bytes(canonical_document_bytes(document))


class AutoCleanOrchestrationTests(
    AutoCleanOrchestrationSupport,
    unittest.TestCase,
):
    maxDiff = None

    def test_direct_cli_still_refuses_mutation_without_explicit_apply(self) -> None:
        from workflow_generated_artifacts import contract_document_path

        repo = self.make_repo()
        contract, manifest, plan, artifact = self.ready_cleanup(repo)
        state_path, state_before = self.write_state(repo)
        manifest_path = repo / "cleanup.manifest.json"
        plan_path = repo / "cleanup.plan.json"
        self.write_document(manifest_path, manifest)
        self.write_document(plan_path, plan)

        completed = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "cleanup",
                "--repo",
                str(repo),
                "--contract",
                str(contract_document_path(repo, contract)),
                "--manifest",
                str(manifest_path),
                "--plan",
                str(plan_path),
            ],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 3, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "authorization_required")
        self.assertEqual(result["decision"], "AUTO_CLEAN")
        self.assertIn("--apply", result["nextAction"])
        self.assertTrue(artifact.exists())
        self.assert_state_unchanged(state_path, state_before)

    def test_trusted_orchestrator_supplies_guarded_apply_and_terminal_verifies(self) -> None:
        from workflow_generated_artifacts import validate_terminal_cleanup

        repo = self.make_repo()
        contract, manifest, plan, artifact = self.ready_cleanup(repo)
        state_path, state_before = self.write_state(repo)

        result = self.orchestrate(repo, contract, manifest, plan)

        self.assertEqual(result.get("decision"), "AUTO_CLEAN", result)
        self.assertEqual(
            (result.get("authorityResolution") or {}).get("decision"),
            "AUTO_CLEAN",
            result,
        )
        self.assertEqual(result.get("status"), "complete", result)
        self.assertTrue(result.get("applyAllowed"), result)
        self.assertTrue(result.get("requiresExplicitApply"), result)
        self.assertTrue(result.get("applySafeguardSupplied"), result)
        self.assertTrue(result.get("receiptRequired"), result)
        receipt = result.get("receipt")
        self.assertIsInstance(receipt, dict, result)
        self.assertEqual(receipt.get("decision"), "AUTO_CLEAN", receipt)
        self.assertEqual(receipt.get("status"), "complete", receipt)
        self.assertEqual(
            validate_terminal_cleanup(repo, contract, manifest, result["plan"], receipt),
            [],
        )
        self.assertFalse(artifact.exists())
        self.assert_state_unchanged(state_path, state_before)

    def test_active_owner_returns_wait_owner_without_apply_or_human_state(self) -> None:
        from workflow_generated_artifacts import plan_cleanup

        repo = self.make_repo()
        contract = self.prepare(repo, owner_pid=os.getpid())
        artifact = self.create_output(repo, contract)
        manifest = self.observe(repo, contract)
        plan = plan_cleanup(repo, contract, manifest)
        self.assertEqual(plan["decision"], "WAIT_OWNER", plan)
        state_path, state_before = self.write_state(repo)

        result = self.orchestrate(repo, contract, manifest, plan)

        self.assertEqual(result.get("decision"), "WAIT_OWNER", result)
        self.assertEqual(result.get("action"), "WAIT_OWNER", result)
        self.assertFalse(result.get("applyAllowed"), result)
        self.assertIsNone(result.get("receipt"), result)
        self.assertTrue(artifact.exists())
        self.assert_state_unchanged(state_path, state_before)

    def test_plan_identity_and_membership_drift_stop_for_repair_without_gate(self) -> None:
        cases = ("plan", "identity", "membership")
        for case in cases:
            with self.subTest(case=case):
                repo = self.make_repo()
                contract, manifest, plan, artifact = self.ready_cleanup(repo)
                state_path, state_before = self.write_state(repo)
                proposed_plan: dict[str, object] | None = plan
                expected_reason = "stale_or_self_authored_plan"
                if case == "plan":
                    proposed_plan = deepcopy(plan)
                    proposed_plan["reasons"] = ["self_authored"]
                elif case == "identity":
                    artifact.write_bytes(b"changed-after-observation")
                    proposed_plan = None
                    expected_reason = "identity_drift"
                else:
                    (artifact.parent / "late-unlisted.bin").write_bytes(b"late")
                    proposed_plan = None
                    expected_reason = "membership_drift"

                result = self.orchestrate(
                    repo,
                    contract,
                    manifest,
                    proposed_plan,
                )

                self.assert_repair_stop(result, reason=expected_reason)
                self.assertTrue(artifact.exists())
                self.assert_state_unchanged(state_path, state_before)

    def test_tracked_source_and_preexisting_user_content_are_preserved(self) -> None:
        from workflow_generated_artifacts import capture_identity, plan_cleanup

        for case in ("tracked-source", "preexisting-user"):
            with self.subTest(case=case):
                repo = self.make_repo()
                source = repo / "src"
                source.mkdir()
                artifact = source / "generated.tmp"
                if case == "preexisting-user":
                    artifact.write_bytes(b"user-content")
                contract = self.prepare(
                    repo,
                    isolated_roots=[],
                    adjacent_outputs=[{"parent": "src", "pattern": "**/*.tmp"}],
                )
                if case == "tracked-source":
                    artifact.write_bytes(b"generated-source")
                    subprocess.run(
                        ["git", "add", "src/generated.tmp"],
                        cwd=repo,
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                manifest = self.observe(repo, contract)
                if case == "preexisting-user":
                    manifest["entries"] = [
                        {
                            "scopeId": "adjacent-1",
                            **capture_identity(repo, artifact),
                        }
                    ]
                plan = plan_cleanup(repo, contract, manifest)
                state_path, state_before = self.write_state(repo)

                result = self.orchestrate(repo, contract, manifest, None)

                expected_reason = (
                    "tracked_path" if case == "tracked-source" else "preexisting_path"
                )
                self.assert_repair_stop(result, reason=expected_reason)
                self.assertTrue(artifact.exists())
                self.assert_state_unchanged(state_path, state_before)

    def test_historical_receipt_and_persistent_evidence_scopes_are_preserved(self) -> None:
        from workflow_generated_artifacts import document_sha256

        protected_scopes = (
            ".planning/devflow/generated-artifacts/history",
            "openspec/changes/centralize-devflow-authority-delta/evidence",
        )
        for protected_scope in protected_scopes:
            with self.subTest(protected_scope=protected_scope):
                repo = self.make_repo()
                contract, manifest, _plan, artifact = self.ready_cleanup(repo)
                protected_contract = deepcopy(contract)
                protected_contract["scopes"][0]["path"] = protected_scope
                protected_manifest = deepcopy(manifest)
                protected_manifest["contractSha256"] = document_sha256(
                    protected_contract
                )
                state_path, state_before = self.write_state(repo)

                result = self.orchestrate(
                    repo,
                    protected_contract,
                    protected_manifest,
                    None,
                )

                self.assert_repair_stop(result, reason="protected_scope")
                self.assertTrue(artifact.exists())
                self.assert_state_unchanged(state_path, state_before)

    def test_ambiguous_ownership_is_preserved_without_automatic_gate_write(self) -> None:
        repo = self.make_repo()
        contract, manifest, _plan, artifact = self.ready_cleanup(repo)
        ambiguous_manifest = deepcopy(manifest)
        ambiguous_manifest["owner"]["id"] = "unknown-owner"
        state_path, state_before = self.write_state(repo)

        result = self.orchestrate(repo, contract, ambiguous_manifest, None)

        self.assert_repair_stop(result, reason="owner_binding_mismatch")
        self.assertTrue(artifact.exists())
        self.assert_state_unchanged(state_path, state_before)

    def test_non_exact_and_recursive_plan_targets_never_mutate(self) -> None:
        for case, replacement in (
            ("parent", ".devflow-generated/task-auto-clean"),
            ("recursive", ".devflow-generated/task-auto-clean/run-1/**"),
        ):
            with self.subTest(case=case):
                repo = self.make_repo()
                contract, manifest, plan, artifact = self.ready_cleanup(repo)
                unsafe_plan = deepcopy(plan)
                unsafe_plan["entries"] = [replacement]
                state_path, state_before = self.write_state(repo)

                result = self.orchestrate(
                    repo,
                    contract,
                    manifest,
                    unsafe_plan,
                )

                self.assert_repair_stop(
                    result,
                    reason="stale_or_self_authored_plan",
                )
                self.assertTrue(artifact.exists())
                self.assertTrue((repo / ".devflow-generated").exists())
                self.assert_state_unchanged(state_path, state_before)

    def test_terminal_receipt_replay_is_idempotent_and_does_not_reapply(self) -> None:
        from workflow_generated_artifacts import apply_cleanup, validate_terminal_cleanup

        repo = self.make_repo()
        contract, manifest, plan, artifact = self.ready_cleanup(repo)
        receipt = apply_cleanup(repo, contract, manifest, plan)
        self.assertFalse(artifact.exists())
        self.assertEqual(
            validate_terminal_cleanup(repo, contract, manifest, plan, receipt),
            [],
        )
        state_path, state_before = self.write_state(repo)

        result = self.orchestrate(
            repo,
            contract,
            manifest,
            plan,
            prior_receipt=receipt,
        )

        self.assertEqual(result.get("status"), "complete", result)
        self.assertEqual(result.get("receipt"), receipt, result)
        self.assertTrue(result.get("replayed"), result)
        self.assertFalse(result.get("applySafeguardSupplied"), result)
        self.assertFalse(artifact.exists())
        self.assert_state_unchanged(state_path, state_before)


if __name__ == "__main__":
    unittest.main()
