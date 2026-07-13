from __future__ import annotations

import fnmatch
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any


PLUGIN_INCLUDE = [
    ".codex-plugin/**",
    "docs/**",
    "skills/**",
    "hooks.json",
    "scripts/**",
    "assets/**",
    "agents/**",
    ".mcp.json",
    ".app.json",
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
    "LICENSE.*",
]
SKILL_INCLUDE = [
    "SKILL.md",
    "references/**",
    "assets/**",
    "scripts/**",
    "agents/**",
]
DEFAULT_EXCLUDE = [
    "tests/**",
    "test/**",
    "fixtures/**",
    "fixture/**",
    "log/**",
    "logs/**",
    "eval/**",
    "evals/**",
    "reports/**",
    ".reports/**",
    ".eval/**",
    "docs/superpowers/**",
    "__pycache__/**",
    ".pytest_cache/**",
    ".mypy_cache/**",
    "tmp/**",
    "scratch/**",
    "*.pyc",
    "*.pyo",
    "*.log",
    "*.tmp",
    ".DS_Store",
]
_RELEASE_APPLY_AUTHORIZATION_TTL_SECONDS = 5.0
_RELEASE_APPLY_AUTHORIZATION_SEAL = object()


class _ReleaseApplyAuthorization:
    __slots__ = ()

    def __new__(cls, seal: object) -> _ReleaseApplyAuthorization:
        if seal is not _RELEASE_APPLY_AUTHORIZATION_SEAL:
            raise TypeError("release apply authorization is issued internally")
        return super().__new__(cls)


@dataclass(frozen=True)
class _ReleaseApplyAuthorizationRecord:
    repo: Path
    targets: tuple[str, ...]
    expires_at: float


_ACTIVE_RELEASE_APPLY_AUTHORIZATIONS: dict[
    _ReleaseApplyAuthorization,
    _ReleaseApplyAuthorizationRecord,
] = {}


@dataclass(frozen=True)
class ReleaseAsset:
    kind: str
    name: str
    source: Path
    release: Path
    include: list[str]
    exclude: list[str]
    build_commands: list[list[str]]
    managed_output_commands: list[list[str]]
    managed_outputs: list[str]


@dataclass
class PreparedRelease:
    asset: ReleaseAsset
    runtime_files: list[Path]
    changed_files: list[str]
    stale_files: list[str]
    missing_outputs: list[str]
    output_fingerprints: dict[str, bytes | None]
    commands: list[list[str]]
    stage_root: Path
    candidate: Path
    target_tree_sha256: str
    backup_root: Path | None = None
    backup: Path | None = None
    promoted: bool = False
    command_results: list[dict[str, Any]] | None = None


def sync_release_assets(
    repo: Path,
    apply: bool = False,
    targets: list[str] | None = None,
    *,
    _apply_authorization: object | None = None,
) -> dict[str, Any]:
    repo = repo.resolve()
    requested_targets = list(targets or [])
    apply_authorized = False
    authorization_reason = "not_requested"
    if apply:
        apply_authorized, authorization_reason = _consume_release_apply_authorization(
            repo,
            requested_targets,
            _apply_authorization,
        )
    discovered = discover_assets(repo)
    selected, selection_errors = select_assets(repo, discovered, requested_targets)
    if apply and not apply_authorized:
        assets = [sync_asset(repo, asset, apply=False) for asset in selected]
        return {
            "status": "authorization_required",
            "assets": assets,
            "evalTargets": eval_targets_for_assets(selected),
            "requestedTargets": requested_targets,
            "selectionErrors": selection_errors,
            "authorization": release_apply_authorization_report(False, authorization_reason),
            "message": (
                "Release sync apply is available only through release_promotion_gate.py "
                "after fresh verification and archive/release authorization."
            ),
        }
    if apply and not requested_targets:
        return {
            "status": "target_required",
            "assets": [],
            "evalTargets": [],
            "requestedTargets": [],
            "selectionErrors": ["release sync apply requires at least one explicit target"],
            "authorization": release_apply_authorization_report(True, "consumed"),
        }
    if selection_errors:
        return {
            "status": "invalid_target",
            "assets": [],
            "evalTargets": [],
            "requestedTargets": requested_targets,
            "selectionErrors": selection_errors,
            "authorization": release_apply_authorization_report(
                apply_authorized,
                "consumed" if apply else "not_requested",
            ),
        }
    assets = (
        sync_assets_atomic(repo, selected)
        if apply
        else [sync_asset(repo, asset, apply=False) for asset in selected]
    )
    active = [
        asset
        for asset in assets
        if (
            asset["changedFiles"]
            or asset["missingOutputs"]
            or asset["changedOutputs"]
            or asset["staleOutputs"]
            or asset["staleFiles"]
            or asset["deletedFiles"]
        )
    ]
    if not assets:
        status = "not_applicable"
    elif apply and active:
        status = "synced"
    elif active:
        status = "pending"
    else:
        status = "current"
    return {
        "status": status,
        "assets": assets,
        "evalTargets": eval_targets_for_assets(selected),
        "requestedTargets": requested_targets,
        "selectionErrors": [],
        "authorization": release_apply_authorization_report(
            apply_authorized,
            "consumed" if apply else "not_requested",
        ),
    }


