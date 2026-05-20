#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Safely auto-update locally installed Codex plugins and skills."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform updates. Without this flag the script only reports planned work.",
    )
    parser.add_argument("--json", action="store_true", help="Print a JSON report.")
    parser.add_argument(
        "--codex-home",
        default=os.environ.get("CODEX_HOME", str(Path.home() / ".codex")),
        help="Codex home directory.",
    )
    parser.add_argument(
        "--skip-codex-update",
        action="store_true",
        help="Do not run `codex update`.",
    )
    parser.add_argument(
        "--skip-openai-curated-cache",
        action="store_true",
        help="Do not sync openai-curated plugin caches from the local openai/plugins mirror.",
    )
    parser.add_argument(
        "--skip-external-updaters",
        action="store_true",
        help="Do not run known external updaters such as Lark, Agent Reach, GSD, or OpenSpec.",
    )
    return parser.parse_args()


def run_command(command: list[str], cwd: Path | None = None, timeout: int = 300) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": f"missing executable: {command[0]}"}
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "returncode": None,
            "stdout": exc.stdout or "",
            "stderr": f"timeout after {timeout}s",
        }
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def short_output(result: dict[str, Any], limit: int = 600) -> str:
    text = (result.get("stdout") or "") + (result.get("stderr") or "")
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "...(truncated)"


def read_config(codex_home: Path) -> dict[str, Any]:
    path = codex_home / "config.toml"
    if not path.exists():
        return {}
    return tomllib.loads(path.read_text())


def git_head(repo: Path) -> str | None:
    result = run_command(["git", "-C", str(repo), "rev-parse", "HEAD"])
    if not result["ok"]:
        return None
    return result["stdout"].strip()


def git_is_clean(repo: Path) -> bool:
    result = run_command(["git", "-C", str(repo), "status", "--porcelain"])
    return result["ok"] and result["stdout"].strip() == ""


def is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()


def update_git_repo(repo: Path, name: str, apply: bool) -> dict[str, Any]:
    if not repo.exists():
        return item("git", name, "missing", f"{repo} does not exist", path=repo)
    if not is_git_repo(repo):
        return item("git", name, "skipped", "not a git checkout", path=repo)
    if not git_is_clean(repo):
        return item("git", name, "skipped", "working tree is dirty", path=repo)

    before = git_head(repo)
    if not apply:
        return item("git", name, "would-update", "clean git checkout", before=before, path=repo)

    result = run_command(["git", "-C", str(repo), "pull", "--ff-only"], timeout=600)
    after = git_head(repo)
    if result["ok"]:
        status = "updated" if before != after else "unchanged"
        return item("git", name, status, short_output(result) or "already up to date", before=before, after=after, path=repo)
    return item("git", name, "failed", short_output(result), before=before, after=after, path=repo)


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_fingerprint(root: Path) -> dict[str, str]:
    fingerprint: dict[str, str] = {}
    if not root.exists():
        return fingerprint
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if ".git/" in rel or rel == ".git":
            continue
        if path.is_symlink():
            fingerprint[rel] = "symlink:" + os.readlink(path)
        elif path.is_file():
            fingerprint[rel] = "file:" + file_digest(path)
        elif path.is_dir():
            fingerprint[rel] = "dir"
    return fingerprint


def same_tree(left: Path, right: Path) -> bool:
    return tree_fingerprint(left) == tree_fingerprint(right)


def timestamp() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")


def backup_name(path: Path) -> str:
    return path.as_posix().strip("/").replace("/", "__")


def replace_tree(src: Path, dest: Path, backup_root: Path, apply: bool) -> dict[str, Any]:
    if not src.exists():
        return {"ok": False, "detail": f"source missing: {src}"}
    if not dest.exists():
        if apply:
            shutil.copytree(src, dest, symlinks=True)
        return {"ok": True, "detail": "installed"}
    backup = backup_root / backup_name(dest)
    if not apply:
        return {"ok": True, "detail": f"would replace; backup would be {backup}"}
    backup.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(dest), str(backup))
        shutil.copytree(src, dest, symlinks=True)
    except Exception as exc:  # noqa: BLE001
        if not dest.exists() and backup.exists():
            shutil.move(str(backup), str(dest))
        return {"ok": False, "detail": f"{exc}"}
    return {"ok": True, "detail": f"replaced; backup: {backup}"}


def installed_curated_skill_names(codex_home: Path, curated_root: Path) -> list[str]:
    skills_root = codex_home / "skills"
    if not skills_root.exists() or not curated_root.exists():
        return []
    names = []
    for source in sorted(curated_root.iterdir()):
        if source.is_dir() and (source / "SKILL.md").exists() and (skills_root / source.name / "SKILL.md").exists():
            names.append(source.name)
    return names


