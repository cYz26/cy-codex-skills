import importlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


TEST_ROOT = Path(__file__).resolve().parent
PLUGIN_ROOT = TEST_ROOT.parent
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))


class RoadmapProviderTests(unittest.TestCase):
    def roadmap_module(self):
        spec = importlib.util.find_spec("workflow_roadmap_provider")
        self.assertIsNotNone(spec, "roadmap provider adapter module must exist")
        return importlib.import_module("workflow_roadmap_provider")

    def repo(self):
        return Path(tempfile.mkdtemp(prefix="devflow-roadmap-provider-"))

    def write(self, repo, relative, text):
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def make_runtime(self, repo):
        return self.write(repo, ".codex/gsd-core/bin/gsd-tools.cjs", "// fixture\n")

    def init_git(self, repo):
        subprocess.run(["git", "init", "-q", str(repo)], check=True)

    def test_inference_uses_content_markers_not_installed_runtime_or_skills(self):
        module = self.roadmap_module()
        repo = self.repo()
        self.make_runtime(repo)
        self.write(repo, ".agents/skills/gsd-plan-phase/SKILL.md", "fixture\n")
        self.write(repo, ".codex/.gsd-profile", "standard\n")

        report = module.infer_roadmap_ownership(repo)

        self.assertEqual(report["provider"], "none")
        self.assertEqual(report["status"], "no_markers")
        self.assertEqual(report["evidence"], [])

    def test_inference_recognizes_strong_gsd_markers_and_legacy_devflow(self):
        module = self.roadmap_module()
        fixtures = {
            "state": (".planning/STATE.md", "---\ngsd_state_version: '1.0'\n---\n"),
            "project": (
                ".planning/PROJECT.md",
                "# Product\n\n## What This Is\nX\n## Core Value\nY\n"
                "## Requirements\nZ\n## Key Decisions\nA\n",
            ),
            "config": (
                ".planning/config.json",
                json.dumps({"planning": {"commit_docs": True}, "gates": {"confirm_roadmap": True}}),
            ),
            "phase": (
                ".planning/phases/01-foundation/01-01-PLAN.md",
                "---\nphase: 01-foundation\nplan: 01\n---\n",
            ),
        }
        for marker, (relative, content) in fixtures.items():
            with self.subTest(marker=marker):
                repo = self.repo()
                self.write(repo, relative, content)

                report = module.infer_roadmap_ownership(repo)

                self.assertEqual(report["provider"], "gsd")
                self.assertEqual(report["status"], "inferred")
                self.assertTrue(report["evidence"])

        legacy = self.repo()
        self.write(
            legacy,
            ".planning/STATE.md",
            "---\nworkflow_version: 0.3.0\ncurrent_stage: planning\n---\n",
        )
        report = module.infer_roadmap_ownership(legacy)
        self.assertEqual(report["provider"], "none")
        self.assertEqual(report["status"], "legacy_devflow")

    def test_inference_reports_conflicting_owners_without_guessing(self):
        module = self.roadmap_module()
        repo = self.repo()
        self.write(
            repo,
            ".planning/STATE.md",
            "---\nworkflow_version: 0.3.0\ngsd_state_version: '1.0'\n---\n",
        )

        report = module.infer_roadmap_ownership(repo)

        self.assertEqual(report["provider"], None)
        self.assertEqual(report["status"], "manual_review_required")
        self.assertTrue(report["conflicts"])

    def test_roadmap_content_is_inferred_only_after_runtime_validation(self):
        module = self.roadmap_module()
        repo = self.repo()
        self.write(repo, ".planning/ROADMAP.md", "# Runtime-owned roadmap fixture\n")

        class ValidatingAdapter:
            def roadmap_validate(self):
                return {"ok": True, "data": {"warnings": []}}

        without_runtime = module.infer_roadmap_ownership(repo)
        with_runtime = module.infer_roadmap_ownership(repo, adapter=ValidatingAdapter())

        self.assertEqual(without_runtime["provider"], "none")
        self.assertEqual(with_runtime["provider"], "gsd")
        self.assertIn("gsd_runtime_validated_roadmap", with_runtime["evidence"][0])

        class BrokenAdapter:
            def roadmap_validate(self):
                return {"ok": False, "reason": "invalid_json"}

        broken = module.infer_roadmap_ownership(repo, adapter=BrokenAdapter())
        self.assertEqual(broken["status"], "manual_review_required")
        self.assertIn("invalid_json", broken["conflicts"][0])

    def test_gsd_adapter_invokes_only_required_read_only_commands(self):
        module = self.roadmap_module()
        repo = self.repo()
        runtime = self.make_runtime(repo)
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            operation = tuple(command[2:])
            if operation[:2] == ("state", "load"):
                payload = {"config": {"commit_docs": True}, "state_exists": True}
            elif operation[:2] == ("roadmap", "validate"):
                payload = {"warnings": []}
            elif operation[:2] == ("roadmap", "get-phase"):
                payload = {"found": True, "phase_number": operation[2]}
            elif operation[:1] == ("find-phase",):
                payload = {"found": True, "directory": ".planning/phases/02-foundation"}
            else:
                raise AssertionError(f"unexpected command: {command}")
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

        adapter = module.GsdReadOnlyAdapter(repo, runner=runner)
        report = adapter.diagnose(["02-foundation"])

        self.assertTrue(report["ready"])
        self.assertTrue(report["commitDocs"])
        self.assertEqual(report["status"], "ready")
        self.assertEqual(len(calls), 4)
        self.assertTrue(all(call[0][:2] == ["node", str(runtime.resolve())] for call in calls))
        operations = [tuple(call[0][2 : call[0].index("--cwd")]) for call in calls]
        self.assertEqual(
            operations,
            [
                ("state", "load"),
                ("roadmap", "validate"),
                ("roadmap", "get-phase", "02-foundation"),
                ("find-phase", "02-foundation"),
            ],
        )
        for command, kwargs in calls:
            self.assertEqual(command[-3:], ["--cwd", str(repo.resolve()), "--json-errors"])
            self.assertTrue(kwargs["capture_output"])
            self.assertTrue(kwargs["text"])
            self.assertFalse(kwargs["check"])

    def test_gsd_adapter_returns_structured_manual_review_on_runtime_errors(self):
        module = self.roadmap_module()
        missing = module.GsdReadOnlyAdapter(self.repo()).state_load()
        self.assertEqual(missing["status"], "manual_review_required")
        self.assertEqual(missing["reason"], "runtime_missing")

        repo = self.repo()
        self.make_runtime(repo)

        def invalid_json(command, **_kwargs):
            return subprocess.CompletedProcess(command, 0, stdout="not-json", stderr="")

        invalid = module.GsdReadOnlyAdapter(repo, runner=invalid_json).roadmap_validate()
        self.assertEqual(invalid["status"], "manual_review_required")
        self.assertEqual(invalid["reason"], "invalid_json")

        def structured_error(command, **_kwargs):
            payload = {"ok": False, "reason": "phase_missing", "message": "not found"}
            return subprocess.CompletedProcess(command, 1, stdout="", stderr=json.dumps(payload))

        failed = module.GsdReadOnlyAdapter(repo, runner=structured_error).find_phase("09-missing")
        self.assertEqual(failed["status"], "manual_review_required")
        self.assertEqual(failed["reason"], "phase_missing")
        self.assertEqual(failed["error"]["message"], "not found")

    def test_gsd_adapter_resolves_exact_uat_path_with_strict_containment(self):
        module = self.roadmap_module()
        repo = self.repo()
        self.make_runtime(repo)
        uat = self.write(repo, ".planning/phases/02-foundation/02-UAT.md", "fixture\n")

        def runner(command, **_kwargs):
            operation = tuple(command[2 : command.index("--cwd")])
            if operation == ("roadmap", "get-phase", "02-foundation"):
                payload = {"found": True, "phase_number": "02"}
            elif operation == ("find-phase", "02-foundation"):
                payload = {
                    "found": True,
                    "directory": ".planning/phases/02-foundation",
                    "phase_number": "02",
                }
            else:
                raise AssertionError(operation)
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

        report = module.GsdReadOnlyAdapter(repo, runner=runner).resolve_uat_artifact("02-foundation")

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["path"], str(uat.resolve()))
        self.assertEqual(report["relativePath"], ".planning/phases/02-foundation/02-UAT.md")
        self.assertEqual(report["canonicalPhaseId"], "02-foundation")

    def test_gsd_adapter_rejects_traversal_and_symlinked_uat_paths(self):
        module = self.roadmap_module()
        for directory, reason in (
            (".planning/phases/../outside", "phase_directory_outside_canonical_root"),
            ("/tmp/02-foundation", "phase_directory_outside_canonical_root"),
            (".planning/milestones/v1-phases/02-foundation", "phase_directory_outside_canonical_root"),
        ):
            with self.subTest(directory=directory):
                repo = self.repo()
                self.make_runtime(repo)

                def runner(command, **_kwargs):
                    operation = tuple(command[2 : command.index("--cwd")])
                    payload = (
                        {"found": True, "phase_number": "02"}
                        if operation[:2] == ("roadmap", "get-phase")
                        else {"found": True, "directory": directory, "phase_number": "02"}
                    )
                    return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

                result = module.GsdReadOnlyAdapter(repo, runner=runner).resolve_uat_artifact("02-foundation")
                self.assertFalse(result["ok"], result)
                self.assertEqual(result["reason"], reason)

        repo = self.repo()
        self.make_runtime(repo)
        outside = self.write(repo, "outside-UAT.md", "fixture\n")
        phase_dir = repo / ".planning" / "phases" / "02-foundation"
        phase_dir.mkdir(parents=True)
        (phase_dir / "02-UAT.md").symlink_to(outside)

        def symlink_runner(command, **_kwargs):
            operation = tuple(command[2 : command.index("--cwd")])
            payload = (
                {"found": True, "phase_number": "02"}
                if operation[:2] == ("roadmap", "get-phase")
                else {
                    "found": True,
                    "directory": ".planning/phases/02-foundation",
                    "phase_number": "02",
                }
            )
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

        symlink = module.GsdReadOnlyAdapter(repo, runner=symlink_runner).resolve_uat_artifact("02-foundation")
        self.assertFalse(symlink["ok"], symlink)
        self.assertEqual(symlink["reason"], "uat_artifact_symlink")

    def test_binding_validation_checks_schema_change_and_selected_gsd_phase(self):
        module = self.roadmap_module()
        repo = self.repo()
        self.make_runtime(repo)
        (repo / "openspec" / "changes" / "change-a").mkdir(parents=True)

        def runner(command, **_kwargs):
            operation = tuple(command[2 : command.index("--cwd")])
            if operation == ("roadmap", "get-phase", "02-foundation"):
                payload = {"found": True, "phase_number": "02"}
            elif operation == ("find-phase", "02-foundation"):
                payload = {"found": True, "directory": ".planning/phases/02-foundation"}
            else:
                raise AssertionError(operation)
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

        adapter = module.GsdReadOnlyAdapter(repo, runner=runner)
        binding = {
            "change-a": {
                "phase_id": "02-foundation",
                "milestone": "v1.0",
                "status": "active",
            }
        }
        valid = module.validate_roadmap_bindings(repo, binding, "gsd", adapter=adapter)

        self.assertTrue(valid["ready"])
        self.assertEqual(valid["bindings"]["change-a"]["effectiveStatus"], "active")

        missing_change = module.validate_roadmap_bindings(
            repo,
            {"missing": binding["change-a"]},
            "gsd",
            adapter=adapter,
        )
        self.assertEqual(missing_change["status"], "manual_review_required")
        self.assertIn("missing_openspec_change", missing_change["blockingReasons"])

        invalid_schema = module.validate_roadmap_bindings(
            repo,
            {"change-a": {"phase_id": "02-foundation", "status": "active"}},
            "gsd",
            adapter=adapter,
        )
        self.assertEqual(invalid_schema["status"], "invalid_schema")
        self.assertFalse(invalid_schema["ready"])

    def test_binding_validation_rejects_unsafe_change_identifiers_before_path_lookup(self):
        module = self.roadmap_module()
        repo = self.repo()
        outside = repo.parent / "outside-change"
        outside.mkdir(exist_ok=True)
        binding = {"../outside-change": {"phase_id": "02-foundation", "milestone": "v1", "status": "active"}}

        report = module.validate_roadmap_bindings(repo, binding, "gsd")

        self.assertFalse(report["ready"])
        self.assertEqual(report["status"], "invalid_schema")
        self.assertIn("invalid_change_id", report["blockingReasons"])

    def test_binding_missing_phase_blocks_and_none_makes_binding_inactive(self):
        module = self.roadmap_module()
        repo = self.repo()
        self.make_runtime(repo)
        (repo / "openspec" / "changes" / "change-a").mkdir(parents=True)
        binding = {
            "change-a": {
                "phase_id": "02-foundation",
                "milestone": "v1.0",
                "status": "active",
            }
        }

        def missing_phase(command, **_kwargs):
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"found": False}), stderr="")

        blocked = module.validate_roadmap_bindings(
            repo,
            binding,
            "gsd",
            adapter=module.GsdReadOnlyAdapter(repo, runner=missing_phase),
        )
        self.assertEqual(blocked["status"], "manual_review_required")
        self.assertIn("unresolved_gsd_phase", blocked["blockingReasons"])

        inactive = module.validate_roadmap_bindings(repo, binding, "none")
        self.assertTrue(inactive["ready"])
        self.assertEqual(inactive["bindings"]["change-a"]["configuredStatus"], "active")
        self.assertEqual(inactive["bindings"]["change-a"]["effectiveStatus"], "inactive")

    def test_binding_archive_is_explicit_and_requires_all_gates(self):
        module = self.roadmap_module()
        bindings = {
            "change-a": {
                "phase_id": "02-foundation",
                "milestone": "v1.0",
                "status": "active",
            }
        }

        blocked = module.archive_roadmap_binding(
            bindings,
            "change-a",
            openspec_verified=True,
            openspec_archived=False,
            gsd_verified=True,
        )
        self.assertFalse(blocked["applied"])
        self.assertEqual(blocked["bindings"]["change-a"]["status"], "active")
        self.assertIn("openspec_archive", blocked["missingGates"])

        archived = module.archive_roadmap_binding(
            bindings,
            "change-a",
            openspec_verified=True,
            openspec_archived=True,
            gsd_verified=True,
        )
        self.assertTrue(archived["applied"])
        self.assertEqual(archived["bindings"]["change-a"]["status"], "archived")
        self.assertEqual(bindings["change-a"]["status"], "active", "input must not be mutated")

    def test_binding_archive_persistence_is_dry_run_and_policy_authorized(self):
        module = self.roadmap_module()
        repo = self.repo()
        config = {
            "workflow": {
                "methodology_profile": "core",
                "roadmap_provider": "gsd",
                "roadmap_bindings": {
                    "change-a": {
                        "phase_id": "02-foundation",
                        "milestone": "v1.0",
                        "status": "active",
                    }
                },
            }
        }
        config_path = self.write(repo, ".dev-flow.json", json.dumps(config, indent=2) + "\n")
        gates = {
            "openspec_verified": True,
            "openspec_archived": True,
            "gsd_verified": True,
        }

        with mock.patch.object(module, "archive_binding_gate_status", return_value=gates):
            dry_run = module.persist_archived_roadmap_binding(repo, "change-a")
            denied = module.persist_archived_roadmap_binding(repo, "change-a", apply=True)

        self.assertEqual(dry_run["status"], "planned")
        self.assertFalse(dry_run["changed"])
        persisted = json.loads(config_path.read_text())
        self.assertEqual(persisted["workflow"]["roadmap_bindings"]["change-a"]["status"], "active")
        self.assertEqual(denied["status"], "authorization_required")
        self.assertFalse(denied["changed"])
        self.assertEqual({item["effect"] for item in denied["sideEffects"]}, {"canonical.write", "archive_release"})

        with mock.patch.object(module, "archive_binding_gate_status", return_value=gates), mock.patch.object(
            module, "atomic_write_text", wraps=module.atomic_write_text
        ) as atomic_write:
            applied = module.persist_archived_roadmap_binding(
                repo,
                "change-a",
                apply=True,
                authorized=True,
            )

        self.assertTrue(applied["ok"], applied)
        self.assertEqual(applied["status"], "archived")
        self.assertTrue(applied["changed"])
        atomic_write.assert_called_once()
        persisted = json.loads(config_path.read_text())
        self.assertEqual(persisted["workflow"]["roadmap_bindings"]["change-a"]["status"], "archived")

    def test_binding_archive_persistence_derives_and_blocks_missing_gates(self):
        module = self.roadmap_module()
        repo = self.repo()
        config = {
            "workflow": {
                "roadmap_provider": "gsd",
                "roadmap_bindings": {
                    "change-a": {
                        "phase_id": "02-foundation",
                        "milestone": "v1.0",
                        "status": "active",
                    }
                },
            }
        }
        path = self.write(repo, ".dev-flow.json", json.dumps(config, indent=2) + "\n")

        gates = {"openspec_verified": True, "openspec_archived": False, "gsd_verified": True}
        with mock.patch.object(module, "archive_binding_gate_status", return_value=gates):
            blocked = module.persist_archived_roadmap_binding(
                repo,
                "change-a",
                apply=True,
                authorized=True,
            )

        self.assertFalse(blocked["ok"], blocked)
        self.assertEqual(blocked["status"], "blocked")
        self.assertIn("openspec_archive", blocked["missingGates"])
        self.assertEqual(json.loads(path.read_text())["workflow"]["roadmap_bindings"]["change-a"]["status"], "active")

    def test_binding_archive_does_not_overwrite_concurrent_config_change(self):
        module = self.roadmap_module()
        repo = self.repo()
        config = {
            "workflow": {
                "roadmap_provider": "gsd",
                "roadmap_bindings": {
                    "change-a": {
                        "phase_id": "02-foundation",
                        "milestone": "v1.0",
                        "status": "active",
                    }
                },
            }
        }
        path = self.write(repo, ".dev-flow.json", json.dumps(config, indent=2) + "\n")
        gates = {"openspec_verified": True, "openspec_archived": True, "gsd_verified": True}

        def mutate_config(*_args, **_kwargs):
            changed = json.loads(path.read_text())
            changed["concurrent"] = "preserve-me"
            path.write_text(json.dumps(changed, indent=2) + "\n")
            return gates

        with mock.patch.object(module, "archive_binding_gate_status", side_effect=mutate_config):
            result = module.persist_archived_roadmap_binding(
                repo,
                "change-a",
                apply=True,
                authorized=True,
            )

        self.assertFalse(result["ok"], result)
        self.assertEqual(result["reason"], "config_changed_during_operation")
        self.assertEqual(json.loads(path.read_text())["concurrent"], "preserve-me")

    def test_active_bindings_block_phase_transition_until_both_verifications_pass(self):
        module = self.roadmap_module()
        bindings = {
            "change-a": {
                "phase_id": "02-foundation",
                "milestone": "v1.0",
                "status": "active",
            },
            "historical": {
                "phase_id": "02-foundation",
                "milestone": "v1.0",
                "status": "archived",
            },
        }

        blocked = module.roadmap_phase_transition_gate(
            bindings,
            "02-foundation",
            roadmap_provider="gsd",
            openspec_verification={"change-a": False},
            gsd_phase_verified=False,
        )
        self.assertFalse(blocked["ready"])
        self.assertEqual(blocked["unverifiedChanges"], ["change-a"])
        self.assertIn("gsd_phase_verification", blocked["blockingReasons"])

        ready = module.roadmap_phase_transition_gate(
            bindings,
            "02-foundation",
            roadmap_provider="gsd",
            openspec_verification={"change-a": True},
            gsd_phase_verified=True,
        )
        self.assertTrue(ready["ready"])

        disabled = module.roadmap_phase_transition_gate(
            bindings,
            "02-foundation",
            roadmap_provider="none",
            openspec_verification={},
            gsd_phase_verified=False,
        )
        self.assertTrue(disabled["ready"])
        self.assertEqual(disabled["status"], "roadmap_provider_inactive")

    def test_tracking_report_classifies_coverage_and_applies_commit_docs_gate(self):
        module = self.roadmap_module()
        repo = self.repo()
        self.init_git(repo)
        tracked = self.write(repo, ".planning/STATE.md", "gsd\n")
        local = self.write(repo, ".planning/ROADMAP.md", "roadmap\n")
        subprocess.run(["git", "-C", str(repo), "add", str(tracked.relative_to(repo))], check=True)

        partial = module.planning_tracking_report(
            repo,
            [".planning/STATE.md", ".planning/ROADMAP.md"],
            roadmap_provider="gsd",
            commit_docs=True,
        )
        self.assertEqual(partial["status"], "partially_tracked")
        self.assertFalse(partial["roadmapReady"])
        self.assertEqual(partial["trackedPaths"], [".planning/STATE.md"])
        self.assertEqual(partial["localOnlyPaths"], [".planning/ROADMAP.md"])

        advisory = module.planning_tracking_report(
            repo,
            [".planning/STATE.md", ".planning/ROADMAP.md"],
            roadmap_provider="gsd",
            commit_docs=False,
        )
        self.assertTrue(advisory["roadmapReady"])
        self.assertTrue(advisory["advisory"])

        all_local = module.planning_tracking_report(
            repo,
            [".planning/ROADMAP.md"],
            roadmap_provider="none",
            commit_docs=True,
        )
        self.assertEqual(all_local["status"], "local_only")
        self.assertTrue(all_local["roadmapReady"])

        subprocess.run(["git", "-C", str(repo), "add", str(local.relative_to(repo))], check=True)
        all_tracked = module.planning_tracking_report(
            repo,
            [".planning/STATE.md", ".planning/ROADMAP.md"],
            roadmap_provider="gsd",
            commit_docs=True,
        )
        self.assertEqual(all_tracked["status"], "tracked")
        self.assertTrue(all_tracked["roadmapReady"])

        ignored_repo = self.repo()
        self.init_git(ignored_repo)
        self.write(ignored_repo, ".gitignore", ".planning/\n")
        self.write(ignored_repo, ".planning/STATE.md", "local\n")
        ignored = module.planning_tracking_report(
            ignored_repo,
            [".planning/STATE.md"],
            roadmap_provider="gsd",
            commit_docs=True,
        )
        self.assertEqual(ignored["status"], "local_only")
        self.assertEqual(ignored["ignoredPaths"], [".planning/STATE.md"])
        self.assertFalse(ignored["roadmapReady"])

    def test_tracking_report_expands_directories_and_rejects_mixed_file_coverage(self):
        module = self.roadmap_module()
        repo = self.repo()
        self.init_git(repo)
        tracked = self.write(repo, ".planning/phases/01-foundation/01-01-PLAN.md", "tracked\n")
        local = self.write(repo, ".planning/phases/01-foundation/01-01-SUMMARY.md", "local\n")
        subprocess.run(
            ["git", "-C", str(repo), "add", str(tracked.relative_to(repo))],
            check=True,
        )

        report = module.planning_tracking_report(
            repo,
            [".planning/phases"],
            roadmap_provider="gsd",
            commit_docs=True,
        )

        self.assertEqual(report["status"], "partially_tracked")
        self.assertFalse(report["roadmapReady"])
        self.assertEqual(report["trackedPaths"], [tracked.relative_to(repo).as_posix()])
        self.assertEqual(report["localOnlyPaths"], [local.relative_to(repo).as_posix()])
        self.assertEqual(report["untrackedPaths"], [local.relative_to(repo).as_posix()])


if __name__ == "__main__":
    unittest.main()
