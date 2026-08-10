from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from workflow_milestone_contract import (  # noqa: E402
    EXPECTED_REQUESTED_EFFECTS,
    validate_milestone_contract,
)


CANONICAL_CONTRACT = (
    PLUGIN_ROOT.parents[2]
    / "openspec"
    / "changes"
    / "centralize-devflow-authority-delta"
    / "evidence"
    / "standing-milestone-contract.json"
)
CONTRACT_SCHEMA = PLUGIN_ROOT / "schemas" / "milestone-external-effects-contract-v1.schema.json"
ASSET_EXPECTATION = (
    "openspec/changes/centralize-devflow-authority-delta/evidence/"
    "dev-flow-0.4.0.release-assets.json"
)


def canonical_contract() -> dict[str, object]:
    contract = copy.deepcopy(json.loads(CANONICAL_CONTRACT.read_text(encoding="utf-8")))
    publication = contract["publication"]
    publication["assetExpectation"] = ASSET_EXPECTATION
    write_set = contract["writeSet"]
    if ASSET_EXPECTATION not in write_set:
        write_set.append(ASSET_EXPECTATION)
        write_set.sort()
    return contract


class MilestoneContractValidationTests(unittest.TestCase):
    maxDiff = None

    def test_exact_contract_exposes_only_the_sealed_effect_manifest(self) -> None:
        contract = canonical_contract()

        result = validate_milestone_contract(
            contract,
            project_target_available=True,
        )

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["reasonCodes"], [])
        self.assertEqual(result["invalidations"], [])
        self.assertEqual(
            result["requestedEffects"],
            list(EXPECTED_REQUESTED_EFFECTS),
        )
        self.assertEqual(
            result["effectTargets"]["git.push"],
            "origin:refs/heads/main",
        )
        self.assertEqual(
            result["effectTargets"]["devflow.project.refresh"],
            "/Users/cy/Dev/agents-dev/cy-codex-skills",
        )
        self.assertEqual(result["assetExpectation"], ASSET_EXPECTATION)

    def test_asset_expectation_is_safe_required_and_inside_the_exact_write_set(self) -> None:
        cases: list[tuple[str, object | None, bool, str]] = [
            ("missing", None, True, "contract.publication.assetExpectation"),
            (
                "absolute",
                "/tmp/release-assets.json",
                True,
                "contract.publication.assetExpectation",
            ),
            (
                "parent",
                "../release-assets.json",
                True,
                "contract.publication.assetExpectation",
            ),
            (
                "outside-write-set",
                ASSET_EXPECTATION,
                False,
                "contract.publication.assetExpectation:writeSet",
            ),
        ]
        for name, expectation, keep_in_write_set, invalidation in cases:
            with self.subTest(name=name):
                contract = canonical_contract()
                publication = contract["publication"]
                self.assertIsInstance(publication, dict)
                if expectation is None:
                    publication.pop("assetExpectation")
                else:
                    publication["assetExpectation"] = expectation
                if not keep_in_write_set:
                    write_set = contract["writeSet"]
                    self.assertIsInstance(write_set, list)
                    write_set.remove(ASSET_EXPECTATION)

                result = validate_milestone_contract(
                    contract,
                    project_target_available=True,
                )

                self.assertFalse(result["ok"], result)
                self.assertEqual(
                    result["reasonCodes"],
                    ["STANDING_CONTRACT_IDENTITY_INVALID"],
                )
                self.assertIn(invalidation, result["invalidations"])
                self.assertIsNone(result["assetExpectation"])

    def test_requested_effects_must_be_present_exact_unique_and_ordered(self) -> None:
        cases: dict[str, object | None] = {
            "missing": None,
            "not-list": "git.commit",
            "empty": [],
            "mixed-types": ["git.commit", 7],
            "mixed-authority": [*EXPECTED_REQUESTED_EFFECTS[:-1], "github.pr"],
            "duplicate": [*EXPECTED_REQUESTED_EFFECTS, "git.commit"],
            "blank": [*EXPECTED_REQUESTED_EFFECTS[:-1], "  "],
            "partial": list(EXPECTED_REQUESTED_EFFECTS[:-1]),
            "out-of-order": [
                EXPECTED_REQUESTED_EFFECTS[1],
                EXPECTED_REQUESTED_EFFECTS[0],
                *EXPECTED_REQUESTED_EFFECTS[2:],
            ],
        }
        for name, requested in cases.items():
            with self.subTest(name=name):
                contract = canonical_contract()
                if requested is None:
                    contract.pop("requestedEffects")
                else:
                    contract["requestedEffects"] = requested

                result = validate_milestone_contract(
                    contract,
                    project_target_available=True,
                )

                self.assertFalse(result["ok"], result)
                self.assertEqual(result["reasonCodes"], ["REQUESTED_EFFECTS_INVALID"])
                self.assertEqual(result["invalidations"], ["contract.requestedEffects"])
                self.assertEqual(result["effectTargets"], {})

    def test_contract_version_keys_and_target_shapes_are_exact(self) -> None:
        cases: list[tuple[str, tuple[str, ...], object, str]] = [
            ("version", ("schemaVersion",), "2.0", "contract.schemaVersion"),
            ("blank-goal", ("goal",), "  ", "contract.goal"),
            ("root-extra", ("unexpected",), True, "contract.keys"),
            ("plugin-extra", ("plugin", "unexpected"), True, "contract.plugin.keys"),
            ("remote-blank", ("repository", "remote"), "", "contract.repository.remote"),
            (
                "remote-malformed",
                ("repository", "remote"),
                "origin main",
                "contract.repository.remote",
            ),
            (
                "remote-url-control",
                ("repository", "remoteUrl"),
                "git@example.invalid:repo.git\nother",
                "contract.repository.remoteUrl",
            ),
            (
                "remote-url-malformed",
                ("repository", "remoteUrl"),
                "not a remote identity",
                "contract.repository.remoteUrl",
            ),
            (
                "ref-malformed",
                ("repository", "ref"),
                "refs/heads/main..other",
                "contract.repository.ref",
            ),
            (
                "cache-mismatch",
                ("refreshTargets", "cache"),
                "other@cy-codex-skills",
                "contract.refreshTargets.cache",
            ),
            (
                "project-relative",
                ("refreshTargets", "project"),
                "relative/project",
                "contract.refreshTargets.project",
            ),
            (
                "workflow-parent",
                ("publication", "workflow"),
                "../publish.yml",
                "contract.publication.workflow",
            ),
            (
                "failure-policy-extra",
                ("failurePolicy", "retryForever"),
                True,
                "contract.failurePolicy.keys",
            ),
            (
                "reentry-policy-widened",
                ("reentryPolicy", "duplicateEffects"),
                True,
                "contract.reentryPolicy.duplicateEffects",
            ),
            (
                "write-set-parent",
                ("writeSet", 0),
                "../outside",
                "contract.writeSet",
            ),
            (
                "write-set-mixed",
                ("writeSet", 0),
                {"path": "feature.txt"},
                "contract.writeSet",
            ),
            (
                "asset-list-mixed",
                ("publication", "assets", 0),
                {"name": "dev-flow-0.4.0.zip"},
                "contract.publication.assets",
            ),
        ]
        for name, path, value, expected_invalidation in cases:
            with self.subTest(name=name):
                contract = canonical_contract()
                current: object = contract
                for part in path[:-1]:
                    self.assertIsInstance(current, (dict, list))
                    current = current[part]  # type: ignore[index]
                current[path[-1]] = value  # type: ignore[index]

                result = validate_milestone_contract(
                    contract,
                    project_target_available=True,
                )

                self.assertFalse(result["ok"], result)
                self.assertIn(
                    "STANDING_CONTRACT_IDENTITY_INVALID",
                    result["reasonCodes"],
                )
                self.assertIn(expected_invalidation, result["invalidations"])
                self.assertEqual(result["effectTargets"], {})

    def test_declared_but_absent_project_target_is_evidence_repair(self) -> None:
        result = validate_milestone_contract(
            canonical_contract(),
            project_target_available=False,
        )

        self.assertFalse(result["ok"], result)
        self.assertEqual(
            result["reasonCodes"],
            ["STANDING_CONTRACT_TARGET_UNAVAILABLE"],
        )
        self.assertEqual(
            result["invalidations"],
            ["contract.refreshTargets.project:unavailable"],
        )
        self.assertEqual(result["effectTargets"], {})

    def test_draft_2020_12_schema_matches_the_strict_runtime_contract(self) -> None:
        from jsonschema import Draft202012Validator

        schema = json.loads(CONTRACT_SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        self.assertEqual(list(validator.iter_errors(canonical_contract())), [])

        cases: dict[str, tuple[tuple[str, ...], object]] = {
            "requested-effects-order": (
                ("requestedEffects",),
                [
                    EXPECTED_REQUESTED_EFFECTS[1],
                    EXPECTED_REQUESTED_EFFECTS[0],
                    *EXPECTED_REQUESTED_EFFECTS[2:],
                ],
            ),
            "requested-effects-mixed-authority": (
                ("requestedEffects",),
                [*EXPECTED_REQUESTED_EFFECTS[:-1], "github.pr"],
            ),
            "blank-goal": (("goal",), "  "),
            "malformed-remote-url": (
                ("repository", "remoteUrl"),
                "not a remote identity",
            ),
            "malformed-ref": (("repository", "ref"), "refs/heads/main..other"),
            "relative-project": (("refreshTargets", "project"), "relative/project"),
            "asset-expectation-parent": (
                ("publication", "assetExpectation"),
                "../release-assets.json",
            ),
            "failure-policy-extra": (("failurePolicy", "retryForever"), True),
        }
        for name, (path, value) in cases.items():
            with self.subTest(name=name):
                document = canonical_contract()
                current: object = document
                for part in path[:-1]:
                    current = current[part]  # type: ignore[index]
                current[path[-1]] = value  # type: ignore[index]
                self.assertNotEqual(list(validator.iter_errors(document)), [])

        missing_expectation = canonical_contract()
        publication = missing_expectation["publication"]
        self.assertIsInstance(publication, dict)
        publication.pop("assetExpectation")
        self.assertNotEqual(list(validator.iter_errors(missing_expectation)), [])


if __name__ == "__main__":
    unittest.main()
