import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TEST_ROOT = Path(__file__).resolve().parent
PLUGIN_ROOT = TEST_ROOT.parent
sys.path.insert(0, str(TEST_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

import codex_auto_update_plugins_skills as auto_update
import workflow_project_activation as activation
import workflow_project_skill_install as skill_install
from workflow_dependencies import dependency_report
from workflow_dependency_catalog import OPENSPEC_WORKFLOW_SKILLS
from workflow_dependency_provenance import (
    dependency_provenance_fields,
    dependency_provenance_record,
    dependency_update_command,
)


EXPECTED_SKILLS = [
    "openspec-propose",
    "openspec-explore",
    "openspec-apply-change",
    "openspec-update-change",
    "openspec-sync-specs",
    "openspec-archive-change",
]


class OpenSpec16IntegrationTests(unittest.TestCase):
    def make_repo(self) -> Path:
        repo = Path(tempfile.mkdtemp(prefix="devflow-openspec-16-repo-"))
        (repo / ".dev-flow.json").write_text(
            json.dumps(
                {
                    "workflow": {
                        "mode": "full-openspec",
                        "methodology_profile": "core",
                        "roadmap_provider": "none",
                    }
                }
            )
            + "\n"
        )
        return repo

    def make_codex_home(self) -> Path:
        home = Path(tempfile.mkdtemp(prefix="devflow-openspec-16-codex-"))
        (home / "config.toml").write_text('model = "gpt-5"\n')
        return home

    def write_generated_skills(
        self,
        project: Path,
        *,
        version: str = "1.6.0",
        skills: list[str] | None = None,
    ) -> Path:
        skill_root = project / ".codex" / "skills"
        for name in skills or EXPECTED_SKILLS:
            path = skill_root / name / "SKILL.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "---\n"
                f"name: {name}\n"
                "description: Official OpenSpec workflow fixture\n"
                "allowed-tools: Bash(openspec:*)\n"
                "metadata:\n"
                f'  generatedBy: "{version}"\n'
                "---\n"
                f"# {name}\n"
            )
        return skill_root

    def generated_target(self, repo: Path, skill: str) -> Path:
        return repo / ".agents" / "skills" / skill

    def fake_successful_generation(self, captured: dict[str, object] | None = None):
        def fake_run(command, cwd, dry_run, provenance_source=None, environment=None):
            self.assertFalse(dry_run)
            self.assertEqual(command[:2], ["openspec", "init"])
            project = Path(command[-2])
            self.assertEqual(Path(cwd), project)
            self.assertNotEqual(project, captured.get("real_repo") if captured else None)
            self.assertEqual(environment["OPENSPEC_TELEMETRY"], "0")
            self.assertNotEqual(environment["CODEX_HOME"], str(captured.get("codex_home")) if captured else None)
            self.assertNotEqual(
                environment["XDG_CONFIG_HOME"],
                str(captured.get("real_xdg")) if captured else None,
            )
            self.write_generated_skills(project)
            if captured is not None:
                captured["staging_project"] = project
                captured["environment"] = dict(environment)
            return {
                "ok": True,
                "command": command,
                "returncode": 0,
                "stdout": "OpenSpec initialized\n",
                "stderr": "",
                "environment": dict(environment),
                "provenanceSource": provenance_source,
            }

        return fake_run

    def test_pins_released_version_node_runtime_and_six_workflows(self):
        record = dependency_provenance_record("openspec-cli", PLUGIN_ROOT)

        self.assertEqual(OPENSPEC_WORKFLOW_SKILLS, EXPECTED_SKILLS)
        self.assertEqual(record["expectedVersion"], "1.6.0")
        self.assertEqual(record["runtimeRequirements"], {"node": ">=20.19.0"})
        self.assertEqual(
            record["installCommand"],
            ["npm", "install", "-g", "@fission-ai/openspec@1.6.0"],
        )
        self.assertEqual(record["updateCommand"], record["installCommand"])
        self.assertEqual(dependency_update_command("openspec-cli", PLUGIN_ROOT), record["installCommand"])
        self.assertEqual(
            dependency_provenance_fields("openspec-cli", PLUGIN_ROOT)["runtimeRequirements"],
            {"node": ">=20.19.0"},
        )

    def test_dependency_report_blocks_unsupported_node_before_use(self):
        repo = self.make_repo()
        codex_home = self.make_codex_home()
        bin_dir = Path(tempfile.mkdtemp(prefix="devflow-openspec-16-bin-"))
        for name, output in {
            "codex": "codex fixture",
            "openspec": "1.6.0",
            "node": "v18.20.0",
        }.items():
            path = bin_dir / name
            path.write_text(f"#!/bin/sh\nprintf '{output}\\n'\n")
            path.chmod(0o755)

        with mock.patch.dict(os.environ, {"PATH": str(bin_dir)}):
            report = dependency_report(PLUGIN_ROOT, codex_home, codex_home / "config.toml", False, repo)

        openspec = next(item for item in report["dependencies"] if item["name"] == "openspec-cli")
        self.assertEqual(openspec["status"], "runtime_incompatible")
        self.assertEqual(openspec["runtimeRequirements"], {"node": ">=20.19.0"})
        self.assertEqual(openspec["runtimeRequirementResults"]["node"]["installedVersion"], "18.20.0")
        self.assertFalse(openspec["runtimeRequirementResults"]["node"]["ok"])

    def test_dry_run_declares_isolation_without_invocation_or_write(self):
        repo = self.make_repo()
        codex_home = self.make_codex_home()
        before = sorted(str(path.relative_to(repo)) for path in repo.rglob("*"))

        with mock.patch.object(activation, "run_command") as run:
            report = activation.activate_project_dependencies(
                repo,
                dry_run=True,
                plugin_root=PLUGIN_ROOT,
                codex_home=codex_home,
            )

        run.assert_not_called()
        self.assertTrue(report["ok"], report)
        record = next(item for item in report["commands"] if item.get("provider") == "openspec")
        self.assertEqual(record["kind"], "isolated-skill-generation")
        self.assertTrue(record["skipped"])
        self.assertEqual(record["generation"]["status"], "planned")
        self.assertNotIn(str(repo), record["command"])
        self.assertEqual(record["environment"]["OPENSPEC_TELEMETRY"], "0")
        self.assertTrue(record["environment"]["XDG_CONFIG_HOME"].startswith("{isolated"))
        self.assertTrue(record["environment"]["CODEX_HOME"].startswith("{isolated"))
        statuses = {
            item["status"]
            for item in report["local_skills"]["items"]
            if item["provider"] == "openspec"
        }
        self.assertEqual(statuses, {"would-copy-after-openspec-generation"})
        self.assertEqual(before, sorted(str(path.relative_to(repo)) for path in repo.rglob("*")))

    def test_apply_generates_in_isolation_copies_six_and_cleans_staging(self):
        repo = self.make_repo()
        codex_home = self.make_codex_home()
        real_xdg = Path(tempfile.mkdtemp(prefix="devflow-openspec-real-xdg-"))
        real_config = real_xdg / "openspec" / "config.json"
        real_config.parent.mkdir(parents=True)
        real_config.write_text('{"profile":"custom","delivery":"commands"}\n')
        real_prompts = codex_home / "prompts"
        real_prompts.mkdir()
        sentinel = real_prompts / "keep.md"
        sentinel.write_text("keep\n")
        before_config = real_config.read_bytes()
        before_prompts = {path.name: path.read_bytes() for path in real_prompts.iterdir()}
        captured = {"real_repo": repo, "codex_home": codex_home, "real_xdg": real_xdg}

        with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(real_xdg)}), mock.patch.object(
            activation,
            "run_command",
            side_effect=self.fake_successful_generation(captured),
        ):
            report = activation.activate_project_dependencies(
                repo,
                plugin_root=PLUGIN_ROOT,
                codex_home=codex_home,
                refresh_project_skills=True,
            )

        self.assertTrue(report["ok"], report)
        self.assertEqual(real_config.read_bytes(), before_config)
        self.assertEqual(
            {path.name: path.read_bytes() for path in real_prompts.iterdir()},
            before_prompts,
        )
        self.assertFalse((repo / ".codex" / "skills").exists())
        self.assertFalse(Path(captured["staging_project"]).exists())
        for name in EXPECTED_SKILLS:
            target = self.generated_target(repo, name)
            self.assertTrue((target / "SKILL.md").is_file(), report)
            self.assertFalse(target.is_symlink())
            self.assertIn('generatedBy: "1.6.0"', (target / "SKILL.md").read_text())

    def test_wrong_or_incomplete_generation_fails_before_openspec_target_writes(self):
        for label, skills, version in [
            ("missing", EXPECTED_SKILLS[:-1], "1.6.0"),
            ("additional", [*EXPECTED_SKILLS, "openspec-unreleased"], "1.6.0"),
            ("wrong-version", EXPECTED_SKILLS, "1.5.0"),
        ]:
            with self.subTest(label=label):
                repo = self.make_repo()
                codex_home = self.make_codex_home()

                def fake_run(command, cwd, dry_run, provenance_source=None, environment=None):
                    self.write_generated_skills(Path(command[-2]), skills=skills, version=version)
                    return {"ok": True, "command": command, "returncode": 0, "stdout": "", "stderr": ""}

                with mock.patch.object(activation, "run_command", side_effect=fake_run):
                    report = activation.activate_project_dependencies(
                        repo,
                        plugin_root=PLUGIN_ROOT,
                        codex_home=codex_home,
                        refresh_project_skills=True,
                    )

                self.assertFalse(report["ok"], report)
                command = next(item for item in report["commands"] if item.get("provider") == "openspec")
                self.assertEqual(command["generation"]["status"], "contract_mismatch")
                self.assertFalse(any(self.generated_target(repo, name).exists() for name in EXPECTED_SKILLS))
                self.assertFalse(Path(command["generation"]["stagingProject"]).exists())

    def test_command_failure_cleans_staging_and_does_not_mutate_openspec_targets(self):
        repo = self.make_repo()
        codex_home = self.make_codex_home()
        captured = {}

        def failed(command, cwd, dry_run, provenance_source=None, environment=None):
            captured["project"] = Path(command[-2])
            return {"ok": False, "command": command, "returncode": 9, "stdout": "", "stderr": "boom"}

        with mock.patch.object(activation, "run_command", side_effect=failed):
            report = activation.activate_project_dependencies(
                repo,
                plugin_root=PLUGIN_ROOT,
                codex_home=codex_home,
            )

        self.assertFalse(report["ok"], report)
        self.assertFalse(captured["project"].exists())
        self.assertFalse(any(self.generated_target(repo, name).exists() for name in EXPECTED_SKILLS))

    def test_staging_setup_failure_is_reported_and_cleans_temporary_root(self):
        staging_root = Path(tempfile.mkdtemp(prefix="devflow-openspec-setup-failure-"))
        record = activation.isolated_openspec_generation_record(
            dependency_provenance_record("openspec-cli", PLUGIN_ROOT),
            "fixture-provenance.json",
        )

        with mock.patch.object(
            activation.tempfile,
            "mkdtemp",
            return_value=str(staging_root),
        ), mock.patch.object(Path, "mkdir", side_effect=OSError("setup fixture")):
            result, source_root, cleanup_root = activation.run_openspec_generation(
                record,
                dry_run=False,
            )

        self.assertFalse(result["ok"], result)
        self.assertEqual(result["generation"]["status"], "staging_setup_failed")
        self.assertIsNone(source_root)
        self.assertIsNone(cleanup_root)
        self.assertFalse(staging_root.exists())

    def test_generated_refresh_is_copy_and_survives_source_cleanup(self):
        repo = self.make_repo()
        codex_home = self.make_codex_home()
        staging_project = Path(tempfile.mkdtemp(prefix="devflow-openspec-source-"))
        source_root = self.write_generated_skills(staging_project)
        stale = self.generated_target(repo, "openspec-propose")
        stale.mkdir(parents=True)
        (stale / "SKILL.md").write_text(
            '---\nname: openspec-propose\nmetadata:\n  generatedBy: "1.5.0"\n---\n'
        )

        report = skill_install.ensure_project_local_skills(
            repo,
            PLUGIN_ROOT,
            codex_home,
            dry_run=False,
            refresh_existing=True,
            openspec_skill_root=source_root,
        )
        shutil.rmtree(staging_project)

        self.assertTrue(report["ok"], report)
        item = next(item for item in report["items"] if item["skill"] == "openspec-propose")
        self.assertEqual(item["status"], "refreshed-copy")
        for name in EXPECTED_SKILLS:
            target = self.generated_target(repo, name)
            self.assertTrue((target / "SKILL.md").is_file())
            self.assertFalse(target.is_symlink())

    def test_custom_target_blocks_batch_without_overwrite_or_partial_copy(self):
        repo = self.make_repo()
        codex_home = self.make_codex_home()
        staging_project = Path(tempfile.mkdtemp(prefix="devflow-openspec-source-"))
        source_root = self.write_generated_skills(staging_project)
        custom = self.generated_target(repo, "openspec-propose")
        custom.mkdir(parents=True)
        custom_text = "---\nname: openspec-propose\ndescription: custom wrapper\n---\n"
        (custom / "SKILL.md").write_text(custom_text)

        report = skill_install.ensure_project_local_skills(
            repo,
            PLUGIN_ROOT,
            codex_home,
            dry_run=False,
            refresh_existing=True,
            openspec_skill_root=source_root,
        )

        self.assertFalse(report["ok"], report)
        item = next(item for item in report["items"] if item["skill"] == "openspec-propose")
        self.assertEqual(item["status"], "manual-source-conflict")
        self.assertEqual((custom / "SKILL.md").read_text(), custom_text)
        self.assertFalse(self.generated_target(repo, "openspec-explore").exists())

    def test_transaction_failure_restores_old_targets_and_removes_partial_copies(self):
        repo = self.make_repo()
        codex_home = self.make_codex_home()
        staging_project = Path(tempfile.mkdtemp(prefix="devflow-openspec-source-"))
        source_root = self.write_generated_skills(staging_project)
        stale = self.generated_target(repo, "openspec-propose")
        stale.mkdir(parents=True)
        old_text = '---\nname: openspec-propose\nmetadata:\n  generatedBy: "1.5.0"\n---\n'
        (stale / "SKILL.md").write_text(old_text)
        real_replace = getattr(skill_install, "replace_path", None)
        calls = 0

        def flaky_replace(source, target):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise OSError("transaction fixture")
            if real_replace is not None:
                return real_replace(source, target)
            return Path(source).replace(target)

        with mock.patch.object(skill_install, "replace_path", side_effect=flaky_replace, create=True):
            report = skill_install.ensure_project_local_skills(
                repo,
                PLUGIN_ROOT,
                codex_home,
                dry_run=False,
                refresh_existing=True,
                openspec_skill_root=source_root,
            )

        self.assertFalse(report["ok"], report)
        self.assertEqual((stale / "SKILL.md").read_text(), old_text)
        self.assertFalse(self.generated_target(repo, "openspec-explore").exists())
        hidden = list((repo / ".agents" / "skills").glob(".devflow-openspec-*"))
        self.assertEqual(hidden, [])

    def test_updater_prefers_cli_version_and_executes_pinned_command(self):
        codex_home = self.make_codex_home()
        stale = codex_home / "skills" / "openspec-propose" / "SKILL.md"
        stale.parent.mkdir(parents=True)
        stale.write_text('---\nmetadata:\n  generatedBy: "1.5.0"\n---\n')
        commands = []

        def fake_run(command, cwd=None, timeout=300):
            commands.append(command)
            if command == ["openspec", "--version"]:
                return {"ok": True, "returncode": 0, "stdout": "1.6.0\n", "stderr": ""}
            if command == ["npm", "install", "-g", "@fission-ai/openspec@1.6.0"]:
                return {"ok": True, "returncode": 0, "stdout": "updated\n", "stderr": ""}
            raise AssertionError(f"unexpected command: {command}")

        with mock.patch.object(
            auto_update,
            "executable_exists",
            side_effect=lambda name: name in {"openspec", "npm"},
        ), mock.patch.object(auto_update, "run_command", side_effect=fake_run):
            self.assertEqual(auto_update.installed_openspec_version(codex_home), "1.6.0")
            results = auto_update.run_external_updaters(codex_home, apply=True, repo=self.make_repo())

        openspec = next(item for item in results if item["name"] == "openspec-cli")
        self.assertEqual(openspec["status"], "updated-or-unchanged")
        self.assertEqual(
            openspec["recommendedCommand"],
            ["npm", "install", "-g", "@fission-ai/openspec@1.6.0"],
        )
        self.assertIn(["npm", "install", "-g", "@fission-ai/openspec@1.6.0"], commands)
        self.assertNotIn(["npm", "update", "-g", "@fission-ai/openspec"], commands)


if __name__ == "__main__":
    unittest.main()
