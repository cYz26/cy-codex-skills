#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any, Mapping


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EXPECTATION_KEYS = {
    "schemaVersion",
    "kind",
    "contractId",
    "plugin",
    "version",
    "tag",
    "channel",
    "assets",
    "assetSetDigest",
}
ASSET_KEYS = {"name", "size", "sha256"}


class AssetExpectationError(RuntimeError):
    pass


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            raise ValueError(f"duplicate JSON key: {key}")
        document[key] = value
    return document


def canonical_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relative_path(value: str) -> Path:
    path = Path(value)
    if (
        not value
        or path.is_absolute()
        or path.as_posix() != value
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise AssetExpectationError(f"unsafe repository-relative path: {value!r}")
    return path


def trusted_path(repo: Path, relative: Path, *, directory: bool) -> Path:
    current = repo
    for index, part in enumerate(relative.parts):
        current = current / part
        try:
            metadata = current.lstat()
        except FileNotFoundError as error:
            raise AssetExpectationError(f"required path is missing: {relative}") from error
        if stat.S_ISLNK(metadata.st_mode):
            raise AssetExpectationError(f"symlink path is forbidden: {relative}")
        final = index == len(relative.parts) - 1
        if not final and not stat.S_ISDIR(metadata.st_mode):
            raise AssetExpectationError(f"parent is not a directory: {relative}")
        if final:
            expected = stat.S_ISDIR if directory else stat.S_ISREG
            if not expected(metadata.st_mode):
                kind = "directory" if directory else "regular file"
                raise AssetExpectationError(f"path is not a {kind}: {relative}")
    return current


def read_strict_object(path: Path) -> dict[str, Any]:
    try:
        before = member_identity(path)
        if not stat.S_ISREG(before[2]):
            raise AssetExpectationError(f"JSON document is not a regular file: {path}")
        payload = path.read_bytes()
        after = member_identity(path)
        if before != after or not stat.S_ISREG(after[2]):
            raise AssetExpectationError(f"JSON document identity drifted: {path}")
        value = json.loads(
            payload.decode("utf-8"), object_pairs_hook=reject_duplicate_keys
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise AssetExpectationError(f"invalid JSON document: {path}") from error
    if not isinstance(value, dict):
        raise AssetExpectationError(f"JSON document is not an object: {path}")
    return value


def non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def safe_asset_name(value: object) -> bool:
    return bool(
        non_empty_string(value)
        and isinstance(value, str)
        and Path(value).name == value
        and value not in {".", ".."}
    )


def contract_identity(
    contract: Mapping[str, Any], expectation_relative: str
) -> dict[str, object]:
    contract_id = contract.get("contractId")
    write_set = contract.get("writeSet")
    plugin = contract.get("plugin")
    publication = contract.get("publication")
    if (
        not non_empty_string(contract_id)
        or not isinstance(write_set, list)
        or expectation_relative not in write_set
        or not isinstance(plugin, Mapping)
        or not isinstance(publication, Mapping)
    ):
        raise AssetExpectationError("expectation is not bound by the standing contract")
    assets = publication.get("assets")
    if (
        not non_empty_string(plugin.get("id"))
        or not non_empty_string(plugin.get("version"))
        or not non_empty_string(publication.get("tag"))
        or not non_empty_string(publication.get("channel"))
        or publication.get("assetExpectation") != expectation_relative
        or not isinstance(assets, list)
        or not assets
        or any(not safe_asset_name(name) for name in assets)
        or len(assets) != len(set(assets))
    ):
        raise AssetExpectationError("standing publication identity is invalid")
    return {
        "contractId": contract_id,
        "plugin": plugin["id"],
        "version": plugin["version"],
        "tag": publication["tag"],
        "channel": publication["channel"],
        "assetNames": list(assets),
    }


def validate_expectation(
    expectation: Mapping[str, Any], identity: Mapping[str, object]
) -> list[dict[str, object]]:
    if set(expectation) != EXPECTATION_KEYS:
        raise AssetExpectationError("expectation keys are not exact")
    if (
        expectation.get("schemaVersion") != "1.0"
        or expectation.get("kind") != "devflow-release-asset-expectation"
        or any(
            expectation.get(key) != identity.get(key)
            for key in ("contractId", "plugin", "version", "tag", "channel")
        )
    ):
        raise AssetExpectationError("expectation identity does not match the contract")
    assets = expectation.get("assets")
    if not isinstance(assets, list) or not assets:
        raise AssetExpectationError("expectation assets are missing")
    records: list[dict[str, object]] = []
    names: list[str] = []
    for value in assets:
        if not isinstance(value, dict) or set(value) != ASSET_KEYS:
            raise AssetExpectationError("expectation asset record is invalid")
        name = value.get("name")
        size = value.get("size")
        digest = value.get("sha256")
        if (
            not safe_asset_name(name)
            or type(size) is not int
            or size < 0
            or not isinstance(digest, str)
            or not SHA256_RE.fullmatch(digest)
        ):
            raise AssetExpectationError("expectation asset value is invalid")
        assert isinstance(name, str)
        names.append(name)
        records.append({"name": name, "size": size, "sha256": digest})
    if names != identity.get("assetNames") or len(names) != len(set(names)):
        raise AssetExpectationError("expectation asset set differs from the contract")
    if expectation.get("assetSetDigest") != canonical_digest(records):
        raise AssetExpectationError("expectation asset-set digest is invalid")
    return records


def member_identity(path: Path) -> tuple[int, int, int, int, int]:
    metadata = path.lstat()
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_size,
        metadata.st_mtime_ns,
    )


def verify_assets(asset_dir: Path, expected: list[dict[str, object]]) -> None:
    directory_before = member_identity(asset_dir)
    if not stat.S_ISDIR(directory_before[2]):
        raise AssetExpectationError("release asset root is not a real directory")
    observed_names = sorted(entry.name for entry in os.scandir(asset_dir))
    expected_names = sorted(str(record["name"]) for record in expected)
    if observed_names != expected_names:
        raise AssetExpectationError("release asset member set differs from expectation")
    by_name = {str(record["name"]): record for record in expected}
    for name in expected_names:
        path = asset_dir / name
        before = member_identity(path)
        if not stat.S_ISREG(before[2]):
            raise AssetExpectationError(f"release asset is not a regular file: {name}")
        digest = file_sha256(path)
        after = member_identity(path)
        if before != after or not stat.S_ISREG(after[2]):
            raise AssetExpectationError(f"release asset identity drifted: {name}")
        record = by_name[name]
        if after[3] != record["size"] or digest != record["sha256"]:
            raise AssetExpectationError(f"release asset differs from expectation: {name}")
    directory_after = member_identity(asset_dir)
    final_names = sorted(entry.name for entry in os.scandir(asset_dir))
    if directory_before != directory_after or final_names != expected_names:
        raise AssetExpectationError("release asset directory identity drifted")


def verify(
    repo: Path,
    *,
    contract_relative: str,
    expectation_relative: str,
    asset_dir_relative: str,
) -> dict[str, object]:
    repo = repo.resolve()
    if not repo.is_dir():
        raise AssetExpectationError("repository root is unavailable")
    contract_path = trusted_path(
        repo, safe_relative_path(contract_relative), directory=False
    )
    expectation_path = trusted_path(
        repo, safe_relative_path(expectation_relative), directory=False
    )
    asset_dir = trusted_path(repo, safe_relative_path(asset_dir_relative), directory=True)
    contract = read_strict_object(contract_path)
    expectation = read_strict_object(expectation_path)
    identity = contract_identity(contract, expectation_relative)
    records = validate_expectation(expectation, identity)
    verify_assets(asset_dir, records)
    return {
        "ok": True,
        "status": "verified",
        "contractId": identity["contractId"],
        "plugin": identity["plugin"],
        "version": identity["version"],
        "tag": identity["tag"],
        "channel": identity["channel"],
        "assets": records,
        "assetSetDigest": expectation["assetSetDigest"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify exact frozen DevFlow release assets before publication."
    )
    parser.add_argument("--repo", default=".")
    parser.add_argument("--contract", required=True)
    parser.add_argument("--expectation", required=True)
    parser.add_argument("--asset-dir", required=True)
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args()
    try:
        report = verify(
            Path(arguments.repo),
            contract_relative=arguments.contract,
            expectation_relative=arguments.expectation,
            asset_dir_relative=arguments.asset_dir,
        )
    except (AssetExpectationError, OSError) as error:
        report = {"ok": False, "status": "rejected", "reason": str(error)}
        if arguments.json:
            print(json.dumps(report, sort_keys=True))
        else:
            print(report["reason"], file=sys.stderr)
        return 2
    if arguments.json:
        print(json.dumps(report, sort_keys=True))
    else:
        print("DevFlow release assets verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
