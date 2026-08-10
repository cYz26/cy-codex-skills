import copy
import hashlib
import json
import re
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
FIXTURES = PLUGIN_ROOT / "fixtures" / "milestone-external-effects"
MILESTONE_CLI = SCRIPTS / "milestone_external_effects.py"
TERMINAL_SCHEMA = PLUGIN_ROOT / "schemas" / "milestone-terminal-receipt-v1.schema.json"
CANDIDATE_SCHEMA = PLUGIN_ROOT / "schemas" / "milestone-candidate-manifest-v1.schema.json"
VALIDATION_SCHEMA = PLUGIN_ROOT / "schemas" / "milestone-validation-receipt-v1.schema.json"
REVIEW_SCHEMA = PLUGIN_ROOT / "schemas" / "milestone-review-receipt-v1.schema.json"
VALIDATION_EVIDENCE_SCHEMA = (
    PLUGIN_ROOT / "schemas" / "milestone-validation-evidence-v1.schema.json"
)
REVIEW_EVIDENCE_SCHEMA = (
    PLUGIN_ROOT / "schemas" / "milestone-review-evidence-v1.schema.json"
)
sys.path.insert(0, str(SCRIPTS))

try:
    import workflow_milestone_external_effects as milestone_module
    from workflow_milestone_external_effects import (
        apply_milestone_external_effects,
        plan_milestone_external_effects,
        verify_milestone_external_effects,
    )
except ImportError as error:
    MILESTONE_IMPORT_ERROR = error
    apply_milestone_external_effects = None
    plan_milestone_external_effects = None
    simulate_milestone_execution_ledger = None
    verify_milestone_external_effects = None
else:
    MILESTONE_IMPORT_ERROR = None
    simulate_milestone_execution_ledger = getattr(
        milestone_module, "simulate_milestone_execution_ledger", None
    )


def canonical_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


CYCLE_EDGE_SENTINEL = "devflow-canonical-cycle-edge-v1"
CANONICAL_STATE = Path(".planning/devflow/STATE.md")
DEVFLOW_CONFIG = Path(".dev-flow.json")


def normalized_state_bytes(payload: bytes) -> bytes:
    text = payload.decode("utf-8")
    names = ("candidate_digest", "validation_digest", "review_digest")
    for name in names:
        pattern = rf"(?m)^(  {name}:).*$"
        text, count = re.subn(pattern, rf"\1 {CYCLE_EDGE_SENTINEL}", text)
        if count != 1:
            raise AssertionError(f"canonical STATE must contain exactly one {name}")
    return text.encode("utf-8")


def candidate_projection_digest(candidate: dict[str, object], state_bytes: bytes) -> str:
    projected = copy.deepcopy(candidate)
    normalized = normalized_state_bytes(state_bytes)
    state_records = [
        item
        for item in projected["files"]
        if item.get("path") == CANONICAL_STATE.as_posix()
    ]
    if len(state_records) != 1:
        raise AssertionError("candidate must contain canonical STATE exactly once")
    state_records[0]["size"] = len(normalized)
    state_records[0]["sha256"] = hashlib.sha256(normalized).hexdigest()
    payload: dict[str, object] = {
        "files": projected["files"],
        "assets": projected["assets"],
    }
    if "deletions" in projected:
        payload["deletions"] = projected["deletions"]
    projected["payloadDigest"] = canonical_digest(payload)
    return canonical_digest(projected)


def validation_projection_digest(
    validation: dict[str, object], candidate_binding: str
) -> str:
    projected = copy.deepcopy(validation)
    projected["candidateDigest"] = candidate_binding
    return canonical_digest(projected)


def review_projection_digest(review: dict[str, object], candidate_binding: str) -> str:
    projected = copy.deepcopy(review)
    projected["candidateDigest"] = candidate_binding
    projected["reviewedDiffDigest"] = candidate_binding
    return canonical_digest(projected)


class SimulatedBoundaryCrash(RuntimeError):
    """Represents process loss after a true external boundary completed."""


