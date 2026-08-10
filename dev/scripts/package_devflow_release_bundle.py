#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, NamedTuple


FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
POLICY_PATH = Path("dev/plugins/dev-flow/docs/dev-flow-release-policy.json")
RELEASE_ROOT = Path("plugins/dev-flow")
RUNTIME_ASSETS = (
    "devflow_runtime.pyz",
    "devflow_runtime.MANIFEST.json",
    "devflow_runtime.sha256",
)
EXCLUDED_NAMES = {".DS_Store"}

class MemberIdentity(NamedTuple):
    device: int
    inode: int
    mode: int
    link_count: int
    size: int
    mtime_ns: int
    ctime_ns: int
    sha256: str


class BundleError(RuntimeError):
    pass


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def load_policy(repo: Path) -> dict[str, Any]:
    path = repo / POLICY_PATH
    try:
        policy = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise BundleError("release policy is missing or invalid") from error
    required = (
        "plugin",
        "version",
        "tag",
        "channel",
        "repository",
        "assets",
        "expectedManifest",
        "releaseNotes",
    )
    if any(policy.get(key) in (None, "", []) for key in required):
        raise BundleError("release policy is incomplete")
    expected_assets = [
        f"dev-flow-{policy['version']}.zip",
        f"dev-flow-{policy['version']}.release-manifest.json",
        f"dev-flow-{policy['version']}.sha256",
        *RUNTIME_ASSETS,
        f"dev-flow-v{policy['version']}.md",
    ]
    if policy["plugin"] != "dev-flow" or policy["tag"] != f"dev-flow-v{policy['version']}":
        raise BundleError("release policy identity is inconsistent")
    if policy["assets"] != expected_assets:
        raise BundleError("release policy asset list is not exact")
    return policy


def release_files(repo: Path, expected_manifest_name: str) -> list[Path]:
    root = (repo / RELEASE_ROOT).resolve()
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise BundleError(f"release plugin contains a symlink: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if (
            path.name == expected_manifest_name
            or path.name in EXCLUDED_NAMES
            or "__pycache__" in relative.parts
            or path.suffix in {".pyc", ".pyo"}
        ):
            continue
        files.append(path)
    if not files:
        raise BundleError("release plugin is empty")
    return files


def file_mode(path: Path) -> int:
    return 0o755 if path.read_bytes().startswith(b"#!") else 0o644


def tree_records(repo: Path, files: list[Path]) -> list[dict[str, object]]:
    root = (repo / RELEASE_ROOT).resolve()
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "mode": f"{file_mode(path):04o}",
            "sha256": sha256_file(path),
        }
        for path in files
    ]


def expected_manifest_document(repo: Path, policy: dict[str, Any]) -> dict[str, Any]:
    expected_path = (repo / str(policy["expectedManifest"])).resolve()
    files = release_files(repo, expected_path.name)
    records = tree_records(repo, files)
    return {
        "schemaVersion": "1.0",
        "plugin": policy["plugin"],
        "version": policy["version"],
        "tag": policy["tag"],
        "channel": policy["channel"],
        "repository": policy["repository"],
        "treeSha256": sha256_bytes(
            json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
        ),
        "assetNames": list(policy["assets"]),
        "treeEntryCount": len(records),
        "treeDigestExclusions": [
            Path(str(policy["expectedManifest"])).name,
        ],
    }


def verify_expected_manifest(repo: Path, policy: dict[str, Any]) -> tuple[Path, bytes]:
    path = (repo / str(policy["expectedManifest"])).resolve()
    try:
        path.relative_to(repo)
    except ValueError as error:
        raise BundleError("expected manifest path escapes repository") from error
    expected = canonical_bytes(expected_manifest_document(repo, policy))
    if not path.is_file() or path.read_bytes() != expected:
        raise BundleError(
            "checked-in expected release manifest is missing or stale; "
            "regenerate it before candidate freeze"
        )
    return path, expected


