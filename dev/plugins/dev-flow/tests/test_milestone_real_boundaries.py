from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

try:
    from workflow_milestone_real_boundaries import (
        BoundaryConfigurationError,
        CommandResult,
        build_real_boundaries,
    )
except ImportError as error:
    IMPORT_ERROR = error
    BoundaryConfigurationError = ValueError
    CommandResult = None
    build_real_boundaries = None
else:
    IMPORT_ERROR = None


def canonical_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.responses: list[tuple[tuple[str, ...], object]] = []

    def add(
        self,
        prefix: list[str],
        *,
        returncode: int = 0,
        stdout: str | bytes = "",
        stderr: str | bytes = "",
    ) -> None:
        if CommandResult is None:
            raise AssertionError("module unavailable")
        self.responses.append(
            (
                tuple(prefix),
                CommandResult(returncode=returncode, stdout=stdout, stderr=stderr),
            )
        )

    def __call__(
        self,
        command: list[str],
        *,
        cwd: Path,
        binary: bool,
        timeout: int,
    ) -> object:
        self.calls.append(
            {
                "command": list(command),
                "cwd": Path(cwd),
                "binary": binary,
                "timeout": timeout,
            }
        )
        for index, (prefix, result) in enumerate(self.responses):
            if tuple(command[: len(prefix)]) == prefix:
                self.responses.pop(index)
                return result
        raise AssertionError(f"unexpected subprocess command: {command}")


class MilestoneRealBoundaryTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="milestone-real-boundaries-")
        self.root = Path(self.temporary.name).resolve()
        self.repo = self.root / "repo"
        self.project = self.root / "source-project"
        self.codex_home = self.root / "codex-home"
        self.repo.mkdir()
        self.project.mkdir()
        self.codex_home.mkdir()
        (self.repo / ".github" / "workflows").mkdir(parents=True)
        (self.repo / ".github" / "workflows" / "publish-dev-flow.yml").write_text(
            "name: Publish DevFlow\n"
        )
        self.development = self.repo / "dev" / "plugins" / "dev-flow"
        self.release = self.repo / "plugins" / "dev-flow"
        self.write_plugin(self.development)
        self.write_plugin(self.release)
        self.contract = self.make_contract()
        self.identity = self.make_identity()
        self.runner = FakeRunner()
        self.parity_calls: list[tuple[Path, Path, Path]] = []

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_plugin(self, root: Path, *, version: str = "0.4.0") -> None:
        manifest = root / ".codex-plugin" / "plugin.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps({"name": "dev-flow", "version": version}) + "\n")
        script = root / "scripts" / "plugin_project_migration.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("# fixture CLI\n")

    def make_contract(self) -> dict[str, object]:
        return {
            "schemaVersion": "1.0",
            "contractId": "dev-flow-authority-delta-v0.4.0",
            "plugin": {
                "id": "dev-flow",
                "marketplace": "cy-codex-skills",
                "version": "0.4.0",
            },
            "repository": {
                "remote": "origin",
                "remoteUrl": "git@github.com:cYz26/cy-codex-skills.git",
                "ref": "refs/heads/main",
                "expectedBase": "e" * 40,
            },
            "publication": {
                "tag": "dev-flow-v0.4.0",
                "channel": "stable",
                "mechanism": "github_actions",
                "workflow": ".github/workflows/publish-dev-flow.yml",
                "assets": [
                    "dev-flow-0.4.0.zip",
                    "dev-flow-0.4.0.release-manifest.json",
                ],
            },
            "refreshTargets": {
                "cache": "dev-flow@cy-codex-skills",
                "project": str(self.project),
            },
            "exclusions": [
                "archive",
                "force-push",
                "merge",
                "pr",
                "unnamed-consumer",
                "unnamed-plugin",
            ],
        }

    def make_identity(self) -> dict[str, object]:
        payloads = {
            "dev-flow-0.4.0.zip": b"deterministic plugin zip",
            "dev-flow-0.4.0.release-manifest.json": json.dumps(
                {
                    "plugin": "dev-flow",
                    "version": "0.4.0",
                    "tag": "dev-flow-v0.4.0",
                    "channel": "stable",
                    "repository": "cYz26/cy-codex-skills",
                },
                sort_keys=True,
            ).encode(),
        }
        self.asset_payloads = payloads
        return {
            "plugin": "dev-flow",
            "version": "0.4.0",
            "tag": "dev-flow-v0.4.0",
            "channel": "stable",
            "commit": "a" * 40,
            "state": "published",
            "assets": [
                {
                    "name": name,
                    "size": len(payloads[name]),
                    "sha256": hashlib.sha256(payloads[name]).hexdigest(),
                }
                for name in self.contract["publication"]["assets"]
            ],
        }

    def parity(self, development: Path, release: Path, cache: Path) -> dict[str, object]:
        self.parity_calls.append((development, release, cache))
        return {"ok": True, "status": "verified", "errors": []}

    def build(self, **overrides: object) -> dict[str, object]:
        arguments: dict[str, object] = {
            "repo": self.repo,
            "contract": self.contract,
            "codex_home": self.codex_home,
            "runner": self.runner,
            "parity_verifier": self.parity,
            "python_executable": "/fixture/python3",
            "gh_executable": "/fixture/gh",
            "codex_executable": "/fixture/codex",
            "git_executable": "/fixture/git",
        }
        arguments.update(overrides)
        return build_real_boundaries(**arguments)

    def publication_request(self, identity: dict[str, object] | None = None) -> dict[str, object]:
        return {
            "identity": copy.deepcopy(identity or self.identity),
            "mechanism": "github_actions",
            "workflow": ".github/workflows/publish-dev-flow.yml",
        }

    def cache_request(self, identity: dict[str, object] | None = None) -> dict[str, object]:
        return {
            "target": "dev-flow@cy-codex-skills",
            "identity": copy.deepcopy(identity or self.identity),
        }

    def project_request(self, identity: dict[str, object] | None = None) -> dict[str, object]:
        return {"target": str(self.project), "identity": copy.deepcopy(identity or self.identity)}

    def source_request(self, identity: dict[str, object] | None = None) -> dict[str, object]:
        return {"target": str(self.project), "identity": copy.deepcopy(identity or self.identity)}

    def add_source_readback(
        self,
        *,
        head: str | None = None,
        clean: bool = True,
        root: Path | None = None,
        branch: str = "refs/heads/main",
        remote_url: str = "git@github.com:cYz26/cy-codex-skills.git",
        remote_commit: str | None = None,
    ) -> None:
        observed_head = head or str(self.contract["repository"]["expectedBase"])
        observed_remote = remote_commit or str(self.identity["commit"])
        self.runner.add(
            ["/fixture/git", "rev-parse", "--show-toplevel"],
            stdout=f"{root or self.project}\n",
        )
        self.runner.add(
            ["/fixture/git", "status", "--porcelain=v1", "--untracked-files=normal"],
            stdout="" if clean else " M tracked.txt\n",
        )
        self.runner.add(
            ["/fixture/git", "symbolic-ref", "--quiet", "HEAD"],
            stdout=f"{branch}\n",
        )
        self.runner.add(
            ["/fixture/git", "remote", "get-url", "origin"],
            stdout=f"{remote_url}\n",
        )
        self.runner.add(
            ["/fixture/git", "rev-parse", "--verify", "HEAD^{commit}"],
            stdout=f"{observed_head}\n",
        )
        self.runner.add(
            [
                "/fixture/git",
                "ls-remote",
                "--exit-code",
                "origin",
                "refs/heads/main",
            ],
            stdout=f"{observed_remote}\trefs/heads/main\n",
        )

    def install_cache(self, *, suffix: str = "0.4.0", version: str = "0.4.0") -> Path:
        cache = self.codex_home / "plugins" / "cache" / "cy-codex-skills" / "dev-flow" / suffix
        self.write_plugin(cache, version=version)
        return cache

    def add_release_responses(
        self,
        *,
        mutate_asset: str | None = None,
        omit_asset: str | None = None,
    ) -> None:
        assets = []
        for index, expected in enumerate(self.identity["assets"], start=11):
            if omit_asset == expected["name"]:
                continue
            item = {"id": index, "name": expected["name"], "size": expected["size"], "digest": None}
            if mutate_asset == expected["name"]:
                item["size"] = int(expected["size"]) + 1
            assets.append(item)
        release = {
            "tag_name": "dev-flow-v0.4.0",
            "draft": False,
            "prerelease": False,
            "assets": assets,
        }
        self.runner.add(
            [
                "/fixture/gh",
                "api",
                "--method",
                "GET",
                "repos/cYz26/cy-codex-skills/releases/tags/dev-flow-v0.4.0",
            ],
            stdout=json.dumps(release),
        )
        self.runner.add(
            [
                "/fixture/gh",
                "api",
                "--method",
                "GET",
                "repos/cYz26/cy-codex-skills/git/ref/tags/dev-flow-v0.4.0",
            ],
            stdout=json.dumps({"object": {"type": "commit", "sha": "a" * 40}}),
        )
        for asset in assets:
            payload = self.asset_payloads[asset["name"]]
            self.runner.add(
                [
                    "/fixture/gh",
                    "api",
                    "--method",
                    "GET",
                    "-H",
                    "Accept: application/octet-stream",
                    f"repos/cYz26/cy-codex-skills/releases/assets/{asset['id']}",
                ],
                stdout=payload,
            )

    def add_project_plan(
        self,
        *,
        status: str = "migration_pending",
        actions: list[dict[str, object]] | None = None,
        manual: list[dict[str, object]] | None = None,
        required: list[str] | None = None,
        plan_sha: str = "sha256:" + "b" * 64,
    ) -> dict[str, object]:
        actions = actions if actions is not None else [
            {
                "id": "refresh-project-orchestrator-link",
                "authorization": "project-refresh-apply",
                "path": ".agents/skills/project-orchestrator",
            }
        ]
        report = {
            "ok": True,
            "status": status,
            "repo": str(self.project),
            "planSha256": plan_sha,
            "sourceIdentity": {"plugin": "dev-flow", "pluginVersion": "0.4.0"},
            "actions": actions,
            "requiredAuthorizations": required if required is not None else (
                ["project-refresh-apply"] if actions else []
            ),
            "manualActions": manual or [],
            "stateSyncRequired": False,
        }
        cache = self.install_cache()
        prefix = [
            "/fixture/python3",
            str(cache / "scripts" / "plugin_project_migration.py"),
            "plan",
            "--repo",
            str(self.project),
            "--plugin-root",
            str(cache),
            "--codex-home",
            str(self.codex_home),
            "--json",
        ]
        self.runner.add(prefix, stdout=json.dumps(report))
        return report

    def test_mapping_exposes_only_the_thirteen_state_machine_boundaries(self) -> None:
        boundaries = self.build()

        self.assertEqual(
            set(boundaries),
            {
                "publication_readback",
                "publication_apply",
                "publication_diagnose",
                "publication_remediate",
                "source_plan",
                "source_apply",
                "source_verify",
                "cache_plan",
                "cache_apply",
                "cache_verify",
                "project_plan",
                "project_apply",
                "project_verify",
            },
        )
        self.assertTrue(all(callable(value) for value in boundaries.values()))
        self.assertEqual(self.runner.calls, [])

    def test_configuration_refuses_non_github_remote_unnamed_target_and_symlink_project(self) -> None:
        for mutate in ("remote", "cache", "project"):
            with self.subTest(mutate=mutate):
                contract = copy.deepcopy(self.contract)
                if mutate == "remote":
                    contract["repository"]["remoteUrl"] = "https://example.invalid/repo.git"
                elif mutate == "cache":
                    contract["refreshTargets"]["cache"] = "dev-flow"
                else:
                    linked = self.root / "project-link"
                    linked.symlink_to(self.project, target_is_directory=True)
                    contract["refreshTargets"]["project"] = str(linked)
                with self.assertRaises(BoundaryConfigurationError):
                    self.build(contract=contract)
        self.assertEqual(self.runner.calls, [])

    def test_configuration_requires_exact_remote_ref_and_expected_base(self) -> None:
        cases = {
            "remote": ("remote", ""),
            "ref": ("ref", "main"),
            "expected-base": ("expectedBase", "not-a-commit"),
        }
        for name, (field, value) in cases.items():
            with self.subTest(name=name):
                contract = copy.deepcopy(self.contract)
                contract["repository"][field] = value
                with self.assertRaises(BoundaryConfigurationError):
                    self.build(contract=contract)
        self.assertEqual(self.runner.calls, [])

    def test_source_plan_and_apply_reuse_an_already_current_checkout(self) -> None:
        boundaries = self.build()
        for _ in range(3):
            self.add_source_readback(head=str(self.identity["commit"]))

        plan = boundaries["source_plan"](self.source_request())
        result = boundaries["source_apply"](
            {**self.source_request(), "planDigest": plan["planDigest"]}
        )

        self.assertEqual(plan["status"], "already_current")
        self.assertEqual(plan["effect"], "devflow.source.fast_forward")
        self.assertEqual(plan["transition"], "current")
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["status"], "already_current")
        self.assertEqual(result["verification"]["status"], "verified")
        effectful = [
            call["command"]
            for call in self.runner.calls
            if call["command"][1] in {"fetch", "merge-base", "merge"}
        ]
        self.assertEqual(effectful, [])
        self.assertTrue(all(call["cwd"] == self.project for call in self.runner.calls))

    def test_source_apply_fast_forwards_only_the_exact_published_commit_and_verifies(self) -> None:
        boundaries = self.build()
        expected_base = str(self.contract["repository"]["expectedBase"])
        published = str(self.identity["commit"])
        self.add_source_readback(head=expected_base)
        plan = boundaries["source_plan"](self.source_request())
        self.add_source_readback(head=expected_base)
        self.runner.add(
            ["/fixture/git", "fetch", "--no-tags", "origin", "refs/heads/main"]
        )
        self.runner.add(
            ["/fixture/git", "rev-parse", "--verify", "FETCH_HEAD^{commit}"],
            stdout=f"{published}\n",
        )
        self.runner.add(
            [
                "/fixture/git",
                "merge-base",
                "--is-ancestor",
                expected_base,
                published,
            ]
        )
        self.runner.add(["/fixture/git", "merge", "--ff-only", published])
        self.add_source_readback(head=published)

        result = boundaries["source_apply"](
            {**self.source_request(), "planDigest": plan["planDigest"]}
        )

        self.assertEqual(plan["transition"], "fast_forward")
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["status"], "applied_and_verified")
        self.assertEqual(result["effect"], "devflow.source.fast_forward")
        self.assertEqual(
            result["verification"]["effect"], "devflow.source.fast_forward"
        )
        commands = [call["command"] for call in self.runner.calls]
        self.assertIn(
            ["/fixture/git", "fetch", "--no-tags", "origin", "refs/heads/main"],
            commands,
        )
        self.assertIn(
            ["/fixture/git", "merge-base", "--is-ancestor", expected_base, published],
            commands,
        )
        self.assertIn(["/fixture/git", "merge", "--ff-only", published], commands)
        self.assertTrue(all(call["cwd"] == self.project for call in self.runner.calls))
        forbidden = {"reset", "rebase", "--force", "force", "delete", "clean"}
        self.assertFalse(
            any(part in forbidden for command in commands for part in command),
            commands,
        )

    def test_source_crash_reentry_uses_authoritative_verify_without_second_apply(self) -> None:
        boundaries = self.build()
        expected_base = str(self.contract["repository"]["expectedBase"])
        published = str(self.identity["commit"])
        self.add_source_readback(head=expected_base)
        plan = boundaries["source_plan"](self.source_request())
        self.add_source_readback(head=expected_base)
        self.runner.add(["/fixture/git", "fetch", "--no-tags", "origin", "refs/heads/main"])
        self.runner.add(
            ["/fixture/git", "rev-parse", "--verify", "FETCH_HEAD^{commit}"],
            stdout=f"{published}\n",
        )
        self.runner.add(
            ["/fixture/git", "merge-base", "--is-ancestor", expected_base, published]
        )
        self.runner.add(["/fixture/git", "merge", "--ff-only", published])
        self.add_source_readback(head=published)
        intent = {**self.source_request(), "planDigest": plan["planDigest"]}
        applied = boundaries["source_apply"](intent)
        self.add_source_readback(head=published)

        recovered = boundaries["source_verify"](intent)

        self.assertTrue(applied["ok"], applied)
        self.assertTrue(recovered["ok"], recovered)
        merge_commands = [
            call["command"]
            for call in self.runner.calls
            if call["command"][:2] == ["/fixture/git", "merge"]
        ]
        self.assertEqual(merge_commands, [["/fixture/git", "merge", "--ff-only", published]])

    def test_source_plan_refuses_dirty_diverged_branch_and_remote_drift(self) -> None:
        cases = (
            ("dirty", {"clean": False}, "source_worktree_dirty"),
            ("diverged", {"head": "d" * 40}, "source_head_outside_contract"),
            (
                "branch",
                {"branch": "refs/heads/other"},
                "source_branch_mismatch",
            ),
            (
                "remote-url",
                {"remote_url": "git@github.com:other/repository.git"},
                "source_remote_url_mismatch",
            ),
            (
                "remote-ref",
                {"remote_commit": "d" * 40},
                "source_remote_ref_mismatch",
            ),
            (
                "git-root",
                {"root": self.root / "other-root"},
                "source_git_root_mismatch",
            ),
        )
        for name, overrides, reason in cases:
            with self.subTest(name=name):
                self.runner = FakeRunner()
                boundaries = self.build()
                self.add_source_readback(**overrides)

                result = boundaries["source_plan"](self.source_request())

                self.assertFalse(result["ok"], result)
                self.assertEqual(result["reason"], reason)
                self.assertFalse(
                    any(
                        call["command"][1] in {"fetch", "merge-base", "merge"}
                        for call in self.runner.calls
                    )
                )

    def test_source_apply_revalidates_the_exact_plan_before_mutation(self) -> None:
        boundaries = self.build()
        self.add_source_readback()
        plan = boundaries["source_plan"](self.source_request())
        self.add_source_readback()
        request = {**self.source_request(), "planDigest": "0" * 64}

        result = boundaries["source_apply"](request)

        self.assertNotEqual(plan["planDigest"], request["planDigest"])
        self.assertEqual(result["reason"], "source_plan_digest_mismatch")
        self.assertFalse(
            any(
                call["command"][1] in {"fetch", "merge-base", "merge"}
                for call in self.runner.calls
            )
        )

    def test_source_apply_stops_when_fast_forward_ancestry_is_not_proven(self) -> None:
        boundaries = self.build()
        expected_base = str(self.contract["repository"]["expectedBase"])
        published = str(self.identity["commit"])
        self.add_source_readback(head=expected_base)
        plan = boundaries["source_plan"](self.source_request())
        self.add_source_readback(head=expected_base)
        self.runner.add(
            ["/fixture/git", "fetch", "--no-tags", "origin", "refs/heads/main"]
        )
        self.runner.add(
            ["/fixture/git", "rev-parse", "--verify", "FETCH_HEAD^{commit}"],
            stdout=f"{published}\n",
        )
        self.runner.add(
            [
                "/fixture/git",
                "merge-base",
                "--is-ancestor",
                expected_base,
                published,
            ],
            returncode=1,
        )

        result = boundaries["source_apply"](
            {**self.source_request(), "planDigest": plan["planDigest"]}
        )

        self.assertEqual(result["reason"], "source_fast_forward_not_proven")
        self.assertNotIn(
            ["/fixture/git", "merge", "--ff-only", published],
            [call["command"] for call in self.runner.calls],
        )

    def test_publication_readback_reports_404_as_missing_without_mutation(self) -> None:
        boundaries = self.build()
        self.runner.add(
            [
                "/fixture/gh",
                "api",
                "--method",
                "GET",
                "repos/cYz26/cy-codex-skills/releases/tags/dev-flow-v0.4.0",
            ],
            returncode=1,
            stderr="HTTP 404: Not Found",
        )

        result = boundaries["publication_readback"](self.publication_request())

        self.assertEqual(result["status"], "missing")
        self.assertIsNone(result["identity"])
        self.assertEqual(len(self.runner.calls), 1)

    def test_publication_readback_verifies_tag_commit_channel_version_and_asset_sha(self) -> None:
        boundaries = self.build()
        self.add_release_responses()

        result = boundaries["publication_readback"](self.publication_request())

        self.assertEqual(
            result,
            {
                "ok": True,
                "status": "published",
                "identity": self.identity,
                "issues": [],
                "sameIdentity": True,
            },
        )
        self.assertEqual(len(self.runner.calls), 4)
        self.assertTrue(all(call["command"][:2] == ["/fixture/gh", "api"] for call in self.runner.calls))
        self.assertTrue(self.runner.calls[-1]["binary"])

    def test_existing_publication_asset_mismatch_is_read_back_as_collision_identity(self) -> None:
        boundaries = self.build()
        self.add_release_responses(mutate_asset="dev-flow-0.4.0.zip")

        result = boundaries["publication_readback"](self.publication_request())

        self.assertEqual(result["status"], "collision")
        self.assertFalse(result["sameIdentity"])
        self.assertNotEqual(result["identity"], self.identity)
        self.assertIn("asset_size_mismatch:dev-flow-0.4.0.zip", result["issues"])

    def test_same_identity_release_with_incomplete_assets_is_technical_pending(self) -> None:
        boundaries = self.build()
        self.add_release_responses(omit_asset="dev-flow-0.4.0.zip")

        result = boundaries["publication_readback"](self.publication_request())

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["status"], "pending")
        self.assertTrue(result["sameIdentity"])
        self.assertIn("release_asset_names_mismatch", result["issues"])

    def test_publication_apply_only_waits_for_matching_tag_bound_action(self) -> None:
        boundaries = self.build()
        run = {
            "databaseId": 77,
            "status": "in_progress",
            "conclusion": None,
            "headSha": "a" * 40,
            "workflowName": "Publish DevFlow 0.4.0",
            "url": "https://github.com/cYz26/cy-codex-skills/actions/runs/77",
        }
        self.runner.add(
            [
                "/fixture/gh",
                "run",
                "list",
                "--repo",
                "cYz26/cy-codex-skills",
                "--workflow",
                ".github/workflows/publish-dev-flow.yml",
                "--branch",
                "dev-flow-v0.4.0",
                "--event",
                "push",
                "--limit",
                "20",
                "--json",
                "databaseId,status,conclusion,headSha,workflowName,url",
            ],
            stdout=json.dumps([run]),
        )
        self.runner.add(
            [
                "/fixture/gh",
                "run",
                "watch",
                "77",
                "--repo",
                "cYz26/cy-codex-skills",
                "--exit-status",
            ]
        )

        result = boundaries["publication_apply"](self.publication_request())

        self.assertTrue(result["ok"], result)
        flattened = [part for call in self.runner.calls for part in call["command"]]
        self.assertNotIn("release", flattened)
        self.assertNotIn("create", flattened)

    def test_publication_refuses_wrong_workflow_or_identity_before_subprocess(self) -> None:
        boundaries = self.build()
        wrong_workflow = self.publication_request()
        wrong_workflow["workflow"] = ".github/workflows/other.yml"
        wrong_identity = self.publication_request()
        wrong_identity["identity"]["plugin"] = "other-plugin"

        first = boundaries["publication_apply"](wrong_workflow)
        second = boundaries["publication_readback"](wrong_identity)
        remediation = boundaries["publication_remediate"](self.publication_request())

        self.assertFalse(first["ok"])
        self.assertFalse(second["ok"])
        self.assertFalse(remediation["ok"])
        self.assertFalse(remediation["mutated"])
        self.assertEqual(self.runner.calls, [])

    def test_cache_plan_is_deterministic_and_refuses_other_plugin_or_target(self) -> None:
        boundaries = self.build()
        request = self.cache_request()

        first = boundaries["cache_plan"](request)
        second = boundaries["cache_plan"](copy.deepcopy(request))
        other = self.cache_request()
        other["target"] = "other@cy-codex-skills"

        self.assertTrue(first["ok"])
        self.assertEqual(first["planDigest"], second["planDigest"])
        self.assertRegex(first["planDigest"], r"^[0-9a-f]{64}$")
        self.assertFalse(boundaries["cache_plan"](other)["ok"])
        self.assertEqual(self.runner.calls, [])

    def test_cache_apply_uses_only_exact_named_json_command_and_binds_plan(self) -> None:
        boundaries = self.build()
        plan = boundaries["cache_plan"](self.cache_request())
        intent = {**self.cache_request(), "planDigest": plan["planDigest"]}
        self.runner.add(
            ["/fixture/codex", "plugin", "add", "dev-flow@cy-codex-skills", "--json"],
            stdout=json.dumps({"ok": True}),
        )

        result = boundaries["cache_apply"](intent)

        self.assertTrue(result["ok"], result)
        self.assertEqual(
            self.runner.calls[0]["command"],
            ["/fixture/codex", "plugin", "add", "dev-flow@cy-codex-skills", "--json"],
        )
        drift = copy.deepcopy(intent)
        drift["planDigest"] = "0" * 64
        self.assertFalse(boundaries["cache_apply"](drift)["ok"])
        self.assertEqual(len(self.runner.calls), 1)

    def test_cache_verify_requires_one_exact_version_and_source_release_cache_parity(self) -> None:
        boundaries = self.build()
        cache = self.install_cache()

        result = boundaries["cache_verify"](self.cache_request())

        self.assertEqual(result["identity"], self.identity)
        self.assertEqual(result["cachePath"], str(cache.resolve()))
        self.assertEqual(
            self.parity_calls,
            [(self.development.resolve(), self.release.resolve(), cache.resolve())],
        )
        self.install_cache(suffix="0.4.0+duplicate")
        ambiguous = boundaries["cache_verify"](self.cache_request())
        self.assertFalse(ambiguous["ok"])
        self.assertNotIn("identity", ambiguous)

    def test_cache_verify_refuses_parity_drift_without_identity_claim(self) -> None:
        self.install_cache()

        def drift(*_args: Path) -> dict[str, object]:
            return {"ok": False, "status": "drift", "errors": ["cache_file_mismatch"]}

        boundaries = self.build(parity_verifier=drift)
        result = boundaries["cache_verify"](self.cache_request())

        self.assertFalse(result["ok"])
        self.assertNotIn("identity", result)
        self.assertIn("cache_file_mismatch", result["issues"])

    def test_project_plan_is_exact_target_receipt_bound_and_allows_only_reference_actions(self) -> None:
        boundaries = self.build()
        report = self.add_project_plan()

        result = boundaries["project_plan"](self.project_request())

        self.assertEqual(result["status"], "planned")
        self.assertEqual(result["planDigest"], report["planSha256"])
        self.assertEqual(result["actionIds"], ["refresh-project-orchestrator-link"])
        command = self.runner.calls[0]["command"]
        self.assertEqual(command[0], "/fixture/python3")
        self.assertEqual(command[2], "plan")
        self.assertEqual(command[command.index("--repo") + 1], str(self.project))
        self.assertEqual(command[-1], "--json")

    def test_project_plan_refuses_manual_ownership_or_new_authority(self) -> None:
        boundaries = self.build()
        self.add_project_plan(
            manual=[{"path": "AGENTS.md.generated", "reason": "candidate_ownership_ambiguous"}],
            required=["project-refresh-apply", "workflow-config-migration"],
        )

        result = boundaries["project_plan"](self.project_request())

        self.assertFalse(result["ok"])
        self.assertIn("project_manual_action", result["issues"])
        self.assertIn("unauthorized_project_effect:workflow-config-migration", result["issues"])

    def test_project_apply_recomputes_plan_and_selects_only_exact_action_ids(self) -> None:
        boundaries = self.build()
        plan_report = self.add_project_plan()
        plan = boundaries["project_plan"](self.project_request())
        self.add_project_plan()
        apply_report = {
            "ok": True,
            "status": "applied_and_verified",
            "repo": str(self.project),
            "receiptPath": str(
                self.project
                / ".planning"
                / "devflow"
                / "plugin-project-migration"
                / "receipts"
                / "apply-fixture.json"
            ),
        }
        cache = self.codex_home / "plugins" / "cache" / "cy-codex-skills" / "dev-flow" / "0.4.0"
        apply_prefix = [
            "/fixture/python3",
            str(cache / "scripts" / "plugin_project_migration.py"),
            "apply",
            "--repo",
            str(self.project),
            "--plugin-root",
            str(cache),
            "--codex-home",
            str(self.codex_home),
            "--expect-plan",
            plan_report["planSha256"],
            "--allow",
            "project-refresh-apply",
            "--action",
            "refresh-project-orchestrator-link",
            "--json",
        ]
        self.runner.add(apply_prefix, stdout=json.dumps(apply_report))

        result = boundaries["project_apply"](
            {**self.project_request(), "planDigest": plan["planDigest"]}
        )

        self.assertTrue(result["ok"], result)
        self.assertEqual(self.runner.calls[-1]["command"], apply_prefix)

    def test_project_verify_uses_receipt_then_requires_fresh_current_plan(self) -> None:
        boundaries = self.build()
        cache = self.install_cache()
        receipt = (
            self.project
            / ".planning"
            / "devflow"
            / "plugin-project-migration"
            / "receipts"
            / "apply-fixture.json"
        )
        receipt.parent.mkdir(parents=True)
        receipt.write_text("{}\n")
        state = receipt.parents[1] / "state.json"
        state.write_text(
            json.dumps(
                {
                    "plugins": {
                        "dev-flow": {
                            "lastVerifiedReceipt": receipt.relative_to(self.project).as_posix()
                        }
                    }
                }
            )
        )
        verify_report = {"ok": True, "status": "verified", "repo": str(self.project)}
        self.runner.add(
            [
                "/fixture/python3",
                str(cache / "scripts" / "plugin_project_migration.py"),
                "verify",
                "--repo",
                str(self.project),
                "--plugin-root",
                str(cache),
                "--codex-home",
                str(self.codex_home),
                "--receipt",
                str(receipt),
                "--json",
            ],
            stdout=json.dumps(verify_report),
        )
        self.add_project_plan(status="current", actions=[], required=[])

        result = boundaries["project_verify"](self.project_request())

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["identity"], self.identity)
        self.assertEqual(result["receiptPath"], str(receipt))

    def test_project_crash_reentry_verifies_receipt_without_second_apply(self) -> None:
        boundaries = self.build()
        plan_report = self.add_project_plan()
        plan = boundaries["project_plan"](self.project_request())
        self.add_project_plan()
        receipt = (
            self.project
            / ".planning"
            / "devflow"
            / "plugin-project-migration"
            / "receipts"
            / "reentry-fixture.json"
        )
        apply_report = {
            "ok": True,
            "status": "applied_and_verified",
            "repo": str(self.project),
            "receiptPath": str(receipt),
        }
        cache = self.codex_home / "plugins" / "cache" / "cy-codex-skills" / "dev-flow" / "0.4.0"
        apply_prefix = [
            "/fixture/python3",
            str(cache / "scripts" / "plugin_project_migration.py"),
            "apply",
            "--repo",
            str(self.project),
            "--plugin-root",
            str(cache),
            "--codex-home",
            str(self.codex_home),
            "--expect-plan",
            plan_report["planSha256"],
            "--allow",
            "project-refresh-apply",
            "--action",
            "refresh-project-orchestrator-link",
            "--json",
        ]
        self.runner.add(apply_prefix, stdout=json.dumps(apply_report))
        intent = {**self.project_request(), "planDigest": plan["planDigest"]}
        applied = boundaries["project_apply"](intent)
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text("{}\n")
        verify_prefix = [
            "/fixture/python3",
            str(cache / "scripts" / "plugin_project_migration.py"),
            "verify",
            "--repo",
            str(self.project),
            "--plugin-root",
            str(cache),
            "--codex-home",
            str(self.codex_home),
            "--receipt",
            str(receipt),
            "--json",
        ]
        self.runner.add(
            verify_prefix,
            stdout=json.dumps({"ok": True, "status": "verified", "repo": str(self.project)}),
        )
        self.add_project_plan(status="current", actions=[], required=[])

        recovered = boundaries["project_verify"](intent)

        self.assertTrue(applied["ok"], applied)
        self.assertTrue(recovered["ok"], recovered)
        apply_commands = [
            call["command"] for call in self.runner.calls if len(call["command"]) > 2 and call["command"][2] == "apply"
        ]
        self.assertEqual(apply_commands, [apply_prefix])

    def test_project_refuses_unnamed_consumer_before_any_subprocess(self) -> None:
        boundaries = self.build()
        request = self.project_request()
        request["target"] = str(self.root / "other-project")

        for name in ("project_plan", "project_apply", "project_verify"):
            with self.subTest(name=name):
                result = boundaries[name](copy.deepcopy(request))
                self.assertFalse(result["ok"])
        self.assertEqual(self.runner.calls, [])

    def test_all_effectful_commands_are_argument_vectors_without_shell_fallbacks(self) -> None:
        boundaries = self.build()
        plan = boundaries["cache_plan"](self.cache_request())
        self.runner.add(
            ["/fixture/codex", "plugin", "add", "dev-flow@cy-codex-skills", "--json"],
            stdout="{}",
        )
        boundaries["cache_apply"]({**self.cache_request(), "planDigest": plan["planDigest"]})

        for call in self.runner.calls:
            self.assertIsInstance(call["command"], list)
            self.assertTrue(all(isinstance(part, str) for part in call["command"]))
            self.assertNotIn("sh", Path(call["command"][0]).name)
            self.assertNotIn("bash", Path(call["command"][0]).name)
            self.assertFalse(any("force" in part or "delete" in part for part in call["command"]))


if __name__ == "__main__":
    unittest.main()
