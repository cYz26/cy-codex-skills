from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import quote


BOUNDARY_NAMES = (
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
)
PROJECT_REFRESH_AUTHORIZATION = "project-refresh-apply"
SOURCE_FAST_FORWARD_EFFECT = "devflow.source.fast_forward"
SHA256 = re.compile(r"[0-9a-f]{64}")
COMMIT = re.compile(r"[0-9a-f]{40}")
TAG = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]*")


class BoundaryConfigurationError(ValueError):
    """The standing contract cannot identify one safe real boundary."""


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str | bytes = ""
    stderr: str | bytes = ""


Runner = Callable[..., object]
ParityVerifier = Callable[[Path, Path, Path], Mapping[str, Any]]


def build_real_boundaries(
    repo: Path,
    contract: Mapping[str, Any],
    *,
    codex_home: Path | None = None,
    runner: Runner | None = None,
    parity_verifier: ParityVerifier | None = None,
    python_executable: str = sys.executable,
    gh_executable: str = "gh",
    codex_executable: str = "codex",
    git_executable: str = "git",
) -> dict[str, object]:
    """Build the exact boundary mapping consumed by the milestone state machine.

    Construction is read-only. Mutating methods remain unavailable until their
    request matches the same standing contract and receipt-bound plan digest.
    """

    adapter = MilestoneRealBoundaries(
        repo,
        contract,
        codex_home=codex_home,
        runner=runner,
        parity_verifier=parity_verifier,
        python_executable=python_executable,
        gh_executable=gh_executable,
        codex_executable=codex_executable,
        git_executable=git_executable,
    )
    return adapter.mapping()


