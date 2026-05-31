import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "switch-profile.sh"


class SwitchProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.codex_home = Path(self.tmpdir.name) / "codex-home"
        self.codex_home.mkdir()
        self.ccx_dir = Path(self.tmpdir.name) / "missing-ccx"
        self.base_config = textwrap.dedent(
            """\
            model = "gpt-5.5"
            model_reasoning_effort = "medium"
            project_root_markers = [".git"]

            [model_providers.local]
            name = "Local"
            base_url = "http://127.0.0.1:1234/v1"
            wire_api = "chat"

            [features]
            hooks = true
            """
        )
        (self.codex_home / "config.toml").write_text(self.base_config)

    def tearDown(self):
        self.tmpdir.cleanup()

    def run_switch(self, *args):
        env = os.environ.copy()
        env.update(
            {
                "CODEX_HOME": str(self.codex_home),
                "CCX_DIR": str(self.ccx_dir),
                "NO_COLOR": "1",
            }
        )
        return subprocess.run(
            [str(SCRIPT), *args],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

    def parse_base_config(self):
        return tomllib.loads((self.codex_home / "config.toml").read_text())

    def test_deepseek_switches_base_config_and_generates_profile(self):
        result = self.run_switch("deepseek")

        self.assertEqual(result.returncode, 0, result.stdout)
        activated = self.parse_base_config()
        self.assertEqual(activated["model"], "ccx")
        self.assertEqual(activated["model_provider"], "ccx")
        self.assertEqual(activated["model_reasoning_effort"], "high")
        self.assertEqual(activated["model_providers"]["ccx"]["wire_api"], "responses")
        self.assertEqual(activated["model_providers"]["local"]["name"], "Local")

        official_snapshot = self.codex_home / "profiles" / "official" / "config.toml"
        self.assertTrue(official_snapshot.exists(), result.stdout)
        self.assertEqual(official_snapshot.read_text(), self.base_config)

        profile_path = self.codex_home / "deepseek.config.toml"
        self.assertTrue(profile_path.exists(), result.stdout)
        profile = tomllib.loads(profile_path.read_text())
        self.assertEqual(profile["model"], "ccx")
        self.assertEqual(profile["model_provider"], "ccx")
        self.assertEqual(profile["model_providers"]["ccx"]["wire_api"], "responses")

    def test_deepseek_cli_only_generates_overlay_without_mutating_base_config(self):
        result = self.run_switch("deepseek", "--cli-only")

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual((self.codex_home / "config.toml").read_text(), self.base_config)

        profile_path = self.codex_home / "deepseek.config.toml"
        self.assertTrue(profile_path.exists(), result.stdout)
        profile = tomllib.loads(profile_path.read_text())
        self.assertEqual(profile["model"], "ccx")
        self.assertEqual(profile["model_provider"], "ccx")

    def test_deepseek_model_alias_does_not_change_provider_id(self):
        result = self.run_switch("deepseek", "gpt-5.5")

        self.assertEqual(result.returncode, 0, result.stdout)
        profile = tomllib.loads((self.codex_home / "deepseek.config.toml").read_text())
        self.assertEqual(profile["model"], "gpt-5.5")
        self.assertEqual(profile["model_provider"], "ccx")
        activated = self.parse_base_config()
        self.assertEqual(activated["model"], "gpt-5.5")
        self.assertEqual(activated["model_provider"], "ccx")

    def test_official_preserves_custom_providers_and_reasoning_effort(self):
        result = self.run_switch("official")

        self.assertEqual(result.returncode, 0, result.stdout)
        parsed = self.parse_base_config()
        self.assertEqual(parsed["model"], "gpt-5.5")
        self.assertEqual(parsed["model_reasoning_effort"], "medium")
        self.assertEqual(parsed["model_providers"]["local"]["name"], "Local")

    def test_deepseek_switch_updates_base_safely_and_official_restores_snapshot(self):
        activate = self.run_switch("deepseek", "gpt-5.5")

        self.assertEqual(activate.returncode, 0, activate.stdout)
        activated = self.parse_base_config()
        self.assertEqual(activated["model"], "gpt-5.5")
        self.assertEqual(activated["model_provider"], "ccx")
        self.assertEqual(activated["model_reasoning_effort"], "high")
        self.assertEqual(activated["model_providers"]["ccx"]["wire_api"], "responses")
        self.assertEqual(activated["model_providers"]["local"]["name"], "Local")

        official = self.run_switch("official")

        self.assertEqual(official.returncode, 0, official.stdout)
        self.assertEqual((self.codex_home / "config.toml").read_text(), self.base_config)

    def test_activate_deepseek_alias_still_updates_base_safely(self):
        activate = self.run_switch("activate-deepseek", "gpt-5.5")

        self.assertEqual(activate.returncode, 0, activate.stdout)
        activated = self.parse_base_config()
        self.assertEqual(activated["model"], "gpt-5.5")
        self.assertEqual(activated["model_provider"], "ccx")
        self.assertEqual(activated["model_reasoning_effort"], "high")
        self.assertEqual(activated["model_providers"]["ccx"]["wire_api"], "responses")
        self.assertEqual(activated["model_providers"]["local"]["name"], "Local")

    def test_deepseek_model_catalog_is_parseable_by_current_codex(self):
        codex = shutil.which("codex")
        if not codex:
            self.skipTest("codex CLI not available")

        catalog = ROOT / "profiles" / "deepseek" / "models_catalog.json"
        json.loads(catalog.read_text())

        result = subprocess.run(
            [
                codex,
                "-c",
                f'model_catalog_json="{catalog}"',
                "debug",
                "models",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"slug":"ccx"', result.stdout.replace(" ", ""))


if __name__ == "__main__":
    unittest.main()
