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
from typing import Any

from workflow_context_config import read_config as read_toml_config


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
        help="Do not run known external updaters such as Lark, GSD, or OpenSpec.",
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


def parse_jsonish_version(output: str) -> str | None:
    text = output.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return text.splitlines()[-1].strip() or None
    if isinstance(parsed, str):
        return parsed
    if isinstance(parsed, dict):
        version = parsed.get("version")
        return str(version) if version else None
    return None


def npm_latest_version(package: str) -> str | None:
    if not executable_exists("npm"):
        return None
    result = run_command(["npm", "view", package, "version", "--json"], timeout=300)
    if not result["ok"]:
        return None
    return parse_jsonish_version(result["stdout"])


def read_first_existing(paths: list[Path]) -> str | None:
    for path in paths:
        if path.exists():
            value = path.read_text().strip()
            if value:
                return value
    return None


def installed_gsd_version(codex_home: Path) -> str | None:
    return read_first_existing([codex_home / "get-shit-done" / "VERSION"])


def installed_openspec_version(codex_home: Path) -> str | None:
    for skill in ["openspec-propose", "openspec-explore", "openspec-apply-change", "openspec-archive-change"]:
        path = codex_home / "skills" / skill / "SKILL.md"
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if line.strip().startswith("generatedBy:"):
                return line.split(":", 1)[1].strip().strip('"')
    if executable_exists("openspec"):
        result = run_command(["openspec", "--version"], timeout=120)
        if result["ok"]:
            return parse_jsonish_version(result["stdout"])
    return None


def version_check_item(kind: str, name: str, current: str | None, latest: str | None, detail: str) -> dict[str, Any]:
    if current and latest:
        status = "update-available" if current != latest else "unchanged"
    elif latest:
        status = "latest-known"
    else:
        status = "check-unavailable"
    return item(
        kind,
        name,
        status,
        detail,
        current=current,
        latest=latest,
        updateAvailable=bool(current and latest and current != latest),
    )


def short_output(result: dict[str, Any], limit: int = 600) -> str:
    text = (result.get("stdout") or "") + (result.get("stderr") or "")
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "...(truncated)"


def read_config(codex_home: Path) -> dict[str, Any]:
    path = codex_home / "config.toml"
    return read_toml_config(path)


def git_head(repo: Path) -> str | None:
    result = run_command(["git", "-C", str(repo), "rev-parse", "HEAD"])
    if not result["ok"]:
        return None
    return result["stdout"].strip()


def git_upstream_head(repo: Path) -> tuple[str | None, str]:
    fetch = run_command(["git", "-C", str(repo), "fetch", "--quiet"], timeout=600)
    if not fetch["ok"]:
        return None, short_output(fetch) or "could not fetch upstream"
    result = run_command(["git", "-C", str(repo), "rev-parse", "@{upstream}"])
    if not result["ok"]:
        return None, short_output(result) or "could not resolve upstream"
    return result["stdout"].strip(), ""


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
        after, detail = git_upstream_head(repo)
        if after is None:
            return item("git", name, "check-unavailable", detail, before=before, path=repo)
        status = "unchanged" if before == after else "would-update"
        message = "matches upstream" if status == "unchanged" else "remote update available"
        return item("git", name, status, message, before=before, after=after, path=repo)

    result = run_command(["git", "-C", str(repo), "pull", "--ff-only"], timeout=600)
    after = git_head(repo)
    if result["ok"]:
        status = "updated" if before != after else "unchanged"
        return item(
            "git",
            name,
            status,
            short_output(result) or "already up to date",
            before=before,
            after=after,
            path=repo,
        )
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
            results.append(
                item(
                    "plugin-cache",
                    name,
                    "skipped",
                    "cache differs from previous marketplace mirror",
                    path=cache,
                )
            )
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


def configured_plugin_selectors(config: dict[str, Any]) -> list[str]:
    marketplaces = set(config.get("marketplaces", {}))
    selectors: list[str] = []
    for selector, plugin_config in sorted(config.get("plugins", {}).items()):
        if "@" not in selector:
            continue
        marketplace = selector.rsplit("@", 1)[1]
        if marketplace not in marketplaces:
            continue
        if isinstance(plugin_config, dict) and not plugin_config.get("enabled", False):
            continue
        selectors.append(selector)
    return selectors


