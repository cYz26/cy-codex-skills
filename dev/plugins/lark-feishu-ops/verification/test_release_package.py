"""Post-promotion checks for the generated Lark Feishu Ops release."""

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
DEVFLOW_SCRIPTS = REPO_ROOT / "dev" / "plugins" / "dev-flow" / "scripts"
PROMOTION_GATE = DEVFLOW_SCRIPTS / "release_promotion_gate.py"
sys.path.insert(0, str(DEVFLOW_SCRIPTS))

from release_promotion_gate import quality_gates
from workflow_release_sync import sync_release_assets


class LarkFeishuOpsReleasePackageTests(unittest.TestCase):
    def relative_files(self, root):
        return sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())

    def tree_bytes(self, root):
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file()
        }

    def run_promotion_check(self, repo, *extra):
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [
                sys.executable,
                str(PROMOTION_GATE),
                "--repo",
                str(repo),
                "--check",
                "--json",
                *extra,
            ],
            check=False,
            text=True,
            input="{}",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

    def test_release_sync_dry_run_reports_development_only_files_as_stale(self):
        with tempfile.TemporaryDirectory(prefix="lark-release-sync-test-") as temp:
            repo = Path(temp)
            source = repo / "dev" / "plugins" / "lark-feishu-ops"
            release = repo / "plugins" / "lark-feishu-ops"
            shutil.copytree(PLUGIN_ROOT, source)
            shutil.copytree(RELEASE_ROOT, release)
            stale_test = release / "tests" / "stale_release_test.py"
            stale_test.parent.mkdir(parents=True, exist_ok=True)
            stale_test.write_text("stale\n", encoding="utf-8")
            stale_eval = release / "skills" / "lark-feishu-ops" / "evals" / "evals.json"
            stale_eval.parent.mkdir(parents=True, exist_ok=True)
            stale_eval.write_text('{"stale":true}\n', encoding="utf-8")
            before = self.tree_bytes(release)

            report = sync_release_assets(repo, apply=False, targets=["lark-feishu-ops"])

            self.assertEqual("pending", report["status"], report)
            self.assertFalse(report["authorization"]["authorized"])
            self.assertEqual(before, self.tree_bytes(release), "dry-run mutated the release fixture")
            stale_files = set(report["assets"][0]["staleFiles"])
            self.assertIn("tests/stale_release_test.py", stale_files)
            self.assertIn("skills/lark-feishu-ops/evals/evals.json", stale_files)

    def test_generated_release_is_current_with_canonical_development_source(self):
        report = sync_release_assets(REPO_ROOT, apply=False, targets=["lark-feishu-ops"])

        self.assertEqual("current", report["status"], report)
        asset = report["assets"][0]
        self.assertEqual([], asset["changedFiles"])
        self.assertEqual([], asset["missingOutputs"])
        self.assertEqual([], asset["staleFiles"])
        self.assertEqual([], asset["staleOutputs"])

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
            },
            set(report["checks"]),
        )

    def test_canonical_and_release_manifests_publish_stable_0_2_0_identity(self):
        source_manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text())
        release_manifest = json.loads((RELEASE_ROOT / ".codex-plugin" / "plugin.json").read_text())

        self.assertEqual("lark-feishu-ops", source_manifest["name"])
        self.assertEqual("lark-feishu-ops", release_manifest["name"])
        self.assertEqual("0.2.0", source_manifest["version"])
        self.assertEqual(source_manifest, release_manifest)

    def test_promotion_cli_omitting_target_preserves_dev_flow_default(self):
        with tempfile.TemporaryDirectory(prefix="lark-promotion-default-test-") as temp:
            result = self.run_promotion_check(Path(temp))

        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual("dev-flow", report["releaseReadiness"]["target"])

    def test_promotion_cli_accepts_explicit_lark_target_in_check_mode(self):
        with tempfile.TemporaryDirectory(prefix="lark-promotion-target-test-") as temp:
            result = self.run_promotion_check(Path(temp), "--target", "lark-feishu-ops")

        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual("lark-feishu-ops", report["releaseReadiness"]["target"])

    def test_lark_post_promotion_quality_gate_is_target_specific(self):
        report = {
            "evalTargets": [
                {
                    "kind": "plugin",
                    "name": "lark-feishu-ops",
                    "target": "plugins/lark-feishu-ops",
                }
            ]
        }

        gates = quality_gates(report)
        plugin_eval = next(gate for gate in gates if gate["name"] == "Plugin Eval release")
        packaged = [gate for gate in gates if gate["name"] != "Plugin Eval release"]
        packaged_commands = [" ".join(gate["command"]) for gate in packaged]

        self.assertEqual(
            ["plugin-eval", "analyze", "plugins/lark-feishu-ops", "--format", "markdown"],
            plugin_eval["command"],
        )
        self.assertTrue(packaged, gates)
        self.assertTrue(
            all("lark-feishu-ops" in command for command in packaged_commands),
            packaged_commands,
        )
        self.assertNotIn("plugins/dev-flow", "\n".join(packaged_commands))

    def test_dev_flow_post_promotion_quality_gate_remains_backward_compatible(self):
        report = {
            "evalTargets": [
                {"kind": "plugin", "name": "dev-flow", "target": "plugins/dev-flow"}
            ]
        }

        gates = quality_gates(report)
        commands = {gate["name"]: " ".join(gate["command"]) for gate in gates}

        self.assertIn("verify_release_runtime.py", commands["release runtime verification"])
        self.assertIn("plugins/dev-flow", commands["release runtime verification"])
        self.assertIn("plugins/dev-flow", commands["Plugin Eval release"])


if __name__ == "__main__":
    unittest.main()