def _issue_release_apply_authorization(
    repo: Path,
    targets: list[str],
) -> _ReleaseApplyAuthorization:
    if not targets or any(not isinstance(target, str) or not target for target in targets):
        raise ValueError("release apply authorization requires explicit non-empty targets")
    repo = Path(repo).resolve()
    # Keep the minting boundary fail-closed even when this private helper is
    # imported directly.  The promotion entrypoint performs the same checks for
    # its user-facing report, but a token is never minted from that report
    # alone: current repository state and side-effect policy are re-evaluated
    # here at issuance time.
    from workflow_provider_registry import default_plugin_root, side_effect_decision
    from workflow_state import parse_state

    verification_passed = bool(
        parse_state(repo).get("gates", {}).get("verification_passed", False)
    )
    side_effect = side_effect_decision(
        default_plugin_root(),
        "archive_release",
        {"verified_and_explicit_user_request"},
    )
    if not verification_passed or not side_effect.get("authorized", False):
        raise PermissionError(
            "release apply authorization requires passed promotion verification"
        )
    now = time.monotonic()
    _prune_release_apply_authorizations(now)
    authorization = _ReleaseApplyAuthorization(_RELEASE_APPLY_AUTHORIZATION_SEAL)
    _ACTIVE_RELEASE_APPLY_AUTHORIZATIONS[authorization] = _ReleaseApplyAuthorizationRecord(
        repo=repo,
        targets=tuple(targets),
        expires_at=now + _RELEASE_APPLY_AUTHORIZATION_TTL_SECONDS,
    )
    return authorization


def _consume_release_apply_authorization(
    repo: Path,
    targets: list[str],
    authorization: object | None,
) -> tuple[bool, str]:
    if not isinstance(authorization, _ReleaseApplyAuthorization):
        return False, "missing"
    record = _ACTIVE_RELEASE_APPLY_AUTHORIZATIONS.pop(authorization, None)
    if record is None:
        return False, "unknown_or_consumed"
    now = time.monotonic()
    _prune_release_apply_authorizations(now)
    if now > record.expires_at:
        return False, "expired"
    if Path(repo).resolve() != record.repo:
        return False, "repo_mismatch"
    if tuple(targets) != record.targets:
        return False, "target_mismatch"
    return True, "consumed"


def _prune_release_apply_authorizations(now: float) -> None:
    expired = [
        authorization
        for authorization, record in _ACTIVE_RELEASE_APPLY_AUTHORIZATIONS.items()
        if now > record.expires_at
    ]
    for authorization in expired:
        _ACTIVE_RELEASE_APPLY_AUTHORIZATIONS.pop(authorization, None)


def release_apply_authorization_report(authorized: bool, reason: str) -> dict[str, Any]:
    return {
        "authorized": authorized,
        "reason": reason,
        "requiredIssuer": "release_promotion_gate",
        "oneTime": True,
        "repoAndTargetBound": True,
    }


