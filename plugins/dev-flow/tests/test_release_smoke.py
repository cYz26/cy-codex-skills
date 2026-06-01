import json
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from workflow_context_tools import apply_context_tool_actions, audit_context_tools


class ReleaseSmokeTests(unittest.TestCase):
    def test_manifest_uses_packaged_entrypoints(self):
        manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text())

        self.assertEqual(manifest["name"], "dev-flow")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(manifest["hooks"], "./hooks.json")
        self.assertLessEqual(len(manifest["interface"]["defaultPrompt"]), 3)
        self.assertTrue((PLUGIN_ROOT / manifest["interface"]["logo"]).exists())
        self.assertTrue((PLUGIN_ROOT / "hooks.json").exists())

    def test_context_tool_facade_is_importable_and_dry_runs(self):
        home = Path(tempfile.mkdtemp(prefix="devflow-release-home-"))
        repo = Path(tempfile.mkdtemp(prefix="devflow-release-repo-"))
        skill = home / "skills" / "example" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: example\ndescription: fixture\n---\n")
        (repo / "package.json").write_text('{"dependencies":{"react":"latest"}}\n')

        audit = audit_context_tools(home, repo)
        self.assertTrue(audit["ok"])
        self.assertIn("inventory", audit)
        self.assertIn("actions", audit)

        result = apply_context_tool_actions(audit, all_safe=True, apply=False)
        self.assertTrue(result["dryRun"])
        self.assertIn("applied", result)

    def test_subagent_and_repair_guidance_is_packaged(self):
        readme = (PLUGIN_ROOT / "README.md").read_text()
        self.assertIn("## Repair Solution Discipline", readme)
        self.assertIn("## SubAgent Strategy", readme)
        self.assertIn("policy/router layer", readme)
        self.assertIn("does not spawn subagents from scripts or hooks", readme)
        self.assertIn("explicit user authorization", readme)


if __name__ == "__main__":
    unittest.main()
