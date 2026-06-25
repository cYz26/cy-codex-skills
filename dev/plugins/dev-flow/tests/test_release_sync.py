import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from release_promotion_gate import run_gate
from workflow_release_sync import release_eval_target, sync_release_assets


class ReleaseSyncTests(unittest.TestCase):
    def make_repo(self):
        repo = Path(tempfile.mkdtemp(prefix="devflow-release-sync-"))
        self.addCleanup(lambda: shutil.rmtree(repo, ignore_errors=True))
        return repo

    def write_plugin(self, repo, name="sample", *, release=True, sync_config=None):
        dev_root = repo / "dev" / "plugins" / name
        release_root = repo / "plugins" / name
        (dev_root / ".codex-plugin").mkdir(parents=True)
        (dev_root / ".codex-plugin" / "plugin.json").write_text(
            json.dumps({"name": name, "skills": "./skills/", "hooks": "./hooks.json"})
        )
        if sync_config is not None:
            (dev_root / ".codex-plugin" / "release-sync.json").write_text(json.dumps(sync_config))
        (dev_root / "skills" / "demo").mkdir(parents=True)
        (dev_root / "skills" / "demo" / "SKILL.md").write_text("---\nname: demo\ndescription: dev\n---\n")
        (dev_root / "scripts").mkdir()
        (dev_root / "scripts" / "tool.py").write_text("print('dev')\n")
        (dev_root / "docs").mkdir()
        (dev_root / "docs" / "dependency-provenance.json").write_text('{"schemaVersion":2}\n')
        (dev_root / "docs" / "superpowers" / "plans").mkdir(parents=True)
        (dev_root / "docs" / "superpowers" / "plans" / "draft.md").write_text("draft\n")
        (dev_root / "tests").mkdir()
        (dev_root / "tests" / "test_dev_only.py").write_text("SHOULD_NOT_RELEASE = True\n")
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

    def write_state(self, repo, *, verification_passed):
        (repo / ".planning").mkdir(exist_ok=True)
        value = "true" if verification_passed else "false"
        (repo / ".planning" / "STATE.md").write_text(
            f"""---
workflow_version: 0.3.0
current_stage: executing
gates:
  verification_passed: {value}
context_management:
  compact_status: not_needed
---
# State
"""
        )

    def load_runtime_packager(self):
        path = PLUGIN_ROOT.parents[2] / "dev" / "scripts" / "package_devflow_release_runtime.py"
        spec = importlib.util.spec_from_file_location("package_devflow_release_runtime_fixture", path)
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        return module

    def write_runtime_packaging_fixture(self, repo):
        source_scripts = repo / "dev" / "plugins" / "dev-flow" / "scripts"
        release_root = repo / "plugins" / "dev-flow"
        release_scripts = release_root / "scripts"
        source_scripts.mkdir(parents=True)
        release_scripts.mkdir(parents=True)
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
        self.assertEqual(manifest["buildCommand"], ["python3", "dev/scripts/package_devflow_release_runtime.py"])
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
        self.assertNotIn("docs/superpowers/plans/draft.md", asset["changedFiles"])
        self.assertNotIn("tests/test_dev_only.py", asset["changedFiles"])
        self.assertNotIn("log/debug.log", asset["changedFiles"])

        applied = sync_release_assets(repo, apply=True)

        self.assertEqual(applied["status"], "synced", applied)
        self.assertEqual(
            (release_root / "skills" / "demo" / "SKILL.md").read_text(),
            "---\nname: demo\ndescription: dev\n---\n",
        )
        self.assertEqual(
            (release_root / "docs" / "dependency-provenance.json").read_text(),
            '{"schemaVersion":2}\n',
        )
        self.assertFalse((release_root / "docs" / "superpowers" / "plans" / "draft.md").exists())
        self.assertFalse((release_root / "tests" / "test_dev_only.py").exists())
        self.assertFalse((release_root / "log" / "debug.log").exists())

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

        report = sync_release_assets(repo, apply=True)

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
        self.write_state(repo, verification_passed=True)

        report = run_gate(repo, apply=True)

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

        before = run_gate(repo, apply=True)

        self.assertEqual(before["status"], "not_applicable", before)
        self.assertEqual((release_root / "skills" / "demo" / "SKILL.md").read_text(), "old\n")

        self.write_state(repo, verification_passed=True)
        after = run_gate(repo, apply=True)

        self.assertEqual(after["status"], "synced", after)
        self.assertIn("release validation", after["message"])
        self.assertIn("qualityGates", after)
        gate_commands = {gate["name"]: " ".join(gate["command"]) for gate in after["qualityGates"]}
        self.assertIn("release runtime verification", gate_commands)
        self.assertIn("Plugin Eval release", gate_commands)
        self.assertIn("verify_release_runtime.py", gate_commands["release runtime verification"])
        self.assertIn("plugin-eval", gate_commands["Plugin Eval release"])
        self.assertEqual(
            (release_root / "skills" / "demo" / "SKILL.md").read_text(),
            "---\nname: demo\ndescription: dev\n---\n",
        )

    def test_devflow_metadata_builds_packaged_runtime_instead_of_copying_raw_scripts(self):
        metadata = json.loads((PLUGIN_ROOT / ".codex-plugin" / "release-sync.json").read_text())

        self.assertIn("scripts/**", metadata["exclude"])
        self.assertEqual(metadata["buildCommands"], [["python3", "dev/scripts/package_devflow_release_runtime.py"]])
        self.assertIn("scripts/devflow_runtime.pyz", metadata["managedOutputs"])
        self.assertIn("scripts/devflow_runtime.MANIFEST.json", metadata["managedOutputs"])
        self.assertIn("scripts/devflow_runtime.sha256", metadata["managedOutputs"])
        self.assertIn("scripts/devflow_runtime.SOURCE_COMMIT", metadata["managedOutputs"])
        self.assertIn("scripts/verify_release_runtime.py", metadata["managedOutputs"])

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


def hook_index(commands, name):
    return next(index for index, command in enumerate(commands) if name in command)


if __name__ == "__main__":
    unittest.main()
