from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit


GIT_TRANSPORT_READY = "GIT_TRANSPORT_READY"
GIT_TRANSPORT_BLOCKED = "GIT_TRANSPORT_BLOCKED"
DEFAULT_GIT_TRANSPORT_TIMEOUT_SECONDS = 15.0
GITHUB_DIAGNOSIS_LIMIT = 1
GITHUB_REMEDIATION_LIMIT = 1

GitRunner = Callable[..., subprocess.CompletedProcess[str]]

_REMOTE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,254}")
_SCP_LIKE_REMOTE = re.compile(r"(?:[^@/:\s]+@)?[^/:\s]+:.+")
_INVALID_REF_CHARACTERS = re.compile(r"[\x00-\x20\x7f~^:?*\[\\]")

_REPOSITORY_OPERATION_ROUTES = {
    "commit": {
        "capability": "native_git_local",
        "effect": "git.commit",
        "requiresGh": False,
    },
    "push": {
        "capability": "native_git_transport",
        "effect": "git.push",
        "requiresGh": False,
    },
    "push-tag": {
        "capability": "native_git_transport",
        "effect": "git.push",
        "requiresGh": False,
    },
    "pull-request": {
        "capability": "github_control_plane",
        "effect": "github.control_plane_write",
        "requiresGh": True,
    },
    "release": {
        "capability": "github_control_plane",
        "effect": "github.control_plane_write",
        "requiresGh": False,
        "directControlPlaneRequiresGh": True,
        "preferredExecutionPaths": [
            "github_actions",
            "github_cli",
            "human_web",
        ],
        "requiredEffects": [
            "git.push",
            "github.control_plane_write",
        ],
        "workflowMustBeInTriggerCommit": True,
        "immutableTriggerRequired": True,
        "leastPrivilegeTokenRequired": True,
        "postPublicationReadbackRequired": True,
        "localPromotionBlockedUntilReadback": True,
        "preserveTriggerOnFailure": True,
    },
    "repository-settings": {
        "capability": "github_control_plane",
        "effect": "github.control_plane_write",
        "requiresGh": True,
    },
}

_OPERATION_ALIASES = {
    "pr": "pull-request",
    "pull_request": "pull-request",
    "repo-settings": "repository-settings",
    "repository_settings": "repository-settings",
    "tag-push": "push-tag",
}


def git_branch(repo: Path) -> str:
    result = run_git(repo, "branch", "--show-current")
    return result or "no-git"


def git_changed_files(repo: Path) -> str:
    result = run_git(repo, "status", "--short")
    if not result:
        return "  - none"
    return "\n".join(f"  - {line}" for line in result.splitlines())


def route_repository_operation(operation: str) -> dict[str, Any]:
    normalized = operation.strip().lower()
    normalized = _OPERATION_ALIASES.get(normalized, normalized)
    route = _REPOSITORY_OPERATION_ROUTES.get(normalized)
    if route is None:
        supported = ", ".join(sorted(_REPOSITORY_OPERATION_ROUTES))
        raise ValueError(
            f"unsupported repository operation {operation!r}; expected one of: {supported}"
        )
    return {"operation": normalized, **route}


def github_control_plane_recovery_decision(
    diagnosis_attempts: int,
    remediation_attempts: int,
) -> dict[str, Any]:
    if diagnosis_attempts < 0 or remediation_attempts < 0:
        raise ValueError("GitHub recovery attempt counts cannot be negative")
    if diagnosis_attempts < GITHUB_DIAGNOSIS_LIMIT:
        action = "diagnose"
    elif remediation_attempts < GITHUB_REMEDIATION_LIMIT:
        action = "remediate"
    else:
        action = "stop"
    return {
        "effect": "github.control_plane_write",
        "action": action,
        "retryAllowed": action != "stop",
        "diagnosisAttempts": diagnosis_attempts,
        "diagnosisLimit": GITHUB_DIAGNOSIS_LIMIT,
        "remediationAttempts": remediation_attempts,
        "remediationLimit": GITHUB_REMEDIATION_LIMIT,
    }


def classify_remote_transport(url: str) -> str:
    value = url.strip()
    lowered = value.lower()
    if not value:
        return "unknown"
    if "://" not in value and _SCP_LIKE_REMOTE.fullmatch(value):
        return "ssh"
    scheme = urlsplit(value).scheme.lower()
    if scheme in {"ssh", "git+ssh"}:
        return "ssh"
    if scheme in {"http", "https"}:
        return scheme
    if scheme == "git":
        return "git"
    if scheme == "file":
        return "file"
    if Path(value).is_absolute() or lowered.startswith(("./", "../", "~/")):
        return "file"
    if not scheme:
        return "file"
    return "other"


