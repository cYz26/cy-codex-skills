import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLUGIN_ROOT.parents[2] if PLUGIN_ROOT.parts[-3] == "dev" else PLUGIN_ROOT.parents[1]
IS_DEV = PLUGIN_ROOT.parts[-3] == "dev"


class Crawl4AIPluginTests(unittest.TestCase):
    def test_plugin_manifest_and_skill_are_packaged(self):
        manifest_path = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(manifest["name"], "crawl4ai")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(manifest["interface"]["displayName"], "Crawl4AI")
        self.assertIn("Markdown", manifest["interface"]["shortDescription"])

        skill_path = PLUGIN_ROOT / "skills" / "crawl4ai" / "SKILL.md"
        skill_text = skill_path.read_text(encoding="utf-8")
        self.assertIn("name: crawl4ai", skill_text)
        self.assertIn("Use when", skill_text)
        self.assertIn("Crawl4AI", skill_text)
        self.assertIn("MarkItDown", skill_text)

        openai_yaml = PLUGIN_ROOT / "skills" / "crawl4ai" / "agents" / "openai.yaml"
        self.assertTrue(openai_yaml.exists())
        self.assertIn("$crawl4ai", openai_yaml.read_text(encoding="utf-8"))

    def test_marketplace_registers_crawl4ai_plugin(self):
        marketplace_name = "marketplace.dev.json" if IS_DEV else "marketplace.json"
        expected_path = "./dev/plugins/crawl4ai" if IS_DEV else "./plugins/crawl4ai"
        marketplace = json.loads((REPO_ROOT / ".agents" / "plugins" / marketplace_name).read_text(encoding="utf-8"))

        entries = {entry["name"]: entry for entry in marketplace["plugins"]}
        self.assertIn("crawl4ai", entries)
        self.assertEqual(entries["crawl4ai"]["source"]["path"], expected_path)
        self.assertEqual(entries["crawl4ai"]["policy"]["installation"], "AVAILABLE")
        self.assertEqual(entries["crawl4ai"]["policy"]["authentication"], "ON_INSTALL")

    def test_fetch_script_uses_configured_command_and_emits_json(self):
        script_path = PLUGIN_ROOT / "skills" / "crawl4ai" / "scripts" / "crawl4ai_fetch.py"

        with tempfile.TemporaryDirectory() as tmp_dir:
            fake_cmd = Path(tmp_dir) / "fake-crwl"
            fake_cmd.write_text(
                "#!/usr/bin/env python3\n"
                "import sys\n"
                "print('# Example')\n"
                "print('URL:', sys.argv[1])\n",
                encoding="utf-8",
            )
            fake_cmd.chmod(0o755)

            env = os.environ.copy()
            env["CRAWL4AI_CMD"] = str(fake_cmd)
            proc = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--url",
                    "https://example.com/docs",
                    "--json",
                ],
                cwd=PLUGIN_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )

        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["url"], "https://example.com/docs")
        self.assertEqual(payload["format"], "markdown")
        self.assertIn("# Example", payload["content"])
        self.assertEqual(payload["command"], str(fake_cmd))

    def test_fetch_script_reports_unavailable_command(self):
        script_path = PLUGIN_ROOT / "skills" / "crawl4ai" / "scripts" / "crawl4ai_fetch.py"
        env = os.environ.copy()
        env["CRAWL4AI_CMD"] = "/definitely/missing/crwl"

        proc = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--url",
                "https://example.com/docs",
                "--json",
            ],
            cwd=PLUGIN_ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(proc.returncode, 2)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason"], "crawl4ai-unavailable")


if __name__ == "__main__":
    unittest.main()