class MilestoneRealBoundaries:
    def __init__(
        self,
        repo: Path,
        contract: Mapping[str, Any],
        *,
        codex_home: Path | None,
        runner: Runner | None,
        parity_verifier: ParityVerifier | None,
        python_executable: str,
        gh_executable: str,
        codex_executable: str,
        git_executable: str,
    ) -> None:
        self.repo = Path(repo).expanduser().resolve()
        if not self.repo.is_dir():
            raise BoundaryConfigurationError("repository path is not a directory")
        self.contract = _plain_mapping(contract)
        self.codex_home = Path(codex_home or Path.home() / ".codex").expanduser().resolve()
        self.runner = runner or _run_command
        self.parity_verifier = parity_verifier or _default_parity_verifier
        self.python_executable = _executable(python_executable, "python executable")
        self.gh_executable = _executable(gh_executable, "GitHub executable")
        self.codex_executable = _executable(codex_executable, "Codex executable")
        self.git_executable = _executable(git_executable, "Git executable")
        self._last_project_receipt: Path | None = None

        plugin = _mapping(self.contract.get("plugin"), "plugin")
        self.plugin = _nonempty(plugin.get("id"), "plugin.id")
        self.marketplace = _nonempty(plugin.get("marketplace"), "plugin.marketplace")
        self.version = _nonempty(plugin.get("version"), "plugin.version")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", self.plugin):
            raise BoundaryConfigurationError("plugin.id is not an exact selector component")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", self.marketplace):
            raise BoundaryConfigurationError("plugin.marketplace is not an exact selector component")
        self.cache_target = f"{self.plugin}@{self.marketplace}"

        repository = _mapping(self.contract.get("repository"), "repository")
        self.remote = _nonempty(repository.get("remote"), "repository.remote")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", self.remote):
            raise BoundaryConfigurationError("repository.remote is not one exact remote")
        self.remote_url = _nonempty(repository.get("remoteUrl"), "repository.remoteUrl")
        self.repository = _github_repository(self.remote_url)
        self.branch_ref = _safe_branch_ref(
            _nonempty(repository.get("ref"), "repository.ref")
        )
        self.expected_base = _nonempty(
            repository.get("expectedBase"), "repository.expectedBase"
        )
        if not COMMIT.fullmatch(self.expected_base):
            raise BoundaryConfigurationError("repository.expectedBase is not one commit")

        publication = _mapping(self.contract.get("publication"), "publication")
        self.tag = _nonempty(publication.get("tag"), "publication.tag")
        if not TAG.fullmatch(self.tag):
            raise BoundaryConfigurationError("publication.tag is not an exact safe tag")
        self.channel = _nonempty(publication.get("channel"), "publication.channel")
        self.mechanism = _nonempty(publication.get("mechanism"), "publication.mechanism")
        if self.mechanism != "github_actions":
            raise BoundaryConfigurationError("only tag-bound GitHub Actions publication is allowed")
        self.workflow = _safe_repo_file(
            self.repo,
            _nonempty(publication.get("workflow"), "publication.workflow"),
        )
        raw_assets = publication.get("assets")
        if not isinstance(raw_assets, list) or not raw_assets:
            raise BoundaryConfigurationError("publication.assets must be a non-empty exact list")
        self.asset_names = tuple(map(str, raw_assets))
        if len(set(self.asset_names)) != len(self.asset_names) or any(
            not name or Path(name).name != name for name in self.asset_names
        ):
            raise BoundaryConfigurationError("publication.assets contains an unsafe or duplicate name")

        refresh = _mapping(self.contract.get("refreshTargets"), "refreshTargets")
        if refresh.get("cache") != self.cache_target:
            raise BoundaryConfigurationError("refreshTargets.cache is not the exact named plugin")
        raw_project = Path(_nonempty(refresh.get("project"), "refreshTargets.project")).expanduser()
        if (
            not raw_project.is_absolute()
            or raw_project.is_symlink()
            or raw_project.resolve() != raw_project
            or not raw_project.is_dir()
        ):
            raise BoundaryConfigurationError("refreshTargets.project must be one real absolute directory")
        self.project_target = str(raw_project)
        self.project = raw_project.resolve()

        exclusions = set(map(str, self.contract.get("exclusions", [])))
        required_exclusions = {
            "archive",
            "force-push",
            "merge",
            "pr",
            "unnamed-consumer",
            "unnamed-plugin",
        }
        if not required_exclusions.issubset(exclusions):
            raise BoundaryConfigurationError("standing contract omits required effect exclusions")

        self.development_root = self.repo / "dev" / "plugins" / self.plugin
        self.release_root = self.repo / "plugins" / self.plugin
        self.cache_root = (
            self.codex_home / "plugins" / "cache" / self.marketplace / self.plugin
        )

    def mapping(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in BOUNDARY_NAMES}

    # Publication is immutable and tag-bound. These methods can only inspect
    # the release or wait for the action that the milestone's tag push started.
    def publication_readback(self, request: object) -> dict[str, Any]:
        identity, issue = self._publication_request(request)
        if issue:
            return _failure(issue)
        assert identity is not None
        release_result = self._run(
            self._gh_api(f"repos/{self.repository}/releases/tags/{quote(self.tag, safe='')}")
        )
        if release_result.returncode != 0:
            detail = _text(release_result.stderr)
            if "404" in detail or "not found" in detail.lower():
                return {"ok": True, "status": "missing", "identity": None, "issues": []}
            return _failure("publication_readback_unavailable", status="unavailable")
        release = _json_mapping(release_result.stdout)
        if release is None:
            return _failure("publication_readback_invalid", status="unavailable")

        observed, issues = self._observed_publication_identity(identity, release)
        status, same_identity = _publication_readback_status(identity, observed, issues)
        return {
            "ok": status in {"published", "pending", "collision"},
            "status": status,
            "identity": observed,
            "issues": issues,
            "sameIdentity": same_identity,
        }

    def publication_apply(self, request: object) -> dict[str, Any]:
        identity, issue = self._publication_request(request)
        if issue:
            return _failure(issue)
        assert identity is not None
        result = self._run(self._run_list_command())
        runs = _json_list(result.stdout) if result.returncode == 0 else None
        if runs is None:
            return _failure("publication_action_readback_failed")
        matching = [
            run
            for run in runs
            if isinstance(run, Mapping) and run.get("headSha") == identity["commit"]
        ]
        if not matching:
            return _failure("tag_bound_publication_action_missing")
        run = matching[0]
        if run.get("status") == "completed":
            return {
                "ok": run.get("conclusion") == "success",
                "status": "observed",
                "runId": run.get("databaseId"),
                "conclusion": run.get("conclusion"),
                "mutated": False,
            }
        run_id = run.get("databaseId")
        if not isinstance(run_id, int) or run_id < 1:
            return _failure("publication_action_identity_invalid")
        watched = self._run(
            [
                self.gh_executable,
                "run",
                "watch",
                str(run_id),
                "--repo",
                self.repository,
                "--exit-status",
            ],
            timeout=1800,
        )
        return {
            "ok": watched.returncode == 0,
            "status": "observed",
            "runId": run_id,
            "conclusion": "success" if watched.returncode == 0 else "failure",
            "mutated": False,
        }

    def publication_diagnose(self, request: object) -> dict[str, Any]:
        _identity, issue = self._publication_request(request)
        if issue:
            return _failure(issue)
        result = self._run(self._run_list_command())
        runs = _json_list(result.stdout) if result.returncode == 0 else None
        return {
            "ok": runs is not None,
            "status": "diagnosed" if runs is not None else "unavailable",
            "runs": runs or [],
            "mutated": False,
        }

    def publication_remediate(self, request: object) -> dict[str, Any]:
        _identity, issue = self._publication_request(request)
        if issue:
            return _failure(issue)
        return {
            "ok": False,
            "status": "no_safe_automatic_remediation",
            "reason": "alternate publication, overwrite, retag, and release fallback are forbidden",
            "mutated": False,
        }

    # The published source checkout is a distinct, named boundary. Planning
    # proves its complete Git identity without mutation; apply replays that
    # proof, performs one exact fast-forward, and then re-reads the same facts.
    def source_plan(self, request: object) -> dict[str, Any]:
        identity, issue = self._target_request(
            request, target=self.project_target, kind="source"
        )
        if issue:
            return _failure(issue)
        assert identity is not None
        snapshot = self._source_snapshot(identity)
        if not snapshot.get("ok"):
            return snapshot
        payload = self._source_plan_payload(identity, snapshot)
        transition = str(payload["transition"])
        return {
            "ok": True,
            "status": "already_current" if transition == "current" else "planned",
            "planDigest": _digest(payload),
            "effect": SOURCE_FAST_FORWARD_EFFECT,
            "target": self.project_target,
            "transition": transition,
            "head": snapshot["head"],
            "remoteCommit": snapshot["remoteCommit"],
            "commands": payload["commands"],
        }

    def source_apply(self, request: object) -> dict[str, Any]:
        identity, issue = self._target_request(
            request,
            target=self.project_target,
            kind="source",
            allow_plan=True,
        )
        if issue:
            return _failure(issue)
        assert identity is not None and isinstance(request, Mapping)
        snapshot = self._source_snapshot(identity)
        if not snapshot.get("ok"):
            return snapshot
        payload = self._source_plan_payload(identity, snapshot)
        plan_digest = _digest(payload)
        if request.get("planDigest") != plan_digest:
            return _failure("source_plan_digest_mismatch")

        if payload["transition"] == "current":
            verified = self.source_verify(
                {"target": self.project_target, "identity": identity}
            )
            if not verified.get("ok"):
                return _failure(
                    "source_post_apply_verification_failed",
                    status="failed",
                    issues=_result_issues(verified),
                )
            return {
                "ok": True,
                "status": "already_current",
                "planDigest": plan_digest,
                "effect": SOURCE_FAST_FORWARD_EFFECT,
                "verification": verified,
            }

        published = str(identity["commit"])
        fetch = [
            self.git_executable,
            "fetch",
            "--no-tags",
            self.remote,
            self.branch_ref,
        ]
        if self._run(fetch, cwd=self.project, timeout=900).returncode != 0:
            return _failure("source_fetch_failed", status="failed")
        fetched = self._run(
            [
                self.git_executable,
                "rev-parse",
                "--verify",
                "FETCH_HEAD^{commit}",
            ],
            cwd=self.project,
        )
        fetched_commit = _text(fetched.stdout).strip() if fetched.returncode == 0 else ""
        if fetched_commit != published:
            return _failure("source_fetched_commit_mismatch", status="failed")

        ancestry = [
            self.git_executable,
            "merge-base",
            "--is-ancestor",
            self.expected_base,
            published,
        ]
        if self._run(ancestry, cwd=self.project).returncode != 0:
            return _failure("source_fast_forward_not_proven", status="failed")
        fast_forward = [self.git_executable, "merge", "--ff-only", published]
        if self._run(fast_forward, cwd=self.project, timeout=900).returncode != 0:
            return _failure("source_fast_forward_failed", status="failed")

        verified = self.source_verify(
            {"target": self.project_target, "identity": identity}
        )
        if not verified.get("ok"):
            return _failure(
                "source_post_apply_verification_failed",
                status="failed",
                issues=_result_issues(verified),
            )
        return {
            "ok": True,
            "status": "applied_and_verified",
            "planDigest": plan_digest,
            "effect": SOURCE_FAST_FORWARD_EFFECT,
            "commands": [fetch, ancestry, fast_forward],
            "verification": verified,
        }

    def source_verify(self, request: object) -> dict[str, Any]:
        identity, issue = self._target_request(
            request,
            target=self.project_target,
            kind="source",
            allow_plan=True,
        )
        if issue:
            return _failure(issue)
        assert identity is not None
        snapshot = self._source_snapshot(identity)
        if not snapshot.get("ok"):
            return snapshot
        if snapshot.get("head") != identity["commit"]:
            return _failure(
                "source_not_current",
                issues=[f"head:{snapshot.get('head')}", f"expected:{identity['commit']}"],
            )
        return {
            "ok": True,
            "status": "verified",
            "effect": SOURCE_FAST_FORWARD_EFFECT,
            "identity": identity,
            "project": self.project_target,
            "head": snapshot["head"],
            "remoteCommit": snapshot["remoteCommit"],
        }

    # Cache refresh is one exact selector. Plan and apply share a canonical
    # digest; verify claims identity only after source/release/cache parity.
    def cache_plan(self, request: object) -> dict[str, Any]:
        identity, issue = self._target_request(request, target=self.cache_target, kind="cache")
        if issue:
            return _failure(issue)
        assert identity is not None
        payload = self._cache_plan_payload(identity)
        return {
            "ok": True,
            "status": "planned",
            "planDigest": _digest(payload),
            "command": list(payload["command"]),
        }

    def cache_apply(self, request: object) -> dict[str, Any]:
        identity, issue = self._target_request(
            request, target=self.cache_target, kind="cache", allow_plan=True
        )
        if issue:
            return _failure(issue)
        assert identity is not None and isinstance(request, Mapping)
        expected = _digest(self._cache_plan_payload(identity))
        if request.get("planDigest") != expected:
            return _failure("cache_plan_digest_mismatch")
        current = self.cache_verify({"target": self.cache_target, "identity": identity})
        if current.get("ok"):
            return {"ok": True, "status": "already_current", "planDigest": expected}
        command = [
            self.codex_executable,
            "plugin",
            "add",
            self.cache_target,
            "--json",
        ]
        result = self._run(command, timeout=900)
        return {
            "ok": result.returncode == 0,
            "status": "applied" if result.returncode == 0 else "failed",
            "planDigest": expected,
            "command": command,
        }

    def cache_verify(self, request: object) -> dict[str, Any]:
        identity, issue = self._target_request(
            request, target=self.cache_target, kind="cache", allow_plan=True
        )
        if issue:
            return _failure(issue)
        assert identity is not None
        candidates = self._version_cache_candidates()
        if len(candidates) != 1:
            return _failure(
                "cache_identity_ambiguous" if candidates else "cache_identity_missing",
                issues=[f"matching_cache_count:{len(candidates)}"],
            )
        cache = candidates[0]
        try:
            parity = _plain_mapping(
                self.parity_verifier(self.development_root, self.release_root, cache)
            )
        except Exception as error:  # fail closed across the diagnostic seam
            return _failure("cache_parity_unavailable", issues=[type(error).__name__])
        if not parity.get("ok"):
            issues = list(map(str, parity.get("errors", [])))
            return _failure("cache_parity_drift", issues=issues or ["unknown_cache_parity_drift"])
        return {
            "ok": True,
            "status": "verified",
            "identity": identity,
            "cachePath": str(cache),
            "parity": parity,
        }

    # Project refresh invokes the one canonical receipt-bound writer from the
    # one exact cache identity. It never traverses or updates another project.
    def project_plan(self, request: object) -> dict[str, Any]:
        identity, issue = self._target_request(
            request, target=self.project_target, kind="project"
        )
        if issue:
            return _failure(issue)
        assert identity is not None
        loaded = self._load_project_plan(identity)
        if not loaded["ok"]:
            return loaded
        report = loaded["report"]
        actions = report.get("actions", [])
        return {
            "ok": True,
            "status": "planned",
            "planDigest": report["planSha256"],
            "actionIds": [str(action["id"]) for action in actions],
            "sourceIdentity": report.get("sourceIdentity"),
        }

    def project_apply(self, request: object) -> dict[str, Any]:
        identity, issue = self._target_request(
            request, target=self.project_target, kind="project", allow_plan=True
        )
        if issue:
            return _failure(issue)
        assert identity is not None and isinstance(request, Mapping)
        loaded = self._load_project_plan(identity)
        if not loaded["ok"]:
            return loaded
        report = loaded["report"]
        if request.get("planDigest") != report.get("planSha256"):
            return _failure("project_plan_digest_mismatch")
        cache = loaded["cache"]
        command = self._project_command("apply", cache)
        command.extend(
            [
                "--expect-plan",
                str(report["planSha256"]),
                "--allow",
                PROJECT_REFRESH_AUTHORIZATION,
            ]
        )
        for action in report.get("actions", []):
            command.extend(["--action", str(action["id"])])
        command.append("--json")
        result = self._run(command, timeout=900)
        applied = _json_mapping(result.stdout) if result.returncode == 0 else None
        if applied is None or not applied.get("ok"):
            return _failure("project_refresh_apply_failed")
        raw_receipt = applied.get("receiptPath")
        if raw_receipt:
            receipt = Path(str(raw_receipt)).expanduser()
            if not receipt.is_absolute():
                receipt = self.project / receipt
            receipt = receipt.resolve()
            if _within(receipt, self.project):
                self._last_project_receipt = receipt
        return {
            "ok": True,
            "status": str(applied.get("status") or "applied"),
            "planDigest": report["planSha256"],
            "receiptPath": str(self._last_project_receipt) if self._last_project_receipt else None,
        }

    def project_verify(self, request: object) -> dict[str, Any]:
        identity, issue = self._target_request(
            request, target=self.project_target, kind="project", allow_plan=True
        )
        if issue:
            return _failure(issue)
        assert identity is not None
        cache_result = self.cache_verify({"target": self.cache_target, "identity": identity})
        if not cache_result.get("ok"):
            return _failure("project_cache_identity_not_current")
        cache = Path(str(cache_result["cachePath"]))
        receipt = self._last_project_receipt or self._state_receipt()
        if receipt is not None:
            if receipt.is_symlink() or not receipt.is_file() or not _within(receipt, self.project):
                return _failure("project_refresh_receipt_untrusted")
            command = self._project_command("verify", cache)
            command.extend(["--receipt", str(receipt), "--json"])
            result = self._run(command, timeout=600)
            verified = _json_mapping(result.stdout) if result.returncode == 0 else None
            if verified is None or not verified.get("ok"):
                return _failure("project_refresh_receipt_verification_failed")
        loaded = self._load_project_plan(identity, known_cache=cache)
        if not loaded["ok"]:
            return loaded
        report = loaded["report"]
        if (
            report.get("status") != "current"
            or report.get("actions")
            or report.get("manualActions")
            or report.get("stateSyncRequired")
        ):
            return _failure("project_refresh_not_current")
        return {
            "ok": True,
            "status": "verified",
            "identity": identity,
            "receiptPath": str(receipt) if receipt is not None else None,
            "project": str(self.project),
        }

    def _publication_request(
        self, request: object
    ) -> tuple[dict[str, Any] | None, str | None]:
        if not isinstance(request, Mapping):
            return None, "publication_request_invalid"
        if set(request) != {"identity", "mechanism", "workflow"}:
            return None, "publication_request_fields_invalid"
        if request.get("mechanism") != self.mechanism:
            return None, "publication_mechanism_mismatch"
        if request.get("workflow") != self.workflow.relative_to(self.repo).as_posix():
            return None, "publication_workflow_mismatch"
        return self._identity(request.get("identity"))

    def _source_snapshot(self, identity: Mapping[str, Any]) -> dict[str, Any]:
        root_result = self._run(
            [self.git_executable, "rev-parse", "--show-toplevel"],
            cwd=self.project,
        )
        root_text = _text(root_result.stdout).strip() if root_result.returncode == 0 else ""
        if not root_text:
            return _failure("source_git_root_unavailable")
        observed_root = Path(root_text).expanduser()
        if (
            not observed_root.is_absolute()
            or observed_root.is_symlink()
            or observed_root != self.project
            or observed_root.resolve() != self.project
        ):
            return _failure("source_git_root_mismatch")

        status_result = self._run(
            [
                self.git_executable,
                "status",
                "--porcelain=v1",
                "--untracked-files=normal",
            ],
            cwd=self.project,
        )
        if status_result.returncode != 0:
            return _failure("source_status_unavailable")
        if _text(status_result.stdout).strip():
            return _failure("source_worktree_dirty")

        branch_result = self._run(
            [self.git_executable, "symbolic-ref", "--quiet", "HEAD"],
            cwd=self.project,
        )
        branch = _text(branch_result.stdout).strip() if branch_result.returncode == 0 else ""
        if branch != self.branch_ref:
            return _failure("source_branch_mismatch")

        remote_result = self._run(
            [self.git_executable, "remote", "get-url", self.remote],
            cwd=self.project,
        )
        remote_lines = (
            [line for line in _text(remote_result.stdout).splitlines() if line]
            if remote_result.returncode == 0
            else []
        )
        if remote_lines != [self.remote_url]:
            return _failure("source_remote_url_mismatch")

        head_result = self._run(
            [self.git_executable, "rev-parse", "--verify", "HEAD^{commit}"],
            cwd=self.project,
        )
        head = _text(head_result.stdout).strip() if head_result.returncode == 0 else ""
        if not COMMIT.fullmatch(head):
            return _failure("source_head_unavailable")

        remote_ref_result = self._run(
            [
                self.git_executable,
                "ls-remote",
                "--exit-code",
                self.remote,
                self.branch_ref,
            ],
            cwd=self.project,
            timeout=900,
        )
        remote_commit = _exact_ls_remote_commit(
            remote_ref_result,
            expected_ref=self.branch_ref,
        )
        if remote_commit is None:
            return _failure("source_remote_ref_unavailable")
        if remote_commit != identity["commit"]:
            return _failure("source_remote_ref_mismatch")
        if head not in {self.expected_base, str(identity["commit"])}:
            return _failure("source_head_outside_contract")
        return {
            "ok": True,
            "status": "current" if head == identity["commit"] else "base",
            "root": self.project_target,
            "branch": branch,
            "remote": self.remote,
            "remoteUrl": self.remote_url,
            "ref": self.branch_ref,
            "head": head,
            "remoteCommit": remote_commit,
        }

    def _source_plan_payload(
        self,
        identity: Mapping[str, Any],
        snapshot: Mapping[str, Any],
    ) -> dict[str, Any]:
        published = str(identity["commit"])
        transition = "current" if snapshot.get("head") == published else "fast_forward"
        commands: list[list[str]] = []
        if transition == "fast_forward":
            commands = [
                [
                    self.git_executable,
                    "fetch",
                    "--no-tags",
                    self.remote,
                    self.branch_ref,
                ],
                [
                    self.git_executable,
                    "merge-base",
                    "--is-ancestor",
                    self.expected_base,
                    published,
                ],
                [self.git_executable, "merge", "--ff-only", published],
            ]
        return {
            "kind": "devflow-source-fast-forward-plan",
            "effect": SOURCE_FAST_FORWARD_EFFECT,
            "target": self.project_target,
            "identity": _plain_mapping(identity),
            "repository": {
                "remote": self.remote,
                "remoteUrl": self.remote_url,
                "ref": self.branch_ref,
                "expectedBase": self.expected_base,
            },
            "observedHead": snapshot.get("head"),
            "observedRemoteCommit": snapshot.get("remoteCommit"),
            "transition": transition,
            "commands": commands,
        }

    def _target_request(
        self,
        request: object,
        *,
        target: str,
        kind: str,
        allow_plan: bool = False,
    ) -> tuple[dict[str, Any] | None, str | None]:
        if not isinstance(request, Mapping):
            return None, f"{kind}_request_invalid"
        allowed = {"target", "identity"} | ({"planDigest"} if allow_plan else set())
        if set(request) - allowed:
            return None, f"{kind}_request_fields_invalid"
        if request.get("target") != target:
            return None, f"unnamed_{kind}_target"
        return self._identity(request.get("identity"))

    def _identity(self, value: object) -> tuple[dict[str, Any] | None, str | None]:
        if not isinstance(value, Mapping):
            return None, "published_identity_invalid"
        identity = _plain_mapping(value)
        expected_fields = {"plugin", "version", "tag", "channel", "commit", "state", "assets"}
        if set(identity) != expected_fields:
            return None, "published_identity_fields_invalid"
        if (
            identity.get("plugin") != self.plugin
            or identity.get("version") != self.version
            or identity.get("tag") != self.tag
            or identity.get("channel") != self.channel
            or identity.get("state") != "published"
            or not COMMIT.fullmatch(str(identity.get("commit") or ""))
        ):
            return None, "published_identity_mismatch"
        assets = identity.get("assets")
        if not isinstance(assets, list) or [
            item.get("name") if isinstance(item, Mapping) else None for item in assets
        ] != list(self.asset_names):
            return None, "published_asset_manifest_mismatch"
        for asset in assets:
            if (
                not isinstance(asset, Mapping)
                or set(asset) != {"name", "size", "sha256"}
                or not isinstance(asset.get("size"), int)
                or int(asset["size"]) < 0
                or not SHA256.fullmatch(str(asset.get("sha256") or ""))
            ):
                return None, "published_asset_identity_invalid"
        return identity, None

    def _observed_publication_identity(
        self, expected: Mapping[str, Any], release: Mapping[str, Any]
    ) -> tuple[dict[str, Any], list[str]]:
        issues: list[str] = []
        tag_commit = self._tag_commit()
        if tag_commit is None:
            tag_commit = "0" * 40
            issues.append("tag_commit_readback_failed")
        if tag_commit != expected["commit"]:
            issues.append("tag_commit_mismatch")
        release_tag = str(release.get("tag_name") or "")
        if release_tag != self.tag:
            issues.append("release_tag_mismatch")
        channel = "stable"
        if bool(release.get("draft")):
            channel = "draft"
            issues.append("release_is_draft")
        elif bool(release.get("prerelease")):
            channel = "prerelease"
            if self.channel != "prerelease":
                issues.append("release_channel_mismatch")

        raw_assets = release.get("assets")
        raw_assets = raw_assets if isinstance(raw_assets, list) else []
        by_name: dict[str, Mapping[str, Any]] = {}
        for asset in raw_assets:
            if not isinstance(asset, Mapping) or not isinstance(asset.get("name"), str):
                issues.append("release_asset_record_invalid")
                continue
            name = str(asset["name"])
            if name in by_name:
                issues.append(f"duplicate_release_asset:{name}")
            by_name[name] = asset
        if set(by_name) != set(self.asset_names):
            issues.append("release_asset_names_mismatch")

        observed_assets: list[dict[str, Any]] = []
        manifest_payload: bytes | None = None
        expected_assets = {
            str(item["name"]): item for item in expected["assets"] if isinstance(item, Mapping)
        }
        for name in self.asset_names:
            expected_asset = expected_assets[name]
            asset = by_name.get(name)
            if asset is None:
                observed_assets.append({"name": name, "size": -1, "sha256": "0" * 64})
                continue
            raw_size = asset.get("size")
            size = int(raw_size) if isinstance(raw_size, int) else -1
            if size != expected_asset["size"]:
                issues.append(f"asset_size_mismatch:{name}")
            digest = _asset_digest(asset.get("digest"))
            payload: bytes | None = None
            if digest is None or name.endswith(".release-manifest.json"):
                payload = self._download_asset(asset)
                if payload is None:
                    issues.append(f"asset_download_failed:{name}")
                    digest = "0" * 64
                else:
                    digest = hashlib.sha256(payload).hexdigest()
            assert digest is not None
            if digest != expected_asset["sha256"]:
                issues.append(f"asset_sha256_mismatch:{name}")
            if name.endswith(".release-manifest.json"):
                manifest_payload = payload
            observed_assets.append({"name": name, "size": size, "sha256": digest})

        if not self._release_manifest_matches(manifest_payload):
            issues.append("release_manifest_identity_mismatch")
        observed = {
            "plugin": self.plugin,
            "version": self.version if self._release_manifest_matches(manifest_payload) else "unknown",
            "tag": release_tag,
            "channel": channel,
            "commit": tag_commit,
            "state": "published",
            "assets": observed_assets,
        }
        if issues and observed == expected:
            observed["state"] = "published-mismatch"
        return observed, sorted(set(issues))

    def _release_manifest_matches(self, payload: bytes | None) -> bool:
        if payload is None:
            return False
        try:
            document = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return False
        return bool(
            isinstance(document, Mapping)
            and document.get("plugin") == self.plugin
            and document.get("version") == self.version
            and document.get("tag") == self.tag
            and document.get("channel") == self.channel
            and document.get("repository") == self.repository
        )

    def _tag_commit(self) -> str | None:
        path = f"repos/{self.repository}/git/ref/tags/{quote(self.tag, safe='')}"
        result = self._run(self._gh_api(path))
        document = _json_mapping(result.stdout) if result.returncode == 0 else None
        current = document.get("object") if isinstance(document, Mapping) else None
        for _ in range(5):
            if not isinstance(current, Mapping):
                return None
            kind = current.get("type")
            sha = str(current.get("sha") or "")
            if not COMMIT.fullmatch(sha):
                return None
            if kind == "commit":
                return sha
            if kind != "tag":
                return None
            result = self._run(self._gh_api(f"repos/{self.repository}/git/tags/{sha}"))
            document = _json_mapping(result.stdout) if result.returncode == 0 else None
            current = document.get("object") if isinstance(document, Mapping) else None
        return None

    def _download_asset(self, asset: Mapping[str, Any]) -> bytes | None:
        identifier = asset.get("id")
        if not isinstance(identifier, int) or identifier < 1:
            return None
        command = self._gh_api(
            f"repos/{self.repository}/releases/assets/{identifier}",
            headers=("Accept: application/octet-stream",),
        )
        result = self._run(command, binary=True, timeout=900)
        if result.returncode != 0:
            return None
        return _bytes(result.stdout)

    def _run_list_command(self) -> list[str]:
        return [
            self.gh_executable,
            "run",
            "list",
            "--repo",
            self.repository,
            "--workflow",
            self.workflow.relative_to(self.repo).as_posix(),
            "--branch",
            self.tag,
            "--event",
            "push",
            "--limit",
            "20",
            "--json",
            "databaseId,status,conclusion,headSha,workflowName,url",
        ]

    def _gh_api(self, path: str, *, headers: Sequence[str] = ()) -> list[str]:
        command = [self.gh_executable, "api", "--method", "GET"]
        for header in headers:
            command.extend(["-H", header])
        command.append(path)
        return command

    def _cache_plan_payload(self, identity: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "kind": "devflow-exact-cache-refresh-plan",
            "target": self.cache_target,
            "identity": identity,
            "codexHome": str(self.codex_home),
            "command": [
                self.codex_executable,
                "plugin",
                "add",
                self.cache_target,
                "--json",
            ],
        }

    def _version_cache_candidates(self) -> list[Path]:
        if self.cache_root.is_symlink() or not self.cache_root.is_dir():
            return []
        candidates: list[Path] = []
        for child in sorted(self.cache_root.iterdir()):
            if child.is_symlink() or not child.is_dir():
                continue
            manifest = child / ".codex-plugin" / "plugin.json"
            if manifest.is_symlink() or not manifest.is_file():
                continue
            try:
                document = json.loads(manifest.read_text())
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            if (
                isinstance(document, Mapping)
                and document.get("name") == self.plugin
                and document.get("version") == self.version
            ):
                candidates.append(child.resolve())
        return candidates

    def _load_project_plan(
        self, identity: Mapping[str, Any], *, known_cache: Path | None = None
    ) -> dict[str, Any]:
        if known_cache is None:
            cache_result = self.cache_verify({"target": self.cache_target, "identity": identity})
            if not cache_result.get("ok"):
                return _failure("project_cache_identity_not_current")
            cache = Path(str(cache_result["cachePath"]))
        else:
            cache = known_cache
        command = self._project_command("plan", cache)
        command.append("--json")
        result = self._run(command, timeout=600)
        report = _json_mapping(result.stdout) if result.returncode == 0 else None
        if report is None:
            return _failure("project_plan_unavailable")
        issues = self._project_plan_issues(report)
        if issues:
            return _failure("project_plan_refused", issues=issues)
        return {"ok": True, "report": report, "cache": cache}

    def _project_plan_issues(self, report: Mapping[str, Any]) -> list[str]:
        issues: list[str] = []
        if not report.get("ok") or report.get("status") not in {"current", "migration_pending"}:
            issues.append(f"project_status:{report.get('status')}")
        raw_repo = report.get("repo")
        if not isinstance(raw_repo, str) or Path(raw_repo).expanduser().resolve() != self.project:
            issues.append("project_repo_identity_mismatch")
        source = report.get("sourceIdentity")
        if not isinstance(source, Mapping) or (
            source.get("plugin") != self.plugin or source.get("pluginVersion") != self.version
        ):
            issues.append("project_source_identity_mismatch")
        digest = str(report.get("planSha256") or "")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}|[0-9a-f]{64}", digest):
            issues.append("project_plan_digest_invalid")
        actions = report.get("actions")
        if not isinstance(actions, list):
            issues.append("project_actions_invalid")
            actions = []
        identifiers: list[str] = []
        for action in actions:
            if not isinstance(action, Mapping) or not action.get("id"):
                issues.append("project_action_invalid")
                continue
            identifiers.append(str(action["id"]))
            if action.get("authorization") != PROJECT_REFRESH_AUTHORIZATION:
                issues.append(f"unauthorized_project_effect:{action.get('authorization')}")
        if len(set(identifiers)) != len(identifiers):
            issues.append("project_action_id_ambiguous")
        manual = report.get("manualActions")
        if not isinstance(manual, list):
            issues.append("project_manual_actions_invalid")
        elif manual:
            issues.append("project_manual_action")
        required = report.get("requiredAuthorizations")
        if not isinstance(required, list):
            issues.append("project_authorizations_invalid")
        else:
            for authority in required:
                if authority != PROJECT_REFRESH_AUTHORIZATION:
                    issues.append(f"unauthorized_project_effect:{authority}")
        return sorted(set(issues))

    def _project_command(self, operation: str, cache: Path) -> list[str]:
        script = cache / "scripts" / "plugin_project_migration.py"
        if script.is_symlink() or not script.is_file() or not _within(script.resolve(), cache):
            raise BoundaryConfigurationError("cache project-refresh CLI is missing or untrusted")
        return [
            self.python_executable,
            str(script),
            operation,
            "--repo",
            self.project_target,
            "--plugin-root",
            str(cache),
            "--codex-home",
            str(self.codex_home),
        ]

    def _state_receipt(self) -> Path | None:
        state = (
            self.project
            / ".planning"
            / "devflow"
            / "plugin-project-migration"
            / "state.json"
        )
        if state.is_symlink() or not state.is_file():
            return None
        try:
            document = json.loads(state.read_text())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        plugins = document.get("plugins") if isinstance(document, Mapping) else None
        entry = plugins.get(self.plugin) if isinstance(plugins, Mapping) else None
        raw = entry.get("lastVerifiedReceipt") if isinstance(entry, Mapping) else None
        if not isinstance(raw, str) or not raw:
            return None
        receipt = Path(raw).expanduser()
        if receipt.is_absolute():
            candidate = receipt.resolve()
        else:
            candidate = (self.project / receipt).resolve()
        return candidate if _within(candidate, self.project) else None

    def _run(
        self,
        command: list[str],
        *,
        binary: bool = False,
        timeout: int = 300,
        cwd: Path | None = None,
    ) -> CommandResult:
        if not command or not all(isinstance(part, str) and part for part in command):
            return CommandResult(2, b"" if binary else "", "invalid command")
        working_directory = Path(cwd or self.repo).expanduser().resolve()
        if working_directory not in {self.repo, self.project}:
            return CommandResult(2, b"" if binary else "", "invalid working directory")
        try:
            raw = self.runner(
                list(command),
                cwd=working_directory,
                binary=binary,
                timeout=timeout,
            )
        except (OSError, subprocess.SubprocessError) as error:
            return CommandResult(127, b"" if binary else "", str(error))
        return _command_result(raw)