def redact_remote_url(url: str) -> str:
    value = url.strip()
    if not value:
        return value
    if "://" not in value and _SCP_LIKE_REMOTE.fullmatch(value):
        return value
    parts = urlsplit(value)
    if not parts.scheme:
        return value.split("?", 1)[0].split("#", 1)[0]
    if parts.hostname is None:
        return f"{parts.scheme}://[redacted]"
    hostname = parts.hostname
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    try:
        parsed_port = parts.port
    except ValueError:
        return f"{parts.scheme}://[redacted]"
    port = f":{parsed_port}" if parsed_port is not None else ""
    userinfo = "***@" if parts.username is not None or parts.password is not None else ""
    return urlunsplit((parts.scheme, f"{userinfo}{hostname}{port}", parts.path, "", ""))


def sanitize_git_diagnostic(
    message: str,
    remote_urls: list[str] | tuple[str, ...] = (),
) -> str:
    sanitized = message.strip()
    for raw in sorted({url for url in remote_urls if url}, key=len, reverse=True):
        sanitized = sanitized.replace(raw, redact_remote_url(raw))
    sanitized = re.sub(r"(https?://)[^/@\s'\"]+@", r"\1***@", sanitized)
    sanitized = re.sub(
        r"(https?://[^?#\s'\"]+)[?#][^\s'\"]*",
        r"\1",
        sanitized,
    )
    return sanitized[:1000]


def git_transport_preflight(
    repo: Path,
    *,
    remote: str = "origin",
    branch: str | None = None,
    timeout_seconds: float = DEFAULT_GIT_TRANSPORT_TIMEOUT_SECONDS,
    runner: GitRunner = subprocess.run,
) -> dict[str, Any]:
    repository = Path(repo).expanduser().resolve()
    report = _initial_preflight_report(repository, remote, branch)

    if timeout_seconds <= 0:
        return _block_preflight(report, "invalid_timeout", "timeout must be greater than zero")
    if not _valid_remote_name(remote):
        return _block_preflight(report, "invalid_remote_name", "remote name is invalid")
    if branch is not None and not _valid_branch_name(branch):
        return _block_preflight(report, "invalid_branch_name", "branch name is invalid")

    try:
        _checked_git(
            repository,
            "rev-parse",
            "--git-dir",
            failure_reason="not_a_git_repository",
            runner=runner,
            timeout_seconds=timeout_seconds,
        )
        selected_branch = _resolve_preflight_branch(
            repository,
            branch,
            runner=runner,
            timeout_seconds=timeout_seconds,
        )
        report["branch"] = selected_branch
        report["localCommit"] = _resolve_local_commit(
            repository,
            selected_branch,
            runner=runner,
            timeout_seconds=timeout_seconds,
        )
        remote_url = _resolve_remote_url(
            repository,
            remote,
            runner=runner,
            timeout_seconds=timeout_seconds,
        )
        report["remote"] = {
            "name": remote,
            "url": redact_remote_url(remote_url),
            "transport": classify_remote_transport(remote_url),
        }
        report["remoteCommit"] = _probe_remote_commit(
            repository,
            remote,
            selected_branch,
            remote_url,
            runner=runner,
            timeout_seconds=timeout_seconds,
        )
        return _ready_preflight(report)
    except _PreflightFailure as error:
        return _block_preflight(report, error.reason, error.diagnostic)
    except subprocess.TimeoutExpired as error:
        return _block_preflight(
            report,
            "remote_probe_timeout",
            sanitize_git_diagnostic(str(error)),
        )
    except OSError as error:
        return _block_preflight(
            report,
            "git_unavailable",
            sanitize_git_diagnostic(str(error)),
        )


class _PreflightFailure(Exception):
    def __init__(self, reason: str, diagnostic: str):
        super().__init__(diagnostic)
        self.reason = reason
        self.diagnostic = diagnostic


def _initial_preflight_report(
    repository: Path,
    remote: str,
    branch: str | None,
) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "status": GIT_TRANSPORT_BLOCKED,
        "reason": "preflight_not_run",
        "operation": "push",
        "effect": "git.push",
        "repository": str(repository),
        "branch": branch,
        "localCommit": None,
        "remoteCommit": None,
        "remote": {"name": remote, "url": None, "transport": "unknown"},
        "requiresGh": False,
        "pushAttempted": False,
        "authorizationRequired": "explicit_user_request",
        "diagnostic": None,
        "nextAction": "repair_native_git_transport",
    }


