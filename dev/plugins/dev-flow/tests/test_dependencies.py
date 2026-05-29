import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TEST_ROOT = Path(__file__).resolve().parent
PLUGIN_ROOT_FOR_IMPORTS = TEST_ROOT.parent
sys.path.insert(0, str(TEST_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT_FOR_IMPORTS / "scripts"))

from dependency_support import (
    DEV_MARKETPLACE,
    DependencyFixtureMixin,
    MARKETPLACE,
    PLUGIN_ROOT,
    RELEASE_PLUGIN_ROOT,
    run_json,
)

import codex_auto_update_plugins_skills as auto_update
from workflow_project_skill_install import ensure_project_local_skills


class DependencyTests(DependencyFixtureMixin, unittest.TestCase):

    def test_dependency_check_reports_ready_when_project_dependencies_are_active(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo()
        report = run_json(
            "check_dependencies.py",
            "--plugin-root",
            str(PLUGIN_ROOT),
            "--repo",
            str(repo),
            "--codex-home",
            str(codex_home),
            "--config",
            str(codex_home / "config.toml"),
            "--json",
        )
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["status"], "ready")
        checks = {item["name"]: item for item in report["checks"]}
        self.assertTrue(checks["global plugin inactive: superpowers"]["ok"])
        self.assertTrue(checks["global skill inactive: brainstorming"]["ok"])
        self.assertTrue(checks["global skill inactive: test-driven-development"]["ok"])
        self.assertTrue(checks["project skill active: project-orchestrator"]["ok"])
        self.assertTrue(checks["project skill active: context-tool-audit"]["ok"])
        self.assertTrue(checks["project skill active: brainstorming"]["ok"])
        self.assertTrue(checks["project skill active: writing-plans"]["ok"])
        self.assertTrue(checks["project skill active: test-driven-development"]["ok"])
        self.assertTrue(checks["external plugin installed: superpowers"]["ok"])
        self.assertTrue(checks["external skill available: superpowers:brainstorming"]["ok"])
        self.assertTrue(checks["external skill available: superpowers:writing-plans"]["ok"])
        self.assertTrue(checks["external skill available: superpowers:test-driven-development"]["ok"])
        self.assertTrue(checks["project skill active: gsd-new-project"]["ok"])
        self.assertTrue(checks["project skill active: gsd-progress"]["ok"])
        self.assertTrue(checks["project gsd agent active: gsd-planner.toml"]["ok"])
        self.assertTrue(checks["project openspec setup active"]["ok"])
        self.assertTrue(checks["developer plugin enabled: plugin-eval"]["ok"])

    def test_dependency_check_warns_when_superpowers_plugin_is_global(self):
        codex_home = self.make_codex_home(enable_superpowers_plugin=True)
        repo = self.make_project_repo(enable_legacy_openspec_skills=False)

        report = run_json(
            "check_dependencies.py",
            "--plugin-root",
            str(PLUGIN_ROOT),
            "--repo",
            str(repo),
            "--codex-home",
            str(codex_home),
            "--config",
            str(codex_home / "config.toml"),
            "--json",
        )

        checks = {item["name"]: item for item in report["checks"]}
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["status"], "ready_with_recommendations")
        self.assertFalse(checks["global plugin inactive: superpowers"]["ok"])
        self.assertFalse(checks["global plugin inactive: superpowers"]["required"])

    def test_dependency_check_accepts_openspec_config_without_legacy_openspec_skills(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo(enable_legacy_openspec_skills=False, enable_openspec_config=True)

        report = run_json(
            "check_dependencies.py",
            "--plugin-root",
            str(PLUGIN_ROOT),
            "--repo",
            str(repo),
            "--codex-home",
            str(codex_home),
            "--config",
            str(codex_home / "config.toml"),
            "--json",
        )

        checks = {item["name"]: item for item in report["checks"]}
        self.assertTrue(report["ok"], report)
        self.assertTrue(checks["project openspec setup active"]["ok"])
        self.assertTrue(checks["legacy project skill active: openspec-propose"]["required"] is False)
        self.assertFalse(checks["legacy project skill active: openspec-propose"]["ok"])

    def test_dependency_check_requires_openspec_config_when_legacy_skills_are_missing(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo(enable_legacy_openspec_skills=False, enable_openspec_config=False)

        result = subprocess.run(
            [
                sys.executable,
                str(PLUGIN_ROOT / "scripts" / "check_dependencies.py"),
                "--plugin-root",
                str(PLUGIN_ROOT),
                "--repo",
                str(repo),
                "--codex-home",
                str(codex_home),
                "--config",
                str(codex_home / "config.toml"),
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        required_failures = [item["name"] for item in report["checks"] if item["required"] and not item["ok"]]
        self.assertIn("project openspec setup active", required_failures)

    def test_dependency_check_fails_when_project_gsd_and_openspec_setup_are_missing(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo(enable_legacy_openspec_skills=False)
        for directory in [repo / ".codex" / "skills" / "gsd-new-project"]:
            for path in directory.rglob("*"):
                path.unlink()
            directory.rmdir()
        (repo / "openspec" / "config.yaml").unlink()

        result = subprocess.run(
            [
                sys.executable,
                str(PLUGIN_ROOT / "scripts" / "check_dependencies.py"),
                "--plugin-root",
                str(PLUGIN_ROOT),
                "--repo",
                str(repo),
                "--codex-home",
                str(codex_home),
                "--config",
                str(codex_home / "config.toml"),
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        required_failures = [item["name"] for item in report["checks"] if item["required"] and not item["ok"]]
        self.assertIn("project skill active: gsd-new-project", required_failures)
        self.assertIn("project openspec setup active", required_failures)

    def test_dependency_check_fails_when_gsd_progress_is_missing(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo()
        directory = repo / ".codex" / "skills" / "gsd-progress"
        for path in directory.rglob("*"):
            path.unlink()
        directory.rmdir()

        result = subprocess.run(
            [
                sys.executable,
                str(PLUGIN_ROOT / "scripts" / "check_dependencies.py"),
                "--plugin-root",
                str(PLUGIN_ROOT),
                "--repo",
                str(repo),
                "--codex-home",
                str(codex_home),
                "--config",
                str(codex_home / "config.toml"),
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        required_failures = [item["name"] for item in report["checks"] if item["required"] and not item["ok"]]
        self.assertIn("project skill active: gsd-progress", required_failures)

    def test_dependency_check_fails_when_superpowers_skill_is_global(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo()
        global_skill = codex_home / "skills" / "test-driven-development" / "SKILL.md"
        global_skill.parent.mkdir(parents=True)
        global_skill.write_text("---\nname: test-driven-development\ndescription: fixture\n---\n")

        result = subprocess.run(
            [
                sys.executable,
                str(PLUGIN_ROOT / "scripts" / "check_dependencies.py"),
                "--plugin-root",
                str(PLUGIN_ROOT),
                "--repo",
                str(repo),
                "--codex-home",
                str(codex_home),
                "--config",
                str(codex_home / "config.toml"),
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        required_failures = [item["name"] for item in report["checks"] if item["required"] and not item["ok"]]
        self.assertIn("global skill inactive: test-driven-development", required_failures)

    def test_dependency_check_fails_when_project_orchestrator_is_not_active(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo(enable_orchestrator=False)
        result = subprocess.run(
            [
                sys.executable,
                str(PLUGIN_ROOT / "scripts" / "check_dependencies.py"),
                "--plugin-root",
                str(PLUGIN_ROOT),
                "--repo",
                str(repo),
                "--codex-home",
                str(codex_home),
                "--config",
                str(codex_home / "config.toml"),
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        required_failures = [item["name"] for item in report["checks"] if item["required"] and not item["ok"]]
        self.assertIn("project skill active: project-orchestrator", required_failures)

    def test_activation_installs_project_local_skills_without_official_installs(self):
        repo = Path(tempfile.mkdtemp(prefix="cpo-activation-"))
        codex_home = self.make_codex_home()
        report = run_json(
            "activate_project_dependencies.py",
            "--repo",
            str(repo),
            "--plugin-root",
            str(PLUGIN_ROOT),
            "--codex-home",
            str(codex_home),
            "--skip-official-installs",
            "--json",
        )
        self.assertTrue(report["ok"], report)
        self.assertTrue((repo / ".codex" / "skills" / "project-orchestrator" / "SKILL.md").exists())
        self.assertTrue((repo / ".codex" / "skills" / "context-tool-audit" / "SKILL.md").exists())
        self.assertTrue((repo / ".codex" / "skills" / "brainstorming" / "SKILL.md").exists())
        self.assertTrue((repo / ".codex" / "skills" / "writing-plans" / "SKILL.md").exists())
        self.assertTrue((repo / ".codex" / "skills" / "test-driven-development" / "SKILL.md").exists())
        self.assertFalse((repo / ".codex" / "config.toml").exists())

    def test_activation_reports_stale_provider_symlink_without_refresh(self):
        repo = Path(tempfile.mkdtemp(prefix="cpo-refresh-repo-"))
        codex_home = self.make_codex_home()
        plugin_root = PLUGIN_ROOT
        old_source = (
            codex_home
            / "plugins"
            / "cache"
            / "openai-curated"
            / "superpowers"
            / "000-old"
            / "skills"
            / "brainstorming"
        )
        old_source.mkdir(parents=True)
        (old_source / "SKILL.md").write_text("---\nname: brainstorming\ndescription: old\n---\n")
        target = repo / ".codex" / "skills" / "brainstorming"
        target.parent.mkdir(parents=True)
        target.symlink_to(old_source, target_is_directory=True)

        report = ensure_project_local_skills(repo, plugin_root, codex_home, dry_run=True)
        brainstorming = next(item for item in report["items"] if item["skill"] == "brainstorming")

        self.assertEqual(brainstorming["status"], "already-linked-existing-source")
        self.assertEqual(Path(brainstorming["target"]).resolve(), old_source.resolve())

    def test_activation_refreshes_stale_provider_symlink_when_requested(self):
        repo = Path(tempfile.mkdtemp(prefix="cpo-refresh-repo-"))
        codex_home = self.make_codex_home()
        plugin_root = PLUGIN_ROOT
        old_source = (
            codex_home
            / "plugins"
            / "cache"
            / "openai-curated"
            / "superpowers"
            / "000-old"
            / "skills"
            / "brainstorming"
        )
        old_source.mkdir(parents=True)
        (old_source / "SKILL.md").write_text("---\nname: brainstorming\ndescription: old\n---\n")
        target = repo / ".codex" / "skills" / "brainstorming"
        target.parent.mkdir(parents=True)
        target.symlink_to(old_source, target_is_directory=True)

        report = ensure_project_local_skills(repo, plugin_root, codex_home, dry_run=False, refresh_existing=True)
        brainstorming = next(item for item in report["items"] if item["skill"] == "brainstorming")

        self.assertEqual(brainstorming["status"], "refreshed-link")
        self.assertEqual(target.resolve(), Path(brainstorming["source"]).resolve())

    def test_update_dry_run_reports_external_versions_without_mutating_updates(self):
        codex_home = self.make_codex_home()
        (codex_home / "get-shit-done").mkdir()
        (codex_home / "get-shit-done" / "VERSION").write_text("1.42.3")
        openspec_skill = codex_home / "skills" / "openspec-propose" / "SKILL.md"
        openspec_skill.parent.mkdir(parents=True)
        openspec_skill.write_text('---\nname: openspec-propose\nmetadata:\n  generatedBy: "1.3.1"\n---\n')

        def fake_run(command, cwd=None, timeout=300):
            if command[:3] == ["npm", "view", "get-shit-done-cc"]:
                return {"ok": True, "returncode": 0, "stdout": json.dumps({"version": "1.42.4"}), "stderr": ""}
            if command[:3] == ["npm", "view", "@fission-ai/openspec"]:
                return {"ok": True, "returncode": 0, "stdout": json.dumps({"version": "1.3.2"}), "stderr": ""}
            raise AssertionError(f"unexpected command: {command}")

        with mock.patch.object(auto_update, "executable_exists", return_value=True), mock.patch.object(
            auto_update, "run_command", side_effect=fake_run
        ):
            results = auto_update.run_external_updaters(codex_home, apply=False)

        by_name = {item["name"]: item for item in results}
        self.assertEqual(by_name["gsd-codex"]["status"], "update-available")
        self.assertEqual(by_name["gsd-codex"]["current"], "1.42.3")
        self.assertEqual(by_name["gsd-codex"]["latest"], "1.42.4")
        self.assertEqual(by_name["openspec-cli"]["status"], "update-available")
        self.assertEqual(by_name["openspec-cli"]["latest"], "1.3.2")

    def test_plugin_preflight_passes(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo()
        release_report = run_json(
            "codex_plugin_preflight.py",
            "--plugin-root",
            str(RELEASE_PLUGIN_ROOT),
            "--marketplace",
            str(MARKETPLACE),
            "--repo",
            str(repo),
            "--codex-home",
            str(codex_home),
            "--config",
            str(codex_home / "config.toml"),
            "--json",
        )
        self.assertTrue(release_report["ok"], release_report)
        self.assertIn("dependencies", release_report)
        self.assertTrue(release_report["dependencies"]["ok"], release_report["dependencies"])
        self.assertTrue(any(item["name"] == "dependencies ready" for item in release_report["checks"]))

        dev_report = run_json(
            "codex_plugin_preflight.py",
            "--plugin-root",
            str(PLUGIN_ROOT),
            "--marketplace",
            str(DEV_MARKETPLACE),
            "--repo",
            str(repo),
            "--codex-home",
            str(codex_home),
            "--config",
            str(codex_home / "config.toml"),
            "--json",
        )
        self.assertTrue(dev_report["ok"], dev_report)


if __name__ == "__main__":
    unittest.main()
