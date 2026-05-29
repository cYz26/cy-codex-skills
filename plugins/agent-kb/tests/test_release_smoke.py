import json
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
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

        expected = {
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
        self.assertEqual(
            json.loads((repo / ".agent-kb.json").read_text())["storage_adapter"],
            "markdown-filesystem",
        )
        self.assertTrue(lint["ok"], lint)
        self.assertTrue(event["recorded"], event)
        self.assertTrue(event["path"].startswith(".agent-kb/events/"), event)
        self.assertNotIn("SECRET_RELEASE_OUTPUT", (vault / event["path"]).read_text())

if __name__ == "__main__":
    unittest.main()
