import json
import shutil
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

    def test_dry_run_detects_plugin_drift_and_apply_copies_runtime_allowlist(self):
        repo = self.make_repo()
        _, release_root = self.write_plugin(repo)

        dry_run = sync_release_assets(repo, apply=False)

        self.assertEqual(dry_run["status"], "pending", dry_run)
        asset = dry_run["assets"][0]
        self.assertEqual(asset["kind"], "plugin")
        self.assertIn("skills/demo/SKILL.md", asset["changedFiles"])
        self.assertNotIn("tests/test_dev_only.py", asset["changedFiles"])
        self.assertNotIn("log/debug.log", asset["changedFiles"])

        applied = sync_release_assets(repo, apply=True)

        self.assertEqual(applied["status"], "synced", applied)
        self.assertEqual(
            (release_root / "skills" / "demo" / "SKILL.md").read_text(),
            "---\nname: demo\ndescription: dev\n---\n",
        )
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
        self.assertFalse((release_root / "scripts" / "tool.py").exists())
        self.assertEqual((release_root / "scripts" / "generated.py").read_text(), "generated\n")
        self.assertEqual(report["assets"][0]["buildCommands"], [["python3", "-c", command]])

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
        self.assertEqual(
            (release_root / "skills" / "demo" / "SKILL.md").read_text(),
            "---\nname: demo\ndescription: dev\n---\n",
        )

    def test_devflow_metadata_builds_packaged_runtime_instead_of_copying_raw_scripts(self):
        metadata = json.loads((PLUGIN_ROOT / ".codex-plugin" / "release-sync.json").read_text())

        self.assertIn("scripts/**", metadata["exclude"])
        self.assertEqual(metadata["buildCommands"], [["python3", "dev/scripts/package_devflow_release_runtime.py"]])
        self.assertIn("scripts/devflow_runtime.pyz", metadata["managedOutputs"])

    def test_devflow_stop_hook_runs_release_promotion_after_verification_gate(self):
        hooks = json.loads((PLUGIN_ROOT / "hooks.json").read_text())["hooks"]
        stop_commands = [
            hook["command"]
            for entry in hooks["Stop"]
            for hook in entry.get("hooks", [])
        ]

        verification_index = hook_index(stop_commands, "stop_verification_policy.py")
        promotion_index = hook_index(stop_commands, "release_promotion_gate.py")
        checkpoint_index = hook_index(stop_commands, "stop_checkpoint_policy.py")

        self.assertLess(verification_index, promotion_index)
        self.assertLess(promotion_index, checkpoint_index)


def hook_index(commands, name):
    return next(index for index, command in enumerate(commands) if name in command)


if __name__ == "__main__":
    unittest.main()
