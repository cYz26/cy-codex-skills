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
    REPO_ROOT,
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
        self.assertTrue(checks["project skill active: capability-research"]["ok"])
        self.assertTrue(checks["project skill active: claude-code-delegate"]["ok"])
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
        self.assertTrue((repo / ".codex" / "skills" / "claude-code-delegate" / "SKILL.md").exists())
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

    def test_git_dry_run_reports_unchanged_when_upstream_matches(self):
        repo = Path(tempfile.mkdtemp(prefix="cpo-git-current-"))

        def fake_run(command, cwd=None, timeout=300):
            if command[3:] == ["status", "--porcelain"]:
                return {"ok": True, "returncode": 0, "stdout": "", "stderr": ""}
            if command[3:] == ["rev-parse", "HEAD"]:
                return {"ok": True, "returncode": 0, "stdout": "aaa111\n", "stderr": ""}
            if command[3:] == ["fetch", "--quiet"]:
                return {"ok": True, "returncode": 0, "stdout": "", "stderr": ""}
            if command[3:] == ["rev-parse", "@{upstream}"]:
                return {"ok": True, "returncode": 0, "stdout": "aaa111\n", "stderr": ""}
            raise AssertionError(f"unexpected command: {command}")

        with mock.patch.object(auto_update, "is_git_repo", return_value=True), mock.patch.object(
            auto_update, "run_command", side_effect=fake_run
        ):
            result = auto_update.update_git_repo(repo, "mirror", apply=False)

        self.assertEqual(result["status"], "unchanged")
        self.assertEqual(result["before"], "aaa111")
        self.assertEqual(result["after"], "aaa111")

    def test_git_dry_run_reports_update_available_when_upstream_differs(self):
        repo = Path(tempfile.mkdtemp(prefix="cpo-git-update-"))

        def fake_run(command, cwd=None, timeout=300):
            if command[3:] == ["status", "--porcelain"]:
                return {"ok": True, "returncode": 0, "stdout": "", "stderr": ""}
            if command[3:] == ["rev-parse", "HEAD"]:
                return {"ok": True, "returncode": 0, "stdout": "aaa111\n", "stderr": ""}
            if command[3:] == ["fetch", "--quiet"]:
                return {"ok": True, "returncode": 0, "stdout": "", "stderr": ""}
            if command[3:] == ["rev-parse", "@{upstream}"]:
                return {"ok": True, "returncode": 0, "stdout": "bbb222\n", "stderr": ""}
            raise AssertionError(f"unexpected command: {command}")

        with mock.patch.object(auto_update, "is_git_repo", return_value=True), mock.patch.object(
            auto_update, "run_command", side_effect=fake_run
        ):
            result = auto_update.update_git_repo(repo, "mirror", apply=False)

        self.assertEqual(result["status"], "would-update")
        self.assertEqual(result["before"], "aaa111")
        self.assertEqual(result["after"], "bbb222")

    def test_installed_plugin_refresh_is_planned_and_applied(self):
        marketplace_root = Path(tempfile.mkdtemp(prefix="cpo-plugin-install-"))
        source = marketplace_root / "plugins" / "dev-flow"
        source.mkdir(parents=True)
        (source / ".codex-plugin").mkdir()
        (source / ".codex-plugin" / "plugin.json").write_text('{"name":"dev-flow"}\n')
        catalog = marketplace_root / ".agents" / "plugins"
        catalog.mkdir(parents=True)
        (catalog / "marketplace.json").write_text(
            json.dumps({"plugins": [{"name": "dev-flow", "source": {"path": "./plugins/dev-flow"}}]})
        )
        config = {
            "marketplaces": {"local": {"source": str(marketplace_root)}},
            "plugins": {
                "dev-flow@local": {"enabled": True},
                "disabled@local": {"enabled": False},
                "other@missing": {"enabled": True},
            },
        }

        dry_run = auto_update.plugin_install_results(config, apply=False)
        self.assertEqual([item["name"] for item in dry_run], ["dev-flow@local"])
        self.assertEqual(dry_run[0]["status"], "would-refresh")

        with mock.patch.object(auto_update, "run_command") as run_command:
            run_command.return_value = {"ok": True, "returncode": 0, "stdout": "installed\n", "stderr": ""}
            applied = auto_update.plugin_install_results(config, apply=True)

        self.assertEqual(applied[0]["status"], "updated-or-unchanged")
        run_command.assert_called_once_with(["codex", "plugin", "add", "dev-flow@local"], timeout=600)

    def test_plugin_cache_verification_compares_source_and_installed_cache(self):
        codex_home = self.make_codex_home()
        marketplace_root = Path(tempfile.mkdtemp(prefix="cpo-marketplace-"))
        source = marketplace_root / "plugins" / "sample"
        cache = codex_home / "plugins" / "cache" / "local" / "sample" / "1.0.0"
        source.mkdir(parents=True)
        cache.mkdir(parents=True)
        (source / ".codex-plugin").mkdir()
        (cache / ".codex-plugin").mkdir()
        (source / ".codex-plugin" / "plugin.json").write_text('{"name":"sample","version":"1.0.0"}\n')
        (cache / ".codex-plugin" / "plugin.json").write_text('{"name":"sample","version":"1.0.0"}\n')
        (source / "payload.txt").write_text("same\n")
        (cache / "payload.txt").write_text("same\n")
        config = {
            "marketplaces": {"local": {"source": str(marketplace_root)}},
            "plugins": {"sample@local": {"enabled": True}},
        }

        results = auto_update.plugin_cache_verification_results(codex_home, config)

        self.assertEqual(results[0]["kind"], "plugin-cache-verify")
        self.assertEqual(results[0]["name"], "sample@local")
        self.assertEqual(results[0]["status"], "matches-source")

        (cache / "payload.txt").write_text("different\n")
        results = auto_update.plugin_cache_verification_results(codex_home, config)

        self.assertEqual(results[0]["status"], "differs-from-source")

    def test_root_updater_delegates_to_devflow_implementation(self):
        root_script = REPO_ROOT / "dev" / "scripts" / "codex_auto_update_plugins_skills.py"
        text = root_script.read_text()

        self.assertIn("CANONICAL_UPDATER", text)
        self.assertIn("dev/plugins/dev-flow/scripts/codex_auto_update_plugins_skills.py", text)
        self.assertNotIn("def run_external_updaters", text)

    def test_codex_updater_skill_is_packaged_with_trigger_language(self):
        skill_path = PLUGIN_ROOT / "skills" / "codex-updater" / "SKILL.md"
        text = skill_path.read_text()
        lowered = text.lower()

        self.assertIn("name: codex-updater", text)
        self.assertIn("Use when", text)
        for phrase in [
            "codex plugins",
            "codex skills",
            "marketplace",
            "plugin cache",
            "external updater",
        ]:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, lowered)

    def test_codex_updater_skill_requires_dry_run_before_apply_and_excludes_agent_reach(self):
        text = (PLUGIN_ROOT / "skills" / "codex-updater" / "SKILL.md").read_text()
        lowered = text.lower()

        self.assertIn("codex_auto_update_plugins_skills.py --json", text)
        self.assertIn("--apply --json", text)
        self.assertIn("dry-run first", lowered)
        self.assertIn("explicit", lowered)
        self.assertIn("plugin-install", text)
        self.assertIn("plugin-cache-verify", text)
        self.assertIn("Agent Reach", text)
        self.assertIn("do not check, update, or run Agent Reach", text)

    def test_agent_reach_is_excluded_from_external_update_plan(self):
        codex_home = self.make_codex_home()

        def fake_exists(name):
            return name in {"agent-reach", "pipx"}

        with mock.patch.object(auto_update, "executable_exists", side_effect=fake_exists), mock.patch.object(
            auto_update, "run_command"
        ) as run_command:
            dry_run_results = auto_update.run_external_updaters(codex_home, apply=False)
            apply_results = auto_update.run_external_updaters(codex_home, apply=True)

        self.assertNotIn("agent-reach", {item["name"] for item in dry_run_results})
        self.assertNotIn("agent-reach", {item["name"] for item in apply_results})
        run_command.assert_not_called()

    def test_agent_reach_is_documented_as_not_recommended(self):
        repo_root = PLUGIN_ROOT.parents[2]
        docs = {
            "README.md": repo_root / "README.md",
            "archived-skills/agent-reach/SKILL.md": (
                repo_root / "archived-skills" / "agent-reach" / "SKILL.md"
            ),
            "dev/scripts/README.md": repo_root / "dev" / "scripts" / "README.md",
            "dev/plugins/dev-flow/README.md": PLUGIN_ROOT / "README.md",
        }

        for label, path in docs.items():
            text = path.read_text().lower()
            with self.subTest(path=label):
                self.assertIn("agent reach", text)
                self.assertRegex(text, r"deprecated|not recommended")

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