def release_eval_target(repo: Path, target: Path) -> dict[str, Any]:
    repo = repo.resolve()
    resolved = target.expanduser().resolve()
    for asset in discover_assets(repo):
        if resolved == asset.source.resolve() or is_relative_to(resolved, asset.source.resolve()):
            return eval_target_record(asset, asset.release, True)
        if resolved == asset.release.resolve() or is_relative_to(resolved, asset.release.resolve()):
            return eval_target_record(asset, resolved, False)
    return {
        "target": str(resolved),
        "releasePreferred": False,
        "kind": "path",
        "name": resolved.name,
        "source": str(resolved),
        "release": None,
    }


def discover_assets(repo: Path) -> list[ReleaseAsset]:
    assets: list[ReleaseAsset] = []
    assets.extend(discover_plugins(repo))
    assets.extend(discover_skills(repo))
    return sorted(assets, key=lambda asset: (asset.kind, asset.name))


def select_assets(
    repo: Path,
    assets: list[ReleaseAsset],
    targets: list[str],
) -> tuple[list[ReleaseAsset], list[str]]:
    if not targets:
        return assets, []
    selected: list[ReleaseAsset] = []
    errors: list[str] = []
    for raw in targets:
        candidate = Path(raw).expanduser()
        resolved = (repo / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
        matches = [
            asset
            for asset in assets
            if raw == asset.name
            or resolved == asset.source.resolve()
            or resolved == asset.release.resolve()
        ]
        if len(matches) != 1:
            errors.append(f"target `{raw}` matched {len(matches)} release assets")
            continue
        if matches[0] not in selected:
            selected.append(matches[0])
    return selected, errors


def discover_plugins(repo: Path) -> list[ReleaseAsset]:
    roots = sorted((repo / "dev" / "plugins").glob("*"))
    assets = []
    for source in roots:
        if not (source / ".codex-plugin" / "plugin.json").is_file():
            continue
        release = repo / "plugins" / source.name
        if not release.exists() and not release.is_symlink():
            continue
        validate_tree(repo, source, "source")
        validate_tree(repo, release, "target")
        metadata = read_metadata(source)
        assets.append(
            ReleaseAsset(
                kind="plugin",
                name=source.name,
                source=source,
                release=release,
                include=PLUGIN_INCLUDE + list(metadata.get("include", [])),
                exclude=effective_default_excludes(metadata) + list(metadata.get("exclude", [])),
                build_commands=normalize_build_commands(metadata.get("buildCommands", [])),
                managed_output_commands=normalize_build_commands(
                    metadata.get("managedOutputCommands", [])
                ),
                managed_outputs=list(metadata.get("managedOutputs", [])),
            )
        )
    return assets


def discover_skills(repo: Path) -> list[ReleaseAsset]:
    roots = sorted((repo / "dev" / "skills").glob("*"))
    assets = []
    for source in roots:
        if not (source / "SKILL.md").is_file():
            continue
        release = repo / source.name
        if not release.exists() and not release.is_symlink():
            continue
        validate_tree(repo, source, "source")
        validate_tree(repo, release, "target")
        metadata = read_metadata(source)
        assets.append(
            ReleaseAsset(
                kind="skill",
                name=source.name,
                source=source,
                release=release,
                include=SKILL_INCLUDE + list(metadata.get("include", [])),
                exclude=effective_default_excludes(metadata) + list(metadata.get("exclude", [])),
                build_commands=normalize_build_commands(metadata.get("buildCommands", [])),
                managed_output_commands=normalize_build_commands(
                    metadata.get("managedOutputCommands", [])
                ),
                managed_outputs=list(metadata.get("managedOutputs", [])),
            )
        )
    return assets


def effective_default_excludes(metadata: dict[str, Any]) -> list[str]:
    overrides = metadata.get("defaultExcludeOverrides", [])
    if not isinstance(overrides, list) or any(not isinstance(item, str) for item in overrides):
        raise ValueError("release sync defaultExcludeOverrides must be a list of strings")
    unknown = sorted(set(overrides) - set(DEFAULT_EXCLUDE))
    if unknown:
        raise ValueError(
            "release sync defaultExcludeOverrides must name exact default patterns: "
            f"{unknown}"
        )
    return [pattern for pattern in DEFAULT_EXCLUDE if pattern not in set(overrides)]


def sync_asset(repo: Path, asset: ReleaseAsset, apply: bool) -> dict[str, Any]:
    if apply:
        raise PermissionError("release apply requires release_promotion_gate authorization")
    asset = resolve_asset_managed_outputs(repo, asset)
    runtime_files = list_runtime_files(asset)
    changed = changed_files(asset, runtime_files)
    missing_outputs = missing_managed_outputs(asset)
    stale_outputs = stale_managed_outputs(repo, asset)
    stale_files = stale_release_files(asset, runtime_files)
    commands = [list(command) for command in asset.build_commands]
    return {
        "kind": asset.kind,
        "name": asset.name,
        "source": str(asset.source),
        "release": str(asset.release),
        "changedFiles": changed,
        "changedOutputs": [],
        "missingOutputs": missing_outputs,
        "staleOutputs": stale_outputs,
        "staleFiles": stale_files,
        "deletedFiles": [],
        "buildCommands": commands,
        "managedOutputCommands": [list(command) for command in asset.managed_output_commands],
        "managedOutputs": list(asset.managed_outputs),
        "commandResults": [],
    }


def validate_asset_trees(repo: Path, asset: ReleaseAsset) -> None:
    validate_tree(repo, asset.source, "source")
    validate_tree(repo, asset.release, "target")
    for output in asset.managed_outputs:
        if not isinstance(output, str):
            raise ValueError(f"release sync managed output must be a string: {output!r}")
        validate_relative_file(output, "managed output")
    for command in (*asset.build_commands, *asset.managed_output_commands):
        if not command:
            raise ValueError("release sync command must not be empty")


def validate_tree(repo: Path, root: Path, label: str) -> None:
    repo = repo.resolve()
    lexical = root.absolute()
    if not is_relative_to(lexical, repo):
        raise ValueError(f"release sync {label} root escapes repository: {root}")
    current = lexical
    while current != repo:
        if current.is_symlink():
            raise ValueError(f"release sync {label} contains symlink: {current}")
        current = current.parent
    if not root.is_dir():
        raise ValueError(f"release sync {label} root is not a directory: {root}")
    resolved_root = root.resolve(strict=True)
    if not is_relative_to(resolved_root, repo):
        raise ValueError(f"release sync {label} root resolves outside repository: {root}")
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"release sync {label} contains symlink: {path}")
        resolved = path.resolve(strict=True)
        if not is_relative_to(resolved, resolved_root):
            raise ValueError(f"release sync {label} path resolves outside root: {path}")
        if not path.is_file() and not path.is_dir():
            raise ValueError(f"release sync {label} contains unsupported path: {path}")


