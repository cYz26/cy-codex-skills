#!/usr/bin/env python3
"""Post-update sync workflow for the Lark Feishu Ops plugin."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

import lark_feishu_ops_doctor
import lark_feishu_ops_runtime as runtime


HOME = Path.home()
SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = SCRIPT_DIR.parent
PLUGIN_SELECTOR = "lark-feishu-ops@cy-codex-skills"
COMPARE_FILES = runtime.runtime_relative_files(PLUGIN_ROOT)


def run_command(command: list[str], timeout: int = 120) -> dict[str, Any]:
    return runtime.run_command(command, timeout=timeout)


def parse_json_output(result: dict[str, Any]) -> Any | None:
    return runtime.parse_json_output(result)


def compact_result(result: dict[str, Any], *, max_output: int = 1600) -> dict[str, Any]:
    return runtime.compact_result(result, max_output=max_output)


def file_hash(path: Path) -> str | None:
    if path.is_symlink() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def plugin_cache_root(
    home: Path | str,
    plugin_root: Path | str = PLUGIN_ROOT,
) -> Path:
    version = runtime.plugin_version(plugin_root) or "unknown-version"
    return runtime.plugin_cache_root(home) / version


def installed_plugin_root_candidates(
    codex_home: Path | str | None = None,
    plugin_root: Path | str = PLUGIN_ROOT,
) -> list[Path]:
    version = runtime.plugin_version(plugin_root)
    logical_home = logical_codex_home(codex_home)
    if version is None:
        return [plugin_cache_root(logical_home, plugin_root)]
    resolved_home = runtime.resolve_codex_home(codex_home)
    candidates = runtime.installed_plugin_candidates(version, codex_home=codex_home)
    return [logical_home / candidate.relative_to(resolved_home) for candidate in candidates]


def logical_codex_home(explicit: Path | str | None = None) -> Path:
    if explicit is not None:
        return Path(explicit).expanduser()
    configured = os.environ.get("CODEX_HOME")
    if configured:
        return Path(configured).expanduser()
    return HOME / ".codex"


def default_installed_plugin_root(
    codex_home: Path | str | None = None,
    plugin_root: Path | str = PLUGIN_ROOT,
) -> Path:
    candidates = installed_plugin_root_candidates(codex_home, plugin_root)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def inspect_installed_plugin_cache(
    plugin_root: Path | str = PLUGIN_ROOT,
    installed_plugin_root: Path | str | None = None,
    codex_home: Path | str | None = None,
) -> dict[str, Any]:
    source_root = Path(plugin_root)
    installed_root = (
        Path(installed_plugin_root)
        if installed_plugin_root is not None
        else default_installed_plugin_root(codex_home, source_root)
    )
    version = runtime.plugin_version(source_root)
    if not installed_root.exists():
        return {
            "status": "not-installed",
            "source_root": str(source_root),
            "installed_root": str(installed_root),
            "version": version,
            "changed_files": [],
            "missing_files": [],
            "unexpected_files": [],
            "recommendation": f"Install or refresh with `codex plugin add {PLUGIN_SELECTOR}`.",
        }

    changed: list[str] = []
    missing: list[str] = []
    source_files = runtime.runtime_relative_files(source_root)
    installed_files = set(runtime.runtime_relative_files(installed_root))
    for relative in source_files:
        source_hash = file_hash(source_root / relative)
        installed_hash = file_hash(installed_root / relative)
        if installed_hash is None:
            missing.append(relative)
        elif source_hash != installed_hash:
            changed.append(relative)
    unexpected = sorted(installed_files - set(source_files))

    status = (
        "matches-source"
        if not changed and not missing and not unexpected
        else "differs-from-source"
    )
    recommendation = None
    if status != "matches-source":
        recommendation = (
            f"Refresh installed plugin cache with `codex plugin add {PLUGIN_SELECTOR}`."
        )
    return {
        "status": status,
        "source_root": str(source_root),
        "installed_root": str(installed_root),
        "version": version,
        "runtime_files": source_files,
        "changed_files": sorted(changed),
        "missing_files": sorted(missing),
        "unexpected_files": unexpected,
        "recommendation": recommendation,
    }


def run_doctor(repo: str | None = None) -> dict[str, Any]:
    args = argparse.Namespace(
        json=True,
        strict=False,
        repo=repo,
        offline=False,
        skip_update_check=False,
        update_check_policy="always",
        force_update_check=True,
        update_cache_path=None,
        apply_codex_global_unload=False,
    )
    return lark_feishu_ops_doctor.build_report(args)


def build_report(
    *,
    apply_cli_update: bool,
    after_cli_update: bool,
    refresh_installed_plugin: bool,
    repo: str | None,
    plugin_root: Path | str = PLUGIN_ROOT,
    installed_plugin_root: Path | str | None = None,
    codex_home: Path | str | None = None,
) -> dict[str, Any]:
    doctor = run_doctor(repo=repo)
    installed_cache = inspect_installed_plugin_cache(
        plugin_root=plugin_root,
        installed_plugin_root=installed_plugin_root,
        codex_home=codex_home,
    )

    cli_update = None
    if apply_cli_update:
        update_result = run_command(["lark-cli", "update", "--json"], timeout=240)
        update_contract = runtime.validate_json_result(
            update_result,
            required_fields=("action",),
            require_ok_envelope=True,
        )
        cli_update = compact_result(update_result)
        cli_update["ok"] = update_contract["ok"]
        cli_update["payload"] = update_contract["payload"]
        cli_update["validation_errors"] = update_contract["errors"]
        doctor = run_doctor(repo=repo)
        installed_cache = inspect_installed_plugin_cache(
            plugin_root=plugin_root,
            installed_plugin_root=installed_plugin_root,
            codex_home=codex_home,
        )

    installed_plugin_refresh = None
    if refresh_installed_plugin:
        installed_plugin_refresh = compact_result(
            run_command(["codex", "plugin", "add", PLUGIN_SELECTOR], timeout=240)
        )
        doctor = run_doctor(repo=repo)
        installed_cache = inspect_installed_plugin_cache(
            plugin_root=plugin_root,
            installed_plugin_root=installed_plugin_root,
            codex_home=codex_home,
        )

    refresh_recommended = installed_cache["status"] in {"differs-from-source", "not-installed"}

    lark_cli_status = (
        doctor.get("checks", {}).get("lark_cli", {}).get("status")
        if isinstance(doctor, dict)
        else None
    )
    plugin_update_required = lark_cli_status == "FAIL"
    recommendations: list[str] = []
    if refresh_recommended:
        recommendation = installed_cache.get("recommendation")
        if recommendation:
            recommendations.append(recommendation)
    if plugin_update_required:
        recommendations.append(
            "Review Lark CLI compatibility and update lark-feishu-ops through an explicit repository change."
        )
    else:
        recommendations.append(
            "No lark-feishu-ops source change is required unless compatibility checks fail."
        )

    doctor_status = doctor.get("status") if isinstance(doctor, dict) else None
    failed = doctor_status not in {"PASS", "WARN"}
    failed = failed or installed_cache["status"] != "matches-source"
    failed = failed or bool(cli_update is not None and not cli_update.get("ok"))
    failed = failed or bool(
        installed_plugin_refresh is not None and not installed_plugin_refresh.get("ok")
    )

    warned = not failed and doctor_status == "WARN"

    return {
        "status": "FAIL" if failed else ("WARN" if warned else "PASS"),
        "cli_update": cli_update,
        "after_cli_update": after_cli_update,
        "doctor": doctor,
        "compatibility_status": "fail" if plugin_update_required else "pass",
        "installed_plugin_cache": installed_cache,
        "installed_plugin_refresh_recommended": refresh_recommended,
        "installed_plugin_refresh": installed_plugin_refresh,
        "plugin_update_required": plugin_update_required,
        "recommendations": recommendations,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync Lark Feishu Ops after Lark CLI updates.")
    parser.add_argument("--repo", help="Repository path to pass to the Lark Feishu Ops doctor.")
    parser.add_argument(
        "--codex-home",
        help="Explicit Codex home for installed plugin cache inspection.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    parser.add_argument(
        "--apply-cli-update",
        action="store_true",
        help="Explicitly run `lark-cli update --json` before post-update diagnostics.",
    )
    parser.add_argument(
        "--after-cli-update",
        action="store_true",
        help="Run post-update diagnostics without applying the CLI update.",
    )
    parser.add_argument(
        "--refresh-installed-plugin",
        action="store_true",
        help=f"Explicitly run `codex plugin add {PLUGIN_SELECTOR}`.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(
        apply_cli_update=args.apply_cli_update,
        after_cli_update=args.after_cli_update,
        refresh_installed_plugin=args.refresh_installed_plugin,
        repo=args.repo,
        codex_home=args.codex_home,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"status: {report['status']}")
        for recommendation in report["recommendations"]:
            print(f"- {recommendation}")
    return 0 if report["status"] in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