def snapshot_curated_skill_safety(codex_home: Path, curated_root: Path) -> dict[str, bool]:
    safety: dict[str, bool] = {}
    for name in installed_curated_skill_names(codex_home, curated_root):
        local = codex_home / "skills" / name
        source = curated_root / name
        safety[name] = same_tree(local, source)
    return safety


def sync_curated_skills(
    codex_home: Path,
    curated_root: Path,
    safety: dict[str, bool],
    backup_root: Path,
    apply: bool,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for name in sorted(safety):
        local = codex_home / "skills" / name
        source = curated_root / name
        if not safety[name]:
            results.append(item("skill", name, "skipped", "local copy differs from previous upstream", path=local))
            continue
        if same_tree(local, source):
            results.append(item("skill", name, "unchanged", "matches upstream", path=local))
            continue
        replacement = replace_tree(source, local, backup_root, apply)
        status = "updated" if replacement["ok"] else "failed"
        if not apply and replacement["ok"]:
            status = "would-update"
        results.append(item("skill", name, status, replacement["detail"], path=local))
    return results


def openai_curated_cache_dirs(codex_home: Path) -> list[tuple[str, Path]]:
    cache_root = codex_home / "plugins" / "cache" / "openai-curated"
    if not cache_root.exists():
        return []
    found: list[tuple[str, Path]] = []
    for plugin_dir in sorted(cache_root.iterdir()):
        if not plugin_dir.is_dir():
            continue
        for ref_dir in sorted(plugin_dir.iterdir()):
            if (ref_dir / ".codex-plugin" / "plugin.json").exists():
                found.append((plugin_dir.name, ref_dir))
    return found


def snapshot_openai_curated_cache_safety(codex_home: Path, mirror_root: Path) -> dict[str, dict[str, Any]]:
    safety: dict[str, dict[str, Any]] = {}
    source_plugins = mirror_root / "plugins"
    for name, cache_dir in openai_curated_cache_dirs(codex_home):
        source = source_plugins / name
        key = str(cache_dir)
        safety[key] = {
            "name": name,
            "cache": cache_dir,
            "source": source,
            "safe": source.exists() and same_tree(cache_dir, source),
        }
    return safety


def sync_openai_curated_plugin_cache(
    safety: dict[str, dict[str, Any]],
    backup_root: Path,
    apply: bool,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for key in sorted(safety):
        record = safety[key]
        name = record["name"]
        cache = record["cache"]
        source = record["source"]
        if not record["safe"]:
            results.append(item("plugin-cache", name, "skipped", "cache differs from previous marketplace mirror", path=cache))
            continue
        if same_tree(cache, source):
            results.append(item("plugin-cache", name, "unchanged", "matches marketplace mirror", path=cache))
            continue
        replacement = replace_tree(source, cache, backup_root, apply)
        status = "updated" if replacement["ok"] else "failed"
        if not apply and replacement["ok"]:
            status = "would-update"
        results.append(item("plugin-cache", name, status, replacement["detail"], path=cache))
    return results


def marketplace_upgrade_results(config: dict[str, Any], apply: bool) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for name in sorted(config.get("marketplaces", {})):
        if not apply:
            results.append(item("marketplace", name, "would-try", "would run codex plugin marketplace upgrade"))
            continue
        result = run_command(["codex", "plugin", "marketplace", "upgrade", name], timeout=600)
        status = "updated-or-unchanged" if result["ok"] else "skipped"
        results.append(item("marketplace", name, status, short_output(result)))
    return results


def direct_git_install_roots(codex_home: Path) -> list[tuple[str, Path]]:
    roots = [codex_home / "skills", Path.home() / ".agents" / "skills", codex_home / "plugins"]
    found: list[tuple[str, Path]] = []
    for root in roots:
        if not root.exists():
            continue
        for child in sorted(root.iterdir()):
            if child.is_dir() and is_git_repo(child):
                found.append((f"direct:{child.name}", child))
    return found


def executable_exists(name: str) -> bool:
    return shutil.which(name) is not None


def run_external_updaters(codex_home: Path, apply: bool) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    if executable_exists("agent-reach"):
        if not apply:
            results.append(item("external-updater", "agent-reach", "would-try", "would run pipx upgrade agent-reach"))
        elif executable_exists("pipx"):
            result = run_command(["pipx", "upgrade", "agent-reach"], timeout=600)
            status = "updated-or-unchanged" if result["ok"] else "failed"
            results.append(item("external-updater", "agent-reach", status, short_output(result)))
        else:
            result = run_command(["agent-reach", "check-update"], timeout=300)
            status = "checked" if result["ok"] else "failed"
            results.append(item("external-updater", "agent-reach", status, short_output(result)))

    has_lark_skills = (Path.home() / ".agents" / "skills" / "lark-shared" / "SKILL.md").exists()
    if executable_exists("lark-cli") or has_lark_skills:
        if not apply:
            results.append(item("external-updater", "lark-cli-and-skills", "would-try", "would run npm update -g @larksuite/cli and npx skills add larksuite/cli -g -y"))
        elif executable_exists("npm") and executable_exists("npx"):
            first = run_command(["npm", "update", "-g", "@larksuite/cli"], timeout=900)
            second = run_command(["npx", "-y", "skills", "add", "larksuite/cli", "-g", "-y"], timeout=900)
            status = "updated-or-unchanged" if first["ok"] and second["ok"] else "failed"
            detail = "; ".join(part for part in [short_output(first), short_output(second)] if part)
            results.append(item("external-updater", "lark-cli-and-skills", status, detail))
        else:
            results.append(item("external-updater", "lark-cli-and-skills", "skipped", "npm or npx not available"))

    has_gsd = (codex_home / "get-shit-done" / "VERSION").exists() or (codex_home / "skills" / "gsd-update" / "SKILL.md").exists()
    if has_gsd:
        if not apply:
            results.append(item("external-updater", "gsd-codex", "would-try", "would run npx get-shit-done-cc@latest --codex --global --profile=standard"))
        elif executable_exists("npx"):
            result = run_command(
                ["npx", "-y", "get-shit-done-cc@latest", "--codex", "--global", "--profile=standard"],
                timeout=900,
            )
            status = "updated-or-unchanged" if result["ok"] else "failed"
            results.append(item("external-updater", "gsd-codex", status, short_output(result)))
        else:
            results.append(item("external-updater", "gsd-codex", "skipped", "npx not available"))

    has_openspec = any((codex_home / "skills" / skill / "SKILL.md").exists() for skill in [
        "openspec-propose",
        "openspec-explore",
        "openspec-apply-change",
        "openspec-archive-change",
    ])
    if executable_exists("openspec") or has_openspec:
        if not apply:
            results.append(item("external-updater", "openspec-cli", "would-try", "would run npm update -g @fission-ai/openspec"))
        elif executable_exists("npm"):
            result = run_command(["npm", "update", "-g", "@fission-ai/openspec"], timeout=600)
            status = "updated-or-unchanged" if result["ok"] else "failed"
            results.append(item("external-updater", "openspec-cli", status, short_output(result)))
        else:
            results.append(item("external-updater", "openspec-cli", "skipped", "npm not available"))

    return results


def item(
    kind: str,
    name: str,
    status: str,
    detail: str,
    before: str | None = None,
    after: str | None = None,
    path: Path | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "kind": kind,
        "name": name,
        "status": status,
        "detail": detail,
    }
    if before is not None:
        payload["before"] = before
    if after is not None:
        payload["after"] = after
    if path is not None:
        payload["path"] = str(path)
    return payload


def print_text(report: dict[str, Any]) -> None:
    print(f"mode: {'apply' if report['apply'] else 'dry-run'}")
    print(f"codex_home: {report['codex_home']}")
    print(f"backup_root: {report['backup_root']}")
    for result in report["results"]:
        path = f" ({result['path']})" if "path" in result else ""
        print(f"{result['kind']} {result['name']}: {result['status']} - {result['detail']}{path}")


def main() -> int:
    args = parse_args()
    codex_home = Path(args.codex_home).expanduser().resolve()
    backup_root = codex_home / "update-backups" / timestamp()
    vendor_skills = codex_home / "vendor_imports" / "skills"
    curated_root = vendor_skills / "skills" / ".curated"
    openai_plugins_mirror = codex_home / ".tmp" / "plugins"
    config = read_config(codex_home)

    skill_safety = snapshot_curated_skill_safety(codex_home, curated_root)
    plugin_cache_safety = snapshot_openai_curated_cache_safety(codex_home, openai_plugins_mirror)

    results: list[dict[str, Any]] = []
    if not args.skip_codex_update:
        if args.apply:
            result = run_command(["codex", "update"], timeout=600)
            status = "updated-or-unchanged" if result["ok"] else "manual-required"
            results.append(item("codex", "codex-cli-app", status, short_output(result)))
        else:
            results.append(item("codex", "codex-cli-app", "would-try", "would run codex update"))

    results.append(update_git_repo(vendor_skills, "openai/skills mirror", args.apply))
    results.append(update_git_repo(openai_plugins_mirror, "openai/plugins mirror", args.apply))
    for name, repo in direct_git_install_roots(codex_home):
        results.append(update_git_repo(repo, name, args.apply))

    if not args.skip_external_updaters:
        results.extend(run_external_updaters(codex_home, args.apply))

    results.extend(sync_curated_skills(codex_home, curated_root, skill_safety, backup_root, args.apply))
    if not args.skip_openai_curated_cache:
        results.extend(sync_openai_curated_plugin_cache(plugin_cache_safety, backup_root, args.apply))
    results.extend(marketplace_upgrade_results(config, args.apply))

    report = {
        "apply": bool(args.apply),
        "codex_home": str(codex_home),
        "backup_root": str(backup_root),
        "results": results,
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_text(report)

    failed = [r for r in results if r["status"] in {"failed"}]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
