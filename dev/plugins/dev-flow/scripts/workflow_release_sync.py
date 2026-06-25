from __future__ import annotations

import fnmatch
import json
import shutil
import subprocess
from dataclasses import dataclass
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


@dataclass(frozen=True)
class ReleaseAsset:
    kind: str
    name: str
    source: Path
    release: Path
    include: list[str]
    exclude: list[str]
    build_commands: list[list[str]]
    managed_outputs: list[str]


def sync_release_assets(repo: Path, apply: bool = False) -> dict[str, Any]:
    repo = repo.resolve()
    assets = [sync_asset(repo, asset, apply=apply) for asset in discover_assets(repo)]
    active = [
        asset
        for asset in assets
        if asset["changedFiles"] or asset["missingOutputs"] or asset["changedOutputs"]
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
        "evalTargets": eval_targets(repo),
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


def discover_plugins(repo: Path) -> list[ReleaseAsset]:
    roots = sorted((repo / "dev" / "plugins").glob("*"))
    assets = []
    for source in roots:
        if not (source / ".codex-plugin" / "plugin.json").is_file():
            continue
        release = repo / "plugins" / source.name
        if not release.exists():
            continue
        metadata = read_metadata(source)
        assets.append(
            ReleaseAsset(
                kind="plugin",
                name=source.name,
                source=source,
                release=release,
                include=PLUGIN_INCLUDE + list(metadata.get("include", [])),
                exclude=DEFAULT_EXCLUDE + list(metadata.get("exclude", [])),
                build_commands=normalize_build_commands(metadata.get("buildCommands", [])),
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
        if not release.exists():
            continue
        metadata = read_metadata(source)
        assets.append(
            ReleaseAsset(
                kind="skill",
                name=source.name,
                source=source,
                release=release,
                include=SKILL_INCLUDE + list(metadata.get("include", [])),
                exclude=DEFAULT_EXCLUDE + list(metadata.get("exclude", [])),
                build_commands=normalize_build_commands(metadata.get("buildCommands", [])),
                managed_outputs=list(metadata.get("managedOutputs", [])),
            )
        )
    return assets


def sync_asset(repo: Path, asset: ReleaseAsset, apply: bool) -> dict[str, Any]:
    runtime_files = list_runtime_files(asset)
    changed = changed_files(asset, runtime_files)
    missing_outputs = missing_managed_outputs(asset)
    output_fingerprints = managed_output_fingerprints(asset) if apply else {}
    commands = [list(command) for command in asset.build_commands]
    if apply:
        copy_runtime_files(asset, runtime_files)
        command_results = run_build_commands(repo, commands)
        changed_outputs = changed_managed_outputs(asset, output_fingerprints)
        missing_outputs = missing_managed_outputs(asset)
    else:
        command_results = []
        changed_outputs = []
    return {
        "kind": asset.kind,
        "name": asset.name,
        "source": str(asset.source),
        "release": str(asset.release),
        "changedFiles": changed,
        "changedOutputs": changed_outputs,
        "missingOutputs": missing_outputs,
        "buildCommands": commands,
        "commandResults": command_results,
    }


def list_runtime_files(asset: ReleaseAsset) -> list[Path]:
    files = []
    for path in sorted(asset.source.rglob("*")):
        if not path.is_file():
            continue
        rel_path = path.relative_to(asset.source).as_posix()
        if matches_any(rel_path, asset.include) and not matches_any(rel_path, asset.exclude):
            files.append(path)
    return files


def changed_files(asset: ReleaseAsset, runtime_files: list[Path]) -> list[str]:
    changed = []
    for source in runtime_files:
        rel_path = source.relative_to(asset.source)
        release_file = asset.release / rel_path
        if not release_file.exists() or source.read_bytes() != release_file.read_bytes():
            changed.append(rel_path.as_posix())
    return changed


def copy_runtime_files(asset: ReleaseAsset, runtime_files: list[Path]) -> None:
    for source in runtime_files:
        rel_path = source.relative_to(asset.source)
        target = asset.release / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def run_build_commands(repo: Path, commands: list[list[str]]) -> list[dict[str, Any]]:
    results = []
    for command in commands:
        completed = subprocess.run(command, cwd=repo, text=True, capture_output=True, check=False)
        result = {
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
        results.append(result)
        if completed.returncode != 0:
            raise RuntimeError(f"release sync build command failed: {' '.join(command)}")
    return results


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


def eval_targets(repo: Path) -> list[dict[str, Any]]:
    return [eval_target_record(asset, asset.release, True) for asset in discover_assets(repo)]


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