def _default_parity_verifier(
    development: Path, release: Path, cache: Path
) -> Mapping[str, Any]:
    from workflow_release_verification import verify_project_refresh_release_parity

    return verify_project_refresh_release_parity(development, release, cache)


def _run_command(
    command: list[str],
    *,
    cwd: Path,
    binary: bool,
    timeout: int,
) -> CommandResult:
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=not binary,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return CommandResult(127, b"" if binary else "", str(error))
    return CommandResult(result.returncode, result.stdout, result.stderr)


def _command_result(value: object) -> CommandResult:
    if isinstance(value, CommandResult):
        return value
    returncode = getattr(value, "returncode", None)
    if not isinstance(returncode, int):
        return CommandResult(127, "", "runner returned an invalid result")
    return CommandResult(
        returncode,
        getattr(value, "stdout", ""),
        getattr(value, "stderr", ""),
    )


def _asset_digest(value: object) -> str | None:
    text = str(value or "")
    if text.startswith("sha256:"):
        text = text.removeprefix("sha256:")
    return text if SHA256.fullmatch(text) else None


def _exact_ls_remote_commit(
    result: CommandResult,
    *,
    expected_ref: str,
) -> str | None:
    if result.returncode != 0:
        return None
    records = []
    for line in _text(result.stdout).splitlines():
        fields = line.split("\t")
        if len(fields) == 2 and fields[1] == expected_ref and COMMIT.fullmatch(fields[0]):
            records.append(fields[0])
        elif line.strip():
            return None
    return records[0] if len(records) == 1 else None


