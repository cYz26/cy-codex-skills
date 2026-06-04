import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import lark_feishu_ops_sync


class LarkFeishuOpsSyncTests(unittest.TestCase):
    def make_dir(self):
        return Path(tempfile.mkdtemp(prefix="lark-feishu-ops-sync-test-"))

    def test_apply_cli_update_runs_update_then_doctor(self):
        commands = []

        def fake_run_command(command, timeout=30):
            commands.append(command)
            stdout = "{}"
            if command == ["lark-cli", "update", "--json"]:
                stdout = json.dumps(
                    {
                        "action": "updated",
                        "previous_version": "1.0.43",
                        "current_version": "1.0.47",
                        "ok": True,
                    }
                )
            return {
                "command": command,
                "ok": True,
                "exit_code": 0,
                "stdout": stdout,
                "stderr": "",
            }

        with (
            mock.patch.object(lark_feishu_ops_sync, "run_command", side_effect=fake_run_command),
            mock.patch.object(
                lark_feishu_ops_sync,
                "run_doctor",
                return_value={"status": "PASS", "checks": {"lark_cli": {"status": "PASS"}}},
            ),
            mock.patch.object(
                lark_feishu_ops_sync,
                "inspect_installed_plugin_cache",
                return_value={"status": "matches-source", "recommendation": None},
            ),
        ):
            report = lark_feishu_ops_sync.build_report(
                apply_cli_update=True,
                after_cli_update=False,
                refresh_installed_plugin=False,
                repo="/repo",
            )

        self.assertIn(["lark-cli", "update", "--json"], commands)
        self.assertEqual("updated", report["cli_update"]["payload"]["action"])
        self.assertEqual("PASS", report["doctor"]["status"])
        self.assertFalse(report["plugin_update_required"])

    def test_installed_plugin_refresh_is_explicit(self):
        commands = []

        def fake_run_command(command, timeout=30):
            commands.append(command)
            return {
                "command": command,
                "ok": True,
                "exit_code": 0,
                "stdout": "{}",
                "stderr": "",
            }

        with (
            mock.patch.object(lark_feishu_ops_sync, "run_command", side_effect=fake_run_command),
            mock.patch.object(lark_feishu_ops_sync, "run_doctor", return_value={"status": "PASS"}),
            mock.patch.object(
                lark_feishu_ops_sync,
                "inspect_installed_plugin_cache",
                return_value={
                    "status": "differs-from-source",
                    "recommendation": "Refresh installed plugin cache.",
                },
            ),
        ):
            report = lark_feishu_ops_sync.build_report(
                apply_cli_update=False,
                after_cli_update=True,
                refresh_installed_plugin=False,
                repo="/repo",
            )

        self.assertNotIn(["codex", "plugin", "add", "lark-feishu-ops@cy-codex-skills"], commands)
        self.assertEqual("differs-from-source", report["installed_plugin_cache"]["status"])
        self.assertTrue(report["installed_plugin_refresh_recommended"])

    def test_refresh_installed_plugin_runs_only_with_flag(self):
        commands = []

        def fake_run_command(command, timeout=30):
            commands.append(command)
            return {
                "command": command,
                "ok": True,
                "exit_code": 0,
                "stdout": "refreshed",
                "stderr": "",
            }

        with (
            mock.patch.object(lark_feishu_ops_sync, "run_command", side_effect=fake_run_command),
            mock.patch.object(lark_feishu_ops_sync, "run_doctor", return_value={"status": "PASS"}),
            mock.patch.object(
                lark_feishu_ops_sync,
                "inspect_installed_plugin_cache",
                return_value={"status": "differs-from-source"},
            ),
        ):
            report = lark_feishu_ops_sync.build_report(
                apply_cli_update=False,
                after_cli_update=True,
                refresh_installed_plugin=True,
                repo="/repo",
            )

        self.assertIn(["codex", "plugin", "add", "lark-feishu-ops@cy-codex-skills"], commands)
        self.assertTrue(report["installed_plugin_refresh"]["ok"])

    def test_installed_cache_compare_detects_drift(self):
        root = self.make_dir()
        source = root / "source"
        installed = root / "installed"
        for base in (source, installed):
            (base / "skills" / "lark-feishu-ops").mkdir(parents=True)
            (base / "scripts").mkdir()
            (base / "skills" / "lark-feishu-ops" / "SKILL.md").write_text("same", encoding="utf-8")
            (base / "scripts" / "lark_feishu_ops_doctor.py").write_text("same", encoding="utf-8")

        same = lark_feishu_ops_sync.inspect_installed_plugin_cache(
            plugin_root=source,
            installed_plugin_root=installed,
        )
        self.assertEqual("matches-source", same["status"])

        (installed / "scripts" / "lark_feishu_ops_doctor.py").write_text("changed", encoding="utf-8")
        drift = lark_feishu_ops_sync.inspect_installed_plugin_cache(
            plugin_root=source,
            installed_plugin_root=installed,
        )
        self.assertEqual("differs-from-source", drift["status"])
        self.assertIn("scripts/lark_feishu_ops_doctor.py", drift["changed_files"])

    def test_default_installed_plugin_root_prefers_codex_switch_app_home(self):
        root = self.make_dir()
        codex_switch_root = (
            root
            / ".codex-switch"
            / "app-homes"
            / "internal"
            / "plugins"
            / "cache"
            / "cy-codex-skills"
            / "lark-feishu-ops"
            / "0.1.0"
        )
        codex_switch_root.mkdir(parents=True)
        legacy_root = (
            root
            / ".codex"
            / "plugins"
            / "cache"
            / "cy-codex-skills"
            / "lark-feishu-ops"
            / "0.1.0"
        )
        legacy_root.mkdir(parents=True)

        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch.object(lark_feishu_ops_sync, "HOME", root),
        ):
            selected = lark_feishu_ops_sync.default_installed_plugin_root()

        self.assertEqual(codex_switch_root, selected)


if __name__ == "__main__":
    unittest.main()
