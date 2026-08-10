from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

try:
    from workflow_milestone_contract import EXPECTED_REQUESTED_EFFECTS
    from workflow_standing_milestone import resolve_standing_milestone
except ModuleNotFoundError as error:
    if error.name not in {"workflow_milestone_contract", "workflow_standing_milestone"}:
        raise
    EXPECTED_REQUESTED_EFFECTS = ()
    resolve_standing_milestone = None
    IMPORT_ERROR = error
else:
    IMPORT_ERROR = None


REQUIRED_EXCLUSIONS = [
    "archive",
    "force-push",
    "game-dev-plugins",
    "merge",
    "pr",
    "rebase",
    "unnamed-consumer",
    "unnamed-plugin",
    "unrelated-release",
]
ASSET_EXPECTATION = (
    "openspec/changes/centralize-devflow-authority-delta/evidence/"
    "dev-flow-0.4.0.release-assets.json"
)


def standing_contract(**overrides: object) -> dict[str, object]:
    contract: dict[str, object] = {
        "schemaVersion": "1.0",
        "contractId": "dev-flow-authority-delta-v0.4.0",
        "goalId": "goal-authority-delta",
        "goal": "Reduce false Human Gates while preserving fail-closed safety.",
        "change": "centralize-devflow-authority-delta",
        "milestone": "dev-flow-authority-delta-v0.4.0",
        "plugin": {
            "id": "dev-flow",
            "marketplace": "cy-codex-skills",
            "versionRule": "first-non-breaking-capability-release-after-0.3.x",
            "version": "0.4.0",
        },
        "repository": {
            "remote": "origin",
            "remoteUrl": "git@example.invalid:dev-flow.git",
            "ref": "refs/heads/main",
            "expectedBase": "a" * 40,
        },
        "commit": {"message": "feat(dev-flow): centralize authority-delta execution"},
        "publication": {
            "tag": "dev-flow-v0.4.0",
            "channel": "stable",
            "mechanism": "github_actions",
            "workflow": ".github/workflows/publish-dev-flow.yml",
            "assets": ["dev-flow-0.4.0.zip"],
            "assetExpectation": ASSET_EXPECTATION,
        },
        "requestedEffects": list(EXPECTED_REQUESTED_EFFECTS),
        "writeSet": [
            "dev/plugins/dev-flow/.codex-plugin/plugin.json",
            ASSET_EXPECTATION,
        ],
        "refreshTargets": {
            "cache": "dev-flow@cy-codex-skills",
            "project": "@PROJECT_PATH@",
        },
        "failurePolicy": {
            "preserveCommit": True,
            "preserveTag": True,
            "maxDiagnoses": 1,
            "maxRemediations": 1,
            "allowAlternatePublication": False,
        },
        "reentryPolicy": {
            "sameIdentityOnly": True,
            "resume": "first_incomplete_step",
            "duplicateEffects": False,
        },
        "exclusions": list(REQUIRED_EXCLUSIONS),
    }
    contract.update(overrides)
    return contract