def _result_issues(result: Mapping[str, Any]) -> list[str]:
    issues = [str(item) for item in result.get("issues", [])]
    reason = str(result.get("reason") or "")
    return ([reason] if reason else []) + issues


def _publication_readback_status(
    expected: Mapping[str, Any],
    observed: Mapping[str, Any],
    issues: Sequence[str],
) -> tuple[str, bool]:
    """Separate same-identity publication progress from immutable collision."""

    if not issues and observed == expected:
        return "published", True
    issue_set = set(map(str, issues))
    collision_prefixes = (
        "tag_commit_mismatch",
        "release_tag_mismatch",
        "release_channel_mismatch",
        "release_is_draft",
        "duplicate_release_asset:",
        "release_asset_record_invalid",
        "asset_size_mismatch:",
    )
    if any(
        issue == prefix or issue.startswith(prefix)
        for issue in issue_set
        for prefix in collision_prefixes
    ):
        return "collision", False
    if "tag_commit_readback_failed" in issue_set:
        return "unavailable", False

    missing_assets = {
        str(item.get("name"))
        for item in observed.get("assets", [])
        if isinstance(item, Mapping)
        and (item.get("size") == -1 or item.get("sha256") == "0" * 64)
    }
    download_failures = {
        issue.partition(":")[2]
        for issue in issue_set
        if issue.startswith("asset_download_failed:")
    }
    sha_mismatches = {
        issue.partition(":")[2]
        for issue in issue_set
        if issue.startswith("asset_sha256_mismatch:")
    }
    incomplete_assets = missing_assets | download_failures
    if incomplete_assets and sha_mismatches.issubset(incomplete_assets):
        permitted = {
            "release_asset_names_mismatch",
            "release_manifest_identity_mismatch",
        }
        permitted.update(f"asset_download_failed:{name}" for name in incomplete_assets)
        permitted.update(f"asset_sha256_mismatch:{name}" for name in incomplete_assets)
        if issue_set.issubset(permitted):
            return "pending", True

    return "collision", False


