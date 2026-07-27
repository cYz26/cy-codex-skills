import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
import zipfile
from copy import deepcopy
from pathlib import Path, PurePosixPath
from unittest.mock import patch


PLUGIN_ROOT = Path(
    os.environ.get("DEVFLOW_PLUGIN_ROOT", Path(__file__).resolve().parents[1])
).resolve()
SCRIPTS = PLUGIN_ROOT / "scripts"
RUNTIME_ARCHIVE = SCRIPTS / "devflow_runtime.pyz"
sys.path.insert(0, str(RUNTIME_ARCHIVE if RUNTIME_ARCHIVE.is_file() else SCRIPTS))


def runtime_source(relative):
    path = PLUGIN_ROOT / relative
    if path.is_file():
        return path.read_text()
    if RUNTIME_ARCHIVE.is_file() and relative.startswith("scripts/"):
        with zipfile.ZipFile(RUNTIME_ARCHIVE) as archive:
            return archive.read(relative.removeprefix("scripts/")).decode()
    raise FileNotFoundError(path)


class GeneratedArtifactLifecycleCharacterizationTests(unittest.TestCase):
    def test_existing_destructive_cleanup_requires_explicit_file_list_and_rollback(self):
        from workflow_side_effect_policy import (
            load_side_effect_policy,
            side_effect_decision,
        )

        cleanup_policy = load_side_effect_policy(PLUGIN_ROOT)["effects"][
            "destructive.cleanup"
        ]

        self.assertEqual(
            cleanup_policy,
            {
                "authorization": "explicit_file_list_and_rollback",
                "denial": "preserve_and_report",
            },
        )
        self.assertEqual(
            side_effect_decision(PLUGIN_ROOT, "destructive.cleanup", set()),
            {
                "effect": "destructive.cleanup",
                "authorized": False,
                "requiredAuthorization": "explicit_file_list_and_rollback",
                "denial": "preserve_and_report",
                "reason": "authorization_missing",
            },
        )

    def test_artifact_labels_do_not_grant_existing_cleanup_authority(self):
        from workflow_side_effect_policy import side_effect_decision

        non_authorizations = (
            "filename_tmp",
            "extension_log",
            "gitignored",
            "cache_directory",
            "build_output",
            "apparently_disposable",
        )

        for signal in non_authorizations:
            with self.subTest(signal=signal):
                decision = side_effect_decision(
                    PLUGIN_ROOT,
                    "destructive.cleanup",
                    {signal},
                )
                self.assertFalse(decision["authorized"], decision)
                self.assertEqual(decision["denial"], "preserve_and_report")


class GeneratedArtifactTestSupport:
    def make_repo(self):
        temporary = tempfile.TemporaryDirectory(prefix="dfga-", dir="/tmp")
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

    def prepare(self, repo, **overrides):
        from workflow_generated_artifacts import prepare_contract

        values = {
            "repo": repo,
            "task_id": "task-1",
            "run_id": "run-1",
            "owner_id": "main",
            "owner_pid": 999_999_999,
            "command": ["python3", "build.py", "--output", "artifact"],
            "isolated_roots": [".devflow-generated/task-1/run-1"],
            "adjacent_outputs": [],
            "retention": "cleanup",
            "contract_id": "contract-1",
            "now_ns": 1_700_000_000_000_000_000,
        }
        values.update(overrides)
        return prepare_contract(**values)

    def observe(self, repo, contract, *, exit_code=0):
        from workflow_generated_artifacts import observe_artifacts

        return observe_artifacts(
            repo,
            contract,
            exit_code=exit_code,
        )

    def create_isolated_output(self, repo, contract, name="build/output.bin", content=b"data"):
        root = repo / contract["scopes"][0]["path"]
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return target

    def reason_codes(self, plan):
        return [reason.split(":", 1)[0] for reason in plan["reasons"]]

    def impossible_identity_cases(self, manifest, file_path, directory_path):
        huge = 10**100
        return (
            ("boolean-integer", file_path, "device", True),
            ("negative-device", file_path, "device", -1),
            ("oversized-device", file_path, "device", huge),
            ("negative-inode", file_path, "inode", -1),
            ("oversized-inode", file_path, "inode", huge),
            ("negative-mode", file_path, "mode", -1),
            ("zero-link-count", file_path, "nlink", 0),
            ("negative-owner", file_path, "uid", -1),
            ("negative-group", file_path, "gid", -1),
            ("oversized-group", file_path, "gid", huge),
            ("negative-size", file_path, "size", -1),
            ("oversized-size", file_path, "size", huge),
            ("oversized-mtime", file_path, "mtimeNs", huge),
            (
                "identity-after-observation",
                file_path,
                "ctimeNs",
                manifest["observedAtNs"] + 1,
            ),
            ("file-without-digest", file_path, "sha256", None),
            ("file-with-members", file_path, "members", ["ghost"]),
            ("directory-with-digest", directory_path, "sha256", "0" * 64),
            ("directory-with-unbound-member", directory_path, "members", ["ghost"]),
        )


