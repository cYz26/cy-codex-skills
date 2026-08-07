#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

from workflow_release_verification import verify_project_refresh_release_parity


MANIFEST_NAME = "devflow_runtime.MANIFEST.json"
SHA256_NAME = "devflow_runtime.sha256"
SOURCE_COMMIT_NAME = "devflow_runtime.SOURCE_COMMIT"
DEFAULT_ARCHIVE = "scripts/devflow_runtime.pyz"


def verify_release_runtime(plugin_root: Path, repo_root: Path | None = None) -> dict[str, Any]:
    plugin_root = plugin_root.expanduser().resolve()
    repo_root = (repo_root or infer_repo_root(plugin_root)).expanduser().resolve()
    scripts_root = plugin_root / "scripts"
    manifest_path = scripts_root / MANIFEST_NAME
    checks: list[dict[str, Any]] = []

    manifest = read_manifest(manifest_path, checks)
    archive_path = plugin_root / manifest.get("archive", {}).get("path", DEFAULT_ARCHIVE)
    expected_archive_sha = str(manifest.get("archive", {}).get("sha256", ""))

    archive_sha = check_archive(archive_path, expected_archive_sha, checks)
    check_archive_members(archive_path, manifest, checks)
    check_sha_file(scripts_root / SHA256_NAME, archive_sha, checks)
    check_source_commit(scripts_root / SOURCE_COMMIT_NAME, manifest, checks)
    check_sources(repo_root, manifest, checks)
    check_methodology_contract(plugin_root, checks)
    source_root = repo_root / "dev" / "plugins" / "dev-flow"
    refresh_parity: dict[str, Any] | None = None
    if (source_root / ".codex-plugin" / "project-migration.json").is_file():
        refresh_parity = verify_project_refresh_release_parity(source_root, plugin_root)
        add_check(
            checks,
            "project refresh release parity",
            bool(refresh_parity["ok"]),
            json.dumps(refresh_parity["errors"], sort_keys=True),
        )
    else:
        add_check(
            checks,
            "project refresh release parity",
            True,
            "not applicable to this synthetic runtime fixture",
        )

    ok = all(check["ok"] for check in checks)
    return {
        "ok": ok,
        "status": "verified" if ok else "drift",
        "pluginRoot": str(plugin_root),
        "repoRoot": str(repo_root),
        "manifest": str(manifest_path),
        "archive": str(archive_path),
        "archiveSha256": archive_sha,
        "sourceCommit": manifest.get("sourceCommit"),
        "checks": checks,
        "projectRefreshParity": refresh_parity,
        "nextAction": (
            "release runtime verified"
            if ok
            else "rebuild release runtime with python3 dev/scripts/package_devflow_release_runtime.py"
        ),
    }


def read_manifest(path: Path, checks: list[dict[str, Any]]) -> dict[str, Any]:
    if not path.exists():
        add_check(checks, "runtime manifest exists", False, str(path))
        return {"archive": {"path": DEFAULT_ARCHIVE}, "sources": []}
    try:
        manifest = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        add_check(checks, "runtime manifest parses", False, str(exc))
        return {"archive": {"path": DEFAULT_ARCHIVE}, "sources": []}
    add_check(checks, "runtime manifest exists", True, str(path))
    add_check(checks, "runtime manifest parses", True, str(path))
    return manifest


def check_archive(path: Path, expected_sha: str, checks: list[dict[str, Any]]) -> str | None:
    if not path.exists():
        add_check(checks, "runtime archive exists", False, str(path))
        return None
    actual_sha = file_sha256(path)
    add_check(checks, "runtime archive exists", True, str(path))
    add_check(
        checks,
        "runtime archive sha256 matches manifest",
        bool(expected_sha) and actual_sha == expected_sha,
        f"expected {expected_sha or 'missing'}, actual {actual_sha}",
    )
    return actual_sha


def check_archive_members(
    path: Path,
    manifest: dict[str, Any],
    checks: list[dict[str, Any]],
) -> None:
    if not path.exists():
        add_check(checks, "runtime archive members match manifest sources", False, "archive missing")
        return
    sources = manifest.get("sources", [])
    expected = {
        Path(str(source.get("path", ""))).name
        for source in sources
        if isinstance(source, dict) and str(source.get("path", "")).endswith(".py")
    }
    try:
        with zipfile.ZipFile(path) as archive:
            actual = {name for name in archive.namelist() if name.endswith(".py")}
    except (OSError, zipfile.BadZipFile) as error:
        add_check(checks, "runtime archive members match manifest sources", False, str(error))
        return
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    add_check(
        checks,
        "runtime archive members match manifest sources",
        not missing and not unexpected and bool(expected),
        f"missing={missing}, unexpected={unexpected}",
    )


def check_sha_file(path: Path, archive_sha: str | None, checks: list[dict[str, Any]]) -> None:
    if not path.exists():
        add_check(checks, "runtime sha256 file exists", False, str(path))
        return
    text = path.read_text().strip()
    recorded_sha = text.split()[0] if text else ""
    add_check(checks, "runtime sha256 file exists", True, str(path))
    add_check(
        checks,
        "runtime sha256 file matches archive",
        bool(archive_sha) and recorded_sha == archive_sha,
        f"recorded {recorded_sha or 'missing'}, actual {archive_sha or 'missing'}",
    )


