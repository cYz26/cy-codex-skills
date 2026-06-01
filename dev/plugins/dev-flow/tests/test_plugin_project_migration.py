import json
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from plugin_project_migration import (
    apply_project_migrations,
    migration_reminder,
    project_migration_sync_result,
    sync_project_migrations,
)


class PluginProjectMigrationTests(unittest.TestCase):
    def make_repo(self):
        repo = Path(tempfile.mkdtemp(prefix="plugin-migration-repo-"))
        (repo / "AGENTS.md").write_text("# Project Rules\n")
        (repo / "openspec").mkdir()
        (repo / "openspec" / "config.yaml").write_text("schema: spec-driven\n")
        (repo / ".planning").mkdir()
        (repo / ".planning" / "STATE.md").write_text("# State\n")
        return repo

    def make_plugin_root(self, version="1.0.0"):
        plugin = Path(tempfile.mkdtemp(prefix="plugin-migration-plugin-"))
        (plugin / ".codex-plugin").mkdir()
        (plugin / ".codex-plugin" / "plugin.json").write_text(
            json.dumps({"name": "dev-flow", "version": version}) + "\n"
        )
        (plugin / ".codex-plugin" / "project-migration.json").write_text(
            json.dumps(
                {
                    "schemaVersion": "1.0",
                    "plugin": "dev-flow",
                    "projectLocalSkills": ["project-orchestrator", "plugin-project-migration"],
                    "managedFiles": [],
                }
            )
            + "\n"
        )
        self.write_skill(plugin / "skills" / "project-orchestrator" / "SKILL.md")
        self.write_skill(plugin / "skills" / "plugin-project-migration" / "SKILL.md")
        return plugin

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

    def test_sync_reports_stale_project_local_skill_links(self):
        repo = self.make_repo()
        old_plugin = self.make_plugin_root(version="1.0.0")
        new_plugin = self.make_plugin_root(version="1.1.0")
        target = repo / ".codex" / "skills" / "project-orchestrator"
        target.parent.mkdir(parents=True)
        target.symlink_to(old_plugin / "skills" / "project-orchestrator", target_is_directory=True)

        report = sync_project_migrations(repo=repo, plugin_root=new_plugin, codex_home=self.make_codex_home())

        stale = report["plugins"][0]["staleProjectSkills"]
        self.assertEqual(len(stale), 1, report)
        self.assertEqual(stale[0]["skill"], "project-orchestrator")
        self.assertEqual(stale[0]["target"], str(target.parent.resolve() / target.name))
        self.assertEqual(stale[0]["source"], str((new_plugin / "skills" / "project-orchestrator").resolve()))
        self.assertEqual(target.resolve(), (old_plugin / "skills" / "project-orchestrator").resolve())

    def test_apply_refreshes_safe_skill_links_and_writes_audit_files(self):
        repo = self.make_repo()
        old_plugin = self.make_plugin_root(version="1.0.0")
        new_plugin = self.make_plugin_root(version="1.1.0")
        target = repo / ".codex" / "skills" / "project-orchestrator"
        target.parent.mkdir(parents=True)
        target.symlink_to(old_plugin / "skills" / "project-orchestrator", target_is_directory=True)

        report = apply_project_migrations(repo=repo, plugin_root=new_plugin, codex_home=self.make_codex_home())

        runtime = repo / ".dev-flow" / "plugin-project-migration"
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["status"], "applied")
        self.assertEqual(target.resolve(), (new_plugin / "skills" / "project-orchestrator").resolve())
        self.assertTrue((runtime / "state.json").exists())
        self.assertTrue((runtime / "migration-history.jsonl").exists())
        self.assertTrue((runtime / "reports" / "latest.json").exists())
        state = json.loads((runtime / "state.json").read_text())
        self.assertEqual(state["plugins"]["dev-flow"]["version"], "1.1.0")

    def test_apply_refuses_to_replace_non_symlink_skill_target(self):
        repo = self.make_repo()
        plugin = self.make_plugin_root(version="1.1.0")
        self.write_skill(repo / ".codex" / "skills" / "project-orchestrator" / "SKILL.md")

        report = apply_project_migrations(repo=repo, plugin_root=plugin, codex_home=self.make_codex_home())

        conflicts = report["plugins"][0]["conflicts"]
        self.assertFalse(report["ok"], report)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(conflicts[0]["reason"], "target-exists-not-symlink")

    def test_hook_reminder_is_short_and_sync_only(self):
        repo = self.make_repo()
        plugin = self.make_plugin_root(version="1.2.0")
        before = self.snapshot_project_files(repo)

        message = migration_reminder(repo=repo, plugin_root=plugin, codex_home=self.make_codex_home())

        self.assertIn("plugin-project-migration", message)
        self.assertIn("dev-flow", message)
        self.assertEqual(self.snapshot_project_files(repo), before)

    def test_updater_result_uses_project_migration_sync_kind(self):
        repo = self.make_repo()
        plugin = self.make_plugin_root(version="1.2.0")

        result = project_migration_sync_result(repo=repo, plugin_root=plugin, codex_home=self.make_codex_home())

        self.assertEqual(result["kind"], "project-migration-sync")
        self.assertEqual(result["name"], "dev-flow")
        self.assertEqual(result["status"], "migration-pending")
        self.assertIn("plugin-project-migration", result["detail"])


if __name__ == "__main__":
    unittest.main()
