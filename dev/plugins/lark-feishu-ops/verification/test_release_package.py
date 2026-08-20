"""Self-contained checks for the installable Lark Feishu Ops release."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLUGIN_ROOT.parents[2]
RELEASE_ROOT = REPO_ROOT / "plugins" / "lark-feishu-ops"
DEVELOPMENT_ONLY_PARTS = {"tests", "verification", "evals", "__pycache__"}


class LarkFeishuOpsReleasePackageTests(unittest.TestCase):
    def relative_files(self, root):
        return sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())

    def tree_bytes(self, root):
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file()
        }

    def runtime_projection(self, root):
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file()
            and path.name != ".DS_Store"
            and not DEVELOPMENT_ONLY_PARTS.intersection(path.relative_to(root).parts)
        }

    def test_release_matches_canonical_runtime_projection(self):
        self.assertEqual(
            self.runtime_projection(PLUGIN_ROOT),
            self.runtime_projection(RELEASE_ROOT),
        )

    def test_generated_release_contains_runtime_assets_only(self):
        release_files = self.relative_files(RELEASE_ROOT)
        required = {
            ".codex-plugin/plugin.json",
            "README.md",
            "CHANGELOG.md",
            "agents/feishu-ops.toml",
            "agents/runtime-prompts/feishu-ops.md",
            "assets/lark-feishu-ops.png",
            "assets/lark-feishu-ops.svg",
            "scripts/lark_feishu_ops_agent_context.py",
            "scripts/lark_feishu_ops_doctor.py",
            "scripts/lark_feishu_ops_policy.py",
            "scripts/lark_feishu_ops_runtime.py",
            "scripts/lark_feishu_ops_state.py",
            "scripts/lark_feishu_ops_sync.py",
            "scripts/test_runtime_contract.py",
            "skills/lark-feishu-ops/SKILL.md",
            "skills/lark-feishu-ops/agents/openai.yaml",
            "skills/lark-feishu-ops/references/feishuops-protocol.md",
        }
        forbidden_parts = {
            "tests",
            "test",
            "fixtures",
            "fixture",
            "evals",
            "eval",
            "__pycache__",
            ".pytest_cache",
            "scratch",
            "reports",
        }
        forbidden = sorted(
            relative
            for relative in release_files
            if forbidden_parts.intersection(Path(relative).parts)
            or relative.endswith((".pyc", ".pyo", ".log", ".tmp"))
        )

        self.assertEqual([], sorted(required - set(release_files)))
        self.assertEqual([], forbidden)

    def test_packaged_runtime_contract_self_test_passes(self):
        with tempfile.TemporaryDirectory(prefix="lark-runtime-selftest-") as temp:
            package = Path(temp) / "lark-feishu-ops"
            shutil.copytree(RELEASE_ROOT, package)
            shutil.rmtree(package / "scripts" / "__pycache__", ignore_errors=True)
            before = self.tree_bytes(package)
            environment = dict(os.environ)
            environment.pop("PYTHONDONTWRITEBYTECODE", None)
            result = subprocess.run(
                [
                    sys.executable,
                    str(package / "scripts" / "test_runtime_contract.py"),
                    "--json",
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=environment,
            )
            after = self.tree_bytes(package)

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(before, after, "packaged self-test mutated its runtime tree")
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"], report)
        self.assertEqual(
            {
                "auth_cache_disabled",
                "explicit_read_allowed",
                "unknown_action_blocked",
                "write_action_not_direct",
                "unknown_identity_has_no_cli_defaults",
                "explicit_identity_profile_are_bound",
            },
            set(report["checks"]),
        )

    def test_packaged_cli_help_does_not_create_bytecode(self):
        with tempfile.TemporaryDirectory(prefix="lark-runtime-help-") as temp:
            package = Path(temp) / "lark-feishu-ops"
            shutil.copytree(RELEASE_ROOT, package)
            shutil.rmtree(package / "scripts" / "__pycache__", ignore_errors=True)
            before = self.tree_bytes(package)
            environment = dict(os.environ)
            environment.pop("PYTHONDONTWRITEBYTECODE", None)
            results = [
                subprocess.run(
                    [sys.executable, str(package / "scripts" / script), "--help"],
                    check=False,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=environment,
                )
                for script in (
                    "lark_feishu_ops_agent_context.py",
                    "lark_feishu_ops_doctor.py",
                    "lark_feishu_ops_sync.py",
                )
            ]
            after = self.tree_bytes(package)

        self.assertTrue(all(result.returncode == 0 for result in results), results)
        self.assertEqual(before, after, "packaged CLI help mutated its runtime tree")

    def test_canonical_and_release_manifests_publish_stable_0_2_3_identity(self):
        source_manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text())
        release_manifest = json.loads((RELEASE_ROOT / ".codex-plugin" / "plugin.json").read_text())

        self.assertEqual("lark-feishu-ops", source_manifest["name"])
        self.assertEqual("lark-feishu-ops", release_manifest["name"])
        self.assertEqual("0.2.4", source_manifest["version"])
        self.assertEqual(source_manifest, release_manifest)


if __name__ == "__main__":
    unittest.main()
