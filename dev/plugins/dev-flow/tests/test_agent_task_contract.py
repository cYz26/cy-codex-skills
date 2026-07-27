import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
TEMPLATES = PLUGIN_ROOT / "assets" / "templates"
sys.path.insert(0, str(SCRIPTS))

VALID_WRITE_SET = """Allowed write set for worker `parser` only:
- `dev/plugins/dev-flow/scripts/workflow_example.py`
- `dev/plugins/dev-flow/tests/test_example.py`"""

VALID_CONTRACT = f"""# Agent Task Contract

## Goal
Implement the delegated parser change and return a concise summary of the final artifact.

## Worker ID
`parser`

## Scope
{VALID_WRITE_SET}
Forbidden: do not modify release assets, OpenSpec files, `.planning/devflow/STATE.md`,
or files outside the named write set.

## Constraints
Preserve Python 3.9 compatibility, use only the standard library, keep existing
style, and avoid changing public CLI behavior outside the delegated task.

## Verification
Run `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest dev.plugins.dev-flow.tests.test_example`.

## Evidence
Report changed files, commands run, test logs or validation results,
unverified areas, and risk notes.

## Human Gate
Wait for review before expanding scope, touching forbidden files, changing
public APIs, skipping validation, or continuing with failing tests.
"""


class AgentTaskContractTests(unittest.TestCase):
    def test_template_contains_required_sections_and_usage_boundary(self):
        template = (TEMPLATES / "AGENT_TASK_CONTRACT.md.template").read_text()

        for heading in [
            "# Agent Task Contract",
            "## Goal",
            "## Worker ID",
            "## Scope",
            "## Constraints",
            "## Verification",
            "## Evidence",
            "## Human Gate",
        ]:
            self.assertIn(heading, template)
        self.assertIn("Allowed", template)
        self.assertIn("Forbidden", template)
        self.assertIn("changed files", template)
        self.assertIn("unverified areas", template)
        self.assertIn("risk notes", template)
        self.assertIn("Allowed write set for worker `<worker-id>` only", template)
        self.assertIn("Read-only explorers and", template)
        self.assertIn("Primary-owned shared paths", template)
        self.assertIn("repeat `--contract`", template)

    def test_validator_accepts_complete_contract(self):
        from workflow_agent_task_contract import validate_agent_task_contract_text

        report = validate_agent_task_contract_text(VALID_CONTRACT)

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["missingSections"], [])
        self.assertEqual(report["errors"], [])
        self.assertEqual(
            report["validationManifest"]["gates"]["G41"],
            {
                "required": False,
                "status": "not_applicable",
                "errors": [],
            },
        )

    def test_optional_generated_artifact_reference_adds_pending_g41(self):
        from workflow_agent_task_contract import validate_agent_task_contract_text

        contract = (
            VALID_CONTRACT
            + "\n## Generated Artifact Contract\n\n"
            "- Contract: `.planning/devflow/generated-artifacts/parser-run.contract.json`\n"
        )

        report = validate_agent_task_contract_text(contract)

        self.assertTrue(report["ok"], report)
        self.assertEqual(
            report["validationManifest"]["generatedArtifact"],
            {
                "referenced": True,
                "contractPath": (
                    ".planning/devflow/generated-artifacts/"
                    "parser-run.contract.json"
                ),
                "contractSha256": None,
            },
        )
        self.assertEqual(
            report["validationManifest"]["gates"]["G41"],
            {
                "required": True,
                "status": "pending",
                "errors": [],
            },
        )

    def test_g41_post_validation_requires_bound_terminal_cleanup_receipt(self):
        from workflow_agent_task_contract import (
            validate_agent_task_contract_file,
            validate_agent_task_worker_result,
        )
        from workflow_generated_artifacts import (
            apply_cleanup,
            canonical_document_bytes,
            cleanup_receipt,
            observe_artifacts,
            plan_cleanup,
            prepare_contract,
        )

        temporary = tempfile.TemporaryDirectory(prefix="agent-artifact-", dir="/tmp")
        self.addCleanup(temporary.cleanup)
        repo = Path(temporary.name)
        subprocess.run(
            ["git", "init", "-q"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
        lifecycle_root = repo / ".planning" / "devflow" / "generated-artifacts"
        lifecycle_root.mkdir(parents=True)
        contract_path = lifecycle_root / "contracts" / "parser-run.contract.json"
        contract_path.parent.mkdir()
        manifest_path = lifecycle_root / "parser-run.manifest.json"
        plan_path = lifecycle_root / "parser-run.plan.json"
        receipt_path = lifecycle_root / "parser-run.receipt.json"
        artifact_root = ".devflow-generated/parser/run-1"
        contract = prepare_contract(
            repo=repo,
            task_id="task-1",
            run_id="run-1",
            owner_id="parser",
            owner_pid=999_999_999,
            command=["python3", "build.py"],
            isolated_roots=[artifact_root],
            adjacent_outputs=[],
            contract_id="parser-run",
        )
        contract_path.write_bytes(canonical_document_bytes(contract))
        agent_contract_path = repo / "agent-task.md"
        agent_contract_path.write_text(
            VALID_CONTRACT
            + "\n## Generated Artifact Contract\n\n"
            "- Contract: "
            "`.planning/devflow/generated-artifacts/contracts/parser-run.contract.json`\n"
        )
        validation = validate_agent_task_contract_file(
            agent_contract_path,
            repo=repo,
        )
        self.assertTrue(validation["ok"], validation)

        artifact = repo / artifact_root / "output.bin"
        artifact.parent.mkdir(parents=True)
        artifact.write_bytes(b"generated")
        manifest = observe_artifacts(
            repo,
            contract,
            exit_code=0,
        )
        plan = plan_cleanup(repo, contract, manifest)
        manifest_path.write_bytes(canonical_document_bytes(manifest))
        plan_path.write_bytes(canonical_document_bytes(plan))

        unresolved = validate_agent_task_worker_result(
            repo,
            validation,
            {
                "workerId": "parser",
                "generatedArtifacts": {
                    "contractPath": contract_path.relative_to(repo).as_posix(),
                    "manifestPath": manifest_path.relative_to(repo).as_posix(),
                    "planPath": plan_path.relative_to(repo).as_posix(),
                    "cleanupReceiptPath": receipt_path.relative_to(repo).as_posix(),
                    "cleanup_complete": True,
                },
            },
        )

        self.assertEqual(
            validation["validationManifest"]["generatedArtifact"]["contractSha256"],
            manifest["contractSha256"],
        )
        self.assertFalse(unresolved["ok"], unresolved)
        self.assertEqual(unresolved["gate"], "G41")
        self.assertIn("cleanup_receipt_missing", unresolved["errors"])
        self.assertTrue(artifact.exists())

        forged_plan = {**plan, "entries": []}
        forged_receipt = cleanup_receipt(
            contract,
            manifest,
            forged_plan,
            decision="AUTO_CLEAN",
            status="complete",
            removed=[],
            remaining=[],
            failure=None,
        )
        plan_path.write_bytes(canonical_document_bytes(forged_plan))
        receipt_path.write_bytes(canonical_document_bytes(forged_receipt))
        forged = validate_agent_task_worker_result(
            repo,
            validation,
            {
                "workerId": "parser",
                "generatedArtifacts": {
                    "contractPath": contract_path.relative_to(repo).as_posix(),
                    "manifestPath": manifest_path.relative_to(repo).as_posix(),
                    "planPath": plan_path.relative_to(repo).as_posix(),
                    "cleanupReceiptPath": receipt_path.relative_to(repo).as_posix(),
                    "cleanup_complete": True,
                },
            },
        )

        self.assertFalse(forged["ok"], forged)
        self.assertIn("plan:plan_entries_manifest_mismatch", forged["errors"])
        self.assertTrue(
            any(
                error.startswith("generated_artifact_remaining:")
                for error in forged["errors"]
            ),
            forged,
        )
        self.assertTrue(artifact.exists())

        plan_path.write_bytes(canonical_document_bytes(plan))
        receipt = apply_cleanup(repo, contract, manifest, plan)
        receipt_path.write_bytes(canonical_document_bytes(receipt))
        worker_result = {
            "workerId": "parser",
            "generatedArtifacts": {
                "contractPath": contract_path.relative_to(repo).as_posix(),
                "manifestPath": manifest_path.relative_to(repo).as_posix(),
                "planPath": plan_path.relative_to(repo).as_posix(),
                "cleanupReceiptPath": receipt_path.relative_to(repo).as_posix(),
                "cleanup_complete": True,
            },
        }

        post_validation = validate_agent_task_worker_result(
            repo,
            validation,
            worker_result,
        )

        self.assertTrue(post_validation["ok"], post_validation)
        self.assertEqual(post_validation["status"], "passed")
        self.assertTrue(post_validation["cleanupComplete"])
        self.assertFalse(artifact.exists())

        worker_result_path = repo / "worker-result.json"
        worker_result_path.write_bytes(canonical_document_bytes(worker_result))
        cli = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "validate_agent_task_contract.py"),
                "--repo",
                str(repo),
                "--contract",
                str(agent_contract_path),
                "--worker-result",
                str(worker_result_path),
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(cli.returncode, 0, cli.stderr)
        cli_report = json.loads(cli.stdout)
        self.assertTrue(cli_report["ok"], cli_report)
        self.assertEqual(cli_report["postValidation"]["status"], "passed")

    def test_g41_rejects_self_authored_or_mismatched_worker_result(self):
        from workflow_agent_task_contract import (
            validate_agent_task_contract_text,
            validate_agent_task_worker_result,
        )

        report = validate_agent_task_contract_text(
            VALID_CONTRACT
            + "\n## Generated Artifact Contract\n\n"
            "- Contract: `.planning/devflow/generated-artifacts/parser.contract.json`\n"
        )
        result = validate_agent_task_worker_result(
            Path.cwd(),
            report,
            {
                "workerId": "other-worker",
                "generatedArtifacts": {
                    "contractPath": "self-authored.contract.json",
                    "manifestPath": "self-authored.manifest.json",
                    "planPath": "self-authored.plan.json",
                    "cleanupReceiptPath": "self-authored.receipt.json",
                    "cleanup_complete": True,
                },
            },
        )

        self.assertFalse(result["ok"], result)
        self.assertIn("worker_id_mismatch", result["errors"])
        self.assertIn("worker_result_contract_reference_mismatch", result["errors"])

    def test_validator_rejects_overlapping_worker_write_sets(self):
        from workflow_agent_task_contract import validate_agent_task_contract_text

        overlapping = VALID_CONTRACT.replace(
            VALID_WRITE_SET,
            "Allowed write set for worker `parser` only:\n"
            "- `dev/plugins/dev-flow/scripts/workflow_example.py`\n"
            "Allowed write set for worker `tests` only:\n"
            "- `dev/plugins/dev-flow/scripts/workflow_example.py`",
        )

        report = validate_agent_task_contract_text(overlapping)

        self.assertFalse(report["ok"])
        self.assertIn(
            "Write path overlap: `dev/plugins/dev-flow/scripts/workflow_example.py` "
            "is assigned to workers `parser` and `tests`.",
            report["errors"],
        )

    def test_validator_treats_parent_and_child_write_paths_as_overlapping(self):
        from workflow_agent_task_contract import validate_agent_task_contract_text

        overlapping = VALID_CONTRACT.replace(
            VALID_WRITE_SET,
            "Allowed write set for worker `scripts` only:\n"
            "- `dev/plugins/dev-flow/scripts`\n"
            "Allowed write set for worker `parser` only:\n"
            "- `dev/plugins/dev-flow/scripts/workflow_example.py`",
        )

        report = validate_agent_task_contract_text(overlapping)

        self.assertFalse(report["ok"])
        self.assertIn(
            "Write path overlap: `dev/plugins/dev-flow/scripts` is assigned to workers "
            "`scripts` and `parser`.",
            report["errors"],
        )

    def test_validator_reserves_shared_control_plane_paths_for_primary_agent(self):
        from workflow_agent_task_contract import validate_agent_task_contract_text

        worker_owns_openspec = VALID_CONTRACT.replace(
            VALID_WRITE_SET,
            "Allowed write set for worker `parser` only:\n"
            "- `openspec/changes/example/tasks.md`",
        )

        report = validate_agent_task_contract_text(worker_owns_openspec)

        self.assertFalse(report["ok"])
        self.assertIn(
            "Worker `parser` cannot own primary-managed path "
            "`openspec/changes/example/tasks.md`.",
            report["errors"],
        )

    def test_validator_reserves_generated_release_root_for_primary_agent(self):
        from workflow_agent_task_contract import validate_agent_task_contract_text

        worker_owns_release_root = VALID_CONTRACT.replace(
            VALID_WRITE_SET,
            "Allowed write set for worker `packager` only:\n- `plugins`",
        )

        report = validate_agent_task_contract_text(worker_owns_release_root)

        self.assertFalse(report["ok"])
        self.assertIn(
            "Worker `packager` cannot own primary-managed path `plugins`.",
            report["errors"],
        )

    def test_validator_reserves_nested_release_metadata_for_primary_agent(self):
        from workflow_agent_task_contract import validate_agent_task_contract_text

        worker_owns_metadata = VALID_CONTRACT.replace(
            VALID_WRITE_SET,
            "Allowed write set for worker `packager` only:\n"
            "- `dev/plugins/dev-flow/.codex-plugin/release-sync.json`",
        )

        report = validate_agent_task_contract_text(worker_owns_metadata)

        self.assertFalse(report["ok"])
        self.assertIn(
            "Worker `packager` cannot own primary-managed path "
            "`dev/plugins/dev-flow/.codex-plugin/release-sync.json`.",
            report["errors"],
        )

    def test_validator_rejects_write_paths_that_escape_repository_scope(self):
        from workflow_agent_task_contract import validate_agent_task_contract_text

        escaping_scope = VALID_CONTRACT.replace(
            VALID_WRITE_SET,
            "Allowed write set for worker `parser` only:\n- `../openspec/changes/example/tasks.md`",
        )

        report = validate_agent_task_contract_text(escaping_scope)

        self.assertFalse(report["ok"])
        self.assertIn(
            "Worker `parser` write path must be a normalized repository-relative path: "
            "`../openspec/changes/example/tasks.md`.",
            report["errors"],
        )

    def test_validator_rejects_glob_write_paths_before_overlap_analysis(self):
        from workflow_agent_task_contract import validate_agent_task_contract_text

        glob_scope = VALID_CONTRACT.replace(
            VALID_WRITE_SET,
            "Allowed write set for worker `parser` only:\n- `dev/plugins/dev-flow/**`",
        )

        report = validate_agent_task_contract_text(glob_scope)

        self.assertFalse(report["ok"])
        self.assertIn(
            "Worker `parser` write path must be a normalized repository-relative path: "
            "`dev/plugins/dev-flow/**`.",
            report["errors"],
        )

    def test_batch_validator_rejects_write_overlap_across_contracts(self):
        from workflow_agent_task_contract import validate_agent_task_contract_files

        root = Path(tempfile.mkdtemp(prefix="agent-contract-batch-"))
        parser_contract = root / "parser.md"
        tests_contract = root / "tests.md"
        parser_contract.write_text(
            VALID_CONTRACT.replace(
                VALID_WRITE_SET,
                "Allowed write set for worker `parser` only:\n"
                "- `dev/plugins/dev-flow/scripts/workflow_example.py`",
            )
        )
        tests_contract.write_text(
            VALID_CONTRACT.replace(
                VALID_WRITE_SET,
                "Allowed write set for worker `tests` only:\n"
                "- `dev/plugins/dev-flow/scripts/workflow_example.py`",
            )
        )

        report = validate_agent_task_contract_files([parser_contract, tests_contract])

        self.assertFalse(report["ok"])
        self.assertEqual(len(report["contracts"]), 2)
        self.assertEqual(
            report["overlaps"],
            [
                {
                    "path": "dev/plugins/dev-flow/scripts/workflow_example.py",
                    "owners": [
                        {"contract": str(parser_contract), "worker": "parser"},
                        {"contract": str(tests_contract), "worker": "tests"},
                    ],
                }
            ],
        )

    def test_validator_rejects_generic_unnamed_write_scope(self):
        from workflow_agent_task_contract import validate_agent_task_contract_text

        unnamed = VALID_CONTRACT.replace(
            VALID_WRITE_SET,
            "Allowed: modify `dev/plugins/dev-flow/scripts/workflow_example.py`.",
        )

        report = validate_agent_task_contract_text(unnamed)

        self.assertFalse(report["ok"])
        self.assertTrue(
            any("generic write ownership is not allowed" in error for error in report["errors"]),
            report,
        )

    def test_validator_rejects_hidden_write_intent_after_read_only_scope(self):
        from workflow_agent_task_contract import validate_agent_task_contract_text

        hidden_write = VALID_CONTRACT.replace(
            VALID_WRITE_SET,
            "Allowed read-only scope: inspect `dev/plugins/dev-flow/scripts`.\n"
            "Worker may modify `dev/plugins/dev-flow/scripts/workflow_example.py`.\n"
            "Forbidden: do not modify any other repository path.",
        )

        report = validate_agent_task_contract_text(hidden_write)

        self.assertFalse(report["ok"], report)
        self.assertIn(
            "Implementation scope must name a unique worker id for every write set.",
            report["errors"],
        )

    def test_validator_rejects_change_synonym_hidden_in_read_only_scope(self):
        from workflow_agent_task_contract import validate_agent_task_contract_text

        hidden_change = VALID_CONTRACT.replace(
            VALID_WRITE_SET,
            "Allowed read-only scope: inspect `dev/plugins/dev-flow/scripts`.\n"
            "Worker may change `dev/plugins/dev-flow/scripts/workflow_example.py`.\n"
            "Forbidden: do not modify any other repository path.",
        )

        report = validate_agent_task_contract_text(hidden_change)

        self.assertFalse(report["ok"], report)
        self.assertIn(
            "Implementation scope must name a unique worker id for every write set.",
            report["errors"],
        )

    def test_read_only_scope_must_forbid_all_not_merely_other_writes(self):
        from workflow_agent_task_contract import validate_agent_task_contract_text

        ambiguous = VALID_CONTRACT.replace(
            VALID_WRITE_SET,
            "Allowed read-only scope: inspect `dev/plugins/dev-flow/scripts`.\n"
            "Forbidden: do not modify any other repository path.",
        )

        report = validate_agent_task_contract_text(ambiguous)

        self.assertFalse(report["ok"], report)
        self.assertIn(
            "A contract without a named write set must explicitly forbid all repository writes.",
            report["errors"],
        )

    def test_batch_validator_rejects_duplicate_worker_ids_across_contracts(self):
        from workflow_agent_task_contract import validate_agent_task_contract_files

        root = Path(tempfile.mkdtemp(prefix="agent-contract-duplicate-worker-"))
        first = root / "first.md"
        second = root / "second.md"
        first.write_text(VALID_CONTRACT)
        second.write_text(
            VALID_CONTRACT.replace(
                "workflow_example.py", "workflow_other.py"
            ).replace("test_example.py", "test_other.py")
        )

        report = validate_agent_task_contract_files([first, second])

        self.assertFalse(report["ok"])
        self.assertEqual(set(report["duplicateWorkers"]), {"parser"})

    def test_validator_rejects_missing_forbidden_scope_and_vague_verification(self):
        from workflow_agent_task_contract import validate_agent_task_contract_text

        invalid = VALID_CONTRACT.replace(
            "Forbidden: do not modify release assets, OpenSpec files, `.planning/devflow/STATE.md`,\n"
            "or files outside the named write set.",
            "",
        ).replace(
            "Run `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest dev.plugins.dev-flow.tests.test_example`.",
            "Run tests as needed.",
        )

        report = validate_agent_task_contract_text(invalid)

        self.assertFalse(report["ok"])
        self.assertIn("Scope must include forbidden boundaries.", report["errors"])
        self.assertIn(
            "Verification must list concrete commands or a read-only/not-applicable rationale.",
            report["errors"],
        )

    def test_validator_allows_read_only_verification_rationale(self):
        from workflow_agent_task_contract import validate_agent_task_contract_text

        read_only = VALID_CONTRACT.replace(
            VALID_WRITE_SET,
            "Allowed read-only scope: inspect `dev/plugins/dev-flow/scripts`.\n"
            "Forbidden: do not modify any repository path.",
        ).replace(
            "Run `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest dev.plugins.dev-flow.tests.test_example`.",
            "Not applicable: this is a read-only explorer task; verify by reporting inspected files "
            "and residual risks.",
        )

        report = validate_agent_task_contract_text(read_only)

        self.assertTrue(report["ok"], report)

    def test_validator_rejects_anonymous_read_only_worker(self):
        from workflow_agent_task_contract import validate_agent_task_contract_text

        read_only = VALID_CONTRACT.replace(
            "## Worker ID\n`parser`\n\n",
            "",
        ).replace(
            VALID_WRITE_SET,
            "Allowed read-only scope: inspect `dev/plugins/dev-flow/scripts`.\n"
            "Forbidden: do not modify any repository path.",
        )

        report = validate_agent_task_contract_text(read_only)

        self.assertFalse(report["ok"])
        self.assertIn("Missing required section: Worker ID.", report["errors"])

    def test_validator_rejects_case_insensitive_primary_paths(self):
        from workflow_agent_task_contract import validate_agent_task_contract_text

        for protected in (
            "AGENT_TASK_CONTRACT.md",
            "OpenSpec/changes/example/tasks.md",
            "Plugins/dev-flow/README.md",
            "dev/plugins/dev-flow/.CODEX-PLUGIN/release-sync.json",
        ):
            with self.subTest(path=protected):
                report = validate_agent_task_contract_text(
                    VALID_CONTRACT.replace(
                        VALID_WRITE_SET,
                        f"Allowed write set for worker `parser` only:\n- `{protected}`",
                    )
                )
                self.assertFalse(report["ok"], report)
                self.assertTrue(
                    any("cannot own primary-managed path" in error for error in report["errors"]),
                    report,
                )

    def test_batch_validator_rejects_case_insensitive_worker_ids_and_paths(self):
        from workflow_agent_task_contract import validate_agent_task_contract_files

        root = Path(tempfile.mkdtemp(prefix="agent-contract-casefold-"))
        first = root / "first.md"
        second = root / "second.md"
        first.write_text(VALID_CONTRACT.replace("`parser`", "`Foo`").replace(
            "workflow_example.py", "Workflow_Example.py"
        ))
        second.write_text(VALID_CONTRACT.replace("`parser`", "`foo`").replace(
            "test_example.py", "test_other.py"
        ))

        report = validate_agent_task_contract_files([first, second])

        self.assertFalse(report["ok"])
        self.assertEqual(set(report["duplicateWorkers"]), {"Foo"})
        self.assertEqual(
            report["overlaps"][0]["path"].casefold(),
            "dev/plugins/dev-flow/scripts/workflow_example.py",
        )

    def test_cli_reports_json_failure_for_placeholder_contract(self):
        contract = Path(tempfile.mkdtemp(prefix="agent-contract-")) / "contract.md"
        contract.write_text(
            """# Agent Task Contract

## Goal
pending

## Scope
pending

## Constraints
pending

## Verification
pending

## Evidence
pending

## Human Gate
pending
"""
        )

        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "validate_agent_task_contract.py"), "--contract", str(contract), "--json"],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertIn("Goal contains placeholder content.", report["errors"])

    def test_cli_repeated_contract_flag_rejects_cross_contract_overlap(self):
        root = Path(tempfile.mkdtemp(prefix="agent-contract-cli-batch-"))
        first = root / "first.md"
        second = root / "second.md"
        for path, worker in ((first, "first"), (second, "second")):
            path.write_text(
                VALID_CONTRACT.replace(
                    VALID_WRITE_SET,
                    f"Allowed write set for worker `{worker}` only:\n"
                    "- `dev/plugins/dev-flow/scripts/workflow_example.py`",
                )
            )

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "validate_agent_task_contract.py"),
                "--contract",
                str(first),
                "--contract",
                str(second),
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertEqual(
            report["overlaps"][0]["path"],
            "dev/plugins/dev-flow/scripts/workflow_example.py",
        )


if __name__ == "__main__":
    unittest.main()
