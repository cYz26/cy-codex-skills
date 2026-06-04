#!/usr/bin/env python3
"""Post-update sync workflow for the Lark Feishu Ops plugin."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import lark_feishu_ops_doctor


HOME = Path.home()
SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = SCRIPT_DIR.parent
PLUGIN_SELECTOR = "lark-feishu-ops@cy-codex-skills"
COMPARE_FILES = [
    ".codex-plugin/plugin.json",
    "README.md",
    "agents/feishu-ops.toml",
    "agents/runtime-prompts/feishu-ops.md",
    "scripts/lark_feishu_ops_agent_context.py",
    "scripts/lark_feishu_ops_doctor.py",
    "scripts/lark_feishu_ops_sync.py",
    "skills/lark-feishu-ops/SKILL.md",
]


def run_command(command: list[str], timeout: int = 120) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        return {
            "command": command,
            "ok": False,
            "exit_code": None,
            "stdout": "",
            "stderr": str(exc),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "ok": False,
            "exit_code": None,
            "stdout": exc.stdout or "",
            "stderr": f"timed out after {timeout}s",
        }
    return {
        "command": command,
        "ok": completed.returncode == 0,
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def parse_json_output(result: dict[str, Any]) -> Any | None:
    stdout = result.get("stdout") or ""
    if not stdout:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def compact_result(result: dict[str, Any], *, max_output: int = 1600) -> dict[str, Any]:
    return {
        "command": result.get("command"),
        "ok": result.get("ok"),
        "exit_code": result.get("exit_code"),
        "stdout": (result.get("stdout") or "")[:max_output],
        "stderr": (result.get("stderr") or "")[:max_output],
    }


def file_hash(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def plugin_cache_root(home: Path) -> Path:
    return home / "plugins" / "cache" / "cy-codex-skills" / "lark-feishu-ops" / "0.1.0"


def installed_plugin_root_candidates(codex_home: Path | None = None) -> list[Path]:
    candidates: list[Path] = []
    env_home = os.environ.get("CODEX_HOME")
    if codex_home is not None:
        candidates.append(plugin_cache_root(codex_home))
    elif env_home:
        candidates.append(plugin_cache_root(Path(env_home).expanduser()))

    candidates.extend(
        [
            plugin_cache_root(HOME / ".codex-switch" / "app-homes" / "internal"),
            plugin_cache_root(HOME / ".codex"),
        ]
    )

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key not in seen:
            unique.append(candidate)
            seen.add(key)
    return unique


def default_installed_plugin_root(codex_home: Path | None = None) -> Path:
    candidates = installed_plugin_root_candidates(codex_home)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def inspect_installed_plugin_cache(
    plugin_root: Path | str = PLUGIN_ROOT,
    installed_plugin_root: Path | str | None = None,
) -> dict[str, Any]:
    source_root = Path(plugin_root)
    installed_root = (
        Path(installed_plugin_root)
        if installed_plugin_root is not None
        else default_installed_plugin_root()
    )
    if not installed_root.exists():
        return {
            "status": "not-installed",
            "source_root": str(source_root),
            "installed_root": str(installed_root),
            "changed_files": [],
            "missing_files": [],
            "recommendation": f"Install or refresh with `codex plugin add {PLUGIN_SELECTOR}`.",
        }

    changed: list[str] = []
    missing: list[str] = []
    for relative in COMPARE_FILES:
        source_hash = file_hash(source_root / relative)
        installed_hash = file_hash(installed_root / relative)
        if source_hash is None:
            continue
        if installed_hash is None:
            missing.append(relative)
        elif source_hash != installed_hash:
            changed.append(relative)

    status = "matches-source" if not changed and not missing else "differs-from-source"
    recommendation = None
    if status != "matches-source":
        recommendation = f"Refresh installed plugin cache with `codex plugin add {PLUGIN_SELECTOR}`."
    return {
        "status": status,
        "source_root": str(source_root),
        "installed_root": str(installed_root),
        "changed_files": changed,
        "missing_files": missing,
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
) -> dict[str, Any]:
    cli_update = None
    if apply_cli_update:
        update_result = run_command(["lark-cli", "update", "--json"], timeout=240)
        cli_update = compact_result(update_result)
        cli_update["payload"] = parse_json_output(update_result)

    doctor = run_doctor(repo=repo)
    installed_cache = inspect_installed_plugin_cache(
        plugin_root=plugin_root,
        installed_plugin_root=installed_plugin_root,
    )
    refresh_recommended = installed_cache["status"] in {"differs-from-source", "not-installed"}

    installed_plugin_refresh = None
    if refresh_installed_plugin:
        installed_plugin_refresh = compact_result(
            run_command(["codex", "plugin", "add", PLUGIN_SELECTOR], timeout=240)
        )

    lark_cli_status = (
        doctor.get("checks", {}).get("lark_cli", {}).get("status")
        if isinstance(doctor, dict)
        else None
    )
    plugin_update_required = lark_cli_status == "FAIL"
    recommendations: list[str] = []
    if refresh_recommended and not refresh_installed_plugin:
        recommendations.append(installed_cache["recommendation"])
    if plugin_update_required:
        recommendations.append(
            "Review Lark CLI compatibility and update lark-feishu-ops source through OpenSpec."
        )
    else:
        recommendations.append(
            "No lark-feishu-ops source change is required unless compatibility checks fail."
        )

    failed = plugin_update_required
    failed = failed or bool(cli_update is not None and not cli_update.get("ok"))
    failed = failed or bool(
        installed_plugin_refresh is not None and not installed_plugin_refresh.get("ok")
    )

    return {
        "status": "FAIL" if failed else "PASS",
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
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"status: {report['status']}")
        for recommendation in report["recommendations"]:
            print(f"- {recommendation}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