def validate_relative_file(value: str, label: str) -> None:
    path = Path(value)
    if (
        not value
        or path == Path(".")
        or path.is_absolute()
        or ".." in path.parts
        or value.endswith("/")
    ):
        raise ValueError(f"release sync {label} must be a safe relative file: {value}")


def resolve_asset_managed_outputs(repo: Path, asset: ReleaseAsset) -> ReleaseAsset:
    validate_asset_trees(repo, asset)
    if asset.managed_output_commands:
        raise ValueError(
            "release sync managedOutputCommands are not allowed; "
            "declare the complete static managedOutputs list"
        )
    resolved = replace(asset, managed_outputs=sorted(set(asset.managed_outputs)))
    validate_asset_trees(repo, resolved)
    return resolved


def list_runtime_files(asset: ReleaseAsset) -> list[Path]:
    files = []
    for path in sorted(asset.source.rglob("*")):
        if not path.is_file():
            continue
        rel_path = path.relative_to(asset.source).as_posix()
        if matches_any(rel_path, asset.include) and not matches_any(rel_path, asset.exclude):
            files.append(path)
    return files


def expected_release_files(asset: ReleaseAsset, runtime_files: list[Path]) -> set[str]:
    runtime = {path.relative_to(asset.source).as_posix() for path in runtime_files}
    managed = set(asset.managed_outputs)
    overlap = runtime & managed
    if overlap:
        raise ValueError(f"managed outputs overlap copied runtime files: {sorted(overlap)}")
    return runtime | managed