class BoundaryHarness:
    """Fake only GitHub, Codex cache, and project-process boundaries.

    The public milestone seam receives this SDK-like mapping. Each callable
    accepts one request mapping and returns one result mapping. Git is
    deliberately absent: tests use a real repository and bare remote.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.publication: dict[str, object] | None = None
        self.source: dict[str, object] | None = None
        self.cache: dict[str, object] | None = None
        self.project: dict[str, object] | None = None
        self.publication_failure = False
        self.publication_readback_incomplete = False
        self.publication_asset_mismatch = False
        self.source_already_current = False
        self.cache_mismatch = False
        self.cache_failures_before_effect = 0
        self.project_plan_drift = False
        self.project_mismatch = False
        self.crash_before: set[str] = set()
        self.crash_after: set[str] = set()
        self.crash_after_effect: set[str] = set()

    def mapping(self) -> dict[str, object]:
        return {
            "publication_readback": self.publication_readback,
            "publication_apply": self.publication_apply,
            "publication_diagnose": self.publication_diagnose,
            "publication_remediate": self.publication_remediate,
            "source_plan": self.source_plan,
            "source_apply": self.source_apply,
            "source_verify": self.source_verify,
            "cache_plan": self.cache_plan,
            "cache_apply": self.cache_apply,
            "cache_verify": self.cache_verify,
            "project_plan": self.project_plan,
            "project_apply": self.project_apply,
            "project_verify": self.project_verify,
            "after_irreversible_effect": self.after_irreversible_effect,
        }

    def count(self, name: str) -> int:
        return sum(call_name == name for call_name, _ in self.calls)

    def mutating_count(self) -> int:
        mutating = {
            "publication_apply",
            "publication_remediate",
            "source_apply",
            "cache_apply",
            "project_apply",
        }
        return sum(name in mutating for name, _ in self.calls)

    def _request(self, name: str, request: object) -> dict[str, object]:
        if not isinstance(request, dict):
            raise AssertionError(f"{name} boundary request must be a mapping")
        payload = copy.deepcopy(request)
        self.calls.append((name, payload))
        return payload

    def _identity(self, payload: dict[str, object]) -> dict[str, object]:
        identity = payload.get("identity")
        if not isinstance(identity, dict):
            raise AssertionError("boundary request must bind an identity mapping")
        return copy.deepcopy(identity)

    def _crash_if_configured(self, name: str) -> None:
        if name in self.crash_after:
            self.crash_after.remove(name)
            raise SimulatedBoundaryCrash(name)

    def _crash_before_if_configured(self, name: str) -> None:
        if name in self.crash_before:
            self.crash_before.remove(name)
            raise SimulatedBoundaryCrash(name)

    def after_irreversible_effect(self, request: object) -> dict[str, object]:
        payload = self._request("after_irreversible_effect", request)
        effect = str(payload.get("effect") or "")
        if effect in self.crash_after_effect:
            self.crash_after_effect.remove(effect)
            raise SimulatedBoundaryCrash(effect)
        return {"ok": True, "effect": effect}

    def publication_readback(self, request: object) -> dict[str, object]:
        self._request("publication_readback", request)
        if self.publication is None:
            return {"ok": True, "status": "missing", "identity": None}
        identity = copy.deepcopy(self.publication)
        if self.publication_readback_incomplete:
            identity.pop("assets", None)
            return {
                "ok": True,
                "status": "pending",
                "identity": identity,
                "sameIdentity": True,
                "issues": ["release_asset_names_mismatch"],
            }
        if self.publication_asset_mismatch:
            assets = identity.get("assets")
            if isinstance(assets, list) and assets:
                assets[0]["sha256"] = "0" * 64
        return {
            "ok": True,
            "status": "published",
            "identity": identity,
            "sameIdentity": identity == self.publication,
        }

    def publication_apply(self, request: object) -> dict[str, object]:
        payload = self._request("publication_apply", request)
        identity = self._identity(payload)
        if self.publication_failure:
            return {
                "ok": False,
                "status": "workflow_failed",
                "identity": identity,
                "diagnostic": "synthetic tag-bound workflow failure",
            }
        self.publication = identity
        self._crash_if_configured("publication_apply")
        return {"ok": True, "status": "published", "identity": copy.deepcopy(identity)}

    def publication_diagnose(self, request: object) -> dict[str, object]:
        payload = self._request("publication_diagnose", request)
        return {"ok": True, "status": "diagnosed", "identity": self._identity(payload)}

    def publication_remediate(self, request: object) -> dict[str, object]:
        payload = self._request("publication_remediate", request)
        return {"ok": False, "status": "not_applicable", "identity": self._identity(payload)}

    def source_plan(self, request: object) -> dict[str, object]:
        payload = self._request("source_plan", request)
        return {
            "ok": True,
            "status": "already_current" if self.source_already_current else "planned",
            "target": payload.get("target"),
            "identity": self._identity(payload),
            "planDigest": canonical_digest(payload),
        }

    def source_apply(self, request: object) -> dict[str, object]:
        payload = self._request("source_apply", request)
        self.source = self._identity(payload)
        self._crash_if_configured("source_apply")
        return {"ok": True, "status": "fast_forwarded", "identity": copy.deepcopy(self.source)}

    def source_verify(self, request: object) -> dict[str, object]:
        payload = self._request("source_verify", request)
        if self.source is None and not self.source_already_current:
            return {"ok": False, "status": "not_current", "reason": "source_not_current"}
        identity = copy.deepcopy(self.source or self._identity(payload))
        return {"ok": True, "status": "verified", "identity": identity}

    def cache_plan(self, request: object) -> dict[str, object]:
        payload = self._request("cache_plan", request)
        return {
            "ok": True,
            "status": "planned",
            "target": payload.get("target"),
            "identity": self._identity(payload),
            "planDigest": canonical_digest(payload),
        }

    def cache_apply(self, request: object) -> dict[str, object]:
        payload = self._request("cache_apply", request)
        self._crash_before_if_configured("cache_apply")
        if self.cache_failures_before_effect:
            self.cache_failures_before_effect -= 1
            return {
                "ok": False,
                "status": "technical_failure_before_effect",
                "identity": self._identity(payload),
            }
        self.cache = self._identity(payload)
        self._crash_if_configured("cache_apply")
        return {"ok": True, "status": "applied", "identity": copy.deepcopy(self.cache)}

    def cache_verify(self, request: object) -> dict[str, object]:
        payload = self._request("cache_verify", request)
        if self.cache is None:
            return {
                "ok": False,
                "status": "not_current",
                "reason": "cache_refresh_not_current",
            }
        identity = copy.deepcopy(self.cache)
        if self.cache_mismatch:
            identity["version"] = "0.4.1"
        return {"ok": True, "status": "verified", "identity": identity}

    def project_plan(self, request: object) -> dict[str, object]:
        payload = self._request("project_plan", request)
        if self.project_plan_drift:
            return {
                "ok": False,
                "status": "plan_drift",
                "target": payload.get("target"),
                "identity": self._identity(payload),
                "planDigest": "f" * 64,
            }
        result = {
            "ok": True,
            "status": "planned",
            "target": payload.get("target"),
            "identity": self._identity(payload),
            "planDigest": canonical_digest(payload),
        }
        return result

    def project_apply(self, request: object) -> dict[str, object]:
        payload = self._request("project_apply", request)
        self.project = self._identity(payload)
        self._crash_if_configured("project_apply")
        return {"ok": True, "status": "applied", "identity": copy.deepcopy(self.project)}

    def project_verify(self, request: object) -> dict[str, object]:
        payload = self._request("project_verify", request)
        if self.project is None:
            return {
                "ok": False,
                "status": "not_current",
                "reason": "project_refresh_not_current",
            }
        identity = copy.deepcopy(self.project)
        if self.project_mismatch:
            identity["commit"] = "1" * 40
        return {"ok": True, "status": "verified", "identity": identity}


class MilestoneExternalEffectsPublicSeamTests(unittest.TestCase):
    def test_public_milestone_module_and_three_seams_exist(self):
        self.assertIsNone(
            MILESTONE_IMPORT_ERROR,
            "expected RED until workflow_milestone_external_effects.py implements "
            "plan_milestone_external_effects, apply_milestone_external_effects, "
            f"and verify_milestone_external_effects: {MILESTONE_IMPORT_ERROR}",
        )
        self.assertTrue(callable(plan_milestone_external_effects))
        self.assertTrue(callable(apply_milestone_external_effects))
        self.assertTrue(callable(verify_milestone_external_effects))
        self.assertTrue(callable(simulate_milestone_execution_ledger))

    def test_cli_exposes_plan_advance_verify_and_guarded_apply(self):
        self.assertTrue(MILESTONE_CLI.is_file())
        source = MILESTONE_CLI.read_text()
        for command in ("plan", "advance", "verify"):
            self.assertIn(f'subparsers.add_parser("{command}")', source)
        self.assertIn('advance.add_argument("--apply"', source)
        self.assertIn("EXPLICIT_EXECUTION_SAFEGUARD_REQUIRED", source)


@unittest.skipIf(MILESTONE_IMPORT_ERROR is not None, "public milestone seam is intentionally RED")
class MilestoneExternalEffectsTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory(prefix="devflow-milestone-")
        self.root = Path(self.temporary_directory.name)
        self.repo = self.root / "work"
        self.remote = self.root / "origin.git"
        self.receipts = Path(
            ".planning/devflow/milestone-external-effects/"
            "dev-flow-authority-delta-v0.4.0"
        )
        (self.repo / self.receipts).mkdir(parents=True)
        self.project = self.root / "source-project"
        self.project.mkdir()
        self.run_git("init", "--bare", str(self.remote))
        self.run_git("init", "-b", "main", str(self.repo))
        self.run_git("-C", str(self.repo), "config", "user.name", "DevFlow Tests")
        self.run_git("-C", str(self.repo), "config", "user.email", "devflow@example.invalid")
        fixture_contract = json.loads((FIXTURES / "standing-contract-v1.json").read_text())
        self.change = str(fixture_contract["change"])
        openspec = self.repo / "openspec" / "changes" / self.change
        (openspec / "specs" / "milestone-external-effects").mkdir(parents=True)
        (openspec / ".openspec.yaml").write_text("schema: spec-driven\n")
        (openspec / "proposal.md").write_text("# Canonical milestone proposal\n")
        (openspec / "design.md").write_text("# Canonical milestone design\n")
        (openspec / "tasks.md").write_text("# Canonical milestone tasks\n")
        (openspec / "specs" / "milestone-external-effects" / "spec.md").write_text(
            "# Canonical milestone specification\n"
        )
        (self.repo / DEVFLOW_CONFIG).write_text(
            json.dumps(
                {"projectContract": 8, "workflow": {"mode": "full-openspec"}},
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        (self.repo / "README.md").write_text("milestone fixture\n")
        (self.repo / "obsolete.txt").write_text("tracked legacy bytes\n")
        self.run_git(
            "-C",
            str(self.repo),
            "add",
            DEVFLOW_CONFIG.as_posix(),
            "README.md",
            "obsolete.txt",
            "openspec",
        )
        self.run_git("-C", str(self.repo), "commit", "-qm", "fixture base")
        self.run_git("-C", str(self.repo), "remote", "add", "origin", str(self.remote))
        self.run_git("-C", str(self.repo), "push", "-q", "-u", "origin", "main")
        self.base = self.git_output(self.repo, "rev-parse", "HEAD")
        self.contract = self.load_contract()
        self.include_deletions = True
        self.candidate_deletions: list[str] = []
        self.write_candidate_files()
        self.write_canonical_state(
            candidate_digest="0" * 64,
            validation_digest="0" * 64,
            review_digest="0" * 64,
        )
        provisional_candidate = self.candidate_manifest()
        provisional_validation = self.validation_receipt_for(provisional_candidate)
        provisional_review = self.review_receipt_for(provisional_candidate)
        candidate_binding = candidate_projection_digest(
            provisional_candidate, (self.repo / CANONICAL_STATE).read_bytes()
        )
        self.write_canonical_state(
            candidate_digest=candidate_binding,
            validation_digest=validation_projection_digest(
                provisional_validation, candidate_binding
            ),
            review_digest=review_projection_digest(provisional_review, candidate_binding),
        )
        self.candidate = self.candidate_manifest()
        self.validation = self.validation_receipt()
        self.review = self.review_receipt()
        self.assertEqual(
            self.canonical_state_values()["candidate_digest"],
            candidate_projection_digest(
                self.candidate, (self.repo / CANONICAL_STATE).read_bytes()
            ),
        )
        self.assertEqual(
            self.canonical_state_values()["validation_digest"],
            validation_projection_digest(
                self.validation, self.canonical_state_values()["candidate_digest"]
            ),
        )
        self.assertEqual(
            self.canonical_state_values()["review_digest"],
            review_projection_digest(
                self.review, self.canonical_state_values()["candidate_digest"]
            ),
        )
        self.long_run = json.loads((FIXTURES / "long-run-v1.json").read_text())
        self.boundary = BoundaryHarness()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def run_git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            text=True,
            capture_output=True,
            check=check,
        )

    def git_output(self, repo: Path, *args: str) -> str:
        return self.run_git("-C", str(repo), *args).stdout.strip()

    def load_contract(self) -> dict[str, object]:
        contract = json.loads((FIXTURES / "standing-contract-v1.json").read_text())
        contract["repository"]["remoteUrl"] = str(self.remote)
        contract["repository"]["expectedBase"] = self.base
        contract["refreshTargets"]["project"] = str(self.project)
        self.contract_relative = Path(
            "openspec/changes"
        ) / str(contract["change"]) / "evidence" / "standing-milestone-contract.json"
        openspec_root = Path("openspec/changes") / str(contract["change"])
        self.validation_evidence_relative = (
            openspec_root / "evidence" / "final-validation-evidence.json"
        )
        self.review_evidence_relative = (
            openspec_root / "evidence" / "final-independent-review.json"
        )
        self.asset_expectation_relative = (
            openspec_root / "evidence" / "release-assets.json"
        )
        contract["publication"]["assetExpectation"] = (
            self.asset_expectation_relative.as_posix()
        )
        contract["requestedEffects"] = [
            "git.commit",
            "git.push",
            "git.tag.push",
            "github.release",
            "devflow.source.fast_forward",
            "codex.cache.refresh",
            "devflow.project.refresh",
        ]
        contract["writeSet"] = sorted(
            [
                *(
                    path
                    for path in contract["writeSet"]
                    if not str(path).startswith("release-assets/")
                ),
                CANONICAL_STATE.as_posix(),
                self.contract_relative.as_posix(),
                self.validation_evidence_relative.as_posix(),
                self.review_evidence_relative.as_posix(),
                self.asset_expectation_relative.as_posix(),
                (openspec_root / ".openspec.yaml").as_posix(),
                (openspec_root / "proposal.md").as_posix(),
                (openspec_root / "design.md").as_posix(),
                (openspec_root / "tasks.md").as_posix(),
                (
                    openspec_root
                    / "specs"
                    / "milestone-external-effects"
                    / "spec.md"
                ).as_posix(),
            ]
        )
        return contract

    def write_candidate_files(self) -> None:
        payloads = {
            ".github/workflows/publish-dev-flow.yml": "name: publish-dev-flow\non: push\n",
            "dev/plugins/dev-flow/.codex-plugin/plugin.json": '{"name":"dev-flow","version":"0.4.0"}\n',
            "feature.txt": "central authority delta\n",
            "plugins/dev-flow/.codex-plugin/plugin.json": '{"name":"dev-flow","version":"0.4.0"}\n',
            f"openspec/changes/{self.change}/.openspec.yaml": (
                "schema: spec-driven\n# approved milestone candidate\n"
            ),
            f"openspec/changes/{self.change}/proposal.md": (
                "# Canonical milestone proposal\n\nApproved candidate.\n"
            ),
            f"openspec/changes/{self.change}/design.md": (
                "# Canonical milestone design\n\nApproved candidate.\n"
            ),
            f"openspec/changes/{self.change}/tasks.md": (
                "# Canonical milestone tasks\n\n- [x] implementation verified\n"
            ),
            (
                f"openspec/changes/{self.change}/specs/"
                "milestone-external-effects/spec.md"
            ): "# Canonical milestone specification\n\nApproved candidate.\n",
            self.validation_evidence_relative.as_posix(): (
                json.dumps(self.validation_evidence_document(), indent=2, sort_keys=True)
                + "\n"
            ),
            self.review_evidence_relative.as_posix(): (
                json.dumps(self.review_evidence_document(), indent=2, sort_keys=True)
                + "\n"
            ),
            self.asset_expectation_relative.as_posix(): (
                '{"kind":"fixture-release-asset-expectation"}\n'
            ),
        }
        self.assertEqual(
            sorted(payloads),
            sorted(
                set(self.contract["writeSet"])
                - {CANONICAL_STATE.as_posix(), self.contract_relative.as_posix()}
            ),
        )
        for relative, content in payloads.items():
            path = self.repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        asset_payloads = {
            "dev-flow-0.4.0.release-manifest.json": '{"plugin":"dev-flow","version":"0.4.0"}\n',
            "dev-flow-0.4.0.sha256": "fixture checksums\n",
            "dev-flow-0.4.0.zip": "fixture zip bytes\n",
            "dev-flow-v0.4.0.md": "# DevFlow 0.4.0\n",
            "devflow_runtime.MANIFEST.json": '{"schemaVersion":"2.0"}\n',
            "devflow_runtime.pyz": "fixture pyz bytes\n",
            "devflow_runtime.sha256": "fixture runtime checksum\n",
        }
        asset_root = self.repo / self.receipts / "release-assets"
        asset_root.mkdir()
        for name, content in asset_payloads.items():
            (asset_root / name).write_text(content)
        contract_path = self.repo / self.contract_relative
        contract_path.parent.mkdir(parents=True, exist_ok=True)
        contract_path.write_text(json.dumps(self.contract, indent=2, sort_keys=True) + "\n")

    def write_canonical_state(
        self,
        *,
        candidate_digest: str,
        validation_digest: str,
        review_digest: str,
        stage: str = "external_effects",
        change_status: str | None = None,
        standing_status: str = "current",
        goal_id: str | None = None,
        change_id: str | None = None,
        contract_sha256: str | None = None,
        verification_passed: bool = True,
    ) -> None:
        contract_bytes = (self.repo / self.contract_relative).read_bytes()
        state = self.repo / CANONICAL_STATE
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(
            "---\n"
            'workflow_version: "0.4.0"\n'
            "project_mode: brownfield\n"
            f"current_stage: {stage}\n"
            "current_change:\n"
            f"  id: {change_id or self.contract['change']}\n"
            f"  status: {change_status or stage}\n"
            "goal_gate:\n"
            "  required: true\n"
            f"  id: {goal_id or self.contract['goalId']}\n"
            "  status: active\n"
            "  reason: fixture-standing-milestone\n"
            "standing_milestone:\n"
            f"  status: {standing_status}\n"
            f"  contract_path: {self.contract_relative.as_posix()}\n"
            "  contract_sha256: "
            f"{contract_sha256 or hashlib.sha256(contract_bytes).hexdigest()}\n"
            f"  goal_id: {goal_id or self.contract['goalId']}\n"
            f"  change_id: {change_id or self.contract['change']}\n"
            f"  candidate_digest: {candidate_digest}\n"
            f"  validation_digest: {validation_digest}\n"
            f"  review_digest: {review_digest}\n"
            "gates:\n"
            "  spec_approved: true\n"
            "  plan_written: true\n"
            "  implementation_done: true\n"
            f"  verification_passed: {str(verification_passed).lower()}\n"
            "  state_updated: true\n"
            "---\n"
            "# Hermetic canonical DevFlow state\n"
        )

    def canonical_state_values(self) -> dict[str, str]:
        values: dict[str, str] = {}
        for line in (self.repo / CANONICAL_STATE).read_text().splitlines():
            match = re.fullmatch(
                r"  (candidate_digest|validation_digest|review_digest): (.+)", line
            )
            if match:
                values[match.group(1)] = match.group(2)
        return values

    def refreeze_contract(self, contract: dict[str, object]) -> None:
        self.contract = copy.deepcopy(contract)
        (self.repo / self.contract_relative).write_text(
            json.dumps(self.contract, indent=2, sort_keys=True) + "\n"
        )
        self.refreeze_supplied_evidence()

    def declare_tracked_deletion(
        self, relative: str = "obsolete.txt", *, remove_from_worktree: bool = True
    ) -> None:
        contract = copy.deepcopy(self.contract)
        contract["writeSet"] = sorted({*contract["writeSet"], relative})
        self.candidate_deletions = sorted({*self.candidate_deletions, relative})
        path = self.repo / relative
        if remove_from_worktree:
            path.unlink()
        self.refreeze_contract(contract)

    def refreeze_supplied_evidence(
        self,
        *,
        validation_projection: dict[str, object] | None = None,
        review_projection: dict[str, object] | None = None,
    ) -> None:
        self.write_canonical_state(
            candidate_digest="0" * 64,
            validation_digest="0" * 64,
            review_digest="0" * 64,
        )
        provisional_candidate = self.candidate_manifest()
        provisional_validation = self.validation_receipt_for(
            provisional_candidate, projection=validation_projection
        )
        provisional_review = self.review_receipt_for(
            provisional_candidate, projection=review_projection
        )
        candidate_binding = candidate_projection_digest(
            provisional_candidate, (self.repo / CANONICAL_STATE).read_bytes()
        )
        self.write_canonical_state(
            candidate_digest=candidate_binding,
            validation_digest=validation_projection_digest(
                provisional_validation, candidate_binding
            ),
            review_digest=review_projection_digest(
                provisional_review, candidate_binding
            ),
        )
        self.candidate = self.candidate_manifest()
        self.validation = self.validation_receipt_for(
            self.candidate, projection=validation_projection
        )
        self.review = self.review_receipt_for(
            self.candidate, projection=review_projection
        )

    def candidate_manifest(self) -> dict[str, object]:
        files: list[dict[str, object]] = []
        for relative in self.contract["writeSet"]:
            if relative in self.candidate_deletions:
                continue
            path = self.repo / relative
            mode = "100755" if path.stat().st_mode & stat.S_IXUSR else "100644"
            files.append(
                {
                    "path": relative,
                    "mode": mode,
                    "size": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
        assets = []
        for name in self.contract["publication"]["assets"]:
            path = self.repo / self.receipts / "release-assets" / name
            assets.append(
                {
                    "name": name,
                    "size": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
        payload: dict[str, object] = {"files": files, "assets": assets}
        if self.include_deletions:
            payload["deletions"] = list(self.candidate_deletions)
        payload_digest = canonical_digest(payload)
        candidate = {
            "schemaVersion": "1.0",
            "contractId": self.contract["contractId"],
            "goalId": self.contract["goalId"],
            "change": self.contract["change"],
            "milestone": self.contract["milestone"],
            "plugin": copy.deepcopy(self.contract["plugin"]),
            "expectedBase": self.base,
            "files": files,
            "assetDirectory": "release-assets",
            "assets": assets,
            "payloadDigest": payload_digest,
            "evidence": {
                "validation": self.evidence_reference(
                    self.validation_evidence_relative
                ),
                "independentReview": self.evidence_reference(
                    self.review_evidence_relative
                ),
            },
            "secretScan": {
                "status": "pass",
                "findings": [],
                "evidence": self.evidence_reference(
                    self.validation_evidence_relative
                ),
            },
            "unresolvedBlockers": [],
        }
        if self.include_deletions:
            candidate["deletions"] = list(self.candidate_deletions)
        return candidate

    def evidence_reference(self, relative: Path) -> dict[str, object]:
        path = self.repo / relative
        return {
            "path": relative.as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    def validation_evidence_document(self) -> dict[str, object]:
        check_ids = (
            "completion-contract",
            "focused-tests",
            "broad-tests",
            "devflow-validators",
            "source-release-parity",
            "secret-scan",
            "unexpected-candidate-scan",
            "blocker-scan",
        )
        return {
            "schemaVersion": "1.0",
            "kind": "devflow-milestone-validation-evidence",
            "contractId": self.contract["contractId"],
            "checks": [
                {
                    "id": check_id,
                    "command": self.canonical_validation_commands()[check_id],
                    "exitCode": 0,
                    "status": "pass",
                    "counts": {"passed": 1, "failed": 0, "skipped": 0},
                }
                for check_id in check_ids
            ],
            "pluginEval": {
                "target": "plugins/dev-flow",
                "command": "plugin-eval analyze plugins/dev-flow --format markdown",
                "exitCode": 0,
                "status": "pass",
                "score": 86,
                "grade": "B",
                "failFindings": 0,
                "warnFindings": 1,
                "findings": [
                    {
                        "id": "token-budget-advisory",
                        "severity": "warning",
                        "decision": "accepted-with-rationale",
                        "rationale": "non-blocking release-target advisory",
                    }
                ],
            },
            "secretScan": {"status": "pass", "findings": []},
            "unexpectedCandidateFiles": [],
            "unresolvedBlockers": [],
        }

    def canonical_validation_commands(self) -> dict[str, str]:
        manifest = (
            ".planning/devflow/milestone-external-effects/"
            f"{self.contract['contractId']}/candidate-manifest.json"
        )
        secret_code = (
            "import json,pathlib,re,sys;p=pathlib.Path('.');"
            f"m=json.loads((p/'{manifest}').read_text());"
            "q=re.compile(r'AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9_]{36,}|"
            "-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----');"
            "sys.exit(any(q.search((p/x['path']).read_text(errors='ignore')) "
            "for x in m['files']))"
        )
        unexpected_code = (
            "import json,pathlib,subprocess,sys;p=pathlib.Path('.');"
            f"m=json.loads((p/'{manifest}').read_text());"
            "e={x['path'] for x in m['files']}|set(m.get('deletions',[]));"
            "a=subprocess.check_output(['git','diff','--name-only','-z','HEAD','--']);"
            "b=subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z','--']);"
            "o={x for x in (a+b).decode().split('\\0') if x};sys.exit(bool(o-e))"
        )
        change = self.contract["change"]
        return {
            "completion-contract": (
                f"openspec validate {change} --strict --json && "
                "openspec validate --all --strict --json"
            ),
            "focused-tests": (
                "PYTHONDONTWRITEBYTECODE=1 python3.12 "
                "dev/plugins/dev-flow/tests/test_milestone_external_effects.py"
            ),
            "broad-tests": (
                "PYTHONDONTWRITEBYTECODE=1 python3.12 "
                "dev/scripts/run_devflow_prepromotion_tests.py && "
                "PYTHONDONTWRITEBYTECODE=1 python3.12 -m unittest discover "
                "-s dev/plugins/dev-flow/tests -p 'test_*.py' && "
                "PYTHONDONTWRITEBYTECODE=1 python3.12 -m unittest discover "
                "-s plugins/dev-flow/tests -p 'test_*.py'"
            ),
            "devflow-validators": (
                "PYTHONDONTWRITEBYTECODE=1 python3.12 "
                "dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo . --json && "
                "PYTHONDONTWRITEBYTECODE=1 python3.12 "
                "dev/plugins/dev-flow/scripts/doctor_workflow.py --repo . --json"
            ),
            "source-release-parity": (
                "PYTHONDONTWRITEBYTECODE=1 python3.12 "
                "dev/plugins/dev-flow/scripts/release_promotion_gate.py --repo . "
                "--target dev-flow --check --json && "
                "PYTHONDONTWRITEBYTECODE=1 python3.12 "
                "dev/plugins/dev-flow/scripts/verify_release_runtime.py "
                "--plugin-root plugins/dev-flow --repo-root . --json"
            ),
            "secret-scan": f'PYTHONDONTWRITEBYTECODE=1 python3.12 -c "{secret_code}"',
            "unexpected-candidate-scan": (
                f'PYTHONDONTWRITEBYTECODE=1 python3.12 -c "{unexpected_code}"'
            ),
            "blocker-scan": f"openspec status --change {change} --json",
        }

    def review_evidence_document(self) -> dict[str, object]:
        return {
            "schemaVersion": "1.0",
            "kind": "devflow-milestone-review-evidence",
            "contractId": self.contract["contractId"],
            "reviewer": "fixture-independent-reviewer",
            "reviewMode": "independent-read-only",
            "p0": 0,
            "p1": 0,
            "status": "pass",
        }

    def validation_receipt(self) -> dict[str, object]:
        return self.validation_receipt_for(self.candidate)

    def validation_receipt_for(
        self,
        candidate: dict[str, object],
        *,
        projection: dict[str, object] | None = None,
    ) -> dict[str, object]:
        evidence = copy.deepcopy(projection or self.validation_evidence_document())
        evidence.pop("kind", None)
        return {
            **evidence,
            "candidateDigest": candidate["payloadDigest"],
            "evidence": copy.deepcopy(candidate["evidence"]["validation"]),
        }

    def review_receipt(self) -> dict[str, object]:
        return self.review_receipt_for(self.candidate)

    def review_receipt_for(
        self,
        candidate: dict[str, object],
        *,
        projection: dict[str, object] | None = None,
    ) -> dict[str, object]:
        evidence = copy.deepcopy(projection or self.review_evidence_document())
        evidence.pop("kind", None)
        return {
            **evidence,
            "candidateDigest": candidate["payloadDigest"],
            "reviewedDiffDigest": candidate["payloadDigest"],
            "evidence": copy.deepcopy(candidate["evidence"]["independentReview"]),
        }

    def plan(self, **overrides: object) -> dict[str, object]:
        arguments: dict[str, object] = {
            "candidate_manifest": self.candidate,
            "validation_receipt": self.validation,
            "review_receipt": self.review,
            "execution_ledger": self.long_run,
            "receipt_dir": self.receipts,
            "boundaries": self.boundary.mapping(),
        }
        arguments.update(overrides)
        return plan_milestone_external_effects(self.repo, self.contract, **arguments)

    def apply(self, plan: dict[str, object], **overrides: object) -> dict[str, object]:
        arguments: dict[str, object] = {
            "plan": plan,
            "receipt_dir": self.receipts,
            "boundaries": self.boundary.mapping(),
        }
        arguments.update(overrides)
        return apply_milestone_external_effects(self.repo, self.contract, **arguments)

    def verify(self, receipt: dict[str, object], **overrides: object) -> dict[str, object]:
        arguments: dict[str, object] = {
            "receipt": receipt,
            "receipt_dir": self.receipts,
            "boundaries": self.boundary.mapping(),
        }
        arguments.update(overrides)
        return verify_milestone_external_effects(self.repo, self.contract, **arguments)

    def assert_technical_stop(self, report: dict[str, object], reason: str) -> None:
        self.assertFalse(report["ok"], report)
        self.assertEqual(report["decision"], "FAIL_CLOSED_REPAIR", report)
        self.assertEqual(report["missingAuthority"], [], report)
        self.assertNotIn("AWAIT_HUMAN", json.dumps(report))
        self.assertIn(reason, report["reasonCodes"])

    def assert_human_gate(
        self,
        report: dict[str, object],
        missing_authority: str,
        reason: str,
    ) -> None:
        self.assertFalse(report["ok"], report)
        self.assertEqual(report["decision"], "AWAIT_HUMAN", report)
        self.assertEqual(report["missingAuthority"], [f"target:{missing_authority}"], report)
        self.assertIn(reason, report["reasonCodes"])
        self.assertRegex(report["gateKey"], r"^[0-9a-f]{64}$")

    def assert_no_git_or_boundary_mutation(self) -> None:
        self.assertEqual(self.git_output(self.repo, "rev-parse", "HEAD"), self.base)
        self.assertEqual(self.git_output(self.repo, "diff", "--cached", "--name-only"), "")
        self.assertEqual(self.boundary.mutating_count(), 0)

    def make_exact_commit(self) -> str:
        self.run_git(
            "-C",
            str(self.repo),
            "--literal-pathspecs",
            "add",
            "--",
            *self.contract["writeSet"],
        )
        self.run_git(
            "-C",
            str(self.repo),
            "commit",
            "-qm",
            self.contract["commit"]["message"],
        )
        return self.git_output(self.repo, "rev-parse", "HEAD")

    def test_plan_binds_all_five_contract_and_evidence_digests_without_mutation(self):
        before = self.git_output(self.repo, "status", "--porcelain=v1")

        first = self.plan()
        second = self.plan()

        self.assertTrue(first["ok"], first)
        self.assertEqual(first["decision"], "CONTINUE")
        self.assertEqual(first["status"], "READY")
        self.assertEqual(first["nextStep"], "CONTRACT_VALIDATED")
        for key in (
            "contractDigest",
            "candidateDigest",
            "validationDigest",
            "reviewDigest",
            "executionLedgerDigest",
            "planDigest",
        ):
            self.assertRegex(first[key], r"^[0-9a-f]{64}$", key)
            self.assertEqual(first[key], second[key], key)
        self.assertEqual(first["writeSet"], self.contract["writeSet"])
        self.assertEqual(first["excludedEffects"], self.contract["exclusions"])
        self.assertEqual(self.git_output(self.repo, "status", "--porcelain=v1"), before)
        self.assertEqual(self.boundary.mutating_count(), 0)

    def test_explicit_empty_deletions_have_a_distinct_deterministic_payload(self):
        self.assertEqual(self.candidate["deletions"], [])
        expected = canonical_digest(
            {
                "files": self.candidate["files"],
                "deletions": [],
                "assets": self.candidate["assets"],
            }
        )
        legacy = canonical_digest(
            {"files": self.candidate["files"], "assets": self.candidate["assets"]}
        )

        first = self.plan()
        second = self.plan()

        self.assertTrue(first["ok"], first)
        self.assertEqual(self.candidate["payloadDigest"], expected)
        self.assertNotEqual(expected, legacy)
        self.assertEqual(first["candidateDigest"], second["candidateDigest"])
        self.assertIn(
            "set(m.get('deletions',[]))",
            self.canonical_validation_commands()["unexpected-candidate-scan"],
        )

    def test_legacy_v1_candidate_without_deletions_keeps_legacy_digest_and_plans(self):
        self.include_deletions = False
        self.refreeze_supplied_evidence()
        self.assertNotIn("deletions", self.candidate)

        report = self.plan()

        self.assertTrue(report["ok"], report)
        self.assertEqual(
            self.candidate["payloadDigest"],
            canonical_digest(
                {"files": self.candidate["files"], "assets": self.candidate["assets"]}
            ),
        )
        self.assertEqual(report["writeSet"], self.contract["writeSet"])
        self.assertIn(
            "set(m.get('deletions',[]))",
            self.validation["checks"][6]["command"],
        )

    def test_plan_binds_canonical_goal_openspec_state_and_acyclic_evidence_projection(self):
        report = self.plan()

        self.assertTrue(report["ok"], report)
        binding = report["canonicalGuard"]
        self.assertEqual(binding["statePath"], CANONICAL_STATE.as_posix())
        self.assertEqual(binding["stateStage"], "external_effects")
        self.assertEqual(binding["changeStatus"], "external_effects")
        self.assertEqual(binding["goalId"], self.contract["goalId"])
        self.assertEqual(binding["changeId"], self.contract["change"])
        self.assertEqual(binding["contractPath"], self.contract_relative.as_posix())
        self.assertEqual(binding["configPath"], DEVFLOW_CONFIG.as_posix())
        self.assertEqual(binding["workflowMode"], "full-openspec")
        self.assertEqual(binding["stateSource"], "worktree")
        self.assertEqual(
            binding["frozenEvidence"],
            {
                "candidateDigest": self.canonical_state_values()["candidate_digest"],
                "validationDigest": self.canonical_state_values()["validation_digest"],
                "reviewDigest": self.canonical_state_values()["review_digest"],
            },
        )
        for key in (
            "bindingDigest",
            "configSha256",
            "stateSha256",
            "contractSha256",
            "openSpecDigest",
        ):
            self.assertRegex(binding[key], r"^[0-9a-f]{64}$", key)

    def test_canonical_binding_failures_are_technical_and_never_fabricate_a_gate(self):
        original_state = (self.repo / CANONICAL_STATE).read_text()
        original_config = (self.repo / DEVFLOW_CONFIG).read_text()
        original_tasks = (
            self.repo / "openspec" / "changes" / self.change / "tasks.md"
        ).read_text()
        cases = {
            "standing_declared": lambda: self.write_canonical_state(
                candidate_digest=self.canonical_state_values()["candidate_digest"],
                validation_digest=self.canonical_state_values()["validation_digest"],
                review_digest=self.canonical_state_values()["review_digest"],
                standing_status="declared",
            ),
            "goal_drift": lambda: self.write_canonical_state(
                candidate_digest=self.canonical_state_values()["candidate_digest"],
                validation_digest=self.canonical_state_values()["validation_digest"],
                review_digest=self.canonical_state_values()["review_digest"],
                goal_id="goal-other",
            ),
            "stage_drift": lambda: self.write_canonical_state(
                candidate_digest=self.canonical_state_values()["candidate_digest"],
                validation_digest=self.canonical_state_values()["validation_digest"],
                review_digest=self.canonical_state_values()["review_digest"],
                stage="verifying",
            ),
            "verification_not_ready": lambda: self.write_canonical_state(
                candidate_digest=self.canonical_state_values()["candidate_digest"],
                validation_digest=self.canonical_state_values()["validation_digest"],
                review_digest=self.canonical_state_values()["review_digest"],
                verification_passed=False,
            ),
            "projection_drift": lambda: (self.repo / CANONICAL_STATE).write_text(
                original_state.replace(
                    self.canonical_state_values()["candidate_digest"], "f" * 64, 1
                )
            ),
            "openspec_drift": lambda: (
                self.repo / "openspec" / "changes" / self.change / "tasks.md"
            ).write_text("# Unreviewed OpenSpec drift\n"),
            "config_missing": lambda: (self.repo / DEVFLOW_CONFIG).unlink(),
            "config_mode_drift": lambda: (self.repo / DEVFLOW_CONFIG).write_text(
                '{"projectContract":8,"workflow":{"mode":"lightweight-ledger"}}\n'
            ),
            "config_legacy": lambda: (self.repo / DEVFLOW_CONFIG).write_text(
                '{"projectContract":8,"workflow_mode":"full-openspec"}\n'
            ),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name):
                (self.repo / CANONICAL_STATE).write_text(original_state)
                (self.repo / DEVFLOW_CONFIG).write_text(original_config)
                (
                    self.repo / "openspec" / "changes" / self.change / "tasks.md"
                ).write_text(original_tasks)
                mutate()
                report = self.plan()
                self.assert_technical_stop(report, "CANONICAL_AUTHORITY_BINDING_INVALID")
                self.assert_no_git_or_boundary_mutation()
        (self.repo / CANONICAL_STATE).write_text(original_state)
        (self.repo / DEVFLOW_CONFIG).write_text(original_config)
        (self.repo / "openspec" / "changes" / self.change / "tasks.md").write_text(
            original_tasks
        )

    def test_cli_rejects_off_canonical_and_duplicate_mapping_inputs_without_mutation(self):
        documents = {
            "copied-contract.json": self.contract,
            "candidate.json": self.candidate,
            "validation.json": self.validation,
            "review.json": self.review,
            "ledger.json": self.long_run,
        }
        for name, value in documents.items():
            (self.root / name).write_text(json.dumps(value))
        codex_home = self.root / "codex-home"
        codex_home.mkdir()

        def run_plan(contract_path: Path) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [
                    sys.executable,
                    str(MILESTONE_CLI),
                    "plan",
                    "--repo",
                    str(self.repo),
                    "--contract",
                    str(contract_path.resolve()),
                    "--candidate-manifest",
                    str(self.root / "candidate.json"),
                    "--validation-receipt",
                    str(self.root / "validation.json"),
                    "--review-receipt",
                    str(self.root / "review.json"),
                    "--execution-ledger",
                    str(self.root / "ledger.json"),
                    "--receipt-dir",
                    self.receipts.as_posix(),
                    "--codex-home",
                    str(codex_home),
                    "--json",
                ],
                text=True,
                capture_output=True,
            )

        off_canonical = run_plan(self.root / "copied-contract.json")
        self.assertEqual(
            off_canonical.returncode,
            2,
            off_canonical.stdout + off_canonical.stderr,
        )
        report = json.loads(off_canonical.stdout)
        self.assertIn("CANONICAL_CONTRACT_PATH_REQUIRED", report["reasonCodes"])

        canonical_contract_path = self.repo / self.contract_relative
        original_contract = canonical_contract_path.read_text()
        contract_marker = f'"contractId": "{self.contract["contractId"]}"'
        canonical_contract_path.write_text(
            original_contract.replace(
                contract_marker,
                f"{contract_marker},\n  {contract_marker}",
                1,
            )
        )
        duplicate_contract = run_plan(canonical_contract_path)
        self.assertEqual(
            duplicate_contract.returncode,
            2,
            duplicate_contract.stdout + duplicate_contract.stderr,
        )
        duplicate_contract_report = json.loads(duplicate_contract.stdout)
        self.assertIn(
            "MILESTONE_INPUT_OR_BOUNDARY_INVALID",
            duplicate_contract_report["reasonCodes"],
        )
        self.assertIn("duplicate JSON key", duplicate_contract_report["error"])
        canonical_contract_path.write_text(original_contract)

        review_marker = '"status": "pass"'
        (self.root / "review.json").write_text(
            json.dumps(self.review).replace(
                review_marker,
                f"{review_marker}, {review_marker}",
                1,
            )
        )
        duplicate_review = run_plan(canonical_contract_path)
        self.assertEqual(
            duplicate_review.returncode,
            2,
            duplicate_review.stdout + duplicate_review.stderr,
        )
        duplicate_review_report = json.loads(duplicate_review.stdout)
        self.assertIn(
            "MILESTONE_INPUT_OR_BOUNDARY_INVALID",
            duplicate_review_report["reasonCodes"],
        )
        self.assertIn("duplicate JSON key", duplicate_review_report["error"])

        plan = self.plan()
        self.assertTrue(plan["ok"], plan)
        plan_marker = f'"planDigest": "{plan["planDigest"]}"'
        (self.root / "plan.json").write_text(
            json.dumps(plan).replace(
                plan_marker,
                f'{plan_marker}, "planDigest": "{"0" * 64}"',
                1,
            )
        )
        duplicate_plan = subprocess.run(
            [
                sys.executable,
                str(MILESTONE_CLI),
                "advance",
                "--repo",
                str(self.repo),
                "--contract",
                str(canonical_contract_path.resolve()),
                "--plan",
                str(self.root / "plan.json"),
                "--apply",
                "--receipt-dir",
                self.receipts.as_posix(),
                "--codex-home",
                str(codex_home),
                "--json",
            ],
            text=True,
            capture_output=True,
        )

        self.assertEqual(
            duplicate_plan.returncode,
            2,
            duplicate_plan.stdout + duplicate_plan.stderr,
        )
        duplicate_plan_report = json.loads(duplicate_plan.stdout)
        self.assertIn(
            "MILESTONE_INPUT_OR_BOUNDARY_INVALID",
            duplicate_plan_report["reasonCodes"],
        )
        self.assertIn("duplicate JSON key", duplicate_plan_report["error"])
        self.assert_no_git_or_boundary_mutation()

    def test_reentry_uses_same_commit_canonical_state_and_contract_not_later_worktree_bytes(self):
        plan = self.plan()
        self.boundary.crash_after_effect.add("git.commit")
        with self.assertRaises(SimulatedBoundaryCrash):
            self.apply(plan)
        commit = self.git_output(self.repo, "rev-parse", "HEAD")
        self.assertNotEqual(commit, self.base)
        committed_config_sha = hashlib.sha256(
            (self.repo / DEVFLOW_CONFIG).read_bytes()
        ).hexdigest()
        (self.repo / CANONICAL_STATE).write_text("untrusted later worktree STATE\n")
        (self.repo / self.contract_relative).write_text("{}\n")
        (self.repo / DEVFLOW_CONFIG).write_text(
            '{"projectContract":8,"workflow":{"mode":"lightweight-ledger"}}\n'
        )
        (self.repo / self.validation_evidence_relative).write_text(
            '{"untrusted":"later validation evidence"}\n'
        )
        (self.repo / self.review_evidence_relative).write_text(
            '{"untrusted":"later review evidence"}\n'
        )

        recovered = self.apply(plan)

        self.assertTrue(recovered["ok"], recovered)
        self.assertEqual(recovered["receipt"]["canonicalGuard"]["stateSource"], "commit")
        self.assertEqual(
            recovered["receipt"]["canonicalGuard"]["sourceCommit"], commit
        )
        self.assertEqual(
            recovered["receipt"]["canonicalGuard"]["configSha256"],
            committed_config_sha,
        )
        self.assertEqual(self.boundary.count("publication_apply"), 1)

    def test_plan_binds_the_exact_repo_local_receipt_directory(self):
        report = self.plan()

        self.assertTrue(report["ok"], report)
        self.assertEqual(
            report["receiptBinding"]["relativePath"],
            self.receipts.as_posix(),
        )
        self.assertEqual(report["receiptBinding"]["contractId"], self.contract["contractId"])
        self.assertEqual(report["receiptBinding"]["repositoryRealPath"], str(self.repo.resolve()))
        self.assertRegex(report["receiptBinding"]["bindingDigest"], r"^[0-9a-f]{64}$")

    def test_untrusted_receipt_directories_fail_closed_before_any_write(self):
        outside = self.root / "outside-receipts"
        outside.mkdir()
        cases = {
            "absolute": self.repo / self.receipts,
            "off_repo": Path("../outside-receipts"),
            "contract_mismatch": Path(
                ".planning/devflow/milestone-external-effects/other-contract"
            ),
        }
        (self.repo / cases["contract_mismatch"]).mkdir(parents=True)
        for name, receipt_dir in cases.items():
            with self.subTest(name=name):
                report = self.plan(receipt_dir=receipt_dir)
                self.assert_technical_stop(report, "RECEIPT_DIRECTORY_UNTRUSTED")
                self.assert_no_git_or_boundary_mutation()

        canonical = self.repo / self.receipts
        asset_root = canonical / "release-assets"
        for name in self.contract["publication"]["assets"]:
            (asset_root / name).unlink()
        asset_root.rmdir()
        canonical.rmdir()
        target = self.root / "symlink-target"
        target.mkdir()
        canonical.symlink_to(target, target_is_directory=True)
        report = self.plan()
        self.assert_technical_stop(report, "RECEIPT_DIRECTORY_UNTRUSTED")
        self.assert_no_git_or_boundary_mutation()

    def test_every_human_gate_carries_the_central_resolver_receipt(self):
        plan = self.plan()
        competitor = self.root / "gate-competitor"
        self.run_git("clone", "-q", str(self.remote), str(competitor))
        self.run_git("-C", str(competitor), "config", "user.name", "Competitor")
        self.run_git(
            "-C", str(competitor), "config", "user.email", "competitor@example.invalid"
        )
        (competitor / "GATE.txt").write_text("remote moved\n")
        self.run_git("-C", str(competitor), "add", "GATE.txt")
        self.run_git("-C", str(competitor), "commit", "-qm", "remote moved")
        self.run_git("-C", str(competitor), "push", "-q", "origin", "main")

        report = self.apply(plan)

        self.assertEqual(report["decision"], "AWAIT_HUMAN", report)
        self.assertEqual(report["schemaVersion"], 1)
        for key in (
            "requestDigest",
            "authorityDigest",
            "evidenceDigest",
            "standingContractDigest",
            "gateKey",
        ):
            self.assertRegex(report[key], r"^[0-9a-f]{64}$", report)
        self.assertEqual(
            report["missingAuthority"], ["target:repository.expectedBase"]
        )

    def test_contract_validation_names_each_missing_standing_authority(self):
        cases = (
            (("contractId",), "standingContract.contractId"),
            (("goalId",), "standingContract.goalId"),
            (("change",), "standingContract.change"),
            (("writeSet",), "standingContract.writeSet"),
            (("plugin", "id"), "plugin.id"),
            (("plugin", "marketplace"), "plugin.marketplace"),
            (("plugin", "versionRule"), "plugin.versionRule"),
            (("plugin", "version"), "plugin.version"),
            (("repository", "remote"), "repository.remote"),
            (("repository", "ref"), "repository.ref"),
            (("publication", "tag"), "publication.tag"),
            (("publication", "channel"), "publication.channel"),
            (("publication", "mechanism"), "publication.mechanism"),
            (("publication", "workflow"), "publication.workflow"),
            (("publication", "assets"), "publication.assets"),
            (("refreshTargets", "cache"), "refreshTargets.cache"),
            (("refreshTargets", "project"), "refreshTargets.project"),
            (("failurePolicy",), "standingContract.failurePolicy"),
            (("reentryPolicy",), "standingContract.reentryPolicy"),
            (("exclusions",), "standingContract.exclusions"),
        )
        for key_path, missing in cases:
            with self.subTest(key_path=key_path):
                invalid = copy.deepcopy(self.contract)
                target = invalid
                for key in key_path[:-1]:
                    target = target[key]
                target.pop(key_path[-1])
                report = plan_milestone_external_effects(
                    self.repo,
                    invalid,
                    candidate_manifest=self.candidate,
                    validation_receipt=self.validation,
                    review_receipt=self.review,
                    execution_ledger=self.long_run,
                    receipt_dir=self.receipts,
                    boundaries=self.boundary.mapping(),
                )
                self.assert_technical_stop(
                    report, "STANDING_CONTRACT_IDENTITY_INVALID"
                )
                self.assert_no_git_or_boundary_mutation()

    def test_missing_derived_repository_evidence_is_a_repair_stop_not_a_human_gate(self):
        for key_path in (
            ("repository", "remoteUrl"),
            ("repository", "expectedBase"),
            ("commit", "message"),
        ):
            with self.subTest(key_path=key_path):
                invalid = copy.deepcopy(self.contract)
                invalid[key_path[0]].pop(key_path[1])
                report = plan_milestone_external_effects(
                    self.repo,
                    invalid,
                    candidate_manifest=self.candidate,
                    validation_receipt=self.validation,
                    review_receipt=self.review,
                    execution_ledger=self.long_run,
                    receipt_dir=self.receipts,
                    boundaries=self.boundary.mapping(),
                )
                self.assert_technical_stop(
                    report, "STANDING_CONTRACT_IDENTITY_INVALID"
                )
                self.assert_no_git_or_boundary_mutation()

    def test_missing_contract_is_default_deny_and_does_not_infer_authority(self):
        report = plan_milestone_external_effects(
            self.repo,
            None,
            candidate_manifest=self.candidate,
            validation_receipt=self.validation,
            review_receipt=self.review,
            execution_ledger=self.long_run,
            receipt_dir=self.receipts,
            boundaries=self.boundary.mapping(),
        )

        self.assert_technical_stop(report, "CANONICAL_AUTHORITY_BINDING_INVALID")
        self.assert_no_git_or_boundary_mutation()

    def test_incomplete_validation_and_review_are_technical_stops_not_human_gates(self):
        validation = copy.deepcopy(self.validation)
        validation["broadTests"] = "fail"
        report = self.plan(validation_receipt=validation)
        self.assert_technical_stop(report, "VALIDATION_RECEIPT_INVALID")
        self.assert_no_git_or_boundary_mutation()

        review = copy.deepcopy(self.review)
        review["p1"] = 1
        report = self.plan(review_receipt=review)
        self.assert_technical_stop(report, "REVIEW_RECEIPT_INVALID")
        self.assert_no_git_or_boundary_mutation()

    def test_candidate_and_review_receipts_are_bound_to_the_same_exact_payload(self):
        candidate = copy.deepcopy(self.candidate)
        candidate["goalId"] = "different-goal"
        report = self.plan(candidate_manifest=candidate)
        self.assert_technical_stop(report, "CANONICAL_AUTHORITY_BINDING_INVALID")
        self.assert_no_git_or_boundary_mutation()

        review = copy.deepcopy(self.review)
        review["candidateDigest"] = "0" * 64
        report = self.plan(review_receipt=review)
        self.assert_technical_stop(report, "REVIEW_CANDIDATE_MISMATCH")
        self.assert_no_git_or_boundary_mutation()

        asset_drift = copy.deepcopy(self.candidate)
        asset_drift["assets"][0]["sha256"] = "0" * 64
        report = self.plan(candidate_manifest=asset_drift)
        self.assert_technical_stop(report, "CANONICAL_AUTHORITY_BINDING_INVALID")
        self.assert_no_git_or_boundary_mutation()

    def test_reviewed_diff_drift_stops_before_index_mutation(self):
        plan = self.plan()
        (self.repo / "feature.txt").write_text("reviewed bytes drifted\n")

        report = self.apply(plan)

        self.assert_technical_stop(report, "CANDIDATE_DRIFT")
        self.assert_no_git_or_boundary_mutation()

    def test_exact_tracked_deletion_is_bound_staged_committed_and_reentered(self):
        self.declare_tracked_deletion()
        expected_payload = canonical_digest(
            {
                "files": self.candidate["files"],
                "deletions": ["obsolete.txt"],
                "assets": self.candidate["assets"],
            }
        )
        self.assertEqual(self.candidate["deletions"], ["obsolete.txt"])
        self.assertEqual(self.candidate["payloadDigest"], expected_payload)
        plan = self.plan()
        self.assertTrue(plan["ok"], plan)
        self.boundary.crash_after_effect.add("git.commit")

        with self.assertRaises(SimulatedBoundaryCrash):
            self.apply(plan)

        commit = self.git_output(self.repo, "rev-parse", "HEAD")
        self.assertNotEqual(commit, self.base)
        self.assertNotEqual(
            self.run_git(
                "-C",
                str(self.repo),
                "cat-file",
                "-e",
                f"{commit}:obsolete.txt",
                check=False,
            ).returncode,
            0,
        )

        recovered = self.apply(plan)

        self.assertTrue(recovered["ok"], recovered)
        self.assertEqual(recovered["status"], "COMPLETE")
        self.assertEqual(recovered["receipt"]["commit"], commit)
        self.assertEqual(self.boundary.count("publication_apply"), 1)

    def test_declared_deletion_that_is_not_tracked_at_base_fails_closed(self):
        relative = "ignored-never-tracked.txt"
        (self.repo / ".git" / "info" / "exclude").write_text(f"{relative}\n")
        contract = copy.deepcopy(self.contract)
        contract["writeSet"] = sorted({*contract["writeSet"], relative})
        self.candidate_deletions = [relative]
        self.refreeze_contract(contract)

        report = self.plan()

        self.assert_technical_stop(report, "CANDIDATE_DRIFT")
        self.assert_no_git_or_boundary_mutation()

    def test_deletion_worktree_resurrection_fails_before_index_mutation(self):
        self.declare_tracked_deletion()
        plan = self.plan()
        (self.repo / "obsolete.txt").write_text("resurrected reviewed path\n")

        report = self.apply(plan)

        self.assert_technical_stop(report, "CANDIDATE_DRIFT")
        self.assert_no_git_or_boundary_mutation()

    def test_deletion_wrong_commit_tree_is_rejected_even_if_worktree_is_absent(self):
        self.declare_tracked_deletion()
        plan = self.plan()
        (self.repo / "obsolete.txt").write_text("committed resurrection\n")
        wrong_commit = self.make_exact_commit()
        (self.repo / "obsolete.txt").unlink()

        report = self.apply(plan)

        self.assert_technical_stop(report, "CANDIDATE_DRIFT")
        self.assertEqual(self.git_output(self.repo, "rev-parse", "HEAD"), wrong_commit)
        self.assertEqual(self.git_output(self.remote, "rev-parse", "refs/heads/main"), self.base)
        self.assertEqual(self.boundary.mutating_count(), 0)

    def test_deletion_index_resurrection_is_rejected_before_commit(self):
        self.declare_tracked_deletion()
        plan = self.plan()
        hook = self.repo / ".git" / "hooks" / "pre-commit"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(hook.stat().st_mode | stat.S_IXUSR)

        failed_commit = self.apply(plan)

        self.assert_technical_stop(failed_commit, "COMMIT_FAILED")
        self.assertEqual(self.git_output(self.repo, "rev-parse", "HEAD"), self.base)
        hook.unlink()
        resurrected = self.root / "resurrected-index-blob.txt"
        resurrected.write_text("index-only resurrection\n")
        object_id = self.git_output(
            self.repo, "hash-object", "-w", str(resurrected)
        )
        self.run_git(
            "-C",
            str(self.repo),
            "update-index",
            "--add",
            "--cacheinfo",
            f"100644,{object_id},obsolete.txt",
        )

        report = self.apply(plan)

        self.assert_technical_stop(report, "INDEX_NOT_EXACT")
        self.assertEqual(self.git_output(self.repo, "rev-parse", "HEAD"), self.base)
        self.assertNotEqual(
            self.git_output(self.repo, "ls-files", "-s", "--", "obsolete.txt"), ""
        )
        self.assertEqual(self.boundary.mutating_count(), 0)

    def test_same_identity_reentry_rejects_worktree_deletion_resurrection(self):
        self.declare_tracked_deletion()
        plan = self.plan()
        self.boundary.crash_after_effect.add("git.commit")
        with self.assertRaises(SimulatedBoundaryCrash):
            self.apply(plan)
        commit = self.git_output(self.repo, "rev-parse", "HEAD")
        (self.repo / "obsolete.txt").write_text("later resurrection\n")

        report = self.apply(plan)

        self.assert_technical_stop(report, "CANDIDATE_DRIFT")
        self.assertEqual(self.git_output(self.remote, "rev-parse", "refs/heads/main"), self.base)
        self.assertEqual(self.git_output(self.repo, "rev-parse", "HEAD"), commit)
        self.assertEqual(self.boundary.mutating_count(), 0)

    def test_deletion_shape_overlap_and_undeclared_paths_are_technical_repairs(self):
        malformed = {
            "unsorted": ["z.txt", "a.txt"],
            "duplicate": ["z.txt", "z.txt"],
            "unsafe": ["../outside.txt"],
            "overlap": [self.candidate["files"][0]["path"]],
        }
        for name, deletions in malformed.items():
            with self.subTest(name=name):
                candidate = copy.deepcopy(self.candidate)
                candidate["deletions"] = deletions
                report = self.plan(candidate_manifest=candidate)
                self.assert_technical_stop(report, "CANDIDATE_MANIFEST_INVALID")
                self.assert_no_git_or_boundary_mutation()

        (self.repo / "obsolete.txt").unlink()
        self.candidate_deletions = ["obsolete.txt"]
        self.refreeze_supplied_evidence()
        report = self.plan()
        self.assert_technical_stop(report, "CANDIDATE_CONTRACT_MISMATCH")
        self.assert_no_git_or_boundary_mutation()

    def test_strict_candidate_validation_and_review_shapes_bind_canonical_evidence(self):
        cases: list[tuple[str, str, dict[str, object]]] = []

        candidate_extra = copy.deepcopy(self.candidate)
        candidate_extra["fabricatedPass"] = True
        cases.append(("candidate_extra", "CANDIDATE_MANIFEST_INVALID", {"candidate_manifest": candidate_extra}))
        candidate_mixed = copy.deepcopy(self.candidate)
        candidate_mixed["assets"][0]["size"] = True
        cases.append(("candidate_mixed_type", "CANDIDATE_MANIFEST_INVALID", {"candidate_manifest": candidate_mixed}))
        candidate_unbound = copy.deepcopy(self.candidate)
        candidate_unbound["evidence"]["validation"]["path"] = "evidence/not-in-candidate.json"
        cases.append(
            (
                "candidate_unbound_evidence",
                "CANDIDATE_EVIDENCE_INVALID",
                {"candidate_manifest": candidate_unbound},
            )
        )

        validation_extra = copy.deepcopy(self.validation)
        validation_extra["fabricatedPass"] = True
        cases.append(("validation_extra", "VALIDATION_RECEIPT_INVALID", {"validation_receipt": validation_extra}))
        validation_old = {
            "schemaVersion": "1.0",
            "contractId": self.contract["contractId"],
            "candidateDigest": self.candidate["payloadDigest"],
            "focusedTests": "pass",
            "broadTests": "pass",
        }
        cases.append(("validation_pass_only", "VALIDATION_RECEIPT_INVALID", {"validation_receipt": validation_old}))
        validation_duplicate = copy.deepcopy(self.validation)
        validation_duplicate["checks"][1]["id"] = validation_duplicate["checks"][0]["id"]
        cases.append(
            (
                "validation_duplicate_check",
                "VALIDATION_RECEIPT_INVALID",
                {"validation_receipt": validation_duplicate},
            )
        )
        validation_unbound = copy.deepcopy(self.validation)
        validation_unbound["evidence"]["sha256"] = "0" * 64
        cases.append(
            (
                "validation_unbound_evidence",
                "VALIDATION_EVIDENCE_INVALID",
                {"validation_receipt": validation_unbound},
            )
        )

        review_extra = copy.deepcopy(self.review)
        review_extra["fabricatedPass"] = True
        cases.append(("review_extra", "REVIEW_RECEIPT_INVALID", {"review_receipt": review_extra}))
        review_wrong_contract = copy.deepcopy(self.review)
        review_wrong_contract["contractId"] = "other-contract"
        cases.append(
            (
                "review_wrong_contract",
                "CANONICAL_AUTHORITY_BINDING_INVALID",
                {"review_receipt": review_wrong_contract},
            )
        )
        review_unbound = copy.deepcopy(self.review)
        review_unbound["evidence"]["path"] = self.validation_evidence_relative.as_posix()
        review_unbound["evidence"]["sha256"] = self.candidate["evidence"]["validation"]["sha256"]
        cases.append(("review_unbound_evidence", "REVIEW_EVIDENCE_INVALID", {"review_receipt": review_unbound}))

        for name, reason, overrides in cases:
            with self.subTest(name=name):
                report = self.plan(**overrides)
                self.assert_technical_stop(report, reason)
                self.assert_no_git_or_boundary_mutation()

    def test_ignored_release_asset_directory_is_exact_and_rechecked_on_reentry_and_verify(self):
        asset_root = self.repo / self.receipts / "release-assets"
        first = asset_root / self.contract["publication"]["assets"][0]
        original = first.read_bytes()

        def expect_plan_drift() -> None:
            report = self.plan()
            self.assert_technical_stop(report, "CANDIDATE_ASSET_DRIFT")
            self.assert_no_git_or_boundary_mutation()

        first.write_bytes(original + b"drift")
        expect_plan_drift()
        first.write_bytes(original)

        extra = asset_root / "undeclared.asset"
        extra.write_text("extra\n")
        expect_plan_drift()
        extra.unlink()

        first.unlink()
        first.mkdir()
        expect_plan_drift()
        first.rmdir()
        first.write_bytes(original)

        target = self.root / "asset-symlink-target"
        target.write_bytes(original)
        first.unlink()
        first.symlink_to(target)
        expect_plan_drift()
        first.unlink()
        first.write_bytes(original)

        replacement = self.root / "replacement-assets"
        asset_root.rename(replacement)
        asset_root.symlink_to(replacement, target_is_directory=True)
        expect_plan_drift()
        asset_root.unlink()
        replacement.rename(asset_root)

        plan = self.plan()
        self.assertTrue(plan["ok"], plan)
        first.write_bytes(original + b"apply-drift")
        blocked = self.apply(plan)
        self.assert_technical_stop(blocked, "CANDIDATE_ASSET_DRIFT")
        self.assert_no_git_or_boundary_mutation()
        first.write_bytes(original)

        complete = self.apply(plan)
        self.assertTrue(complete["ok"], complete)
        first.write_bytes(original + b"terminal-drift")
        replay = self.apply(plan)
        verified = self.verify(complete["receipt"])
        self.assert_technical_stop(replay, "CANDIDATE_ASSET_DRIFT")
        self.assert_technical_stop(verified, "CANDIDATE_ASSET_DRIFT")

    def test_candidate_validation_and_review_schemas_accept_only_the_exact_shapes(self):
        from jsonschema import Draft202012Validator

        documents = (
            (CANDIDATE_SCHEMA, self.candidate),
            (VALIDATION_SCHEMA, self.validation),
            (REVIEW_SCHEMA, self.review),
            (VALIDATION_EVIDENCE_SCHEMA, self.validation_evidence_document()),
            (REVIEW_EVIDENCE_SCHEMA, self.review_evidence_document()),
        )
        for schema_path, document in documents:
            with self.subTest(schema=schema_path.name):
                schema = json.loads(schema_path.read_text())
                self.assertEqual(
                    list(Draft202012Validator(schema).iter_errors(document)), []
                )
                invalid = copy.deepcopy(document)
                invalid["unexpected"] = True
                self.assertTrue(
                    list(Draft202012Validator(schema).iter_errors(invalid))
                )

        candidate_validator = Draft202012Validator(
            json.loads(CANDIDATE_SCHEMA.read_text())
        )
        legacy = copy.deepcopy(self.candidate)
        legacy.pop("deletions")
        legacy["payloadDigest"] = canonical_digest(
            {"files": legacy["files"], "assets": legacy["assets"]}
        )
        self.assertEqual(list(candidate_validator.iter_errors(legacy)), [])
        for deletions in (["duplicate.txt", "duplicate.txt"], ["../outside.txt"]):
            invalid_deletion = copy.deepcopy(self.candidate)
            invalid_deletion["deletions"] = deletions
            self.assertTrue(list(candidate_validator.iter_errors(invalid_deletion)))

    def test_supplied_validation_score_cannot_override_candidate_evidence(self):
        forged = self.validation_evidence_document()
        forged["pluginEval"]["score"] = 100
        forged["pluginEval"]["grade"] = "A"
        self.refreeze_supplied_evidence(validation_projection=forged)

        report = self.plan()

        self.assert_technical_stop(report, "VALIDATION_EVIDENCE_MISMATCH")
        self.assert_no_git_or_boundary_mutation()

    def test_supplied_review_threshold_cannot_override_candidate_evidence(self):
        tracked = self.review_evidence_document()
        tracked["p1"] = 3
        tracked["status"] = "fail"
        (self.repo / self.review_evidence_relative).write_text(
            json.dumps(tracked, indent=2, sort_keys=True) + "\n"
        )
        supplied = self.review_evidence_document()
        self.refreeze_supplied_evidence(review_projection=supplied)

        report = self.plan()

        self.assert_technical_stop(report, "REVIEW_EVIDENCE_MISMATCH")
        self.assert_no_git_or_boundary_mutation()

    def test_noncanonical_validation_and_plugin_eval_commands_are_rejected(self):
        cases = ("validation", "plugin-eval")
        for name in cases:
            with self.subTest(name=name):
                tracked = self.validation_evidence_document()
                if name == "validation":
                    tracked["checks"][0]["command"] = "true"
                else:
                    tracked["pluginEval"]["command"] = (
                        "python3 local-plugin-eval.py dev/plugins/dev-flow"
                    )
                (self.repo / self.validation_evidence_relative).write_text(
                    json.dumps(tracked, indent=2, sort_keys=True) + "\n"
                )
                self.refreeze_supplied_evidence(validation_projection=tracked)

                report = self.plan()

                self.assert_technical_stop(report, "VALIDATION_COMMAND_INVALID")
                self.assert_no_git_or_boundary_mutation()

    def test_candidate_evidence_duplicate_keys_unknown_fields_and_byte_drift_fail_closed(self):
        validation_path = self.repo / self.validation_evidence_relative
        original_document = self.validation_evidence_document()

        duplicate = json.dumps(original_document, sort_keys=True).replace(
            '"kind":',
            '"kind":"devflow-milestone-validation-evidence","kind":',
            1,
        )
        validation_path.write_text(duplicate + "\n")
        self.refreeze_supplied_evidence(validation_projection=original_document)
        duplicate_report = self.plan()
        self.assert_technical_stop(
            duplicate_report, "VALIDATION_EVIDENCE_INVALID"
        )
        self.assert_no_git_or_boundary_mutation()

        unknown = self.validation_evidence_document()
        unknown["callerAssertion"] = "pass"
        validation_path.write_text(json.dumps(unknown, sort_keys=True) + "\n")
        self.refreeze_supplied_evidence(
            validation_projection=original_document
        )
        unknown_report = self.plan()
        self.assert_technical_stop(unknown_report, "VALIDATION_EVIDENCE_INVALID")
        self.assert_no_git_or_boundary_mutation()

        validation_path.write_text(
            json.dumps(original_document, indent=2, sort_keys=True) + "\n"
        )
        self.refreeze_supplied_evidence()
        plan = self.plan()
        self.assertTrue(plan["ok"], plan)
        validation_path.write_text("{}\n")
        drift = self.apply(plan)
        self.assert_technical_stop(drift, "CANDIDATE_DRIFT")
        self.assert_no_git_or_boundary_mutation()

    def test_unreviewed_file_is_rejected_at_freeze_and_if_it_appears_after_freeze(self):
        (self.repo / "UNREVIEWED.txt").write_text("not in the candidate\n")
        frozen = self.plan()
        self.assert_technical_stop(frozen, "UNEXPECTED_CANDIDATE_FILES")
        self.assert_no_git_or_boundary_mutation()

        (self.repo / "UNREVIEWED.txt").unlink()
        plan = self.plan()
        (self.repo / "UNREVIEWED.txt").write_text("appeared after review\n")
        report = self.apply(plan)
        self.assert_technical_stop(report, "UNEXPECTED_CANDIDATE_FILES")
        self.assert_no_git_or_boundary_mutation()

    def test_candidate_paths_cannot_escape_the_repository(self):
        contract = copy.deepcopy(self.contract)
        candidate = copy.deepcopy(self.candidate)
        outside = self.root / "outside.txt"
        outside.write_text("outside repository\n")
        item = {
            "path": "../outside.txt",
            "mode": "100644",
            "size": outside.stat().st_size,
            "sha256": hashlib.sha256(outside.read_bytes()).hexdigest(),
        }
        contract["writeSet"] = [item["path"]]
        candidate["files"] = [item]
        candidate["payloadDigest"] = canonical_digest(
            {
                "files": candidate["files"],
                "deletions": candidate["deletions"],
                "assets": candidate["assets"],
            }
        )
        validation = self.validation_receipt()
        validation["candidateDigest"] = candidate["payloadDigest"]
        review = self.review_receipt()
        review["candidateDigest"] = candidate["payloadDigest"]
        review["reviewedDiffDigest"] = candidate["payloadDigest"]

        report = plan_milestone_external_effects(
            self.repo,
            contract,
            candidate_manifest=candidate,
            validation_receipt=validation,
            review_receipt=review,
            execution_ledger=self.long_run,
            receipt_dir=self.receipts,
            boundaries=self.boundary.mapping(),
        )

        self.assert_technical_stop(report, "STANDING_CONTRACT_IDENTITY_INVALID")
        self.assertEqual(outside.read_text(), "outside repository\n")
        self.assert_no_git_or_boundary_mutation()

    def test_contaminated_index_stops_before_commit(self):
        plan = self.plan()
        (self.repo / "README.md").write_text("unreviewed staged drift\n")
        self.run_git("-C", str(self.repo), "--literal-pathspecs", "add", "README.md")

        report = self.apply(plan)

        self.assert_technical_stop(report, "INDEX_NOT_EXACT")
        self.assertEqual(self.git_output(self.repo, "rev-parse", "HEAD"), self.base)
        self.assertEqual(self.boundary.mutating_count(), 0)

    def test_invalid_state_is_never_treated_as_absent_or_allowed_to_reset_replay_guards(self):
        plan = self.plan()
        state_path = self.repo / self.receipts / "milestone-state.json"
        cases = {
            "unreadable_shape": None,
            "malformed": '{"planDigest":',
            "duplicate_key": (
                '{"schemaVersion":"1.0","planDigest":"%s",'
                '"planDigest":"%s","effects":[],"intents":{}}'
                % (plan["planDigest"], plan["planDigest"])
            ),
            "wrong_plan": json.dumps(
                {
                    "schemaVersion": "1.0",
                    "planDigest": "0" * 64,
                    "effects": [],
                    "intents": {},
                    "stateDigest": "0" * 64,
                }
            ),
        }
        for name, payload in cases.items():
            with self.subTest(name=name):
                if state_path.exists():
                    if state_path.is_dir():
                        state_path.rmdir()
                    else:
                        state_path.unlink()
                if payload is None:
                    state_path.mkdir()
                else:
                    state_path.write_text(payload)
                report = self.apply(plan)
                self.assert_technical_stop(report, "MILESTONE_STATE_INVALID")
                self.assert_no_git_or_boundary_mutation()

    def test_self_rehashed_wrong_plan_and_digest_tampering_both_fail_closed(self):
        plan = self.plan()
        state_path = self.repo / self.receipts / "milestone-state.json"
        base_state = {
            "schemaVersion": "1.0",
            "kind": "devflow-milestone-external-effects-state",
            "planDigest": plan["planDigest"],
            "receiptBindingDigest": plan["receiptBinding"]["bindingDigest"],
            "effects": [],
            "intents": {},
            "counters": {"diagnoses": 0, "remediations": 0},
        }

        wrong_plan = copy.deepcopy(base_state)
        wrong_plan["planDigest"] = "0" * 64
        wrong_plan["stateDigest"] = canonical_digest(wrong_plan)
        state_path.write_text(json.dumps(wrong_plan))
        report = self.apply(plan)
        self.assert_technical_stop(report, "MILESTONE_STATE_INVALID")
        self.assert_no_git_or_boundary_mutation()

        tampered = copy.deepcopy(base_state)
        tampered["stateDigest"] = canonical_digest(tampered)
        tampered["counters"]["remediations"] = 1
        state_path.write_text(json.dumps(tampered))
        report = self.apply(plan)
        self.assert_technical_stop(report, "MILESTONE_STATE_INVALID")
        self.assert_no_git_or_boundary_mutation()

    def test_dangling_state_symlink_is_invalid_not_absent(self):
        plan = self.plan()
        state_path = self.repo / self.receipts / "milestone-state.json"
        state_path.symlink_to(self.root / "missing-state-target")

        report = self.apply(plan)

        self.assert_technical_stop(report, "MILESTONE_STATE_INVALID")
        self.assert_no_git_or_boundary_mutation()

    def test_remote_divergence_is_one_concrete_authority_gate_without_push(self):
        plan = self.plan()
        competitor = self.root / "competitor"
        self.run_git("clone", "-q", str(self.remote), str(competitor))
        self.run_git("-C", str(competitor), "config", "user.name", "Competitor")
        self.run_git("-C", str(competitor), "config", "user.email", "competitor@example.invalid")
        (competitor / "COMPETING.txt").write_text("remote moved\n")
        self.run_git("-C", str(competitor), "add", "COMPETING.txt")
        self.run_git("-C", str(competitor), "commit", "-qm", "remote moved")
        self.run_git("-C", str(competitor), "push", "-q", "origin", "main")
        competing_commit = self.git_output(self.remote, "rev-parse", "refs/heads/main")

        report = self.apply(plan)

        self.assert_human_gate(report, "repository.expectedBase", "REMOTE_DIVERGENCE")
        self.assertEqual(self.git_output(self.remote, "rev-parse", "refs/heads/main"), competing_commit)
        self.assertEqual(self.boundary.mutating_count(), 0)

    def test_remote_transport_failure_is_technical_and_never_opens_a_human_gate(self):
        plan = self.plan()
        self.remote.rename(self.root / "offline-origin.git")

        report = self.apply(plan)

        self.assert_technical_stop(report, "GIT_TRANSPORT_READBACK_FAILED")
        self.assertEqual(self.git_output(self.repo, "rev-parse", "HEAD"), self.base)
        self.assertEqual(self.boundary.mutating_count(), 0)

    def test_push_success_with_readback_mismatch_stops_before_tag_or_publication(self):
        plan = self.plan()
        hook = self.remote / "hooks" / "post-receive"
        hook.write_text(f"#!/bin/sh\ngit update-ref refs/heads/main {self.base}\n")
        hook.chmod(hook.stat().st_mode | stat.S_IXUSR)

        report = self.apply(plan)

        self.assert_technical_stop(report, "PUSH_READBACK_MISMATCH")
        self.assertNotEqual(self.git_output(self.repo, "rev-parse", "HEAD"), self.base)
        self.assertEqual(self.git_output(self.remote, "rev-parse", "refs/heads/main"), self.base)
        self.assertEqual(self.run_git("-C", str(self.remote), "show-ref", "--tags", check=False).stdout, "")
        self.assertEqual(self.boundary.mutating_count(), 0)

    def test_matching_commit_and_push_without_receipt_are_recovered_by_readback(self):
        plan = self.plan()
        commit = self.make_exact_commit()
        self.run_git("-C", str(self.repo), "push", "-q", "origin", "HEAD:refs/heads/main")

        report = self.apply(plan)

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["status"], "COMPLETE")
        self.assertEqual(report["receipt"]["commit"], commit)
        self.assertEqual(self.git_output(self.remote, "rev-parse", "refs/heads/main"), commit)
        self.assertEqual(self.git_output(self.repo, "rev-list", "--count", f"{self.base}..HEAD"), "1")
        self.assertEqual(self.boundary.count("publication_apply"), 1)

    def test_wrong_mode_commit_fails_closed_then_exact_commit_is_reused_and_pushed_once(self):
        plan = self.plan()
        candidate_path = self.repo / "feature.txt"
        candidate_path.chmod(candidate_path.stat().st_mode | stat.S_IXUSR)
        wrong_mode_commit = self.make_exact_commit()

        rejected = self.apply(plan)

        self.assert_technical_stop(rejected, "CANDIDATE_DRIFT")
        self.assertEqual(self.git_output(self.repo, "rev-parse", "HEAD"), wrong_mode_commit)
        self.assertEqual(self.git_output(self.remote, "rev-parse", "refs/heads/main"), self.base)
        self.assertEqual(self.boundary.mutating_count(), 0)

        candidate_path.chmod(candidate_path.stat().st_mode & ~stat.S_IXUSR)
        self.run_git("-C", str(self.repo), "add", "feature.txt")
        self.run_git(
            "-C",
            str(self.repo),
            "commit",
            "--amend",
            "-qm",
            self.contract["commit"]["message"],
        )
        commit = self.git_output(self.repo, "rev-parse", "HEAD")
        self.assertEqual(self.git_output(self.remote, "rev-parse", "refs/heads/main"), self.base)

        report = self.apply(plan)

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["status"], "COMPLETE")
        self.assertEqual(report["receipt"]["commit"], commit)
        self.assertEqual(self.git_output(self.remote, "rev-parse", "refs/heads/main"), commit)
        self.assertEqual(self.git_output(self.repo, "rev-list", "--count", f"{self.base}..HEAD"), "1")

    def test_exact_declared_ignored_candidate_is_force_added_without_widening(self):
        info_exclude = self.repo / ".git" / "info" / "exclude"
        info_exclude.write_text("feature.txt\n")
        plan = self.plan()
        self.assertTrue(plan["ok"], plan)

        report = self.apply(plan)

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["status"], "COMPLETE")
        committed = self.git_output(self.repo, "show", "--format=", "--name-only", "HEAD")
        self.assertEqual(sorted(committed.splitlines()), sorted(self.contract["writeSet"]))
        self.assertNotIn(".git/info/exclude", committed)

    def test_existing_same_identity_tag_and_publication_are_reused(self):
        plan = self.plan()
        commit = self.make_exact_commit()
        self.run_git("-C", str(self.repo), "push", "-q", "origin", "HEAD:refs/heads/main")
        self.run_git("-C", str(self.repo), "tag", "dev-flow-v0.4.0", commit)
        self.run_git("-C", str(self.repo), "push", "-q", "origin", "refs/tags/dev-flow-v0.4.0")
        self.boundary.publication = {
            "plugin": "dev-flow",
            "version": "0.4.0",
            "tag": "dev-flow-v0.4.0",
            "channel": "stable",
            "commit": commit,
            "state": "published",
            "assets": copy.deepcopy(self.candidate["assets"]),
        }

        report = self.apply(plan)

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["status"], "COMPLETE")
        self.assertEqual(self.boundary.count("publication_apply"), 0)
        self.assertEqual(self.git_output(self.remote, "rev-parse", "refs/tags/dev-flow-v0.4.0"), commit)

    def test_tag_collision_requires_new_tag_authority_and_never_retags(self):
        plan = self.plan()
        collision = self.git_output(self.remote, "rev-parse", "refs/heads/main")
        self.run_git("-C", str(self.repo), "tag", "dev-flow-v0.4.0", collision)
        self.run_git("-C", str(self.repo), "push", "-q", "origin", "refs/tags/dev-flow-v0.4.0")

        report = self.apply(plan)

        self.assert_human_gate(report, "publication.tag", "TAG_COLLISION")
        self.assertEqual(self.git_output(self.remote, "rev-parse", "refs/tags/dev-flow-v0.4.0"), collision)
        self.assertEqual(self.boundary.mutating_count(), 0)

    def test_existing_mismatched_release_is_a_collision_and_is_never_overwritten(self):
        plan = self.plan()
        self.boundary.publication = {
            "plugin": "dev-flow",
            "version": "0.4.0",
            "tag": "dev-flow-v0.4.0",
            "channel": "stable",
            "commit": "2" * 40,
            "state": "published",
            "assets": copy.deepcopy(self.candidate["assets"]),
        }

        report = self.apply(plan)

        self.assert_human_gate(report, "publication.release", "RELEASE_COLLISION")
        self.assertEqual(self.boundary.count("publication_apply"), 0)
        self.assertEqual(self.boundary.count("cache_apply"), 0)
        self.assertEqual(self.boundary.count("project_apply"), 0)
        self.assertEqual(self.boundary.publication["commit"], "2" * 40)

    def test_publication_failure_preserves_tag_and_exhausts_only_one_recovery_budget(self):
        plan = self.plan()
        self.boundary.publication_failure = True

        report = self.apply(plan)

        self.assert_technical_stop(report, "PUBLICATION_FAILED")
        commit = self.git_output(self.repo, "rev-parse", "HEAD")
        self.assertEqual(self.git_output(self.remote, "rev-parse", "refs/heads/main"), commit)
        self.assertEqual(self.git_output(self.remote, "rev-parse", "refs/tags/dev-flow-v0.4.0"), commit)
        self.assertEqual(self.boundary.count("publication_apply"), 1)
        self.assertLessEqual(self.boundary.count("publication_diagnose"), 1)
        self.assertLessEqual(self.boundary.count("publication_remediate"), 1)
        self.assertEqual(self.boundary.count("cache_apply"), 0)
        self.assertEqual(self.boundary.count("project_apply"), 0)

    def test_incomplete_publication_readback_blocks_every_refresh(self):
        plan = self.plan()
        self.boundary.publication_readback_incomplete = True

        report = self.apply(plan)

        self.assert_technical_stop(report, "PUBLICATION_PENDING")
        first_apply_count = self.boundary.count("publication_apply")
        replay = self.apply(plan)
        self.assert_technical_stop(replay, "PUBLICATION_PENDING")
        self.assertEqual(self.boundary.count("publication_apply"), first_apply_count)
        self.assertEqual(self.boundary.count("cache_apply"), 0)
        self.assertEqual(self.boundary.count("project_apply"), 0)

    def test_publication_asset_sha_mismatch_blocks_every_refresh(self):
        plan = self.plan()
        self.boundary.publication_asset_mismatch = True

        report = self.apply(plan)

        self.assert_human_gate(report, "publication.release", "RELEASE_COLLISION")
        self.assertEqual(self.boundary.count("cache_apply"), 0)
        self.assertEqual(self.boundary.count("project_apply"), 0)

    def test_unnamed_cache_or_project_target_is_refused_before_boundary_apply(self):
        cases = (
            (
                ("refreshTargets", "cache"),
                "other-plugin@cy-codex-skills",
                "STANDING_CONTRACT_IDENTITY_INVALID",
            ),
            (
                ("refreshTargets", "project"),
                str(self.root / "other-consumer"),
                "STANDING_CONTRACT_TARGET_UNAVAILABLE",
            ),
        )
        for key_path, value, reason in cases:
            with self.subTest(key_path=key_path):
                invalid = copy.deepcopy(self.contract)
                invalid[key_path[0]][key_path[1]] = value
                report = plan_milestone_external_effects(
                    self.repo,
                    invalid,
                    candidate_manifest=self.candidate,
                    validation_receipt=self.validation,
                    review_receipt=self.review,
                    execution_ledger=self.long_run,
                    receipt_dir=self.receipts,
                    boundaries=self.boundary.mapping(),
                )
                self.assert_technical_stop(report, reason)
                self.assert_no_git_or_boundary_mutation()

    def test_project_plan_drift_and_five_layer_mismatch_are_technical_stops(self):
        plan = self.plan()
        self.boundary.project_plan_drift = True
        report = self.apply(plan)
        self.assert_technical_stop(report, "PROJECT_PLAN_DRIFT")
        self.assertEqual(self.boundary.count("project_apply"), 0)

    def test_cache_identity_mismatch_prevents_project_refresh(self):
        plan = self.plan()
        self.boundary.cache_mismatch = True

        report = self.apply(plan)

        self.assert_technical_stop(report, "CACHE_IDENTITY_MISMATCH")
        self.assertEqual(self.boundary.count("project_apply"), 0)

    def test_project_identity_mismatch_preserves_receipts_and_blocks_terminal_claim(self):
        plan = self.plan()
        self.boundary.project_mismatch = True

        report = self.apply(plan)

        self.assert_technical_stop(report, "FIVE_LAYER_IDENTITY_MISMATCH")
        self.assertEqual(self.boundary.count("project_apply"), 1)
        self.assertTrue(report["receiptsPreserved"])

    def exercise_crash_recovery(self, boundary_name: str) -> None:
        self.boundary.crash_after.add(boundary_name)
        plan = self.plan()
        with self.assertRaises(SimulatedBoundaryCrash):
            self.apply(plan)

        recovered = self.apply(plan)

        self.assertTrue(recovered["ok"], recovered)
        self.assertEqual(recovered["status"], "COMPLETE")
        self.assertEqual(self.boundary.count(boundary_name), 1)

    def exercise_effect_intent_recovery(self, effect: str) -> None:
        self.boundary.crash_after_effect.add(effect)
        plan = self.plan()
        with self.assertRaises(SimulatedBoundaryCrash):
            self.apply(plan)

        state = json.loads(
            (self.repo / self.receipts / "milestone-state.json").read_text()
        )
        intent = state["intents"][effect]
        self.assertEqual(intent["status"], "PENDING")
        self.assertEqual(intent["effect"], effect)
        self.assertRegex(intent["beforeIntentDigest"], r"^[0-9a-f]{64}$")

        recovered = self.apply(plan)
        self.assertTrue(recovered["ok"], recovered)
        completed = json.loads(
            (self.repo / self.receipts / "milestone-state.json").read_text()
        )["intents"][effect]
        self.assertEqual(completed["status"], "COMPLETE")
        self.assertRegex(completed["afterReadbackDigest"], r"^[0-9a-f]{64}$")

    def test_commit_intent_is_durable_before_effect_and_recovers_by_head_readback(self):
        self.exercise_effect_intent_recovery("git.commit")
        self.assertEqual(self.git_output(self.repo, "rev-list", "--count", f"{self.base}..HEAD"), "1")

    def test_push_intent_is_durable_before_effect_and_recovers_by_remote_readback(self):
        self.exercise_effect_intent_recovery("git.push")
        self.assertEqual(
            self.git_output(self.remote, "rev-parse", "refs/heads/main"),
            self.git_output(self.repo, "rev-parse", "HEAD"),
        )

    def test_tag_intent_is_durable_before_effect_and_recovers_by_remote_readback(self):
        self.exercise_effect_intent_recovery("git.tag.push")
        self.assertEqual(
            self.git_output(self.remote, "rev-parse", "refs/tags/dev-flow-v0.4.0"),
            self.git_output(self.repo, "rev-parse", "HEAD"),
        )

    def test_publication_intent_is_durable_and_same_identity_readback_prevents_republish(self):
        self.exercise_effect_intent_recovery("github.release")
        self.assertEqual(self.boundary.count("publication_apply"), 1)

    def test_source_intent_is_durable_and_same_identity_readback_prevents_second_apply(self):
        self.exercise_effect_intent_recovery("devflow.source.fast_forward")
        self.assertEqual(self.boundary.count("source_apply"), 1)
        self.assertEqual(self.boundary.count("source_plan"), 1)

    def test_cache_intent_is_durable_and_same_identity_readback_prevents_second_apply(self):
        self.exercise_effect_intent_recovery("codex.cache.refresh")
        self.assertEqual(self.boundary.count("cache_apply"), 1)

    def test_pending_cache_intent_before_effect_retries_same_sealed_apply_once(self):
        self.boundary.crash_before.add("cache_apply")
        plan = self.plan()

        with self.assertRaises(SimulatedBoundaryCrash):
            self.apply(plan)

        state_path = self.repo / self.receipts / "milestone-state.json"
        pending = json.loads(state_path.read_text())["intents"]["codex.cache.refresh"]
        self.assertEqual(pending["status"], "PENDING")
        self.assertIsNone(self.boundary.cache)
        self.assertEqual(self.boundary.count("cache_plan"), 1)
        self.assertEqual(self.boundary.count("cache_apply"), 1)

        recovered = self.apply(plan)

        self.assertTrue(recovered["ok"], recovered)
        self.assertEqual(recovered["status"], "COMPLETE")
        completed = json.loads(state_path.read_text())["intents"]["codex.cache.refresh"]
        self.assertEqual(completed["status"], "COMPLETE")
        self.assertEqual(completed["beforeIntentDigest"], pending["beforeIntentDigest"])
        self.assertEqual(self.boundary.count("cache_plan"), 1)
        self.assertEqual(self.boundary.count("cache_apply"), 2)
        self.assertEqual(self.boundary.count("cache_verify"), 2)

        replay = self.apply(plan)

        self.assertTrue(replay["ok"], replay)
        self.assertEqual(replay["status"], "COMPLETE")
        self.assertEqual(self.boundary.count("cache_apply"), 2)

    def test_pending_cache_retry_is_bounded_and_remains_technical(self):
        self.boundary.cache_failures_before_effect = 2
        plan = self.plan()

        first = self.apply(plan)
        self.assert_technical_stop(first, "CACHE_REFRESH_FAILED")
        second = self.apply(plan)
        self.assert_technical_stop(second, "CACHE_REFRESH_FAILED")

        third = self.apply(plan)

        self.assert_technical_stop(third, "CACHE_REFRESH_RETRY_EXHAUSTED")
        self.assertIsNone(self.boundary.cache)
        self.assertEqual(self.boundary.count("cache_plan"), 1)
        self.assertEqual(self.boundary.count("cache_apply"), 2)

    def test_project_intent_is_durable_and_same_identity_readback_prevents_second_apply(self):
        self.exercise_effect_intent_recovery("devflow.project.refresh")
        self.assertEqual(self.boundary.count("project_apply"), 1)
        self.assertEqual(self.boundary.count("project_plan"), 1)

    def test_crash_after_publication_recovers_without_duplicate_effect(self):
        self.exercise_crash_recovery("publication_apply")

    def test_crash_after_source_fast_forward_recovers_without_duplicate_effect(self):
        self.exercise_crash_recovery("source_apply")

    def test_already_current_named_source_is_reused_without_a_false_gate(self):
        self.boundary.source_already_current = True
        complete = self.apply(self.plan())

        self.assertTrue(complete["ok"], complete)
        self.assertEqual(complete["status"], "COMPLETE")
        self.assertEqual(complete["missingAuthority"], [])
        self.assertEqual(self.boundary.count("source_apply"), 0)

    def test_crash_after_cache_refresh_recovers_without_duplicate_effect(self):
        self.exercise_crash_recovery("cache_apply")

    def test_crash_after_project_refresh_recovers_without_duplicate_effect(self):
        self.exercise_crash_recovery("project_apply")

    def test_terminal_reentry_is_read_only_and_replays_same_identity(self):
        plan = self.plan()
        complete = self.apply(plan)
        self.assertTrue(complete["ok"], complete)
        mutating_counts = {
            name: self.boundary.count(name)
            for name in (
                "publication_apply",
                "publication_remediate",
                "source_apply",
                "cache_apply",
                "project_apply",
            )
        }
        commit = self.git_output(self.repo, "rev-parse", "HEAD")
        tag = self.git_output(self.remote, "rev-parse", "refs/tags/dev-flow-v0.4.0")

        replay = self.apply(plan)
        verified = self.verify(replay["receipt"])

        self.assertTrue(replay["ok"], replay)
        self.assertEqual(replay["status"], "COMPLETE")
        self.assertEqual(replay["receipt"]["terminalDigest"], complete["receipt"]["terminalDigest"])
        self.assertTrue(verified["ok"], verified)
        self.assertEqual(verified["status"], "COMPLETE")
        self.assertEqual(self.git_output(self.repo, "rev-parse", "HEAD"), commit)
        self.assertEqual(self.git_output(self.remote, "rev-parse", "refs/tags/dev-flow-v0.4.0"), tag)
        self.assertEqual(
            {
                name: self.boundary.count(name)
                for name in (
                    "publication_apply",
                    "publication_remediate",
                    "source_apply",
                    "cache_apply",
                    "project_apply",
                )
            },
            mutating_counts,
        )
        self.assertEqual(self.git_output(self.repo, "rev-list", "--count", f"{self.base}..HEAD"), "1")

    def test_effect_and_terminal_receipts_bind_before_and_after_identity(self):
        plan = self.plan()
        complete = self.apply(plan)

        self.assertTrue(complete["ok"], complete)
        receipt = complete["receipt"]
        self.assertEqual(receipt["schemaVersion"], "1.0")
        self.assertRegex(receipt["terminalDigest"], r"^[0-9a-f]{64}$")
        effects = receipt["effects"]
        self.assertEqual(
            [effect["effect"] for effect in effects],
            [
                "git.commit",
                "git.push",
                "git.tag.push",
                "github.release",
                "devflow.source.fast_forward",
                "codex.cache.refresh",
                "devflow.project.refresh",
            ],
        )
        for effect in effects:
            self.assertIsInstance(effect["beforeIntent"], dict)
            self.assertIsInstance(effect["afterReadback"], dict)
            self.assertRegex(effect["beforeIntentDigest"], r"^[0-9a-f]{64}$", effect)
            self.assertRegex(effect["afterReadbackDigest"], r"^[0-9a-f]{64}$", effect)
            self.assertEqual(effect["contractDigest"], plan["contractDigest"])
            self.assertEqual(effect["candidateDigest"], plan["candidateDigest"])
            self.assertEqual(effect["planDigest"], plan["planDigest"])
        for key in (
            "plan",
            "receiptBinding",
            "contractDigest",
            "candidateDigest",
            "validationDigest",
            "reviewDigest",
            "executionLedgerDigest",
            "publicationIdentity",
            "fiveLayerIdentity",
            "counters",
        ):
            self.assertIn(key, receipt)
        self.assertEqual(receipt["plan"], plan)
        self.assertEqual(receipt["receiptBinding"], plan["receiptBinding"])

    def test_terminal_schema_accepts_the_full_canonical_binding_receipt(self):
        from jsonschema import Draft202012Validator

        complete = self.apply(self.plan())
        self.assertTrue(complete["ok"], complete)
        schema = json.loads(TERMINAL_SCHEMA.read_text())
        errors = sorted(
            Draft202012Validator(schema).iter_errors(complete["receipt"]),
            key=lambda error: list(error.path),
        )
        self.assertEqual([error.message for error in errors], [])

    def test_self_rehashed_partial_terminal_receipt_is_rejected(self):
        complete = self.apply(self.plan())
        partial = copy.deepcopy(complete["receipt"])
        partial.pop("reviewDigest")
        partial.pop("plan")
        partial["terminalDigest"] = canonical_digest(
            {key: value for key, value in partial.items() if key != "terminalDigest"}
        )
        mutation_count = self.boundary.mutating_count()

        report = self.verify(partial)

        self.assert_technical_stop(report, "TERMINAL_RECEIPT_INVALID")
        self.assertEqual(self.boundary.mutating_count(), mutation_count)

    def test_terminal_receipt_directory_binding_is_rechecked_on_verify(self):
        complete = self.apply(self.plan())
        wrong = Path(".planning/devflow/milestone-external-effects/other-contract")
        (self.repo / wrong).mkdir(parents=True)

        report = self.verify(complete["receipt"], receipt_dir=wrong)

        self.assert_technical_stop(report, "RECEIPT_DIRECTORY_UNTRUSTED")

    def test_tampered_terminal_receipt_fails_verification_without_replaying_effects(self):
        plan = self.plan()
        complete = self.apply(plan)
        receipt = copy.deepcopy(complete["receipt"])
        receipt["effects"][0]["afterReadbackDigest"] = "0" * 64
        mutating_count = self.boundary.mutating_count()

        report = self.verify(receipt)

        self.assert_technical_stop(report, "TERMINAL_RECEIPT_INVALID")
        self.assertEqual(self.boundary.mutating_count(), mutating_count)

    def test_excluded_effect_cannot_be_added_by_an_ordinary_step(self):
        invalid = copy.deepcopy(self.contract)
        invalid["requestedEffects"] = [*invalid["requestedEffects"], "github.pr"]
        self.refreeze_contract(invalid)

        report = self.plan()

        self.assert_technical_stop(report, "REQUESTED_EFFECTS_INVALID")
        self.assert_no_git_or_boundary_mutation()

    def test_missing_or_malformed_requested_effects_are_repairs_not_human_gates(self):
        baseline = copy.deepcopy(self.contract)
        cases = {
            "missing": None,
            "not_list": "git.commit",
            "empty": [],
            "mixed_type": ["git.commit", 7],
            "duplicate": ["git.commit", "git.commit"],
            "blank": ["git.commit", "  "],
            "trimmed": ["git.commit", " git.push"],
        }
        for name, requested in cases.items():
            with self.subTest(name=name):
                invalid = copy.deepcopy(baseline)
                if requested is None:
                    invalid.pop("requestedEffects")
                else:
                    invalid["requestedEffects"] = requested
                self.refreeze_contract(invalid)
                report = self.plan()
                self.assert_technical_stop(report, "REQUESTED_EFFECTS_INVALID")
                self.assert_no_git_or_boundary_mutation()

        self.refreeze_contract(baseline)
        self.assert_no_git_or_boundary_mutation()

    def test_shared_contract_validation_precedes_plan_apply_and_verify_mutation(self):
        invalid = copy.deepcopy(self.contract)
        invalid["requestedEffects"] = ["git.commit", "git.commit"]

        planned = plan_milestone_external_effects(
            self.repo,
            invalid,
            candidate_manifest=self.candidate,
            validation_receipt=self.validation,
            review_receipt=self.review,
            execution_ledger=self.long_run,
            receipt_dir=self.receipts,
            boundaries=self.boundary.mapping(),
        )
        self.assert_technical_stop(planned, "REQUESTED_EFFECTS_INVALID")
        self.assert_no_git_or_boundary_mutation()

        valid_plan = self.plan()
        applied = apply_milestone_external_effects(
            self.repo,
            invalid,
            plan=valid_plan,
            receipt_dir=self.receipts,
            boundaries=self.boundary.mapping(),
        )
        self.assert_technical_stop(applied, "REQUESTED_EFFECTS_INVALID")
        self.assert_no_git_or_boundary_mutation()

        complete = self.apply(valid_plan)
        mutation_count = self.boundary.mutating_count()
        verified = verify_milestone_external_effects(
            self.repo,
            invalid,
            receipt=complete["receipt"],
            receipt_dir=self.receipts,
            boundaries=self.boundary.mapping(),
        )
        self.assert_technical_stop(verified, "REQUESTED_EFFECTS_INVALID")
        self.assertEqual(self.boundary.mutating_count(), mutation_count)

    def test_28_event_fixture_is_executed_as_a_dependency_ordered_simulation(self):
        simulation = simulate_milestone_execution_ledger(self.long_run)
        events = self.long_run["events"]

        self.assertTrue(simulation["ok"], simulation)
        self.assertEqual(simulation["transitionCount"], 28)
        self.assertEqual(simulation["executedEventIds"], [event["id"] for event in events])
        self.assertEqual(simulation["falseHumanGateCount"], 0)
        self.assertEqual(simulation["externalEffectCount"], 7)
        self.assertEqual(simulation["duplicateEffectCount"], 0)
        self.assertEqual(simulation["crashRecoveryScenarioCount"], 7)
        self.assertTrue(all(item["reentryVerified"] for item in simulation["crashRecoveryResults"]))
        self.assertEqual(simulation["injectionCount"], 5)
        self.assertTrue(all(item["failedClosedBeforeMutation"] for item in simulation["injectionResults"]))

        plan = self.plan()
        self.assertEqual(plan["executionSimulationDigest"], canonical_digest(simulation))
        complete = self.apply(plan)
        verified = self.verify(complete["receipt"])

        self.assertTrue(verified["ok"], verified)
        self.assertEqual(verified["status"], "COMPLETE")
        self.assertEqual(verified["simulationId"], self.long_run["simulationId"])
        self.assertEqual(verified["eventIds"], [event["id"] for event in events])
        self.assertEqual(verified["falseHumanGateCount"], 0)
        self.assertEqual(verified["duplicateEffectCount"], 0)
        self.assertEqual(verified["externalEffectCount"], 7)

    def test_long_run_injected_failures_are_all_pre_mutation_and_classified(self):
        failures = {item["kind"]: item for item in self.long_run["injectedFailures"]}
        self.assertEqual(set(failures), {
            "contract_ambiguity",
            "reviewed_diff_drift",
            "remote_divergence",
            "tag_collision",
            "undeclared_refresh_target",
        })
        for failure in failures.values():
            self.assertEqual(failure["expectedMutationCount"], 0)
        self.assertEqual(failures["reviewed_diff_drift"]["expectedDecision"], "FAIL_CLOSED_REPAIR")
        self.assertIsNone(failures["reviewed_diff_drift"]["expectedMissingAuthority"])
        for kind in (
            "contract_ambiguity",
            "remote_divergence",
            "tag_collision",
            "undeclared_refresh_target",
        ):
            self.assertEqual(failures[kind]["expectedDecision"], "AWAIT_HUMAN")
            self.assertTrue(failures[kind]["expectedMissingAuthority"])


if __name__ == "__main__":
    unittest.main()
