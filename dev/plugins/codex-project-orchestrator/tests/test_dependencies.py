import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from dependency_support import DependencyFixtureMixin, MARKETPLACE, PLUGIN_ROOT, run_json


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
        self.assertTrue(checks["project skill active: brainstorming"]["ok"])
        self.assertTrue(checks["project skill active: writing-plans"]["ok"])
        self.assertTrue(checks["project skill active: test-driven-development"]["ok"])
        self.assertTrue(checks["external plugin installed: superpowers"]["ok"])
        self.assertTrue(checks["external skill available: superpowers:brainstorming"]["ok"])
        self.assertTrue(checks["external skill available: superpowers:writing-plans"]["ok"])
        self.assertTrue(checks["external skill available: superpowers:test-driven-development"]["ok"])
        self.assertTrue(checks["project skill active: gsd-new-project"]["ok"])
        self.assertTrue(checks["project gsd agent active: gsd-planner.toml"]["ok"])
        self.assertTrue(checks["project skill active: openspec-propose"]["ok"])
        self.assertTrue(checks["developer plugin enabled: plugin-eval"]["ok"])

    def test_dependency_check_fails_when_project_gsd_and_openspec_skills_are_missing(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo()
        for directory in [
            repo / ".codex" / "skills" / "gsd-new-project",
            repo / ".codex" / "skills" / "openspec-propose",
        ]:
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
        self.assertIn("project skill active: gsd-new-project", required_failures)
        self.assertIn("project skill active: openspec-propose", required_failures)

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
        self.assertTrue((repo / ".codex" / "skills" / "brainstorming" / "SKILL.md").exists())
        self.assertTrue((repo / ".codex" / "skills" / "writing-plans" / "SKILL.md").exists())
        self.assertTrue((repo / ".codex" / "skills" / "test-driven-development" / "SKILL.md").exists())
        self.assertFalse((repo / ".codex" / "config.toml").exists())

    def test_plugin_preflight_passes(self):
        report = run_json(
            "codex_plugin_preflight.py",
            "--plugin-root",
            str(PLUGIN_ROOT),
            "--marketplace",
            str(MARKETPLACE),
            "--json",
        )
        self.assertTrue(report["ok"], report)
        self.assertIn("dependencies", report)
        self.assertTrue(report["dependencies"]["ok"], report["dependencies"])
        self.assertTrue(any(item["name"] == "dependencies ready" for item in report["checks"]))


if __name__ == "__main__":
    unittest.main()