def list_release_files(asset: ReleaseAsset) -> set[str]:
    return {
        path.relative_to(asset.release).as_posix()
        for path in asset.release.rglob("*")
        if path.is_file()
    }


def stale_release_files(asset: ReleaseAsset, runtime_files: list[Path]) -> list[str]:
    return sorted(list_release_files(asset) - expected_release_files(asset, runtime_files))


def changed_files(asset: ReleaseAsset, runtime_files: list[Path]) -> list[str]:
    changed = []
    for source in runtime_files:
        rel_path = source.relative_to(asset.source)
        release_file = asset.release / rel_path
        if not release_file.exists() or source.read_bytes() != release_file.read_bytes():
            changed.append(rel_path.as_posix())
    return changed


def copy_runtime_files(asset: ReleaseAsset, runtime_files: list[Path], destination: Path | None = None) -> None:
    root = destination or asset.release
    for source in runtime_files:
        rel_path = source.relative_to(asset.source)
        target = root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def prepare_release(repo: Path, asset: ReleaseAsset) -> PreparedRelease:
    asset = resolve_asset_managed_outputs(repo, asset)
    runtime_files = list_runtime_files(asset)
    target_tree_sha256 = release_tree_sha256(asset.release)
    stage_root = Path(
        tempfile.mkdtemp(
            prefix=f".{asset.name}.release-sync-stage-",
            dir=asset.release.parent,
        )
    )
    candidate = stage_root / "candidate"
    candidate.mkdir()
    try:
        copy_runtime_files(asset, runtime_files, candidate)
        for output in asset.managed_outputs:
            source = asset.release / output
            if not source.exists():
                continue
            if not source.is_file():
                raise ValueError(f"managed output is not a file: {source}")
            target = candidate / output
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        expected_release_files(asset, runtime_files)
        validate_tree(repo, candidate, "staging target")
        return PreparedRelease(
            asset=asset,
            runtime_files=runtime_files,
            changed_files=changed_files(asset, runtime_files),
            stale_files=stale_release_files(asset, runtime_files),
            missing_outputs=missing_managed_outputs(asset),
            output_fingerprints=managed_output_fingerprints(asset),
            commands=[list(command) for command in asset.build_commands],
            stage_root=stage_root,
            candidate=candidate,
            target_tree_sha256=target_tree_sha256,
        )
    except Exception:
        shutil.rmtree(stage_root, ignore_errors=True)
        raise


def promote_release(prepared: PreparedRelease) -> None:
    asset = prepared.asset
    current_target_sha256 = release_tree_sha256(asset.release)
    if current_target_sha256 != prepared.target_tree_sha256:
        raise RuntimeError(
            "release sync target changed after preparation; "
            f"refusing to overwrite concurrent changes for {asset.name}"
        )
    backup_root = Path(
        tempfile.mkdtemp(
            prefix=f".{asset.name}.release-sync-backup-",
            dir=asset.release.parent,
        )
    )
    backup = backup_root / "original"
    try:
        asset.release.replace(backup)
        prepared.candidate.replace(asset.release)
    except Exception:
        if backup.exists() and not asset.release.exists():
            backup.replace(asset.release)
        shutil.rmtree(backup_root, ignore_errors=True)
        raise
    prepared.backup_root = backup_root
    prepared.backup = backup
    prepared.promoted = True


def verify_promoted_release(repo: Path, prepared: PreparedRelease) -> None:
    asset = prepared.asset
    validate_asset_trees(repo, asset)
    expected = expected_release_files(asset, prepared.runtime_files)
    actual = list_release_files(asset)
    failures = []
    if actual != expected:
        failures.append(
            {
                "missing": sorted(expected - actual),
                "unexpected": sorted(actual - expected),
            }
        )
    drift = changed_files(asset, prepared.runtime_files)
    if drift:
        failures.append({"runtimeDrift": drift})
    missing_outputs = missing_managed_outputs(asset)
    if missing_outputs:
        failures.append({"missingOutputs": missing_outputs})
    stale_outputs = stale_managed_outputs(repo, asset)
    if stale_outputs:
        failures.append({"staleOutputs": stale_outputs})
    if failures:
        raise RuntimeError(f"release sync verification failed for {asset.name}: {failures}")


