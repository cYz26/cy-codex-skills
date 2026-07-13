import importlib
import importlib.util
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

TEST_ROOT = Path(__file__).resolve().parent
PLUGIN_ROOT = TEST_ROOT.parent
sys.path.insert(0, str(TEST_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from dependency_support import DependencyFixtureMixin
from workflow_dependency_catalog import PROJECT_ORCHESTRATOR_SKILLS
from workflow_mode_routing import read_workflow_mode_config, route_workflow_mode
from workflow_dependencies import dependency_report
from workflow_project_activation import activate_project_dependencies
from workflow_project_skill_install import ensure_project_local_skills
import codex_auto_update_plugins_skills as auto_update


MATT_ALLOWED = [
    "grilling",
    "tdd",
    "diagnosing-bugs",
    "code-review",
    "codebase-design",
    "domain-modeling",
]


class ProviderProfileTests(DependencyFixtureMixin, unittest.TestCase):
    def make_project_repo(self, **kwargs):
        repo = super().make_project_repo(**kwargs)
        if kwargs.get("enable_orchestrator", True):
            for skill in PROJECT_ORCHESTRATOR_SKILLS:
                source = PLUGIN_ROOT / "skills" / skill / "SKILL.md"
                target = repo / ".agents" / "skills" / skill / "SKILL.md"
                target.write_bytes(source.read_bytes())
        return repo

    def provider_module(self):
        spec = importlib.util.find_spec("workflow_provider_profiles")
        self.assertIsNotNone(spec, "provider facade module must exist")
        return importlib.import_module("workflow_provider_profiles")

    def dependency_report_with_fake_path(self, codex_home, repo, *, strict=False):
        binary_dir = Path(tempfile.mkdtemp(prefix="devflow-provider-bin-"))
        for name, body in {
            "codex": "#!/bin/sh\nprintf 'codex fixture\\n'\n",
            "openspec": "#!/bin/sh\nprintf '1.5.0\\n'\n",
        }.items():
            path = binary_dir / name
            path.write_text(body)
            path.chmod(0o755)
        with mock.patch.dict(os.environ, {"PATH": f"{binary_dir}{os.pathsep}{os.environ.get('PATH', '')}"}):
            return dependency_report(
                PLUGIN_ROOT,
                codex_home,
                codex_home / "config.toml",
                strict,
                repo,
            )

    def write_matching_matt_lock(self, repo):
        root = repo / ".agents" / "skills"
        hashes = {
            skill: hashlib.sha256((root / skill / "SKILL.md").read_bytes()).hexdigest()
            for skill in MATT_ALLOWED
        }
        return self.write_provider_lock(
            repo,
            {
                "mattpocock-skills": {
                    "repository": "mattpocock/skills",
                    "ref": "v1.1.0",
                    "commit": "d574778f94cf620fcc8ce741584093bc650a61d3",
                    "sourceRoot": str(root.resolve()),
                    "skillHashes": hashes,
                }
            },
        )

    def write_project_matt_skills(self, repo, skills=MATT_ALLOWED):
        root = repo / ".agents" / "skills"
        for skill in skills:
            source = (
                PLUGIN_ROOT
                / "fixtures"
                / "provider-profiles"
                / "lean-matt"
                / ".agents"
                / "skills"
                / skill
            )
            shutil.copytree(source, root / skill, dirs_exist_ok=True)
        return root

    def test_registry_declares_profiles_capabilities_and_side_effect_policy(self):
        module = self.provider_module()

        registry = module.load_provider_registry(PLUGIN_ROOT)

        self.assertEqual(set(registry["methodologyProfiles"]), {"core", "lean-matt", "strict-superpowers"})
        self.assertEqual(set(registry["roadmapProviders"]), {"none", "gsd"})
        self.assertEqual(len(registry["capabilities"]), 10)
        self.assertEqual(len(registry["sideEffects"]), 13)
        self.assertTrue(registry["defaultDeny"])

    def test_side_effect_policy_is_executable_and_default_deny(self):
        registry_module = importlib.import_module("workflow_provider_registry")

        readable = registry_module.side_effect_decision(PLUGIN_ROOT, "workspace.read", {"task_scope"})
        install = registry_module.side_effect_decision(PLUGIN_ROOT, "dependency.install_update", set())
        canonical = registry_module.side_effect_decision(
            PLUGIN_ROOT,
            "canonical.write",
            {"approved_promoter_write_set"},
        )
        release = registry_module.side_effect_decision(PLUGIN_ROOT, "archive_release", set())
        unknown = registry_module.side_effect_decision(PLUGIN_ROOT, "unknown.effect", {"task_scope"})

        self.assertTrue(readable["authorized"])
        self.assertFalse(install["authorized"])
        self.assertEqual(install["denial"], "dry_run_only")
        self.assertTrue(canonical["authorized"])
        self.assertFalse(release["authorized"])
        self.assertEqual(release["denial"], "ready_not_applied")
        self.assertFalse(unknown["authorized"])
        self.assertEqual(unknown["reason"], "unknown_effect_default_denied")

    def test_workflow_config_reads_canonical_provider_keys_and_aliases(self):
        canonical_repo = Path(tempfile.mkdtemp(prefix="devflow-provider-config-"))
        self.write_provider_config(
            canonical_repo,
            methodology_profile="lean-matt",
            roadmap_provider="gsd",
            provider_selectors={"gsd": {"version": "1.6.1"}},
            roadmap_bindings={"change-a": {"phase_id": "02"}},
        )
        alias_repo = Path(tempfile.mkdtemp(prefix="devflow-provider-alias-"))
        (alias_repo / ".dev-flow.json").write_text(
            json.dumps(
                {
                    "workflow": {
                        "methodologyProfile": "strict-superpowers",
                        "roadmapProvider": "none",
                        "providerSelectors": {"superpowers": {"sourceChannel": "curated"}},
                        "roadmapBindings": {},
                    }
                }
            )
        )

        canonical = read_workflow_mode_config(canonical_repo)
        alias = read_workflow_mode_config(alias_repo)

        self.assertEqual(canonical.get("methodology_profile"), "lean-matt")
        self.assertEqual(canonical.get("roadmap_provider"), "gsd")
        self.assertEqual(canonical.get("provider_selectors", {}).get("gsd", {}).get("version"), "1.6.1")
        self.assertIn("change-a", canonical.get("roadmap_bindings", {}))
        self.assertEqual(alias.get("methodology_profile"), "strict-superpowers")
        self.assertEqual(alias.get("roadmap_provider"), "none")
        self.assertEqual(
            alias.get("provider_selectors", {}).get("superpowers", {}).get("sourceChannel"),
            "curated",
        )

    def test_malformed_workflow_config_is_explicitly_invalid_and_never_defaults_silently(self):
        repo = Path(tempfile.mkdtemp(prefix="devflow-provider-invalid-config-"))
        (repo / ".dev-flow.json").write_text('{"workflow": ')

        config = read_workflow_mode_config(repo)

        self.assertFalse(config["valid"])
        self.assertTrue(config["config_errors"])
        self.assertEqual(config["methodology_profile"], "core")
        self.assertEqual(config["roadmap_provider"], "none")

    def test_structurally_invalid_provider_config_fails_closed_in_both_readers(self):
        module = self.provider_module()
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        invalid_payloads = {
            "workflow-not-object": {"workflow": []},
            "unknown-methodology": {"workflow": {"methodology_profile": "fast-and-loose"}},
            "unknown-roadmap": {"workflow": {"roadmap_provider": "spreadsheet"}},
            "selectors-not-object": {"workflow": {"provider_selectors": []}},
            "bindings-not-object": {"workflow": {"roadmap_bindings": "phase-1"}},
        }

        for label, payload in invalid_payloads.items():
            with self.subTest(label=label):
                repo = Path(tempfile.mkdtemp(prefix=f"devflow-invalid-{label}-"))
                (repo / ".dev-flow.json").write_text(json.dumps(payload))

                config = read_workflow_mode_config(repo)
                selection = module.resolve_provider_selection(repo, home, {})
                route = route_workflow_mode(repo, kind="docs-only", openspec_ready=True)

                self.assertFalse(config["valid"], config)
                self.assertTrue(selection["configErrors"], selection)
                self.assertEqual(route["mode"], "blocked", route)
                self.assertFalse(route["execution_allowed"], route)

    def test_core_none_is_ready_without_external_providers(self):
        module = self.provider_module()
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="core",
            roadmap_provider="none",
        )

        selection = module.resolve_provider_selection(repo, home, {})
        report = module.diagnose_provider_selection(selection, repo, home)

        self.assertEqual(selection["effectiveMethodologyProfile"], "core")
        self.assertEqual(selection["effectiveRoadmapProvider"], "none")
        self.assertTrue(report["coreReady"], report)
        self.assertTrue(report["methodologyReady"], report)
        self.assertTrue(report["roadmapReady"], report)
        self.assertEqual(report["blockingReasons"], [])
        self.assertEqual(report["selectedProviders"], [])

    def test_selected_lean_matt_rejects_global_only_pack(self):
        module = self.provider_module()
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        self.write_standalone_skills(home, MATT_ALLOWED)
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="lean-matt",
            roadmap_provider="none",
        )

        report = module.diagnose_provider_selection(
            module.resolve_provider_selection(repo, home, {}), repo, home
        )

        matt = report["providers"]["mattpocock-skills"]
        self.assertFalse(report["methodologyReady"], report)
        self.assertEqual(matt["status"], "missing_capabilities")
        self.assertEqual(matt["root"], str((repo / ".agents" / "skills").resolve()))
        self.assertTrue(matt["globalPackPresent"])
        self.assertEqual(matt["globalRoot"], str((home / "skills").resolve()))

    def test_project_local_matt_pack_satisfies_selected_lean_profile(self):
        module = self.provider_module()
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="lean-matt",
            roadmap_provider="none",
        )
        project_root = self.write_project_matt_skills(repo)

        report = module.diagnose_provider_selection(
            module.resolve_provider_selection(repo, home, {}), repo, home
        )

        matt = report["providers"]["mattpocock-skills"]
        self.assertTrue(report["methodologyReady"], report)
        self.assertEqual(matt["status"], "ready")
        self.assertEqual(matt["root"], str(project_root.resolve()))
        self.assertFalse(matt["globalPackPresent"])

    def test_selected_lean_matt_rejects_project_links_that_escape_to_global_pack(self):
        module = self.provider_module()
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        self.write_standalone_skills(home, MATT_ALLOWED)
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="lean-matt",
            roadmap_provider="none",
        )
        root = repo / ".agents" / "skills"
        for skill in MATT_ALLOWED:
            (root / skill).symlink_to(home / "skills" / skill, target_is_directory=True)

        report = module.diagnose_provider_selection(
            module.resolve_provider_selection(repo, home, {}), repo, home
        )

        matt = report["providers"]["mattpocock-skills"]
        self.assertFalse(report["methodologyReady"], report)
        self.assertEqual(matt["status"], "nonlocal_skill_route")
        self.assertEqual(set(matt["nonLocalSkills"]), set(MATT_ALLOWED))

    def test_selected_lean_matt_rejects_symlinked_project_skill_root(self):
        module = self.provider_module()
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        self.write_standalone_skills(home, MATT_ALLOWED)
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="lean-matt",
            roadmap_provider="none",
        )
        root = repo / ".agents" / "skills"
        shutil.rmtree(root)
        root.symlink_to(home / "skills", target_is_directory=True)

        report = module.diagnose_provider_selection(
            module.resolve_provider_selection(repo, home, {}), repo, home
        )

        matt = report["providers"]["mattpocock-skills"]
        self.assertFalse(report["methodologyReady"], report)
        self.assertEqual(matt["root"], str(repo.resolve() / ".agents" / "skills"))
        self.assertEqual(matt["status"], "nonlocal_skill_route")
        self.assertEqual(set(matt["nonLocalSkills"]), set(MATT_ALLOWED))

    def test_lean_matt_nonlocal_route_never_plans_or_runs_installer(self):
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        self.write_standalone_skills(home, MATT_ALLOWED)
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="lean-matt",
            roadmap_provider="none",
            provider_selectors={
                "mattpocock-skills": {"source_id": "mattpocock-skills-v1-1-0"}
            },
        )
        root = repo / ".agents" / "skills"
        shutil.rmtree(root)
        root.symlink_to(home / "skills", target_is_directory=True)

        report = activate_project_dependencies(
            repo,
            dry_run=True,
            plugin_root=PLUGIN_ROOT,
            codex_home=home,
        )

        self.assertEqual(
            report["providers"]["mattpocock-skills"]["status"],
            "nonlocal_skill_route",
        )
        self.assertFalse(
            any("skills@1.5.9" in item["command"] for item in report["commands"]),
            report["commands"],
        )

    def test_project_skill_install_uses_diagnosed_project_local_matt_root(self):
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="lean-matt",
            roadmap_provider="none",
        )
        project_root = self.write_project_matt_skills(repo)
        expected_hashes = {
            skill: hashlib.sha256((project_root / skill / "SKILL.md").read_bytes()).hexdigest()
            for skill in MATT_ALLOWED
        }

        report = ensure_project_local_skills(
            repo,
            PLUGIN_ROOT,
            home,
            dry_run=True,
            selection={"effectiveMethodologyProfile": "lean-matt"},
            provider_diagnosis={
                "providers": {
                    "mattpocock-skills": {
                        "root": str(project_root),
                        "implicitSkills": MATT_ALLOWED,
                        "expectedSkillHashes": expected_hashes,
                    }
                }
            },
        )

        items = [item for item in report["items"] if item["provider"] == "mattpocock-skills"]
        self.assertEqual(len(items), len(MATT_ALLOWED))
        self.assertTrue(all(item["status"] == "already-present" for item in items), items)
        self.assertTrue(all(Path(item["source"]).is_relative_to(project_root) for item in items), items)

    def test_standalone_superpowers_governance_uses_manifest_declared_hooks(self):
        plugin_checks = importlib.import_module("workflow_dependency_plugin_checks")
        home = self.make_codex_home(
            enable_plugin_eval=False,
            superpowers_version="6.1.1",
            superpowers_channel="openai-curated-remote",
        )

        report = plugin_checks.superpowers_governance_report(home, strict=True)
        checks = []
        plugin_checks.add_superpowers_governance_checks(checks, home, strict=True)

        self.assertEqual(report["recommendedVersion"], "6.1.1")
        self.assertEqual(report["strictProfileRequires"], "5.1.3")
        self.assertEqual(report["status"], "superpowers_ok")
        self.assertFalse(report["sessionStartHookDeclared"])
        self.assertFalse(any("session-start hook" in item["name"] for item in checks), checks)

    def test_no_repo_dependency_check_treats_absent_superpowers_as_unselected(self):
        home = self.make_codex_home(
            enable_plugin_eval=False,
            install_superpowers=False,
        )

        report = self.dependency_report_with_fake_path(home, None)

        self.assertIsNone(report["selection"])
        self.assertEqual(report["superpowers"]["status"], "absent_unselected")
        self.assertEqual(report["superpowers"]["compatibility"], "unselected")
        self.assertEqual(report["superpowers"]["nextAction"], "")

    def test_no_repo_dependency_check_treats_present_superpowers_as_unselected(self):
        home = self.make_codex_home(
            enable_plugin_eval=False,
            superpowers_version="6.1.1",
            superpowers_channel="openai-curated-remote",
        )

        report = self.dependency_report_with_fake_path(home, None)

        self.assertIsNone(report["selection"])
        self.assertEqual(report["superpowers"]["status"], "available_unselected")
        self.assertEqual(report["superpowers"]["compatibility"], "unselected")
        self.assertEqual(report["superpowers"]["nextAction"], "")

    def test_standalone_superpowers_governance_never_mixes_skill_roots(self):
        plugin_checks = importlib.import_module("workflow_dependency_plugin_checks")
        home = self.make_codex_home(
            enable_plugin_eval=False,
            superpowers_version="6.0.3",
            superpowers_channel="superpowers-upstream-v6-0-3",
        )
        for skill in [
            "using-superpowers",
            "brainstorming",
            "test-driven-development",
            "verification-before-completion",
        ]:
            self.write_skill(home, "superpowers", skill, channel="openai-curated-remote")
        current_root = self.write_plugin_manifest(
            home,
            "superpowers",
            version="6.1.1",
            channel="openai-curated-remote",
        )

        report = plugin_checks.superpowers_governance_report(home, strict=True)

        self.assertEqual(report["pluginRoot"], str(current_root))
        self.assertFalse(report["requiredSkills"]["writing-plans"])
        self.assertEqual(report["status"], "superpowers_unsupported")

    def test_core_readiness_requires_hash_matched_project_devflow_skills(self):
        module = self.provider_module()
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="core",
            roadmap_provider="none",
        )
        target = repo / ".agents" / "skills" / "project-orchestrator" / "SKILL.md"
        target.write_text("---\nname: project-orchestrator\ndescription: foreign source\n---\n")

        report = module.diagnose_provider_selection(
            module.resolve_provider_selection(repo, home, {}), repo, home
        )

        self.assertFalse(report["coreReady"], report)
        self.assertFalse(report["ok"], report)
        self.assertEqual(
            report["coreProjectSkills"]["skills"]["project-orchestrator"]["status"],
            "source_conflict",
        )

    def test_core_activation_dry_run_plans_missing_skills_without_claiming_current_readiness(self):
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = self.make_project_repo(
            enable_orchestrator=False,
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="core",
            roadmap_provider="none",
        )

        report = activate_project_dependencies(
            repo,
            dry_run=True,
            skip_official_installs=True,
            plugin_root=PLUGIN_ROOT,
            codex_home=home,
        )

        self.assertTrue(report["ok"], report)
        self.assertFalse(report["coreReady"], report)
        core_items = [item for item in report["local_skills"]["items"] if item["provider"] == "dev-flow"]
        self.assertTrue(core_items)
        self.assertTrue(all(item["status"] == "would-link" for item in core_items), core_items)

    def test_dependency_report_core_none_ignores_absent_external_providers(self):
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="core",
            roadmap_provider="none",
        )

        report = self.dependency_report_with_fake_path(home, repo)

        self.assertTrue(report["ok"], report)
        self.assertTrue(report["coreReady"])
        self.assertTrue(report["methodologyReady"])
        self.assertTrue(report["roadmapReady"])
        required_failures = [item["name"] for item in report["checks"] if item["required"] and not item["ok"]]
        self.assertFalse(any("superpowers" in name or "gsd" in name for name in required_failures))

    def test_unconfigured_legacy_superpowers_links_require_one_authoritative_source(self):
        module = self.provider_module()
        home = self.make_codex_home(
            superpowers_version="6.1.1", superpowers_channel="openai-curated-remote"
        )
        self.write_standalone_skills(home, MATT_ALLOWED)
        repo = Path(tempfile.mkdtemp(prefix="devflow-legacy-profile-"))
        (repo / "openspec").mkdir()
        (repo / "openspec" / "config.yaml").write_text("schema: spec-driven\n")
        source = home / "plugins" / "cache" / "openai-curated-remote" / "superpowers" / "local"
        skill_root = repo / ".agents" / "skills"
        skill_root.mkdir(parents=True)
        for skill in ["brainstorming", "writing-plans", "test-driven-development"]:
            (skill_root / skill).symlink_to(source / "skills" / skill, target_is_directory=True)

        selection = module.resolve_provider_selection(repo, home, {})

        self.assertEqual(selection["effectiveMethodologyProfile"], "strict-superpowers")
        self.assertEqual(selection["selectionSource"], "legacy_profile_inferred")
        self.assertEqual(selection["inferenceConfidence"]["methodology"], "high")
        self.assertEqual(selection["configErrors"], [])

    def test_unconfigured_same_named_skill_links_do_not_infer_untrusted_superpowers(self):
        module = self.provider_module()
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = Path(tempfile.mkdtemp(prefix="devflow-untrusted-profile-"))
        (repo / "openspec").mkdir()
        (repo / "openspec" / "config.yaml").write_text("schema: spec-driven\n")
        source = Path(tempfile.mkdtemp(prefix="untrusted-superpowers-"))
        skill_root = repo / ".agents" / "skills"
        skill_root.mkdir(parents=True)
        for skill in ["brainstorming", "writing-plans", "test-driven-development"]:
            skill_file = source / "skills" / skill / "SKILL.md"
            skill_file.parent.mkdir(parents=True)
            skill_file.write_text(self.skill_fixture_text(skill))
            (skill_root / skill).symlink_to(skill_file.parent, target_is_directory=True)

        selection = module.resolve_provider_selection(repo, home, {})

        self.assertEqual(selection["effectiveMethodologyProfile"], "core")
        self.assertEqual(selection["selectionSource"], "legacy_inference_conflict")
        self.assertEqual(selection["inferenceConfidence"]["methodology"], "unverified")
        self.assertTrue(selection["configErrors"], selection)

    def test_strict_cli_flag_does_not_change_core_methodology_selection(self):
        home = self.make_codex_home(enable_plugin_eval=True, install_superpowers=False)
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="core",
            roadmap_provider="none",
        )

        report = self.dependency_report_with_fake_path(home, repo, strict=True)

        self.assertEqual(report.get("selection", {}).get("effectiveMethodologyProfile"), "core")
        self.assertTrue(report["methodologyReady"], report)

    def test_dependency_cli_methodology_and_source_overrides_are_read_only(self):
        home = self.make_codex_home(
            superpowers_version="6.1.1",
            superpowers_channel="openai-curated-remote",
        )
        repo = self.make_project_repo(
            enable_superpowers=True,
            methodology_profile="core",
            roadmap_provider="none",
            provider_selectors={},
        )
        config_path = repo / ".dev-flow.json"
        before = config_path.read_text()
        binary_dir = Path(tempfile.mkdtemp(prefix="devflow-provider-cli-bin-"))
        for name in ("codex", "openspec"):
            path = binary_dir / name
            output = "1.5.0" if name == "openspec" else "codex fixture"
            path.write_text(f"#!/bin/sh\nprintf '{output}\\n'\n")
            path.chmod(0o755)
        command = [
            sys.executable,
            str(PLUGIN_ROOT / "scripts" / "check_dependencies.py"),
            "--plugin-root",
            str(PLUGIN_ROOT),
            "--repo",
            str(repo),
            "--codex-home",
            str(home),
            "--methodology-profile",
            "strict-superpowers",
            "--roadmap-provider",
            "none",
            "--provider-source",
            "superpowers=superpowers-openai-curated-remote",
            "--json",
        ]

        with mock.patch.dict(
            os.environ,
            {"PATH": f"{binary_dir}{os.pathsep}{os.environ.get('PATH', '')}"},
        ):
            result = subprocess.run(command, text=True, capture_output=True, check=False)

        self.assertEqual(result.returncode, 0, f"{result.stderr}\n{result.stdout}")
        report = json.loads(result.stdout)
        self.assertEqual(report["selection"]["effectiveMethodologyProfile"], "strict-superpowers")
        self.assertEqual(report["selection"]["effectiveRoadmapProvider"], "none")
        self.assertEqual(
            report["selection"]["providerSourceOverrides"]["superpowers"],
            "superpowers-openai-curated-remote",
        )
        self.assertEqual(config_path.read_text(), before)
        self.assertFalse((repo / ".planning" / "devflow" / "providers.lock.json").exists())
        self.assertTrue(any(item["name"] == "developer plugin enabled: plugin-eval" for item in report["checks"]))

    def test_strict_methodology_does_not_select_or_require_gsd(self):
        module = self.provider_module()
        home = self.make_codex_home(
            superpowers_version="6.1.1", superpowers_channel="openai-curated-remote"
        )
        repo = self.make_project_repo(
            enable_gsd=False,
            methodology_profile="strict-superpowers",
            roadmap_provider="none",
            provider_selectors={
                "superpowers": {
                    "kind": "codex-plugin",
                    "plugin_id": "superpowers",
                    "source_channel": "openai-curated-remote",
                    "version": "6.1.1",
                }
            },
        )

        report = module.diagnose_provider_selection(
            module.resolve_provider_selection(repo, home, {}), repo, home
        )

        self.assertTrue(report["methodologyReady"], report)
        self.assertTrue(report["roadmapReady"], report)
        self.assertNotIn("gsd", report["selectedProviders"])
        self.assertFalse(any("gsd" in item.lower() for item in report["blockingReasons"]))

    def test_hookless_selected_superpowers_manifest_is_valid(self):
        module = self.provider_module()
        home = self.make_codex_home(
            superpowers_version="6.1.1", superpowers_channel="openai-curated-remote"
        )
        repo = self.make_project_repo(
            enable_gsd=False,
            methodology_profile="strict-superpowers",
            roadmap_provider="none",
            provider_selectors={
                "superpowers": {
                    "kind": "codex-plugin",
                    "plugin_id": "superpowers",
                    "source_channel": "openai-curated-remote",
                    "version": "6.1.1",
                }
            },
        )

        report = module.diagnose_provider_selection(
            module.resolve_provider_selection(repo, home, {}), repo, home
        )

        strict = report["providers"]["superpowers"]
        self.assertEqual(strict["status"], "ready")
        self.assertFalse(strict["hookDeclared"])
        self.assertTrue(report["methodologyReady"], report)

    def test_hook_injection_into_authoritative_hookless_source_blocks_strict_methodology(self):
        module = self.provider_module()
        home = self.make_codex_home(
            superpowers_version="6.1.1",
            superpowers_channel="openai-curated-remote",
            superpowers_hooks="hooks/hooks-codex.json",
        )
        repo = self.make_project_repo(
            enable_gsd=False,
            methodology_profile="strict-superpowers",
            roadmap_provider="none",
            provider_selectors={
                "superpowers": {
                    "kind": "codex-plugin",
                    "plugin_id": "superpowers",
                    "source_channel": "openai-curated-remote",
                    "version": "6.1.1",
                }
            },
        )

        report = module.diagnose_provider_selection(
            module.resolve_provider_selection(repo, home, {}), repo, home
        )

        self.assertTrue(report["coreReady"], report)
        self.assertFalse(report["methodologyReady"], report)
        self.assertTrue(report["roadmapReady"], report)
        self.assertEqual(report["providers"]["superpowers"]["status"], "source_drift")

    def test_multiple_unbound_superpowers_sources_are_ambiguous(self):
        module = self.provider_module()
        home = self.make_codex_home(
            superpowers_version="6.0.3", superpowers_channel="superpowers-upstream-v6-0-3"
        )
        for skill in [
            "using-superpowers",
            "brainstorming",
            "writing-plans",
            "test-driven-development",
            "verification-before-completion",
            "systematic-debugging",
            "requesting-code-review",
        ]:
            self.write_skill(home, "superpowers", skill, channel="openai-curated-remote")
        self.write_plugin_manifest(
            home,
            "superpowers",
            version="6.1.1",
            channel="openai-curated-remote",
        )
        repo = self.make_project_repo(
            enable_gsd=False,
            methodology_profile="strict-superpowers",
            roadmap_provider="none",
            provider_selectors={},
        )

        report = module.diagnose_provider_selection(
            module.resolve_provider_selection(repo, home, {}), repo, home
        )

        self.assertFalse(report["methodologyReady"], report)
        self.assertEqual(report["providers"]["superpowers"]["status"], "ambiguous_source")
        self.assertEqual(len(report["providers"]["superpowers"]["candidates"]), 2)

    def test_matching_provider_lock_binds_one_superpowers_source(self):
        module = self.provider_module()
        home = self.make_codex_home(
            superpowers_version="6.0.3", superpowers_channel="superpowers-upstream-v6-0-3"
        )
        for skill in [
            "using-superpowers",
            "brainstorming",
            "writing-plans",
            "test-driven-development",
            "systematic-debugging",
            "requesting-code-review",
            "verification-before-completion",
            "receiving-code-review",
            "executing-plans",
            "subagent-driven-development",
            "using-git-worktrees",
            "finishing-a-development-branch",
        ]:
            self.write_skill(home, "superpowers", skill, channel="openai-curated-remote")
        source_b = self.write_plugin_manifest(
            home, "superpowers", version="6.1.1", channel="openai-curated-remote"
        )
        digest = hashlib.sha256((source_b / ".codex-plugin" / "plugin.json").read_bytes()).hexdigest()
        repo = self.make_project_repo(
            enable_gsd=False,
            methodology_profile="strict-superpowers",
            roadmap_provider="none",
            provider_selectors={},
        )
        self.write_provider_lock(
            repo,
            {
                "superpowers": {
                    "sourceChannel": "openai-curated-remote",
                    "version": "6.1.1",
                    "manifestDigest": digest,
                    "skillHashes": {
                        skill: hashlib.sha256(
                            (source_b / "skills" / skill / "SKILL.md").read_bytes()
                        ).hexdigest()
                        for skill in [
                            "using-superpowers",
                            "brainstorming",
                            "writing-plans",
                            "test-driven-development",
                            "systematic-debugging",
                            "requesting-code-review",
                            "verification-before-completion",
                        ]
                    },
                }
            },
        )

        selection = module.resolve_provider_selection(repo, home, {})
        report = module.diagnose_provider_selection(selection, repo, home)

        strict = report["providers"]["superpowers"]
        self.assertTrue(report["methodologyReady"], report)
        self.assertEqual(strict["sourceChannel"], "openai-curated-remote")
        self.assertEqual(strict["selectionSource"], "matching_lock")
        self.assertTrue(all(path.startswith(str(source_b.resolve())) for path in strict["skillPaths"].values()))

    def test_stale_provider_lock_does_not_fall_back_to_another_source(self):
        module = self.provider_module()
        home = self.make_codex_home(
            superpowers_version="6.1.1", superpowers_channel="openai-curated-remote"
        )
        repo = self.make_project_repo(
            enable_gsd=False,
            methodology_profile="strict-superpowers",
            roadmap_provider="none",
            provider_selectors={},
        )
        self.write_provider_lock(
            repo,
            {"superpowers": {"sourceChannel": "missing", "manifestDigest": "0" * 64}},
        )

        report = module.diagnose_provider_selection(
            module.resolve_provider_selection(repo, home, {}), repo, home
        )

        self.assertFalse(report["methodologyReady"], report)
        self.assertEqual(report["providers"]["superpowers"]["status"], "stale_lock")

    def test_matt_lock_hash_drift_blocks_lean_routing(self):
        module = self.provider_module()
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="lean-matt",
            roadmap_provider="none",
            provider_selectors={
                "mattpocock-skills": {
                    "kind": "git-skill-pack",
                    "repository": "mattpocock/skills",
                    "ref": "v1.1.0",
                    "commit": "d574778f94cf620fcc8ce741584093bc650a61d3",
                }
            },
        )
        project_root = self.write_project_matt_skills(repo)
        self.write_matching_matt_lock(repo)
        with (project_root / "tdd" / "SKILL.md").open("a") as handle:
            handle.write("\nlocal drift\n")

        report = module.diagnose_provider_selection(
            module.resolve_provider_selection(repo, home, {}), repo, home
        )

        self.assertFalse(report["methodologyReady"], report)
        self.assertEqual(report["providers"]["mattpocock-skills"]["status"], "source_drift")

    def test_wrong_explicit_matt_selector_cannot_attest_same_named_skills(self):
        module = self.provider_module()
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="lean-matt",
            roadmap_provider="none",
            provider_selectors={
                "mattpocock-skills": {
                    "kind": "git-skill-pack",
                    "repository": "attacker/skills",
                    "ref": "v1.1.0",
                    "commit": "d574778f94cf620fcc8ce741584093bc650a61d3",
                }
            },
        )
        self.write_project_matt_skills(repo)

        report = module.diagnose_provider_selection(
            module.resolve_provider_selection(repo, home, {}), repo, home
        )

        self.assertFalse(report["methodologyReady"], report)
        self.assertEqual(report["providers"]["mattpocock-skills"]["status"], "source_mismatch")

    def test_unlocked_arbitrary_same_named_matt_skills_are_not_trusted(self):
        module = self.provider_module()
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="lean-matt",
            roadmap_provider="none",
        )
        self.write_project_matt_skills(repo)
        for skill in MATT_ALLOWED:
            (repo / ".agents" / "skills" / skill / "SKILL.md").write_text(
                self.skill_fixture_text(skill)
            )

        report = module.diagnose_provider_selection(
            module.resolve_provider_selection(repo, home, {}), repo, home
        )

        self.assertFalse(report["methodologyReady"], report)
        self.assertEqual(report["providers"]["mattpocock-skills"]["status"], "unverifiable_source")

    def test_triggered_lean_matt_capability_rejects_foreign_project_skill_route(self):
        module = self.provider_module()
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="lean-matt",
            roadmap_provider="none",
        )
        self.write_project_matt_skills(repo)
        self.write_matching_matt_lock(repo)
        target = repo / ".agents" / "skills" / "tdd" / "SKILL.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("---\nname: tdd\ndescription: foreign source\n---\n")

        report = module.diagnose_provider_selection(
            module.resolve_provider_selection(repo, home, {}),
            repo,
            home,
            triggered_capabilities={"test-first-execution"},
        )

        capability = report["capabilities"]["test-first-execution"]
        self.assertFalse(capability["ready"], report)
        self.assertEqual(capability["projectSkills"]["tdd"]["status"], "source_untrusted")
        self.assertFalse(report["methodologyReady"], report)
        self.assertFalse(report["ok"], report)

    def test_lean_matt_activation_reports_existing_foreign_target_as_conflict(self):
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="lean-matt",
            roadmap_provider="none",
        )
        target = repo / ".agents" / "skills" / "tdd" / "SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_text("---\nname: tdd\ndescription: foreign source\n---\n")

        report = ensure_project_local_skills(
            repo,
            PLUGIN_ROOT,
            home,
            dry_run=True,
            selection={"effectiveMethodologyProfile": "lean-matt"},
            provider_diagnosis={
                "providers": {"mattpocock-skills": {"implicitSkills": MATT_ALLOWED}}
            },
        )

        item = next(
            item
            for item in report["items"]
            if item["provider"] == "mattpocock-skills" and item["skill"] == "tdd"
        )
        self.assertFalse(item["ok"], item)
        self.assertEqual(item["status"], "source-conflict")
        self.assertFalse(report["ok"], report)

    def test_superpowers_lock_skill_hash_drift_blocks_strict_routing(self):
        module = self.provider_module()
        home = self.make_codex_home(
            superpowers_version="6.1.1", superpowers_channel="openai-curated-remote"
        )
        repo = self.make_project_repo(
            enable_gsd=False,
            methodology_profile="strict-superpowers",
            roadmap_provider="none",
            provider_selectors={},
        )
        root = home / "plugins" / "cache" / "openai-curated-remote" / "superpowers" / "local"
        manifest_digest = hashlib.sha256((root / ".codex-plugin" / "plugin.json").read_bytes()).hexdigest()
        required = [
            "using-superpowers",
            "brainstorming",
            "writing-plans",
            "test-driven-development",
            "systematic-debugging",
            "requesting-code-review",
            "verification-before-completion",
        ]
        hashes = {
            skill: hashlib.sha256((root / "skills" / skill / "SKILL.md").read_bytes()).hexdigest()
            for skill in required
        }
        self.write_provider_lock(
            repo,
            {
                "superpowers": {
                    "sourceChannel": "openai-curated-remote",
                    "version": "6.1.1",
                    "manifestDigest": manifest_digest,
                    "skillHashes": hashes,
                }
            },
        )
        with (root / "skills" / "brainstorming" / "SKILL.md").open("a") as handle:
            handle.write("\nlocal drift\n")

        report = module.diagnose_provider_selection(
            module.resolve_provider_selection(repo, home, {}), repo, home
        )

        self.assertFalse(report["methodologyReady"], report)
        self.assertEqual(report["providers"]["superpowers"]["status"], "source_drift")

    def test_gsd_selector_version_drift_blocks_roadmap_readiness(self):
        module = self.provider_module()
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=True,
            methodology_profile="core",
            roadmap_provider="gsd",
            provider_selectors={"gsd": {"package": "@opengsd/gsd-core", "version": "1.6.1"}},
        )
        self.write_gsd_core_runtime(repo, version="1.4.4")

        report = module.diagnose_provider_selection(
            module.resolve_provider_selection(repo, home, {}), repo, home
        )

        self.assertFalse(report["roadmapReady"], report)
        self.assertEqual(report["providers"]["gsd"]["status"], "source_drift")

    def test_gsd_first_lock_requires_a_successful_pinned_install_receipt(self):
        module = self.provider_module()
        activation = importlib.import_module("workflow_provider_activation")
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=True,
            methodology_profile="core",
            roadmap_provider="gsd",
            provider_selectors={"gsd": {"source_id": "gsd-core-1-6-1"}},
        )
        (repo / ".planning" / "devflow" / "providers.lock.json").unlink()
        selection = module.resolve_provider_selection(repo, home, {})

        normal = module.diagnose_provider_selection(selection, repo, home)
        self.assertFalse(normal["roadmapReady"])
        self.assertEqual(normal["providers"]["gsd"]["status"], "content_lock_required")

        install_command = [
            "npx",
            "-y",
            "@opengsd/gsd-core@1.6.1",
            "--codex",
            "--local",
            "--profile=standard",
        ]
        bootstrap = module.diagnose_provider_selection(
            selection,
            repo,
            home,
            trusted_install_receipts={
                "gsd": {
                    "ok": True,
                    "source_id": "gsd-core-1-6-1",
                    "command": install_command,
                }
            },
        )
        self.assertTrue(bootstrap["roadmapReady"], bootstrap)
        self.assertEqual(bootstrap["providers"]["gsd"]["attestationAuthority"], "authorized-pinned-install")
        payload = activation.provider_lock_payload(bootstrap)
        self.write_provider_lock(repo, payload["providers"])

        locked = module.diagnose_provider_selection(
            module.resolve_provider_selection(repo, home, {}), repo, home
        )
        self.assertTrue(locked["roadmapReady"], locked)

    def test_malformed_gsd_manifest_fails_closed_without_exception(self):
        module = self.provider_module()
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=True,
            methodology_profile="core",
            roadmap_provider="gsd",
            provider_selectors={"gsd": {"source_id": "gsd-core-1-6-1"}},
        )
        (repo / ".codex" / "gsd-file-manifest.json").write_text("not-json\n")

        report = module.diagnose_provider_selection(
            module.resolve_provider_selection(repo, home, {}), repo, home
        )

        self.assertFalse(report["roadmapReady"])
        self.assertEqual(report["providers"]["gsd"]["status"], "content_manifest_invalid")

    def test_provider_lock_persistence_requires_apply_and_persist_authority(self):
        module = self.provider_module()
        activation = importlib.import_module("workflow_provider_activation")
        persist_provider_lock = getattr(activation, "persist_provider_lock", None)
        self.assertIsNotNone(persist_provider_lock, "provider lock persistence seam must exist")
        home = self.make_codex_home(
            superpowers_version="6.1.1", superpowers_channel="openai-curated-remote"
        )
        repo = self.make_project_repo(
            enable_gsd=False,
            methodology_profile="strict-superpowers",
            roadmap_provider="none",
            provider_selectors={
                "superpowers": {
                    "kind": "codex-plugin",
                    "plugin_id": "superpowers",
                    "source_channel": "openai-curated-remote",
                    "version": "6.1.1",
                }
            },
        )
        lock = repo / ".planning" / "devflow" / "providers.lock.json"
        selection = module.resolve_provider_selection(repo, home, {})
        report = module.diagnose_provider_selection(selection, repo, home)

        dry_run = persist_provider_lock(report, repo, apply=False, persist_selection=True)
        apply_without_persist = persist_provider_lock(report, repo, apply=True, persist_selection=False)

        self.assertFalse(lock.exists())
        self.assertEqual(dry_run["status"], "planned")
        self.assertEqual(apply_without_persist["status"], "authorization_required")

        applied = persist_provider_lock(report, repo, apply=True, persist_selection=True)

        self.assertEqual(applied["status"], "applied")
        payload = json.loads(lock.read_text())
        self.assertEqual(
            payload["providers"]["superpowers"]["sourceChannel"], "openai-curated-remote"
        )

    def test_lean_matt_maps_only_approved_primitives(self):
        module = self.provider_module()
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        self.write_standalone_skills(
            home,
            MATT_ALLOWED + ["ask-matt", "to-spec", "to-tickets", "implement", "triage", "wayfinder"],
        )
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="lean-matt",
            roadmap_provider="none",
        )
        self.write_project_matt_skills(repo)
        self.write_matching_matt_lock(repo)

        report = module.diagnose_provider_selection(
            module.resolve_provider_selection(repo, home, {}), repo, home
        )

        self.assertTrue(report["methodologyReady"], report)
        implicit = set(report["providers"]["mattpocock-skills"]["implicitSkills"])
        self.assertEqual(implicit, set(MATT_ALLOWED))
        self.assertTrue(
            {"ask-matt", "to-spec", "to-tickets", "implement", "triage", "wayfinder"}.isdisjoint(implicit)
        )
        self.assertEqual(report["capabilities"]["implementation-planning"]["provider"], "devflow-native")
        self.assertEqual(report["capabilities"]["completion-proof"]["provider"], "devflow-native")

    def test_gsd_drift_is_advisory_when_roadmap_is_none(self):
        module = self.provider_module()
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = self.make_project_repo(
            enable_superpowers=False,
            methodology_profile="core",
            roadmap_provider="none",
        )
        self.write_gsd_core_runtime(repo, version="1.4.4")

        report = module.diagnose_provider_selection(
            module.resolve_provider_selection(repo, home, {}), repo, home
        )

        self.assertTrue(report["coreReady"], report)
        self.assertTrue(report["roadmapReady"], report)
        self.assertEqual(report["providers"]["gsd"]["status"], "available_unselected")

    def test_gsd_tracking_scope_includes_requirements(self):
        module = self.provider_module()
        repo = Path(tempfile.mkdtemp(prefix="devflow-gsd-owned-paths-"))
        requirements = repo / ".planning" / "REQUIREMENTS.md"
        requirements.parent.mkdir(parents=True)
        requirements.write_text("# Requirements\n")

        self.assertIn(".planning/REQUIREMENTS.md", module.gsd_owned_paths(repo))

    def test_implicit_roadmap_inference_never_executes_untrusted_gsd_runtime(self):
        module = self.provider_module()
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = Path(tempfile.mkdtemp(prefix="devflow-untrusted-gsd-inference-"))
        (repo / "openspec").mkdir()
        (repo / "openspec" / "config.yaml").write_text("schema: spec-driven\n")
        runtime = repo / ".codex" / "gsd-core" / "bin" / "gsd-tools.cjs"
        runtime.parent.mkdir(parents=True)
        runtime.write_text("throw new Error('must not execute during inference');\n")
        roadmap = repo / ".planning" / "ROADMAP.md"
        roadmap.parent.mkdir(parents=True)
        roadmap.write_text("# Untrusted roadmap\n")

        with mock.patch.object(module, "GsdReadOnlyAdapter", side_effect=AssertionError("unexpected runtime")):
            selection = module.resolve_provider_selection(repo, home, {})

        self.assertEqual(selection["effectiveRoadmapProvider"], "none")

    def test_activation_plan_contains_only_selected_provider_actions(self):
        module = self.provider_module()
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = self.make_project_repo(
            enable_superpowers=False,
            methodology_profile="core",
            roadmap_provider="none",
        )

        plan = module.provider_activation_plan(
            module.resolve_provider_selection(repo, home, {}), repo, home
        )

        self.assertTrue(plan["dryRun"])
        commands = [" ".join(item.get("command", [])) for item in plan["actions"]]
        self.assertFalse(any("superpowers" in item or "matt" in item or "gsd" in item for item in commands))
        self.assertFalse(any(item["effect"] == "dependency.install_update" for item in plan["actions"]))

    def test_project_activation_commands_and_skills_are_selection_scoped(self):
        core_home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        core_repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="core",
            roadmap_provider="none",
        )
        strict_home = self.make_codex_home(
            superpowers_version="6.1.1", superpowers_channel="openai-curated-remote"
        )
        strict_repo = self.make_project_repo(
            enable_gsd=False,
            methodology_profile="strict-superpowers",
            roadmap_provider="none",
            provider_selectors={
                "superpowers": {
                    "kind": "codex-plugin",
                    "source_channel": "openai-curated-remote",
                    "version": "6.1.1",
                }
            },
        )
        gsd_repo = self.make_project_repo(
            enable_superpowers=False,
            methodology_profile="core",
            roadmap_provider="gsd",
        )

        core = activate_project_dependencies(
            core_repo,
            dry_run=True,
            plugin_root=PLUGIN_ROOT,
            codex_home=core_home,
        )
        strict = activate_project_dependencies(
            strict_repo,
            dry_run=True,
            plugin_root=PLUGIN_ROOT,
            codex_home=strict_home,
        )
        gsd = activate_project_dependencies(
            gsd_repo,
            dry_run=True,
            plugin_root=PLUGIN_ROOT,
            codex_home=core_home,
        )

        core_commands = [item["command"] for item in core["commands"]]
        strict_commands = [item["command"] for item in strict["commands"]]
        gsd_commands = [item["command"] for item in gsd["commands"]]
        self.assertFalse(any("@opengsd/gsd-core" in part for command in core_commands for part in command))
        self.assertFalse(any(item["provider"] in {"superpowers", "gsd"} for item in core["local_skills"]["items"]))
        self.assertFalse(any("@opengsd/gsd-core" in part for command in strict_commands for part in command))
        self.assertTrue(any(item["provider"] == "superpowers" for item in strict["local_skills"]["items"]))
        self.assertTrue(any("@opengsd/gsd-core" in part for command in gsd_commands for part in command))

    def test_activation_plans_pinned_install_for_missing_selected_methodology_provider(self):
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        strict_repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="strict-superpowers",
            roadmap_provider="none",
            provider_selectors={"superpowers": {"source_id": "superpowers-openai-curated-remote"}},
        )
        matt_repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="lean-matt",
            roadmap_provider="none",
            provider_selectors={"mattpocock-skills": {"source_id": "mattpocock-skills-v1-1-0"}},
        )

        strict = activate_project_dependencies(
            strict_repo, dry_run=True, plugin_root=PLUGIN_ROOT, codex_home=home
        )
        matt = activate_project_dependencies(
            matt_repo, dry_run=True, plugin_root=PLUGIN_ROOT, codex_home=home
        )

        strict_commands = [item["command"] for item in strict["commands"]]
        matt_commands = [item["command"] for item in matt["commands"]]
        self.assertIn(
            ["codex", "plugin", "add", "superpowers@openai-curated-remote", "--json"],
            strict_commands,
        )
        matt_command = next(command for command in matt_commands if "skills@1.5.9" in command)
        self.assertIn("https://github.com/mattpocock/skills/tree/v1.1.0", matt_command)
        self.assertNotIn("--global", matt_command)
        self.assertTrue(strict["local_skills"]["ok"], strict)
        self.assertTrue(matt["local_skills"]["ok"], matt)

    def test_activation_bootstraps_matt_from_matching_lock_without_selector(self):
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="lean-matt",
            roadmap_provider="none",
            provider_selectors={},
        )
        self.write_project_matt_skills(repo)
        self.write_matching_matt_lock(repo)
        for skill in MATT_ALLOWED:
            shutil.rmtree(repo / ".agents" / "skills" / skill)

        report = activate_project_dependencies(
            repo,
            dry_run=True,
            plugin_root=PLUGIN_ROOT,
            codex_home=home,
        )

        matt_commands = [item["command"] for item in report["commands"]]
        command = next(command for command in matt_commands if "skills@1.5.9" in command)
        self.assertIn("https://github.com/mattpocock/skills/tree/v1.1.0", command)
        self.assertNotIn("--global", command)

    def test_activation_bootstraps_matt_from_unique_trusted_source(self):
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="lean-matt",
            roadmap_provider="none",
            provider_selectors={},
        )
        lock = repo / ".planning" / "devflow" / "providers.lock.json"
        if lock.exists():
            lock.unlink()

        report = activate_project_dependencies(
            repo,
            dry_run=True,
            plugin_root=PLUGIN_ROOT,
            codex_home=home,
        )

        matt_commands = [item["command"] for item in report["commands"]]
        command = next(command for command in matt_commands if "skills@1.5.9" in command)
        self.assertIn("https://github.com/mattpocock/skills/tree/v1.1.0", command)
        self.assertNotIn("--global", command)

    def test_activation_keeps_ambiguous_matt_bootstrap_fail_closed(self):
        activation_module = importlib.import_module("workflow_project_activation")
        source = {
            "provider": "mattpocock-skills",
            "repository": "mattpocock/skills",
            "ref": "v1.1.0",
            "commit": "d574778f94cf620fcc8ce741584093bc650a61d3",
            "installCommand": ["npx", "skills@1.5.9", "add", "fixture"],
        }
        commands = activation_module.official_install_command_records(
            Path("/tmp/devflow-matt-ambiguous"),
            plugin_root=PLUGIN_ROOT,
            selection={
                "effectiveMethodologyProfile": "lean-matt",
                "effectiveRoadmapProvider": "none",
                "providerSelectors": {},
                "providerLock": {"providers": {}},
            },
            diagnosis={
                "providers": {
                    "mattpocock-skills": {
                        "ready": False,
                        "status": "missing_capabilities",
                        "projectRootLocal": True,
                        "nonLocalSkills": [],
                    }
                }
            },
            source_records={
                "matt-a": source,
                "matt-b": {**source, "commit": "b" * 40},
            },
        )

        self.assertFalse(any("skills@1.5.9" in command["command"] for command in commands))

    def test_lean_matt_apply_rediagnoses_project_local_installer_output(self):
        activation_module = importlib.import_module("workflow_project_activation")
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="lean-matt",
            roadmap_provider="none",
            provider_selectors={
                "mattpocock-skills": {"source_id": "mattpocock-skills-v1-1-0"}
            },
        )

        def successful(command, _repo, dry_run, provenance_source=None, environment=None):
            if "skills@1.5.9" in command:
                self.write_project_matt_skills(repo)
            return {
                "ok": True,
                "command": command,
                "skipped": dry_run,
                "provenanceSource": provenance_source,
                "environment": environment or {},
            }

        with mock.patch.object(activation_module, "run_command", side_effect=successful):
            report = activation_module.activate_project_dependencies(
                repo,
                dry_run=False,
                plugin_root=PLUGIN_ROOT,
                codex_home=home,
            )

        matt = report["providers"]["mattpocock-skills"]
        matt_items = [
            item for item in report["local_skills"]["items"]
            if item["provider"] == "mattpocock-skills"
        ]
        lock = json.loads((repo / ".planning" / "devflow" / "providers.lock.json").read_text())
        project_root = (repo / ".agents" / "skills").resolve()
        self.assertTrue(report["ok"], report)
        self.assertTrue(report["methodologyReady"], report)
        self.assertEqual(matt["root"], str(project_root))
        self.assertTrue(all(item["status"] == "already-present" for item in matt_items), matt_items)
        self.assertTrue(all(Path(item["source"]).is_relative_to(project_root) for item in matt_items))
        self.assertEqual(
            lock["providers"]["mattpocock-skills"]["sourceRoot"],
            str(project_root),
        )
        self.assertFalse((home / "skills").exists())

    def test_gsd_apply_bootstraps_lock_only_from_successful_pinned_install_and_rediagnoses(self):
        activation_module = importlib.import_module("workflow_project_activation")
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=True,
            methodology_profile="core",
            roadmap_provider="gsd",
            provider_selectors={"gsd": {"source_id": "gsd-core-1-6-1"}},
        )
        lock = repo / ".planning" / "devflow" / "providers.lock.json"
        lock.unlink()

        def successful(command, _repo, dry_run, provenance_source=None, environment=None):
            return {
                "ok": True,
                "command": command,
                "skipped": dry_run,
                "provenanceSource": provenance_source,
                "environment": environment or {},
            }

        with mock.patch.object(activation_module, "run_command", side_effect=successful):
            report = activation_module.activate_project_dependencies(
                repo,
                dry_run=False,
                plugin_root=PLUGIN_ROOT,
                codex_home=home,
            )

        self.assertTrue(report["ok"], report)
        self.assertTrue(report["roadmapReady"], report)
        self.assertTrue(lock.exists())
        persisted = json.loads(lock.read_text())["providers"]["gsd"]
        self.assertEqual(persisted["contentAttestation"]["kind"], "authorized-pinned-install")
        self.assertEqual(report["provider_persistence"]["status"], "applied")

    def test_activation_cli_is_dry_run_by_default_and_apply_is_explicit(self):
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = self.make_project_repo(
            enable_orchestrator=False,
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="core",
            roadmap_provider="none",
        )
        command = [
            sys.executable,
            str(PLUGIN_ROOT / "scripts" / "activate_project_dependencies.py"),
            "--repo",
            str(repo),
            "--plugin-root",
            str(PLUGIN_ROOT),
            "--codex-home",
            str(home),
            "--skip-official-installs",
            "--json",
        ]

        dry_run = subprocess.run(command, text=True, capture_output=True, check=False)

        self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
        dry_report = json.loads(dry_run.stdout)
        self.assertTrue(dry_report["dry_run"])
        self.assertFalse((repo / ".agents" / "skills" / "project-orchestrator").exists())

        applied = subprocess.run([*command[:-1], "--apply", "--json"], text=True, capture_output=True, check=False)

        self.assertEqual(applied.returncode, 0, applied.stderr)
        apply_report = json.loads(applied.stdout)
        self.assertFalse(apply_report["dry_run"])
        self.assertTrue(apply_report["coreReady"], apply_report)
        self.assertTrue((repo / ".agents" / "skills" / "project-orchestrator" / "SKILL.md").exists())

    def test_provider_source_override_is_dry_run_until_apply_and_persist(self):
        home = self.make_codex_home(superpowers_version="6.0.3", superpowers_channel="source-a")
        for skill in [
            "using-superpowers",
            "brainstorming",
            "writing-plans",
            "test-driven-development",
            "systematic-debugging",
            "requesting-code-review",
            "verification-before-completion",
            "receiving-code-review",
            "executing-plans",
            "subagent-driven-development",
            "using-git-worktrees",
            "finishing-a-development-branch",
        ]:
            self.write_skill(home, "superpowers", skill, channel="openai-curated-remote")
        self.write_plugin_manifest(
            home,
            "superpowers",
            version="6.1.1",
            channel="openai-curated-remote",
        )
        repo = self.make_project_repo(
            enable_gsd=False,
            methodology_profile="strict-superpowers",
            roadmap_provider="none",
            provider_selectors={},
        )
        config_path = repo / ".dev-flow.json"
        lock_path = repo / ".planning" / "devflow" / "providers.lock.json"
        command = [
            sys.executable,
            str(PLUGIN_ROOT / "scripts" / "activate_project_dependencies.py"),
            "--repo",
            str(repo),
            "--plugin-root",
            str(PLUGIN_ROOT),
            "--codex-home",
            str(home),
            "--skip-official-installs",
            "--provider-source",
            "superpowers=superpowers-openai-curated-remote",
            "--persist-provider-selection",
            "--json",
        ]

        before = config_path.read_text()
        dry_run = subprocess.run(command, text=True, capture_output=True, check=False)

        self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
        dry_report = json.loads(dry_run.stdout)
        self.assertTrue(dry_report["methodologyReady"], dry_report)
        self.assertEqual(dry_report["provider_persistence"]["status"], "planned")
        self.assertEqual(config_path.read_text(), before)
        self.assertFalse(lock_path.exists())

        applied = subprocess.run([*command[:-1], "--apply", "--json"], text=True, capture_output=True, check=False)

        self.assertEqual(applied.returncode, 0, applied.stderr)
        apply_report = json.loads(applied.stdout)
        self.assertEqual(apply_report["provider_persistence"]["status"], "applied")
        config = json.loads(config_path.read_text())
        selector = config["workflow"]["provider_selectors"]["superpowers"]
        self.assertEqual(selector["source_channel"], "openai-curated-remote")
        self.assertEqual(
            json.loads(lock_path.read_text())["providers"]["superpowers"]["sourceChannel"],
            "openai-curated-remote",
        )

    def test_provider_source_apply_without_persist_authority_is_atomic_and_fails(self):
        home = self.make_codex_home(superpowers_version="6.1.1", superpowers_channel="openai-curated-remote")
        repo = self.make_project_repo(
            enable_orchestrator=False,
            enable_superpowers=False,
            enable_gsd=False,
            enable_legacy_openspec_skills=False,
            methodology_profile="strict-superpowers",
            roadmap_provider="none",
            provider_selectors={},
        )
        config_path = repo / ".dev-flow.json"
        before = config_path.read_text()

        result = activate_project_dependencies(
            repo,
            dry_run=False,
            skip_official_installs=True,
            plugin_root=PLUGIN_ROOT,
            codex_home=home,
            provider_sources=["superpowers=superpowers-openai-curated-remote"],
            persist_provider_selection=False,
        )

        self.assertFalse(result["ok"], result)
        self.assertEqual(result["provider_persistence"]["status"], "authorization_required")
        self.assertTrue(result["writes_blocked"])
        self.assertEqual(config_path.read_text(), before)
        self.assertFalse((repo / ".planning" / "devflow" / "providers.lock.json").exists())
        self.assertFalse((repo / ".agents" / "skills" / "brainstorming").exists())

    def test_methodology_override_requires_persist_authority_and_can_select_core(self):
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="strict-superpowers",
            roadmap_provider="gsd",
            provider_selectors={},
        )
        config_path = repo / ".dev-flow.json"
        before = config_path.read_text()

        command = [
            sys.executable,
            str(PLUGIN_ROOT / "scripts" / "activate_project_dependencies.py"),
            "--repo",
            str(repo),
            "--plugin-root",
            str(PLUGIN_ROOT),
            "--codex-home",
            str(home),
            "--skip-official-installs",
            "--methodology-profile",
            "core",
            "--roadmap-provider",
            "none",
            "--json",
        ]
        dry_run = subprocess.run(command, text=True, capture_output=True, check=False)
        self.assertEqual(dry_run.returncode, 0, f"{dry_run.stderr}\n{dry_run.stdout}")
        dry_report = json.loads(dry_run.stdout)

        self.assertTrue(dry_report["ok"], dry_report)
        self.assertEqual(dry_report["selection"]["effectiveMethodologyProfile"], "core")
        self.assertEqual(dry_report["selection"]["effectiveRoadmapProvider"], "none")
        self.assertEqual(config_path.read_text(), before)

        unauthorized = activate_project_dependencies(
            repo,
            dry_run=False,
            skip_official_installs=True,
            plugin_root=PLUGIN_ROOT,
            codex_home=home,
            methodology_profile="core",
            roadmap_provider="none",
        )

        self.assertFalse(unauthorized["ok"], unauthorized)
        self.assertTrue(unauthorized["writes_blocked"])
        self.assertEqual(
            unauthorized["provider_persistence"]["status"],
            "authorization_required",
        )
        self.assertEqual(config_path.read_text(), before)

        applied = activate_project_dependencies(
            repo,
            dry_run=False,
            skip_official_installs=True,
            plugin_root=PLUGIN_ROOT,
            codex_home=home,
            methodology_profile="core",
            roadmap_provider="none",
            persist_provider_selection=True,
        )

        self.assertTrue(applied["ok"], applied)
        persisted = json.loads(config_path.read_text())["workflow"]
        self.assertEqual(persisted["methodology_profile"], "core")
        self.assertEqual(persisted["roadmap_provider"], "none")

    def test_external_updater_plans_only_selected_methodology_and_roadmap(self):
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        core_repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="core",
            roadmap_provider="none",
        )
        strict_repo = self.make_project_repo(
            enable_gsd=False,
            methodology_profile="strict-superpowers",
            roadmap_provider="none",
        )
        gsd_repo = self.make_project_repo(
            enable_superpowers=False,
            methodology_profile="core",
            roadmap_provider="gsd",
        )
        superpowers_result = auto_update.item(
            "external-updater", "superpowers", "unchanged", "fixture"
        )

        with mock.patch.object(auto_update, "executable_exists", return_value=False), mock.patch.object(
            auto_update, "superpowers_update_result", return_value=superpowers_result
        ):
            core = auto_update.run_external_updaters(home, apply=False, repo=core_repo)
            strict = auto_update.run_external_updaters(home, apply=False, repo=strict_repo)
            gsd = auto_update.run_external_updaters(home, apply=False, repo=gsd_repo)

        self.assertNotIn("superpowers", [item["name"] for item in core])
        self.assertNotIn("gsd-core", [item["name"] for item in core])
        self.assertIn("superpowers", [item["name"] for item in strict])
        self.assertNotIn("gsd-core", [item["name"] for item in strict])
        self.assertNotIn("superpowers", [item["name"] for item in gsd])
        self.assertIn("gsd-core", [item["name"] for item in gsd])

    def test_external_updater_apply_obeys_default_deny_policy(self):
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="core",
            roadmap_provider="none",
        )

        with mock.patch.object(auto_update, "run_command") as runner:
            result = auto_update.run_external_updaters(
                home,
                apply=True,
                repo=repo,
                authorizations=set(),
            )

        self.assertEqual(result[0]["status"], "authorization-required")
        self.assertEqual(result[0]["sideEffect"]["denial"], "dry_run_only")
        runner.assert_not_called()

    def test_updater_apply_exit_code_blocks_unfulfilled_provider_actions(self):
        results = [
            auto_update.item("external-updater", "provider", status, "fixture")
            for status in (
                "authorization-required",
                "source-selection-required",
                "source-registration-required",
            )
        ]

        self.assertEqual(auto_update.updater_exit_code(results, apply=True), 1)
        self.assertEqual(auto_update.updater_exit_code(results, apply=False), 0)

    def test_profile_roadmap_matrix_has_exact_readiness_and_selected_providers(self):
        module = self.provider_module()
        home = self.make_codex_home(
            superpowers_version="6.1.1", superpowers_channel="openai-curated-remote"
        )
        self.write_standalone_skills(home, MATT_ALLOWED)
        for methodology in ["core", "lean-matt", "strict-superpowers"]:
            for roadmap in ["none", "gsd"]:
                selectors = {}
                if methodology == "strict-superpowers":
                    selectors["superpowers"] = {
                        "kind": "codex-plugin",
                        "source_channel": "openai-curated-remote",
                        "version": "6.1.1",
                    }
                repo = self.make_project_repo(
                    enable_superpowers=methodology == "strict-superpowers",
                    enable_gsd=roadmap == "gsd",
                    methodology_profile=methodology,
                    roadmap_provider=roadmap,
                    provider_selectors=selectors,
                )
                if methodology == "lean-matt":
                    self.write_project_matt_skills(repo)
                    self.write_matching_matt_lock(repo)

                report = module.diagnose_provider_selection(
                    module.resolve_provider_selection(repo, home, {}), repo, home
                )

                expected = []
                if methodology == "lean-matt":
                    expected.append("mattpocock-skills")
                elif methodology == "strict-superpowers":
                    expected.append("superpowers")
                if roadmap == "gsd":
                    expected.append("gsd")
                self.assertTrue(report["coreReady"], (methodology, roadmap, report))
                self.assertTrue(report["methodologyReady"], (methodology, roadmap, report))
                self.assertTrue(report["roadmapReady"], (methodology, roadmap, report))
                self.assertEqual(report["selectedProviders"], expected)

    def test_goal_definition_is_required_only_when_triggered(self):
        module = self.provider_module()
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="core",
            roadmap_provider="none",
        )
        selection = module.resolve_provider_selection(repo, home, {})

        ordinary = module.diagnose_provider_selection(selection, repo, home)
        goal_backed = module.diagnose_provider_selection(
            selection, repo, home, triggered_capabilities={"goal-definition"}
        )

        self.assertTrue(ordinary["coreReady"], ordinary)
        self.assertEqual(ordinary["capabilities"]["goal-definition"]["status"], "not_triggered")
        self.assertFalse(goal_backed["capabilities"]["goal-definition"]["ready"])
        self.assertEqual(goal_backed["capabilities"]["goal-definition"]["nextAction"], "Use define-goal.")

    def test_provider_availability_does_not_satisfy_canonical_evidence(self):
        module = self.provider_module()
        home = self.make_codex_home(enable_plugin_eval=False, install_superpowers=False)
        repo = self.make_project_repo(
            enable_superpowers=False,
            enable_gsd=False,
            methodology_profile="lean-matt",
            roadmap_provider="none",
        )
        self.write_project_matt_skills(repo)
        self.write_matching_matt_lock(repo)

        report = module.diagnose_provider_selection(
            module.resolve_provider_selection(repo, home, {}),
            repo,
            home,
            triggered_capabilities={"test-first-execution"},
        )

        capability = report["capabilities"]["test-first-execution"]
        self.assertTrue(capability["ready"])
        self.assertFalse(capability["evidenceSatisfied"])
        self.assertEqual(capability["evidenceStatus"], "missing_red_evidence")

    def test_strict_conditional_skill_is_hash_verified_only_when_capability_is_triggered(self):
        module = self.provider_module()
        home = self.make_codex_home(
            superpowers_version="6.1.1", superpowers_channel="openai-curated-remote"
        )
        provider_skills = (
            home
            / "plugins"
            / "cache"
            / "openai-curated-remote"
            / "superpowers"
            / "local"
            / "skills"
        )
        for skill in [
            "receiving-code-review",
            "executing-plans",
            "subagent-driven-development",
            "using-git-worktrees",
            "finishing-a-development-branch",
        ]:
            shutil.rmtree(provider_skills / skill)
        repo = self.make_project_repo(
            enable_gsd=False,
            methodology_profile="strict-superpowers",
            roadmap_provider="none",
            provider_selectors={
                "superpowers": {
                    "source_channel": "openai-curated-remote",
                    "version": "6.1.1",
                }
            },
        )
        selection = module.resolve_provider_selection(repo, home, {})

        ordinary = module.diagnose_provider_selection(selection, repo, home)
        missing = module.diagnose_provider_selection(
            selection,
            repo,
            home,
            triggered_capabilities={"execution-orchestration"},
        )

        self.assertTrue(ordinary["methodologyReady"], ordinary)
        self.assertFalse(missing["capabilities"]["execution-orchestration"]["ready"])
        self.assertFalse(missing["ok"])

        self.write_skill(home, "superpowers", "executing-plans", channel="openai-curated-remote")
        (repo / ".agents" / "skills" / "executing-plans").symlink_to(
            provider_skills / "executing-plans",
            target_is_directory=True,
        )
        ready = module.diagnose_provider_selection(
            selection,
            repo,
            home,
            triggered_capabilities={"execution-orchestration"},
        )
        self.assertTrue(ready["capabilities"]["execution-orchestration"]["ready"], ready)

        with (
            home
            / "plugins"
            / "cache"
            / "openai-curated-remote"
            / "superpowers"
            / "local"
            / "skills"
            / "executing-plans"
            / "SKILL.md"
        ).open("a") as handle:
            handle.write("\ntampered\n")
        drifted = module.diagnose_provider_selection(
            selection,
            repo,
            home,
            triggered_capabilities={"execution-orchestration"},
        )
        self.assertFalse(drifted["capabilities"]["execution-orchestration"]["ready"])
        self.assertIn(
            "executing-plans",
            drifted["providers"]["superpowers"]["driftedConditionalSkills"],
        )

    def test_strict_conditional_activation_skills_are_reachable_from_capability_triggers(self):
        installer = importlib.import_module("workflow_project_skill_install")

        review = installer.strict_project_skills({"change-review"})
        orchestration = installer.strict_project_skills({"execution-orchestration"})

        self.assertIn("receiving-code-review", review)
        self.assertTrue(
            {
                "executing-plans",
                "subagent-driven-development",
                "using-git-worktrees",
                "finishing-a-development-branch",
            }.issubset(orchestration)
        )


if __name__ == "__main__":
    unittest.main()