def marketplace_plugin_source(config: dict[str, Any], selector: str) -> Path | None:
    plugin_name, marketplace = selector.rsplit("@", 1)
    marketplace_config = config.get("marketplaces", {}).get(marketplace, {})
    source_root_value = marketplace_config.get("source") if isinstance(marketplace_config, dict) else None
    if not source_root_value:
        return None
    source_root = Path(str(source_root_value)).expanduser()
    catalog = source_root / ".agents" / "plugins" / "marketplace.json"
    if catalog.exists():
        try:
            data = json.loads(catalog.read_text())
        except json.JSONDecodeError:
            data = {}
        for record in data.get("plugins", []):
            if record.get("name") != plugin_name:
                continue
            source = record.get("source", {})
            path_value = source.get("path") if isinstance(source, dict) else None
            if path_value:
                return (source_root / path_value).resolve()
    for candidate in [source_root / "plugins" / plugin_name, source_root / plugin_name]:
        if candidate.exists():
            return candidate.resolve()
    return None


def installed_plugin_cache_dirs(codex_home: Path, selector: str) -> list[Path]:
    plugin_name, marketplace = selector.rsplit("@", 1)
    root = codex_home / "plugins" / "cache" / marketplace / plugin_name
    if not root.exists():
        return []
    return sorted(path for path in root.iterdir() if (path / ".codex-plugin" / "plugin.json").exists())


def plugin_cache_verification_results(codex_home: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for selector in configured_plugin_selectors(config):
        source = marketplace_plugin_source(config, selector)
        caches = installed_plugin_cache_dirs(codex_home, selector)
        if source is None:
            results.append(item("plugin-cache-verify", selector, "source-unavailable", "marketplace source not found"))
            continue
        if not caches:
            results.append(
                item(
                    "plugin-cache-verify",
                    selector,
                    "cache-missing",
                    "installed plugin cache not found",
                    source=str(source),
                )
            )
            continue
        for cache in caches:
            status = "matches-source" if same_tree(cache, source) else "differs-from-source"
            detail = (
                "installed cache matches marketplace source"
                if status == "matches-source"
                else "installed cache differs from marketplace source"
            )
            results.append(item("plugin-cache-verify", selector, status, detail, path=cache, source=str(source)))
    return results


def plugin_install_results(config: dict[str, Any], apply: bool) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for selector in configured_plugin_selectors(config):
        source = marketplace_plugin_source(config, selector)
        if source is None:
            results.append(item("plugin-install", selector, "source-unavailable", "marketplace source not found"))
            continue
        if not apply:
            results.append(
                item("plugin-install", selector, "would-refresh", "would run codex plugin add", source=str(source))
            )
            continue
        result = run_command(["codex", "plugin", "add", selector], timeout=600)
        status = "updated-or-unchanged" if result["ok"] else "failed"
        results.append(item("plugin-install", selector, status, short_output(result), source=str(source)))
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

    has_lark_skills = (Path.home() / ".agents" / "skills" / "lark-shared" / "SKILL.md").exists()
    if executable_exists("lark-cli") or has_lark_skills:
        if not apply:
            detail = (
                "would run npm update -g @larksuite/cli and "
                "npx skills add larksuite/cli -g -y"
            )
            results.append(
                item("external-updater", "lark-cli-and-skills", "would-try", detail)
            )
        elif executable_exists("npm") and executable_exists("npx"):
            first = run_command(["npm", "update", "-g", "@larksuite/cli"], timeout=900)
            second = run_command(["npx", "-y", "skills", "add", "larksuite/cli", "-g", "-y"], timeout=900)
            status = "updated-or-unchanged" if first["ok"] and second["ok"] else "failed"
            detail = "; ".join(part for part in [short_output(first), short_output(second)] if part)
            results.append(item("external-updater", "lark-cli-and-skills", status, detail))
        else:
            results.append(item("external-updater", "lark-cli-and-skills", "skipped", "npm or npx not available"))

    has_gsd = (
        (codex_home / "get-shit-done" / "VERSION").exists()
        or (codex_home / "skills" / "gsd-update" / "SKILL.md").exists()
    )
    if has_gsd:
        if not apply:
            current = installed_gsd_version(codex_home)
            latest = npm_latest_version("get-shit-done-cc")
            results.append(
                version_check_item(
                    "external-updater",
                    "gsd-codex",
                    current,
                    latest,
                    "read-only check; apply would run npx get-shit-done-cc@latest --codex --global --profile=standard",
                )
            )
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
            current = installed_openspec_version(codex_home)
            latest = npm_latest_version("@fission-ai/openspec")
            results.append(
                version_check_item(
                    "external-updater",
                    "openspec-cli",
                    current,
                    latest,
                    "read-only check; apply would run npm update -g @fission-ai/openspec",
                )
            )
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
    **extra: Any,
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
    payload.update({key: value for key, value in extra.items() if value is not None})
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
    results.extend(plugin_install_results(config, args.apply))
    results.extend(plugin_cache_verification_results(codex_home, config))

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
