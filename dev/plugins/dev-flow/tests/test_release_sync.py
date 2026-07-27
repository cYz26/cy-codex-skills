import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from release_promotion_gate import quality_gates, run_gate
import workflow_release_sync
from workflow_release_sync import release_eval_target, sync_release_assets
from workflow_release_verification import (
    DEVFLOW_PREPROMOTION_COMMAND,
    record_release_verification,
    release_promotion_readiness,
    release_source_snapshot,
)


class ReleaseSyncTests(unittest.TestCase):
    def make_repo(self):
        repo = Path(tempfile.mkdtemp(prefix="devflow-release-sync-"))
        self.addCleanup(lambda: shutil.rmtree(repo, ignore_errors=True))
        return repo

    def apply_with_internal_test_authorization(self, repo, targets):
        self.write_state(repo, verification_passed=True, release_allowed=True)
        for target in targets:
            self.write_release_verification(repo, target)
        authorization = workflow_release_sync._issue_release_apply_authorization(
            repo,
            targets,
        )
        return sync_release_assets(
            repo,
            apply=True,
            targets=targets,
            _apply_authorization=authorization,
        )

    def write_plugin(self, repo, name="sample", *, release=True, sync_config=None):
        dev_root = repo / "dev" / "plugins" / name
        release_root = repo / "plugins" / name
        (dev_root / ".codex-plugin").mkdir(parents=True)
        (dev_root / ".codex-plugin" / "plugin.json").write_text(
            json.dumps({"name": name, "skills": "./skills/", "hooks": "./hooks.json"})
        )
        release_sync = {
            "releaseVerificationName": "release package verification",
            "releaseVerificationCommand": [
                "{python}",
                "-B",
                "{source}/tests/test_release_package.py",
                "--release-root",
                "{release}",
            ],
        }
        if sync_config is not None:
            release_sync.update(sync_config)
        (dev_root / ".codex-plugin" / "release-sync.json").write_text(
            json.dumps(release_sync)
        )
        (dev_root / "skills" / "demo").mkdir(parents=True)
        (dev_root / "skills" / "demo" / "SKILL.md").write_text("---\nname: demo\ndescription: dev\n---\n")
        (dev_root / "scripts").mkdir()
        (dev_root / "scripts" / "tool.py").write_text("print('dev')\n")
        (dev_root / "docs").mkdir()
        (dev_root / "docs" / "dependency-provenance.json").write_text('{"schemaVersion":2}\n')
        (dev_root / "docs" / "history").mkdir(parents=True)
        (dev_root / "docs" / "history" / "draft.md").write_text("draft\n")
        (dev_root / "tests").mkdir()
        (dev_root / "tests" / "test_dev_only.py").write_text("SHOULD_NOT_RELEASE = True\n")
        (dev_root / "tests" / "test_release_package.py").write_text(
            "# synthetic release verification fixture\n"
        )
        (dev_root / "log").mkdir()
        (dev_root / "log" / "debug.log").write_text("local\n")
        if release:
            (release_root / "skills" / "demo").mkdir(parents=True)
            (release_root / "skills" / "demo" / "SKILL.md").write_text("old\n")
        return dev_root, release_root

    def write_skill(self, repo, name="standalone", *, release=True):
        dev_root = repo / "dev" / "skills" / name
        release_root = repo / name
        dev_root.mkdir(parents=True)
        (dev_root / "SKILL.md").write_text("---\nname: standalone\ndescription: dev\n---\n")
        (dev_root / "references").mkdir()
        (dev_root / "references" / "guide.md").write_text("dev guide\n")
        (dev_root / "log").mkdir()
        (dev_root / "log" / "debug.log").write_text("local\n")
        if release:
            release_root.mkdir()
            (release_root / "SKILL.md").write_text("old\n")
        return dev_root, release_root

    def write_state(
        self,
        repo,
        *,
        verification_passed,
        release_allowed=False,
        implementation_done=True,
        change_status="verified",
    ):
        (repo / ".planning" / "devflow").mkdir(parents=True, exist_ok=True)
        value = "true" if verification_passed else "false"
        release_value = "true" if release_allowed else "false"
        implementation_value = "true" if implementation_done else "false"
        (repo / ".planning" / "devflow" / "STATE.md").write_text(
            f"""---
workflow_version: 0.3.0
current_stage: executing
current_change:
  id: release-fixture
  status: {change_status}
gates:
  spec_approved: true
  plan_written: true
  implementation_done: {implementation_value}
  verification_passed: {value}
  state_updated: true
  release_allowed: {release_value}
context_management:
  compact_status: not_needed
---
# State
"""
        )

    def write_release_verification(self, repo, target="sample"):
        development_command = (
            DEVFLOW_PREPROMOTION_COMMAND
            if target == "dev-flow"
            else (
                "PYTHONDONTWRITEBYTECODE=1 python3.12 -m unittest discover "
                f"-s dev/plugins/{target}/tests -p 'test_*.py'"
            )
        )
        report = record_release_verification(
            repo,
            target,
            "release-fixture",
            development_command=development_command,
            development_result="pass",
            openspec_command="openspec validate --all --strict",
            openspec_result="pass",
            diff_command="git diff --check",
            diff_result="pass",
        )
        self.assertTrue(report["ok"], report)
        return report

    def load_runtime_packager(self):
        path = PLUGIN_ROOT.parents[2] / "dev" / "scripts" / "package_devflow_release_runtime.py"
        spec = importlib.util.spec_from_file_location("package_devflow_release_runtime_fixture", path)
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        return module

    def write_runtime_packaging_fixture(self, repo):
        source_scripts = repo / "dev" / "plugins" / "dev-flow" / "scripts"
        source_root = source_scripts.parent
        release_root = repo / "plugins" / "dev-flow"
        release_scripts = release_root / "scripts"
        source_scripts.mkdir(parents=True)
        release_scripts.mkdir(parents=True)
        (source_root / ".codex-plugin").mkdir(parents=True)
        (source_root / ".codex-plugin" / "plugin.json").write_text(
            json.dumps({"name": "dev-flow", "skills": "./skills/"})
        )
        (source_root / ".codex-plugin" / "release-sync.json").write_text(
            json.dumps(
                {
                    "exclude": ["scripts/**"],
                    "buildCommands": [["{python}", "dev/scripts/package_devflow_release_runtime.py"]],
                    "managedOutputs": [
                        "scripts/devflow_runtime.pyz",
                        "scripts/devflow_runtime.MANIFEST.json",
                        "scripts/devflow_runtime.sha256",
                        "scripts/devflow_runtime.SOURCE_COMMIT",
                    ],
                }
            )
        )
        (repo / "dev" / "scripts").mkdir(parents=True, exist_ok=True)
        (repo / "dev" / "scripts" / "package_devflow_release_runtime.py").write_text(
            "# fixture packager\n"
        )
        (repo / "dev" / "scripts" / "run_devflow_prepromotion_tests.py").write_text(
            "# fixture pre-promotion suite\n"
        )
        (release_root / "docs").mkdir(parents=True)
        vendor_root = release_root / "vendor" / "mattpocock-skills"
        skill_names = [
            "grilling",
            "tdd",
            "diagnosing-bugs",
            "code-review",
            "codebase-design",
            "domain-modeling",
        ]
        file_hashes = {}
        skill_hashes = {}
        for skill_name in skill_names:
            skill_path = vendor_root / skill_name / "SKILL.md"
            skill_path.parent.mkdir(parents=True, exist_ok=True)
            skill_path.write_text(f"# {skill_name}\n")
            digest = hashlib.sha256(skill_path.read_bytes()).hexdigest()
            file_hashes[f"{skill_name}/SKILL.md"] = digest
            skill_hashes[skill_name] = digest
        license_path = vendor_root / "UPSTREAM_LICENSE.txt"
        license_path.write_text("MIT\n")
        (release_root / "docs" / "dependency-provenance.json").write_text(
            json.dumps(
                {
                    "schemaVersion": 3,
                    "methodology": {
                        "name": "mattpocock-skills",
                        "repository": "mattpocock/skills",
                        "ref": "v1.1.0",
                        "commit": "d574778f94cf620fcc8ce741584093bc650a61d3",
                        "skillHashes": skill_hashes,
                        "fileHashes": file_hashes,
                        "licensePath": "vendor/mattpocock-skills/UPSTREAM_LICENSE.txt",
                        "licenseSha256": hashlib.sha256(license_path.read_bytes()).hexdigest(),
                    },
                }
            )
        )
        (source_scripts / "tool.py").write_text("print('runtime tool')\n")
        (source_scripts / "verify_release_runtime.py").write_text("print('verify wrapper')\n")
        (release_root / "README.md").write_text(
            "Run python3 scripts/verify_release_runtime.py --plugin-root plugins/dev-flow --json\n"
        )
        return source_scripts, release_root, release_scripts

    def package_runtime_fixture(self, repo):
        source_scripts, release_root, release_scripts = self.write_runtime_packaging_fixture(repo)
        module = self.load_runtime_packager()
        module.REPO_ROOT = repo
        module.SOURCE_SCRIPTS = source_scripts
        module.RELEASE_SCRIPTS = release_scripts
        module.ENTRYPOINT_SCAN_ROOTS = (release_root / "README.md",)

        exit_code = module.main()

        self.assertEqual(exit_code, 0)
        return release_root, release_scripts

    def test_runtime_packager_writes_manifest_checksum_and_source_commit(self):
        repo = self.make_repo()
        _, release_scripts = self.package_runtime_fixture(repo)

        archive = release_scripts / "devflow_runtime.pyz"
        manifest_path = release_scripts / "devflow_runtime.MANIFEST.json"
        sha_path = release_scripts / "devflow_runtime.sha256"
        commit_path = release_scripts / "devflow_runtime.SOURCE_COMMIT"

        self.assertTrue(archive.exists())
        self.assertTrue(manifest_path.exists())
        self.assertTrue(sha_path.exists())
        self.assertTrue(commit_path.exists())

        archive_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
        manifest = json.loads(manifest_path.read_text())
        self.assertEqual(
            manifest["buildCommand"],
            [sys.executable, "dev/scripts/package_devflow_release_runtime.py"],
        )
        self.assertEqual(manifest["archive"]["path"], "scripts/devflow_runtime.pyz")
        self.assertEqual(manifest["archive"]["sha256"], archive_sha)
        self.assertEqual(sha_path.read_text(), f"{archive_sha}  scripts/devflow_runtime.pyz\n")
        self.assertEqual(commit_path.read_text().strip(), manifest["sourceCommit"])

        sources = {item["path"]: item for item in manifest["sources"]}
        self.assertIn("dev/plugins/dev-flow/scripts/tool.py", sources)
        self.assertIn("dev/plugins/dev-flow/scripts/verify_release_runtime.py", sources)
        self.assertTrue(
            all(path.startswith("dev/plugins/dev-flow/scripts/") for path in sources),
            sources,
        )
        self.assertEqual(
            sources["dev/plugins/dev-flow/scripts/tool.py"]["sha256"],
            hashlib.sha256((repo / "dev" / "plugins" / "dev-flow" / "scripts" / "tool.py").read_bytes()).hexdigest(),
        )

    def test_generated_wrapper_does_not_write_bytecode(self):
        repo = self.make_repo()
        release_root, release_scripts = self.package_runtime_fixture(repo)
        before = {
            path.relative_to(release_root).as_posix()
            for path in release_root.rglob("*")
            if path.is_file()
        }
        environment = os.environ.copy()
        environment.pop("PYTHONDONTWRITEBYTECODE", None)

        result = subprocess.run(
            [sys.executable, str(release_scripts / "verify_release_runtime.py")],
            text=True,
            capture_output=True,
            check=False,
            env=environment,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        after = {
            path.relative_to(release_root).as_posix()
            for path in release_root.rglob("*")
            if path.is_file()
        }
        self.assertEqual(after, before)

    def test_runtime_verification_command_passes_then_detects_archive_drift(self):
        verifier = SCRIPTS / "verify_release_runtime.py"
        self.assertTrue(verifier.exists())
        repo = self.make_repo()
        release_root, release_scripts = self.package_runtime_fixture(repo)

        ok = subprocess.run(
            [
                sys.executable,
                str(verifier),
                "--plugin-root",
                str(release_root),
                "--repo-root",
                str(repo),
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertTrue(json.loads(ok.stdout)["ok"])
        check_names = {check["name"] for check in json.loads(ok.stdout)["checks"]}
        self.assertIn("runtime archive members match manifest sources", check_names)
        self.assertIn("methodology identity is pinned", check_names)
        self.assertIn("methodology skill set is exact", check_names)

        with (release_scripts / "devflow_runtime.pyz").open("ab") as archive:
            archive.write(b"drift")

        drift = subprocess.run(
            [
                sys.executable,
                str(verifier),
                "--plugin-root",
                str(release_root),
                "--repo-root",
                str(repo),
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(drift.returncode, 0)
        payload = json.loads(drift.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["status"], "drift")
        self.assertIn("rebuild release runtime", payload["nextAction"])

    def test_dry_run_detects_plugin_drift_and_apply_copies_runtime_allowlist(self):
        repo = self.make_repo()
        _, release_root = self.write_plugin(repo)

        dry_run = sync_release_assets(repo, apply=False)

        self.assertEqual(dry_run["status"], "pending", dry_run)
        asset = dry_run["assets"][0]
        self.assertEqual(asset["kind"], "plugin")
        self.assertIn("skills/demo/SKILL.md", asset["changedFiles"])
        self.assertIn("docs/dependency-provenance.json", asset["changedFiles"])
        self.assertNotIn("docs/history/draft.md", asset["changedFiles"])
        self.assertNotIn("tests/test_dev_only.py", asset["changedFiles"])
        self.assertNotIn("log/debug.log", asset["changedFiles"])

        applied = self.apply_with_internal_test_authorization(repo, ["sample"])

        self.assertEqual(applied["status"], "synced", applied)
        self.assertEqual(
            (release_root / "skills" / "demo" / "SKILL.md").read_text(),
            "---\nname: demo\ndescription: dev\n---\n",
        )
        self.assertEqual(
            (release_root / "docs" / "dependency-provenance.json").read_text(),
            '{"schemaVersion":2}\n',
        )
        self.assertFalse((release_root / "docs" / "history" / "draft.md").exists())
        self.assertFalse((release_root / "tests" / "test_dev_only.py").exists())
        self.assertFalse((release_root / "log" / "debug.log").exists())

    def test_release_metadata_can_publish_one_explicit_smoke_test(self):
        repo = self.make_repo()
        dev_root, release_root = self.write_plugin(
            repo,
            sync_config={
                "include": ["tests/test_release_smoke.py"],
                "defaultExcludeOverrides": ["tests/**"],
            },
        )
        (dev_root / "tests" / "test_release_smoke.py").write_text(
            "RELEASE_SMOKE = True\n"
        )

        dry_run = sync_release_assets(repo, apply=False, targets=["sample"])

        self.assertIn("tests/test_release_smoke.py", dry_run["assets"][0]["changedFiles"])
        self.assertNotIn("tests/test_dev_only.py", dry_run["assets"][0]["changedFiles"])

        applied = self.apply_with_internal_test_authorization(repo, ["sample"])

        self.assertEqual(applied["status"], "synced", applied)
        self.assertTrue((release_root / "tests" / "test_release_smoke.py").is_file())
        self.assertFalse((release_root / "tests" / "test_dev_only.py").exists())

    def test_release_sync_rejects_unknown_default_exclude_override(self):
        repo = self.make_repo()
        self.write_plugin(
            repo,
            sync_config={
                "include": ["tests/test_release_smoke.py"],
                "defaultExcludeOverrides": ["../outside/**"],
            },
        )

        with self.assertRaisesRegex(ValueError, "defaultExcludeOverrides"):
            sync_release_assets(repo, apply=False, targets=["sample"])

    def test_dry_run_detects_release_only_file_and_apply_deletes_it(self):
        repo = self.make_repo()
        dev_root, release_root = self.write_plugin(repo)
        (release_root / "docs").mkdir()
        stale = release_root / "docs" / "removed.md"
        stale.write_text("release-only\n")
        (release_root / "skills" / "demo" / "SKILL.md").write_text(
            (dev_root / "skills" / "demo" / "SKILL.md").read_text()
        )

        dry_run = sync_release_assets(repo, apply=False, targets=["sample"])
        applied = self.apply_with_internal_test_authorization(repo, ["sample"])

        self.assertEqual(dry_run["status"], "pending", dry_run)
        self.assertIn("docs/removed.md", dry_run["assets"][0]["staleFiles"])
        self.assertEqual(applied["status"], "synced", applied)
        self.assertIn("docs/removed.md", applied["assets"][0]["deletedFiles"])
        self.assertFalse(stale.exists())

    def test_release_sync_rejects_source_and_target_symlink_escape(self):
        for location in ("source", "target"):
            with self.subTest(location=location):
                repo = self.make_repo()
                dev_root, release_root = self.write_plugin(repo)
                outside = repo / "outside.txt"
                outside.write_text("outside\n")
                parent = dev_root / "docs" if location == "source" else release_root / "docs"
                parent.mkdir(exist_ok=True)
                (parent / "escape.md").symlink_to(outside)

                with self.assertRaisesRegex(ValueError, "symlink"):
                    sync_release_assets(repo, apply=False, targets=["sample"])

    def test_release_sync_rejects_managed_output_commands_without_executing_them(self):
        repo = self.make_repo()
        marker = repo / "dry-run-command-executed.txt"
        command = (
            "from pathlib import Path; "
            f"Path({str(marker)!r}).write_text('executed\\n')"
        )
        self.write_plugin(
            repo,
            sync_config={
                "managedOutputCommands": [[sys.executable, "-c", command]],
            },
        )

        with self.assertRaisesRegex(ValueError, "managedOutputCommands are not allowed"):
            sync_release_assets(repo, apply=False, targets=["sample"])
        self.assertFalse(marker.exists())

    def test_build_failure_rolls_back_entire_release_tree(self):
        repo = self.make_repo()
        command = (
            "from pathlib import Path; "
            "p=Path('plugins/sample/scripts/generated.py'); "
            "p.parent.mkdir(parents=True, exist_ok=True); "
            "p.write_text('partial\\n'); "
            "raise SystemExit(7)"
        )
        _, release_root = self.write_plugin(
            repo,
            sync_config={
                "exclude": ["scripts/**"],
                "buildCommands": [["python3", "-c", command]],
                "managedOutputs": ["scripts/generated.py"],
            },
        )
        (release_root / "sentinel.txt").write_text("original\n")
        before = {
            path.relative_to(release_root).as_posix(): path.read_bytes()
            for path in release_root.rglob("*")
            if path.is_file()
        }

        with self.assertRaisesRegex(RuntimeError, "build command failed"):
            self.apply_with_internal_test_authorization(repo, ["sample"])

        after = {
            path.relative_to(release_root).as_posix(): path.read_bytes()
            for path in release_root.rglob("*")
            if path.is_file()
        }
        self.assertEqual(after, before)
        self.assertFalse((release_root / "scripts" / "generated.py").exists())
        self.assertEqual(list((repo / "plugins").glob(".*.release-sync-*")), [])

    def test_post_build_verification_failure_rolls_back_release_tree(self):
        repo = self.make_repo()
        _, release_root = self.write_plugin(
            repo,
            sync_config={
                "exclude": ["scripts/**"],
                "buildCommands": [["python3", "-c", "print('build succeeded')"]],
                "managedOutputs": ["scripts/missing.py"],
            },
        )
        before = (release_root / "skills" / "demo" / "SKILL.md").read_text()

        with self.assertRaisesRegex(RuntimeError, "verification failed"):
            self.apply_with_internal_test_authorization(repo, ["sample"])

        self.assertEqual((release_root / "skills" / "demo" / "SKILL.md").read_text(), before)
        self.assertFalse((release_root / "scripts" / "missing.py").exists())
        self.assertEqual(list((repo / "plugins").glob(".*.release-sync-*")), [])

    def test_later_target_build_failure_rolls_back_earlier_target(self):
        repo = self.make_repo()
        success = (
            "from pathlib import Path; "
            "p=Path('plugins/sample/scripts/generated.py'); "
            "p.parent.mkdir(parents=True, exist_ok=True); "
            "p.write_text('sample\\n')"
        )
        failure = (
            "from pathlib import Path; "
            "p=Path('plugins/other/scripts/generated.py'); "
            "p.parent.mkdir(parents=True, exist_ok=True); "
            "p.write_text('other-partial\\n'); "
            "raise SystemExit(9)"
        )
        _, sample_release = self.write_plugin(
            repo,
            "sample",
            sync_config={
                "exclude": ["scripts/**"],
                "buildCommands": [["python3", "-c", success]],
                "managedOutputs": ["scripts/generated.py"],
            },
        )
        _, other_release = self.write_plugin(
            repo,
            "other",
            sync_config={
                "exclude": ["scripts/**"],
                "buildCommands": [["python3", "-c", failure]],
                "managedOutputs": ["scripts/generated.py"],
            },
        )

        with self.assertRaisesRegex(RuntimeError, "build command failed"):
            self.apply_with_internal_test_authorization(repo, ["sample", "other"])

        self.assertEqual((sample_release / "skills" / "demo" / "SKILL.md").read_text(), "old\n")
        self.assertEqual((other_release / "skills" / "demo" / "SKILL.md").read_text(), "old\n")
        self.assertFalse((sample_release / "scripts" / "generated.py").exists())
        self.assertFalse((other_release / "scripts" / "generated.py").exists())
        self.assertEqual(list((repo / "plugins").glob(".*.release-sync-*")), [])

    def test_concurrent_target_change_after_prepare_stops_before_promotion(self):
        repo = self.make_repo()
        _, sample_release = self.write_plugin(repo, "sample")
        _, other_release = self.write_plugin(repo, "other")
        original_prepare = workflow_release_sync.prepare_release
        prepare_count = 0

        def prepare_then_mutate_target(repo_path, asset):
            nonlocal prepare_count
            prepared = original_prepare(repo_path, asset)
            prepare_count += 1
            if prepare_count == 2:
                (sample_release / "concurrent.txt").write_text("concurrent\n")
            return prepared

        with mock.patch.object(
            workflow_release_sync,
            "prepare_release",
            side_effect=prepare_then_mutate_target,
        ):
            with self.assertRaisesRegex(RuntimeError, "target changed after preparation"):
                self.apply_with_internal_test_authorization(repo, ["sample", "other"])

        self.assertEqual((sample_release / "concurrent.txt").read_text(), "concurrent\n")
        self.assertEqual((sample_release / "skills" / "demo" / "SKILL.md").read_text(), "old\n")
        self.assertEqual((other_release / "skills" / "demo" / "SKILL.md").read_text(), "old\n")
        self.assertEqual(list((repo / "plugins").glob(".*.release-sync-*")), [])

    def test_real_devflow_metadata_and_packager_apply_then_become_current(self):
        repo = self.make_repo()
        source_root = repo / "dev" / "plugins" / "dev-flow"
        release_root = repo / "plugins" / "dev-flow"
        (source_root / ".codex-plugin").mkdir(parents=True)
        release_root.mkdir(parents=True)
        (source_root / ".codex-plugin" / "plugin.json").write_text(
            json.dumps({"name": "dev-flow", "skills": "./skills/", "hooks": "./hooks.json"})
        )
        real_metadata = PLUGIN_ROOT / ".codex-plugin" / "release-sync.json"
        shutil.copy2(real_metadata, source_root / ".codex-plugin" / "release-sync.json")
        source_scripts = source_root / "scripts"
        source_scripts.mkdir()
        executable_names = (
            "devflow_stop_hook.py",
            "inspect_legacy_workflow_config.py",
            "verify_release_runtime.py",
        )
        for name in (*executable_names, "referenced_extra.py", "internal_only.py"):
            path = source_scripts / name
            path.write_text(f"print({name!r})\n")
            path.chmod(0o755 if name in executable_names else 0o644)
        (source_root / "hooks.json").write_text(
            json.dumps(
                {
                    "hooks": {
                        "Stop": [
                            {
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": "python3 scripts/referenced_extra.py",
                                    }
                                ]
                            }
                        ]
                    }
                }
            )
        )
        repo_packager = repo / "dev" / "scripts" / "package_devflow_release_runtime.py"
        repo_packager.parent.mkdir(parents=True)
        shutil.copy2(
            PLUGIN_ROOT.parents[2] / "dev" / "scripts" / "package_devflow_release_runtime.py",
            repo_packager,
        )
        shutil.copy2(
            PLUGIN_ROOT.parents[2] / "dev" / "scripts" / "run_devflow_prepromotion_tests.py",
            repo / "dev" / "scripts" / "run_devflow_prepromotion_tests.py",
        )
        metadata = json.loads((source_root / ".codex-plugin" / "release-sync.json").read_text())
        packager = self.load_runtime_packager()
        packager.REPO_ROOT = repo
        packager.SOURCE_SCRIPTS = source_scripts
        packager.RELEASE_SCRIPTS = release_root / "scripts"
        packager.ENTRYPOINT_SCAN_ROOTS = (
            source_root / "hooks.json",
            source_root / "README.md",
            source_root / "skills",
        )
        metadata["managedOutputs"] = packager.managed_output_paths(packager.iter_source_scripts())
        (source_root / ".codex-plugin" / "release-sync.json").write_text(json.dumps(metadata))
        (release_root / "release-only.txt").write_text("stale\n")

        first = self.apply_with_internal_test_authorization(repo, ["dev-flow"])
        second = self.apply_with_internal_test_authorization(repo, ["dev-flow"])

        self.assertEqual(first["status"], "synced", first)
        self.assertIn("release-only.txt", first["assets"][0]["deletedFiles"])
        self.assertTrue((release_root / "scripts" / "referenced_extra.py").is_file())
        self.assertFalse((release_root / "scripts" / "internal_only.py").exists())
        self.assertTrue((release_root / "scripts" / "devflow_runtime.pyz").is_file())
        self.assertEqual(second["status"], "current", second)
        self.assertEqual(second["assets"][0]["staleFiles"], [])
        self.assertEqual(second["assets"][0]["changedOutputs"], [])

    def test_release_sync_metadata_excludes_raw_paths_and_runs_build_commands(self):
        repo = self.make_repo()
        command = (
            "from pathlib import Path; "
            "p=Path('plugins/sample/scripts/generated.py'); "
            "p.parent.mkdir(parents=True, exist_ok=True); "
            "p.write_text('generated\\n')"
        )
        _, release_root = self.write_plugin(
            repo,
            sync_config={
                "exclude": ["scripts/**"],
                "buildCommands": [["python3", "-c", command]],
                "managedOutputs": ["scripts/generated.py"],
            },
        )

        report = self.apply_with_internal_test_authorization(repo, ["sample"])

        self.assertEqual(report["status"], "synced", report)
        self.assertEqual(report["assets"][0]["changedOutputs"], ["scripts/generated.py"])
        self.assertFalse((release_root / "scripts" / "tool.py").exists())
        self.assertEqual((release_root / "scripts" / "generated.py").read_text(), "generated\n")
        self.assertEqual(report["assets"][0]["buildCommands"], [["python3", "-c", command]])

    def test_release_promotion_gate_stays_current_when_build_outputs_are_idempotent(self):
        repo = self.make_repo()
        command = (
            "from pathlib import Path; "
            "p=Path('plugins/sample/scripts/generated.py'); "
            "p.parent.mkdir(parents=True, exist_ok=True); "
            "p.write_text('generated\\n')"
        )
        _, release_root = self.write_plugin(
            repo,
            sync_config={
                "exclude": ["scripts/**"],
                "buildCommands": [["python3", "-c", command]],
                "managedOutputs": ["scripts/generated.py"],
            },
        )
        shutil.copytree(
            repo / "dev" / "plugins" / "sample" / ".codex-plugin",
            release_root / ".codex-plugin",
        )
        (release_root / "skills" / "demo" / "SKILL.md").write_text("---\nname: demo\ndescription: dev\n---\n")
        (release_root / "docs").mkdir()
        (release_root / "docs" / "dependency-provenance.json").write_text('{"schemaVersion":2}\n')
        (release_root / "scripts").mkdir(exist_ok=True)
        (release_root / "scripts" / "generated.py").write_text("generated\n")
        self.write_state(repo, verification_passed=True, release_allowed=True)
        self.write_release_verification(repo, "sample")

        report = run_gate(repo, apply=True, target="sample")

        self.assertEqual(report["status"], "current", report)
        self.assertNotIn("release validation", report["message"])

    def test_release_eval_target_prefers_release_counterpart_for_dev_assets(self):
        repo = self.make_repo()
        dev_plugin, release_plugin = self.write_plugin(repo)
        dev_skill, release_skill = self.write_skill(repo)

        plugin_target = release_eval_target(repo, dev_plugin)
        skill_target = release_eval_target(repo, dev_skill)
        release_target = release_eval_target(repo, release_plugin)

        self.assertEqual(plugin_target["target"], str(release_plugin.resolve()))
        self.assertTrue(plugin_target["releasePreferred"])
        self.assertEqual(skill_target["target"], str(release_skill.resolve()))
        self.assertEqual(release_target["target"], str(release_plugin.resolve()))

    def test_release_promotion_gate_only_syncs_after_verification_passes(self):
        repo = self.make_repo()
        _, release_root = self.write_plugin(repo)
        self.write_state(repo, verification_passed=False)

        before = run_gate(repo, apply=True, target="sample")

        self.assertEqual(before["status"], "not_applicable", before)
        self.assertEqual((release_root / "skills" / "demo" / "SKILL.md").read_text(), "old\n")

        self.write_state(repo, verification_passed=True, release_allowed=True)
        self.write_release_verification(repo, "sample")
        after = run_gate(repo, apply=True, target="sample")

        self.assertEqual(after["status"], "synced", after)
        self.assertIn("release validation", after["message"])
        self.assertIn("qualityGates", after)
        gate_commands = {gate["name"]: " ".join(gate["command"]) for gate in after["qualityGates"]}
        self.assertIn("release package verification", gate_commands)
        self.assertIn("Plugin Eval release", gate_commands)
        self.assertIn("test_release_package.py", gate_commands["release package verification"])
        self.assertIn(str(release_root), gate_commands["release package verification"])
        self.assertIn("plugin-eval", gate_commands["Plugin Eval release"])
        self.assertEqual(
            (release_root / "skills" / "demo" / "SKILL.md").read_text(),
            "---\nname: demo\ndescription: dev\n---\n",
        )

    def test_focused_test_list_cannot_create_release_verification(self):
        repo = self.make_repo()
        self.write_plugin(repo)

        report = record_release_verification(
            repo,
            "sample",
            "release-fixture",
            development_command=(
                "python3.12 -m unittest dev.plugins.sample.tests.test_one "
                "test_two test_three test_four test_five"
            ),
            development_result="pass",
            openspec_command="openspec validate --all --strict",
            openspec_result="pass",
            diff_command="git diff --check",
            diff_result="pass",
        )

        self.assertFalse(report["ok"], report)
        self.assertTrue(
            any("canonical complete test command" in error for error in report["errors"]),
            report,
        )

    def test_release_source_snapshot_rejects_missing_declared_build_helper(self):
        repo = self.make_repo()
        self.write_plugin(
            repo,
            sync_config={
                "buildCommands": [["{python}", "dev/scripts/missing-build-helper.py"]],
            },
        )

        snapshot = release_source_snapshot(repo, "sample")

        self.assertFalse(snapshot["ready"], snapshot)
        self.assertIn(
            "dev/scripts/missing-build-helper.py",
            snapshot["untrustedPaths"],
        )

    def test_release_readiness_requires_implementation_done_and_verified_change(self):
        for state_overrides, blocker in (
            ({"implementation_done": False}, "implementation_done"),
            ({"change_status": "executing"}, "current_change_verified"),
        ):
            with self.subTest(blocker=blocker):
                repo = self.make_repo()
                self.write_plugin(repo)
                self.write_state(
                    repo,
                    verification_passed=True,
                    release_allowed=True,
                    **state_overrides,
                )
                self.write_release_verification(repo)

                readiness = release_promotion_readiness(
                    repo,
                    "sample",
                    require_authorization=True,
                )

                self.assertFalse(readiness["ready"], readiness)
                self.assertIn(blocker, readiness["blockers"])

    def test_release_readiness_rejects_stale_source_evidence(self):
        repo = self.make_repo()
        dev_root, _ = self.write_plugin(repo)
        self.write_state(repo, verification_passed=True, release_allowed=True)
        self.write_release_verification(repo)
        (dev_root / "skills" / "demo" / "SKILL.md").write_text("changed after receipt\n")

        readiness = release_promotion_readiness(
            repo,
            "sample",
            require_authorization=True,
        )

        self.assertFalse(readiness["ready"], readiness)
        self.assertEqual(readiness["evidence"]["status"], "stale_evidence")

    def test_apply_flag_without_durable_release_authorization_cannot_mutate(self):
        repo = self.make_repo()
        _, release_root = self.write_plugin(repo)
        self.write_state(repo, verification_passed=True, release_allowed=False)
        self.write_release_verification(repo)

        report = run_gate(repo, apply=True, target="sample")

        self.assertEqual(report["status"], "authorization_required", report)
        self.assertIn(
            "durable_release_authorization",
            report["releaseReadiness"]["blockers"],
        )
        self.assertEqual(
            (release_root / "skills" / "demo" / "SKILL.md").read_text(),
            "old\n",
        )

    def test_symlinked_external_state_cannot_authorize_release(self):
        repo = self.make_repo()
        _, release_root = self.write_plugin(repo)
        self.write_state(repo, verification_passed=True, release_allowed=True)
        self.write_release_verification(repo)
        outside = Path(tempfile.mkdtemp(prefix="devflow-release-state-outside-"))
        self.addCleanup(lambda: shutil.rmtree(outside, ignore_errors=True))
        planning = repo / ".planning"
        planning.replace(outside / "planning")
        planning.symlink_to(outside / "planning", target_is_directory=True)

        report = run_gate(repo, apply=True, target="sample")

        self.assertEqual(report["status"], "not_applicable", report)
        self.assertIn(
            "trusted_namespaced_state",
            report["releaseReadiness"]["blockers"],
        )
        self.assertEqual(
            (release_root / "skills" / "demo" / "SKILL.md").read_text(),
            "old\n",
        )

    def test_release_promotion_gate_is_dry_run_by_default(self):
        repo = self.make_repo()
        _, release_root = self.write_plugin(repo)
        self.write_state(repo, verification_passed=True)
        self.write_release_verification(repo, "sample")

        report = run_gate(repo, target="sample")

        self.assertEqual(report["status"], "pending", report)
        self.assertFalse(report["sideEffect"]["authorized"])
        self.assertEqual(report["sideEffect"]["denial"], "ready_not_applied")
        self.assertEqual((release_root / "skills" / "demo" / "SKILL.md").read_text(), "old\n")

    def test_devflow_metadata_builds_packaged_runtime_instead_of_copying_raw_scripts(self):
        metadata = json.loads((PLUGIN_ROOT / ".codex-plugin" / "release-sync.json").read_text())

        self.assertEqual(
            metadata["include"],
            [
                "tests/test_packaged_runtime.py",
                "vendor/**",
            ],
        )
        self.assertEqual(metadata["defaultExcludeOverrides"], ["tests/**"])
        self.assertIn("scripts/**", metadata["exclude"])
        self.assertEqual(metadata["buildCommands"], [["{python}", "dev/scripts/package_devflow_release_runtime.py"]])
        self.assertNotIn("managedOutputCommands", metadata)
        packager = self.load_runtime_packager()
        self.assertEqual(
            metadata["managedOutputs"],
            packager.managed_output_paths(packager.iter_source_scripts()),
        )
        self.assertIn("scripts/devflow_runtime.pyz", metadata["managedOutputs"])
        self.assertIn("scripts/devflow_runtime.MANIFEST.json", metadata["managedOutputs"])
        self.assertIn("scripts/devflow_runtime.sha256", metadata["managedOutputs"])
        self.assertIn("scripts/devflow_runtime.SOURCE_COMMIT", metadata["managedOutputs"])
        self.assertIn("scripts/devflow_launcher.py", metadata["managedOutputs"])
        self.assertIn("scripts/record_release_verification.py", metadata["managedOutputs"])
        self.assertIn("scripts/record_spec_sync.py", metadata["managedOutputs"])

    def test_devflow_stop_hook_uses_single_read_only_stop_entrypoint(self):
        hooks = json.loads((PLUGIN_ROOT / "hooks.json").read_text())["hooks"]
        stop_commands = [
            hook["command"]
            for entry in hooks["Stop"]
            for hook in entry.get("hooks", [])
        ]

        self.assertEqual(len(stop_commands), 1)
        self.assertIn("devflow_stop_hook.py", stop_commands[0])
        self.assertNotIn("release_promotion_gate.py", stop_commands[0])

    def test_apply_requires_gate_authorization_and_internal_grants_require_targets(self):
        repo = self.make_repo()
        _, sample_release = self.write_plugin(repo, "sample")
        _, other_release = self.write_plugin(repo, "other")

        denied_without_target = sync_release_assets(repo, apply=True)
        denied_with_target = sync_release_assets(repo, apply=True, targets=["sample"])
        denied_with_fake_authorization = sync_release_assets(
            repo,
            apply=True,
            targets=["sample"],
            _apply_authorization=object(),
        )

        self.assertEqual(denied_without_target["status"], "authorization_required")
        self.assertEqual(denied_with_target["status"], "authorization_required")
        self.assertEqual(
            denied_with_fake_authorization["status"],
            "authorization_required",
        )
        with self.assertRaisesRegex(ValueError, "explicit non-empty targets"):
            workflow_release_sync._issue_release_apply_authorization(repo, [])
        self.assertEqual((other_release / "skills" / "demo" / "SKILL.md").read_text(), "old\n")
        self.assertEqual((sample_release / "skills" / "demo" / "SKILL.md").read_text(), "old\n")

    def test_private_authorization_factory_rejects_repo_without_passed_promotion_gate(self):
        repo = self.make_repo()
        self.write_plugin(repo, "sample")

        with self.assertRaisesRegex(PermissionError, "promotion verification"):
            workflow_release_sync._issue_release_apply_authorization(repo, ["sample"])

        self.write_state(repo, verification_passed=False)
        with self.assertRaisesRegex(PermissionError, "promotion verification"):
            workflow_release_sync._issue_release_apply_authorization(repo, ["sample"])

    def test_public_sync_cli_apply_is_denied_with_or_without_target(self):
        repo = self.make_repo()
        _, release_root = self.write_plugin(repo, "sample")

        for target_args in ([], ["--target", "sample"]):
            with self.subTest(target_args=target_args):
                completed = subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPTS / "sync_release_assets.py"),
                        "--repo",
                        str(repo),
                        "--apply",
                        *target_args,
                        "--json",
                    ],
                    text=True,
                    capture_output=True,
                    check=False,
                )

                self.assertEqual(completed.returncode, 2, completed.stderr)
                self.assertEqual(
                    json.loads(completed.stdout)["status"],
                    "authorization_required",
                )
        self.assertEqual((release_root / "skills" / "demo" / "SKILL.md").read_text(), "old\n")

    def test_release_apply_authorization_is_repo_and_target_bound_and_single_use(self):
        repo = self.make_repo()
        _, sample_release = self.write_plugin(repo, "sample")
        _, other_release = self.write_plugin(repo, "other")
        other_repo = self.make_repo()
        _, other_repo_release = self.write_plugin(other_repo, "sample")
        self.write_state(repo, verification_passed=True, release_allowed=True)
        self.write_state(other_repo, verification_passed=True, release_allowed=True)
        self.write_release_verification(repo, "sample")
        self.write_release_verification(repo, "other")
        self.write_release_verification(other_repo, "sample")

        repo_grant = workflow_release_sync._issue_release_apply_authorization(
            repo,
            ["sample"],
        )
        wrong_repo = sync_release_assets(
            other_repo,
            apply=True,
            targets=["sample"],
            _apply_authorization=repo_grant,
        )
        repo_grant_reuse = sync_release_assets(
            repo,
            apply=True,
            targets=["sample"],
            _apply_authorization=repo_grant,
        )

        target_grant = workflow_release_sync._issue_release_apply_authorization(
            repo,
            ["sample"],
        )
        wrong_target = sync_release_assets(
            repo,
            apply=True,
            targets=["other"],
            _apply_authorization=target_grant,
        )

        valid_grant = workflow_release_sync._issue_release_apply_authorization(
            repo,
            ["sample"],
        )
        applied = sync_release_assets(
            repo,
            apply=True,
            targets=["sample"],
            _apply_authorization=valid_grant,
        )
        valid_grant_reuse = sync_release_assets(
            repo,
            apply=True,
            targets=["sample"],
            _apply_authorization=valid_grant,
        )

        self.assertEqual(wrong_repo["status"], "authorization_required")
        self.assertEqual(repo_grant_reuse["status"], "authorization_required")
        self.assertEqual(wrong_target["status"], "authorization_required")
        self.assertEqual(applied["status"], "synced")
        self.assertEqual(valid_grant_reuse["status"], "authorization_required")
        self.assertEqual((other_repo_release / "skills" / "demo" / "SKILL.md").read_text(), "old\n")
        self.assertEqual((other_release / "skills" / "demo" / "SKILL.md").read_text(), "old\n")
        self.assertNotEqual((sample_release / "skills" / "demo" / "SKILL.md").read_text(), "old\n")

    def test_release_apply_authorization_expires_before_mutation(self):
        repo = self.make_repo()
        _, release_root = self.write_plugin(repo, "sample")
        self.write_state(repo, verification_passed=True, release_allowed=True)
        self.write_release_verification(repo, "sample")

        with mock.patch.object(
            workflow_release_sync.time,
            "monotonic",
            side_effect=[100.0, 106.0],
        ):
            grant = workflow_release_sync._issue_release_apply_authorization(
                repo,
                ["sample"],
            )
            report = sync_release_assets(
                repo,
                apply=True,
                targets=["sample"],
                _apply_authorization=grant,
            )

        self.assertEqual(report["status"], "authorization_required")
        self.assertEqual((release_root / "skills" / "demo" / "SKILL.md").read_text(), "old\n")

    def test_quality_gate_selects_devflow_eval_target_by_identity(self):
        report = {
            "evalTargets": [
                {"kind": "plugin", "name": "agent-kb", "target": "/release/agent-kb"},
                {"kind": "plugin", "name": "dev-flow", "target": "/release/dev-flow"},
            ]
        }

        gates = quality_gates(report)
        plugin_eval = next(gate for gate in gates if gate["name"] == "Plugin Eval release")

        self.assertEqual(plugin_eval["command"][2], "/release/dev-flow")

    def test_dry_run_detects_stale_runtime_manifest_source_hash(self):
        repo = self.make_repo()
        release_root, _ = self.package_runtime_fixture(repo)
        source = repo / "dev" / "plugins" / "dev-flow" / "scripts" / "tool.py"
        source.write_text("print('changed runtime tool')\n")

        report = sync_release_assets(repo, apply=False, targets=["dev-flow"])

        self.assertEqual(report["status"], "pending")
        asset = report["assets"][0]
        self.assertIn("scripts/devflow_runtime.MANIFEST.json", asset["staleOutputs"])

    def test_dry_run_detects_runtime_module_missing_from_manifest(self):
        repo = self.make_repo()
        release_root, _ = self.package_runtime_fixture(repo)
        source = repo / "dev" / "plugins" / "dev-flow" / "scripts" / "new_runtime_module.py"
        source.write_text("VALUE = 1\n")

        report = sync_release_assets(repo, apply=False, targets=[release_root.name])

        self.assertEqual(report["status"], "pending")
        self.assertIn(
            "scripts/devflow_runtime.MANIFEST.json",
            report["assets"][0]["staleOutputs"],
        )


def hook_index(commands, name):
    return next(index for index, command in enumerate(commands) if name in command)


if __name__ == "__main__":
    unittest.main()
