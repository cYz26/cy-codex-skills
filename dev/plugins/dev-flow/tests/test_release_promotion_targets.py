from __future__ import annotations

import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import release_promotion_gate


class ReleasePromotionTargetTests(unittest.TestCase):
    def run_main(self, *arguments: str) -> tuple[int, dict, mock.Mock]:
        report = {
            "status": "current",
            "message": "current",
            "assets": [],
        }
        output = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["release_promotion_gate.py", *arguments]),
            mock.patch.object(release_promotion_gate, "read_hook_payload", return_value={}),
            mock.patch.object(
                release_promotion_gate,
                "run_gate",
                return_value=report,
            ) as run_gate,
            contextlib.redirect_stdout(output),
        ):
            status = release_promotion_gate.main()
        return status, json.loads(output.getvalue()), run_gate

    def test_cli_accepts_explicit_lark_target(self):
        status, payload, run_gate = self.run_main(
            "--repo",
            ".",
            "--target",
            "lark-feishu-ops",
            "--json",
        )

        self.assertEqual(status, 0)
        self.assertEqual(payload["status"], "current")
        run_gate.assert_called_once_with(
            Path("."),
            apply=False,
            target="lark-feishu-ops",
        )

    def test_cli_keeps_dev_flow_as_explicit_default(self):
        _, _, run_gate = self.run_main("--repo", ".", "--json")

        run_gate.assert_called_once_with(
            Path("."),
            apply=False,
            target="dev-flow",
        )

    def test_lark_target_reports_packaged_release_verification(self):
        report = {
            "evalTargets": [
                {
                    "kind": "plugin",
                    "name": "lark-feishu-ops",
                    "target": "plugins/lark-feishu-ops",
                }
            ]
        }

        gates = release_promotion_gate.quality_gates(
            report,
            target="lark-feishu-ops",
        )
        commands = {gate["name"]: gate["command"] for gate in gates}

        runtime = " ".join(commands["release runtime verification"])
        self.assertIn(" -B ", f" {runtime} ")
        self.assertIn("dev/plugins/lark-feishu-ops/verification", runtime)
        self.assertIn("test_release_package.py", runtime)
        self.assertEqual(
            commands["Plugin Eval release"],
            [
                "plugin-eval",
                "analyze",
                "plugins/lark-feishu-ops",
                "--format",
                "markdown",
            ],
        )

    def test_dev_flow_target_keeps_runtime_verifier(self):
        gates = release_promotion_gate.quality_gates(
            {"evalTargets": []},
            target="dev-flow",
        )

        command = " ".join(gates[0]["command"])
        self.assertIn("plugins/dev-flow/scripts/verify_release_runtime.py", command)

    def test_unprofiled_asset_is_rejected_instead_of_getting_fabricated_tests(self):
        report = release_promotion_gate.run_gate(
            Path("."),
            apply=False,
            target="unknown-without-profile",
        )

        self.assertEqual("unsupported_target", report["status"])
        self.assertEqual([], report["qualityGates"])
        self.assertIn("releaseVerificationCommand", report["message"])
        with self.assertRaises(ValueError):
            release_promotion_gate.quality_gates(
                {
                    "evalTargets": [
                        {
                            "kind": "plugin",
                            "name": "sample",
                            "target": "plugins/sample",
                        }
                    ]
                },
                target="sample",
            )

    def test_metadata_profile_supplies_asset_specific_verification(self):
        profile = {
            "source": "release-sync metadata",
            "name": "release package verification",
            "command": ["python3.12", "-B", "verify-sample.py"],
        }
        gates = release_promotion_gate.quality_gates(
            {
                "evalTargets": [
                    {
                        "kind": "plugin",
                        "name": "sample",
                        "target": "plugins/sample",
                    }
                ]
            },
            target="sample",
            release_profile=profile,
        )
        commands = {gate["name"]: gate["command"] for gate in gates}

        self.assertEqual(
            ["python3.12", "-B", "verify-sample.py"],
            commands["release package verification"],
        )

    def test_malformed_target_metadata_fails_closed_without_exception(self):
        with mock.patch.object(
            release_promotion_gate,
            "discover_assets",
            side_effect=ValueError("synthetic malformed release metadata"),
        ):
            profile, errors = release_promotion_gate.resolve_release_profile(
                Path("."),
                "sample",
            )

        self.assertIsNone(profile)
        self.assertIn("metadata", " ".join(errors).lower())


if __name__ == "__main__":
    unittest.main()