def write_plugin_zip(repo: Path, target: Path, expected_manifest: Path) -> None:
    root = (repo / RELEASE_ROOT).resolve()
    release_manifest = root / "docs" / expected_manifest.name
    if not release_manifest.is_file() or release_manifest.read_bytes() != expected_manifest.read_bytes():
        raise BundleError("source and release expected manifests do not match")
    files = release_files(repo, expected_manifest.name)
    if release_manifest not in files:
        files.append(release_manifest)
        files.sort()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as archive:
        for path in files:
            relative = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(f"dev-flow/{relative}", date_time=FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.create_version = 20
            info.extract_version = 20
            info.flag_bits = 0
            info.volume = 0
            info.reserved = 0
            info.internal_attr = 0
            info.external_attr = (stat.S_IFREG | file_mode(path)) << 16
            info.extra = b""
            info.comment = b""
            archive.writestr(info, path.read_bytes())


def directory_identity(path: Path) -> tuple[int, int]:
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise BundleError(f"directory identity is unavailable: {path}") from error
    if not stat.S_ISDIR(metadata.st_mode):
        raise BundleError(f"path is not a real directory: {path}")
    return metadata.st_dev, metadata.st_ino


def regular_member_identity(path: Path) -> MemberIdentity:
    try:
        before = path.lstat()
    except FileNotFoundError as error:
        raise BundleError(f"member identity is unavailable: {path}") from error
    if not stat.S_ISREG(before.st_mode):
        raise BundleError(f"member is not a regular file: {path}")
    digest = sha256_file(path)
    try:
        after = path.lstat()
    except FileNotFoundError as error:
        raise BundleError(f"member identity changed while recording: {path}") from error
    before_fields = (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_nlink,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    after_fields = (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_nlink,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )
    if before_fields != after_fields or not stat.S_ISREG(after.st_mode):
        raise BundleError(f"member identity changed while recording: {path}")
    return MemberIdentity(*after_fields, digest)


def member_link_transition_matches(
    before: MemberIdentity,
    after: MemberIdentity,
    *,
    link_delta: int,
) -> bool:
    return (
        before.device == after.device
        and before.inode == after.inode
        and before.mode == after.mode
        and after.link_count == before.link_count + link_delta
        and before.size == after.size
        and before.mtime_ns == after.mtime_ns
        and before.sha256 == after.sha256
    )


def inspect_caller_output(path: Path) -> tuple[int, int] | None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISDIR(metadata.st_mode) or any(path.iterdir()):
        raise BundleError("output directory must be absent or empty")
    return metadata.st_dev, metadata.st_ino


def require_empty_directory_identity(path: Path, expected: tuple[int, int]) -> None:
    if directory_identity(path) != expected or any(path.iterdir()):
        raise BundleError("output directory identity or contents changed during build")


def remove_invocation_owned_directory(
    path: Path,
    expected: tuple[int, int],
    owned_members: dict[str, MemberIdentity] | None = None,
    *,
    remove_directory: bool = True,
) -> None:
    try:
        current = directory_identity(path)
    except BundleError:
        if not os.path.lexists(path):
            return
        raise
    if current != expected:
        raise BundleError("invocation-owned directory identity changed; refusing cleanup")

    registered = owned_members or {}
    for name, identity in registered.items():
        if (
            not isinstance(name, str)
            or not name
            or Path(name).name != name
            or name in {".", ".."}
            or not isinstance(identity, tuple)
            or len(identity) != 8
        ):
            raise BundleError("invocation-owned member registry is invalid")

    present_names = {member.name for member in path.iterdir()}
    unknown_names = present_names - set(registered)
    drifted_names: set[str] = set()
    removable_names: list[str] = []
    for name in sorted(present_names & set(registered)):
        member = path / name
        try:
            current_identity = regular_member_identity(member)
        except BundleError:
            drifted_names.add(name)
            continue
        if current_identity != registered[name]:
            drifted_names.add(name)
            continue
        removable_names.append(name)

    for name in removable_names:
        member = path / name
        try:
            current_identity = regular_member_identity(member)
        except BundleError:
            drifted_names.add(name)
            continue
        if current_identity != registered[name]:
            drifted_names.add(name)
            continue
        try:
            member.unlink()
        except OSError as error:
            raise BundleError(
                f"invocation-owned member changed before exact cleanup completed: {name}"
            ) from error

    remaining_names = {member.name for member in path.iterdir()}
    if unknown_names or drifted_names or remaining_names:
        raise BundleError(
            "invocation-owned cleanup preserved unknown or identity-drifted members"
        )
    if not remove_directory:
        return
    if directory_identity(path) != expected or any(path.iterdir()):
        raise BundleError(
            "invocation-owned directory identity or contents changed before removal"
        )
    try:
        path.rmdir()
    except OSError as error:
        raise BundleError(
            "invocation-owned directory changed before exact cleanup completed"
        ) from error


def promote_staged_assets(
    staging: Path,
    output: Path,
    asset_names: list[str],
    *,
    staging_members: dict[str, MemberIdentity],
    output_members: dict[str, MemberIdentity],
) -> None:
    staged_names = sorted(path.name for path in staging.iterdir())
    if staged_names != sorted(asset_names):
        raise BundleError("staged release asset set is not exact")
    if set(staging_members) != set(asset_names) or output_members:
        raise BundleError("release asset ownership registry is not exact")
    for name in asset_names:
        source = staging / name
        expected_identity = staging_members[name]
        if regular_member_identity(source) != expected_identity:
            raise BundleError(f"staged release asset identity changed: {name}")
        target = output / name
        try:
            os.link(source, target, follow_symlinks=False)
        except FileExistsError as error:
            raise BundleError(f"release asset target already exists: {name}") from error
        output_members[name] = expected_identity
        linked_source_identity = regular_member_identity(source)
        linked_target_identity = regular_member_identity(target)
        if (
            linked_source_identity != linked_target_identity
            or not member_link_transition_matches(
                expected_identity,
                linked_source_identity,
                link_delta=1,
            )
        ):
            raise BundleError(f"staged release asset identity changed during promotion: {name}")
        output_members[name] = linked_target_identity
        source.unlink()
        promoted_identity = regular_member_identity(target)
        if not member_link_transition_matches(
            linked_target_identity,
            promoted_identity,
            link_delta=-1,
        ):
            raise BundleError(f"release asset identity changed during promotion: {name}")
        output_members[name] = promoted_identity


def build_bundle(
    repo: Path,
    output: Path,
    *,
    invocation_owned_members: dict[str, MemberIdentity] | None = None,
) -> dict[str, Any]:
    def register_created_member(path: Path) -> None:
        if invocation_owned_members is None:
            return
        if path.name in invocation_owned_members:
            raise BundleError(f"release asset was registered twice: {path.name}")
        invocation_owned_members[path.name] = regular_member_identity(path)

    repo = repo.expanduser().resolve()
    policy = load_policy(repo)
    release_root = repo / RELEASE_ROOT
    manifest = json.loads((release_root / ".codex-plugin" / "plugin.json").read_text())
    if manifest.get("name") != policy["plugin"] or manifest.get("version") != policy["version"]:
        raise BundleError("release plugin metadata does not match release policy")
    expected_manifest, expected_bytes = verify_expected_manifest(repo, policy)
    notes = (repo / str(policy["releaseNotes"])).resolve()
    if not notes.is_file():
        raise BundleError("release notes are missing")
    for name in RUNTIME_ASSETS:
        if not (release_root / "scripts" / name).is_file():
            raise BundleError(f"runtime asset is missing: {name}")

    if output.exists():
        if not output.is_dir() or any(output.iterdir()):
            raise BundleError("output directory must be absent or empty")
    else:
        output.mkdir(parents=True)
    version = str(policy["version"])
    zip_name = f"dev-flow-{version}.zip"
    manifest_name = f"dev-flow-{version}.release-manifest.json"
    checksum_name = f"dev-flow-{version}.sha256"
    notes_name = f"dev-flow-v{version}.md"
    write_plugin_zip(repo, output / zip_name, expected_manifest)
    register_created_member(output / zip_name)
    manifest_output = output / manifest_name
    manifest_output.write_bytes(expected_bytes)
    register_created_member(manifest_output)
    for name in RUNTIME_ASSETS:
        runtime_output = output / name
        shutil.copyfile(release_root / "scripts" / name, runtime_output)
        register_created_member(runtime_output)
    notes_output = output / notes_name
    shutil.copyfile(notes, notes_output)
    register_created_member(notes_output)

    hashed_names = [name for name in policy["assets"] if name != checksum_name]
    checksum_text = "".join(
        f"{sha256_file(output / name)}  {name}\n" for name in hashed_names
    )
    checksum_output = output / checksum_name
    checksum_output.write_text(checksum_text)
    register_created_member(checksum_output)
    assets = [
        {
            "name": name,
            "bytes": (output / name).stat().st_size,
            "sha256": sha256_file(output / name),
        }
        for name in policy["assets"]
    ]
    return {
        "status": "built",
        "plugin": policy["plugin"],
        "version": version,
        "tag": policy["tag"],
        "assets": assets,
        "expectedManifest": str(expected_manifest.relative_to(repo)),
    }


def build_bundle_for_caller_output(repo: Path, output: Path) -> dict[str, Any]:
    output = output.expanduser().absolute()
    caller_identity = inspect_caller_output(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{output.name or 'devflow-release'}.tmp-",
            dir=output.parent,
        )
    )
    staging_identity = directory_identity(staging)
    staging_members: dict[str, MemberIdentity] = {}
    output_members: dict[str, MemberIdentity] = {}
    invocation_output_identity: tuple[int, int] | None = None
    try:
        report = build_bundle(
            repo,
            staging,
            invocation_owned_members=staging_members,
        )
        asset_names = [str(item["name"]) for item in report["assets"]]
        if caller_identity is None:
            try:
                output.mkdir()
            except FileExistsError as error:
                raise BundleError("output path appeared during build") from error
            invocation_output_identity = directory_identity(output)
        else:
            require_empty_directory_identity(output, caller_identity)
        try:
            promote_staged_assets(
                staging,
                output,
                asset_names,
                staging_members=staging_members,
                output_members=output_members,
            )
        except Exception:
            output_identity = invocation_output_identity or caller_identity
            if output_identity is not None:
                remove_invocation_owned_directory(
                    output,
                    output_identity,
                    output_members,
                    remove_directory=invocation_output_identity is not None,
                )
            raise
        return report
    finally:
        remove_invocation_owned_directory(
            staging,
            staging_identity,
            staging_members,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the exact deterministic DevFlow release bundle.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    output = Path(args.output_dir)
    try:
        report = build_bundle_for_caller_output(Path(args.repo), output)
    except (BundleError, OSError, json.JSONDecodeError) as error:
        if args.json:
            print(json.dumps({"status": "failed", "error": str(error)}, sort_keys=True))
        else:
            print(str(error), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
