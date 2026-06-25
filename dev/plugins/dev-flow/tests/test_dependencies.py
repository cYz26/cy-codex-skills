import json
import os
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
from workflow_dependencies import dependency_report
from workflow_project_activation import activate_project_dependencies
from workflow_project_skill_install import ensure_project_local_skills


class DependencyTests(DependencyFixtureMixin, unittest.TestCase):
    def write_executable(self, directory, name, text):
        path = directory / name
        path.write_text(text)
        path.chmod(0o755)
        return path

    def dependency_report_with_fake_path(self, codex_home, repo, openspec_version="1.4.1"):
        bin_dir = Path(tempfile.mkdtemp(prefix="cpo-dependency-bin-"))
        self.write_executable(bin_dir, "codex", "#!/bin/sh\nprintf 'codex fixture\\n'\n")
        self.write_executable(bin_dir, "openspec", f"#!/bin/sh\nprintf '{openspec_version}\\n'\n")
        with mock.patch.dict(os.environ, {"PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"}):
            return dependency_report(PLUGIN_ROOT, codex_home, codex_home / "config.toml", False, repo)

    def make_dependency_ready_project_repo(self, **kwargs):
        return self.make_project_repo(skill_layout="official", **kwargs)

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
        self.assertEqual(report["status"], "ready_with_recommendations")
        checks = {item["name"]: item for item in report["checks"]}
        self.assertTrue(checks["global plugin inactive: superpowers"]["ok"])
        self.assertTrue(checks["global skill inactive: brainstorming"]["ok"])
        self.assertTrue(checks["global skill inactive: test-driven-development"]["ok"])
        self.assertTrue(checks["project skill active: ai-native-tech-plan"]["ok"])
        self.assertEqual(checks["project skill active: ai-native-tech-plan"]["path_kind"], "official_repo_skill_path")
        self.assertIn(
            "/.agents/skills/ai-native-tech-plan/SKILL.md",
            checks["project skill active: ai-native-tech-plan"]["detail"],
        )
        self.assertTrue(checks["project skill active: capability-research"]["ok"])
        self.assertTrue(checks["project skill active: claude-code-delegate"]["ok"])
        self.assertTrue(checks["project skill active: project-orchestrator"]["ok"])
        self.assertTrue(checks["project skill active: checkpoint-compact"]["ok"])
        self.assertTrue(checks["project skill active: context-health-check"]["ok"])
        self.assertTrue(checks["project skill active: context-tool-audit"]["ok"])
        self.assertTrue(checks["project skill active: codex-updater"]["ok"])
        self.assertTrue(checks["project skill active: plugin-project-migration"]["ok"])
        self.assertTrue(checks["project skill active: brainstorming"]["ok"])
        self.assertTrue(checks["project skill active: writing-plans"]["ok"])
        self.assertTrue(checks["project skill active: test-driven-development"]["ok"])
        self.assertTrue(checks["external plugin installed: superpowers"]["ok"])
        self.assertTrue(checks["external skill available: superpowers:brainstorming"]["ok"])
        self.assertTrue(checks["external skill available: superpowers:writing-plans"]["ok"])
        self.assertTrue(checks["external skill available: superpowers:test-driven-development"]["ok"])
        self.assertNotIn("external cli available: gsd-sdk", checks)
        self.assertTrue(checks["project gsd core runtime active"]["ok"])
        self.assertTrue(checks["project skill active: gsd-new-project"]["ok"])
        self.assertTrue(checks["project skill active: gsd-progress"]["ok"])
        self.assertTrue(checks["project gsd agent active: gsd-planner.toml"]["ok"])
        self.assertTrue(checks["project openspec setup active"]["ok"])
        self.assertTrue(checks["developer plugin enabled: plugin-eval"]["ok"])

    def test_dependency_report_includes_provenance_and_verified_smoke_results(self):
        codex_home = self.make_codex_home()
        repo = self.make_dependency_ready_project_repo()

        report = self.dependency_report_with_fake_path(codex_home, repo)

        self.assertTrue(report["ok"], report)
        self.assertIn("provenance", report)
        self.assertIn("dependencies", report)
        self.assertIn("dependency-provenance.json", report["provenance"]["sourcePath"])
        dependencies = {item["name"]: item for item in report["dependencies"]}
        openspec = dependencies["openspec-cli"]
        self.assertEqual(openspec["status"], "verified")
        self.assertEqual(openspec["expectedVersion"], "1.4.1")
        self.assertEqual(openspec["installedVersion"], "1.4.1")
        self.assertTrue(openspec["binaryPath"].endswith("/openspec"))
        self.assertEqual(openspec["installCommand"], ["npm", "install", "-g", "@fission-ai/openspec@1.4.1"])
        self.assertEqual(openspec["smokeCommand"], ["openspec", "--version"])
        self.assertTrue(openspec["smokeResult"]["ok"], openspec)
        self.assertEqual(openspec["smokeResult"]["summary"], "1.4.1")
        self.assertIn("@fission-ai/openspec", openspec["source"])
        self.assertEqual(report["provenance"]["schemaVersion"], 2)
        self.assertEqual(openspec["lastVerified"], "2026-06-25")

        gsd = dependencies["gsd-core"]
        self.assertEqual(gsd["status"], "verified")
        self.assertEqual(gsd["expectedVersion"], "1.6.0")
        self.assertEqual(gsd["installedVersion"], "1.6.0")
        self.assertTrue(gsd["binaryPath"].endswith("/.codex/gsd-core/bin/gsd-tools.cjs"))
        self.assertEqual(
            gsd["installCommand"],
            ["npx", "-y", "@opengsd/gsd-core@1.6.0", "--codex", "--local", "--profile=standard"],
        )
        self.assertEqual(gsd["smokeCommand"][-1], "current-timestamp")
        self.assertTrue(gsd["smokeResult"]["ok"], gsd)
        self.assertEqual(gsd["lastVerified"], "2026-06-25")

        superpowers = dependencies["superpowers"]
        self.assertEqual(superpowers["status"], "policy_recorded")
        self.assertEqual(superpowers["minimumCompatibleVersion"], "5.1.3")
        self.assertEqual(superpowers["recommendedVersion"], "6.0.3")
        self.assertEqual(superpowers["strictProfileRequires"], "6.0.3")
        self.assertIn("using-superpowers", superpowers["requiredSkills"])

    def test_dependency_check_reports_superpowers_fallback_and_upgrade_recommendation(self):
        codex_home = self.make_codex_home(superpowers_version="5.1.3", superpowers_channel="openai-curated")
        repo = self.make_dependency_ready_project_repo()

        report = self.dependency_report_with_fake_path(codex_home, repo)

        self.assertTrue(report["ok"], report)
        superpowers = report["superpowers"]
        self.assertEqual(superpowers["status"], "superpowers_upgrade_recommended")
        self.assertEqual(superpowers["version"], "5.1.3")
        self.assertEqual(superpowers["sourceChannel"], "openai-curated")
        self.assertEqual(superpowers["compatibility"], "fallback")
        self.assertIn("6.0.3", superpowers["nextAction"])
        checks = {item["name"]: item for item in report["checks"]}
        self.assertFalse(checks["superpowers dependency status"]["ok"])
        self.assertFalse(checks["superpowers dependency status"]["required"])
        self.assertEqual(checks["superpowers dependency status"]["status"], "superpowers_upgrade_recommended")

    def test_dependency_check_blocks_strict_when_superpowers_v6_hook_is_untrusted(self):
        codex_home = self.make_codex_home(
            superpowers_version="6.0.3",
            superpowers_channel="upstream-official",
            superpowers_hooks="hooks/hooks-codex.json",
        )
        repo = self.make_dependency_ready_project_repo()

        report = dependency_report(PLUGIN_ROOT, codex_home, codex_home / "config.toml", True, repo)

        self.assertFalse(report["ok"], report)
        superpowers = report["superpowers"]
        self.assertEqual(superpowers["status"], "superpowers_hook_untrusted")
        self.assertEqual(superpowers["version"], "6.0.3")
        self.assertEqual(superpowers["compatibility"], "recommended")
        checks = {item["name"]: item for item in report["checks"]}
        self.assertTrue(checks["superpowers latest ready"]["ok"])
        self.assertFalse(checks["superpowers session-start hook trusted"]["ok"])
        self.assertTrue(checks["superpowers session-start hook trusted"]["required"])

    def test_dependency_check_accepts_superpowers_v6_hook_trust_from_codex_config(self):
        codex_home = self.make_codex_home(
            superpowers_version="6.0.3",
            superpowers_channel="superpowers-upstream-v6-0-3",
            superpowers_hooks="hooks/hooks-codex.json",
        )
        config = codex_home / "config.toml"
        config.write_text(
            config.read_text()
            + '\n[hooks.state."superpowers@superpowers-upstream-v6-0-3:hooks/hooks-codex.json:session_start:0:0"]\n'
            + 'trusted_hash = "sha256:fixture"\n'
        )
        repo = self.make_dependency_ready_project_repo()

        report = dependency_report(PLUGIN_ROOT, codex_home, config, True, repo)

        self.assertTrue(report["ok"], report)
        superpowers = report["superpowers"]
        self.assertEqual(superpowers["status"], "superpowers_ok")
        self.assertTrue(superpowers["sessionStartHookTrusted"])
        checks = {item["name"]: item for item in report["checks"]}
        self.assertTrue(checks["superpowers session-start hook trusted"]["ok"])
        self.assertTrue(checks["superpowers session-start hook trusted"]["required"])

    def test_dependency_report_marks_drift_missing_and_smoke_failed(self):
        codex_home = self.make_codex_home()

        drift_repo = self.make_dependency_ready_project_repo()
        self.write_gsd_core_runtime(drift_repo, version="1.4.4")
        drift_report = self.dependency_report_with_fake_path(codex_home, drift_repo)
        self.assertIn("dependencies", drift_report)
        drift_gsd = next(item for item in drift_report["dependencies"] if item["name"] == "gsd-core")
        self.assertFalse(drift_report["ok"], drift_report)
        self.assertEqual(drift_gsd["status"], "dependency_drift")
        self.assertEqual(drift_gsd["expectedVersion"], "1.6.0")
        self.assertEqual(drift_gsd["installedVersion"], "1.4.4")
        self.assertEqual(
            drift_gsd["recommendedCommand"],
            ["npx", "-y", "@opengsd/gsd-core@1.6.0", "--codex", "--local", "--profile=standard"],
        )

        missing_repo = self.make_dependency_ready_project_repo()
        (missing_repo / ".codex" / "gsd-core" / "bin" / "gsd-tools.cjs").unlink()
        missing_report = self.dependency_report_with_fake_path(codex_home, missing_repo)
        self.assertIn("dependencies", missing_report)
        missing_gsd = next(item for item in missing_report["dependencies"] if item["name"] == "gsd-core")
        self.assertFalse(missing_report["ok"], missing_report)
        self.assertEqual(missing_gsd["status"], "missing")
        self.assertEqual(missing_gsd["installedVersion"], "1.6.0")

        smoke_repo = self.make_dependency_ready_project_repo()
        smoke_tool = smoke_repo / ".codex" / "gsd-core" / "bin" / "gsd-tools.cjs"
        smoke_tool.write_text("#!/bin/sh\nprintf 'boom\\n' >&2\nexit 7\n")
        smoke_tool.chmod(0o755)
        smoke_report = self.dependency_report_with_fake_path(codex_home, smoke_repo)
        self.assertIn("dependencies", smoke_report)
        smoke_gsd = next(item for item in smoke_report["dependencies"] if item["name"] == "gsd-core")
        self.assertFalse(smoke_report["ok"], smoke_report)
        self.assertEqual(smoke_gsd["status"], "smoke_failed")
        self.assertEqual(smoke_gsd["smokeResult"]["returncode"], 7)

    def test_activation_install_commands_are_sourced_from_dependency_provenance(self):
        repo = Path(tempfile.mkdtemp(prefix="cpo-provenance-activation-"))
        codex_home = self.make_codex_home()

        report = activate_project_dependencies(
            repo,
            dry_run=True,
            skip_official_installs=False,
            plugin_root=PLUGIN_ROOT,
            codex_home=codex_home,
        )

        gsd_install = next(item for item in report["commands"] if item["command"][0:2] == ["npx", "-y"])
        self.assertIn(
            ["npx", "-y", "@opengsd/gsd-core@1.6.0", "--codex", "--local", "--profile=standard"],
            [item["command"] for item in report["commands"]],
        )
        self.assertIn("provenanceSource", gsd_install)
        self.assertTrue(
            gsd_install["provenanceSource"].endswith("dev/plugins/dev-flow/docs/dependency-provenance.json")
        )

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
        for directory in [repo / ".agents" / "skills" / "gsd-new-project"]:
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
        directory = repo / ".agents" / "skills" / "gsd-progress"
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

    def test_dependency_check_fails_when_project_gsd_core_runtime_is_missing(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo()
        runtime = repo / ".codex" / "gsd-core"
        for path in sorted(runtime.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        runtime.rmdir()

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
        self.assertIn("project gsd core runtime active", required_failures)

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
        self.assertEqual(report["local_skills"]["strategy"], "project-local .agents/skills")
        for item in report["local_skills"]["items"]:
            self.assertEqual(item["path_kind"], "official_repo_skill_path")
        self.assertTrue((repo / ".agents" / "skills" / "project-orchestrator" / "SKILL.md").exists())
        self.assertTrue((repo / ".agents" / "skills" / "claude-code-delegate" / "SKILL.md").exists())
        self.assertTrue((repo / ".agents" / "skills" / "checkpoint-compact" / "SKILL.md").exists())
        self.assertTrue((repo / ".agents" / "skills" / "context-health-check" / "SKILL.md").exists())
        self.assertTrue((repo / ".agents" / "skills" / "context-tool-audit" / "SKILL.md").exists())
        self.assertTrue((repo / ".agents" / "skills" / "codex-updater" / "SKILL.md").exists())
        self.assertTrue((repo / ".agents" / "skills" / "plugin-project-migration" / "SKILL.md").exists())
        self.assertTrue((repo / ".agents" / "skills" / "brainstorming" / "SKILL.md").exists())
        self.assertTrue((repo / ".agents" / "skills" / "writing-plans" / "SKILL.md").exists())
        self.assertTrue((repo / ".agents" / "skills" / "test-driven-development" / "SKILL.md").exists())
        self.assertFalse((repo / ".codex" / "skills" / "project-orchestrator").exists())
        self.assertFalse((repo / ".codex" / "config.toml").exists())

    def test_dependency_check_reports_legacy_skill_layout_without_treating_it_as_active(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo(skill_layout="legacy")

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
        checks = {item["name"]: item for item in report["checks"]}
        active = checks["project skill active: project-orchestrator"]
        layout = checks["project skill layout: project-orchestrator"]
        self.assertFalse(active["ok"])
        self.assertEqual(active["path_kind"], "official_repo_skill_path")
        self.assertIn("/.agents/skills/project-orchestrator/SKILL.md", active["detail"])
        self.assertEqual(layout["status"], "legacy_detected")
        self.assertFalse(layout["ok"])
        self.assertFalse(layout["required"])
        self.assertIn("--migrate-official-skill-layout", " ".join(layout["migration_command"]))
        self.assertIn("--dry-run", layout["migration_command"])

    def test_dependency_check_allows_matching_legacy_duplicate_with_cleanup_recommendation(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo()
        legacy = self.project_skill_path(repo, "project-orchestrator", layout="legacy")
        legacy.parent.mkdir(parents=True)
        legacy.write_text(self.project_skill_path(repo, "project-orchestrator").read_text())

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
        layout = checks["project skill layout: project-orchestrator"]
        self.assertTrue(report["ok"], report)
        self.assertEqual(layout["status"], "legacy_duplicate")
        self.assertFalse(layout["required"])
        self.assertIn("cleanup", layout["next_action"])

    def test_dependency_check_fails_on_conflicting_legacy_duplicate(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo()
        legacy = self.project_skill_path(repo, "project-orchestrator", layout="legacy")
        legacy.parent.mkdir(parents=True)
        legacy.write_text("---\nname: project-orchestrator\ndescription: conflicting legacy\n---\n")

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
        checks = {item["name"]: item for item in report["checks"]}
        layout = checks["project skill layout: project-orchestrator"]
        self.assertEqual(layout["status"], "skill_layout_conflict")
        self.assertTrue(layout["required"])
        self.assertFalse(layout["ok"])
        self.assertIn("manual selection", layout["next_action"])

    def test_activation_migration_dry_run_reports_legacy_moves_without_mutating(self):
        repo = Path(tempfile.mkdtemp(prefix="cpo-layout-migration-"))
        codex_home = self.make_codex_home()
        legacy = repo / ".codex" / "skills" / "project-orchestrator" / "SKILL.md"
        legacy.parent.mkdir(parents=True)
        legacy.write_text("---\nname: project-orchestrator\ndescription: legacy\n---\n")

        report = run_json(
            "activate_project_dependencies.py",
            "--repo",
            str(repo),
            "--plugin-root",
            str(PLUGIN_ROOT),
            "--codex-home",
            str(codex_home),
            "--skip-official-installs",
            "--migrate-official-skill-layout",
            "--dry-run",
            "--json",
        )

        migration = report["skill_layout_migration"]
        project_orchestrator = next(item for item in migration["items"] if item["skill"] == "project-orchestrator")
        self.assertTrue(report["ok"], report)
        self.assertEqual(migration["mode"], "dry-run")
        self.assertEqual(project_orchestrator["status"], "would_migrate")
        self.assertEqual(Path(project_orchestrator["legacy_path"]).resolve(), legacy.parent.resolve())
        self.assertEqual(
            Path(project_orchestrator["official_path"]).resolve(),
            (repo / ".agents" / "skills" / "project-orchestrator").resolve(),
        )
        self.assertFalse((repo / ".agents" / "skills" / "project-orchestrator").exists())

    def test_activation_migration_apply_creates_official_copy_and_keeps_legacy_entry(self):
        repo = Path(tempfile.mkdtemp(prefix="cpo-layout-migration-"))
        codex_home = self.make_codex_home()
        legacy = repo / ".codex" / "skills" / "project-orchestrator" / "SKILL.md"
        legacy.parent.mkdir(parents=True)
        legacy.write_text("---\nname: project-orchestrator\ndescription: legacy\n---\n")

        report = run_json(
            "activate_project_dependencies.py",
            "--repo",
            str(repo),
            "--plugin-root",
            str(PLUGIN_ROOT),
            "--codex-home",
            str(codex_home),
            "--skip-official-installs",
            "--migrate-official-skill-layout",
            "--apply",
            "--json",
        )

        migration = report["skill_layout_migration"]
        project_orchestrator = next(item for item in migration["items"] if item["skill"] == "project-orchestrator")
        self.assertTrue(report["ok"], report)
        self.assertEqual(migration["mode"], "apply")
        self.assertEqual(project_orchestrator["status"], "migrated")
        self.assertTrue((repo / ".agents" / "skills" / "project-orchestrator" / "SKILL.md").exists())
        self.assertTrue(legacy.exists())
        self.assertEqual(
            Path(project_orchestrator["rollback"]["remove_created_path"]).resolve(),
            (repo / ".agents" / "skills" / "project-orchestrator").resolve(),
        )

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
        target = repo / ".agents" / "skills" / "brainstorming"
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
        target = repo / ".agents" / "skills" / "brainstorming"
        target.parent.mkdir(parents=True)
        target.symlink_to(old_source, target_is_directory=True)

        report = ensure_project_local_skills(repo, plugin_root, codex_home, dry_run=False, refresh_existing=True)
        brainstorming = next(item for item in report["items"] if item["skill"] == "brainstorming")

        self.assertEqual(brainstorming["status"], "refreshed-link")
        self.assertEqual(target.resolve(), Path(brainstorming["source"]).resolve())

    def test_update_dry_run_reports_external_versions_without_mutating_updates(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo()
        openspec_skill = codex_home / "skills" / "openspec-propose" / "SKILL.md"
        openspec_skill.parent.mkdir(parents=True)
        openspec_skill.write_text('---\nname: openspec-propose\nmetadata:\n  generatedBy: "1.3.1"\n---\n')

        def fake_run(command, cwd=None, timeout=300):
            if command[:3] == ["npm", "view", "@opengsd/gsd-core"]:
                return {"ok": True, "returncode": 0, "stdout": json.dumps({"version": "1.6.1"}), "stderr": ""}
            if command[:3] == ["npm", "view", "@fission-ai/openspec"]:
                return {"ok": True, "returncode": 0, "stdout": json.dumps({"version": "1.3.2"}), "stderr": ""}
            raise AssertionError(f"unexpected command: {command}")

        with mock.patch.object(auto_update, "executable_exists", return_value=True), mock.patch.object(
            auto_update, "run_command", side_effect=fake_run
        ):
            results = auto_update.run_external_updaters(codex_home, apply=False, repo=repo)

        by_name = {item["name"]: item for item in results}
        self.assertEqual(by_name["gsd-core"]["status"], "update-available")
        self.assertEqual(by_name["gsd-core"]["current"], "1.6.0")
        self.assertEqual(by_name["gsd-core"]["latest"], "1.6.1")
        self.assertIn("expectedVersion", by_name["gsd-core"])
        self.assertEqual(by_name["gsd-core"]["expectedVersion"], "1.6.0")
        self.assertIn("provenanceSource", by_name["gsd-core"])
        self.assertTrue(by_name["gsd-core"]["provenanceSource"].endswith("dependency-provenance.json"))
        self.assertIn("installCommand", by_name["gsd-core"])
        self.assertEqual(
            by_name["gsd-core"]["installCommand"],
            ["npx", "-y", "@opengsd/gsd-core@1.6.0", "--codex", "--local", "--profile=standard"],
        )
        self.assertIn("@opengsd/gsd-core", by_name["gsd-core"]["detail"])
        self.assertNotIn("get-shit-done-cc", by_name["gsd-core"]["detail"])
        self.assertEqual(by_name["openspec-cli"]["status"], "update-available")
        self.assertIn("expectedVersion", by_name["openspec-cli"])
        self.assertEqual(by_name["openspec-cli"]["expectedVersion"], "1.4.1")
        self.assertIn("installCommand", by_name["openspec-cli"])
        self.assertEqual(
            by_name["openspec-cli"]["installCommand"],
            ["npm", "install", "-g", "@fission-ai/openspec@1.4.1"],
        )
        self.assertEqual(by_name["openspec-cli"]["latest"], "1.3.2")

    def test_gsd_apply_uses_opengsd_core_local_installer(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo()
        commands = []

        def fake_run(command, cwd=None, timeout=300):
            commands.append((command, cwd))
            return {"ok": True, "returncode": 0, "stdout": "", "stderr": ""}

        with mock.patch.object(auto_update, "executable_exists", return_value=True), mock.patch.object(
            auto_update, "run_command", side_effect=fake_run
        ):
            results = auto_update.run_external_updaters(codex_home, apply=True, repo=repo)

        by_name = {item["name"]: item for item in results}
        self.assertEqual(by_name["gsd-core"]["status"], "updated-or-unchanged")
        self.assertIn(
            (["npx", "-y", "@opengsd/gsd-core@latest", "--codex", "--local", "--profile=standard"], repo),
            commands,
        )
        self.assertFalse(any("get-shit-done-cc" in part for command, _ in commands for part in command))

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
