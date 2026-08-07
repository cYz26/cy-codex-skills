import json
import os
import re
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


def write_official_openspec_skills(repo: Path) -> None:
    from workflow_dependency_catalog import OPENSPEC_WORKFLOW_SKILLS

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


class MethodologyContractTests(unittest.TestCase):
    def test_static_registry_has_one_owner_and_six_pinned_matt_primitives(self):
        from workflow_methodology import methodology_manifest

        manifest = methodology_manifest()

        self.assertEqual(manifest["schemaVersion"], 1)
        self.assertEqual(manifest["controlPlane"], "devflow-openspec")
        self.assertEqual(manifest["source"]["repository"], "mattpocock/skills")
        self.assertEqual(manifest["source"]["ref"], "v1.1.0")
        self.assertEqual(
            manifest["source"]["commit"],
            "d574778f94cf620fcc8ce741584093bc650a61d3",
        )
        self.assertEqual(
            list(manifest["source"]["skillHashes"]),
            [
                "grilling",
                "tdd",
                "diagnosing-bugs",
                "code-review",
                "codebase-design",
                "domain-modeling",
            ],
        )
        self.assertNotIn("profiles", manifest)
        self.assertNotIn("roadmapProviders", manifest)

    def test_capability_routes_are_fixed_and_do_not_delegate_control_plane(self):
        from workflow_methodology import CAPABILITY_IDS, route_capability

        expected = {
            "decision-resolution": ("openspec", ["grilling"]),
            "implementation-planning": ("openspec", ["change-plan", "ai-native-tech-plan"]),
            "test-first-execution": ("devflow", ["tdd"]),
            "root-cause-diagnosis": ("devflow", ["diagnosing-bugs"]),
            "change-review": ("devflow", ["code-review"]),
            "completion-proof": ("devflow", ["verify-and-archive"]),
            "execution-orchestration": ("devflow", ["execute-task"]),
            "architecture-guidance": ("openspec", ["codebase-design"]),
            "domain-language-modeling": ("openspec", ["domain-modeling"]),
            "goal-definition": ("devflow", ["define-goal"]),
        }
        self.assertEqual(set(CAPABILITY_IDS), set(expected))
        for capability, (owner, skills) in expected.items():
            route = route_capability(capability)
            self.assertEqual(route["owner"], owner)
            self.assertEqual(route["skills"], skills)
            self.assertNotIn("profile", route)
            self.assertNotIn("provider", route)

    def test_only_triggered_matt_primitives_are_required(self):
        from workflow_methodology import required_matt_skills

        self.assertEqual(required_matt_skills(set()), [])
        self.assertEqual(
            required_matt_skills({"test-first-execution", "decision-resolution"}),
            ["grilling", "tdd"],
        )
        self.assertEqual(required_matt_skills({"execution-orchestration"}), [])
        self.assertEqual(required_matt_skills({"architecture-guidance"}), ["codebase-design"])
        self.assertEqual(
            required_matt_skills({"architecture-guidance", "domain-language-modeling"}),
            ["codebase-design", "domain-modeling"],
        )

    def test_flow_owning_matt_skills_are_never_allowlisted(self):
        from workflow_methodology import EXCLUDED_MATT_SKILLS, MATT_SKILLS

        for name in [
            "ask-matt",
            "setup-matt-pocock-skills",
            "to-spec",
            "to-tickets",
            "triage",
            "wayfinder",
            "implement",
            "improve-codebase-architecture",
        ]:
            self.assertIn(name, EXCLUDED_MATT_SKILLS)
            self.assertNotIn(name, MATT_SKILLS)

    def test_unknown_capability_fails_closed(self):
        from workflow_methodology import route_capability

        with self.assertRaisesRegex(ValueError, "unsupported DevFlow capability"):
            route_capability("roadmap-lifecycle")

    def test_current_config_has_no_provider_state_and_legacy_keys_fail_closed(self):
        from workflow_mode_routing import read_workflow_mode_config, route_workflow_mode

        current_repo = Path(tempfile.mkdtemp(prefix="devflow-current-config-"))
        (current_repo / ".dev-flow.json").write_text(
            json.dumps({"workflow": {"mode": "full-openspec"}}) + "\n"
        )
        current = read_workflow_mode_config(current_repo)

        self.assertTrue(current["valid"], current)
        for key in [
            "methodology_profile",
            "roadmap_provider",
            "provider_selectors",
            "roadmap_bindings",
        ]:
            self.assertNotIn(key, current)

        legacy_repo = Path(tempfile.mkdtemp(prefix="devflow-legacy-config-"))
        (legacy_repo / ".dev-flow.json").write_text(
            json.dumps(
                {
                    "workflow": {
                        "mode": "full-openspec",
                        "methodology_profile": "strict-superpowers",
                        "roadmap_provider": "gsd",
                    }
                }
            )
            + "\n"
        )
        legacy = read_workflow_mode_config(legacy_repo)
        routed = route_workflow_mode(legacy_repo, kind="internal-maintenance")

        self.assertFalse(legacy["valid"])
        self.assertIn("legacy workflow selection key", "; ".join(legacy["config_errors"]))
        self.assertEqual(routed["route_id"], "invalid-workflow-config")
        self.assertIn("inspect_legacy_workflow_config.py", routed["next_action"])

    def test_symlinked_workflow_config_fails_closed_without_reading_target(self):
        from workflow_mode_routing import read_workflow_mode_config, route_workflow_mode

        repo = Path(tempfile.mkdtemp(prefix="devflow-config-symlink-"))
        outside = Path(tempfile.mkdtemp(prefix="devflow-config-outside-")) / "secret.json"
        secret = "config-target-secret-must-not-leak"
        outside.write_text(
            json.dumps(
                {
                    "workflow": {"lightweight_ledger": {"enabled": True}},
                    "secret": secret,
                }
            )
        )
        (repo / ".dev-flow.json").symlink_to(outside)

        report = read_workflow_mode_config(repo)
        route = route_workflow_mode(repo, kind="docs-only")

        self.assertFalse(report["valid"], report)
        self.assertFalse(report["lightweight_ledger_enabled"])
        self.assertEqual(route["route_id"], "invalid-workflow-config")
        self.assertNotIn(secret, json.dumps(report, sort_keys=True))

    def test_side_effect_policy_is_generic_and_default_deny(self):
        from workflow_side_effect_policy import (
            load_side_effect_policy,
            side_effect_decision,
        )

        policy = load_side_effect_policy(PLUGIN_ROOT)
        self.assertTrue(policy["defaultDeny"])
        self.assertTrue(policy["sourcePath"].endswith("docs/side_effect_policy.json"))
        self.assertIn("git.commit", policy["effects"])
        self.assertNotIn("providers", policy)

        denied = side_effect_decision(PLUGIN_ROOT, "git.commit", set())
        allowed = side_effect_decision(
            PLUGIN_ROOT,
            "git.commit",
            {"explicit_user_request"},
        )
        unknown = side_effect_decision(PLUGIN_ROOT, "legacy.provider.install", set())

        self.assertFalse(denied["authorized"])
        self.assertTrue(allowed["authorized"])
        self.assertEqual(unknown["reason"], "unknown_effect_default_denied")

    def test_git_push_and_github_control_plane_have_independent_authorization(self):
        from workflow_side_effect_policy import (
            load_side_effect_policy,
            side_effect_decision,
        )

        policy = load_side_effect_policy(PLUGIN_ROOT)
        self.assertIn("git.push", policy["effects"])
        self.assertIn("github.control_plane_write", policy["effects"])
        self.assertIn("git.push_pr", policy["effects"])

        push = side_effect_decision(
            PLUGIN_ROOT,
            "git.push",
            {"explicit_user_request"},
        )
        github_without_credentials = side_effect_decision(
            PLUGIN_ROOT,
            "github.control_plane_write",
            {"explicit_user_request"},
        )
        github_with_credentials = side_effect_decision(
            PLUGIN_ROOT,
            "github.control_plane_write",
            {"explicit_user_request_and_credentials"},
        )
        legacy = side_effect_decision(
            PLUGIN_ROOT,
            "git.push_pr",
            {"explicit_user_request"},
        )

        self.assertTrue(push["authorized"])
        self.assertFalse(github_without_credentials["authorized"])
        self.assertTrue(github_with_credentials["authorized"])
        self.assertTrue(legacy["authorized"])

    def test_matt_readiness_uses_required_project_copy_and_all_resource_hashes(self):
        from workflow_methodology import diagnose_methodology

        repo = Path(tempfile.mkdtemp(prefix="devflow-matt-project-"))
        codex_home = Path(tempfile.mkdtemp(prefix="devflow-matt-global-"))
        source = PLUGIN_ROOT / "vendor" / "mattpocock-skills" / "tdd"
        global_skill = codex_home / "skills" / "tdd"
        global_skill.parent.mkdir(parents=True)
        shutil.copytree(source, global_skill)

        missing = diagnose_methodology(
            repo,
            {"test-first-execution"},
            PLUGIN_ROOT,
            codex_home=codex_home,
        )

        self.assertFalse(missing["ready"])
        self.assertEqual(missing["status"], "missing_project_skills")
        self.assertEqual(missing["requiredSkills"], ["tdd"])
        self.assertEqual(missing["missingSkills"], ["tdd"])
        self.assertTrue(missing["globalSkills"]["tdd"])

        project_skill = repo / ".agents" / "skills" / "tdd"
        project_skill.parent.mkdir(parents=True)
        shutil.copytree(source, project_skill)
        shutil.copy2(
            PLUGIN_ROOT / "vendor" / "mattpocock-skills" / "UPSTREAM_LICENSE.txt",
            project_skill / "UPSTREAM_LICENSE.txt",
        )
        ready = diagnose_methodology(
            repo,
            {"test-first-execution"},
            PLUGIN_ROOT,
            codex_home=codex_home,
        )

        self.assertTrue(ready["ready"], ready)
        self.assertEqual(ready["status"], "ready")
        self.assertEqual(ready["driftedFiles"], [])

        (project_skill / "mocking.md").write_text("tampered\n")
        drifted = diagnose_methodology(
            repo,
            {"test-first-execution"},
            PLUGIN_ROOT,
            codex_home=codex_home,
        )

        self.assertFalse(drifted["ready"])
        self.assertEqual(drifted["status"], "source_drift")
        self.assertEqual(drifted["driftedFiles"], ["tdd/mocking.md"])

    def test_adapted_project_skills_remove_excluded_workflow_handoffs(self):
        from workflow_methodology import diagnose_methodology
        from workflow_project_skill_install import install_matt_project_skill

        repo = Path(tempfile.mkdtemp(prefix="devflow-matt-adapted-"))
        for skill, capability, forbidden, replacement in (
            (
                "code-review",
                "change-review",
                "/setup-matt-pocock-skills",
                "do not invoke setup or issue-tracker bootstrap skills",
            ),
            (
                "diagnosing-bugs",
                "root-cause-diagnosis",
                "/improve-codebase-architecture",
                "DevFlow's `architecture-guidance` capability",
            ),
        ):
            result = install_matt_project_skill(
                repo,
                skill,
                PLUGIN_ROOT / "vendor" / "mattpocock-skills" / skill,
            )
            self.assertTrue(result["ok"], result)
            text = (repo / ".agents" / "skills" / skill / "SKILL.md").read_text()
            self.assertNotIn(forbidden, text)
            self.assertIn(replacement, text)
            diagnosis = diagnose_methodology(repo, {capability}, PLUGIN_ROOT)
            self.assertTrue(diagnosis["ready"], diagnosis)
            license_path = repo / ".agents" / "skills" / skill / "UPSTREAM_LICENSE.txt"
            self.assertTrue(license_path.is_file())

    def test_vendor_drift_blocks_all_project_skill_writes_before_activation(self):
        from workflow_project_skill_install import ensure_project_local_skills

        plugin_root = Path(tempfile.mkdtemp(prefix="devflow-matt-drift-plugin-"))
        source = PLUGIN_ROOT / "vendor" / "mattpocock-skills" / "tdd"
        target = plugin_root / "vendor" / "mattpocock-skills" / "tdd"
        target.parent.mkdir(parents=True)
        shutil.copytree(source, target)
        (target / "SKILL.md").write_text("tampered\n")
        repo = Path(tempfile.mkdtemp(prefix="devflow-matt-drift-project-"))

        report = ensure_project_local_skills(
            repo,
            plugin_root,
            Path(tempfile.mkdtemp(prefix="devflow-matt-drift-home-")),
            triggered_capabilities={"test-first-execution"},
        )

        self.assertFalse(report["ok"])
        self.assertEqual(report["methodology_source"]["status"], "source_drift")
        self.assertFalse((repo / ".agents").exists())

    def test_untriggered_vendor_drift_does_not_affect_readiness(self):
        from workflow_methodology import diagnose_methodology

        plugin_root = Path(tempfile.mkdtemp(prefix="devflow-untriggered-matt-drift-"))
        source = PLUGIN_ROOT / "vendor" / "mattpocock-skills" / "tdd"
        target = plugin_root / "vendor" / "mattpocock-skills" / "tdd"
        target.parent.mkdir(parents=True)
        shutil.copytree(source, target)
        (target / "SKILL.md").write_text("tampered\n")
        repo = Path(tempfile.mkdtemp(prefix="devflow-untriggered-matt-project-"))

        report = diagnose_methodology(repo, set(), plugin_root)

        self.assertTrue(report["ready"], report)
        self.assertEqual(report["sourceVerification"]["skills"], [])

    def test_symlinked_vendor_parent_is_never_trusted(self):
        from workflow_methodology import verify_matt_vendor

        plugin_root = Path(tempfile.mkdtemp(prefix="devflow-matt-vendor-symlink-"))
        (plugin_root / "vendor").symlink_to(PLUGIN_ROOT / "vendor", target_is_directory=True)

        report = verify_matt_vendor(plugin_root, {"tdd"})

        self.assertFalse(report["ready"], report)
        self.assertTrue(report["untrustedParents"], report)

    def test_vendor_license_is_required_and_hash_verified_for_triggered_skills(self):
        from workflow_methodology import verify_matt_vendor

        plugin_root = Path(tempfile.mkdtemp(prefix="devflow-matt-license-"))
        vendor = plugin_root / "vendor" / "mattpocock-skills"
        vendor.mkdir(parents=True)
        shutil.copytree(
            PLUGIN_ROOT / "vendor" / "mattpocock-skills" / "tdd",
            vendor / "tdd",
        )
        upstream_license = (
            PLUGIN_ROOT / "vendor" / "mattpocock-skills" / "UPSTREAM_LICENSE.txt"
        )

        missing = verify_matt_vendor(plugin_root, {"tdd"})
        self.assertFalse(missing["ready"], missing)
        self.assertIn("UPSTREAM_LICENSE.txt", missing["missingFiles"])

        shutil.copy2(upstream_license, vendor / "UPSTREAM_LICENSE.txt")
        ready = verify_matt_vendor(plugin_root, {"tdd"})
        self.assertTrue(ready["ready"], ready)

        (vendor / "UPSTREAM_LICENSE.txt").write_text("tampered license\n")
        drifted = verify_matt_vendor(plugin_root, {"tdd"})
        self.assertFalse(drifted["ready"], drifted)
        self.assertIn("UPSTREAM_LICENSE.txt", drifted["driftedFiles"])

    def test_symlinked_project_skill_parent_is_never_project_local(self):
        from workflow_methodology import diagnose_methodology

        repo = Path(tempfile.mkdtemp(prefix="devflow-matt-project-parent-symlink-"))
        outside = Path(tempfile.mkdtemp(prefix="devflow-matt-project-outside-"))
        shutil.copytree(
            PLUGIN_ROOT / "vendor" / "mattpocock-skills" / "tdd",
            outside / "tdd",
        )
        (repo / ".agents").mkdir()
        (repo / ".agents" / "skills").symlink_to(outside, target_is_directory=True)

        report = diagnose_methodology(repo, {"test-first-execution"}, PLUGIN_ROOT)

        self.assertFalse(report["ready"], report)
        self.assertEqual(report["status"], "nonlocal_project_skills")
        self.assertEqual(report["nonLocalSkills"], ["tdd"])

    def test_unexpected_symlink_inside_project_skill_fails_closed(self):
        from workflow_methodology import diagnose_methodology

        repo = Path(tempfile.mkdtemp(prefix="devflow-matt-project-extra-link-"))
        project_skill = repo / ".agents" / "skills" / "tdd"
        project_skill.parent.mkdir(parents=True)
        shutil.copytree(
            PLUGIN_ROOT / "vendor" / "mattpocock-skills" / "tdd",
            project_skill,
        )
        shutil.copy2(
            PLUGIN_ROOT / "vendor" / "mattpocock-skills" / "UPSTREAM_LICENSE.txt",
            project_skill / "UPSTREAM_LICENSE.txt",
        )
        outside = Path(tempfile.mkdtemp(prefix="devflow-matt-project-link-target-"))
        (project_skill / "extra-link").symlink_to(outside, target_is_directory=True)

        report = diagnose_methodology(repo, {"test-first-execution"}, PLUGIN_ROOT)

        self.assertFalse(report["ready"], report)
        self.assertEqual(report["status"], "source_drift")
        self.assertEqual(report["unexpectedFiles"], ["tdd/extra-link"])

    @unittest.skipUnless(hasattr(os, "mkfifo"), "requires FIFO support")
    def test_unexpected_non_regular_entry_inside_project_skill_fails_closed(self):
        from workflow_methodology import diagnose_methodology

        repo = Path(tempfile.mkdtemp(prefix="devflow-matt-project-extra-fifo-"))
        project_skill = repo / ".agents" / "skills" / "tdd"
        project_skill.parent.mkdir(parents=True)
        shutil.copytree(
            PLUGIN_ROOT / "vendor" / "mattpocock-skills" / "tdd",
            project_skill,
        )
        shutil.copy2(
            PLUGIN_ROOT / "vendor" / "mattpocock-skills" / "UPSTREAM_LICENSE.txt",
            project_skill / "UPSTREAM_LICENSE.txt",
        )
        os.mkfifo(project_skill / "extra-fifo")

        report = diagnose_methodology(repo, {"test-first-execution"}, PLUGIN_ROOT)

        self.assertFalse(report["ready"], report)
        self.assertEqual(report["status"], "source_drift")
        self.assertEqual(report["unexpectedFiles"], ["tdd/extra-fifo"])

    def test_dependency_report_contains_only_active_capabilities(self):
        from workflow_dependencies import dependency_report
        from workflow_dependency_catalog import PROJECT_ORCHESTRATOR_SKILLS

        repo = Path(tempfile.mkdtemp(prefix="devflow-dependencies-"))
        codex_home = Path(tempfile.mkdtemp(prefix="devflow-codex-home-"))
        (codex_home / "config.toml").write_text("")
        (repo / ".dev-flow.json").write_text(
            json.dumps({"workflow": {"mode": "full-openspec"}}) + "\n"
        )
        (repo / "openspec").mkdir()
        (repo / "openspec" / "config.yaml").write_text("schema: spec-driven\n")
        skill_root = repo / ".agents" / "skills"
        for skill in PROJECT_ORCHESTRATOR_SKILLS:
            source = PLUGIN_ROOT / "skills" / skill
            target = skill_root / skill
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, target)
        shutil.copytree(
            PLUGIN_ROOT / "vendor" / "mattpocock-skills" / "tdd",
            skill_root / "tdd",
        )
        shutil.copy2(
            PLUGIN_ROOT / "vendor" / "mattpocock-skills" / "UPSTREAM_LICENSE.txt",
            skill_root / "tdd" / "UPSTREAM_LICENSE.txt",
        )
        write_official_openspec_skills(repo)

        with tempfile.TemporaryDirectory(prefix="devflow-methodology-bin-") as bin_root:
            for name, output in {
                "codex": "codex fixture",
                "openspec": "1.7.0",
                "node": "v24.13.0",
            }.items():
                binary = Path(bin_root) / name
                binary.write_text(f"#!/bin/sh\nprintf '{output}\\n'\n")
                binary.chmod(0o755)
            with mock.patch.dict(
                os.environ,
                {"PATH": f"{bin_root}{os.pathsep}{os.environ.get('PATH', '')}"},
            ):
                report = dependency_report(
                    PLUGIN_ROOT,
                    codex_home=codex_home,
                    config_path=codex_home / "config.toml",
                    repo=repo,
                    triggered_capabilities={"test-first-execution"},
                )

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["methodology"]["requiredSkills"], ["tdd"])
        self.assertTrue(report["capabilities"]["test-first-execution"]["ready"])
        for key in [
            "selection",
            "providers",
            "superpowers",
            "methodologyReady",
            "roadmapReady",
        ]:
            self.assertNotIn(key, report)
        serialized = json.dumps(report, sort_keys=True).lower()
        self.assertNotIn("superpowers", serialized)
        self.assertNotIn("gsd", serialized)

    def test_dependency_cli_exposes_capabilities_without_provider_selection(self):
        cli = PLUGIN_ROOT / "scripts" / "check_dependencies.py"
        help_result = subprocess.run(
            [sys.executable, str(cli), "--help"],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("--capability", help_result.stdout)
        self.assertNotIn("--methodology-profile", help_result.stdout)
        self.assertNotIn("--roadmap-provider", help_result.stdout)
        self.assertNotIn("--provider-source", help_result.stdout)
        self.assertNotIn("roadmap-lifecycle", help_result.stdout)

    def test_project_skill_plan_copies_only_triggered_matt_skills(self):
        from workflow_project_skill_install import ensure_project_local_skills

        repo = Path(tempfile.mkdtemp(prefix="devflow-activation-"))
        codex_home = Path(tempfile.mkdtemp(prefix="devflow-activation-home-"))
        report = ensure_project_local_skills(
            repo,
            PLUGIN_ROOT,
            codex_home,
            dry_run=True,
            triggered_capabilities={"test-first-execution"},
            openspec_generation_planned=True,
        )
        matt_items = [
            item
            for item in report["items"]
            if item.get("sourceKind") == "mattpocock-skills"
        ]

        self.assertEqual([item["skill"] for item in matt_items], ["tdd"])
        self.assertEqual(matt_items[0]["status"], "would-copy")
        self.assertTrue(
            matt_items[0]["source"].endswith("vendor/mattpocock-skills/tdd")
        )
        self.assertFalse((repo / ".agents" / "skills" / "tdd").exists())

    def test_layout_migration_scope_contains_only_triggered_matt_skills(self):
        from workflow_project_activation import managed_project_skills

        untriggered = managed_project_skills(set())
        triggered = managed_project_skills({"test-first-execution"})

        self.assertNotIn("tdd", untriggered)
        self.assertNotIn("domain-modeling", untriggered)
        self.assertIn("tdd", triggered)
        self.assertNotIn("domain-modeling", triggered)

    def test_matt_legacy_symlink_is_never_promoted_to_official_route(self):
        from workflow_project_skill_install import install_matt_project_skill
        from workflow_project_skill_paths import migrate_project_skill_layout

        repo = Path(tempfile.mkdtemp(prefix="devflow-matt-legacy-route-"))
        outside = Path(tempfile.mkdtemp(prefix="devflow-matt-legacy-outside-")) / "tdd"
        shutil.copytree(
            PLUGIN_ROOT / "vendor" / "mattpocock-skills" / "tdd",
            outside,
        )
        legacy = repo / ".codex" / "skills" / "tdd"
        legacy.parent.mkdir(parents=True)
        legacy.symlink_to(outside, target_is_directory=True)

        migration = migrate_project_skill_layout(
            repo,
            ["tdd"],
            dry_run=False,
            authoritative_source_skills={"tdd"},
        )
        official = repo / ".agents" / "skills" / "tdd"

        self.assertTrue(migration["ok"], migration)
        self.assertEqual(
            migration["items"][0]["status"],
            "authoritative_source_install_required",
        )
        self.assertFalse(official.exists())

        installed = install_matt_project_skill(
            repo,
            "tdd",
            PLUGIN_ROOT / "vendor" / "mattpocock-skills" / "tdd",
        )
        self.assertTrue(installed["ok"], installed)
        self.assertTrue(official.is_dir())
        self.assertFalse(official.is_symlink())

    def test_matt_refresh_retains_backup_when_rollback_restore_fails(self):
        from workflow_project_skill_install import install_matt_project_skill

        repo = Path(tempfile.mkdtemp(prefix="devflow-matt-rollback-retained-"))
        target = repo / ".agents" / "skills" / "tdd"
        target.mkdir(parents=True)
        original = "original project skill\n"
        (target / "SKILL.md").write_text(original)
        source = PLUGIN_ROOT / "vendor" / "mattpocock-skills" / "tdd"
        real_replace = Path.replace

        def fail_promotion_and_restore(path, destination):
            if path.name.startswith(".devflow-matt-stage-tdd-"):
                raise OSError("promotion fixture")
            if path.name.startswith(".devflow-matt-backup-tdd-"):
                raise OSError("restore fixture")
            return real_replace(path, destination)

        with mock.patch.object(Path, "replace", new=fail_promotion_and_restore):
            report = install_matt_project_skill(
                repo,
                "tdd",
                source,
                refresh_existing=True,
            )

        self.assertFalse(report["ok"], report)
        self.assertEqual(report["status"], "transaction-rollback-failed")
        self.assertEqual(report["rollbackStatus"], "backup-retained")
        self.assertIn("restore fixture", report["rollbackError"])
        backup = repo / report["retainedBackupPath"]
        self.assertTrue(backup.is_dir(), report)
        self.assertEqual((backup / "SKILL.md").read_text(), original)
        self.assertFalse(target.exists())
        self.assertEqual(
            list((repo / ".agents" / "skills").glob(".devflow-matt-stage-*")),
            [],
        )

    def test_activation_cli_has_one_path_and_plans_only_triggered_matt_copy(self):
        cli = PLUGIN_ROOT / "scripts" / "activate_project_dependencies.py"
        help_result = subprocess.run(
            [sys.executable, str(cli), "--help"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        for option in [
            "--methodology-profile",
            "--roadmap-provider",
            "--provider-source",
            "--persist-provider-selection",
            "--deactivate-provider",
            "--authorize-provider-cleanup",
            "--provider-cleanup-plan",
        ]:
            self.assertNotIn(option, help_result.stdout)

        repo = Path(tempfile.mkdtemp(prefix="devflow-activation-cli-"))
        codex_home = Path(tempfile.mkdtemp(prefix="devflow-activation-cli-home-"))
        (codex_home / "config.toml").write_text("")
        (repo / ".dev-flow.json").write_text(
            json.dumps({"workflow": {"mode": "full-openspec"}}) + "\n"
        )
        write_official_openspec_skills(repo)
        result = subprocess.run(
            [
                sys.executable,
                str(cli),
                "--repo",
                str(repo),
                "--plugin-root",
                str(PLUGIN_ROOT),
                "--codex-home",
                str(codex_home),
                "--dry-run",
                "--skip-official-installs",
                "--capability",
                "test-first-execution",
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        matt_items = [
            item
            for item in report["local_skills"]["items"]
            if item.get("sourceKind") == "mattpocock-skills"
        ]
        self.assertEqual([item["skill"] for item in matt_items], ["tdd"])
        serialized = json.dumps(report, sort_keys=True).lower()
        self.assertNotIn("superpowers", serialized)
        self.assertNotIn("gsd", serialized)

    def test_scaffold_writes_minimal_workflow_configuration(self):
        from workflow_scaffold import scaffold_workflow

        repo = Path(tempfile.mkdtemp(prefix="devflow-scaffold-config-"))
        report = scaffold_workflow(repo, mode="brownfield")
        config = json.loads((repo / ".dev-flow.json").read_text())

        self.assertIn(".dev-flow.json", report["written"])
        self.assertEqual(
            config,
            {"projectContract": 2, "workflow": {"mode": "full-openspec"}},
        )

    def test_state_and_verification_contract_are_roadmap_free(self):
        from workflow_state import default_state_values, merged_gates, render_state

        values = default_state_values("brownfield", "example-change")
        gates = merged_gates({}, {})
        rendered = render_state(values).lower()

        for forbidden in ["gsd", "roadmap", "methodology_profile", "provider"]:
            self.assertNotIn(forbidden, json.dumps(values, sort_keys=True).lower())
            self.assertNotIn(forbidden, json.dumps(gates, sort_keys=True).lower())
            self.assertNotIn(forbidden, rendered)

        cli = PLUGIN_ROOT / "scripts" / "record_verification.py"
        help_result = subprocess.run(
            [sys.executable, str(cli), "--help"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertNotIn("--gsd-change", help_result.stdout)
        self.assertNotIn("--gsd-phase", help_result.stdout)

    def test_project_migration_cli_has_no_legacy_apply_or_runtime_import(self):
        cli = PLUGIN_ROOT / "scripts" / "plugin_project_migration.py"
        help_result = subprocess.run(
            [sys.executable, str(cli), "--help"],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertNotIn("--apply-provider-files", help_result.stdout)
        self.assertNotIn("--rollback-manifest", help_result.stdout)
        source = cli.read_text()
        self.assertNotIn("workflow_provider_", source)
        self.assertNotIn("legacy_workflow_config", source)

    def test_updater_has_no_provider_profile_or_removed_dependency_path(self):
        cli = PLUGIN_ROOT / "scripts" / "codex_auto_update_plugins_skills.py"
        help_result = subprocess.run(
            [sys.executable, str(cli), "--help"],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        source = cli.read_text().lower()
        for forbidden in [
            "workflow_provider_",
            "superpowers_update_result",
            "strict-superpowers",
            "gsd_core_update_command",
            "installed_gsd_core_version",
            '"gsd-core"',
        ]:
            self.assertNotIn(forbidden, source)
        self.assertNotIn("gsd", help_result.stdout.lower())
        self.assertNotIn("superpowers", help_result.stdout.lower())

    def test_release_runtime_verifies_matt_contract_without_provider_defaults(self):
        from verify_release_runtime import check_methodology_contract

        checks = []
        check_methodology_contract(PLUGIN_ROOT, checks)

        self.assertTrue(checks)
        self.assertTrue(all(check["ok"] for check in checks), checks)
        serialized = json.dumps(checks, sort_keys=True).lower()
        self.assertNotIn("provider", serialized)
        self.assertNotIn("superpowers", serialized)
        self.assertNotIn("gsd", serialized)

    def test_release_and_stop_runtime_have_no_removed_provider_aliases(self):
        for relative in [
            "scripts/release_promotion_gate.py",
            "scripts/workflow_release_sync.py",
            "scripts/devflow_stop_hook.py",
        ]:
            source = (PLUGIN_ROOT / relative).read_text().lower()
            self.assertNotIn("workflow_provider_", source)
            self.assertNotIn("superpowers_completion", source)

    def test_retired_provider_surfaces_are_absent_from_active_source(self):
        removed_paths = [
            "scripts/superpowers_artifact_mapping.py",
            "scripts/workflow_superpowers_gates.py",
            "scripts/workflow_roadmap_provider.py",
            "scripts/workflow_provider_registry.py",
            "docs/provider_profiles.json",
            "docs/superpowers_gate_matrix.json",
            "assets/templates/ROADMAP.md.template",
            "assets/templates/PHASE_CONTEXT.md.template",
            "assets/templates/PHASE_PLAN.md.template",
            "assets/templates/PHASE_SUMMARY.md.template",
        ]
        for relative in removed_paths:
            with self.subTest(path=relative):
                self.assertFalse((PLUGIN_ROOT / relative).exists())

        for relative in ["fixtures/provider-profiles", "evals/provider-profiles"]:
            root = PLUGIN_ROOT / relative
            self.assertFalse(
                any(path.is_file() or path.is_symlink() for path in root.rglob("*")),
                relative,
            )

        retired_module_identifiers = [
            "workflow_provider_",
            "workflow_roadmap_provider",
            "workflow_superpowers_gates",
            "archive_roadmap_binding",
            "superpowers_artifact_mapping",
            "aggregate_provider_benchmark",
            "run_provider_benchmark",
        ]
        for path in (PLUGIN_ROOT / "scripts").glob("*.py"):
            if path.name == "legacy_workflow_config.py":
                continue
            source = path.read_text().lower()
            for identifier in retired_module_identifiers:
                self.assertNotIn(identifier, source, path.name)

        guidance_paths = [PLUGIN_ROOT / "README.md"]
        guidance_paths.extend((PLUGIN_ROOT / "skills").rglob("*.md"))
        guidance_paths.extend((PLUGIN_ROOT / "assets" / "templates").rglob("*"))
        forbidden_guidance = [
            "strict-superpowers",
            "lean-matt",
            "methodology_profile",
            "roadmap_provider",
            "roadmap provider",
            "methodology profile",
            "superpowers:",
            "gsd-",
        ]
        for path in guidance_paths:
            if not path.is_file():
                continue
            text = path.read_text().lower()
            for phrase in forbidden_guidance:
                self.assertNotIn(phrase, text, str(path.relative_to(PLUGIN_ROOT)))

    def test_legacy_names_exist_only_in_explicit_inspector_test_and_history_allowlist(self):
        legacy_name = re.compile(
            r"(?:"
            r"superpowers|"
            r"(?<![a-z0-9])gsd(?![a-z0-9])|"
            r"methodology[_ -]?profile|"
            r"roadmap[_ -]?provider|"
            r"provider[_ -]?(?:profile|selector)s?|"
            r"roadmap[_ -]?bindings?|"
            r"pre[_ -]?next[_ -]?phase"
            r")",
            re.IGNORECASE,
        )
        allowed = {
            ".planning/checkpoints/2026-05-23-verification_passed-integrate-ai-native-planning.md",
            "docs/history/2026-05-18-audit-context-tools-design.md",
            "docs/history/2026-05-18-audit-context-tools-plan.md",
            "openspec/changes/integrate-ai-native-planning/design.md",
            "openspec/changes/integrate-ai-native-planning/proposal.md",
            "openspec/changes/integrate-ai-native-planning/specs/integrate-ai-native-planning/spec.md",
            "openspec/changes/integrate-ai-native-planning/tasks.md",
            "scripts/legacy_workflow_config.py",
            "scripts/workflow_mode_routing.py",
            "tests/test_archive_policy.py",
            "tests/test_legacy_workflow_config.py",
            "tests/test_methodology.py",
            "tests/test_packaged_runtime.py",
            "tests/test_project_orchestrator.py",
            "tests/test_release_smoke.py",
            "tests/test_runtime_gates.py",
        }
        actual = set()
        for path in PLUGIN_ROOT.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            try:
                source = path.read_text()
            except UnicodeDecodeError:
                continue
            if legacy_name.search(source):
                actual.add(path.relative_to(PLUGIN_ROOT).as_posix())

        self.assertEqual(actual, allowed)


if __name__ == "__main__":
    unittest.main()