class GeneratedArtifactContractTests(GeneratedArtifactTestSupport, unittest.TestCase):
    def load_lifecycle_schemas(self):
        schema_root = PLUGIN_ROOT / "schemas"
        return (
            json.loads(
                (schema_root / "generated-artifact-contract.schema.json").read_text()
            ),
            json.loads(
                (schema_root / "generated-artifact-manifest.schema.json").read_text()
            ),
            json.loads(
                (
                    schema_root
                    / "generated-artifact-cleanup-receipt.schema.json"
                ).read_text()
            ),
        )

    def assert_contract_schema_identity_types(self, contract_schema):
        identifier = {
            "type": "string",
            "minLength": 1,
            "maxLength": 128,
            "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]*$",
        }
        sha256 = {
            "type": "string",
            "pattern": "^[0-9a-f]{64}$",
        }
        self.assertEqual(contract_schema["$defs"]["identifier"], identifier)
        self.assertEqual(contract_schema["$defs"]["sha256"], sha256)
        for field in ("contractId", "taskId", "runId"):
            self.assertEqual(
                contract_schema["properties"][field],
                {"$ref": "#/$defs/identifier"},
            )
        self.assertEqual(
            contract_schema["$defs"]["identity"]["properties"]["sha256"],
            {
                "oneOf": [
                    {"$ref": "#/$defs/sha256"},
                    {"type": "null"},
                ]
            },
        )
        self.assertEqual(
            len(contract_schema["$defs"]["isolatedBeforeState"]["allOf"]),
            2,
        )

    def assert_read_only_cli_and_guidance(self, decisions):
        cli_source = (SCRIPTS / "generated_artifact_lifecycle.py").read_text()
        for writer in ("write_text(", "write_bytes(", "atomic_write"):
            self.assertNotIn(writer, cli_source)
        for surface in (
            PLUGIN_ROOT / "README.md",
            PLUGIN_ROOT / "docs" / "generated-artifact-lifecycle.md",
            PLUGIN_ROOT / "assets" / "templates" / "AGENTS.md.template",
            PLUGIN_ROOT / "skills" / "project-orchestrator" / "SKILL.md",
        ):
            text = surface.read_text()
            for decision in decisions:
                self.assertIn(decision, text, f"{decision} missing from {surface}")
            self.assertNotIn("Generated Artifact Task Queue", text)

    def test_versioned_schema_documents_are_strict_and_complete(self):
        schema_root = PLUGIN_ROOT / "schemas"
        expected = {
            "generated-artifact-contract.schema.json":
                "generated-artifact-contract/v1",
            "generated-artifact-manifest.schema.json":
                "generated-artifact-manifest/v1",
            "generated-artifact-cleanup-receipt.schema.json":
                "generated-artifact-cleanup-receipt/v1",
        }

        for filename, schema_id in expected.items():
            with self.subTest(filename=filename):
                document = json.loads((schema_root / filename).read_text())
                self.assertEqual(document["$id"], schema_id)
                self.assertEqual(document["type"], "object")
                self.assertFalse(document["additionalProperties"])
                self.assertTrue(document["required"])

    def test_identity_schemas_encode_file_and_directory_semantics(self):
        contract_schema, manifest_schema, _receipt_schema = (
            self.load_lifecycle_schemas()
        )
        definitions = (
            contract_schema["$defs"]["identity"],
            manifest_schema["$defs"]["identity"],
            manifest_schema["$defs"]["manifestEntry"],
        )

        for definition in definitions:
            with self.subTest(title=definition.get("title")):
                os_scalar_max = 18_446_744_073_709_551_615
                timestamp_min = -9_223_372_036_854_775_808
                timestamp_max = 9_223_372_036_854_775_807
                variants = definition["allOf"][0]["oneOf"]
                self.assertEqual(
                    [variant["properties"]["type"] for variant in variants],
                    [
                        {"const": "file"},
                        {"const": "directory"},
                        {
                            "enum": [
                                "symlink",
                                "socket",
                                "fifo",
                                "device",
                                "other",
                            ]
                        },
                    ],
                )
                self.assertEqual(variants[0]["properties"]["members"], {"maxItems": 0})
                self.assertEqual(variants[1]["properties"]["sha256"], {"type": "null"})
                self.assertEqual(variants[2]["properties"]["members"], {"maxItems": 0})
                for field in ("device", "inode", "uid", "gid", "size"):
                    self.assertEqual(
                        definition["properties"][field],
                        {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": os_scalar_max,
                        },
                    )
                self.assertEqual(
                    definition["properties"]["mode"],
                    {"type": "integer", "minimum": 0, "maximum": 4095},
                )
                self.assertEqual(
                    definition["properties"]["nlink"],
                    {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": os_scalar_max,
                    },
                )
                for field in ("mtimeNs", "ctimeNs"):
                    self.assertEqual(
                        definition["properties"][field],
                        {
                            "type": "integer",
                            "minimum": timestamp_min,
                            "maximum": timestamp_max,
                        },
                    )

        self.assertEqual(
            contract_schema["properties"]["sealedAtNs"]["maximum"],
            timestamp_max,
        )
        self.assertEqual(
            manifest_schema["properties"]["observedAtNs"]["maximum"],
            timestamp_max,
        )

    def test_static_schema_guidance_and_cli_contracts_stay_consistent(self):
        from workflow_generated_artifacts import (
            CONTRACT_FIELDS,
            DECISIONS,
            MANIFEST_FIELDS,
            RECEIPT_FIELDS,
        )

        contract_schema, manifest_schema, receipt_schema = (
            self.load_lifecycle_schemas()
        )

        self.assertEqual(set(contract_schema["required"]), CONTRACT_FIELDS)
        self.assertEqual(set(manifest_schema["required"]), MANIFEST_FIELDS)
        self.assertEqual(set(receipt_schema["required"]), RECEIPT_FIELDS)
        for name in (
            "repository",
            "manifestOwner",
            "commandResult",
            "manifestEntry",
            "scopeInventory",
            "identity",
        ):
            self.assertFalse(
                manifest_schema["$defs"][name]["additionalProperties"],
                name,
            )
        self.assertFalse(
            receipt_schema["$defs"]["effects"]["additionalProperties"]
        )
        self.assertFalse(
            receipt_schema["$defs"]["failure"]["additionalProperties"]
        )
        self.assertEqual(
            set(receipt_schema["properties"]["decision"]["enum"]),
            set(DECISIONS),
        )
        self.assert_contract_schema_identity_types(contract_schema)
        self.assert_read_only_cli_and_guidance(DECISIONS)

    def test_prepare_binds_repository_task_run_owner_and_command(self):
        repo = self.make_repo()

        contract = self.prepare(repo)

        self.assertEqual(contract["schema"], "generated-artifact-contract/v1")
        self.assertEqual(contract["contractId"], "contract-1")
        self.assertEqual(contract["taskId"], "task-1")
        self.assertEqual(contract["runId"], "run-1")
        self.assertEqual(contract["owner"]["id"], "main")
        self.assertEqual(contract["owner"]["pid"], 999_999_999)
        self.assertEqual(contract["owner"]["uid"], os.getuid())
        self.assertEqual(
            contract["owner"]["processStartToken"],
            "absent-at-contract-seal",
        )
        self.assertEqual(contract["repository"]["root"], str(repo.resolve()))
        self.assertEqual(
            contract["command"]["sha256"],
            hashlib.sha256(
                json.dumps(
                    ["python3", "build.py", "--output", "artifact"],
                    separators=(",", ":"),
                ).encode()
            ).hexdigest(),
        )

    def test_prepare_records_absent_and_empty_isolated_root_baselines(self):
        repo = self.make_repo()

        absent = self.prepare(repo)
        empty_root = repo / ".devflow-generated" / "task-2" / "run-2"
        empty_root.mkdir(parents=True)
        empty = self.prepare(
            repo,
            task_id="task-2",
            run_id="run-2",
            contract_id="contract-2",
            isolated_roots=[".devflow-generated/task-2/run-2"],
        )

        self.assertEqual(absent["scopes"][0]["beforeState"]["state"], "absent")
        self.assertEqual(empty["scopes"][0]["beforeState"]["state"], "empty")
        self.assertEqual(empty["scopes"][0]["beforeState"]["members"], [])

    def test_prepare_rejects_nonempty_isolated_root(self):
        from workflow_generated_artifacts import GeneratedArtifactError

        repo = self.make_repo()
        output = repo / ".devflow-generated" / "task-1" / "run-1"
        output.mkdir(parents=True)
        (output / "preexisting.log").write_text("user data\n")

        with self.assertRaisesRegex(GeneratedArtifactError, "isolated_root_not_empty"):
            self.prepare(repo)

    def test_prepare_adjacent_scope_captures_complete_before_state(self):
        repo = self.make_repo()
        source = repo / "src"
        source.mkdir()
        (source / "existing.pyc").write_bytes(b"old")
        (source / "keep.txt").write_text("keep\n")

        contract = self.prepare(
            repo,
            isolated_roots=[],
            adjacent_outputs=[{"parent": "src", "pattern": "**/*.pyc"}],
        )

        scope = contract["scopes"][0]
        self.assertEqual(scope["kind"], "adjacent_output")
        self.assertEqual(scope["pattern"], "**/*.pyc")
        self.assertEqual(
            [entry["path"] for entry in scope["beforeState"]["entries"]],
            ["src/existing.pyc", "src/keep.txt"],
        )

    def test_prepare_records_retention_policy(self):
        repo = self.make_repo()

        contract = self.prepare(repo, retention="retain")

        self.assertEqual(contract["retention"], "retain")

    def test_contract_validator_rejects_missing_unknown_and_malformed_fields(self):
        from workflow_generated_artifacts import validate_contract

        repo = self.make_repo()
        contract = self.prepare(repo)
        contract.pop("taskId")
        contract["inferredFromExtension"] = True
        contract["owner"]["pid"] = "not-an-integer"

        errors = validate_contract(repo, contract)

        self.assertIn("missing_field:taskId", errors)
        self.assertIn("unknown_field:inferredFromExtension", errors)
        self.assertIn("invalid_owner_pid", errors)

    def test_owner_pid_bounds_are_os_call_safe(self):
        from workflow_generated_artifacts import (
            pid_alive,
            validate_contract,
            validate_manifest,
        )

        repo = self.make_repo()
        contract = self.prepare(repo)
        manifest = self.observe(repo, contract)
        too_large = 2_147_483_648
        contract["owner"]["pid"] = too_large
        manifest["owner"]["pid"] = too_large
        contract_schema, manifest_schema, _receipt_schema = (
            self.load_lifecycle_schemas()
        )

        self.assertIn("invalid_owner_pid", validate_contract(repo, contract))
        self.assertIn("invalid_owner_pid", validate_manifest(repo, manifest))
        self.assertEqual(
            contract_schema["$defs"]["owner"]["properties"]["pid"]["maximum"],
            too_large - 1,
        )
        self.assertEqual(
            manifest_schema["$defs"]["manifestOwner"]["properties"]["pid"][
                "maximum"
            ],
            too_large - 1,
        )
        self.assertTrue(pid_alive(too_large))

    def test_process_start_token_is_timezone_stable(self):
        from workflow_generated_artifacts import process_start_token

        with patch.dict(os.environ, {"TZ": "UTC"}, clear=False):
            utc_token = process_start_token(os.getpid())
        with patch.dict(os.environ, {"TZ": "Asia/Shanghai"}, clear=False):
            shanghai_token = process_start_token(os.getpid())

        self.assertIsNotNone(utc_token)
        self.assertEqual(utc_token, shanghai_token)

    def test_contract_validator_rejects_malformed_lease_and_unbound_baselines(self):
        from workflow_generated_artifacts import capture_identity, validate_contract

        repo = self.make_repo()
        lease = repo / "owner.lease"
        lease.write_text("active\n")
        leased = self.prepare(repo, lease_path="owner.lease")
        misbound_lease = deepcopy(leased)
        misbound_lease["owner"]["lease"]["identity"]["path"] = "other.lease"
        leased["owner"]["lease"]["identity"] = {"path": "owner.lease"}

        empty_root = repo / ".devflow-generated" / "task-2" / "run-2"
        empty_root.mkdir(parents=True)
        isolated = self.prepare(
            repo,
            task_id="task-2",
            run_id="run-2",
            contract_id="contract-2",
            isolated_roots=[".devflow-generated/task-2/run-2"],
        )
        misbound_isolated = deepcopy(isolated)
        other_empty = repo / "other-empty"
        other_empty.mkdir()
        fraudulent_identity = capture_identity(repo, other_empty)
        fraudulent_identity["path"] = isolated["scopes"][0]["path"]
        misbound_isolated["scopes"][0]["beforeState"]["identity"] = (
            fraudulent_identity
        )
        nonempty = repo / "nonempty"
        nonempty.mkdir()
        (nonempty / "user-data").write_text("preserve\n")
        nonempty_isolated = deepcopy(isolated)
        nonempty_identity = capture_identity(repo, nonempty)
        nonempty_identity["path"] = isolated["scopes"][0]["path"]
        nonempty_isolated["scopes"][0]["beforeState"]["identity"] = (
            nonempty_identity
        )
        isolated["scopes"][0]["beforeState"]["identity"]["path"] = "other-root"

        source = repo / "src"
        source.mkdir()
        baseline = source / "existing.pyc"
        baseline.write_bytes(b"old")
        adjacent = self.prepare(
            repo,
            task_id="task-3",
            run_id="run-3",
            contract_id="contract-3",
            isolated_roots=[],
            adjacent_outputs=[{"parent": "src", "pattern": "**/*.pyc"}],
        )
        adjacent["scopes"][0]["beforeState"]["parentIdentity"]["path"] = "other"
        adjacent["scopes"][0]["beforeState"]["entries"][0]["path"] = "outside.pyc"

        self.assertIn("invalid_owner_lease_identity", validate_contract(repo, leased))
        self.assertIn(
            "owner_lease_identity_path_mismatch",
            validate_contract(repo, misbound_lease),
        )
        self.assertIn(
            "isolated_baseline_identity_mismatch:isolated-1",
            validate_contract(repo, isolated),
        )
        self.assertIn(
            "isolated_baseline_identity_drift:isolated-1",
            validate_contract(repo, misbound_isolated),
        )
        self.assertIn(
            "isolated_baseline_not_empty:isolated-1",
            validate_contract(repo, nonempty_isolated),
        )
        adjacent_errors = validate_contract(repo, adjacent)
        self.assertIn(
            "adjacent_baseline_identity_mismatch:adjacent-1",
            adjacent_errors,
        )
        self.assertIn("adjacent_baseline_scope_escape:adjacent-1", adjacent_errors)

    def test_manifest_and_receipt_validators_reject_unknown_or_unbound_documents(self):
        from workflow_generated_artifacts import (
            validate_manifest,
            validate_receipt,
        )

        repo = self.make_repo()
        contract, manifest, plan, receipt = self.empty_lifecycle_documents(repo)

        self.assertEqual(validate_manifest(repo, manifest, contract=contract), [])
        self.assertEqual(
            validate_receipt(
                receipt,
                contract=contract,
                manifest=manifest,
                plan=plan,
            ),
            [],
        )

        malformed_manifest = deepcopy(manifest)
        malformed_manifest["owner"]["processAlive"] = "unknown"
        malformed_manifest["inferredCandidates"] = ["artifact.log"]
        manifest_errors = validate_manifest(
            repo,
            malformed_manifest,
            contract=contract,
        )
        self.assertIn("invalid_owner_process_alive", manifest_errors)
        self.assertIn("unknown_field:inferredCandidates", manifest_errors)

        malformed_receipt = deepcopy(receipt)
        malformed_receipt["contractSha256"] = "0" * 64
        malformed_receipt["effects"]["git"] = True
        receipt_errors = validate_receipt(
            malformed_receipt,
            contract=contract,
            manifest=manifest,
            plan=plan,
        )
        self.assertIn("receipt_contract_mismatch", receipt_errors)
        self.assertIn("receipt_unlisted_effect:git", receipt_errors)

    def empty_lifecycle_documents(self, repo):
        from workflow_generated_artifacts import AUTO_CLEAN, document_sha256

        contract = self.prepare(repo)
        manifest = {
            "schema": "generated-artifact-manifest/v1",
            "contractSha256": document_sha256(contract),
            "observedAtNs": contract["sealedAtNs"] + 1,
            "repository": contract["repository"],
            "taskId": contract["taskId"],
            "runId": contract["runId"],
            "owner": {
                "id": contract["owner"]["id"],
                "pid": contract["owner"]["pid"],
                "uid": contract["owner"]["uid"],
                "processAlive": False,
                "leaseActive": False,
                "completed": True,
            },
            "commandResult": {"exitCode": 0, "completed": True},
            "entries": [],
            "scopeInventories": [{"scopeId": "isolated-1", "entries": []}],
        }
        plan = {
            "schema": "generated-artifact-cleanup-plan/v1",
            "contractSha256": document_sha256(contract),
            "manifestSha256": document_sha256(manifest),
            "decision": AUTO_CLEAN,
            "reasons": ["all_invariants_pass"],
            "entries": [],
            "retained": [],
        }
        receipt = {
            "schema": "generated-artifact-cleanup-receipt/v1",
            "contractSha256": document_sha256(contract),
            "manifestSha256": document_sha256(manifest),
            "planSha256": document_sha256(plan),
            "decision": AUTO_CLEAN,
            "status": "complete",
            "removed": [],
            "remaining": [],
            "absent": [],
            "retained": [],
            "zeroUnlistedMutation": True,
            "effects": {
                "process": False,
                "configuration": False,
                "git": False,
                "network": False,
            },
            "failure": None,
        }
        return contract, manifest, plan, receipt

    def test_manifest_and_plan_bind_every_observed_candidate(self):
        from workflow_generated_artifacts import (
            validate_manifest,
            validate_plan,
        )

        repo = self.make_repo()
        contract = self.prepare(repo)
        self.create_isolated_output(repo, contract)
        manifest = self.observe(repo, contract)

        omitted_manifest = deepcopy(manifest)
        omitted_manifest["entries"] = []
        self.assertIn(
            "manifest_candidate_coverage_mismatch",
            validate_manifest(repo, omitted_manifest, contract=contract),
        )

        plan = {
            "schema": "generated-artifact-cleanup-plan/v1",
            "contractSha256": manifest["contractSha256"],
            "manifestSha256": hashlib.sha256(
                (
                    json.dumps(manifest, sort_keys=True, indent=2)
                    + "\n"
                ).encode()
            ).hexdigest(),
            "decision": "AUTO_CLEAN",
            "reasons": ["all_invariants_pass"],
            "entries": [],
            "retained": [],
        }
        self.assertIn(
            "plan_entries_manifest_mismatch",
            validate_plan(plan, contract=contract, manifest=manifest),
        )