def rollback_releases(prepared_assets: list[PreparedRelease]) -> list[str]:
    errors = []
    for prepared in reversed(prepared_assets):
        asset = prepared.asset
        try:
            if prepared.promoted:
                failed = prepared.stage_root / "failed-release"
                if asset.release.exists() or asset.release.is_symlink():
                    asset.release.replace(failed)
                if prepared.backup is None or not prepared.backup.exists():
                    raise RuntimeError(f"release sync backup is missing for {asset.name}")
                prepared.backup.replace(asset.release)
                prepared.promoted = False
        except Exception as exc:
            errors.append(f"{asset.name}: {exc}")
        finally:
            shutil.rmtree(prepared.stage_root, ignore_errors=True)
            if prepared.backup_root is not None:
                shutil.rmtree(prepared.backup_root, ignore_errors=True)
    return errors


def commit_releases(prepared_assets: list[PreparedRelease]) -> None:
    for prepared in prepared_assets:
        shutil.rmtree(prepared.stage_root, ignore_errors=True)
        if prepared.backup_root is not None:
            shutil.rmtree(prepared.backup_root, ignore_errors=True)
        prepared.promoted = False


def release_report(repo: Path, prepared: PreparedRelease) -> dict[str, Any]:
    asset = prepared.asset
    return {
        "kind": asset.kind,
        "name": asset.name,
        "source": str(asset.source),
        "release": str(asset.release),
        "changedFiles": prepared.changed_files,
        "changedOutputs": changed_managed_outputs(asset, prepared.output_fingerprints),
        "missingOutputs": missing_managed_outputs(asset),
        "staleOutputs": stale_managed_outputs(repo, asset),
        "staleFiles": prepared.stale_files,
        "deletedFiles": prepared.stale_files,
        "buildCommands": prepared.commands,
        "managedOutputCommands": [list(command) for command in asset.managed_output_commands],
        "managedOutputs": list(asset.managed_outputs),
        "commandResults": prepared.command_results or [],
    }


def sync_assets_atomic(repo: Path, assets: list[ReleaseAsset]) -> list[dict[str, Any]]:
    prepared_assets: list[PreparedRelease] = []
    try:
        for asset in assets:
            prepared_assets.append(prepare_release(repo, asset))
        for prepared in prepared_assets:
            promote_release(prepared)
        for prepared in prepared_assets:
            prepared.command_results = run_build_commands(repo, prepared.commands)
        for prepared in prepared_assets:
            verify_promoted_release(repo, prepared)
        reports = [release_report(repo, prepared) for prepared in prepared_assets]
    except Exception as exc:
        rollback_errors = rollback_releases(prepared_assets)
        if rollback_errors:
            raise RuntimeError(
                f"release sync failed and rollback was incomplete: {rollback_errors}"
            ) from exc
        raise
    commit_releases(prepared_assets)
    return reports


