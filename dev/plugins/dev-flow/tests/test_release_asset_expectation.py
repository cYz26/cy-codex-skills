import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT = REPO_ROOT / "dev" / "scripts" / "verify_devflow_release_assets.py"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "publish-dev-flow.yml"
EXPECTATION_RELATIVE = Path(
    "openspec/changes/centralize-devflow-authority-delta/evidence/"
    "dev-flow-0.4.0.release-assets.json"
)
CONTRACT_RELATIVE = Path(
    "openspec/changes/centralize-devflow-authority-delta/evidence/"
    "standing-milestone-contract.json"
)


def canonical_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class ReleaseAssetExpectationPublicSeamTests(unittest.TestCase):
    def test_verifier_cli_exists(self) -> None:
        self.assertTrue(SCRIPT.is_file())


@unittest.skipUnless(SCRIPT.is_file(), "release-asset verifier intentionally RED")
class ReleaseAssetExpectationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="devflow-release-expectation-"
        )
        self.repo = Path(self.temporary.name)
        self.asset_dir = self.repo / "release-assets"
        self.asset_dir.mkdir()
        self.assets = {
            "dev-flow-0.4.0.zip": b"plugin bytes\n",
            "dev-flow-v0.4.0.md": b"release notes\n",
        }
        for name, payload in self.assets.items():
            (self.asset_dir / name).write_bytes(payload)
        self.expectation_path = self.repo / EXPECTATION_RELATIVE
        self.contract_path = self.repo / CONTRACT_RELATIVE
        self.expectation_path.parent.mkdir(parents=True)
        asset_records = [
            {
                "name": name,
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
            for name, payload in self.assets.items()
        ]
        self.contract = {
            "contractId": "dev-flow-authority-delta-v0.4.0",
            "writeSet": [EXPECTATION_RELATIVE.as_posix()],
            "plugin": {
                "id": "dev-flow",
                "marketplace": "cy-codex-skills",
                "versionRule": "fixture",
                "version": "0.4.0",
            },
            "publication": {
                "tag": "dev-flow-v0.4.0",
                "channel": "stable",
                "assetExpectation": EXPECTATION_RELATIVE.as_posix(),
                "assets": list(self.assets),
            },
        }
        self.expectation = {
            "schemaVersion": "1.0",
            "kind": "devflow-release-asset-expectation",
            "contractId": self.contract["contractId"],
            "plugin": "dev-flow",
            "version": "0.4.0",
            "tag": "dev-flow-v0.4.0",
            "channel": "stable",
            "assets": asset_records,
            "assetSetDigest": canonical_digest(asset_records),
        }
        self.write_documents()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_documents(self) -> None:
        self.contract_path.write_text(json.dumps(self.contract) + "\n")
        self.expectation_path.write_text(json.dumps(self.expectation) + "\n")

    def run_verifier(self, *extra: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--repo",
                str(self.repo),
                "--contract",
                CONTRACT_RELATIVE.as_posix(),
                "--expectation",
                EXPECTATION_RELATIVE.as_posix(),
                "--asset-dir",
                "release-assets",
                "--json",
                *extra,
            ],
            text=True,
            capture_output=True,
            env=environment,
            check=False,
        )

    def assert_rejected(self) -> None:
        result = self.run_verifier()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(
            {path.name: path.read_bytes() for path in self.asset_dir.iterdir()},
            self.assets,
        )

    def test_exact_asset_set_size_and_sha_are_verified(self) -> None:
        result = self.run_verifier()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["status"], "verified")
        self.assertEqual(report["assetSetDigest"], self.expectation["assetSetDigest"])
        self.assertEqual(
            [item["name"] for item in report["assets"]], list(self.assets)
        )

    def test_missing_extra_size_or_sha_drift_fails_closed(self) -> None:
        cases = ("missing", "extra", "bytes", "size", "sha")
        for case in cases:
            with self.subTest(case=case):
                original_assets = copy.deepcopy(self.assets)
                original_expectation = copy.deepcopy(self.expectation)
                try:
                    if case == "missing":
                        (self.asset_dir / next(iter(self.assets))).unlink()
                        self.assets.pop(next(iter(self.assets)))
                    elif case == "extra":
                        (self.asset_dir / "extra.bin").write_bytes(b"extra")
                        self.assets["extra.bin"] = b"extra"
                    elif case == "bytes":
                        name = next(iter(self.assets))
                        (self.asset_dir / name).write_bytes(b"drift")
                        self.assets[name] = b"drift"
                    elif case == "size":
                        self.expectation["assets"][0]["size"] += 1
                        self.write_documents()
                    else:
                        self.expectation["assets"][0]["sha256"] = "0" * 64
                        self.expectation["assetSetDigest"] = canonical_digest(
                            self.expectation["assets"]
                        )
                        self.write_documents()
                    self.assert_rejected()
                finally:
                    self.assets = original_assets
                    self.expectation = original_expectation
                    for path in list(self.asset_dir.iterdir()):
                        if path.is_symlink() or path.is_file():
                            path.unlink()
                    for name, payload in self.assets.items():
                        (self.asset_dir / name).write_bytes(payload)
                    self.write_documents()

    def test_symlinked_member_and_duplicate_key_documents_fail_closed(self) -> None:
        name = next(iter(self.assets))
        member = self.asset_dir / name
        payload = member.read_bytes()
        member.unlink()
        target = self.repo / "outside.bin"
        target.write_bytes(payload)
        member.symlink_to(target)
        self.assert_rejected()
        member.unlink()
        member.write_bytes(payload)

        self.expectation_path.write_text(
            '{"schemaVersion":"1.0","schemaVersion":"1.0"}\n'
        )
        self.assert_rejected()

    def test_expectation_must_be_candidate_write_set_bound_and_identity_exact(self) -> None:
        self.contract["writeSet"] = []
        self.write_documents()
        self.assert_rejected()

        self.contract["writeSet"] = [EXPECTATION_RELATIVE.as_posix()]
        self.expectation["tag"] = "dev-flow-v0.4.1"
        self.write_documents()
        self.assert_rejected()

        self.expectation["tag"] = "dev-flow-v0.4.0"
        self.contract["publication"]["assetExpectation"] = "evidence/alternate.json"
        self.write_documents()
        self.assert_rejected()


@unittest.skipUnless(WORKFLOW.is_file(), "publication workflow missing")
class ReleaseAssetExpectationWorkflowTests(unittest.TestCase):
    def test_action_verifies_frozen_assets_before_immutable_release(self) -> None:
        text = WORKFLOW.read_text()
        command = (
            "dev/scripts/verify_devflow_release_assets.py --repo . "
            f"--contract {CONTRACT_RELATIVE.as_posix()} "
            f"--expectation {EXPECTATION_RELATIVE.as_posix()} "
            "--asset-dir release-assets --json"
        )
        self.assertIn(command, text)
        self.assertLess(text.index(command), text.index("gh release create"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
