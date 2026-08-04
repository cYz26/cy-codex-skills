import hashlib
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

import codex_auto_update_plugins_skills as auto_update
from workflow_dependencies import dependency_report
from workflow_dependency_catalog import (
    OPENSPEC_WORKFLOW_SKILLS,
    PROJECT_ORCHESTRATOR_SKILLS,
)
from workflow_dependency_provenance import load_dependency_provenance
from workflow_project_activation import activate_project_dependencies


class DependencyTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="devflow-dependencies-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.codex_home = self.root / "codex-home"
        self.codex_home.mkdir()
        (self.codex_home / "config.toml").write_text("")
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.write_executable("codex", "#!/bin/sh\nprintf 'codex fixture\\n'\n")
        self.write_executable("openspec", "#!/bin/sh\nprintf '1.7.0\\n'\n")
        self.write_executable("node", "#!/bin/sh\nprintf 'v20.19.0\\n'\n")
        self.repo_counter = 0

    def write_executable(self, name, content):
        path = self.bin_dir / name
        path.write_text(content)
        path.chmod(0o755)
        return path

    def tool_environment(self):
        return mock.patch.dict(
            os.environ,
            {"PATH": f"{self.bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"},
        )

    def make_repo(
        self,
        *,
        openspec=True,
        project_skills=True,
        matt_skills=(),
    ):
        self.repo_counter += 1
        repo = self.root / f"repo-{self.repo_counter}"
        repo.mkdir()
        (repo / ".dev-flow.json").write_text(
            json.dumps({"workflow": {"mode": "full-openspec"}}) + "\n"
        )
        if openspec:
            config = repo / "openspec" / "config.yaml"
            config.parent.mkdir()
            config.write_text("schema: spec-driven\n")
        if project_skills:
            for skill in PROJECT_ORCHESTRATOR_SKILLS:
                source = PLUGIN_ROOT / "skills" / skill
                target = repo / ".agents" / "skills" / skill
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(source, target)
            for skill in OPENSPEC_WORKFLOW_SKILLS:
                path = repo / ".agents" / "skills" / skill / "SKILL.md"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    "---\n"
                    f"name: {skill}\n"
                    "description: Official OpenSpec workflow fixture\n"
                    "allowed-tools: Bash(openspec:*)\n"
                    "metadata:\n"
                    '  generatedBy: "1.7.0"\n'
                    "---\n"
                )
        for skill in matt_skills:
            source = PLUGIN_ROOT / "vendor" / "mattpocock-skills" / skill
            target = repo / ".agents" / "skills" / skill
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, target)
            shutil.copy2(
                PLUGIN_ROOT / "vendor" / "mattpocock-skills" / "UPSTREAM_LICENSE.txt",
                target / "UPSTREAM_LICENSE.txt",
            )
        return repo

    def report(self, repo, capabilities=()):
        with self.tool_environment():
            return dependency_report(
                PLUGIN_ROOT,
                codex_home=self.codex_home,
                config_path=self.codex_home / "config.toml",
                repo=repo,
                triggered_capabilities=set(capabilities),
            )

    def run_dependency_cli(self, repo, *args):
        environment = dict(os.environ)
        environment["PATH"] = (
            f"{self.bin_dir}{os.pathsep}{environment.get('PATH', '')}"
        )
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "check_dependencies.py"),
                "--plugin-root",
                str(PLUGIN_ROOT),
                "--repo",
                str(repo),
                "--codex-home",
                str(self.codex_home),
                "--config",
                str(self.codex_home / "config.toml"),
                *args,
            ],
            text=True,
            capture_output=True,
            check=False,
            env=environment,
        )

    def tree_snapshot(self, root):
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file()
        }

    def test_dependency_report_is_ready_for_current_project_and_triggered_tdd(self):
        repo = self.make_repo(matt_skills=("tdd",))

        report = self.report(repo, {"test-first-execution"})

        self.assertTrue(report["ok"], report)
        self.assertIn(report["status"], {"ready", "ready_with_recommendations"})
        self.assertEqual(report["triggeredCapabilities"], ["test-first-execution"])
        self.assertEqual(report["methodology"]["requiredSkills"], ["tdd"])
        self.assertTrue(report["methodology"]["skills"]["tdd"]["ready"])
        self.assertTrue(report["capabilities"]["test-first-execution"]["ready"])
        self.assertEqual(
            [item["name"] for item in report["dependencies"]],
            ["openspec-cli"],
        )
        checks = {item["name"]: item for item in report["checks"]}
        self.assertTrue(checks["workflow config current"]["ok"])
        self.assertTrue(checks["project openspec setup active"]["ok"])
        self.assertTrue(checks["project openspec update workflow available"]["ok"])
        self.assertTrue(checks["project methodology skill ready: tdd"]["ok"])
        self.assertTrue(checks["project DevFlow skill trusted: project-orchestrator"]["ok"])
        self.assertFalse(any("plugin-eval" in item["name"] for item in report["checks"]))

    def test_strict_dependency_report_includes_independently_requested_plugin_eval(self):
        repo = self.make_repo()
        with self.tool_environment():
            report = dependency_report(
                PLUGIN_ROOT,
                codex_home=self.codex_home,
                config_path=self.codex_home / "config.toml",
                repo=repo,
                strict=True,
            )

        self.assertEqual(
            [item["name"] for item in report["dependencies"]],
            ["openspec-cli", "plugin-eval"],
        )
        self.assertTrue(any("plugin-eval" in item["name"] for item in report["checks"]))

    def test_untriggered_matt_skills_are_not_required(self):
        repo = self.make_repo()

        report = self.report(repo)

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["methodology"]["requiredSkills"], [])
        self.assertEqual(report["methodology"]["skills"], {})
        self.assertTrue(
            all(item["ready"] for item in report["capabilities"].values()),
            report["capabilities"],
        )

    def test_triggered_matt_skill_missing_from_project_blocks_readiness(self):
        repo = self.make_repo()

        report = self.report(repo, {"test-first-execution"})

        self.assertFalse(report["ok"])
        self.assertEqual(report["methodology"]["status"], "missing_project_skills")
        self.assertEqual(report["methodology"]["missingSkills"], ["tdd"])
        self.assertFalse(report["capabilities"]["test-first-execution"]["ready"])
        failure = next(
            item
            for item in report["checks"]
            if item["name"] == "project methodology skill ready: tdd"
        )
        self.assertTrue(failure["required"])
        self.assertFalse(failure["ok"])

    def test_tampered_matt_resource_blocks_dependency_readiness(self):
        repo = self.make_repo(matt_skills=("tdd",))
        (repo / ".agents" / "skills" / "tdd" / "mocking.md").write_text("tampered\n")

        report = self.report(repo, {"test-first-execution"})

        self.assertFalse(report["ok"])
        self.assertEqual(report["methodology"]["status"], "source_drift")
        self.assertEqual(report["methodology"]["driftedFiles"], ["tdd/mocking.md"])

    def test_tampered_project_devflow_skill_blocks_readiness(self):
        repo = self.make_repo()
        skill_file = repo / ".agents" / "skills" / "project-orchestrator" / "SKILL.md"
        skill_file.write_text(skill_file.read_text() + "\nTampered.\n")

        report = self.report(repo)

        self.assertFalse(report["ok"])
        failure = next(
            item
            for item in report["checks"]
            if item["name"] == "project DevFlow skill trusted: project-orchestrator"
        )
        self.assertEqual(failure["status"], "source_conflict")

    def test_partial_devflow_skill_copy_blocks_activation_and_readiness(self):
        repo = self.make_repo()
        target = repo / ".agents" / "skills" / "dev-flow-refresh"
        shutil.rmtree(target)
        target.mkdir(parents=True)
        shutil.copy2(
            PLUGIN_ROOT / "skills" / "dev-flow-refresh" / "SKILL.md",
            target / "SKILL.md",
        )

        activation = activate_project_dependencies(
            repo,
            skip_official_installs=True,
            plugin_root=PLUGIN_ROOT,
            codex_home=self.codex_home,
            authorizations={"explicit_named_dependency_request"},
        )
        diagnosis = self.report(repo)

        activation_item = next(
            item for item in activation["local_skills"]["items"]
            if item["skill"] == "dev-flow-refresh"
        )
        dependency_item = next(
            item for item in diagnosis["checks"]
            if item["name"] == "project DevFlow skill trusted: dev-flow-refresh"
        )
        self.assertFalse(activation["ok"], activation)
        self.assertEqual(activation_item["status"], "source-conflict")
        self.assertFalse(diagnosis["ok"], diagnosis)
        self.assertEqual(dependency_item["status"], "source_conflict")

    def test_extra_symlink_in_devflow_skill_blocks_activation_parity(self):
        repo = self.make_repo()
        target = repo / ".agents" / "skills" / "dev-flow-refresh"
        outside = self.root / "outside-devflow-skill"
        outside.mkdir()
        (target / "extra-link").symlink_to(outside, target_is_directory=True)

        activation = activate_project_dependencies(
            repo,
            skip_official_installs=True,
            plugin_root=PLUGIN_ROOT,
            codex_home=self.codex_home,
            authorizations={"explicit_named_dependency_request"},
        )

        item = next(
            item for item in activation["local_skills"]["items"]
            if item["skill"] == "dev-flow-refresh"
        )
        self.assertFalse(activation["ok"], activation)
        self.assertEqual(item["status"], "source-conflict")

    def test_nonlocal_project_skill_root_blocks_readiness(self):
        repo = self.make_repo(project_skills=False)
        external = self.root / "external-skills"
        external.mkdir()
        agents = repo / ".agents"
        agents.mkdir()
        (agents / "skills").symlink_to(external, target_is_directory=True)

        report = self.report(repo)

        self.assertFalse(report["ok"])
        failures = [
            item
            for item in report["checks"]
            if item["name"].startswith("project DevFlow skill trusted:")
        ]
        self.assertTrue(failures)
        self.assertTrue(all(item["status"] == "nonlocal_skill_route" for item in failures))

    def test_symlinked_devflow_source_parent_is_untrusted(self):
        from workflow_dependency_checks import diagnose_project_devflow_skill

        plugin_root = self.root / "symlinked-plugin-source"
        plugin_root.mkdir()
        (plugin_root / "skills").symlink_to(
            PLUGIN_ROOT / "skills",
            target_is_directory=True,
        )
        repo = self.make_repo()

        report = diagnose_project_devflow_skill(
            repo,
            plugin_root,
            "project-orchestrator",
        )

        self.assertFalse(report["ready"], report)
        self.assertEqual(report["status"], "source_untrusted")

    def test_dependency_report_does_not_expose_runtime_config_secrets(self):
        secret = "devflow-secret-must-not-leak"
        (self.codex_home / "config.toml").write_text(
            "[mcp_servers.fixture]\n"
            'command = "fixture"\n'
            "[mcp_servers.fixture.env]\n"
            f'SECRET = "{secret}"\n'
        )
        repo = self.make_repo()

        report = self.report(repo)

        self.assertNotIn(secret, json.dumps(report, sort_keys=True))
        self.assertNotIn("runtimeConfig", report)

    def test_methodology_provenance_matches_all_vendored_resources(self):
        provenance = load_dependency_provenance(PLUGIN_ROOT)
        methodology = provenance["methodology"]
        vendor_root = PLUGIN_ROOT / "vendor" / "mattpocock-skills"

        self.assertEqual(provenance["schemaVersion"], 3)
        self.assertEqual(methodology["repository"], "mattpocock/skills")
        self.assertEqual(methodology["ref"], "v1.1.0")
        self.assertEqual(
            methodology["installCommand"],
            [
                "npx",
                "-y",
                "skills@1.5.20",
                "add",
                "https://github.com/mattpocock/skills/tree/v1.1.0",
                "--skill",
                "grilling",
                "--skill",
                "tdd",
                "--skill",
                "diagnosing-bugs",
                "--skill",
                "code-review",
                "--skill",
                "codebase-design",
                "--skill",
                "domain-modeling",
                "--agent",
                "codex",
                "--yes",
            ],
        )
        self.assertEqual(
            methodology["runtimeRequirements"],
            {"node": ">=22.20.0"},
        )
        self.assertEqual(
            list(methodology["skillHashes"]),
            [
                "grilling",
                "tdd",
                "diagnosing-bugs",
                "code-review",
                "codebase-design",
                "domain-modeling",
            ],
        )
        actual_files = {
            path.relative_to(vendor_root).as_posix()
            for path in vendor_root.rglob("*")
            if path.is_file()
        }
        license_relative = (
            Path(methodology["licensePath"])
            .relative_to("vendor/mattpocock-skills")
            .as_posix()
        )
        self.assertEqual(
            actual_files,
            set(methodology["fileHashes"]) | {license_relative},
        )
        for relative, expected in methodology["fileHashes"].items():
            digest = hashlib.sha256((vendor_root / relative).read_bytes()).hexdigest()
            self.assertEqual(digest, expected, relative)
        license_digest = hashlib.sha256(
            (PLUGIN_ROOT / methodology["licensePath"]).read_bytes()
        ).hexdigest()
        self.assertEqual(license_digest, methodology["licenseSha256"])
        adaptations = {item["path"]: item for item in methodology["projectAdaptations"]}
        self.assertEqual(
            set(adaptations),
            {"code-review/SKILL.md", "diagnosing-bugs/SKILL.md"},
        )
        self.assertEqual(
            adaptations["code-review/SKILL.md"]["sha256"],
            "91a53d4f185d2610c0bb5284348ef71d00519d9d070ccf3929b09ea37b6df222",
        )

    def test_dependency_cli_exposes_static_capability_routing(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "check_dependencies.py"), "--help"],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--capability", result.stdout)
        self.assertIn("test-first-execution", result.stdout)
        self.assertIn("Require one routed capability", result.stdout)

    def test_dependency_cli_blocks_missing_openspec_project_setup(self):
        repo = self.make_repo(openspec=False)

        result = self.run_dependency_cli(repo, "--json")

        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        failure = next(
            item
            for item in report["checks"]
            if item["name"] == "project openspec setup active"
        )
        self.assertTrue(failure["required"])
        self.assertFalse(failure["ok"])

    def test_openspec_config_without_six_official_project_skills_is_not_ready(self):
        repo = self.make_repo(project_skills=False)

        report = self.report(repo)

        setup = next(
            item for item in report["checks"]
            if item["name"] == "project openspec setup active"
        )
        self.assertFalse(report["ok"], report)
        self.assertFalse(setup["ok"], setup)
        self.assertEqual(setup["path_kind"], "official_repo_skill_path")
        self.assertTrue(setup["skill_mismatches"], setup)

    def test_missing_or_drifted_official_openspec_skill_blocks_readiness(self):
        for mutation in ("missing", "wrong-version", "extra-symlink"):
            with self.subTest(mutation=mutation):
                repo = self.make_repo()
                skill_file = (
                    repo / ".agents" / "skills" / "openspec-archive-change" / "SKILL.md"
                )
                if mutation == "missing":
                    skill_file.unlink()
                elif mutation == "wrong-version":
                    skill_file.write_text(skill_file.read_text().replace("1.7.0", "1.6.0"))
                else:
                    outside = self.root / f"openspec-outside-{self.repo_counter}"
                    outside.mkdir()
                    (skill_file.parent / "extra-link").symlink_to(
                        outside,
                        target_is_directory=True,
                    )

                report = self.report(repo)
                setup = next(
                    item for item in report["checks"]
                    if item["name"] == "project openspec setup active"
                )

                self.assertFalse(report["ok"], report)
                self.assertFalse(setup["ok"], setup)
                self.assertEqual(setup["skill_status"], "contract_mismatch")

    def test_invalid_utf8_openspec_skill_fails_closed_without_crashing(self):
        repo = self.make_repo()
        skill_file = repo / ".agents" / "skills" / "openspec-propose" / "SKILL.md"
        skill_file.write_bytes(b"\xff\xfe")

        report = self.report(repo)
        setup = next(
            item for item in report["checks"]
            if item["name"] == "project openspec setup active"
        )

        self.assertFalse(report["ok"], report)
        self.assertFalse(setup["ok"], setup)
        self.assertEqual(setup["skill_status"], "contract_mismatch")

    def test_legacy_openspec_skills_do_not_satisfy_official_readiness(self):
        repo = self.make_repo(project_skills=False)
        for skill in OPENSPEC_WORKFLOW_SKILLS:
            path = repo / ".codex" / "skills" / skill / "SKILL.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"---\nname: {skill}\n---\n")

        report = self.report(repo)
        setup = next(
            item for item in report["checks"]
            if item["name"] == "project openspec setup active"
        )

        self.assertFalse(setup["ok"], setup)
        self.assertFalse(report["workflowReady"], report)

    def test_dependency_cli_blocks_a_missing_triggered_matt_skill(self):
        repo = self.make_repo()

        result = self.run_dependency_cli(
            repo,
            "--capability",
            "test-first-execution",
            "--json",
        )

        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report["capabilities"]["test-first-execution"]["ready"])
        self.assertEqual(report["methodology"]["missingSkills"], ["tdd"])

    def test_activation_dry_run_plans_openspec_and_matt_without_project_writes(self):
        repo = self.make_repo(openspec=False, project_skills=False)
        before = self.tree_snapshot(repo)

        report = activate_project_dependencies(
            repo,
            dry_run=True,
            plugin_root=PLUGIN_ROOT,
            codex_home=self.codex_home,
            triggered_capabilities={"test-first-execution"},
        )

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["status"], "planned")
        self.assertFalse(report["writes_blocked"])
        self.assertEqual(before, self.tree_snapshot(repo))
        self.assertEqual(report["commands"][0]["kind"], "isolated-skill-generation")
        self.assertIn("openspec", report["commands"][0]["command"])
        matt = next(
            item
            for item in report["local_skills"]["items"]
            if item["skill"] == "tdd"
        )
        self.assertEqual(matt["status"], "would-copy")

    def test_activation_apply_without_authorization_is_default_deny(self):
        repo = self.make_repo(openspec=False, project_skills=False)
        before = self.tree_snapshot(repo)

        report = activate_project_dependencies(
            repo,
            dry_run=False,
            skip_official_installs=True,
            plugin_root=PLUGIN_ROOT,
            codex_home=self.codex_home,
            authorizations=set(),
            triggered_capabilities={"test-first-execution"},
        )

        self.assertFalse(report["ok"])
        self.assertTrue(report["writes_blocked"])
        self.assertEqual(
            report["side_effects"]["dependency.install_update"]["reason"],
            "authorization_missing",
        )
        self.assertEqual(before, self.tree_snapshot(repo))

    def test_activation_library_default_does_not_imply_write_authorization(self):
        repo = self.make_repo(openspec=False, project_skills=False)
        before = self.tree_snapshot(repo)

        report = activate_project_dependencies(
            repo,
            skip_official_installs=True,
            plugin_root=PLUGIN_ROOT,
            codex_home=self.codex_home,
            triggered_capabilities={"test-first-execution"},
        )

        self.assertFalse(report["ok"])
        self.assertTrue(report["writes_blocked"])
        self.assertEqual(before, self.tree_snapshot(repo))

    def test_openspec_updater_dry_run_uses_pinned_provenance_without_commands(self):
        fake_home = self.root / "user-home"
        fake_home.mkdir()
        with (
            mock.patch.object(Path, "home", return_value=fake_home),
            mock.patch.object(
                auto_update,
                "executable_exists",
                side_effect=lambda name: name == "openspec",
            ),
            mock.patch.object(
                auto_update,
                "installed_openspec_version",
                return_value="1.6.0",
            ),
            mock.patch.object(auto_update, "npm_latest_version", return_value="1.7.0"),
            mock.patch.object(
                auto_update,
                "run_command",
                side_effect=AssertionError("unexpected command"),
            ),
        ):
            results = auto_update.run_external_updaters(self.codex_home, apply=False)

        openspec = next(item for item in results if item["name"] == "openspec-cli")
        self.assertEqual(openspec["status"], "update-available")
        self.assertEqual(openspec["current"], "1.6.0")
        self.assertEqual(openspec["expectedVersion"], "1.7.0")
        self.assertEqual(
            openspec["recommendedCommand"],
            ["npm", "install", "-g", "@fission-ai/openspec@1.7.0"],
        )

    def test_external_updater_apply_without_authorization_stops_before_commands(self):
        with mock.patch.object(
            auto_update,
            "run_command",
            side_effect=AssertionError("unauthorized command"),
        ):
            results = auto_update.run_external_updaters(
                self.codex_home,
                apply=True,
                authorizations=set(),
            )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "authorization-required")
        self.assertFalse(results[0]["sideEffect"]["authorized"])
        self.assertEqual(auto_update.updater_exit_code(results, apply=True), 1)

    def test_external_updater_library_default_does_not_imply_authorization(self):
        with mock.patch.object(
            auto_update,
            "run_command",
            side_effect=AssertionError("unauthorized command"),
        ):
            results = auto_update.run_external_updaters(
                self.codex_home,
                apply=True,
            )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "authorization-required")

    def test_authorized_openspec_update_uses_pinned_command_and_verifies_result(self):
        fake_home = self.root / "authorized-user-home"
        fake_home.mkdir()
        command_result = {
            "ok": True,
            "returncode": 0,
            "stdout": "updated\n",
            "stderr": "",
        }
        with (
            mock.patch.object(Path, "home", return_value=fake_home),
            mock.patch.object(
                auto_update,
                "executable_exists",
                side_effect=lambda name: name in {"openspec", "npm"},
            ),
            mock.patch.object(
                auto_update,
                "installed_openspec_version",
                side_effect=["1.6.0", "1.7.0"],
            ),
            mock.patch.object(auto_update, "run_command", return_value=command_result) as run,
        ):
            results = auto_update.run_external_updaters(
                self.codex_home,
                apply=True,
                authorizations={"explicit_named_dependency_request"},
            )

        openspec = next(item for item in results if item["name"] == "openspec-cli")
        self.assertEqual(openspec["status"], "updated-or-unchanged")
        self.assertEqual(openspec["before"], "1.6.0")
        self.assertEqual(openspec["after"], "1.7.0")
        run.assert_called_once_with(
            ["npm", "install", "-g", "@fission-ai/openspec@1.7.0"],
            timeout=600,
        )


if __name__ == "__main__":
    unittest.main()