def write_contract(repo: Path, contract: dict[str, object]) -> tuple[str, str]:
    contract = copy.deepcopy(contract)
    refresh = contract.get("refreshTargets")
    if isinstance(refresh, dict) and refresh.get("project") == "@PROJECT_PATH@":
        project = repo / "dev-flow-source"
        project.mkdir()
        refresh["project"] = str(project)
    relative = "openspec/changes/centralize-devflow-authority-delta/evidence/standing-contract.json"
    path = repo / relative
    path.parent.mkdir(parents=True)
    payload = json.dumps(contract, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    path.write_text(payload, encoding="utf-8")
    return relative, hashlib.sha256(payload.encode("utf-8")).hexdigest()


def bound_state(
    *,
    status: str,
    contract_path: str,
    contract_sha256: str,
    **standing_overrides: object,
) -> dict[str, object]:
    standing: dict[str, object] = {
        "status": status,
        "contract_path": contract_path,
        "contract_sha256": contract_sha256,
        "goal_id": "goal-authority-delta",
        "change_id": "centralize-devflow-authority-delta",
    }
    standing.update(standing_overrides)
    return {
        "current_change": {"id": "centralize-devflow-authority-delta"},
        "goal_gate": {"id": "goal-authority-delta"},
        "standing_milestone": standing,
    }


def current_state(*, contract_path: str, contract_sha256: str, **overrides: object) -> dict[str, object]:
    return bound_state(
        status="current",
        contract_path=contract_path,
        contract_sha256=contract_sha256,
        candidate_digest="b" * 64,
        validation_digest="c" * 64,
        review_digest="d" * 64,
        **overrides,
    )


class StandingMilestoneTests(unittest.TestCase):
    maxDiff = None

    def test_existing_project_without_contract_default_denies_external_effect(self) -> None:
        self.assertIsNotNone(
            resolve_standing_milestone,
            f"public resolver is unavailable: {IMPORT_ERROR}",
        )
        with tempfile.TemporaryDirectory() as directory:
            result = resolve_standing_milestone(  # type: ignore[misc]
                Path(directory),
                {
                    "current_change": {"id": "legacy-change"},
                    "goal_gate": {"id": "legacy-goal"},
                    "standing_milestone": {"status": "inactive"},
                },
                requested_effect="git.push",
                requested_target="origin:refs/heads/main",
            )

        self.assertEqual(result["decision"], "AWAIT_HUMAN")
        self.assertEqual(result["missingAuthority"], ["standing_milestone.contract"])
        self.assertTrue(result["materialDelta"])
        self.assertRegex(str(result["gateKey"]), r"^[0-9a-f]{64}$")

    def test_declared_contract_allows_only_local_release_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            contract_path, contract_sha256 = write_contract(repo, standing_contract())
            result = resolve_standing_milestone(  # type: ignore[misc]
                repo,
                bound_state(
                    status="declared",
                    contract_path=contract_path,
                    contract_sha256=contract_sha256,
                ),
                requested_effect="release.promote_local",
                requested_target="plugins/dev-flow",
            )

        self.assertEqual(result["decision"], "CONTINUE")
        self.assertEqual(result["reasonCodes"], ["STANDING_MILESTONE_DECLARED_LOCAL_PROMOTION"])
        self.assertFalse(result["authorityCurrent"])
        self.assertEqual(result["missingAuthority"], [])
        self.assertIsNone(result["gateKey"])

    def test_declared_contract_stops_external_effect_as_technical_repair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            contract_path, contract_sha256 = write_contract(repo, standing_contract())
            result = resolve_standing_milestone(  # type: ignore[misc]
                repo,
                bound_state(
                    status="declared",
                    contract_path=contract_path,
                    contract_sha256=contract_sha256,
                ),
                requested_effect="git.push",
                requested_target="origin:refs/heads/main",
            )

        self.assertEqual(result["decision"], "FAIL_CLOSED_REPAIR")
        self.assertEqual(result["reasonCodes"], ["STANDING_MILESTONE_NOT_CURRENT"])
        self.assertEqual(result["invalidations"], ["standing_milestone.status"])
        self.assertEqual(result["missingAuthority"], [])
        self.assertFalse(result["materialDelta"])
        self.assertIsNone(result["gateKey"])

    def test_current_contract_requires_all_frozen_evidence_digests(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            contract_path, contract_sha256 = write_contract(repo, standing_contract())
            result = resolve_standing_milestone(  # type: ignore[misc]
                repo,
                bound_state(
                    status="current",
                    contract_path=contract_path,
                    contract_sha256=contract_sha256,
                ),
                requested_effect="git.push",
                requested_target="origin:refs/heads/main",
            )

        self.assertEqual(result["decision"], "FAIL_CLOSED_REPAIR")
        self.assertEqual(result["reasonCodes"], ["FROZEN_EVIDENCE_INCOMPLETE"])
        self.assertEqual(
            result["invalidations"],
            [
                "standing_milestone.candidate_digest",
                "standing_milestone.validation_digest",
                "standing_milestone.review_digest",
            ],
        )
        self.assertEqual(result["missingAuthority"], [])
        self.assertFalse(result["authorityCurrent"])

    def test_current_contract_authorizes_only_its_exact_external_targets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            contract_path, contract_sha256 = write_contract(repo, standing_contract())
            state = current_state(
                contract_path=contract_path,
                contract_sha256=contract_sha256,
            )
            project_target = str(repo / "dev-flow-source")
            cases = (
                ("git.commit", "origin:refs/heads/main"),
                ("git.push", "origin:refs/heads/main"),
                ("git.tag.push", "dev-flow-v0.4.0"),
                ("github.release", "dev-flow-v0.4.0"),
                ("release.publish", "dev-flow-v0.4.0"),
                ("devflow.source.fast_forward", project_target),
                ("devflow.source.fast_forward_named", project_target),
                ("codex.cache.refresh", "dev-flow@cy-codex-skills"),
                ("plugin.cache.refresh_named", "dev-flow@cy-codex-skills"),
                ("devflow.project.refresh", project_target),
                ("devflow.project.refresh_named", project_target),
            )
            for effect, target in cases:
                with self.subTest(effect=effect):
                    result = resolve_standing_milestone(  # type: ignore[misc]
                        repo,
                        state,
                        requested_effect=effect,
                        requested_target=target,
                    )
                    self.assertEqual(result["decision"], "CONTINUE")
                    self.assertEqual(
                        result["reasonCodes"],
                        ["STANDING_MILESTONE_AUTHORITY_CURRENT"],
                    )
                    self.assertTrue(result["authorityCurrent"])
                    self.assertEqual(result["resolvedTarget"], target)
                    self.assertEqual(result["missingAuthority"], [])
                    self.assertEqual(
                        result["frozenEvidenceDigests"],
                        {
                            "candidate_digest": "b" * 64,
                            "validation_digest": "c" * 64,
                            "review_digest": "d" * 64,
                        },
                    )

    def test_malformed_requested_effects_are_technical_and_never_authorize_push(self) -> None:
        cases: dict[str, object | None] = {
            "missing": None,
            "not-list": "git.push",
            "empty": [],
            "mixed-types": ["git.commit", 7],
            "mixed-authority": [*EXPECTED_REQUESTED_EFFECTS[:-1], "github.pr"],
            "duplicate": [*EXPECTED_REQUESTED_EFFECTS, "git.push"],
            "blank": [*EXPECTED_REQUESTED_EFFECTS[:-1], " "],
            "out-of-order": [
                EXPECTED_REQUESTED_EFFECTS[1],
                EXPECTED_REQUESTED_EFFECTS[0],
                *EXPECTED_REQUESTED_EFFECTS[2:],
            ],
        }
        for name, requested in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                repo = Path(directory)
                contract = standing_contract()
                if requested is None:
                    contract.pop("requestedEffects")
                else:
                    contract["requestedEffects"] = requested
                contract_path, contract_sha256 = write_contract(repo, contract)

                result = resolve_standing_milestone(  # type: ignore[misc]
                    repo,
                    current_state(
                        contract_path=contract_path,
                        contract_sha256=contract_sha256,
                    ),
                    requested_effect="git.push",
                    requested_target="origin:refs/heads/main",
                )

                self.assertEqual(result["decision"], "FAIL_CLOSED_REPAIR")
                self.assertEqual(result["reasonCodes"], ["REQUESTED_EFFECTS_INVALID"])
                self.assertEqual(result["invalidations"], ["contract.requestedEffects"])
                self.assertEqual(result["missingAuthority"], [])
                self.assertFalse(result["authorityCurrent"])
                self.assertIsNone(result["gateKey"])

    def test_contract_target_evidence_failures_are_technical_repairs(self) -> None:
        cases: list[tuple[str, dict[str, object], str, str]] = []
        malformed_ref = standing_contract()
        repository = malformed_ref["repository"]
        self.assertIsInstance(repository, dict)
        repository["ref"] = "refs/heads/main..other"
        cases.append(
            (
                "malformed-ref",
                malformed_ref,
                "STANDING_CONTRACT_IDENTITY_INVALID",
                "contract.repository.ref",
            )
        )
        for name, contract, reason, invalidation in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                repo = Path(directory)
                contract_path, contract_sha256 = write_contract(repo, contract)
                result = resolve_standing_milestone(  # type: ignore[misc]
                    repo,
                    current_state(
                        contract_path=contract_path,
                        contract_sha256=contract_sha256,
                    ),
                    requested_effect="git.push",
                    requested_target="origin:refs/heads/main",
                )
                self.assertEqual(result["decision"], "FAIL_CLOSED_REPAIR")
                self.assertEqual(result["reasonCodes"], [reason])
                self.assertIn(invalidation, result["invalidations"])
                self.assertEqual(result["missingAuthority"], [])
                self.assertIsNone(result["gateKey"])

        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            contract = standing_contract()
            refresh = contract["refreshTargets"]
            self.assertIsInstance(refresh, dict)
            refresh["project"] = str(repo / "declared-but-absent")
            contract_path, contract_sha256 = write_contract(repo, contract)
            result = resolve_standing_milestone(  # type: ignore[misc]
                repo,
                current_state(
                    contract_path=contract_path,
                    contract_sha256=contract_sha256,
                ),
                requested_effect="git.push",
                requested_target="origin:refs/heads/main",
            )

        self.assertEqual(result["decision"], "FAIL_CLOSED_REPAIR")
        self.assertEqual(
            result["reasonCodes"],
            ["STANDING_CONTRACT_TARGET_UNAVAILABLE"],
        )
        self.assertEqual(
            result["invalidations"],
            ["contract.refreshTargets.project:unavailable"],
        )
        self.assertEqual(result["missingAuthority"], [])
        self.assertIsNone(result["gateKey"])

    def test_malformed_or_nonconcrete_effect_requests_never_create_human_gates(self) -> None:
        cases = (
            ("effect-whitespace", " github.pr", "origin:refs/heads/main", "request.effect"),
            ("target-blank", "github.pr", " ", "request.target"),
            ("target-control", "github.pr", "origin\nmain", "request.target"),
            ("unknown-without-target", "github.pr", None, "request.target"),
        )
        for name, effect, target, invalidation in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                repo = Path(directory)
                contract_path, contract_sha256 = write_contract(repo, standing_contract())
                result = resolve_standing_milestone(  # type: ignore[misc]
                    repo,
                    current_state(
                        contract_path=contract_path,
                        contract_sha256=contract_sha256,
                    ),
                    requested_effect=effect,
                    requested_target=target,
                )

                self.assertEqual(result["decision"], "FAIL_CLOSED_REPAIR")
                self.assertEqual(result["reasonCodes"], ["STANDING_REQUEST_INVALID"])
                self.assertIn(invalidation, result["invalidations"])
                self.assertEqual(result["missingAuthority"], [])
                self.assertFalse(result["materialDelta"])
                self.assertIsNone(result["gateKey"])

    def test_current_contract_derives_an_omitted_recognized_effect_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            contract_path, contract_sha256 = write_contract(repo, standing_contract())
            state = current_state(
                contract_path=contract_path,
                contract_sha256=contract_sha256,
            )

            derived = resolve_standing_milestone(  # type: ignore[misc]
                repo,
                state,
                requested_effect="git.commit",
            )
            explicit = resolve_standing_milestone(  # type: ignore[misc]
                repo,
                state,
                requested_effect="git.commit",
                requested_target="origin:refs/heads/main",
            )

        self.assertEqual(derived["decision"], "CONTINUE")
        self.assertEqual(derived["requestedTarget"], "")
        self.assertEqual(derived["resolvedTarget"], "origin:refs/heads/main")
        self.assertEqual(derived["missingAuthority"], [])
        self.assertEqual(derived["requestDigest"], explicit["requestDigest"])
        self.assertEqual(derived["authorityDigest"], explicit["authorityDigest"])

    def test_contract_safety_identity_drift_is_technical_repair(self) -> None:
        cases: list[tuple[str, dict[str, object], str, str]] = []
        missing_exclusion = standing_contract()
        exclusions = list(missing_exclusion["exclusions"])  # type: ignore[arg-type]
        exclusions.remove("game-dev-plugins")
        missing_exclusion["exclusions"] = exclusions
        cases.append(
            (
                "missing-exclusion",
                missing_exclusion,
                "STANDING_CONTRACT_IDENTITY_INVALID",
                "contract.exclusions:game-dev-plugins",
            )
        )

        undeclared_effect = copy.deepcopy(standing_contract())
        undeclared_effect["requestedEffects"] = ["git.commit", "github.pr"]
        cases.append(
            (
                "mixed-requested-effect",
                undeclared_effect,
                "REQUESTED_EFFECTS_INVALID",
                "contract.requestedEffects",
            )
        )

        mismatched_cache = copy.deepcopy(standing_contract())
        refresh_targets = mismatched_cache["refreshTargets"]
        self.assertIsInstance(refresh_targets, dict)
        refresh_targets["cache"] = "other-plugin@other-marketplace"
        cases.append(
            (
                "cache-identity",
                mismatched_cache,
                "STANDING_CONTRACT_IDENTITY_INVALID",
                "contract.refreshTargets.cache",
            )
        )
        missing_expectation = copy.deepcopy(standing_contract())
        publication = missing_expectation["publication"]
        self.assertIsInstance(publication, dict)
        publication.pop("assetExpectation")
        cases.append(
            (
                "asset-expectation-missing",
                missing_expectation,
                "STANDING_CONTRACT_IDENTITY_INVALID",
                "contract.publication.assetExpectation",
            )
        )
        expectation_outside_write_set = copy.deepcopy(standing_contract())
        write_set = expectation_outside_write_set["writeSet"]
        self.assertIsInstance(write_set, list)
        write_set.remove(ASSET_EXPECTATION)
        cases.append(
            (
                "asset-expectation-outside-write-set",
                expectation_outside_write_set,
                "STANDING_CONTRACT_IDENTITY_INVALID",
                "contract.publication.assetExpectation:writeSet",
            )
        )

        for name, contract, expected_reason, expected_invalidation in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                repo = Path(directory)
                contract_path, contract_sha256 = write_contract(repo, contract)
                result = resolve_standing_milestone(  # type: ignore[misc]
                    repo,
                    current_state(
                        contract_path=contract_path,
                        contract_sha256=contract_sha256,
                    ),
                    requested_effect="git.push",
                    requested_target="origin:refs/heads/main",
                )

                self.assertEqual(result["decision"], "FAIL_CLOSED_REPAIR")
                self.assertEqual(result["reasonCodes"], [expected_reason])
                self.assertIn(expected_invalidation, result["invalidations"])
                self.assertEqual(result["missingAuthority"], [])

    def test_repo_local_but_noncanonical_contract_path_is_not_trusted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            contract = standing_contract()
            payload = json.dumps(contract, sort_keys=True, separators=(",", ":"))
            relative = "tmp/standing-contract.json"
            path = repo / relative
            path.parent.mkdir(parents=True)
            path.write_text(payload, encoding="utf-8")
            result = resolve_standing_milestone(  # type: ignore[misc]
                repo,
                current_state(
                    contract_path=relative,
                    contract_sha256=hashlib.sha256(payload.encode()).hexdigest(),
                ),
                requested_effect="git.push",
                requested_target="origin:refs/heads/main",
            )

        self.assertEqual(result["decision"], "FAIL_CLOSED_REPAIR")
        self.assertEqual(result["reasonCodes"], ["STANDING_CONTRACT_PATH_UNTRUSTED"])
        self.assertEqual(result["invalidations"], ["contract.path"])
        self.assertEqual(result["missingAuthority"], [])

    def test_unknown_standing_status_is_technical_state_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            contract_path, contract_sha256 = write_contract(repo, standing_contract())
            result = resolve_standing_milestone(  # type: ignore[misc]
                repo,
                bound_state(
                    status="ready-ish",
                    contract_path=contract_path,
                    contract_sha256=contract_sha256,
                ),
                requested_effect="git.push",
                requested_target="origin:refs/heads/main",
            )

        self.assertEqual(result["decision"], "FAIL_CLOSED_REPAIR")
        self.assertEqual(result["reasonCodes"], ["STANDING_MILESTONE_STATUS_INVALID"])
        self.assertEqual(result["invalidations"], ["standing_milestone.status"])
        self.assertEqual(result["missingAuthority"], [])

    def test_declared_contract_distinguishes_freeze_repair_from_authority_delta(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            contract_path, contract_sha256 = write_contract(repo, standing_contract())
            state = bound_state(
                status="declared",
                contract_path=contract_path,
                contract_sha256=contract_sha256,
            )
            cases = (
                ("github.pr", "origin:refs/heads/main", "effect:github.pr"),
                ("git.push", "origin:refs/heads/other", "target:origin:refs/heads/other"),
            )
            for effect, target, missing in cases:
                with self.subTest(effect=effect, target=target):
                    result = resolve_standing_milestone(  # type: ignore[misc]
                        repo,
                        state,
                        requested_effect=effect,
                        requested_target=target,
                    )
                    self.assertEqual(result["decision"], "AWAIT_HUMAN")
                    self.assertEqual(result["missingAuthority"], [missing])
                    self.assertTrue(result["materialDelta"])
                    self.assertRegex(str(result["gateKey"]), r"^[0-9a-f]{64}$")

    def test_duplicate_contract_keys_fail_closed_as_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            contract = standing_contract()
            relative = "openspec/changes/centralize-devflow-authority-delta/evidence/standing-contract.json"
            path = repo / relative
            path.parent.mkdir(parents=True)
            payload = json.dumps(contract, sort_keys=True, separators=(",", ":"))
            needle = '"goal":"Reduce false Human Gates while preserving fail-closed safety."'
            payload = payload.replace(needle, f"{needle},{needle}", 1)
            path.write_text(payload, encoding="utf-8")
            result = resolve_standing_milestone(  # type: ignore[misc]
                repo,
                current_state(
                    contract_path=relative,
                    contract_sha256=hashlib.sha256(payload.encode()).hexdigest(),
                ),
                requested_effect="git.push",
                requested_target="origin:refs/heads/main",
            )

        self.assertEqual(result["decision"], "FAIL_CLOSED_REPAIR")
        self.assertEqual(result["reasonCodes"], ["STANDING_CONTRACT_INVALID_JSON"])
        self.assertEqual(result["invalidations"], ["contract.document"])
        self.assertEqual(result["missingAuthority"], [])

    def test_bound_identity_and_frozen_evidence_drift_are_never_human_gates(self) -> None:
        cases = (
            ("sha", standing_contract(), {"contract_sha256": "0" * 64}, "STANDING_CONTRACT_SHA256_DRIFT"),
            (
                "goal",
                standing_contract(goalId="different-goal"),
                {},
                "STANDING_CONTRACT_GOAL_DRIFT",
            ),
            (
                "change",
                standing_contract(change="different-change"),
                {},
                "STANDING_CONTRACT_CHANGE_DRIFT",
            ),
            (
                "candidate",
                standing_contract(),
                {"candidate_digest": "not-a-sha256"},
                "FROZEN_EVIDENCE_INCOMPLETE",
            ),
        )
        for name, contract, state_overrides, reason in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                repo = Path(directory)
                contract_path, contract_sha256 = write_contract(repo, contract)
                state = current_state(
                    contract_path=contract_path,
                    contract_sha256=contract_sha256,
                )
                standing = state["standing_milestone"]
                self.assertIsInstance(standing, dict)
                standing.update(state_overrides)
                result = resolve_standing_milestone(  # type: ignore[misc]
                    repo,
                    state,
                    requested_effect="git.push",
                    requested_target="origin:refs/heads/main",
                )
                self.assertEqual(result["decision"], "FAIL_CLOSED_REPAIR")
                self.assertEqual(result["reasonCodes"], [reason])
                self.assertEqual(result["missingAuthority"], [])
                self.assertFalse(result["materialDelta"])
                self.assertIsNone(result["gateKey"])

    def test_policy_effect_aliases_resolve_to_the_same_sealed_targets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            contract_path, contract_sha256 = write_contract(repo, standing_contract())
            state = current_state(
                contract_path=contract_path,
                contract_sha256=contract_sha256,
            )
            project_target = str(repo / "dev-flow-source")
            cases = (
                ("release.publish", "dev-flow-v0.4.0"),
                ("plugin.cache.refresh_named", "dev-flow@cy-codex-skills"),
                ("devflow.project.refresh_named", project_target),
            )
            for effect, target in cases:
                with self.subTest(effect=effect):
                    result = resolve_standing_milestone(  # type: ignore[misc]
                        repo,
                        state,
                        requested_effect=effect,
                        requested_target=target,
                    )
                    self.assertEqual(result["decision"], "CONTINUE")
                    self.assertEqual(result["resolvedTarget"], target)
                    self.assertTrue(result["authorityCurrent"])

    def test_same_identity_resolution_is_deterministic_and_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            contract_path, contract_sha256 = write_contract(repo, standing_contract())
            state = current_state(
                contract_path=contract_path,
                contract_sha256=contract_sha256,
            )
            before = sorted(path.relative_to(repo) for path in repo.rglob("*"))
            first = resolve_standing_milestone(  # type: ignore[misc]
                repo,
                state,
                requested_effect="github.release",
                requested_target="dev-flow-v0.4.0",
            )
            second = resolve_standing_milestone(  # type: ignore[misc]
                repo,
                state,
                requested_effect="github.release",
                requested_target="dev-flow-v0.4.0",
            )
            after = sorted(path.relative_to(repo) for path in repo.rglob("*"))

        self.assertEqual(first, second)
        self.assertEqual(before, after)

    def test_current_candidate_refuses_local_promotion_after_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            contract_path, contract_sha256 = write_contract(repo, standing_contract())
            result = resolve_standing_milestone(  # type: ignore[misc]
                repo,
                current_state(
                    contract_path=contract_path,
                    contract_sha256=contract_sha256,
                ),
                requested_effect="release.promote_local",
                requested_target="plugins/dev-flow",
            )

        self.assertEqual(result["decision"], "FAIL_CLOSED_REPAIR")
        self.assertEqual(result["reasonCodes"], ["LOCAL_PROMOTION_AFTER_CANDIDATE_FREEZE"])
        self.assertEqual(result["invalidations"], ["standing_milestone.status"])
        self.assertEqual(result["missingAuthority"], [])
        self.assertFalse(result["authorityCurrent"])

    def test_human_gate_key_invalidates_when_contract_identity_changes(self) -> None:
        gate_keys: list[str] = []
        contract_digests: list[str] = []
        for version in ("0.4.0", "0.4.1"):
            with tempfile.TemporaryDirectory() as directory:
                repo = Path(directory)
                contract = standing_contract()
                plugin = contract["plugin"]
                self.assertIsInstance(plugin, dict)
                plugin["version"] = version
                contract_path, contract_sha256 = write_contract(repo, contract)
                result = resolve_standing_milestone(  # type: ignore[misc]
                    repo,
                    current_state(
                        contract_path=contract_path,
                        contract_sha256=contract_sha256,
                    ),
                    requested_effect="github.pr",
                    requested_target="origin:refs/heads/main",
                )
                self.assertEqual(result["decision"], "AWAIT_HUMAN")
                gate_keys.append(str(result["gateKey"]))
                contract_digests.append(str(result["contractDigest"]))

        self.assertEqual(len(set(contract_digests)), 2)
        self.assertEqual(len(set(gate_keys)), 2)

    def test_human_gate_uses_central_resolver_bindings_and_canonical_key(self) -> None:
        from workflow_authority_gate import canonical_authority_gate_key

        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            contract_path, contract_sha256 = write_contract(repo, standing_contract())
            result = resolve_standing_milestone(  # type: ignore[misc]
                repo,
                current_state(
                    contract_path=contract_path,
                    contract_sha256=contract_sha256,
                ),
                requested_effect="github.pr",
                requested_target="origin:refs/heads/main",
            )

        self.assertEqual(result["decision"], "AWAIT_HUMAN")
        for field in (
            "requestDigest",
            "authorityDigest",
            "evidenceDigest",
            "standingContractDigest",
        ):
            self.assertRegex(str(result[field]), r"^[0-9a-f]{64}$")
        expected = canonical_authority_gate_key(
            missing_authority=result["missingAuthority"],
            authority_contract_sha256=result["authorityDigest"],
            evidence_sha256=result["evidenceDigest"],
            request_sha256=result["requestDigest"],
            standing_contract_sha256=result["standingContractDigest"],
        )
        self.assertEqual("sha256:" + str(result["gateKey"]), expected)


if __name__ == "__main__":
    unittest.main()