class GeneratedArtifactDecisionTests(GeneratedArtifactTestSupport, unittest.TestCase):
    def test_auto_clean_wait_owner_and_retain_decisions(self):
        from workflow_generated_artifacts import (
            AUTO_CLEAN,
            RETAIN,
            WAIT_OWNER,
            plan_cleanup,
        )

        repo = self.make_repo()
        cleanup_contract = self.prepare(repo)
        self.create_isolated_output(repo, cleanup_contract)
        cleanup_manifest = self.observe(repo, cleanup_contract)

        waiting_contract = self.prepare(
            repo,
            task_id="task-2",
            run_id="run-2",
            contract_id="contract-2",
            owner_pid=os.getpid(),
            isolated_roots=[".devflow-generated/task-2/run-2"],
        )
        self.create_isolated_output(repo, waiting_contract)
        waiting_manifest = self.observe(repo, waiting_contract)

        retained_contract = self.prepare(
            repo,
            task_id="task-3",
            run_id="run-3",
            contract_id="contract-3",
            retention="retain",
            isolated_roots=[".devflow-generated/task-3/run-3"],
        )
        self.create_isolated_output(repo, retained_contract)
        retained_manifest = self.observe(repo, retained_contract)

        self.assertEqual(
            plan_cleanup(repo, cleanup_contract, cleanup_manifest)["decision"],
            AUTO_CLEAN,
        )
        self.assertEqual(
            plan_cleanup(repo, waiting_contract, waiting_manifest)["decision"],
            WAIT_OWNER,
        )
        self.assertEqual(
            plan_cleanup(repo, retained_contract, retained_manifest)["decision"],
            RETAIN,
        )

    def test_unregistered_and_preexisting_candidates_require_human_gate(self):
        from workflow_generated_artifacts import (
            HUMAN_GATE,
            capture_identity,
            plan_cleanup,
        )

        repo = self.make_repo()
        source = repo / "src"
        source.mkdir()
        existing = source / "existing.pyc"
        existing.write_bytes(b"old")
        contract = self.prepare(
            repo,
            isolated_roots=[],
            adjacent_outputs=[{"parent": "src", "pattern": "**/*.pyc"}],
        )
        manifest = self.observe(repo, contract)
        manifest["entries"] = [
            {"scopeId": "adjacent-1", **capture_identity(repo, existing)}
        ]

        unregistered = plan_cleanup(
            repo,
            None,
            None,
            candidates=["cache/output.tmp"],
        )
        preexisting = plan_cleanup(repo, contract, manifest)

        self.assertEqual(unregistered["decision"], HUMAN_GATE)
        self.assertIn("unregistered_contract", self.reason_codes(unregistered))
        self.assertEqual(preexisting["decision"], HUMAN_GATE)
        self.assertIn("preexisting_path", self.reason_codes(preexisting))

    def test_tracked_protected_shared_and_external_scopes_require_human_gate(self):
        from workflow_generated_artifacts import (
            HUMAN_GATE,
            document_sha256,
            plan_cleanup,
        )

        repo = self.make_repo()
        contract = self.prepare(repo)
        target = self.create_isolated_output(repo, contract)
        subprocess.run(
            ["git", "add", target.relative_to(repo).as_posix()],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
        manifest = self.observe(repo, contract)
        tracked = plan_cleanup(repo, contract, manifest)

        protected_contract = deepcopy(contract)
        protected_contract["scopes"][0]["path"] = ".planning/devflow/generated"
        protected_manifest = deepcopy(manifest)
        protected_manifest["contractSha256"] = document_sha256(protected_contract)
        protected = plan_cleanup(repo, protected_contract, protected_manifest)

        shared_contract = deepcopy(contract)
        shared_contract["scopes"][0]["shared"] = True
        shared_manifest = deepcopy(manifest)
        shared_manifest["contractSha256"] = document_sha256(shared_contract)
        shared = plan_cleanup(repo, shared_contract, shared_manifest)

        external_contract = deepcopy(contract)
        external_contract["scopes"][0]["path"] = "../outside"
        external_manifest = deepcopy(manifest)
        external_manifest["contractSha256"] = document_sha256(external_contract)
        external = plan_cleanup(repo, external_contract, external_manifest)

        for plan, reason in (
            (tracked, "tracked_path"),
            (protected, "protected_scope"),
            (shared, "shared_scope"),
            (external, "invalid_scope_path"),
        ):
            with self.subTest(reason=reason):
                self.assertEqual(plan["decision"], HUMAN_GATE, plan)
                self.assertIn(reason, self.reason_codes(plan), plan)

    def test_filesystem_case_aliases_preserve_protected_and_tracked_state(self):
        from workflow_generated_artifacts import (
            AUTO_CLEAN,
            GeneratedArtifactError,
            HUMAN_GATE,
            plan_cleanup,
        )

        repo = self.make_repo()
        case_insensitive = (repo / ".GIT").exists()
        (repo / ".planning").mkdir()
        if case_insensitive:
            with self.assertRaisesRegex(GeneratedArtifactError, "protected_scope"):
                self.prepare(
                    repo,
                    isolated_roots=[],
                    adjacent_outputs=[
                        {"parent": ".PLANNING", "pattern": "**/*.tmp"}
                    ],
                )
        else:
            (repo / ".PLANNING").mkdir()
            self.prepare(
                repo,
                isolated_roots=[],
                adjacent_outputs=[{"parent": ".PLANNING", "pattern": "**/*.tmp"}],
            )

        source = repo / "src"
        source.mkdir()
        tracked = source / "tracked.tmp"
        tracked.write_text("baseline")
        subprocess.run(
            ["git", "add", "src/tracked.tmp"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
        tracked.unlink()
        contract = self.prepare(
            repo,
            task_id="task-2",
            run_id="run-2",
            contract_id="contract-2",
            isolated_roots=[],
            adjacent_outputs=[{"parent": "src", "pattern": "**/*.tmp"}],
        )
        alias = source / "TRACKED.tmp"
        alias.write_text("generated")
        manifest = self.observe(repo, contract)
        plan = plan_cleanup(repo, contract, manifest)

        if case_insensitive:
            self.assertEqual(plan["decision"], HUMAN_GATE, plan)
            self.assertIn("tracked_path", self.reason_codes(plan), plan)
        else:
            self.assertEqual(plan["decision"], AUTO_CLEAN, plan)

        overlap = {
            "isolated_roots": ["CaseRoot", "caseroot"],
            "adjacent_outputs": [],
            "task_id": "task-3",
            "run_id": "run-3",
            "contract_id": "contract-3",
        }
        if case_insensitive:
            with self.assertRaisesRegex(GeneratedArtifactError, "overlapping_scopes"):
                self.prepare(repo, **overlap)
        else:
            self.prepare(repo, **overlap)

    def test_nested_git_subdirectory_inherits_case_alias_protection(self):
        from workflow_generated_artifacts import (
            GeneratedArtifactError,
            HUMAN_GATE,
            apply_cleanup,
            filesystem_case_insensitive,
            plan_cleanup,
        )

        root = self.make_repo()
        repo = root / "project"
        source = repo / "src"
        source.mkdir(parents=True)
        case_insensitive = (root / ".GIT").exists()
        self.assertEqual(filesystem_case_insensitive(repo), case_insensitive)
        if not case_insensitive:
            return

        (repo / ".planning").mkdir()
        with self.assertRaisesRegex(GeneratedArtifactError, "protected_scope"):
            self.prepare(
                repo,
                isolated_roots=[],
                adjacent_outputs=[
                    {"parent": ".PLANNING", "pattern": "**/*.tmp"}
                ],
            )
        with self.assertRaisesRegex(GeneratedArtifactError, "overlapping_scopes"):
            self.prepare(
                repo,
                isolated_roots=["CaseRoot", "caseroot"],
                adjacent_outputs=[],
            )

        tracked = source / "tracked.tmp"
        tracked.write_text("baseline")
        subprocess.run(
            ["git", "add", "project/src/tracked.tmp"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        tracked.unlink()
        contract = self.prepare(
            repo,
            task_id="task-2",
            run_id="run-2",
            contract_id="contract-2",
            isolated_roots=[],
            adjacent_outputs=[{"parent": "src", "pattern": "**/*.tmp"}],
        )
        alias = source / "TRACKED.tmp"
        alias.write_text("generated")
        manifest = self.observe(repo, contract)
        plan = plan_cleanup(repo, contract, manifest)
        receipt = apply_cleanup(repo, contract, manifest, plan)

        self.assertEqual(plan["decision"], HUMAN_GATE, plan)
        self.assertIn("tracked_path", self.reason_codes(plan), plan)
        self.assertEqual(receipt["status"], "blocked", receipt)
        self.assertTrue(alias.exists())

    def test_unicode_normalization_aliases_preserve_tracked_state(self):
        from workflow_generated_artifacts import (
            HUMAN_GATE,
            path_comparison_key,
            plan_cleanup,
        )

        repo = self.make_repo()
        source = repo / "src"
        source.mkdir()
        composed = "src/\u00e9.tmp"
        decomposed = "src/e\u0301.tmp"
        self.assertEqual(
            path_comparison_key(repo, composed),
            path_comparison_key(repo, decomposed),
        )
        tracked = repo / composed
        tracked.write_text("baseline")
        subprocess.run(
            ["git", "add", composed],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
        tracked.unlink()
        contract = self.prepare(
            repo,
            isolated_roots=[],
            adjacent_outputs=[{"parent": "src", "pattern": "**/*.tmp"}],
        )
        (repo / decomposed).write_text("generated")
        manifest = self.observe(repo, contract)
        plan = plan_cleanup(repo, contract, manifest)

        self.assertEqual(plan["decision"], HUMAN_GATE, plan)
        self.assertIn("tracked_path", self.reason_codes(plan), plan)

    def test_foreign_owner_symlink_and_hardlink_require_human_gate(self):
        from workflow_generated_artifacts import (
            HUMAN_GATE,
            document_sha256,
            plan_cleanup,
        )

        repo = self.make_repo()
        owner_contract = self.prepare(repo)
        self.create_isolated_output(repo, owner_contract)
        owner_manifest = self.observe(repo, owner_contract)
        owner_contract["owner"]["uid"] = os.getuid() + 1
        owner_manifest["owner"]["uid"] = owner_contract["owner"]["uid"]
        owner_manifest["contractSha256"] = document_sha256(owner_contract)

        symlink_contract = self.prepare(
            repo,
            task_id="task-2",
            run_id="run-2",
            contract_id="contract-2",
            isolated_roots=[".devflow-generated/task-2/run-2"],
        )
        symlink_root = repo / symlink_contract["scopes"][0]["path"]
        symlink_root.mkdir(parents=True)
        (symlink_root / "link").symlink_to("/tmp")
        symlink_manifest = self.observe(repo, symlink_contract)

        hardlink_contract = self.prepare(
            repo,
            task_id="task-3",
            run_id="run-3",
            contract_id="contract-3",
            isolated_roots=[".devflow-generated/task-3/run-3"],
        )
        first = self.create_isolated_output(repo, hardlink_contract, "first.bin")
        os.link(first, first.with_name("second.bin"))
        hardlink_manifest = self.observe(repo, hardlink_contract)

        for plan, reason in (
            (plan_cleanup(repo, owner_contract, owner_manifest), "owner_uid_mismatch"),
            (plan_cleanup(repo, symlink_contract, symlink_manifest), "symlink_path"),
            (plan_cleanup(repo, hardlink_contract, hardlink_manifest), "hardlink_path"),
        ):
            with self.subTest(reason=reason):
                self.assertEqual(plan["decision"], HUMAN_GATE, plan)
                self.assertIn(reason, self.reason_codes(plan), plan)

    def test_identity_and_directory_membership_drift_require_human_gate(self):
        from workflow_generated_artifacts import HUMAN_GATE, plan_cleanup

        repo = self.make_repo()
        identity_contract = self.prepare(repo)
        target = self.create_isolated_output(repo, identity_contract)
        identity_manifest = self.observe(repo, identity_contract)
        target.write_bytes(b"changed after observation")

        membership_contract = self.prepare(
            repo,
            task_id="task-2",
            run_id="run-2",
            contract_id="contract-2",
            isolated_roots=[".devflow-generated/task-2/run-2"],
        )
        self.create_isolated_output(repo, membership_contract)
        membership_manifest = self.observe(repo, membership_contract)
        root = repo / membership_contract["scopes"][0]["path"]
        (root / "unlisted.log").write_text("late\n")

        identity_plan = plan_cleanup(repo, identity_contract, identity_manifest)
        membership_plan = plan_cleanup(
            repo,
            membership_contract,
            membership_manifest,
        )

        self.assertEqual(identity_plan["decision"], HUMAN_GATE)
        self.assertIn("identity_drift", self.reason_codes(identity_plan))
        self.assertEqual(membership_plan["decision"], HUMAN_GATE)
        self.assertTrue(
            {"membership_drift", "unlisted_scope_entry"}
            & set(self.reason_codes(membership_plan)),
            membership_plan,
        )

    def test_live_lease_identity_drift_requires_human_gate(self):
        from workflow_generated_artifacts import HUMAN_GATE, plan_cleanup

        repo = self.make_repo()
        lease = repo / "owner.lease"
        lease.write_text("original\n")
        contract = self.prepare(repo, lease_path="owner.lease")
        self.create_isolated_output(repo, contract)
        lease.write_text("changed\n")
        manifest = self.observe(repo, contract)

        plan = plan_cleanup(repo, contract, manifest)

        self.assertEqual(plan["decision"], HUMAN_GATE, plan)
        self.assertIn("lease_identity_drift", self.reason_codes(plan))


class GeneratedArtifactInspectionTests(GeneratedArtifactTestSupport, unittest.TestCase):
    def write_lifecycle_document(self, repo, name, document):
        from workflow_generated_artifacts import canonical_document_bytes

        root = repo / ".planning" / "devflow" / "generated-artifacts"
        root.mkdir(parents=True, exist_ok=True)
        path = root / name
        path.write_bytes(canonical_document_bytes(document))
        return path

    def write_decision_cases(self, repo, plan_cleanup):
        cases = []
        for index, (retention, owner_pid) in enumerate(
            (
                ("cleanup", 999_999_991),
                ("cleanup", os.getpid()),
                ("retain", 999_999_993),
                ("cleanup", 999_999_994),
            ),
            1,
        ):
            contract = self.prepare(
                repo,
                task_id=f"task-{index}",
                run_id=f"run-{index}",
                contract_id=f"contract-{index}",
                owner_pid=owner_pid,
                isolated_roots=[f".devflow-generated/task-{index}/run-{index}"],
                retention=retention,
            )
            artifact = self.create_isolated_output(repo, contract)
            if index == 4:
                subprocess.run(
                    ["git", "add", artifact.relative_to(repo).as_posix()],
                    cwd=repo,
                    check=True,
                    capture_output=True,
                    text=True,
                )
            manifest = self.observe(repo, contract)
            plan = plan_cleanup(repo, contract, manifest)
            self.write_lifecycle_document(
                repo,
                f"case-{index}.contract.json",
                contract,
            )
            self.write_lifecycle_document(
                repo,
                f"case-{index}.manifest.json",
                manifest,
            )
            self.write_lifecycle_document(repo, f"case-{index}.plan.json", plan)
            cases.append((artifact, plan["decision"]))
        return cases

    def assert_decision_routes(self, inspection):
        decisions = {
            record["contractId"]: (
                record["decision"],
                record["nextAction"],
            )
            for record in inspection["records"]
        }
        self.assertEqual(decisions["contract-1"][0], "AUTO_CLEAN")
        self.assertIn("`cleanup --apply`", decisions["contract-1"][1])
        self.assertEqual(decisions["contract-2"][0], "WAIT_OWNER")
        self.assertIn("owning process or lease to exit", decisions["contract-2"][1])
        self.assertEqual(decisions["contract-3"][0], "RETAIN")
        self.assertIn("do not apply cleanup", decisions["contract-3"][1])
        self.assertEqual(decisions["contract-4"][0], "HUMAN_GATE")
        self.assertIn("resolve the Human Gate", decisions["contract-4"][1])
        self.assertFalse(inspection["ok"])

    def assert_surfaces_are_read_only(self):
        for relative in (
            "scripts/workflow_validate.py",
            "scripts/workflow_doctor.py",
            "scripts/devflow_stop_hook.py",
            "scripts/stop_verification_policy.py",
            "scripts/check_review_gate.py",
            "scripts/workflow_hooks.py",
        ):
            self.assertNotIn(
                "apply_cleanup(",
                runtime_source(relative),
                relative,
            )

    def test_read_only_surfaces_report_every_decision_and_exact_next_action(self):
        from check_review_gate import generated_artifact_review_status
        from devflow_stop_hook import generated_artifact_stop_check
        from workflow_doctor import doctor_workflow
        from workflow_generated_artifacts import (
            inspect_generated_artifact_lifecycle,
            plan_cleanup,
        )
        from workflow_validate import validate_workflow_state

        repo = self.make_repo()
        cases = self.write_decision_cases(repo, plan_cleanup)

        inspection = inspect_generated_artifact_lifecycle(repo)
        self.assert_decision_routes(inspection)

        validation = validate_workflow_state(repo)
        doctor = doctor_workflow(repo)
        stop = generated_artifact_stop_check(repo)
        review = generated_artifact_review_status(repo)

        self.assertEqual(validation["generatedArtifacts"], inspection)
        self.assertEqual(doctor["generatedArtifacts"], inspection)
        self.assertFalse(stop["ok"])
        self.assertEqual(stop["nextActions"], inspection["nextActions"])
        self.assertFalse(review["ok"])
        self.assertEqual(review["generatedArtifacts"], inspection)
        for artifact, _decision in cases:
            self.assertTrue(artifact.exists())
        self.assert_surfaces_are_read_only()

    def test_terminal_receipt_resolves_inspection_without_replaying_mutation(self):
        from workflow_generated_artifacts import (
            apply_cleanup,
            inspect_generated_artifact_lifecycle,
            plan_cleanup,
            validate_terminal_cleanup,
        )

        repo = self.make_repo()
        contract = self.prepare(repo)
        artifact = self.create_isolated_output(repo, contract)
        manifest = self.observe(repo, contract)
        plan = plan_cleanup(repo, contract, manifest)
        receipt = apply_cleanup(repo, contract, manifest, plan)
        for name, document in (
            ("terminal.contract.json", contract),
            ("terminal.manifest.json", manifest),
            ("terminal.plan.json", plan),
            ("terminal.receipt.json", receipt),
        ):
            self.write_lifecycle_document(repo, name, document)

        inspection = inspect_generated_artifact_lifecycle(repo)

        self.assertTrue(inspection["ok"], inspection)
        self.assertEqual(inspection["status"], "complete")
        self.assertEqual(inspection["records"][0]["status"], "complete")
        self.assertIn(
            "retain the terminal cleanup receipt",
            inspection["records"][0]["nextAction"],
        )
        self.assertFalse(artifact.exists())

        retained_receipt = deepcopy(receipt)
        retained_receipt["retained"] = list(plan["entries"])
        self.assertIn(
            "terminal_receipt_retained_mismatch",
            validate_terminal_cleanup(
                repo,
                contract,
                manifest,
                plan,
                retained_receipt,
            ),
        )

    def test_terminal_cleanup_rejects_auto_clean_for_retained_contract(self):
        from workflow_generated_artifacts import (
            AUTO_CLEAN,
            cleanup_receipt,
            document_sha256,
            validate_terminal_cleanup,
        )

        repo = self.make_repo()
        contract = self.prepare(repo, retention="retain")
        manifest = self.observe(repo, contract)
        forged_plan = {
            "schema": "generated-artifact-cleanup-plan/v1",
            "contractSha256": document_sha256(contract),
            "manifestSha256": document_sha256(manifest),
            "decision": AUTO_CLEAN,
            "reasons": ["all_invariants_pass"],
            "entries": [],
            "retained": [],
        }
        forged_receipt = cleanup_receipt(
            contract,
            manifest,
            forged_plan,
            decision=AUTO_CLEAN,
            status="complete",
            removed=[],
            remaining=[],
            failure=None,
        )

        errors = validate_terminal_cleanup(
            repo,
            contract,
            manifest,
            forged_plan,
            forged_receipt,
        )

        self.assertIn("plan:plan_decision_contract_mismatch", errors)
        self.assertIn("plan:plan_reasons_contract_mismatch", errors)

    def test_terminal_cleanup_rejects_forged_manifest_owner_binding(self):
        from workflow_generated_artifacts import (
            AUTO_CLEAN,
            cleanup_receipt,
            document_sha256,
            validate_terminal_cleanup,
        )

        repo = self.make_repo()
        contract = self.prepare(repo)
        manifest = self.observe(repo, contract)
        manifest["owner"]["id"] = "forged"
        forged_plan = {
            "schema": "generated-artifact-cleanup-plan/v1",
            "contractSha256": document_sha256(contract),
            "manifestSha256": document_sha256(manifest),
            "decision": AUTO_CLEAN,
            "reasons": ["all_invariants_pass"],
            "entries": [],
            "retained": [],
        }
        forged_receipt = cleanup_receipt(
            contract,
            manifest,
            forged_plan,
            decision=AUTO_CLEAN,
            status="complete",
            removed=[],
            remaining=[],
            failure=None,
        )

        errors = validate_terminal_cleanup(
            repo,
            contract,
            manifest,
            forged_plan,
            forged_receipt,
        )

        self.assertIn("manifest:owner_binding_mismatch:id", errors)
        self.assertIn("plan:plan_decision_contract_mismatch", errors)

    def test_terminal_cleanup_rechecks_live_owner_after_manifest_forgery(self):
        from workflow_generated_artifacts import (
            AUTO_CLEAN,
            cleanup_receipt,
            document_sha256,
            manifest_paths,
            validate_terminal_cleanup,
        )

        repo = self.make_repo()
        contract = self.prepare(repo, owner_pid=os.getpid())
        artifact = self.create_isolated_output(repo, contract)
        manifest = self.observe(repo, contract)
        self.assertTrue(manifest["owner"]["processAlive"])
        artifact.unlink()
        artifact.parent.rmdir()
        (repo / contract["scopes"][0]["path"]).rmdir()

        forged_manifest = deepcopy(manifest)
        forged_manifest["owner"].update(
            {
                "processAlive": False,
                "leaseActive": False,
                "completed": True,
            }
        )
        entries = manifest_paths(forged_manifest)
        forged_plan = {
            "schema": "generated-artifact-cleanup-plan/v1",
            "contractSha256": document_sha256(contract),
            "manifestSha256": document_sha256(forged_manifest),
            "decision": AUTO_CLEAN,
            "reasons": ["all_invariants_pass"],
            "entries": entries,
            "retained": [],
        }
        forged_receipt = cleanup_receipt(
            contract,
            forged_manifest,
            forged_plan,
            decision=AUTO_CLEAN,
            status="complete",
            removed=entries,
            remaining=[],
            failure=None,
        )

        errors = validate_terminal_cleanup(
            repo,
            contract,
            forged_manifest,
            forged_plan,
            forged_receipt,
        )

        self.assertIn("plan:plan_decision_contract_mismatch", errors)

    def test_successful_replay_ignores_reused_owner_process_identity(self):
        from workflow_generated_artifacts import (
            apply_cleanup,
            plan_cleanup,
            successful_replay,
            validate_terminal_cleanup,
        )

        repo = self.make_repo()
        with (
            patch("workflow_generated_artifacts.pid_alive", return_value=True),
            patch(
                "workflow_generated_artifacts.process_start_token",
                return_value="owner-incarnation",
            ),
        ):
            contract = self.prepare(repo)
        self.assertEqual(
            contract["owner"]["processStartToken"],
            "owner-incarnation",
        )
        self.create_isolated_output(repo, contract)
        manifest = self.observe(repo, contract)
        plan = plan_cleanup(repo, contract, manifest)
        receipt = apply_cleanup(repo, contract, manifest, plan)
        self.assertEqual(receipt["status"], "complete", receipt)

        with (
            patch("workflow_generated_artifacts.pid_alive", return_value=True),
            patch(
                "workflow_generated_artifacts.process_start_token",
                return_value="replacement-incarnation",
            ),
        ):
            self.assertEqual(
                validate_terminal_cleanup(
                    repo,
                    contract,
                    manifest,
                    plan,
                    receipt,
                ),
                [],
            )
            self.assertTrue(
                successful_replay(repo, contract, manifest, plan, receipt)
            )
            self.assertEqual(
                apply_cleanup(
                    repo,
                    contract,
                    manifest,
                    plan,
                    prior_receipt=receipt,
                ),
                receipt,
            )

    def test_terminal_cleanup_rejects_forged_recorded_safety_invariant(self):
        from workflow_generated_artifacts import (
            AUTO_CLEAN,
            apply_cleanup,
            cleanup_receipt,
            document_sha256,
            plan_cleanup,
            validate_terminal_cleanup,
        )

        repo = self.make_repo()
        contract = self.prepare(repo)
        artifact = self.create_isolated_output(repo, contract)
        manifest = self.observe(repo, contract)
        canonical_plan = plan_cleanup(repo, contract, manifest)
        self.assertEqual(
            apply_cleanup(repo, contract, manifest, canonical_plan)["status"],
            "complete",
        )

        forged_manifest = deepcopy(manifest)
        artifact_path = artifact.relative_to(repo).as_posix()
        for entry in forged_manifest["entries"]:
            if entry["path"] == artifact_path:
                entry["nlink"] = 2
        for inventory in forged_manifest["scopeInventories"]:
            for entry in inventory["entries"]:
                if entry["path"] == artifact_path:
                    entry["nlink"] = 2
        forged_plan = {
            "schema": "generated-artifact-cleanup-plan/v1",
            "contractSha256": document_sha256(contract),
            "manifestSha256": document_sha256(forged_manifest),
            "decision": AUTO_CLEAN,
            "reasons": ["all_invariants_pass"],
            "entries": canonical_plan["entries"],
            "retained": [],
        }
        forged_receipt = cleanup_receipt(
            contract,
            forged_manifest,
            forged_plan,
            decision=AUTO_CLEAN,
            status="complete",
            removed=forged_plan["entries"],
            remaining=[],
            failure=None,
        )

        errors = validate_terminal_cleanup(
            repo,
            contract,
            forged_manifest,
            forged_plan,
            forged_receipt,
        )

        self.assertIn("plan:plan_decision_contract_mismatch", errors)
        self.assertIn("plan:plan_reasons_contract_mismatch", errors)

    def test_terminal_cleanup_rejects_tracked_artifact_after_external_deletion(self):
        from workflow_generated_artifacts import (
            AUTO_CLEAN,
            cleanup_receipt,
            document_sha256,
            ordered_removal_entries,
            remove_exact_entry,
            validate_terminal_cleanup,
        )

        repo = self.make_repo()
        contract = self.prepare(repo)
        artifact = self.create_isolated_output(repo, contract)
        subprocess.run(
            ["git", "add", artifact.relative_to(repo).as_posix()],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
        manifest = self.observe(repo, contract)
        for entry in ordered_removal_entries(manifest["entries"]):
            remove_exact_entry(repo, entry)
        forged_plan = {
            "schema": "generated-artifact-cleanup-plan/v1",
            "contractSha256": document_sha256(contract),
            "manifestSha256": document_sha256(manifest),
            "decision": AUTO_CLEAN,
            "reasons": ["all_invariants_pass"],
            "entries": [entry["path"] for entry in manifest["entries"]],
            "retained": [],
        }
        forged_receipt = cleanup_receipt(
            contract,
            manifest,
            forged_plan,
            decision=AUTO_CLEAN,
            status="complete",
            removed=forged_plan["entries"],
            remaining=[],
            failure=None,
        )

        errors = validate_terminal_cleanup(
            repo,
            contract,
            manifest,
            forged_plan,
            forged_receipt,
        )

        self.assertIn("plan:plan_decision_contract_mismatch", errors)
        self.assertIn("plan:plan_reasons_contract_mismatch", errors)

    def test_terminal_validation_fails_closed_on_malformed_policy_documents(self):
        from workflow_generated_artifacts import (
            AUTO_CLEAN,
            cleanup_receipt,
            document_sha256,
            validate_terminal_cleanup,
        )

        repo = self.make_repo()
        contract = self.prepare(repo)
        manifest = self.observe(repo, contract)
        malformed_contract = deepcopy(contract)
        malformed_contract["scopes"] = None
        forged_plan = {
            "schema": "generated-artifact-cleanup-plan/v1",
            "contractSha256": document_sha256(malformed_contract),
            "manifestSha256": document_sha256(manifest),
            "decision": AUTO_CLEAN,
            "reasons": ["all_invariants_pass"],
            "entries": [],
            "retained": [],
        }
        forged_receipt = cleanup_receipt(
            malformed_contract,
            manifest,
            forged_plan,
            decision=AUTO_CLEAN,
            status="complete",
            removed=[],
            remaining=[],
            failure=None,
        )

        errors = validate_terminal_cleanup(
            repo,
            malformed_contract,
            manifest,
            forged_plan,
            forged_receipt,
        )

        self.assertIn("contract:invalid_scopes", errors)

        malformed_manifest = deepcopy(manifest)
        malformed_manifest["owner"]["id"] = "forged"
        malformed_plan = {
            **forged_plan,
            "contractSha256": document_sha256(contract),
            "manifestSha256": document_sha256(malformed_manifest),
            "reasons": [{}],
        }
        malformed_receipt = cleanup_receipt(
            contract,
            malformed_manifest,
            malformed_plan,
            decision=AUTO_CLEAN,
            status="complete",
            removed=[],
            remaining=[],
            failure=None,
        )

        malformed_errors = validate_terminal_cleanup(
            repo,
            contract,
            malformed_manifest,
            malformed_plan,
            malformed_receipt,
        )

        self.assertIn("plan:invalid_plan_reasons", malformed_errors)
        self.assertIn("plan:plan_reasons_contract_mismatch", malformed_errors)

    def test_terminal_validation_fails_closed_on_nonstring_retention(self):
        from workflow_generated_artifacts import (
            AUTO_CLEAN,
            cleanup_receipt,
            document_sha256,
            validate_terminal_cleanup,
        )

        repo = self.make_repo()
        contract = self.prepare(repo)
        manifest = self.observe(repo, contract)
        for retention in ([], {}):
            with self.subTest(retention=retention):
                malformed_contract = deepcopy(contract)
                malformed_contract["retention"] = retention
                forged_plan = {
                    "schema": "generated-artifact-cleanup-plan/v1",
                    "contractSha256": document_sha256(malformed_contract),
                    "manifestSha256": document_sha256(manifest),
                    "decision": AUTO_CLEAN,
                    "reasons": ["all_invariants_pass"],
                    "entries": [],
                    "retained": [],
                }
                forged_receipt = cleanup_receipt(
                    malformed_contract,
                    manifest,
                    forged_plan,
                    decision=AUTO_CLEAN,
                    status="complete",
                    removed=[],
                    remaining=[],
                    failure=None,
                )

                errors = validate_terminal_cleanup(
                    repo,
                    malformed_contract,
                    manifest,
                    forged_plan,
                    forged_receipt,
                )

                self.assertIn("contract:invalid_retention", errors)

    def test_terminal_validation_structures_malformed_nested_json_values(self):
        from workflow_generated_artifacts import (
            cleanup_receipt,
            plan_cleanup,
            validate_terminal_cleanup,
        )

        repo = self.make_repo()
        contract = self.prepare(repo)
        self.create_isolated_output(repo, contract)
        manifest = self.observe(repo, contract)
        plan = plan_cleanup(repo, contract, manifest)
        receipt = cleanup_receipt(
            contract,
            manifest,
            plan,
            decision=plan["decision"],
            status="complete",
            removed=plan["entries"],
            remaining=[],
            failure=None,
        )
        cases = (
            ("receipt-status", ((3, ("status",)),), "receipt:invalid_receipt_status"),
            (
                "isolated-before-state",
                ((0, ("scopes", 0, "beforeState", "state")),),
                "contract:invalid_before_state:",
            ),
            (
                "manifest-identity-type",
                ((1, ("entries", 0, "type")),),
                "manifest:invalid_manifest_entry:",
            ),
            (
                "manifest-entry-scope",
                ((1, ("entries", 0, "scopeId")),),
                "manifest:invalid_manifest_scope:",
            ),
            (
                "scope-inventory-binding",
                (
                    (0, ("scopes", 0, "scopeId")),
                    (1, ("scopeInventories", 0, "scopeId")),
                ),
                "manifest:manifest_scope_inventory_mismatch",
            ),
            ("plan-entries", ((2, ("entries", 0)),), "plan:invalid_plan_entries"),
            ("plan-retained", ((2, ("retained",)),), "plan:invalid_plan_retained"),
        )

        for malformed_value in ([], {}):
            for label, changes, expected_prefix in cases:
                with self.subTest(label=label, malformed_value=malformed_value):
                    documents = deepcopy([contract, manifest, plan, receipt])
                    for document_index, path in changes:
                        target = documents[document_index]
                        for segment in path[:-1]:
                            target = target[segment]
                        target[path[-1]] = (
                            [deepcopy(malformed_value)]
                            if label == "plan-retained"
                            else deepcopy(malformed_value)
                        )

                    errors = validate_terminal_cleanup(repo, *documents)

                    self.assertTrue(
                        any(error.startswith(expected_prefix) for error in errors),
                        errors,
                    )

    def test_retained_policy_structures_malformed_plan_decision(self):
        from workflow_generated_artifacts import (
            cleanup_receipt,
            plan_cleanup,
            validate_terminal_cleanup,
        )

        repo = self.make_repo()
        contract = self.prepare(repo, retention="retain")
        manifest = self.observe(repo, contract)
        plan = plan_cleanup(repo, contract, manifest)
        receipt = cleanup_receipt(
            contract,
            manifest,
            plan,
            decision=plan["decision"],
            status="complete",
            removed=[],
            remaining=[],
            failure=None,
        )

        for malformed_value in ([], {}):
            with self.subTest(malformed_value=malformed_value):
                malformed_plan = deepcopy(plan)
                malformed_plan["decision"] = malformed_value

                errors = validate_terminal_cleanup(
                    repo,
                    contract,
                    manifest,
                    malformed_plan,
                    receipt,
                )

                self.assertIn("plan:invalid_plan_decision", errors)

    def test_terminal_validation_rejects_impossible_identity_semantics(self):
        from workflow_generated_artifacts import (
            AUTO_CLEAN,
            apply_cleanup,
            cleanup_receipt,
            document_sha256,
            plan_cleanup,
            validate_terminal_cleanup,
        )

        repo = self.make_repo()
        contract = self.prepare(repo)
        artifact = self.create_isolated_output(repo, contract)
        manifest = self.observe(repo, contract)
        canonical_plan = plan_cleanup(repo, contract, manifest)
        self.assertEqual(
            apply_cleanup(repo, contract, manifest, canonical_plan)["status"],
            "complete",
        )
        file_path = artifact.relative_to(repo).as_posix()
        directory_path = next(
            entry["path"]
            for entry in manifest["entries"]
            if entry["type"] == "directory"
        )
        cases = self.impossible_identity_cases(
            manifest,
            file_path,
            directory_path,
        )

        for label, path, field, value in cases:
            with self.subTest(label=label):
                forged_manifest = deepcopy(manifest)
                collections = [forged_manifest["entries"]]
                collections.extend(
                    inventory["entries"]
                    for inventory in forged_manifest["scopeInventories"]
                )
                for entries in collections:
                    for entry in entries:
                        if entry["path"] == path:
                            entry[field] = value
                forged_plan = {
                    "schema": "generated-artifact-cleanup-plan/v1",
                    "contractSha256": document_sha256(contract),
                    "manifestSha256": document_sha256(forged_manifest),
                    "decision": AUTO_CLEAN,
                    "reasons": ["all_invariants_pass"],
                    "entries": canonical_plan["entries"],
                    "retained": [],
                }
                forged_receipt = cleanup_receipt(
                    contract,
                    forged_manifest,
                    forged_plan,
                    decision=AUTO_CLEAN,
                    status="complete",
                    removed=forged_plan["entries"],
                    remaining=[],
                    failure=None,
                )

                errors = validate_terminal_cleanup(
                    repo,
                    contract,
                    forged_manifest,
                    forged_plan,
                    forged_receipt,
                )

                self.assertTrue(
                    any(error.startswith("manifest:invalid_") for error in errors),
                    errors,
                )

    def test_terminal_validation_rejects_precontract_observation(self):
        from workflow_generated_artifacts import (
            cleanup_receipt,
            document_sha256,
            plan_cleanup,
            validate_terminal_cleanup,
        )

        repo = self.make_repo()
        contract = self.prepare(repo)
        manifest = self.observe(repo, contract)
        manifest["observedAtNs"] = contract["sealedAtNs"] - 1
        plan = plan_cleanup(repo, contract, manifest)
        plan["manifestSha256"] = document_sha256(manifest)
        receipt = cleanup_receipt(
            contract,
            manifest,
            plan,
            decision=plan["decision"],
            status="complete",
            removed=[],
            remaining=[],
            failure=None,
        )

        errors = validate_terminal_cleanup(repo, contract, manifest, plan, receipt)

        self.assertIn("manifest:manifest_observed_before_contract", errors)

    def test_terminal_validation_rejects_non_directory_isolated_root(self):
        from workflow_generated_artifacts import (
            AUTO_CLEAN,
            apply_cleanup,
            cleanup_receipt,
            document_sha256,
            plan_cleanup,
            validate_terminal_cleanup,
        )

        repo = self.make_repo()
        contract = self.prepare(repo)
        root_path = contract["scopes"][0]["path"]
        (repo / root_path).mkdir(parents=True)
        manifest = self.observe(repo, contract)
        canonical_plan = plan_cleanup(repo, contract, manifest)
        self.assertEqual(
            apply_cleanup(repo, contract, manifest, canonical_plan)["status"],
            "complete",
        )
        forged_manifest = deepcopy(manifest)
        collections = [forged_manifest["entries"]]
        collections.extend(
            inventory["entries"]
            for inventory in forged_manifest["scopeInventories"]
        )
        for entries in collections:
            for entry in entries:
                if entry["path"] == root_path:
                    entry["type"] = "file"
                    entry["nlink"] = 1
                    entry["sha256"] = "0" * 64
                    entry["members"] = []
        forged_plan = {
            "schema": "generated-artifact-cleanup-plan/v1",
            "contractSha256": document_sha256(contract),
            "manifestSha256": document_sha256(forged_manifest),
            "decision": AUTO_CLEAN,
            "reasons": ["all_invariants_pass"],
            "entries": canonical_plan["entries"],
            "retained": [],
        }
        forged_receipt = cleanup_receipt(
            contract,
            forged_manifest,
            forged_plan,
            decision=AUTO_CLEAN,
            status="complete",
            removed=forged_plan["entries"],
            remaining=[],
            failure=None,
        )

        errors = validate_terminal_cleanup(
            repo,
            contract,
            forged_manifest,
            forged_plan,
            forged_receipt,
        )

        self.assertTrue(
            any(
                error.startswith("manifest:manifest_scope_inventory_structure:")
                for error in errors
            ),
            errors,
        )

    def test_json_integer_fields_reject_booleans(self):
        from workflow_generated_artifacts import (
            validate_contract,
            validate_manifest,
        )

        repo = self.make_repo()
        contract = self.prepare(repo)
        manifest = self.observe(repo, contract)
        malformed_contract = deepcopy(contract)
        malformed_contract["owner"]["uid"] = True
        malformed_contract["repository"]["device"] = True
        malformed_manifest = deepcopy(manifest)
        malformed_manifest["owner"]["uid"] = False
        malformed_manifest["repository"]["inode"] = False

        contract_errors = validate_contract(repo, malformed_contract)
        manifest_errors = validate_manifest(repo, malformed_manifest)

        self.assertIn("invalid_owner_uid", contract_errors)
        self.assertIn("invalid_repository_device", contract_errors)
        self.assertIn("invalid_owner_uid", manifest_errors)
        self.assertIn("invalid_repository_inode", manifest_errors)

    def test_issue_only_registry_reports_a_human_gate_next_action(self):
        from devflow_stop_hook import generated_artifact_stop_check
        from workflow_generated_artifacts import inspect_generated_artifact_lifecycle

        repo = self.make_repo()
        self.write_lifecycle_document(
            repo,
            "unknown.json",
            {"schema": "unknown-generated-artifact-document/v1"},
        )

        inspection = inspect_generated_artifact_lifecycle(repo)
        stop = generated_artifact_stop_check(repo)

        self.assertEqual(inspection["status"], "invalid")
        self.assertFalse(inspection["ok"])
        self.assertEqual(
            inspection["nextActions"],
            ["Record the failed invariants and resolve the Human Gate before any cleanup."],
        )
        self.assertEqual(stop["nextActions"], inspection["nextActions"])

    def test_forged_subset_plan_and_receipt_cannot_hide_remaining_artifacts(self):
        from workflow_generated_artifacts import (
            AUTO_CLEAN,
            cleanup_receipt,
            document_sha256,
            inspect_generated_artifact_lifecycle,
            validate_terminal_cleanup,
        )

        repo = self.make_repo()
        contract = self.prepare(repo)
        artifact = self.create_isolated_output(repo, contract)
        manifest = self.observe(repo, contract)
        forged_plan = {
            "schema": "generated-artifact-cleanup-plan/v1",
            "contractSha256": document_sha256(contract),
            "manifestSha256": document_sha256(manifest),
            "decision": AUTO_CLEAN,
            "reasons": ["all_invariants_pass"],
            "entries": [],
            "retained": [],
        }
        forged_receipt = cleanup_receipt(
            contract,
            manifest,
            forged_plan,
            decision=AUTO_CLEAN,
            status="complete",
            removed=[],
            remaining=[],
            failure=None,
        )

        terminal_errors = validate_terminal_cleanup(
            repo,
            contract,
            manifest,
            forged_plan,
            forged_receipt,
        )
        self.assertIn("plan:plan_entries_manifest_mismatch", terminal_errors)
        self.assertTrue(
            any(
                error.startswith("generated_artifact_remaining:")
                for error in terminal_errors
            ),
            terminal_errors,
        )

        for name, document in (
            ("forged.contract.json", contract),
            ("forged.manifest.json", manifest),
            ("forged.plan.json", forged_plan),
            ("forged.receipt.json", forged_receipt),
        ):
            self.write_lifecycle_document(repo, name, document)
        inspection = inspect_generated_artifact_lifecycle(repo)

        self.assertFalse(inspection["ok"], inspection)
        self.assertEqual(inspection["records"][0]["status"], "unresolved")
        self.assertTrue(artifact.exists())


class GeneratedArtifactCleanupTests(GeneratedArtifactTestSupport, unittest.TestCase):
    def ready_cleanup(self, repo, *, files=("build/output.bin",)):
        from workflow_generated_artifacts import plan_cleanup

        contract = self.prepare(repo)
        for index, name in enumerate(files):
            self.create_isolated_output(
                repo,
                contract,
                name,
                f"payload-{index}".encode(),
            )
        manifest = self.observe(repo, contract)
        plan = plan_cleanup(repo, contract, manifest)
        return contract, manifest, plan

    def test_cleanup_removes_only_exact_entries_and_directories_deepest_first(self):
        from workflow_generated_artifacts import (
            apply_cleanup,
            remove_exact_entry,
            validate_receipt,
        )

        repo = self.make_repo()
        user_file = repo / "user-owned.txt"
        user_file.write_text("preserve\n")
        contract, manifest, plan = self.ready_cleanup(
            repo,
            files=("build/output.bin", "spool/deep/item.log"),
        )
        removal_order = []

        def recording_remover(root, entry):
            removal_order.append(entry["path"])
            remove_exact_entry(root, entry)

        receipt = apply_cleanup(
            repo,
            contract,
            manifest,
            plan,
            remover=recording_remover,
        )

        self.assertEqual(receipt["status"], "complete", receipt)
        self.assertEqual(receipt["decision"], "AUTO_CLEAN")
        self.assertEqual(receipt["removed"], sorted(plan["entries"]))
        self.assertEqual(receipt["remaining"], [])
        self.assertEqual(receipt["absent"], sorted(plan["entries"]))
        self.assertTrue(receipt["zeroUnlistedMutation"])
        self.assertEqual(
            receipt["effects"],
            {
                "process": False,
                "configuration": False,
                "git": False,
                "network": False,
            },
        )
        self.assertEqual(
            validate_receipt(
                receipt,
                contract=contract,
                manifest=manifest,
                plan=plan,
            ),
            [],
        )
        self.assertTrue(user_file.exists())
        self.assertFalse((repo / contract["scopes"][0]["path"]).exists())

        entries = {entry["path"]: entry for entry in manifest["entries"]}
        first_directory = next(
            index
            for index, path in enumerate(removal_order)
            if entries[path]["type"] == "directory"
        )
        self.assertTrue(
            all(
                entries[path]["type"] != "directory"
                for path in removal_order[:first_directory]
            )
        )
        directory_depths = [
            len(PurePosixPath(path).parts)
            for path in removal_order[first_directory:]
        ]
        self.assertEqual(directory_depths, sorted(directory_depths, reverse=True))

    def test_preflight_drift_causes_zero_mutation_and_does_not_follow_symlink(self):
        from workflow_generated_artifacts import apply_cleanup

        repo = self.make_repo()
        contract, manifest, plan = self.ready_cleanup(
            repo,
            files=("a.bin", "b.bin"),
        )
        root = repo / contract["scopes"][0]["path"]
        (root / "a.bin").write_bytes(b"changed")

        drift_receipt = apply_cleanup(repo, contract, manifest, plan)

        self.assertEqual(drift_receipt["status"], "blocked", drift_receipt)
        self.assertEqual(drift_receipt["removed"], [])
        self.assertTrue((root / "a.bin").exists())
        self.assertTrue((root / "b.bin").exists())

        symlink_repo = self.make_repo()
        symlink_contract, symlink_manifest, symlink_plan = self.ready_cleanup(
            symlink_repo,
            files=("output.bin",),
        )
        outside = symlink_repo / "outside.txt"
        outside.write_text("must survive\n")
        target = (
            symlink_repo
            / symlink_contract["scopes"][0]["path"]
            / "output.bin"
        )
        target.unlink()
        target.symlink_to(outside)

        symlink_receipt = apply_cleanup(
            symlink_repo,
            symlink_contract,
            symlink_manifest,
            symlink_plan,
        )

        self.assertEqual(symlink_receipt["status"], "blocked", symlink_receipt)
        self.assertEqual(symlink_receipt["removed"], [])
        self.assertTrue(target.is_symlink())
        self.assertEqual(outside.read_text(), "must survive\n")

    def test_success_receipt_replay_is_idempotent(self):
        from workflow_generated_artifacts import apply_cleanup

        repo = self.make_repo()
        contract, manifest, plan = self.ready_cleanup(repo)

        first = apply_cleanup(repo, contract, manifest, plan)
        replay = apply_cleanup(
            repo,
            contract,
            manifest,
            plan,
            prior_receipt=first,
        )

        self.assertEqual(first["status"], "complete", first)
        self.assertEqual(replay, first)

    def test_orchestrator_only_routes_fresh_auto_clean_after_owner_exit(self):
        from workflow_continuation import generated_artifact_orchestration

        repo = self.make_repo()
        contract, manifest, plan = self.ready_cleanup(repo)
        target = repo / "devflow-generated-placeholder"
        artifact = repo / plan["entries"][0]

        routed = generated_artifact_orchestration(
            repo,
            contract,
            manifest,
            plan,
        )

        self.assertEqual(routed["decision"], "AUTO_CLEAN", routed)
        self.assertEqual(
            routed["action"],
            "APPLY_GENERATED_ARTIFACT_CLEANUP",
        )
        self.assertTrue(routed["applyAllowed"])
        self.assertTrue(routed["requiresExplicitApply"])
        self.assertTrue(routed["receiptRequired"])
        self.assertTrue(artifact.exists())
        self.assertFalse(target.exists())

        active_contract = self.prepare(
            repo,
            task_id="task-2",
            run_id="run-2",
            contract_id="contract-2",
            owner_pid=os.getpid(),
            isolated_roots=[".devflow-generated/task-2/run-2"],
        )
        active_artifact = self.create_isolated_output(repo, active_contract)
        active_manifest = self.observe(repo, active_contract)
        waiting = generated_artifact_orchestration(
            repo,
            active_contract,
            active_manifest,
            None,
        )

        self.assertEqual(waiting["decision"], "WAIT_OWNER", waiting)
        self.assertEqual(waiting["action"], "WAIT_OWNER")
        self.assertFalse(waiting["applyAllowed"])
        self.assertTrue(active_artifact.exists())

        stale_plan = dict(plan)
        stale_plan["reasons"] = ["self_authored"]
        stale = generated_artifact_orchestration(
            repo,
            contract,
            manifest,
            stale_plan,
        )
        self.assertEqual(stale["action"], "AWAIT_HUMAN")
        self.assertFalse(stale["applyAllowed"])
        self.assertIn("stale_or_self_authored_plan", stale["reasons"])

    def test_main_task_evidence_retains_terminal_cleanup_receipt(self):
        from workflow_generated_artifacts import (
            apply_cleanup,
            canonical_document_bytes,
        )

        repo = self.make_repo()
        contract, manifest, plan = self.ready_cleanup(repo)
        receipt = apply_cleanup(repo, contract, manifest, plan)
        lifecycle_root = repo / ".planning" / "devflow" / "generated-artifacts"
        lifecycle_root.mkdir(parents=True)
        paths = {
            "contract": lifecycle_root / "task-1-run-1.contract.json",
            "manifest": lifecycle_root / "task-1-run-1.manifest.json",
            "plan": lifecycle_root / "task-1-run-1.plan.json",
            "receipt": lifecycle_root / "task-1-run-1.receipt.json",
        }
        for label, document in (
            ("contract", contract),
            ("manifest", manifest),
            ("plan", plan),
            ("receipt", receipt),
        ):
            paths[label].write_bytes(canonical_document_bytes(document))

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "record_task_evidence.py"),
                "--repo",
                str(repo),
                "--task-id",
                "task-1",
                "--claim",
                "Generated output was reclaimed under its sealed contract.",
                "--generated-artifact-contract",
                paths["contract"].relative_to(repo).as_posix(),
                "--generated-artifact-manifest",
                paths["manifest"].relative_to(repo).as_posix(),
                "--generated-artifact-plan",
                paths["plan"].relative_to(repo).as_posix(),
                "--generated-artifact-cleanup-receipt",
                paths["receipt"].relative_to(repo).as_posix(),
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        evidence = Path(report["path"]).read_text()
        self.assertIn("## Generated Artifact Lifecycle", evidence)
        self.assertIn("G41: `passed`", evidence)
        self.assertIn("cleanup_complete: `true`", evidence)
        self.assertIn(paths["receipt"].relative_to(repo).as_posix(), evidence)

    def test_partial_operating_system_failure_stops_and_records_remaining_entries(self):
        from workflow_generated_artifacts import apply_cleanup, remove_exact_entry

        repo = self.make_repo()
        contract, manifest, plan = self.ready_cleanup(
            repo,
            files=("a.bin", "b.bin", "c.bin"),
        )
        attempted = []

        def fail_on_second_file(root, entry):
            attempted.append(entry["path"])
            if entry["path"].endswith("/b.bin"):
                raise OSError("simulated removal failure")
            remove_exact_entry(root, entry)

        receipt = apply_cleanup(
            repo,
            contract,
            manifest,
            plan,
            remover=fail_on_second_file,
        )
        root = repo / contract["scopes"][0]["path"]

        self.assertEqual(receipt["status"], "failed", receipt)
        self.assertEqual(receipt["failure"]["code"], "os_remove_failed")
        self.assertIn(
            (root / "a.bin").relative_to(repo).as_posix(),
            receipt["removed"],
        )
        self.assertIn(
            (root / "b.bin").relative_to(repo).as_posix(),
            receipt["remaining"],
        )
        self.assertTrue((root / "b.bin").exists())
        self.assertTrue((root / "c.bin").exists())
        self.assertFalse(any(path.endswith("/c.bin") for path in attempted))
        self.assertTrue(receipt["zeroUnlistedMutation"])

    def test_generic_rules_cover_logs_build_cache_locks_sockets_and_spools(self):
        from workflow_generated_artifacts import apply_cleanup, plan_cleanup

        repo = self.make_repo()
        contract = self.prepare(repo)
        root = repo / contract["scopes"][0]["path"]
        regular_outputs = (
            "logs/task.log",
            "build/app.bundle",
            "cache/entry",
            "locks/task.lock",
            "locks/task.pid",
            "spool/messages/item",
        )
        for relative in regular_outputs:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"{relative}\n")
        fifo = root / "spool" / "events.fifo"
        os.mkfifo(fifo)
        socket_path = root / "locks" / "worker.sock"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(socket_path))

        manifest = self.observe(repo, contract)
        plan = plan_cleanup(repo, contract, manifest)
        receipt = apply_cleanup(repo, contract, manifest, plan)

        self.assertEqual(plan["decision"], "AUTO_CLEAN", plan)
        entry_types = {
            entry["path"]: entry["type"]
            for entry in manifest["entries"]
        }
        self.assertEqual(entry_types[fifo.relative_to(repo).as_posix()], "fifo")
        self.assertEqual(
            entry_types[socket_path.relative_to(repo).as_posix()],
            "socket",
        )
        for relative in regular_outputs:
            self.assertEqual(
                entry_types[(root / relative).relative_to(repo).as_posix()],
                "file",
            )
        self.assertEqual(receipt["status"], "complete", receipt)
        self.assertFalse(root.exists())

        implementation = runtime_source(
            "scripts/workflow_generated_artifacts.py"
        )
        for extension in (".log", ".pyc", ".pid", ".sock"):
            self.assertNotIn(f'endswith("{extension}")', implementation)
            self.assertNotIn(f"endswith('{extension}')", implementation)


class GeneratedArtifactCliTests(GeneratedArtifactTestSupport, unittest.TestCase):
    def run_cli(self, *arguments):
        cli = SCRIPTS / "generated_artifact_lifecycle.py"
        return subprocess.run(
            [sys.executable, str(cli), *map(str, arguments)],
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

    def write_document(self, path, document):
        path.write_text(
            json.dumps(
                document,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            + "\n"
        )

    def prepare_cli_contract(self, repo, root):
        prepared = self.run_cli(
            "prepare",
            "--repo",
            repo,
            "--task-id",
            "cli-task",
            "--run-id",
            "cli-run",
            "--owner-id",
            "main",
            "--owner-pid",
            "999999999",
            "--command-json",
            '["python3","build.py"]',
            "--isolated-root",
            root,
        )
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        contract = json.loads(prepared.stdout)
        self.assertEqual(contract["schema"], "generated-artifact-contract/v1")
        self.assertFalse((repo / root).exists())
        contract_path = repo / "contract.json"
        self.write_document(contract_path, contract)
        return prepared, contract_path

    def observe_and_plan_cli_contract(self, repo, contract_path):
        observed = self.run_cli(
            "observe",
            "--repo",
            repo,
            "--contract",
            contract_path,
            "--exit-code",
            "0",
        )
        self.assertEqual(observed.returncode, 0, observed.stderr)
        manifest_path = repo / "manifest.json"
        self.write_document(manifest_path, json.loads(observed.stdout))

        planned = self.run_cli(
            "plan",
            "--repo",
            repo,
            "--contract",
            contract_path,
            "--manifest",
            manifest_path,
        )
        self.assertEqual(planned.returncode, 0, planned.stderr)
        self.assertEqual(json.loads(planned.stdout)["decision"], "AUTO_CLEAN")
        plan_path = repo / "plan.json"
        self.write_document(plan_path, json.loads(planned.stdout))
        return observed, manifest_path, planned, plan_path

    def test_cli_help_exposes_three_read_only_modes_and_explicit_apply(self):
        result = self.run_cli("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        for command in ("prepare", "observe", "plan", "cleanup"):
            self.assertIn(command, result.stdout)
        self.assertIn("read-only", result.stdout.lower())
        self.assertIn("--apply", self.run_cli("cleanup", "--help").stdout)

    def test_cli_lifecycle_is_structured_and_cleanup_requires_apply(self):
        repo = self.make_repo()
        config = repo / "user-config.json"
        config.write_text('{"preserve":true}\n')
        root = ".devflow-generated/cli-task/cli-run"

        prepared, contract_path = self.prepare_cli_contract(repo, root)
        artifact = repo / root / "output.log"
        artifact.parent.mkdir(parents=True)
        artifact.write_text("generated\n")
        observed, manifest_path, planned, plan_path = (
            self.observe_and_plan_cli_contract(repo, contract_path)
        )

        denied = self.run_cli(
            "cleanup",
            "--repo",
            repo,
            "--contract",
            contract_path,
            "--manifest",
            manifest_path,
            "--plan",
            plan_path,
        )
        self.assertEqual(denied.returncode, 3, denied)
        self.assertEqual(json.loads(denied.stdout)["status"], "authorization_required")
        self.assertTrue(artifact.exists())

        applied = self.run_cli(
            "cleanup",
            "--repo",
            repo,
            "--contract",
            contract_path,
            "--manifest",
            manifest_path,
            "--plan",
            plan_path,
            "--apply",
        )
        self.assertEqual(applied.returncode, 0, applied.stderr)
        receipt = json.loads(applied.stdout)
        self.assertEqual(receipt["status"], "complete", receipt)
        self.assertFalse(artifact.exists())
        self.assertEqual(config.read_text(), '{"preserve":true}\n')
        self.assertEqual(contract_path.read_text(), prepared.stdout)
        self.assertEqual(manifest_path.read_text(), observed.stdout)
        self.assertEqual(plan_path.read_text(), planned.stdout)


if __name__ == "__main__":
    unittest.main()