def run_build_commands(repo: Path, commands: list[list[str]]) -> list[dict[str, Any]]:
    results = []
    for command in commands:
        resolved_command = resolve_build_command(command)
        completed = subprocess.run(resolved_command, cwd=repo, text=True, capture_output=True, check=False)
        result = {
            "command": resolved_command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
        results.append(result)
        if completed.returncode != 0:
            raise RuntimeError(f"release sync build command failed: {' '.join(resolved_command)}")
    return results


def resolve_build_command(command: list[str]) -> list[str]:
    if command and command[0] == "{python}":
        return [sys.executable, *command[1:]]
    return list(command)


def missing_managed_outputs(asset: ReleaseAsset) -> list[str]:
    return [output for output in asset.managed_outputs if not (asset.release / output).exists()]


def managed_output_fingerprints(asset: ReleaseAsset) -> dict[str, bytes | None]:
    fingerprints: dict[str, bytes | None] = {}
    for output in asset.managed_outputs:
        path = asset.release / output
        fingerprints[output] = path.read_bytes() if path.exists() else None
    return fingerprints


def changed_managed_outputs(asset: ReleaseAsset, before: dict[str, bytes | None]) -> list[str]:
    changed = []
    for output in asset.managed_outputs:
        path = asset.release / output
        previous = before.get(output)
        current = path.read_bytes() if path.exists() else None
        if current != previous:
            changed.append(output)
    return changed


def stale_managed_outputs(repo: Path, asset: ReleaseAsset) -> list[str]:
    stale: list[str] = []
    for output in asset.managed_outputs:
        if not output.endswith(".MANIFEST.json"):
            continue
        manifest_path = asset.release / output
        if not manifest_path.exists():
            continue
        try:
            manifest = json.loads(manifest_path.read_text())
        except (OSError, json.JSONDecodeError):
            stale.append(output)
            continue
        sources = manifest.get("sources")
        if not isinstance(sources, list) or not sources:
            stale.append(output)
            continue
        for source in sources:
            rel_path = source.get("path") if isinstance(source, dict) else None
            expected = source.get("sha256") if isinstance(source, dict) else None
            if not isinstance(rel_path, str) or not isinstance(expected, str):
                stale.append(output)
                break
            path = (repo / rel_path).resolve()
            if not is_relative_to(path, repo) or not path.is_file() or file_sha256(path) != expected:
                stale.append(output)
                break
        if output in stale or not output.endswith("devflow_runtime.MANIFEST.json"):
            continue
        recorded = {
            str(source["path"])
            for source in sources
            if isinstance(source, dict) and isinstance(source.get("path"), str)
        }
        source_parents = {(repo / path).parent.resolve() for path in recorded}
        actual = {
            path.relative_to(repo).as_posix()
            for parent in source_parents
            if is_relative_to(parent, repo) and parent.is_dir()
            for path in parent.glob("*.py")
            if path.is_file()
        }
        if actual != recorded:
            stale.append(output)
    return stale


def eval_targets(repo: Path) -> list[dict[str, Any]]:
    return eval_targets_for_assets(discover_assets(repo))


def eval_targets_for_assets(assets: list[ReleaseAsset]) -> list[dict[str, Any]]:
    return [eval_target_record(asset, asset.release, True) for asset in assets]


def eval_target_record(asset: ReleaseAsset, target: Path, release_preferred: bool) -> dict[str, Any]:
    return {
        "target": str(target.resolve()),
        "releasePreferred": release_preferred,
        "kind": asset.kind,
        "name": asset.name,
        "source": str(asset.source.resolve()),
        "release": str(asset.release.resolve()),
    }


def read_metadata(source: Path) -> dict[str, Any]:
    candidates = [
        source / ".codex-plugin" / "release-sync.json",
        source / "release-sync.json",
    ]
    for path in candidates:
        if path.is_file():
            return json.loads(path.read_text())
    return {}


def normalize_build_commands(commands: Any) -> list[list[str]]:
    normalized = []
    for command in commands:
        if isinstance(command, str):
            normalized.append(command.split())
        else:
            normalized.append([str(part) for part in command])
    return normalized


def matches_any(path: str, patterns: list[str]) -> bool:
    return any(matches(path, pattern) for pattern in patterns)


def matches(path: str, pattern: str) -> bool:
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return path == prefix or path.startswith(f"{prefix}/")
    return fnmatch.fnmatchcase(path, pattern)


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def release_tree_sha256(root: Path) -> str:
    """Return a stable digest of every file and directory in a release tree."""
    if not root.is_dir() or root.is_symlink():
        raise ValueError(f"release sync target root is not a safe directory: {root}")
    digest = hashlib.sha256(b"devflow-release-tree-v1\0")
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if path.is_symlink():
            raise ValueError(f"release sync target contains symlink: {path}")
        relative = path.relative_to(root).as_posix().encode()
        if path.is_dir():
            digest.update(b"D\0" + relative + b"\0")
            continue
        if not path.is_file():
            raise ValueError(f"release sync target contains unsupported path: {path}")
        digest.update(b"F\0" + relative + b"\0")
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()