def _github_repository(remote_url: str) -> str:
    patterns = (
        r"git@github\.com:([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?$",
        r"https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$",
        r"ssh://git@github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$",
    )
    for pattern in patterns:
        match = re.fullmatch(pattern, remote_url)
        if match:
            return match.group(1)
    raise BoundaryConfigurationError("repository.remoteUrl is not one exact GitHub repository")


def _safe_branch_ref(value: str) -> str:
    if not re.fullmatch(r"refs/heads/[A-Za-z0-9][A-Za-z0-9._/-]*", value):
        raise BoundaryConfigurationError("repository.ref is not one exact branch ref")
    branch = value.removeprefix("refs/heads/")
    parts = branch.split("/")
    if (
        any(part in {"", ".", ".."} or part.endswith(".") or part.endswith(".lock") for part in parts)
        or ".." in branch
        or "@{" in branch
    ):
        raise BoundaryConfigurationError("repository.ref is not one exact branch ref")
    return value


def _safe_repo_file(repo: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise BoundaryConfigurationError("publication.workflow escapes the repository")
    unresolved = repo / path
    candidate = unresolved.resolve()
    if (
        not _within(candidate, repo)
        or unresolved.is_symlink()
        or candidate != unresolved
        or not candidate.is_file()
    ):
        raise BoundaryConfigurationError("publication.workflow is missing or untrusted")
    return candidate


def _executable(value: str, label: str) -> str:
    text = str(value).strip()
    if not text or "\x00" in text:
        raise BoundaryConfigurationError(f"{label} is invalid")
    return text


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise BoundaryConfigurationError(f"{label} is missing")
    return value


def _nonempty(value: object, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise BoundaryConfigurationError(f"{label} is missing")
    return text


def _plain_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, sort_keys=True))


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _json_mapping(value: str | bytes) -> dict[str, Any] | None:
    try:
        parsed = json.loads(_text(value))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return _plain_mapping(parsed) if isinstance(parsed, Mapping) else None


def _json_list(value: str | bytes) -> list[Any] | None:
    try:
        parsed = json.loads(_text(value))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return json.loads(json.dumps(parsed, sort_keys=True)) if isinstance(parsed, list) else None


def _text(value: str | bytes) -> str:
    return value.decode() if isinstance(value, bytes) else str(value)


def _bytes(value: str | bytes) -> bytes:
    return value if isinstance(value, bytes) else value.encode()


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _failure(
    reason: str,
    *,
    status: str = "refused",
    issues: Sequence[str] = (),
) -> dict[str, Any]:
    return {
        "ok": False,
        "status": status,
        "reason": reason,
        "issues": list(issues),
    }