def check_source_commit(path: Path, manifest: dict[str, Any], checks: list[dict[str, Any]]) -> None:
    expected = str(manifest.get("sourceCommit") or "")
    if not path.exists():
        add_check(checks, "runtime source commit file exists", False, str(path))
        return
    actual = path.read_text().strip()
    add_check(checks, "runtime source commit file exists", True, str(path))
    add_check(
        checks,
        "runtime source commit matches manifest",
        bool(expected) and actual == expected,
        f"expected {expected or 'missing'}, actual {actual or 'missing'}",
    )


def check_sources(repo_root: Path, manifest: dict[str, Any], checks: list[dict[str, Any]]) -> None:
    sources = manifest.get("sources", [])
    add_check(checks, "runtime manifest has sources", bool(sources), f"{len(sources)} sources")
    for source in sources:
        rel_path = str(source.get("path", ""))
        expected_sha = str(source.get("sha256", ""))
        path = (repo_root / rel_path).resolve()
        if not rel_path or not is_relative_to(path, repo_root):
            add_check(checks, f"runtime source path valid: {rel_path or '<empty>'}", False, str(path))
            continue
        if not path.exists():
            add_check(checks, f"runtime source exists: {rel_path}", False, str(path))
            continue
        actual_sha = file_sha256(path)
        add_check(checks, f"runtime source exists: {rel_path}", True, str(path))
        add_check(
            checks,
            f"runtime source sha256 matches: {rel_path}",
            bool(expected_sha) and actual_sha == expected_sha,
            f"expected {expected_sha or 'missing'}, actual {actual_sha}",
        )


def check_methodology_contract(plugin_root: Path, checks: list[dict[str, Any]]) -> None:
    path = plugin_root / "docs" / "dependency-provenance.json"
    if not path.exists():
        add_check(checks, "methodology contract exists", False, str(path))
        return
    try:
        document = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        add_check(checks, "methodology contract parses", False, str(error))
        return
    methodology = document.get("methodology", {})
    expected_skills = [
        "grilling",
        "tdd",
        "diagnosing-bugs",
        "code-review",
        "codebase-design",
        "domain-modeling",
    ]
    identity = {
        "name": methodology.get("name"),
        "repository": methodology.get("repository"),
        "ref": methodology.get("ref"),
        "commit": methodology.get("commit"),
    }
    identity_ok = identity == {
        "name": "mattpocock-skills",
        "repository": "mattpocock/skills",
        "ref": "v1.1.0",
        "commit": "d574778f94cf620fcc8ce741584093bc650a61d3",
    }
    add_check(
        checks,
        "methodology identity is pinned",
        identity_ok,
        json.dumps(identity, sort_keys=True),
    )
    skill_hashes = methodology.get("skillHashes", {})
    add_check(
        checks,
        "methodology skill set is exact",
        list(skill_hashes) == expected_skills,
        json.dumps(list(skill_hashes)),
    )
    vendor_root = plugin_root / "vendor" / "mattpocock-skills"
    file_hashes = methodology.get("fileHashes", {})
    for relative, expected_sha in file_hashes.items():
        source = vendor_root / str(relative)
        actual_sha = file_sha256(source) if source.is_file() else None
        add_check(
            checks,
            f"methodology file sha256 matches: {relative}",
            actual_sha == expected_sha,
            f"expected {expected_sha}, actual {actual_sha or 'missing'}",
        )
    license_path = plugin_root / str(methodology.get("licensePath") or "")
    license_sha = file_sha256(license_path) if license_path.is_file() else None
    add_check(
        checks,
        "methodology license sha256 matches",
        license_sha == methodology.get("licenseSha256"),
        f"expected {methodology.get('licenseSha256') or 'missing'}, actual {license_sha or 'missing'}",
    )


def infer_repo_root(plugin_root: Path) -> Path:
    if plugin_root.parent.name == "plugins" and plugin_root.parent.parent.name == "dev":
        return plugin_root.parents[2]
    if plugin_root.parent.name == "plugins":
        return plugin_root.parents[1]
    return Path.cwd()


def add_check(checks: list[dict[str, Any]], name: str, ok: bool, detail: str = "") -> None:
    checks.append({"name": name, "ok": bool(ok), "detail": detail})


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def render_text(report: dict[str, Any]) -> str:
    lines = [f"Release runtime status: {report['status']}"]
    for check in report["checks"]:
        prefix = "OK" if check["ok"] else "FAIL"
        lines.append(f"- {prefix} {check['name']}: {check['detail']}")
    if not report["ok"]:
        lines.append(f"Next action: {report['nextAction']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify DevFlow release runtime audit artifacts.")
    parser.add_argument("--plugin-root", default="plugins/dev-flow")
    parser.add_argument("--repo-root")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = verify_release_runtime(
        Path(args.plugin_root),
        Path(args.repo_root) if args.repo_root else None,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
