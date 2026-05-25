import sys
import tempfile
import unittest
import importlib
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from workflow_context_tools import apply_context_tool_actions, audit_context_tools


class ContextToolAuditTests(unittest.TestCase):

    def make_codex_home(self):
        home = Path(tempfile.mkdtemp(prefix="cpo-context-home-"))
        config = home / "config.toml"
        config.write_text(
            "\n".join(
                [
                    'model = "gpt-5"',
                    "",
                    '[plugins."superpowers@openai-curated"]',
                    "enabled = true",
                    "",
                    '[plugins."unused-plugin@local"]',
                    "enabled = true",
                ]
            )
            + "\n"
        )
        self.write_skill(home / "skills" / "test-driven-development" / "SKILL.md")
        self.write_skill(
            home
            / "plugins"
            / "cache"
            / "openai-curated"
            / "build-web-apps"
            / "local"
            / "skills"
            / "react-best-practices"
            / "SKILL.md",
            "react-best-practices",
        )
        return home

    def make_react_repo(self):
        repo = Path(tempfile.mkdtemp(prefix="cpo-context-repo-"))
        (repo / "package.json").write_text('{"dependencies":{"react":"latest","vite":"latest"}}\n')
        self.write_skill(repo / ".codex" / "skills" / "project-orchestrator" / "SKILL.md")
        return repo

    def write_skill(self, path, name=None):
        path.parent.mkdir(parents=True, exist_ok=True)
        skill_name = name or path.parent.name
        path.write_text(f"---\nname: {skill_name}\ndescription: fixture\n---\n")

    def test_context_tool_modules_are_split_behind_stable_facade(self):
        facade = importlib.import_module("workflow_context_tools")
        expected_exports = {"audit_context_tools", "apply_context_tool_actions"}
        self.assertTrue(expected_exports.issubset(set(facade.__all__)))
        for module_name in [
            "workflow_context_inventory",
            "workflow_context_catalog",
            "workflow_context_recommendations",
            "workflow_context_actions",
        ]:
            module = importlib.import_module(module_name)
            self.assertIsNotNone(module, module_name)

    def test_audit_reports_global_pressure_and_project_relevant_installed_skills(self):
        codex_home = self.make_codex_home()
        repo = self.make_react_repo()

        report = audit_context_tools(codex_home=codex_home, repo=repo)

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["contextPressure"], "high")
        self.assertIn("javascript", report["projectSignals"])
        self.assertIn("react", report["projectSignals"])
        global_plugins = {item["key"] for item in report["inventory"]["globalPlugins"]}
        self.assertIn("superpowers@openai-curated", global_plugins)
        global_skills = {item["name"] for item in report["inventory"]["globalSkills"]}
        self.assertIn("test-driven-development", global_skills)
        action_ids = {item["id"] for item in report["actions"]}
        self.assertIn("disable-global-plugin-superpowers-openai-curated", action_ids)
        self.assertIn("disable-global-plugin-unused-plugin-local", action_ids)
        self.assertIn("disable-global-skill-test-driven-development", action_ids)
        self.assertIn("install-project-skill-react-best-practices", action_ids)

    def test_apply_actions_dry_run_does_not_change_files(self):
        codex_home = self.make_codex_home()
        repo = self.make_react_repo()
        report = audit_context_tools(codex_home=codex_home, repo=repo)
        before_config = (codex_home / "config.toml").read_text()

        result = apply_context_tool_actions(
            report,
            ["disable-global-plugin-superpowers-openai-curated", "install-project-skill-react-best-practices"],
            apply=False,
            timestamp="20260518-120000",
        )

        self.assertTrue(result["ok"], result)
        self.assertTrue(result["dryRun"])
        self.assertEqual(before_config, (codex_home / "config.toml").read_text())
        self.assertFalse((repo / ".codex" / "skills" / "react-best-practices" / "SKILL.md").exists())

    def test_apply_actions_requires_selected_actions_and_writes_backup(self):
        codex_home = self.make_codex_home()
        repo = self.make_react_repo()
        report = audit_context_tools(codex_home=codex_home, repo=repo)

        empty_result = apply_context_tool_actions(report, [], apply=True, timestamp="20260518-120000")
        self.assertFalse(empty_result["ok"])

        result = apply_context_tool_actions(
            report,
            ["disable-global-plugin-superpowers-openai-curated", "install-project-skill-react-best-practices"],
            apply=True,
            timestamp="20260518-120000",
        )

        self.assertTrue(result["ok"], result)
        self.assertFalse(result["dryRun"])
        config_text = (codex_home / "config.toml").read_text()
        self.assertIn('[plugins."superpowers@openai-curated"]', config_text)
        self.assertIn("enabled = false", config_text)
        self.assertIn('[plugins."unused-plugin@local"]', config_text)
        self.assertIn("enabled = true", config_text)
        self.assertTrue((codex_home / "config.toml.bak-20260518-120000").exists())
        self.assertTrue((repo / ".codex" / "skills" / "react-best-practices" / "SKILL.md").exists())

    def test_audit_recommends_relevant_source_catalog_tools(self):
        codex_home = self.make_codex_home()
        repo = self.make_react_repo()
        catalog = Path(tempfile.mkdtemp(prefix="cpo-context-catalog-")) / "marketplace.json"
        catalog.write_text('{"plugins":[{"name":"build-web-apps","description":"React and frontend app tooling"}]}\n')

        report = audit_context_tools(codex_home=codex_home, repo=repo, source_catalogs=[catalog])

        titles = {item["title"] for item in report["recommendations"]}
        self.assertIn("Consider plugin build-web-apps", titles)


if __name__ == "__main__":
    unittest.main()