def _resolve_preflight_branch(
    repository: Path,
    branch: str | None,
    *,
    runner: GitRunner,
    timeout_seconds: float,
) -> str:
    if branch is not None:
        return branch
    result = _checked_git(
        repository,
        "symbolic-ref",
        "--quiet",
        "--short",
        "HEAD",
        failure_reason="branch_required",
        require_output=True,
        runner=runner,
        timeout_seconds=timeout_seconds,
    )
    selected = result.stdout.strip()
    if not _valid_branch_name(selected):
        raise _PreflightFailure("invalid_branch_name", "current branch name is invalid")
    return selected


def _resolve_local_commit(
    repository: Path,
    branch: str,
    *,
    runner: GitRunner,
    timeout_seconds: float,
) -> str:
    result = _checked_git(
        repository,
        "rev-parse",
        "--verify",
        f"refs/heads/{branch}^{{commit}}",
        failure_reason="local_branch_missing",
        require_output=True,
        runner=runner,
        timeout_seconds=timeout_seconds,
    )
    return result.stdout.strip()


def _resolve_remote_url(
    repository: Path,
    remote: str,
    *,
    runner: GitRunner,
    timeout_seconds: float,
) -> str:
    result = _checked_git(
        repository,
        "remote",
        "get-url",
        "--push",
        remote,
        failure_reason="remote_not_configured",
        require_output=True,
        runner=runner,
        timeout_seconds=timeout_seconds,
    )
    return result.stdout.strip().splitlines()[0]


def _probe_remote_commit(
    repository: Path,
    remote: str,
    branch: str,
    remote_url: str,
    *,
    runner: GitRunner,
    timeout_seconds: float,
) -> str | None:
    expected_ref = f"refs/heads/{branch}"
    result = _checked_git(
        repository,
        "ls-remote",
        "--heads",
        remote,
        expected_ref,
        failure_reason="remote_probe_failed",
        remote_urls=[remote_url],
        runner=runner,
        timeout_seconds=timeout_seconds,
    )
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[1] == expected_ref:
            return fields[0]
    return None


def _ready_preflight(report: dict[str, Any]) -> dict[str, Any]:
    report.update(
        {
            "status": GIT_TRANSPORT_READY,
            "reason": (
                "remote_branch_found"
                if report["remoteCommit"]
                else "remote_reachable_branch_absent"
            ),
            "diagnostic": None,
            "nextAction": "request_or_verify_git_push_authorization",
        }
    )
    return report


def _checked_git(
    repo: Path,
    *args: str,
    failure_reason: str,
    runner: GitRunner,
    timeout_seconds: float,
    require_output: bool = False,
    remote_urls: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = _run_git_result(
        repo,
        *args,
        runner=runner,
        timeout_seconds=timeout_seconds,
    )
    if result.returncode == 0 and (not require_output or result.stdout.strip()):
        return result
    detail = result.stderr.strip() or result.stdout.strip() or failure_reason
    raise _PreflightFailure(
        failure_reason,
        sanitize_git_diagnostic(detail, remote_urls or []),
    )


def _run_git_result(
    repo: Path,
    *args: str,
    runner: GitRunner,
    timeout_seconds: float,
) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["GIT_TERMINAL_PROMPT"] = "0"
    return runner(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout_seconds,
        env=environment,
    )


def _block_preflight(
    report: dict[str, Any],
    reason: str,
    diagnostic: str,
) -> dict[str, Any]:
    report.update(
        {
            "status": GIT_TRANSPORT_BLOCKED,
            "reason": reason,
            "diagnostic": diagnostic,
            "nextAction": "repair_native_git_transport",
        }
    )
    return report


def _valid_remote_name(remote: str) -> bool:
    return bool(
        _REMOTE_NAME.fullmatch(remote)
        and ".." not in remote
        and "//" not in remote
        and not remote.endswith(("/", ".lock"))
    )


def _valid_branch_name(branch: str) -> bool:
    return bool(
        branch
        and len(branch) <= 1024
        and not branch.startswith(("-", ".", "/"))
        and not branch.endswith((".", "/", ".lock"))
        and ".." not in branch
        and "//" not in branch
        and "@{" not in branch
        and "/." not in branch
        and not _INVALID_REF_CHARACTERS.search(branch)
    )


def run_git(repo: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            text=True,
            capture_output=True,
            check=False,
            timeout=3,
        )
    except Exception:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""
