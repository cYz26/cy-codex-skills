import json
import os
import shutil
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
from workflow_dependency_catalog import LEGACY_OPENSPEC_SKILLS, PROJECT_ORCHESTRATOR_SKILLS
from workflow_dependencies import dependency_report
from workflow_validate import missing_agents_guidance
from workflow_project_activation import activate_project_dependencies
from workflow_project_skill_install import ensure_project_local_skills
from workflow_provider_deactivation import deactivate_project_provider_skills
import workflow_provider_deactivation as provider_deactivation_module


class DependencyTests(DependencyFixtureMixin, unittest.TestCase):
    def make_project_repo(self, **kwargs):
        repo = super().make_project_repo(**kwargs)
        if kwargs.get("enable_orchestrator", True) and kwargs.get("skill_layout", "official") == "official":
            for skill in PROJECT_ORCHESTRATOR_SKILLS:
                source = PLUGIN_ROOT / "skills" / skill / "SKILL.md"
                target = repo / ".agents" / "skills" / skill / "SKILL.md"
                target.write_bytes(source.read_bytes())
        return repo

    def write_executable(self, directory, name, text):
        path = directory / name
        path.write_text(text)
        path.chmod(0o755)
        return path

    def dependency_report_with_fake_path(self, codex_home, repo, openspec_version="1.5.0"):
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
        self.assertIn(report["status"], {"ready", "ready_with_recommendations"})
        checks = {item["name"]: item for item in report["checks"]}
        self.assertTrue(checks["global plugin inactive: superpowers"]["ok"])
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
        self.assertNotIn("external cli available: gsd-sdk", checks)
        self.assertNotIn("project gsd core runtime active", checks)
        self.assertEqual(report["selection"]["effectiveMethodologyProfile"], "core")
        self.assertEqual(report["selection"]["effectiveRoadmapProvider"], "none")
        self.assertTrue(checks["project openspec setup active"]["ok"])
        self.assertTrue(checks["project openspec sync workflow available"]["ok"])
        self.assertFalse(checks["project openspec sync workflow available"]["required"])
        self.assertTrue(checks["developer plugin enabled: plugin-eval"]["ok"])

    def test_dependency_json_does_not_embed_runtime_config_or_sensitive_values(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo()
        sensitive_value = "devflow-test-secret-must-not-leak"
        with (codex_home / "config.toml").open("a") as config_file:
            config_file.write(
                "\n[mcp_servers.sensitive-fixture]\n"
                'command = "fixture"\n'
                "[mcp_servers.sensitive-fixture.env]\n"
                f'DEVFLOW_TEST_SECRET = "{sensitive_value}"\n'
            )

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

        self.assertNotIn("runtimeConfig", report["selection"])
        self.assertNotIn(sensitive_value, json.dumps(report, sort_keys=True))

    def test_dependency_cli_capability_flag_blocks_missing_goal_definition(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo()
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
                "--capability",
                "goal-definition",
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report["capabilities"]["goal-definition"]["ready"])
        self.assertIn("goal-definition", report["triggeredCapabilities"])

    def test_activation_cli_capability_flag_plans_strict_conditional_links(self):
        codex_home = self.make_codex_home(
            superpowers_version="6.1.1",
            superpowers_channel="openai-curated-remote",
        )
        repo = self.make_project_repo(
            enable_superpowers=True,
            methodology_profile="strict-superpowers",
            roadmap_provider="none",
            provider_selectors={
                "superpowers": {
                    "source_channel": "openai-curated-remote",
                    "version": "6.1.1",
                }
            },
        )
        result = subprocess.run(
            [
                sys.executable,
                str(PLUGIN_ROOT / "scripts" / "activate_project_dependencies.py"),
                "--repo",
                str(repo),
                "--plugin-root",
                str(PLUGIN_ROOT),
                "--codex-home",
                str(codex_home),
                "--skip-official-installs",
                "--capability",
                "execution-orchestration",
                "--dry-run",
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        report = json.loads(result.stdout)
        conditional = {
            item["skill"]: item
            for item in report["local_skills"]["items"]
            if item["provider"] == "superpowers"
        }
        for skill in (
            "executing-plans",
            "subagent-driven-development",
            "using-git-worktrees",
            "finishing-a-development-branch",
        ):
            self.assertIn(skill, conditional)
            self.assertEqual(conditional[skill]["status"], "would-link")

    def test_dependency_report_includes_provenance_and_verified_smoke_results(self):
        codex_home = self.make_codex_home()
        repo = self.make_dependency_ready_project_repo(
            enable_gsd=True,
            methodology_profile="core",
            roadmap_provider="gsd",
        )

        report = self.dependency_report_with_fake_path(codex_home, repo)

        self.assertTrue(report["ok"], report)
        self.assertIn("provenance", report)
        self.assertIn("dependencies", report)
        self.assertIn("dependency-provenance.json", report["provenance"]["sourcePath"])
        dependencies = {item["name"]: item for item in report["dependencies"]}
        openspec = dependencies["openspec-cli"]
        self.assertEqual(openspec["status"], "verified")
        self.assertEqual(openspec["expectedVersion"], "1.5.0")
        self.assertEqual(openspec["installedVersion"], "1.5.0")
        self.assertTrue(openspec["binaryPath"].endswith("/openspec"))
        self.assertEqual(openspec["installCommand"], ["npm", "install", "-g", "@fission-ai/openspec@1.5.0"])
        self.assertEqual(openspec["smokeCommand"], ["openspec", "--version"])
        self.assertTrue(openspec["smokeResult"]["ok"], openspec)
        self.assertEqual(openspec["smokeResult"]["summary"], "1.5.0")
        self.assertIn("@fission-ai/openspec", openspec["source"])
        self.assertEqual(report["provenance"]["schemaVersion"], 2)
        self.assertEqual(openspec["lastVerified"], "2026-07-13")

        gsd = dependencies["gsd-core"]
        self.assertEqual(gsd["status"], "verified")
        self.assertEqual(gsd["expectedVersion"], "1.6.1")
        self.assertEqual(gsd["installedVersion"], "1.6.1")
        self.assertTrue(gsd["binaryPath"].endswith("/.codex/gsd-core/bin/gsd-tools.cjs"))
        self.assertEqual(
            gsd["installCommand"],
            ["npx", "-y", "@opengsd/gsd-core@1.6.1", "--codex", "--local", "--profile=standard"],
        )
        self.assertEqual(gsd["smokeCommand"][-1], "current-timestamp")
        self.assertTrue(gsd["smokeResult"]["ok"], gsd)
        self.assertEqual(gsd["lastVerified"], "2026-07-13")

        superpowers = dependencies["superpowers"]
        self.assertEqual(superpowers["status"], "not_selected")
        self.assertEqual(superpowers["installCommand"], [])
        self.assertEqual(superpowers["recommendedCommand"], [])
        self.assertEqual(superpowers["fallbackOrBlocker"], "")
        self.assertEqual(superpowers["minimumCompatibleVersion"], "5.1.3")
        self.assertEqual(superpowers["recommendedVersion"], "6.1.1")
        self.assertEqual(superpowers["strictProfileRequires"], "5.1.3")
        self.assertIn("using-superpowers", superpowers["requiredSkills"])

    def test_dependency_report_does_not_probe_unselected_gsd_runtime(self):
        codex_home = self.make_codex_home()
        repo = self.make_dependency_ready_project_repo(
            methodology_profile="core",
            roadmap_provider="none",
        )
        marker = repo / "gsd-smoke-invoked"
        runtime = repo / ".codex" / "gsd-core" / "bin" / "gsd-tools.cjs"
        runtime.parent.mkdir(parents=True, exist_ok=True)
        runtime.write_text(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('invoked')\n"
            "print('{\"timestamp\": \"2026-07-10T00:00:00Z\"}')\n"
        )
        runtime.chmod(0o755)

        report = self.dependency_report_with_fake_path(codex_home, repo)

        self.assertFalse(marker.exists(), report)
        gsd = next(item for item in report["dependencies"] if item["name"] == "gsd-core")
        self.assertEqual(gsd["status"], "not_selected")
        self.assertFalse(gsd["required"])
        self.assertIsNone(gsd["installedVersion"])
        self.assertEqual(gsd["installCommand"], [])
        self.assertEqual(gsd["recommendedCommand"], [])
        self.assertEqual(gsd["fallbackOrBlocker"], "")
        self.assertEqual(gsd["smokeCommand"], [])
        self.assertEqual(gsd["smokeResult"]["summary"], "not selected; runtime was not inspected")
        superpowers = next(
            item for item in report["dependencies"] if item["name"] == "superpowers"
        )
        self.assertEqual(superpowers["status"], "not_selected")
        self.assertEqual(superpowers["installCommand"], [])
        self.assertEqual(superpowers["recommendedCommand"], [])
        self.assertEqual(superpowers["fallbackOrBlocker"], "")

    def test_dependency_check_reports_superpowers_fallback_and_upgrade_recommendation(self):
        codex_home = self.make_codex_home(superpowers_version="5.1.3", superpowers_channel="openai-curated")
        repo = self.make_dependency_ready_project_repo(
            enable_superpowers=True,
            methodology_profile="strict-superpowers",
            roadmap_provider="none",
        )

        report = self.dependency_report_with_fake_path(codex_home, repo)

        self.assertTrue(report["ok"], report)
        superpowers = report["superpowers"]
        self.assertEqual(superpowers["status"], "superpowers_upgrade_recommended")
        self.assertEqual(superpowers["version"], "5.1.3")
        self.assertEqual(superpowers["sourceChannel"], "openai-curated")
        self.assertEqual(superpowers["compatibility"], "fallback")
        self.assertIn("6.1.1", superpowers["nextAction"])
        checks = {item["name"]: item for item in report["checks"]}
        self.assertFalse(checks["superpowers dependency status"]["ok"])
        self.assertFalse(checks["superpowers dependency status"]["required"])
        self.assertEqual(checks["superpowers dependency status"]["status"], "superpowers_upgrade_recommended")

    def test_dependency_check_blocks_hook_injection_into_selected_source(self):
        codex_home = self.make_codex_home(
            superpowers_version="6.1.1",
            superpowers_channel="openai-curated-remote",
            superpowers_hooks="hooks/hooks-codex.json",
        )
        repo = self.make_dependency_ready_project_repo(
            enable_superpowers=True,
            methodology_profile="strict-superpowers",
            roadmap_provider="none",
            provider_selectors={
                "superpowers": {
                    "source_channel": "openai-curated-remote",
                    "version": "6.1.1",
                }
            },
        )

        report = dependency_report(PLUGIN_ROOT, codex_home, codex_home / "config.toml", True, repo)

        self.assertFalse(report["ok"], report)
        self.assertEqual(report["providers"]["superpowers"]["status"], "source_drift")

    def test_dependency_check_accepts_authoritative_hookless_superpowers_source(self):
        codex_home = self.make_codex_home(
            superpowers_version="6.1.1",
            superpowers_channel="openai-curated-remote",
        )
        repo = self.make_dependency_ready_project_repo(
            enable_superpowers=True,
            methodology_profile="strict-superpowers",
            roadmap_provider="none",
            provider_selectors={
                "superpowers": {
                    "source_channel": "openai-curated-remote",
                    "version": "6.1.1",
                }
            },
        )

        report = dependency_report(
            PLUGIN_ROOT,
            codex_home,
            codex_home / "config.toml",
            True,
            repo,
        )

        self.assertTrue(report["ok"], report)
        superpowers = report["superpowers"]
        self.assertEqual(superpowers["status"], "superpowers_ok")
        self.assertFalse(report["providers"]["superpowers"]["hookDeclared"])

    def test_unselected_superpowers_summary_preserves_available_status_without_action(self):
        codex_home = self.make_codex_home()
        repo = self.make_dependency_ready_project_repo(
            methodology_profile="core",
            roadmap_provider="none",
        )

        report = self.dependency_report_with_fake_path(codex_home, repo)

        self.assertEqual(report["providers"]["superpowers"]["status"], "available_unselected")
        self.assertEqual(report["superpowers"]["status"], "available_unselected")
        self.assertEqual(report["superpowers"]["compatibility"], "unselected")
        self.assertEqual(report["superpowers"]["nextAction"], "")

    def test_unselected_superpowers_summary_preserves_absent_status_without_action(self):
        codex_home = self.make_codex_home(install_superpowers=False)
        repo = self.make_dependency_ready_project_repo(
            methodology_profile="core",
            roadmap_provider="none",
        )

        report = self.dependency_report_with_fake_path(codex_home, repo)

        self.assertEqual(report["providers"]["superpowers"]["status"], "absent_unselected")
        self.assertEqual(report["superpowers"]["status"], "absent_unselected")
        self.assertEqual(report["superpowers"]["compatibility"], "unselected")
        self.assertEqual(report["superpowers"]["nextAction"], "")

    def test_no_repo_strict_check_keeps_superpowers_unselected_and_action_free(self):
        codex_home = self.make_codex_home()

        report = dependency_report(
            PLUGIN_ROOT,
            codex_home,
            codex_home / "config.toml",
            True,
            None,
        )

        self.assertEqual(report["superpowers"]["status"], "available_unselected")
        self.assertEqual(report["superpowers"]["compatibility"], "unselected")
        self.assertEqual(report["superpowers"]["nextAction"], "")

    def test_global_matt_control_plane_skill_is_non_blocking_pollution_advisory(self):
        codex_home = self.make_codex_home()
        repo = self.make_dependency_ready_project_repo(
            methodology_profile="core",
            roadmap_provider="none",
        )
        skill = codex_home / "skills" / "ask-matt" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: ask-matt\ndescription: fixture\n---\n")

        report = self.dependency_report_with_fake_path(codex_home, repo)

        self.assertTrue(report["ok"], report)
        check = next(
            item
            for item in report["checks"]
            if item["name"] == "global Matt control-plane skill inactive: ask-matt"
        )
        self.assertFalse(check["ok"])
        self.assertFalse(check["required"])
        self.assertEqual(check["status"], "global_control_plane_pollution")
        self.assertIn(str(skill), check["detail"])

    def test_dependency_check_rejects_ambiguous_superpowers_skill_roots(self):
        codex_home = self.make_codex_home(
            superpowers_version="6.1.1",
            superpowers_channel="openai-curated-remote",
        )
        for skill in [
            "using-superpowers",
            "brainstorming",
            "writing-plans",
            "test-driven-development",
            "systematic-debugging",
            "requesting-code-review",
            "verification-before-completion",
        ]:
            self.write_skill(
                codex_home,
                "superpowers",
                skill,
                channel="superpowers-upstream-v6-0-3",
            )
        self.write_plugin_manifest(
            codex_home,
            "superpowers",
            version="6.0.3",
            channel="superpowers-upstream-v6-0-3",
        )
        repo = self.make_dependency_ready_project_repo(
            enable_superpowers=True,
            methodology_profile="strict-superpowers",
            roadmap_provider="none",
        )

        report = self.dependency_report_with_fake_path(codex_home, repo)

        self.assertFalse(report["ok"], report)
        self.assertEqual(report["providers"]["superpowers"]["status"], "ambiguous_source")
        self.assertEqual(len(report["providers"]["superpowers"]["candidates"]), 2)

    def test_dependency_report_marks_drift_missing_and_smoke_failed(self):
        codex_home = self.make_codex_home()

        drift_repo = self.make_dependency_ready_project_repo(
            enable_gsd=True,
            methodology_profile="core",
            roadmap_provider="gsd",
        )
        self.write_gsd_core_runtime(drift_repo, version="1.4.4")
        drift_report = self.dependency_report_with_fake_path(codex_home, drift_repo)
        self.assertIn("dependencies", drift_report)
        drift_gsd = next(item for item in drift_report["dependencies"] if item["name"] == "gsd-core")
        self.assertFalse(drift_report["ok"], drift_report)
        self.assertEqual(drift_gsd["status"], "dependency_drift")
        self.assertEqual(drift_gsd["expectedVersion"], "1.6.1")
        self.assertEqual(drift_gsd["installedVersion"], "1.4.4")
        self.assertEqual(
            drift_gsd["recommendedCommand"],
            ["npx", "-y", "@opengsd/gsd-core@1.6.1", "--codex", "--local", "--profile=standard"],
        )

        missing_repo = self.make_dependency_ready_project_repo(
            enable_gsd=True,
            methodology_profile="core",
            roadmap_provider="gsd",
        )
        (missing_repo / ".codex" / "gsd-core" / "bin" / "gsd-tools.cjs").unlink()
        missing_report = self.dependency_report_with_fake_path(codex_home, missing_repo)
        self.assertIn("dependencies", missing_report)
        missing_gsd = next(item for item in missing_report["dependencies"] if item["name"] == "gsd-core")
        self.assertFalse(missing_report["ok"], missing_report)
        self.assertEqual(missing_gsd["status"], "missing")
        self.assertEqual(missing_gsd["installedVersion"], "1.6.1")

        smoke_repo = self.make_dependency_ready_project_repo(
            enable_gsd=True,
            methodology_profile="core",
            roadmap_provider="gsd",
        )
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
        self.write_provider_config(repo, methodology_profile="core", roadmap_provider="gsd")

        report = activate_project_dependencies(
            repo,
            dry_run=True,
            skip_official_installs=False,
            plugin_root=PLUGIN_ROOT,
            codex_home=codex_home,
        )

        gsd_install = next(item for item in report["commands"] if item["command"][0:2] == ["npx", "-y"])
        openspec_install = next(item for item in report["commands"] if item["command"][0:2] == ["openspec", "init"])
        self.assertEqual(
            openspec_install["command"],
            ["openspec", "init", "--tools", "codex", "--profile", "core", str(repo.resolve()), "--force"],
        )
        self.assertIn(
            ["npx", "-y", "@opengsd/gsd-core@1.6.1", "--codex", "--local", "--profile=standard"],
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
        self.assertFalse(checks["project openspec sync workflow available"]["required"])
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
        repo = self.make_project_repo(
            enable_legacy_openspec_skills=False,
            enable_gsd=True,
            methodology_profile="core",
            roadmap_provider="gsd",
        )
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
        repo = self.make_project_repo(
            enable_gsd=True,
            methodology_profile="core",
            roadmap_provider="gsd",
        )
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
        repo = self.make_project_repo(
            enable_gsd=True,
            methodology_profile="core",
            roadmap_provider="gsd",
        )
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
        repo = self.make_project_repo(
            enable_superpowers=True,
            methodology_profile="strict-superpowers",
            roadmap_provider="none",
        )
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
        self.write_provider_config(repo, methodology_profile="strict-superpowers", roadmap_provider="none")
        report = run_json(
            "activate_project_dependencies.py",
            "--repo",
            str(repo),
            "--plugin-root",
            str(PLUGIN_ROOT),
            "--codex-home",
            str(codex_home),
            "--skip-official-installs",
            "--apply",
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
        self.assertTrue((repo / ".agents" / "skills" / "dev-flow-refresh" / "SKILL.md").exists())
        self.assertTrue((repo / ".agents" / "skills" / "brainstorming" / "SKILL.md").exists())
        self.assertTrue((repo / ".agents" / "skills" / "writing-plans" / "SKILL.md").exists())
        self.assertTrue((repo / ".agents" / "skills" / "test-driven-development" / "SKILL.md").exists())
        self.assertFalse((repo / ".codex" / "skills" / "project-orchestrator").exists())
        self.assertFalse((repo / ".codex" / "config.toml").exists())

    def test_provider_deactivation_dry_run_has_zero_writes(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo(methodology_profile="core", roadmap_provider="none")
        source = (
            PLUGIN_ROOT
            / "fixtures"
            / "provider-profiles"
            / "strict-superpowers"
            / ".agents"
            / "skills"
            / "brainstorming"
        )
        target = repo / ".agents" / "skills" / "brainstorming"
        target.symlink_to(source, target_is_directory=True)
        before_config = (repo / ".dev-flow.json").read_bytes()
        before_link = os.readlink(target)

        report = run_json(
            "activate_project_dependencies.py",
            "--repo",
            str(repo),
            "--plugin-root",
            str(PLUGIN_ROOT),
            "--codex-home",
            str(codex_home),
            "--skip-official-installs",
            "--deactivate-provider",
            "superpowers",
            "--dry-run",
            "--json",
        )

        cleanup = report["provider_deactivation"]
        item = next(entry for entry in cleanup["items"] if entry["skill"] == "brainstorming")
        self.assertEqual(cleanup["mode"], "dry-run")
        self.assertFalse(cleanup["changed"])
        self.assertEqual(item["status"], "would_remove")
        self.assertEqual(item["verification"], "provenance_hash")
        self.assertEqual(len(cleanup["planDigest"]), 64)
        self.assertEqual(cleanup["plan"]["provider"], "superpowers")
        self.assertEqual(
            set(cleanup["plan"]["items"][0]),
            {"path", "rawTarget", "verification", "skillSha256", "rollback"},
        )
        self.assertTrue(target.is_symlink())
        self.assertEqual(os.readlink(target), before_link)
        self.assertEqual((repo / ".dev-flow.json").read_bytes(), before_config)

        repeated = run_json(
            "activate_project_dependencies.py",
            "--repo",
            str(repo),
            "--plugin-root",
            str(PLUGIN_ROOT),
            "--codex-home",
            str(codex_home),
            "--skip-official-installs",
            "--deactivate-provider",
            "superpowers",
            "--dry-run",
            "--json",
        )["provider_deactivation"]

        self.assertEqual(repeated["planDigest"], cleanup["planDigest"])
        self.assertEqual(repeated["plan"], cleanup["plan"])

    def test_provider_deactivation_apply_requires_matching_named_authorization(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo(methodology_profile="core", roadmap_provider="none")
        source = (
            PLUGIN_ROOT
            / "fixtures"
            / "provider-profiles"
            / "strict-superpowers"
            / ".agents"
            / "skills"
            / "brainstorming"
        )
        target = repo / ".agents" / "skills" / "brainstorming"
        target.symlink_to(source, target_is_directory=True)

        result = subprocess.run(
            [
                sys.executable,
                str(PLUGIN_ROOT / "scripts" / "activate_project_dependencies.py"),
                "--repo",
                str(repo),
                "--plugin-root",
                str(PLUGIN_ROOT),
                "--codex-home",
                str(codex_home),
                "--skip-official-installs",
                "--deactivate-provider",
                "superpowers",
                "--apply",
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1, result.stderr)
        cleanup = json.loads(result.stdout)["provider_deactivation"]
        self.assertEqual(cleanup["status"], "authorization_required")
        self.assertEqual(cleanup["authorization"], "explicit_file_list_and_rollback")
        self.assertFalse(cleanup["changed"])
        self.assertTrue(target.is_symlink())

    def test_provider_deactivation_apply_rejects_wrong_plan_digest(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo(
            enable_orchestrator=False,
            enable_legacy_openspec_skills=False,
            methodology_profile="core",
            roadmap_provider="none",
        )
        source = (
            PLUGIN_ROOT
            / "fixtures"
            / "provider-profiles"
            / "strict-superpowers"
            / ".agents"
            / "skills"
            / "brainstorming"
        )
        target = repo / ".agents" / "skills" / "brainstorming"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source, target_is_directory=True)
        before_paths = sorted(
            str(path.relative_to(repo))
            for path in repo.rglob("*")
        )

        result = subprocess.run(
            [
                sys.executable,
                str(PLUGIN_ROOT / "scripts" / "activate_project_dependencies.py"),
                "--repo",
                str(repo),
                "--plugin-root",
                str(PLUGIN_ROOT),
                "--codex-home",
                str(codex_home),
                "--skip-official-installs",
                "--deactivate-provider",
                "superpowers",
                "--authorize-provider-cleanup",
                "superpowers",
                "--provider-cleanup-plan",
                "0" * 64,
                "--apply",
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1, result.stderr)
        cleanup = json.loads(result.stdout)["provider_deactivation"]
        self.assertEqual(cleanup["status"], "authorization_required")
        self.assertTrue(cleanup["namedAuthorizationMatches"])
        self.assertTrue(cleanup["sideEffect"]["authorized"])
        self.assertFalse(cleanup["planDigestMatches"])
        self.assertFalse(cleanup["changed"])
        self.assertTrue(target.is_symlink())
        self.assertEqual(
            sorted(str(path.relative_to(repo)) for path in repo.rglob("*")),
            before_paths,
        )

    def test_provider_deactivation_apply_has_no_non_cleanup_writes(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo(
            enable_orchestrator=False,
            enable_legacy_openspec_skills=False,
            methodology_profile="core",
            roadmap_provider="none",
        )
        source = (
            PLUGIN_ROOT
            / "fixtures"
            / "provider-profiles"
            / "strict-superpowers"
            / ".agents"
            / "skills"
            / "brainstorming"
        )
        target = repo / ".agents" / "skills" / "brainstorming"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source, target_is_directory=True)
        before_paths = {
            str(path.relative_to(repo))
            for path in repo.rglob("*")
        }
        common = (
            "--repo",
            str(repo),
            "--plugin-root",
            str(PLUGIN_ROOT),
            "--codex-home",
            str(codex_home),
            "--skip-official-installs",
            "--deactivate-provider",
            "superpowers",
        )
        plan = run_json(
            "activate_project_dependencies.py",
            *common,
            "--dry-run",
            "--json",
        )["provider_deactivation"]

        cleanup = run_json(
            "activate_project_dependencies.py",
            *common,
            "--authorize-provider-cleanup",
            "superpowers",
            "--provider-cleanup-plan",
            plan["planDigest"],
            "--apply",
            "--json",
        )["provider_deactivation"]

        after_paths = {
            str(path.relative_to(repo))
            for path in repo.rglob("*")
        }
        self.assertEqual(cleanup["status"], "applied")
        self.assertEqual(after_paths, before_paths - {".agents/skills/brainstorming"})
        self.assertFalse(target.exists() or target.is_symlink())

    def test_provider_deactivation_preserves_external_symlinked_skill_layout(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo(
            enable_orchestrator=False,
            enable_legacy_openspec_skills=False,
            methodology_profile="core",
            roadmap_provider="none",
        )
        source = (
            PLUGIN_ROOT
            / "fixtures"
            / "provider-profiles"
            / "strict-superpowers"
            / ".agents"
            / "skills"
            / "brainstorming"
        )
        external_root = Path(tempfile.mkdtemp(prefix="devflow-external-skill-layout-"))
        external_target = external_root / "skills" / "brainstorming"
        external_target.parent.mkdir(parents=True)
        external_target.symlink_to(source, target_is_directory=True)
        (repo / ".agents").symlink_to(external_root, target_is_directory=True)
        selection = {
            "effectiveMethodologyProfile": "core",
            "selectionSource": "explicit_config",
        }

        plan = deactivate_project_provider_skills(
            repo,
            "superpowers",
            PLUGIN_ROOT,
            codex_home=codex_home,
            selection=selection,
        )
        cleanup = deactivate_project_provider_skills(
            repo,
            "superpowers",
            PLUGIN_ROOT,
            codex_home=codex_home,
            apply=True,
            authorized_provider="superpowers",
            authorized_plan_digest=plan["planDigest"],
            selection=selection,
        )

        self.assertEqual(plan["plan"]["items"], [])
        self.assertTrue(external_target.is_symlink())
        self.assertFalse(cleanup["changed"])
        self.assertEqual(cleanup["status"], "current_with_preserved_paths")
        self.assertTrue(cleanup["planDigestMatches"])
        self.assertTrue(
            any(item["status"] == "preserved_unsafe_layout" for item in cleanup["items"]),
            cleanup,
        )

    def test_provider_deactivation_requires_explicit_persisted_selection(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo(
            enable_orchestrator=False,
            enable_legacy_openspec_skills=False,
            methodology_profile="core",
            roadmap_provider="none",
        )
        (repo / ".dev-flow.json").unlink()
        source = (
            PLUGIN_ROOT
            / "fixtures"
            / "provider-profiles"
            / "strict-superpowers"
            / ".agents"
            / "skills"
            / "brainstorming"
        )
        target = repo / ".agents" / "skills" / "brainstorming"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source, target_is_directory=True)
        dry_run_args = (
            "--repo",
            str(repo),
            "--plugin-root",
            str(PLUGIN_ROOT),
            "--codex-home",
            str(codex_home),
            "--skip-official-installs",
            "--deactivate-provider",
            "superpowers",
            "--dry-run",
            "--json",
        )
        plan = run_json(
            "activate_project_dependencies.py",
            *dry_run_args,
        )["provider_deactivation"]

        result = subprocess.run(
            [
                sys.executable,
                str(PLUGIN_ROOT / "scripts" / "activate_project_dependencies.py"),
                "--repo",
                str(repo),
                "--plugin-root",
                str(PLUGIN_ROOT),
                "--codex-home",
                str(codex_home),
                "--skip-official-installs",
                "--deactivate-provider",
                "superpowers",
                "--authorize-provider-cleanup",
                "superpowers",
                "--provider-cleanup-plan",
                plan["planDigest"],
                "--apply",
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1, result.stderr)
        cleanup = json.loads(result.stdout)["provider_deactivation"]
        self.assertEqual(cleanup["status"], "activation_prerequisite_failed")
        self.assertIn("selection_not_persisted", cleanup["blockingReasons"])
        self.assertTrue(target.is_symlink())

    def test_provider_deactivation_requires_complete_explicit_selection(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo(
            enable_orchestrator=False,
            enable_legacy_openspec_skills=False,
            methodology_profile="core",
            roadmap_provider="none",
        )
        (repo / ".dev-flow.json").write_text(
            json.dumps({"workflow": {"methodology_profile": "core"}}, indent=2) + "\n"
        )
        source = (
            PLUGIN_ROOT
            / "fixtures"
            / "provider-profiles"
            / "strict-superpowers"
            / ".agents"
            / "skills"
            / "brainstorming"
        )
        target = repo / ".agents" / "skills" / "brainstorming"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source, target_is_directory=True)
        common = (
            "--repo",
            str(repo),
            "--plugin-root",
            str(PLUGIN_ROOT),
            "--codex-home",
            str(codex_home),
            "--skip-official-installs",
            "--deactivate-provider",
            "superpowers",
        )
        plan = run_json(
            "activate_project_dependencies.py",
            *common,
            "--dry-run",
            "--json",
        )["provider_deactivation"]

        result = subprocess.run(
            [
                sys.executable,
                str(PLUGIN_ROOT / "scripts" / "activate_project_dependencies.py"),
                *common,
                "--authorize-provider-cleanup",
                "superpowers",
                "--provider-cleanup-plan",
                plan["planDigest"],
                "--apply",
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1, result.stderr)
        cleanup = json.loads(result.stdout)["provider_deactivation"]
        self.assertIn("selection_not_persisted", cleanup["blockingReasons"])
        self.assertTrue(target.is_symlink())

    def test_provider_deactivation_rechecks_parent_layout_before_unlink(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo(
            enable_orchestrator=False,
            enable_legacy_openspec_skills=False,
            methodology_profile="core",
            roadmap_provider="none",
        )
        source = (
            PLUGIN_ROOT
            / "fixtures"
            / "provider-profiles"
            / "strict-superpowers"
            / ".agents"
            / "skills"
            / "brainstorming"
        )
        target = repo / ".agents" / "skills" / "brainstorming"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source, target_is_directory=True)
        selection = {
            "effectiveMethodologyProfile": "core",
            "selectionSource": "explicit_config",
        }
        plan = deactivate_project_provider_skills(
            repo,
            "superpowers",
            PLUGIN_ROOT,
            codex_home=codex_home,
            selection=selection,
        )
        target.unlink()
        target.parent.rmdir()
        external_skills = Path(tempfile.mkdtemp(prefix="devflow-swapped-layout-"))
        external_target = external_skills / "brainstorming"
        external_target.symlink_to(source, target_is_directory=True)
        (repo / ".agents" / "skills").symlink_to(
            external_skills,
            target_is_directory=True,
        )

        cleanup = deactivate_project_provider_skills(
            repo,
            "superpowers",
            PLUGIN_ROOT,
            codex_home=codex_home,
            apply=True,
            authorized_provider="superpowers",
            authorized_plan_digest=plan["planDigest"],
            selection=selection,
        )

        self.assertTrue(external_target.is_symlink())
        self.assertFalse(cleanup["changed"])
        self.assertEqual(cleanup["status"], "authorization_required")
        self.assertFalse(cleanup["planDigestMatches"])
        self.assertTrue(
            any(item["status"] == "preserved_unsafe_layout" for item in cleanup["items"]),
            cleanup,
        )

    def test_provider_deactivation_uses_anchored_parent_when_layout_swaps_after_check(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo(
            enable_orchestrator=False,
            enable_legacy_openspec_skills=False,
            methodology_profile="core",
            roadmap_provider="none",
        )
        source = (
            PLUGIN_ROOT
            / "fixtures"
            / "provider-profiles"
            / "strict-superpowers"
            / ".agents"
            / "skills"
            / "brainstorming"
        )
        target = repo / ".agents" / "skills" / "brainstorming"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source, target_is_directory=True)
        selection = {
            "effectiveMethodologyProfile": "core",
            "selectionSource": "explicit_config",
        }
        plan = deactivate_project_provider_skills(
            repo,
            "superpowers",
            PLUGIN_ROOT,
            codex_home=codex_home,
            selection=selection,
        )
        external_skills = Path(tempfile.mkdtemp(prefix="devflow-post-check-swap-"))
        external_target = external_skills / "brainstorming"
        external_target.symlink_to(source, target_is_directory=True)
        original_skills = repo / ".agents" / "skills.original"
        original_readlink = provider_deactivation_module.os.readlink
        swapped = False

        def swap_parent_before_anchored_readlink(path, *args, **kwargs):
            nonlocal swapped
            if kwargs.get("dir_fd") is not None and not swapped:
                swapped = True
                (repo / ".agents" / "skills").rename(original_skills)
                (repo / ".agents" / "skills").symlink_to(
                    external_skills,
                    target_is_directory=True,
                )
            return original_readlink(path, *args, **kwargs)

        with mock.patch.object(
            provider_deactivation_module.os,
            "readlink",
            side_effect=swap_parent_before_anchored_readlink,
        ):
            cleanup = deactivate_project_provider_skills(
                repo,
                "superpowers",
                PLUGIN_ROOT,
                codex_home=codex_home,
                apply=True,
                authorized_provider="superpowers",
                authorized_plan_digest=plan["planDigest"],
                selection=selection,
            )

        self.assertTrue(swapped)
        self.assertTrue(external_target.is_symlink())
        self.assertTrue((original_skills / "brainstorming").is_symlink())
        self.assertFalse(cleanup["ok"], cleanup)
        self.assertFalse(cleanup["changed"])

    def test_provider_deactivation_apply_removes_only_verified_symlinks_and_is_idempotent(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo(methodology_profile="core", roadmap_provider="none")
        fixture_skills = (
            PLUGIN_ROOT
            / "fixtures"
            / "provider-profiles"
            / "strict-superpowers"
            / ".agents"
            / "skills"
        )
        verified = repo / ".agents" / "skills" / "brainstorming"
        verified.symlink_to(fixture_skills / "brainstorming", target_is_directory=True)
        copied = repo / ".agents" / "skills" / "writing-plans"
        shutil.copytree(fixture_skills / "writing-plans", copied)
        unknown_source = (
            Path(tempfile.mkdtemp(prefix="cpo-unknown-skill-"))
            / "plugins"
            / "cache"
            / "superpowers"
            / "user-build"
            / "skills"
            / "test-driven-development"
        )
        unknown_source.mkdir(parents=True)
        (unknown_source / "SKILL.md").write_text(
            "---\nname: test-driven-development\ndescription: user-owned\n---\n"
        )
        unknown = repo / ".codex" / "skills" / "test-driven-development"
        unknown.parent.mkdir(parents=True, exist_ok=True)
        unknown.symlink_to(unknown_source, target_is_directory=True)
        legacy = repo / ".codex" / "skills" / "verification-before-completion"
        legacy_target = (
            codex_home
            / "plugins"
            / "cache"
            / "legacy"
            / "superpowers"
            / "6.0.3"
            / "skills"
            / "verification-before-completion"
        )
        legacy.symlink_to(legacy_target, target_is_directory=True)

        dry_run_args = (
            "--repo",
            str(repo),
            "--plugin-root",
            str(PLUGIN_ROOT),
            "--codex-home",
            str(codex_home),
            "--skip-official-installs",
            "--deactivate-provider",
            "superpowers",
            "--dry-run",
            "--json",
        )
        plan = run_json(
            "activate_project_dependencies.py",
            *dry_run_args,
        )["provider_deactivation"]
        args = (
            "--repo",
            str(repo),
            "--plugin-root",
            str(PLUGIN_ROOT),
            "--codex-home",
            str(codex_home),
            "--skip-official-installs",
            "--deactivate-provider",
            "superpowers",
            "--authorize-provider-cleanup",
            "superpowers",
            "--provider-cleanup-plan",
            plan["planDigest"],
            "--apply",
            "--json",
        )
        report = run_json("activate_project_dependencies.py", *args)

        cleanup = report["provider_deactivation"]
        by_skill = {item["skill"]: item for item in cleanup["items"]}
        self.assertTrue(cleanup["ok"], cleanup)
        self.assertTrue(cleanup["changed"])
        self.assertEqual(cleanup["status"], "applied_with_preserved_paths")
        self.assertTrue(cleanup["planDigestMatches"])
        self.assertEqual(by_skill["brainstorming"]["status"], "removed")
        self.assertEqual(by_skill["verification-before-completion"]["status"], "removed")
        self.assertEqual(
            by_skill["verification-before-completion"]["verification"],
            "exact_legacy_provider_target",
        )
        self.assertEqual(by_skill["writing-plans"]["status"], "preserved_copy")
        self.assertEqual(by_skill["test-driven-development"]["status"], "preserved_unknown_link")
        self.assertFalse(verified.is_symlink())
        self.assertFalse(legacy.is_symlink())
        self.assertTrue((copied / "SKILL.md").exists())
        self.assertTrue(unknown.is_symlink())
        self.assertIn("rollback", by_skill["brainstorming"])

        second_plan = run_json(
            "activate_project_dependencies.py",
            *dry_run_args,
        )["provider_deactivation"]
        second_args = [*args]
        second_args[second_args.index(plan["planDigest"])] = second_plan["planDigest"]
        second = run_json(
            "activate_project_dependencies.py",
            *second_args,
        )["provider_deactivation"]

        self.assertTrue(second["ok"], second)
        self.assertFalse(second["changed"])
        self.assertEqual(second["status"], "current_with_preserved_paths")
        self.assertTrue((copied / "SKILL.md").exists())
        self.assertTrue(unknown.is_symlink())

    def test_provider_deactivation_apply_blocks_temporary_unpersisted_selection(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo(
            enable_superpowers=True,
            methodology_profile="strict-superpowers",
            roadmap_provider="none",
        )
        source = (
            PLUGIN_ROOT
            / "fixtures"
            / "provider-profiles"
            / "strict-superpowers"
            / ".agents"
            / "skills"
            / "brainstorming"
        )
        target = repo / ".agents" / "skills" / "brainstorming"
        shutil.rmtree(target)
        target.symlink_to(source, target_is_directory=True)
        before_config = (repo / ".dev-flow.json").read_bytes()
        plan = run_json(
            "activate_project_dependencies.py",
            "--repo",
            str(repo),
            "--plugin-root",
            str(PLUGIN_ROOT),
            "--codex-home",
            str(codex_home),
            "--skip-official-installs",
            "--methodology-profile",
            "core",
            "--deactivate-provider",
            "superpowers",
            "--dry-run",
            "--json",
        )["provider_deactivation"]

        result = subprocess.run(
            [
                sys.executable,
                str(PLUGIN_ROOT / "scripts" / "activate_project_dependencies.py"),
                "--repo",
                str(repo),
                "--plugin-root",
                str(PLUGIN_ROOT),
                "--codex-home",
                str(codex_home),
                "--skip-official-installs",
                "--methodology-profile",
                "core",
                "--deactivate-provider",
                "superpowers",
                "--authorize-provider-cleanup",
                "superpowers",
                "--provider-cleanup-plan",
                plan["planDigest"],
                "--apply",
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1, result.stderr)
        cleanup = json.loads(result.stdout)["provider_deactivation"]
        self.assertEqual(cleanup["status"], "activation_prerequisite_failed")
        self.assertEqual(cleanup["mode"], "blocked")
        self.assertIn("selection_not_persisted", cleanup["blockingReasons"])
        self.assertFalse(cleanup["changed"])
        self.assertTrue(target.is_symlink())
        self.assertEqual((repo / ".dev-flow.json").read_bytes(), before_config)

    def test_provider_deactivation_rolls_back_removed_links_when_apply_fails(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo(methodology_profile="core", roadmap_provider="none")
        fixture_skills = (
            PLUGIN_ROOT
            / "fixtures"
            / "provider-profiles"
            / "strict-superpowers"
            / ".agents"
            / "skills"
        )
        first = repo / ".agents" / "skills" / "brainstorming"
        second = repo / ".agents" / "skills" / "test-driven-development"
        first.symlink_to(fixture_skills / "brainstorming", target_is_directory=True)
        second.symlink_to(
            fixture_skills / "test-driven-development",
            target_is_directory=True,
        )
        selection = {"effectiveMethodologyProfile": "core"}
        plan = deactivate_project_provider_skills(
            repo,
            "superpowers",
            PLUGIN_ROOT,
            codex_home=codex_home,
            selection=selection,
        )
        original_unlink = provider_deactivation_module.os.unlink

        def fail_second(path, *args, **kwargs):
            if Path(path).name == "test-driven-development":
                raise OSError("injected unlink failure")
            return original_unlink(path, *args, **kwargs)

        with mock.patch.object(
            provider_deactivation_module.os,
            "unlink",
            new=fail_second,
        ):
            cleanup = deactivate_project_provider_skills(
                repo,
                "superpowers",
                PLUGIN_ROOT,
                codex_home=codex_home,
                apply=True,
                authorized_provider="superpowers",
                authorized_plan_digest=plan["planDigest"],
                selection=selection,
            )

        by_skill = {item["skill"]: item for item in cleanup["items"]}
        self.assertFalse(cleanup["ok"], cleanup)
        self.assertEqual(cleanup["status"], "apply_failed_rolled_back")
        self.assertFalse(cleanup["changed"])
        self.assertEqual(cleanup["rollbackFailures"], [])
        self.assertEqual(by_skill["brainstorming"]["status"], "rolled_back")
        self.assertEqual(
            by_skill["test-driven-development"]["status"],
            "preserved_apply_failed",
        )
        self.assertTrue(first.is_symlink())
        self.assertTrue(second.is_symlink())

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
        legacy.write_bytes((PLUGIN_ROOT / "skills" / "project-orchestrator" / "SKILL.md").read_bytes())

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
        legacy.write_bytes((PLUGIN_ROOT / "skills" / "project-orchestrator" / "SKILL.md").read_bytes())

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

        provider_root = (
            codex_home / "plugins" / "cache" / "openai-curated-remote" / "superpowers" / "local"
        )
        report = ensure_project_local_skills(
            repo,
            plugin_root,
            codex_home,
            dry_run=True,
            selection={"effectiveMethodologyProfile": "strict-superpowers"},
            provider_diagnosis={"providers": {"superpowers": {"root": str(provider_root)}}},
        )
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

        provider_root = (
            codex_home / "plugins" / "cache" / "openai-curated-remote" / "superpowers" / "local"
        )
        report = ensure_project_local_skills(
            repo,
            plugin_root,
            codex_home,
            dry_run=False,
            refresh_existing=True,
            selection={"effectiveMethodologyProfile": "strict-superpowers"},
            provider_diagnosis={"providers": {"superpowers": {"root": str(provider_root)}}},
        )
        brainstorming = next(item for item in report["items"] if item["skill"] == "brainstorming")

        self.assertEqual(brainstorming["status"], "refreshed-link")
        self.assertEqual(target.resolve(), Path(brainstorming["source"]).resolve())

    def test_openspec_sync_workflow_is_managed(self):
        self.assertEqual(
            LEGACY_OPENSPEC_SKILLS,
            [
                "openspec-propose",
                "openspec-explore",
                "openspec-apply-change",
                "openspec-sync-specs",
                "openspec-archive-change",
            ],
        )

    def test_activation_bridges_generated_openspec_sync_skill_to_official_layout(self):
        repo = Path(tempfile.mkdtemp(prefix="cpo-openspec-sync-repo-"))
        codex_home = self.make_codex_home()
        source = repo / ".codex" / "skills" / "openspec-sync-specs" / "SKILL.md"
        source.parent.mkdir(parents=True)
        source.write_text(
            '---\nname: openspec-sync-specs\nmetadata:\n  author: openspec\n  generatedBy: "1.5.0"\n---\n'
        )

        report = ensure_project_local_skills(repo, PLUGIN_ROOT, codex_home, dry_run=False, refresh_existing=True)

        item = next(item for item in report["items"] if item["skill"] == "openspec-sync-specs")
        self.assertTrue(item["ok"], item)
        self.assertEqual(item["provider"], "openspec")
        self.assertIn(item["status"], {"linked", "copied"})
        self.assertTrue((repo / ".agents" / "skills" / "openspec-sync-specs" / "SKILL.md").exists())

    def test_activation_refreshes_generated_openspec_official_copy_when_requested(self):
        repo = Path(tempfile.mkdtemp(prefix="cpo-openspec-refresh-repo-"))
        codex_home = self.make_codex_home()
        source = repo / ".codex" / "skills" / "openspec-propose" / "SKILL.md"
        source.parent.mkdir(parents=True)
        source.write_text(
            '---\nname: openspec-propose\nmetadata:\n  author: openspec\n  generatedBy: "1.5.0"\n---\n'
        )
        target = repo / ".agents" / "skills" / "openspec-propose" / "SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_text(
            '---\nname: openspec-propose\nmetadata:\n  author: openspec\n  generatedBy: "1.4.1"\n---\n'
        )

        report = ensure_project_local_skills(repo, PLUGIN_ROOT, codex_home, dry_run=False, refresh_existing=True)

        item = next(item for item in report["items"] if item["skill"] == "openspec-propose")
        self.assertTrue(item["ok"], item)
        self.assertIn(item["status"], {"refreshed-link", "refreshed-copy"})
        self.assertIn('generatedBy: "1.5.0"', target.read_text())

    def test_activation_preserves_user_authored_openspec_official_skill(self):
        repo = Path(tempfile.mkdtemp(prefix="cpo-openspec-custom-repo-"))
        codex_home = self.make_codex_home()
        source = repo / ".codex" / "skills" / "openspec-propose" / "SKILL.md"
        source.parent.mkdir(parents=True)
        source.write_text(
            '---\nname: openspec-propose\nmetadata:\n  author: openspec\n  generatedBy: "1.5.0"\n---\n'
        )
        target = repo / ".agents" / "skills" / "openspec-propose" / "SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_text("---\nname: openspec-propose\ndescription: custom local wrapper\n---\n")

        report = ensure_project_local_skills(repo, PLUGIN_ROOT, codex_home, dry_run=False, refresh_existing=True)

        item = next(item for item in report["items"] if item["skill"] == "openspec-propose")
        self.assertTrue(item["ok"], item)
        self.assertEqual(item["status"], "already-present")
        self.assertIn("custom local wrapper", target.read_text())

    def test_update_dry_run_reports_external_versions_without_mutating_updates(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo(
            enable_gsd=True,
            methodology_profile="core",
            roadmap_provider="gsd",
        )
        openspec_skill = codex_home / "skills" / "openspec-propose" / "SKILL.md"
        openspec_skill.parent.mkdir(parents=True)
        openspec_skill.write_text('---\nname: openspec-propose\nmetadata:\n  generatedBy: "1.5.0"\n---\n')

        def fake_run(command, cwd=None, timeout=300):
            if command[:3] == ["npm", "view", "@opengsd/gsd-core"]:
                return {"ok": True, "returncode": 0, "stdout": json.dumps({"version": "1.6.1"}), "stderr": ""}
            if command[:3] == ["npm", "view", "@fission-ai/openspec"]:
                return {"ok": True, "returncode": 0, "stdout": json.dumps({"version": "1.5.0"}), "stderr": ""}
            raise AssertionError(f"unexpected command: {command}")

        with mock.patch.object(auto_update, "executable_exists", return_value=True), mock.patch.object(
            auto_update, "run_command", side_effect=fake_run
        ):
            results = auto_update.run_external_updaters(codex_home, apply=False, repo=repo)

        by_name = {item["name"]: item for item in results}
        self.assertEqual(by_name["gsd-core"]["status"], "unchanged")
        self.assertEqual(by_name["gsd-core"]["current"], "1.6.1")
        self.assertEqual(by_name["gsd-core"]["latest"], "1.6.1")
        self.assertIn("expectedVersion", by_name["gsd-core"])
        self.assertEqual(by_name["gsd-core"]["expectedVersion"], "1.6.1")
        self.assertIn("provenanceSource", by_name["gsd-core"])
        self.assertTrue(by_name["gsd-core"]["provenanceSource"].endswith("dependency-provenance.json"))
        self.assertIn("installCommand", by_name["gsd-core"])
        self.assertEqual(
            by_name["gsd-core"]["installCommand"],
            ["npx", "-y", "@opengsd/gsd-core@1.6.1", "--codex", "--local", "--profile=standard"],
        )
        self.assertIn("@opengsd/gsd-core", by_name["gsd-core"]["detail"])
        self.assertNotIn("get-shit-done-cc", by_name["gsd-core"]["detail"])
        self.assertEqual(by_name["openspec-cli"]["status"], "unchanged")
        self.assertIn("expectedVersion", by_name["openspec-cli"])
        self.assertEqual(by_name["openspec-cli"]["expectedVersion"], "1.5.0")
        self.assertIn("installCommand", by_name["openspec-cli"])
        self.assertEqual(
            by_name["openspec-cli"]["installCommand"],
            ["npm", "install", "-g", "@fission-ai/openspec@1.5.0"],
        )
        self.assertEqual(by_name["openspec-cli"]["latest"], "1.5.0")

    def test_update_dry_run_keeps_selected_superpowers_fallback_pinned(self):
        codex_home = self.make_codex_home(superpowers_version="5.1.3", superpowers_channel="openai-curated")
        repo = self.make_project_repo(
            enable_superpowers=True,
            methodology_profile="strict-superpowers",
            roadmap_provider="none",
            provider_selectors={
                "superpowers": {
                    "source_channel": "openai-curated",
                    "version": "5.1.3",
                }
            },
        )

        with mock.patch.object(auto_update, "executable_exists", return_value=False):
            results = auto_update.run_external_updaters(codex_home, apply=False, repo=repo)

        by_name = {item["name"]: item for item in results}
        self.assertIn("superpowers", by_name)
        superpowers = by_name["superpowers"]
        self.assertEqual(superpowers["status"], "unchanged")
        self.assertEqual(superpowers["current"], "5.1.3")
        self.assertEqual(superpowers["latest"], "5.1.3")
        self.assertEqual(superpowers["recommendedVersion"], "5.1.3")
        self.assertEqual(
            superpowers["installCommand"],
            ["codex", "plugin", "add", "superpowers@openai-curated", "--json"],
        )

    def test_update_apply_repairs_only_the_selected_superpowers_source(self):
        codex_home = self.make_codex_home(
            superpowers_version="6.0.3",
            superpowers_channel="superpowers-upstream-v6-0-3",
        )
        config = codex_home / "config.toml"
        config.write_text(
            config.read_text()
            + "\n[marketplaces.superpowers-upstream-v6-0-3]\nsource = 'fixture'\n"
        )
        repo = self.make_project_repo(
            enable_superpowers=True,
            methodology_profile="strict-superpowers",
            roadmap_provider="none",
            provider_selectors={
                "superpowers": {
                    "source_channel": "superpowers-upstream-v6-0-3",
                    "version": "6.0.3",
                }
            },
        )
        skill = (
            codex_home
            / "plugins"
            / "cache"
            / "superpowers-upstream-v6-0-3"
            / "superpowers"
            / "local"
            / "skills"
            / "brainstorming"
            / "SKILL.md"
        )
        skill.write_text(skill.read_text() + "\ndrift\n")
        commands = []
        before_config = (codex_home / "config.toml").read_text()

        def fake_run(command, cwd=None, timeout=300):
            commands.append(command)
            if command[:3] == ["codex", "plugin", "add"]:
                return {
                    "ok": True,
                    "returncode": 0,
                    "stdout": json.dumps(
                        {"pluginId": "superpowers@superpowers-upstream-v6-0-3", "version": "6.0.3"}
                    ),
                    "stderr": "",
                }
            raise AssertionError(f"unexpected command: {command}")

        with mock.patch.object(
            auto_update,
            "executable_exists",
            side_effect=lambda name: name == "codex",
        ), mock.patch.object(
            auto_update,
            "run_command",
            side_effect=fake_run,
        ):
            results = auto_update.run_external_updaters(codex_home, apply=True, repo=repo)

        by_name = {item["name"]: item for item in results}
        self.assertEqual(by_name["superpowers"]["status"], "updated-or-unchanged")
        self.assertEqual(
            commands,
            [["codex", "plugin", "add", "superpowers@superpowers-upstream-v6-0-3", "--json"]],
        )
        self.assertEqual((codex_home / "config.toml").read_text(), before_config)

    def test_update_dry_run_reports_current_superpowers_unchanged(self):
        codex_home = self.make_codex_home(
            superpowers_version="6.1.1",
            superpowers_channel="openai-curated-remote",
        )
        repo = self.make_project_repo(
            enable_superpowers=True,
            methodology_profile="strict-superpowers",
            roadmap_provider="none",
            provider_selectors={
                "superpowers": {
                    "source_channel": "openai-curated-remote",
                    "version": "6.1.1",
                }
            },
        )

        with mock.patch.object(auto_update, "executable_exists", return_value=False):
            results = auto_update.run_external_updaters(codex_home, apply=False, repo=repo)

        superpowers = {item["name"]: item for item in results}["superpowers"]
        self.assertEqual(superpowers["status"], "unchanged")
        self.assertEqual(superpowers["current"], "6.1.1")

    def test_gsd_apply_uses_opengsd_core_local_installer(self):
        codex_home = self.make_codex_home()
        repo = self.make_project_repo(
            enable_gsd=True,
            methodology_profile="core",
            roadmap_provider="gsd",
        )
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
            (["npx", "-y", "@opengsd/gsd-core@1.6.1", "--codex", "--local", "--profile=standard"], repo),
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

    def test_git_marketplace_plugin_source_uses_local_snapshot(self):
        codex_home = self.make_codex_home()
        marketplace_root = codex_home / ".tmp" / "marketplaces" / "cy-codex-skills"
        source = marketplace_root / "plugins" / "dev-flow"
        cache = codex_home / "plugins" / "cache" / "cy-codex-skills" / "dev-flow" / "1.0.0"
        source.mkdir(parents=True)
        cache.mkdir(parents=True)
        (source / ".codex-plugin").mkdir()
        (cache / ".codex-plugin").mkdir()
        (source / ".codex-plugin" / "plugin.json").write_text('{"name":"dev-flow"}\n')
        (cache / ".codex-plugin" / "plugin.json").write_text('{"name":"dev-flow"}\n')
        (source / "payload.txt").write_text("same\n")
        (cache / "payload.txt").write_text("same\n")
        catalog = marketplace_root / ".agents" / "plugins"
        catalog.mkdir(parents=True)
        (catalog / "marketplace.json").write_text(
            json.dumps({"plugins": [{"name": "dev-flow", "source": {"path": "./plugins/dev-flow"}}]})
        )
        config = {
            "marketplaces": {
                "cy-codex-skills": {
                    "source_type": "git",
                    "source": "https://github.com/cYz26/cy-codex-skills.git",
                    "ref": "main",
                }
            },
            "plugins": {"dev-flow@cy-codex-skills": {"enabled": True}},
        }

        dry_run = auto_update.plugin_install_results(config, apply=False, codex_home=codex_home)

        self.assertEqual(dry_run[0]["name"], "dev-flow@cy-codex-skills")
        self.assertEqual(dry_run[0]["status"], "would-refresh")
        self.assertEqual(dry_run[0]["source"], str(source.resolve()))

        verify = auto_update.plugin_cache_verification_results(codex_home, config)

        self.assertEqual(verify[0]["name"], "dev-flow@cy-codex-skills")
        self.assertEqual(verify[0]["status"], "matches-source")
        self.assertEqual(verify[0]["source"], str(source.resolve()))

    def test_git_marketplace_plugin_source_accepts_single_plugin_snapshot_root(self):
        codex_home = self.make_codex_home()
        source = codex_home / ".tmp" / "marketplaces" / "superpowers-dev"
        cache = codex_home / "plugins" / "cache" / "superpowers-dev" / "superpowers" / "6.0.3"
        source.mkdir(parents=True)
        cache.mkdir(parents=True)
        (source / ".codex-plugin").mkdir()
        (cache / ".codex-plugin").mkdir()
        (source / ".codex-plugin" / "plugin.json").write_text('{"name":"superpowers"}\n')
        (cache / ".codex-plugin" / "plugin.json").write_text('{"name":"superpowers"}\n')
        (source / "payload.txt").write_text("same\n")
        (cache / "payload.txt").write_text("same\n")
        config = {
            "marketplaces": {
                "superpowers-dev": {
                    "source_type": "git",
                    "source": "https://github.com/obra/superpowers.git",
                    "ref": "main",
                }
            },
            "plugins": {"superpowers@superpowers-dev": {"enabled": True}},
        }

        dry_run = auto_update.plugin_install_results(config, apply=False, codex_home=codex_home)

        self.assertEqual(dry_run[0]["name"], "superpowers@superpowers-dev")
        self.assertEqual(dry_run[0]["status"], "would-refresh")
        self.assertEqual(dry_run[0]["source"], str(source.resolve()))

        verify = auto_update.plugin_cache_verification_results(codex_home, config)

        self.assertEqual(verify[0]["name"], "superpowers@superpowers-dev")
        self.assertEqual(verify[0]["status"], "matches-source")
        self.assertEqual(verify[0]["source"], str(source.resolve()))

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

    def test_dev_flow_refresh_skill_is_packaged_with_trigger_language(self):
        skill_path = PLUGIN_ROOT / "skills" / "dev-flow-refresh" / "SKILL.md"
        text = skill_path.read_text()
        lowered = text.lower()

        self.assertIn("name: dev-flow-refresh", text)
        self.assertIn("Use when", text)
        for phrase in [
            "devflow",
            "dev-flow",
            "upgrade",
            "local/global devflow",
            "active projects",
            "project-local",
        ]:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, lowered)

    def test_dev_flow_refresh_skill_encodes_global_first_project_second_sop(self):
        text = (PLUGIN_ROOT / "skills" / "dev-flow-refresh" / "SKILL.md").read_text()
        lowered = text.lower()

        for phrase in [
            "codex plugin add dev-flow@cy-codex-skills --json",
            "doctor_workflow.py",
            "plugin_project_migration.py",
            "activate_project_dependencies.py",
            "scaffold_workflow.py",
            "validate_workflow_state.py",
            "AGENTS.md.generated",
            "AGENTS.md",
            "AGENTS Drift Gate",
            "required",
            "durable workflow rules",
            "AGENTS status",
            "generated-deferred",
            ".codex/skills",
            "git status",
        ]:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        self.assertIn("global", lowered)
        self.assertIn("before project", lowered)
        self.assertIn("do not overwrite", lowered)
        self.assertIn("explicit", lowered)

    def test_missing_agents_guidance_reports_current_durable_devflow_sections(self):
        text = "\n".join(
            [
                "## Purpose",
                "## AI Coding Planning Rules",
                "Target State",
                "Completion Contract",
                "Capability Slices",
                "Execution Ledger",
                "Acceptance Criteria",
                "Validation Commands",
                "Final Verification",
                "openspec/changes",
                "docs/superpowers/specs",
                "docs/superpowers/plans",
                "canonical",
            ]
        )

        missing = missing_agents_guidance(text)

        for label in [
            "Goal Workflow",
            "Workflow Mode Routing",
            "Plugin Eval Gate",
            "Local Reference Update Reminder",
            "DevFlow Refresh Workflow",
        ]:
            with self.subTest(label=label):
                self.assertIn(label, missing)

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
        release_repo = self.make_project_repo()
        for skill in PROJECT_ORCHESTRATOR_SKILLS:
            source = RELEASE_PLUGIN_ROOT / "skills" / skill / "SKILL.md"
            target = release_repo / ".agents" / "skills" / skill / "SKILL.md"
            target.write_bytes(source.read_bytes())
        release_report = run_json(
            "codex_plugin_preflight.py",
            "--plugin-root",
            str(RELEASE_PLUGIN_ROOT),
            "--marketplace",
            str(MARKETPLACE),
            "--repo",
            str(release_repo),
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

        dev_repo = self.make_project_repo()
        dev_report = run_json(
            "codex_plugin_preflight.py",
            "--plugin-root",
            str(PLUGIN_ROOT),
            "--marketplace",
            str(DEV_MARKETPLACE),
            "--repo",
            str(dev_repo),
            "--codex-home",
            str(codex_home),
            "--config",
            str(codex_home / "config.toml"),
            "--json",
        )
        self.assertTrue(dev_report["ok"], dev_report)


if __name__ == "__main__":
    unittest.main()
