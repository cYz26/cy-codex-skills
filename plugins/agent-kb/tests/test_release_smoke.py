import json
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
HOOK_SCRIPT_PREFIX = (
    'python3 "${CODEX_HOME:-$HOME/.codex}/plugins/cache/cy-codex-skills/'
    'agent-kb/0.1.0/scripts/'
)
sys.path.insert(0, str(SCRIPTS))

from workflow_agent_kb import lint_agent_kb, record_agent_kb_event, scaffold_agent_kb


class AgentKBReleaseSmokeTests(unittest.TestCase):
    def test_manifest_and_skill_inventory_are_packaged(self):
        manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text())
        self.assertEqual(manifest["name"], "agent-kb")
        self.assertEqual(manifest["interface"]["displayName"], "AgentKB")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(manifest["hooks"], "./hooks.json")
        self.assertTrue((PLUGIN_ROOT / "hooks.json").exists())
        self.assertTrue((PLUGIN_ROOT / "scripts" / "kb_event_hook.py").exists())
        hooks = json.loads((PLUGIN_ROOT / "hooks.json").read_text())["hooks"]
        hook_commands = [
            hook["command"]
            for group in hooks.values()
            for entry in group
            for hook in entry.get("hooks", [])
        ]
        self.assertTrue(all(command.startswith(HOOK_SCRIPT_PREFIX) for command in hook_commands))
        self.assertFalse(any("./scripts/" in command for command in hook_commands))

        expected = {
            "kb-capture",
            "kb-ingest",
            "kb-query",
            "kb-update",
            "kb-compact",
            "kb-lint",
            "kb-reflect",
            "kb-promote",
        }
        self.assertEqual(expected, {path.name for path in (PLUGIN_ROOT / "skills").iterdir() if path.is_dir()})

    def test_packaged_behavior_scaffolds_lints_and_records_events(self):
        root = Path(tempfile.mkdtemp(prefix="agent-kb-release-"))
        repo = root / "repo"
        vault = root / "vault"
        repo.mkdir()

        scaffold = scaffold_agent_kb(repo=repo, vault=vault, project="release-kb", owner="chanYu")
        lint = lint_agent_kb(vault=vault, project="release-kb")
        event = record_agent_kb_event(
            repo,
            "post_tool_use",
            {
                "cwd": str(repo),
                "tool_name": "Bash",
                "tool_response": {"exit_code": 0, "output": "SECRET_RELEASE_OUTPUT"},
            },
        )

        self.assertTrue(scaffold["configured"], scaffold)
        self.assertTrue((repo / ".agent-kb.json").exists())
        config = json.loads((repo / ".agent-kb.json").read_text())
        self.assertEqual(config["schema_version"], 2)
        self.assertEqual(config["vault_profile"], "personal-first")
        self.assertEqual(config["storage_adapter"], "markdown-filesystem")
        self.assertEqual(config["editor_adapter"], "obsidian-cli")
        self.assertEqual(config["context_pack"], "projects/release-kb/context-pack.md")
        self.assertEqual(config["index"], "_system/indexes/home.md")
        self.assertEqual(config["knowledge_index"], "_system/indexes/knowledge-index.md")
        self.assertEqual(config["project_index"], "projects/_project-index.md")
        self.assertTrue((PLUGIN_ROOT / "scripts" / "agent_kb_obsidian_cli.py").exists())
        self.assertTrue((vault / "_system" / "routing-rules.md").exists())
        self.assertTrue((vault / "_agent" / "routing-receipts").exists())
        self.assertTrue((vault / "_bases" / "Promotion.base").exists())
        self.assertTrue((vault / "personal" / "ideas").exists())
        self.assertTrue((vault / "work" / "meetings").exists())
        self.assertTrue((vault / "knowledge" / "index.md").exists())
        self.assertTrue((vault / "promotion" / "candidates").exists())
        self.assertTrue((vault / "projects" / "release-kb" / "context-pack.md").exists())
        self.assertTrue((vault / "projects" / "release-kb" / "candidates").exists())
        self.assertTrue((vault / "playbooks" / "kb-reflect.md").exists())
        self.assertTrue((vault / "playbooks" / "kb-promote.md").exists())
        index = (vault / "_system" / "indexes" / "knowledge-index.md").read_text()
        self.assertIn("[[../../playbooks/kb-reflect|KB reflect]]", index)
        self.assertIn("[[../../playbooks/kb-promote|KB promote]]", index)
        reflect_playbook = (vault / "playbooks" / "kb-reflect.md").read_text()
        promote_playbook = (vault / "playbooks" / "kb-promote.md").read_text()
        self.assertIn("generalized lesson", reflect_playbook.lower())
        self.assertIn("prevention mechanism", reflect_playbook.lower())
        self.assertIn("smallest durable destination", promote_playbook.lower())
        self.assertFalse((vault / "10-wiki").exists())
        self.assertFalse((vault / "20-projects").exists())
        self.assertTrue(lint["ok"], lint)
        self.assertTrue(event["recorded"], event)
        self.assertTrue(event["path"].startswith(".agent-kb/events/"), event)
        self.assertNotIn("SECRET_RELEASE_OUTPUT", (vault / event["path"]).read_text())

if __name__ == "__main__":
    unittest.main()
