import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import plugin_project_migration as migration_module

from plugin_project_migration import (
    apply_project_migrations,
    migration_reminder,
    project_migration_sync_result,
    sync_project_migrations,
)

LEGACY_PROFILE_KEY = "methodology" + "_profile"


class PluginProjectMigrationTests(unittest.TestCase):
    def make_repo(self):
        repo = Path(tempfile.mkdtemp(prefix="plugin-migration-repo-"))
        (repo / "AGENTS.md").write_text("# Project Rules\n")
        (repo / "openspec").mkdir()
        (repo / "openspec" / "config.yaml").write_text("schema: spec-driven\n")
        (repo / ".planning").mkdir()
        (repo / ".planning" / "STATE.md").write_text(
            "---\nworkflow_version: 0.3.0\ncurrent_stage: planning\n---\n# State\n"
        )
        return repo

    def make_plugin_root(self, version="1.0.0", root=None):
        plugin = Path(root) if root is not None else Path(tempfile.mkdtemp(prefix="plugin-migration-plugin-"))
        (plugin / ".codex-plugin").mkdir(parents=True)
        (plugin / ".codex-plugin" / "plugin.json").write_text(
            json.dumps({"name": "dev-flow", "version": version}) + "\n"
        )
        (plugin / ".codex-plugin" / "project-migration.json").write_text(
            json.dumps(
                {
                    "schemaVersion": "2.0",
                    "engineSchemaVersion": "2.0",
                    "plugin": "dev-flow",
                    "projectSchema": {"head": 1, "minimumSupported": 0},
                    "configTargets": {"1": "assets/project-refresh/config-v1.json"},
                    "migrationSteps": [
                        {
                            "id": "legacy-selection-v0-to-v1",
                            "from": 0,
                            "to": 1,
                            "authorization": "workflow-config-migration",
                            "configTarget": 1,
                        }
                    ],
                    "refreshContract": {"revision": 1, "impact": "changed", "trackedInputs": []},
                    "projectLocalSkills": ["project-orchestrator", "plugin-project-migration"],
                    "managedFiles": [
                        "ENGINEERING_POLICY.md",
                        "EVIDENCE_TEMPLATE.md",
                        "REVIEW_CHECKLIST.md",
                        "TASK_LEDGER.md",
                    ],
                    "agentsGuidance": {
                        "activePath": "AGENTS.md",
                        "candidatePath": "AGENTS.md.generated",
                        "template": "assets/templates/AGENTS.md.template",
                    },
                }
            )
            + "\n"
        )
        config = plugin / "assets" / "project-refresh" / "config-v1.json"
        config.parent.mkdir(parents=True)
        config.write_text('{\n  "workflow": {\n    "mode": "full-openspec"\n  }\n}\n')
        template_root = plugin / "assets" / "templates"
        template_root.mkdir(parents=True)
        for name in [
            "AGENTS.md.template",
            "ENGINEERING_POLICY.md.template",
            "EVIDENCE_TEMPLATE.md.template",
            "REVIEW_CHECKLIST.md.template",
            "TASK_LEDGER.md.template",
        ]:
            (template_root / name).write_bytes((PLUGIN_ROOT / "assets" / "templates" / name).read_bytes())
        self.write_skill(plugin / "skills" / "project-orchestrator" / "SKILL.md")
        self.write_skill(plugin / "skills" / "plugin-project-migration" / "SKILL.md")
        return plugin

    def write_marketplace(self, repo, plugin):
        marketplace = repo / ".agents" / "plugins" / "marketplace.json"
        marketplace.parent.mkdir(parents=True, exist_ok=True)
        marketplace.write_text(
            json.dumps(
                {
                    "plugins": [
                        {
                            "name": "dev-flow",
                            "source": {
                                "source": "local",
                                "path": str(plugin),
                            },
                        }
                    ]
                }
            )
            + "\n"
        )

    def make_codex_home(self):
        return Path(tempfile.mkdtemp(prefix="plugin-migration-home-"))

    def write_skill(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\nname: {path.parent.name}\ndescription: fixture\n---\n")

    def snapshot_project_files(self, repo):
        watched = [
            repo / "AGENTS.md",
            repo / "openspec" / "config.yaml",
            repo / ".planning" / "STATE.md",
        ]
        return {path.relative_to(repo).as_posix(): path.read_text() for path in watched}

    def snapshot_tree(self, repo):
        result = {}
        for path in sorted(repo.rglob("*")):
            relative = path.relative_to(repo).as_posix()
            if path.is_symlink():
                result[relative] = f"symlink:{path.readlink()}"
            elif path.is_file():
                result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
            elif path.is_dir():
                result[relative] = "directory"
        return result

    def test_sync_reports_missing_state_without_mutating_project_files(self):
        repo = self.make_repo()
        plugin = self.make_plugin_root(version="1.2.0")
        before = self.snapshot_project_files(repo)

        report = sync_project_migrations(repo=repo, plugin_root=plugin, codex_home=self.make_codex_home())

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["status"], "migration_pending")
        self.assertEqual(report["plugins"][0]["name"], "dev-flow")
        self.assertEqual(report["plugins"][0]["state"], "missing")
        self.assertEqual(report["plugins"][0]["runtimeVersion"], "1.2.0")
        self.assertEqual(self.snapshot_project_files(repo), before)
        self.assertFalse((repo / ".dev-flow" / "plugin-project-migration" / "state.json").exists())
        control = report["plugins"][0]["controlPlane"]
        self.assertEqual(control["status"], "missing")
        self.assertIn("TASK_LEDGER.md", control["missingFiles"])
        self.assertIn("REVIEW_CHECKLIST.md", control["missingFiles"])
        self.assertFalse((repo / ".planning" / "devflow").exists())

    def test_migration_audit_writers_reject_symlinked_devflow_namespace(self):
        repo = self.make_repo()
        plugin = self.make_plugin_root(version="1.2.0")
        outside = Path(tempfile.mkdtemp(prefix="plugin-migration-outside-"))
        (repo / ".planning" / "devflow").symlink_to(outside, target_is_directory=True)

        with self.assertRaises(migration_module.PlanningOwnershipError):
            sync_project_migrations(
                repo=repo,
                plugin_root=plugin,
                codex_home=self.make_codex_home(),
                write_report=True,
            )
        with self.assertRaises(migration_module.PlanningOwnershipError):
            migration_module.append_history(repo, "dev-flow", "planned", [])

        self.assertFalse((outside / "plugin-project-migration" / "reports" / "latest.json").exists())
        self.assertFalse((outside / "plugin-project-migration" / "migration-history.jsonl").exists())

    def test_project_migration_manifest_includes_dev_flow_refresh_skill(self):
        manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "project-migration.json").read_text())

        self.assertIn("dev-flow-refresh", manifest["projectLocalSkills"])

    def test_sync_reports_stale_project_local_skill_links(self):
        repo = self.make_repo()
        old_plugin = self.make_plugin_root(version="1.0.0")
        new_plugin = self.make_plugin_root(version="1.1.0")
        target = repo / ".agents" / "skills" / "project-orchestrator"
        target.parent.mkdir(parents=True)
        target.symlink_to(old_plugin / "skills" / "project-orchestrator", target_is_directory=True)

        report = sync_project_migrations(repo=repo, plugin_root=new_plugin, codex_home=self.make_codex_home())

        stale = report["plugins"][0]["staleProjectSkills"]
        self.assertEqual(len(stale), 1, report)
        self.assertEqual(stale[0]["skill"], "project-orchestrator")
        self.assertEqual(stale[0]["target"], str(target.parent.resolve() / target.name))
        self.assertEqual(stale[0]["source"], str((new_plugin / "skills" / "project-orchestrator").resolve()))
        self.assertEqual(target.resolve(), (old_plugin / "skills" / "project-orchestrator").resolve())

    def test_sync_reports_legacy_skill_layout_and_dry_run_command(self):
        repo = self.make_repo()
        plugin = self.make_plugin_root(version="1.1.0")
        legacy = repo / ".codex" / "skills" / "project-orchestrator" / "SKILL.md"
        legacy.parent.mkdir(parents=True)
        legacy.write_text("---\nname: project-orchestrator\ndescription: legacy\n---\n")

        report = sync_project_migrations(repo=repo, plugin_root=plugin, codex_home=self.make_codex_home())

        skill_layout = report["plugins"][0]["skillLayout"]
        project_orchestrator = next(item for item in skill_layout["items"] if item["skill"] == "project-orchestrator")
        self.assertEqual(skill_layout["status"], "legacy_detected")
        self.assertEqual(project_orchestrator["status"], "legacy_detected")
        self.assertIn("--migrate-official-skill-layout", " ".join(skill_layout["dryRunCommand"]))
        self.assertIn("--dry-run", skill_layout["dryRunCommand"])

    def test_apply_refreshes_safe_skill_links_and_writes_audit_files(self):
        repo = self.make_repo()
        old_plugin = self.make_plugin_root(version="1.0.0")
        new_plugin = self.make_plugin_root(version="1.1.0")
        target = repo / ".agents" / "skills" / "project-orchestrator"
        target.parent.mkdir(parents=True)
        target.symlink_to(old_plugin / "skills" / "project-orchestrator", target_is_directory=True)

        report = apply_project_migrations(repo=repo, plugin_root=new_plugin, codex_home=self.make_codex_home())

        runtime = repo / ".planning" / "devflow" / "plugin-project-migration"
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["status"], "applied")
        self.assertEqual(target.resolve(), (new_plugin / "skills" / "project-orchestrator").resolve())
        self.assertTrue((runtime / "state.json").exists())
        self.assertTrue((runtime / "migration-history.jsonl").exists())
        self.assertTrue((runtime / "reports" / "latest.json").exists())
        state = json.loads((runtime / "state.json").read_text())
        self.assertEqual(state["plugins"]["dev-flow"]["version"], "1.1.0")
        for filename in [
            "ENGINEERING_POLICY.md",
            "TASK_LEDGER.md",
            "EVIDENCE_TEMPLATE.md",
            "REVIEW_CHECKLIST.md",
        ]:
            self.assertTrue((repo / filename).exists(), filename)
        control_changes = [item for item in report["plugins"][0]["changes"] if item["kind"] == "control-plane-file"]
        self.assertEqual({item["path"] for item in control_changes}, {
            "ENGINEERING_POLICY.md",
            "TASK_LEDGER.md",
            "EVIDENCE_TEMPLATE.md",
            "REVIEW_CHECKLIST.md",
        })
        self.assertEqual(report["refreshEngine"]["status"], "applied_incomplete")
        self.assertTrue(Path(report["refreshEngine"]["receiptPath"]).is_file())
        self.assertFalse((repo / ".dev-flow.json").exists())

    def test_apply_refuses_to_replace_non_symlink_skill_target(self):
        repo = self.make_repo()
        plugin = self.make_plugin_root(version="1.1.0")
        self.write_skill(repo / ".agents" / "skills" / "project-orchestrator" / "SKILL.md")

        before = self.snapshot_tree(repo)
        report = apply_project_migrations(repo=repo, plugin_root=plugin, codex_home=self.make_codex_home())

        conflicts = report["plugins"][0]["conflicts"]
        self.assertFalse(report["ok"], report)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(conflicts[0]["reason"], "target-exists-not-symlink")
        self.assertEqual(self.snapshot_tree(repo), before)

    def test_legacy_apply_never_claims_workflow_configuration_authority(self):
        repo = self.make_repo()
        (repo / ".dev-flow.json").write_text(
            json.dumps({LEGACY_PROFILE_KEY: "private-legacy-value"}) + "\n"
        )
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "DevFlow Tests"], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "config", "user.email", "devflow-tests@example.invalid"],
            check=True,
        )
        subprocess.run(["git", "-C", str(repo), "add", ".dev-flow.json"], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "legacy config"], check=True)
        plugin = self.make_plugin_root(version="1.2.0")

        report = apply_project_migrations(repo=repo, plugin_root=plugin, codex_home=self.make_codex_home())

        self.assertEqual(
            json.loads((repo / ".dev-flow.json").read_text()),
            {LEGACY_PROFILE_KEY: "private-legacy-value"},
        )
        refresh = report["refreshEngine"]
        self.assertEqual(refresh["status"], "applied_incomplete")
        self.assertIn("workflow-config-migration", refresh["remainingAuthorizations"])

    def test_no_subcommand_json_cli_remains_a_read_only_compatible_report(self):
        repo = self.make_repo()
        plugin = self.make_plugin_root(version="1.2.0")
        before = self.snapshot_tree(repo)

        completed = subprocess.run(
            [
                sys.executable,
                str(PLUGIN_ROOT / "scripts" / "plugin_project_migration.py"),
                "--repo",
                str(repo),
                "--plugin-root",
                str(plugin),
                "--codex-home",
                str(self.make_codex_home()),
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        report = json.loads(completed.stdout)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(report["status"], "migration_pending")
        self.assertIn("plugins", report)
        self.assertIn("recommendation", report)
        self.assertEqual(self.snapshot_tree(repo), before)

    def test_hook_reminder_is_short_and_sync_only(self):
        repo = self.make_repo()
        plugin = self.make_plugin_root(version="1.2.0")
        before = self.snapshot_project_files(repo)

        message = migration_reminder(repo=repo, plugin_root=plugin, codex_home=self.make_codex_home())

        self.assertIn("plugin-project-migration", message)
        self.assertIn("dev-flow", message)
        self.assertEqual(self.snapshot_project_files(repo), before)

    def test_hook_reminder_prefers_repo_marketplace_source_over_cache_root(self):
        repo = self.make_repo()
        source_plugin = self.make_plugin_root(version="1.2.0")
        cache_plugin = self.make_plugin_root(version="1.2.0")
        codex_home = self.make_codex_home()
        self.write_marketplace(repo, source_plugin)
        apply_project_migrations(repo=repo, plugin_root=source_plugin, codex_home=codex_home)

        message = migration_reminder(repo=repo, plugin_root=cache_plugin, codex_home=codex_home)

        self.assertEqual(message, "")

    def test_source_repo_accepts_dev_skill_links_with_release_marketplace_source(self):
        repo = self.make_repo()
        release_plugin = self.make_plugin_root(version="1.2.0", root=repo / "plugins" / "dev-flow")
        dev_plugin = self.make_plugin_root(version="1.2.0", root=repo / "dev" / "plugins" / "dev-flow")
        codex_home = self.make_codex_home()
        self.write_marketplace(repo, release_plugin)
        apply_project_migrations(repo=repo, plugin_root=release_plugin, codex_home=codex_home)
        target = repo / ".agents" / "skills" / "project-orchestrator"
        target.unlink()
        target.symlink_to(dev_plugin / "skills" / "project-orchestrator", target_is_directory=True)

        report = sync_project_migrations(repo=repo, plugin_root=release_plugin, codex_home=codex_home)

        self.assertEqual(report["status"], "current", report)
        self.assertEqual(report["plugins"][0]["staleProjectSkills"], [])
        self.assertEqual(target.resolve(), (dev_plugin / "skills" / "project-orchestrator").resolve())

    def test_consumer_repo_reports_dev_skill_links_as_stale(self):
        repo = self.make_repo()
        release_plugin = self.make_plugin_root(version="1.2.0")
        dev_plugin = self.make_plugin_root(version="1.2.0")
        self.write_marketplace(repo, release_plugin)
        apply_project_migrations(repo=repo, plugin_root=release_plugin, codex_home=self.make_codex_home())
        target = repo / ".agents" / "skills" / "project-orchestrator"
        target.unlink()
        target.symlink_to(dev_plugin / "skills" / "project-orchestrator", target_is_directory=True)

        report = sync_project_migrations(repo=repo, plugin_root=release_plugin, codex_home=self.make_codex_home())

        stale = report["plugins"][0]["staleProjectSkills"]
        self.assertEqual(report["status"], "migration_pending")
        self.assertEqual(len(stale), 1, report)
        self.assertEqual(stale[0]["skill"], "project-orchestrator")
        self.assertEqual(stale[0]["source"], str((release_plugin / "skills" / "project-orchestrator").resolve()))

    def test_updater_result_uses_project_migration_sync_kind(self):
        repo = self.make_repo()
        plugin = self.make_plugin_root(version="1.2.0")

        result = project_migration_sync_result(repo=repo, plugin_root=plugin, codex_home=self.make_codex_home())

        self.assertEqual(result["kind"], "project-migration-sync")
        self.assertEqual(result["name"], "dev-flow")
        self.assertEqual(result["status"], "migration-pending")
        self.assertIn("plugin-project-migration", result["detail"])

    def test_updater_result_reports_legacy_layout_dry_run_command(self):
        repo = self.make_repo()
        plugin = self.make_plugin_root(version="1.2.0")
        legacy = repo / ".codex" / "skills" / "project-orchestrator" / "SKILL.md"
        legacy.parent.mkdir(parents=True)
        legacy.write_text("---\nname: project-orchestrator\ndescription: legacy\n---\n")

        result = project_migration_sync_result(repo=repo, plugin_root=plugin, codex_home=self.make_codex_home())

        self.assertEqual(result["skillLayoutStatus"], "legacy_detected")
        self.assertIn("--migrate-official-skill-layout", result["detail"])
        self.assertIn("--dry-run", result["skillLayoutDryRunCommand"])

    def test_updater_result_explains_blocked_project_migration(self):
        report = {
            "status": "blocked",
            "plugins": [
                {
                    "name": "dev-flow",
                    "skillLayout": {"status": "current"},
                    "conflicts": [{"reason": "target-exists-not-symlink"}],
                }
            ],
        }
        with mock.patch.object(migration_module, "sync_project_migrations", return_value=report):
            result = project_migration_sync_result(
                repo=self.make_repo(),
                plugin_root=self.make_plugin_root(),
                codex_home=self.make_codex_home(),
            )

        self.assertEqual(result["status"], "blocked")
        self.assertIn("target-exists-not-symlink", result["detail"])


if __name__ == "__main__":
    unittest.main()
