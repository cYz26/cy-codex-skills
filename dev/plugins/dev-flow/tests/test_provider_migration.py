import hashlib
import importlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


TEST_ROOT = Path(__file__).resolve().parent
PLUGIN_ROOT = TEST_ROOT.parent
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))


class ProviderMigrationTests(unittest.TestCase):
    def module(self):
        spec = importlib.util.find_spec("workflow_provider_migration")
        self.assertIsNotNone(spec, "provider migration module must exist")
        return importlib.import_module("workflow_provider_migration")

    def repo(self) -> Path:
        repo = Path(tempfile.mkdtemp(prefix="devflow-provider-migration-"))
        (repo / "openspec").mkdir()
        (repo / "openspec" / "config.yaml").write_text("schema: spec-driven\n")
        return repo

    def write_legacy_state(self, repo: Path, marker: str = "workflow_version: 0.3.0") -> str:
        text = f"---\n{marker}\ncurrent_stage: planning\n---\n\n# State\n"
        path = repo / ".planning" / "STATE.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return text

    def diagnosis(self, repo: Path) -> dict:
        return {
            "ok": True,
            "methodologyReady": True,
            "roadmapReady": True,
            "selection": {
                "codexHome": str(repo / ".codex-home"),
                "effectiveMethodologyProfile": "lean-matt",
                "effectiveRoadmapProvider": "gsd",
                "providerSelectors": {
                    "mattpocock-skills": {
                        "kind": "git-skill-pack",
                        "repository": "mattpocock/skills",
                        "ref": "v1.1.0",
                        "commit": "d574778f94cf620fcc8ce741584093bc650a61d3",
                    }
                },
                "roadmapBindings": {"change-a": {"phase_id": "02"}},
            },
            "selectedProviders": ["mattpocock-skills", "gsd"],
            "providers": {
                "mattpocock-skills": {
                    "ready": True,
                    "skillHashes": {"tdd": "a" * 64},
                },
                "gsd": {
                    "ready": True,
                    "runtime": str(repo / ".agents" / "get-shit-done" / "bin" / "gsd-tools.cjs"),
                    "version": "1.6.1",
                    "tracking": {
                        "status": "partially_tracked",
                        "trackedPaths": [".planning/STATE.md"],
                        "localOnlyPaths": [".planning/ROADMAP.md"],
                        "roadmapReady": True,
                    },
                },
            },
        }

    def digest(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_dry_run_returns_hash_based_report_without_writes_or_snapshot(self):
        module = self.module()
        repo = self.repo()
        legacy_text = self.write_legacy_state(repo)
        config = repo / ".dev-flow.json"
        config.write_text(json.dumps({"hooks": {"mode": "warn"}}))
        before = self.digest(config)

        result = module.plan_provider_migration(repo, self.diagnosis(repo))

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["status"], "planned")
        self.assertTrue(result["dryRun"])
        self.assertEqual(result["sunsetRelease"], "1.0.0")
        self.assertRegex(result["migrationId"], r"^[0-9a-f]{16}$")
        report_path = Path(result["reportPath"])
        self.assertEqual(
            report_path.parent.resolve(),
            (repo / ".planning" / "devflow" / "provider-migration" / "reports").resolve(),
        )
        self.assertFalse(report_path.exists())
        self.assertFalse((repo / ".planning" / "devflow" / "provider-migration" / "snapshots").exists())
        self.assertFalse((repo / ".planning" / "devflow" / "STATE.md").exists())
        self.assertFalse((repo / ".planning" / "devflow" / "providers.lock.json").exists())
        self.assertEqual(result["report"]["tracking"]["status"], "partially_tracked")
        self.assertEqual(self.digest(config), before)
        self.assertEqual((repo / ".planning" / "STATE.md").read_text(), legacy_text)
        for operation in result["operations"]:
            self.assertIn("before", operation)
            self.assertIn("after", operation)
            self.assertIn("sha256", operation["after"])

    def test_apply_requires_explicit_authority_and_writes_snapshot_manifest_first(self):
        module = self.module()
        repo = self.repo()
        self.write_legacy_state(repo)
        config = repo / ".dev-flow.json"
        config.write_text(json.dumps({"hooks": {"mode": "warn"}}))
        before = self.digest(config)

        denied = module.apply_provider_migration(repo, self.diagnosis(repo), authorized=False)

        self.assertEqual(denied["status"], "authorization_required")
        self.assertEqual(self.digest(config), before)
        self.assertFalse((repo / ".planning" / "devflow").exists())

        writes = []
        real_atomic_write = module.atomic_write

        def record_write(path, text):
            writes.append(Path(path))
            return real_atomic_write(path, text)

        with mock.patch.object(module, "atomic_write", side_effect=record_write):
            applied = module.apply_provider_migration(repo, self.diagnosis(repo), authorized=True)

        self.assertTrue(applied["ok"], applied)
        self.assertEqual(applied["status"], "applied")
        checkpoint = Path(applied["checkpointPath"])
        self.assertTrue(checkpoint.exists())
        checkpoint_payload = json.loads(checkpoint.read_text())
        self.assertEqual(checkpoint_payload["kind"], "devflow-provider-state-migration-preflight-checkpoint")
        manifest = Path(applied["manifestPath"])
        target_writes = {
            (repo / ".dev-flow.json").resolve(),
            (repo / ".planning" / "devflow" / "STATE.md").resolve(),
            (repo / ".planning" / "devflow" / "providers.lock.json").resolve(),
        }
        first_target = min(writes.index(path) for path in target_writes)
        self.assertLess(writes.index(checkpoint), first_target)
        self.assertLess(writes.index(manifest), first_target)

    def test_apply_migrates_state_and_provider_selection_without_touching_gsd_or_links(self):
        module = self.module()
        repo = self.repo()
        legacy_text = self.write_legacy_state(repo)
        config = repo / ".dev-flow.json"
        config.write_text(json.dumps({"hooks": {"mode": "warn"}, "custom": 7}))
        gsd_roadmap = repo / ".planning" / "ROADMAP.md"
        gsd_plan = repo / ".planning" / "phases" / "01-core" / "PLAN.md"
        gsd_plan.parent.mkdir(parents=True)
        gsd_roadmap.write_text("# GSD Roadmap\n")
        gsd_plan.write_text("# GSD Plan\n")
        gsd_hashes = (self.digest(gsd_roadmap), self.digest(gsd_plan))
        target = repo / "matt-tdd"
        target.mkdir()
        (target / "SKILL.md").write_text("# TDD\n")
        link = repo / ".agents" / "skills" / "tdd"
        link.parent.mkdir(parents=True)
        link.symlink_to(target, target_is_directory=True)

        result = module.apply_provider_migration(repo, self.diagnosis(repo), authorized=True)

        self.assertTrue(result["ok"], result)
        self.assertEqual((repo / ".planning" / "devflow" / "STATE.md").read_text(), legacy_text)
        self.assertEqual((repo / ".planning" / "STATE.md").read_text(), legacy_text)
        persisted = json.loads(config.read_text())
        self.assertEqual(persisted["custom"], 7)
        self.assertEqual(persisted["hooks"]["mode"], "warn")
        self.assertEqual(persisted["workflow"]["methodology_profile"], "lean-matt")
        self.assertEqual(persisted["workflow"]["roadmap_provider"], "gsd")
        self.assertEqual(persisted["workflow"]["roadmap_bindings"]["change-a"]["phase_id"], "02")
        lock = json.loads((repo / ".planning" / "devflow" / "providers.lock.json").read_text())
        self.assertEqual(lock["providers"]["mattpocock-skills"]["commit"], "d574778f94cf620fcc8ce741584093bc650a61d3")
        self.assertEqual(lock["providers"]["gsd"]["version"], "1.6.1")
        self.assertEqual((self.digest(gsd_roadmap), self.digest(gsd_plan)), gsd_hashes)
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.resolve(), target.resolve())
        manifest = json.loads(Path(result["manifestPath"]).read_text())
        self.assertEqual(manifest["sunsetRelease"], "1.0.0")
        self.assertEqual(manifest["status"], "applied")
        self.assertTrue(all("pre" in item and "post" in item for item in manifest["targets"]))
        provider_state = manifest["preMigrationProviderState"]
        self.assertEqual(
            provider_state["codexHome"]["path"],
            str((repo / ".codex-home").resolve()),
        )
        self.assertEqual(
            provider_state["codexHome"]["pathSha256"],
            hashlib.sha256(str((repo / ".codex-home").resolve()).encode()).hexdigest(),
        )
        self.assertTrue(provider_state["readiness"]["methodologyReady"])
        self.assertTrue(provider_state["readiness"]["roadmapReady"])

    def test_apply_is_idempotent_and_does_not_create_another_snapshot(self):
        module = self.module()
        repo = self.repo()
        self.write_legacy_state(repo)

        first = module.apply_provider_migration(repo, self.diagnosis(repo), authorized=True)
        snapshot_root = repo / ".planning" / "devflow" / "provider-migration" / "snapshots"
        before = sorted(path.relative_to(snapshot_root) for path in snapshot_root.rglob("*"))
        second = module.apply_provider_migration(repo, self.diagnosis(repo), authorized=True)
        after = sorted(path.relative_to(snapshot_root) for path in snapshot_root.rglob("*"))

        self.assertEqual(first["status"], "applied")
        self.assertEqual(second["status"], "current")
        self.assertFalse(second["changed"])
        self.assertEqual(before, after)

    def test_rollback_restores_pre_state_and_removes_new_targets(self):
        module = self.module()
        repo = self.repo()
        legacy_text = self.write_legacy_state(repo)
        config = repo / ".dev-flow.json"
        original = json.dumps({"hooks": {"mode": "warn"}})
        config.write_text(original)
        gsd = repo / ".planning" / "ROADMAP.md"
        gsd.write_text("# GSD Roadmap\n")

        applied = module.apply_provider_migration(repo, self.diagnosis(repo), authorized=True)
        with mock.patch.object(
            module,
            "diagnose_provider_selection",
            return_value=self.diagnosis(repo),
        ):
            rolled_back = module.rollback_provider_migration(
                repo,
                Path(applied["manifestPath"]),
                authorized=True,
            )

        self.assertTrue(rolled_back["ok"], rolled_back)
        self.assertEqual(rolled_back["status"], "rolled_back")
        self.assertEqual(config.read_text(), original)
        self.assertFalse((repo / ".planning" / "devflow" / "STATE.md").exists())
        self.assertFalse((repo / ".planning" / "devflow" / "providers.lock.json").exists())
        self.assertEqual((repo / ".planning" / "STATE.md").read_text(), legacy_text)
        self.assertEqual(gsd.read_text(), "# GSD Roadmap\n")

    def test_rollback_requires_destructive_cleanup_policy_authorization(self):
        module = self.module()
        repo = self.repo()
        self.write_legacy_state(repo)
        applied = module.apply_provider_migration(repo, self.diagnosis(repo), authorized=True)

        denied = module.rollback_provider_migration(
            repo,
            Path(applied["manifestPath"]),
            authorized=False,
        )

        self.assertFalse(denied["ok"])
        self.assertEqual(denied["status"], "authorization_required")
        self.assertEqual(denied["authorization"], "explicit_file_list_and_rollback")
        self.assertEqual(denied["sideEffect"]["effect"], "destructive.cleanup")
        self.assertEqual(
            denied["sideEffect"]["requiredAuthorization"],
            "explicit_file_list_and_rollback",
        )
        self.assertFalse(denied["sideEffect"]["authorized"])

    def test_rollback_rejects_manifest_not_at_canonical_snapshot_location(self):
        module = self.module()
        repo = self.repo()
        self.write_legacy_state(repo)
        applied = module.apply_provider_migration(repo, self.diagnosis(repo), authorized=True)
        source = Path(applied["manifestPath"])
        nested = source.parent / "nested" / "manifest.json"
        nested.parent.mkdir()
        nested.write_text(source.read_text())

        result = module.rollback_provider_migration(repo, nested, authorized=True)

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "manual_review_required")
        self.assertIn("manifest_not_at_canonical_snapshot_location", result["conflicts"])

    def test_rollback_rejects_snapshot_from_another_migration_directory(self):
        module = self.module()
        repo = self.repo()
        self.write_legacy_state(repo)
        config = repo / ".dev-flow.json"
        config.write_text(json.dumps({"hooks": {"mode": "warn"}}))
        applied = module.apply_provider_migration(repo, self.diagnosis(repo), authorized=True)
        manifest_path = Path(applied["manifestPath"])
        manifest = json.loads(manifest_path.read_text())
        record = next(item for item in manifest["targets"] if item["path"] == ".dev-flow.json")
        source = repo / record["pre"]["snapshotPath"]
        other = manifest_path.parent.parent / "other-migration" / "files" / source.name
        other.parent.mkdir(parents=True)
        other.write_bytes(source.read_bytes())
        record["pre"]["snapshotPath"] = other.relative_to(repo.resolve()).as_posix()
        manifest_path.write_text(json.dumps(manifest))

        result = module.rollback_provider_migration(repo, manifest_path, authorized=True)

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "manual_review_required")
        self.assertEqual(result["reason"], "invalid_manifest")
        self.assertTrue(any("snapshot path is outside migration snapshot" in item for item in result["conflicts"]))

    def test_rollback_failure_compensates_to_complete_post_migration_state(self):
        module = self.module()
        repo = self.repo()
        self.write_legacy_state(repo)
        config = repo / ".dev-flow.json"
        config.write_text(json.dumps({"hooks": {"mode": "warn"}}))
        applied = module.apply_provider_migration(repo, self.diagnosis(repo), authorized=True)
        manifest_path = Path(applied["manifestPath"])
        manifest = json.loads(manifest_path.read_text())
        expected_post = {
            item["path"]: item["post"]
            for item in manifest["targets"]
        }
        fail_target = (repo / ".dev-flow.json").resolve()
        real_restore = module._restore_target_to_pre
        failed = False

        def fail_once(repo_path, record, snapshot_root):
            nonlocal failed
            target = (Path(repo_path) / record["path"]).resolve()
            if target == fail_target and not failed:
                failed = True
                raise OSError("injected rollback failure")
            return real_restore(repo_path, record, snapshot_root)

        with mock.patch.object(module, "_restore_target_to_pre", side_effect=fail_once):
            result = module.rollback_provider_migration(repo, manifest_path, authorized=True)

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "rollback_failed_restored")
        self.assertFalse(result["changed"])
        self.assertEqual(result["compensationErrors"], [])
        self.assertEqual(
            expected_post,
            {
                item["path"]: module._fingerprint(repo / item["path"])
                for item in manifest["targets"]
            },
        )
        self.assertEqual(json.loads(manifest_path.read_text())["status"], "applied")

    def test_rollback_stops_before_any_write_when_post_hash_drifted(self):
        module = self.module()
        repo = self.repo()
        self.write_legacy_state(repo)
        config = repo / ".dev-flow.json"
        config.write_text(json.dumps({"hooks": {"mode": "warn"}}))
        applied = module.apply_provider_migration(repo, self.diagnosis(repo), authorized=True)
        namespaced_state = repo / ".planning" / "devflow" / "STATE.md"
        state_before = self.digest(namespaced_state)
        config.write_text("manual edit\n")

        result = module.rollback_provider_migration(
            repo,
            Path(applied["manifestPath"]),
            authorized=True,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "manual_review_required")
        self.assertEqual(result["reason"], "hash_mismatch")
        self.assertEqual(config.read_text(), "manual edit\n")
        self.assertEqual(self.digest(namespaced_state), state_before)

    def test_rollback_stops_before_any_write_when_snapshot_hash_drifted(self):
        module = self.module()
        repo = self.repo()
        self.write_legacy_state(repo)
        config = repo / ".dev-flow.json"
        config.write_text(json.dumps({"hooks": {"mode": "warn"}}))
        applied = module.apply_provider_migration(repo, self.diagnosis(repo), authorized=True)
        manifest_path = Path(applied["manifestPath"])
        manifest = json.loads(manifest_path.read_text())
        config_record = next(item for item in manifest["targets"] if item["path"] == ".dev-flow.json")
        snapshot = repo / config_record["pre"]["snapshotPath"]
        snapshot.write_text("tampered snapshot\n")
        target_hashes = {
            item["path"]: self.digest(repo / item["path"])
            for item in manifest["targets"]
        }

        result = module.rollback_provider_migration(repo, manifest_path, authorized=True)

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "manual_review_required")
        self.assertEqual(result["reason"], "snapshot_hash_mismatch")
        self.assertEqual(
            target_hashes,
            {item["path"]: self.digest(repo / item["path"]) for item in manifest["targets"]},
        )

    def test_rollback_rechecks_all_post_hashes_after_capture_before_restore(self):
        module = self.module()
        repo = self.repo()
        self.write_legacy_state(repo)
        config = repo / ".dev-flow.json"
        config.write_text(json.dumps({"hooks": {"mode": "warn"}}))
        applied = module.apply_provider_migration(repo, self.diagnosis(repo), authorized=True)
        namespaced_state = repo / ".planning" / "devflow" / "STATE.md"
        state_post_hash = self.digest(namespaced_state)
        real_capture = module._capture_target_states

        def edit_after_capture(repo_path, targets):
            states = real_capture(repo_path, targets)
            config.write_text("concurrent rollback edit\n")
            return states

        with mock.patch.object(module, "_capture_target_states", side_effect=edit_after_capture):
            result = module.rollback_provider_migration(
                repo,
                Path(applied["manifestPath"]),
                authorized=True,
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "manual_review_required")
        self.assertEqual(result["reason"], "rollback_concurrent_target_drift")
        self.assertEqual(config.read_text(), "concurrent rollback edit\n")
        self.assertEqual(self.digest(namespaced_state), state_post_hash)
        self.assertEqual(json.loads(Path(applied["manifestPath"]).read_text())["status"], "applied")

    def test_rollback_compensates_restored_targets_when_next_target_changes(self):
        module = self.module()
        repo = self.repo()
        self.write_legacy_state(repo)
        config = repo / ".dev-flow.json"
        config.write_text(json.dumps({"hooks": {"mode": "warn"}}))
        applied = module.apply_provider_migration(repo, self.diagnosis(repo), authorized=True)
        manifest_path = Path(applied["manifestPath"])
        manifest = json.loads(manifest_path.read_text())
        post = {item["path"]: item["post"] for item in manifest["targets"]}
        lock = repo / ".planning" / "devflow" / "providers.lock.json"
        real_restore = module._restore_target_to_pre
        edited = False

        def edit_next_target_after_first_restore(repo_path, record, snapshot_root):
            nonlocal edited
            real_restore(repo_path, record, snapshot_root)
            if not edited:
                edited = True
                lock.write_text("concurrent rollback lock edit\n")

        with mock.patch.object(
            module,
            "_restore_target_to_pre",
            side_effect=edit_next_target_after_first_restore,
        ):
            result = module.rollback_provider_migration(repo, manifest_path, authorized=True)

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "manual_review_required")
        self.assertEqual(result["reason"], "rollback_concurrent_target_drift")
        self.assertEqual(lock.read_text(), "concurrent rollback lock edit\n")
        self.assertEqual(module._fingerprint(config), post[".dev-flow.json"])
        self.assertEqual(
            module._fingerprint(repo / ".planning" / "devflow" / "STATE.md"),
            post[".planning/devflow/STATE.md"],
        )
        self.assertEqual(json.loads(manifest_path.read_text())["status"], "applied")

    def test_rollback_compensates_to_post_state_when_provider_readiness_drifted(self):
        module = self.module()
        repo = self.repo()
        self.write_legacy_state(repo)
        (repo / ".dev-flow.json").write_text(json.dumps({"hooks": {"mode": "warn"}}))
        applied = module.apply_provider_migration(repo, self.diagnosis(repo), authorized=True)
        manifest_path = Path(applied["manifestPath"])
        manifest = json.loads(manifest_path.read_text())
        expected_post = {item["path"]: item["post"] for item in manifest["targets"]}
        drifted = json.loads(json.dumps(self.diagnosis(repo)))
        drifted["ok"] = False
        drifted["methodologyReady"] = False
        drifted["providers"]["mattpocock-skills"]["ready"] = False
        drifted["providers"]["mattpocock-skills"]["status"] = "source_drift"

        with mock.patch.object(
            module,
            "diagnose_provider_selection",
            return_value=drifted,
            create=True,
        ):
            result = module.rollback_provider_migration(repo, manifest_path, authorized=True)

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "rollback_failed_restored")
        self.assertEqual(result["reason"], "provider_readiness_mismatch")
        self.assertEqual(result["compensationErrors"], [])
        self.assertEqual(
            expected_post,
            {
                item["path"]: module._fingerprint(repo / item["path"])
                for item in manifest["targets"]
            },
        )
        self.assertEqual(json.loads(manifest_path.read_text())["status"], "applied")

    def test_apply_failure_restores_all_pre_migration_hashes(self):
        module = self.module()
        repo = self.repo()
        self.write_legacy_state(repo)
        config = repo / ".dev-flow.json"
        original = json.dumps({"hooks": {"mode": "warn"}})
        config.write_text(original)
        namespaced_state = (repo / ".planning" / "devflow" / "STATE.md").resolve()
        real_atomic_write = module.atomic_write
        failed = False

        def fail_once(path, text):
            nonlocal failed
            if Path(path).resolve() == namespaced_state and not failed:
                failed = True
                raise OSError("injected state write failure")
            return real_atomic_write(path, text)

        with mock.patch.object(module, "atomic_write", side_effect=fail_once):
            result = module.apply_provider_migration(repo, self.diagnosis(repo), authorized=True)

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "apply_failed_restored")
        self.assertEqual(config.read_text(), original)
        self.assertFalse(namespaced_state.exists())
        self.assertFalse((repo / ".planning" / "devflow" / "providers.lock.json").exists())
        manifest = json.loads(Path(result["manifestPath"]).read_text())
        self.assertEqual(manifest["status"], "apply_failed_restored")
        self.assertEqual(manifest["restoreErrors"], [])

    def test_apply_stops_when_target_changes_after_snapshot_before_first_write(self):
        module = self.module()
        repo = self.repo()
        self.write_legacy_state(repo)
        config = repo / ".dev-flow.json"
        config.write_text(json.dumps({"hooks": {"mode": "warn"}}))
        real_atomic_write = module.atomic_write
        edited = False

        def edit_after_report_snapshot(path, text):
            nonlocal edited
            real_atomic_write(path, text)
            if Path(path).parent.name == "reports" and not edited:
                edited = True
                config.write_text("concurrent edit after snapshot\n")

        with mock.patch.object(module, "atomic_write", side_effect=edit_after_report_snapshot):
            result = module.apply_provider_migration(
                repo,
                self.diagnosis(repo),
                authorized=True,
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "manual_review_required")
        self.assertEqual(result["reason"], "concurrent_target_drift")
        self.assertEqual(config.read_text(), "concurrent edit after snapshot\n")
        self.assertFalse((repo / ".planning" / "devflow" / "STATE.md").exists())
        self.assertFalse((repo / ".planning" / "devflow" / "providers.lock.json").exists())

    def test_apply_compensates_written_targets_when_next_target_changes(self):
        module = self.module()
        repo = self.repo()
        self.write_legacy_state(repo)
        config = repo / ".dev-flow.json"
        original = json.dumps({"hooks": {"mode": "warn"}})
        config.write_text(original)
        lock = repo / ".planning" / "devflow" / "providers.lock.json"
        real_atomic_write = module.atomic_write
        edited = False

        def edit_next_target_after_config_write(path, text):
            nonlocal edited
            real_atomic_write(path, text)
            if Path(path).resolve() == config.resolve() and not edited:
                edited = True
                lock.write_text("concurrent provider lock edit\n")

        with mock.patch.object(module, "atomic_write", side_effect=edit_next_target_after_config_write):
            result = module.apply_provider_migration(
                repo,
                self.diagnosis(repo),
                authorized=True,
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "manual_review_required")
        self.assertEqual(result["reason"], "concurrent_target_drift")
        self.assertEqual(config.read_text(), original)
        self.assertEqual(lock.read_text(), "concurrent provider lock edit\n")
        self.assertFalse((repo / ".planning" / "devflow" / "STATE.md").exists())

    def test_post_sunset_legacy_state_returns_no_write_migration_action(self):
        module = self.module()
        repo = self.repo()
        legacy = self.write_legacy_state(repo)

        planned = module.plan_provider_migration(
            repo,
            self.diagnosis(repo),
            current_version="1.0.0",
        )
        applied = module.apply_provider_migration(
            repo,
            self.diagnosis(repo),
            authorized=True,
            current_version="1.0.0",
        )

        self.assertFalse(planned["ok"])
        self.assertEqual(planned["status"], "blocked")
        self.assertIn("legacy_state_compatibility_expired", planned["conflicts"])
        self.assertEqual(applied["status"], "blocked")
        self.assertEqual((repo / ".planning" / "STATE.md").read_text(), legacy)
        self.assertFalse((repo / ".dev-flow.json").exists())
        self.assertFalse((repo / ".planning" / "devflow").exists())

    def test_gsd_or_mixed_root_state_blocks_migration_without_writes(self):
        module = self.module()
        for marker in [
            "gsd_state_version: 1",
            "workflow_version: 0.3.0\ngsd_state_version: 1",
        ]:
            with self.subTest(marker=marker):
                repo = self.repo()
                self.write_legacy_state(repo, marker)

                planned = module.plan_provider_migration(repo, self.diagnosis(repo))
                applied = module.apply_provider_migration(repo, self.diagnosis(repo), authorized=True)

                self.assertFalse(planned["ok"])
                self.assertEqual(planned["status"], "blocked")
                self.assertFalse(applied["ok"])
                self.assertEqual(applied["status"], "blocked")
                self.assertFalse((repo / ".planning" / "devflow").exists())

    def test_inference_conflict_blocks_provider_selection_persistence(self):
        module = self.module()
        repo = self.repo()
        diagnosis = self.diagnosis(repo)
        diagnosis["selection"]["configErrors"] = [
            "root planning artifacts contain both DevFlow and GSD ownership markers"
        ]

        result = module.plan_provider_migration(repo, diagnosis)

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "blocked")
        self.assertIn("provider_selection_conflict", result["conflicts"][0])
        self.assertFalse((repo / ".dev-flow.json").exists())

    def test_provider_readiness_failure_blocks_plan_and_apply_without_writes(self):
        module = self.module()
        repo = self.repo()
        diagnosis = self.diagnosis(repo)
        diagnosis["ok"] = False
        diagnosis["methodologyReady"] = False
        diagnosis["providers"]["mattpocock-skills"] = {
            "ready": False,
            "status": "source_drift",
        }
        diagnosis["blockingReasons"] = ["mattpocock-skills: source_drift"]

        planned = module.plan_provider_migration(repo, diagnosis)
        applied = module.apply_provider_migration(repo, diagnosis, authorized=True)

        self.assertFalse(planned["ok"])
        self.assertEqual(planned["status"], "blocked")
        self.assertTrue(any("provider_not_ready" in item for item in planned["conflicts"]))
        self.assertFalse(applied["ok"])
        self.assertEqual(applied["status"], "blocked")
        self.assertFalse((repo / ".dev-flow.json").exists())
        self.assertFalse((repo / ".planning" / "devflow").exists())

    def test_active_phase_or_change_blocks_migration_without_writes(self):
        module = self.module()
        for active_state in [
            "current_phase:\n  id: 02\n  status: executing",
            "current_change:\n  id: change-a\n  status: applying",
        ]:
            with self.subTest(active_state=active_state):
                repo = self.repo()
                self.write_legacy_state(repo, f"workflow_version: 0.3.0\n{active_state}")

                result = module.plan_provider_migration(repo, self.diagnosis(repo))

                self.assertFalse(result["ok"])
                self.assertEqual(result["status"], "blocked")
                self.assertTrue(any("active_conflicting_" in item for item in result["conflicts"]))
                self.assertFalse((repo / ".planning" / "devflow").exists())


if __name__ == "__main__":
    unittest.main()
