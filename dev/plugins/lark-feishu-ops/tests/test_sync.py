import json
import os
import shutil
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
        root = Path(tempfile.mkdtemp(prefix="lark-feishu-ops-sync-test-"))
        self.addCleanup(shutil.rmtree, root, True)
        return root

    def write_file(self, root, relative, content="same"):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

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

    def test_refresh_installed_plugin_reports_fresh_post_mutation_parity(self):
        root = self.make_dir()
        source = root / "source"
        installed = root / "installed"
        self.write_file(source, "README.md", "current")
        self.write_file(installed, "README.md", "stale")
        commands = []

        def fake_run_command(command, timeout=30):
            commands.append(command)
            if command == ["codex", "plugin", "add", "lark-feishu-ops@cy-codex-skills"]:
                shutil.copy2(source / "README.md", installed / "README.md")
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
        ):
            report = lark_feishu_ops_sync.build_report(
                apply_cli_update=False,
                after_cli_update=True,
                refresh_installed_plugin=True,
                repo="/repo",
                plugin_root=source,
                installed_plugin_root=installed,
            )

        self.assertIn(["codex", "plugin", "add", "lark-feishu-ops@cy-codex-skills"], commands)
        self.assertTrue(report["installed_plugin_refresh"]["ok"])
        self.assertEqual("matches-source", report["installed_plugin_cache"]["status"])
        self.assertFalse(report["installed_plugin_refresh_recommended"])

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

    def test_installed_cache_compare_covers_every_shipped_runtime_asset(self):
        root = self.make_dir()
        source = root / "source"
        installed = root / "installed"
        runtime_files = {
            ".codex-plugin/plugin.json": '{"name":"lark-feishu-ops","version":"9.8.7"}',
            "README.md": "readme",
            "CHANGELOG.md": "changes",
            "agents/feishu-ops.toml": "agent",
            "agents/runtime-prompts/feishu-ops.md": "prompt",
            "assets/lark-feishu-ops.png": b"png",
            "assets/lark-feishu-ops.svg": "svg",
            "scripts/lark_feishu_ops_agent_context.py": "context",
            "scripts/lark_feishu_ops_doctor.py": "doctor",
            "scripts/lark_feishu_ops_sync.py": "sync",
            "skills/lark-feishu-ops/SKILL.md": "skill",
            "skills/lark-feishu-ops/agents/openai.yaml": "metadata",
            "skills/lark-feishu-ops/references/feishuops-protocol.md": "protocol",
        }
        for relative, content in runtime_files.items():
            self.write_file(source, relative, content)
            self.write_file(installed, relative, content)

        changed_files = {
            "assets/lark-feishu-ops.png",
            "skills/lark-feishu-ops/agents/openai.yaml",
        }
        for relative in changed_files:
            self.write_file(installed, relative, b"drift" if relative.endswith(".png") else "drift")
        missing_file = "skills/lark-feishu-ops/references/feishuops-protocol.md"
        (installed / missing_file).unlink()

        # Development evidence is deliberately not part of installed runtime parity.
        self.write_file(source, "tests/test_internal.py", "source-test")
        self.write_file(installed, "tests/test_internal.py", "installed-test")
        self.write_file(source, "skills/lark-feishu-ops/evals/evals.json", "source-eval")
        self.write_file(installed, "skills/lark-feishu-ops/evals/evals.json", "installed-eval")

        report = lark_feishu_ops_sync.inspect_installed_plugin_cache(
            plugin_root=source,
            installed_plugin_root=installed,
        )

        self.assertEqual("differs-from-source", report["status"])
        self.assertEqual(sorted(changed_files), report["changed_files"])
        self.assertEqual([missing_file], report["missing_files"])

    def test_manifest_version_and_codex_home_select_installed_cache(self):
        root = self.make_dir()
        source = root / "source"
        codex_home = root / "active-codex-home"
        version = "9.8.7"
        installed = (
            codex_home
            / "plugins"
            / "cache"
            / "cy-codex-skills"
            / "lark-feishu-ops"
            / version
        )
        manifest = json.dumps({"name": "lark-feishu-ops", "version": version})
        self.write_file(source, ".codex-plugin/plugin.json", manifest)
        self.write_file(source, "README.md", "same")
        self.write_file(installed, ".codex-plugin/plugin.json", manifest)
        self.write_file(installed, "README.md", "same")

        with (
            mock.patch.dict(os.environ, {"CODEX_HOME": str(codex_home)}, clear=True),
            mock.patch.object(lark_feishu_ops_sync, "HOME", root / "home"),
            mock.patch.object(lark_feishu_ops_sync, "run_doctor", return_value={"status": "PASS"}),
        ):
            report = lark_feishu_ops_sync.build_report(
                apply_cli_update=False,
                after_cli_update=False,
                refresh_installed_plugin=False,
                repo="/repo",
                plugin_root=source,
            )

        self.assertEqual("matches-source", report["installed_plugin_cache"]["status"])
        self.assertEqual(str(installed), report["installed_plugin_cache"]["installed_root"])

    def test_cli_update_ok_false_envelope_cannot_report_success(self):
        def fake_run_command(command, timeout=30):
            return {
                "command": command,
                "ok": True,
                "exit_code": 0,
                "stdout": json.dumps(
                    {
                        "ok": False,
                        "action": "failed",
                        "error": "synthetic update failure",
                    }
                ),
                "stderr": "",
            }

        with (
            mock.patch.object(lark_feishu_ops_sync, "run_command", side_effect=fake_run_command),
            mock.patch.object(lark_feishu_ops_sync, "run_doctor", return_value={"status": "PASS"}),
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

        self.assertEqual("FAIL", report["status"])
        self.assertFalse(report["cli_update"]["payload"]["ok"])

    def test_doctor_warning_remains_warning_when_cache_is_current(self):
        with (
            mock.patch.object(
                lark_feishu_ops_sync,
                "run_doctor",
                return_value={
                    "status": "WARN",
                    "checks": {"lark_cli": {"status": "PASS"}},
                },
            ),
            mock.patch.object(
                lark_feishu_ops_sync,
                "inspect_installed_plugin_cache",
                return_value={"status": "matches-source", "recommendation": None},
            ),
        ):
            report = lark_feishu_ops_sync.build_report(
                apply_cli_update=False,
                after_cli_update=True,
                refresh_installed_plugin=False,
                repo="/repo",
            )

        self.assertEqual("WARN", report["status"])
        self.assertFalse(report["plugin_update_required"])

    def test_main_treats_warning_as_successful_diagnostic_exit(self):
        args = mock.Mock(
            apply_cli_update=False,
            after_cli_update=True,
            refresh_installed_plugin=False,
            repo="/repo",
            codex_home=None,
            json=True,
        )
        with (
            mock.patch.object(lark_feishu_ops_sync, "parse_args", return_value=args),
            mock.patch.object(
                lark_feishu_ops_sync,
                "build_report",
                return_value={"status": "WARN", "recommendations": []},
            ),
            mock.patch("builtins.print"),
        ):
            result = lark_feishu_ops_sync.main()

        self.assertEqual(0, result)


if __name__ == "__main__":
    unittest.main()
