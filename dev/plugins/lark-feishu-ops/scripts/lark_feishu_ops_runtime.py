#!/usr/bin/env python3
"""Shared local-runtime facts for Lark Feishu Ops command facades."""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path
from typing import Any, Callable, Iterable


TRANSIENT_DIRS = frozenset({"__pycache__", ".pytest_cache", ".mypy_cache"})
TRANSIENT_SUFFIXES = frozenset({".pyc", ".pyo", ".tmp"})
DEVELOPMENT_DIRS = frozenset({"tests", "evals", "fixtures", "log", "logs"})
VERSION_PATTERN = re.compile(r"(?<!\d)(\d+\.\d+\.\d+)(?!\d)")


def run_command(command: list[str], timeout: int = 30) -> dict[str, Any]:
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
        return command_result(command, False, None, "", str(exc))
    except subprocess.TimeoutExpired as exc:
        return command_result(
            command,
            False,
            None,
            _text(exc.stdout),
            f"timed out after {timeout}s",
        )
    return command_result(
        command,
        completed.returncode == 0,
        completed.returncode,
        completed.stdout.strip(),
        completed.stderr.strip(),
    )


def command_result(
    command: list[str],
    ok: bool,
    exit_code: int | None,
    stdout: str,
    stderr: str,
) -> dict[str, Any]:
    return {
        "command": list(command),
        "ok": ok,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
    }


def _text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return str(value or "")


def parse_json_output(result: dict[str, Any]) -> Any | None:
    stdout = result.get("stdout") or ""
    if not isinstance(stdout, str) or not stdout.strip():
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def validate_json_result(
    result: dict[str, Any],
    *,
    required_fields: Iterable[str] = (),
    require_ok_envelope: bool = False,
) -> dict[str, Any]:
    payload = parse_json_output(result)
    errors: list[str] = []
    if result.get("exit_code") != 0 or not result.get("ok"):
        errors.append("process_exit")
    if not isinstance(payload, dict):
        errors.append("json_object_required")
    else:
        if require_ok_envelope and payload.get("ok") is not True:
            errors.append("ok_true_required")
        elif "ok" in payload and payload.get("ok") is not True:
            errors.append("ok_false")
        for field in required_fields:
            if field not in payload or payload.get(field) is None:
                errors.append(f"missing_required_field:{field}")
    return {
        "ok": not errors,
        "payload": payload,
        "errors": errors,
        "command": result.get("command"),
        "exit_code": result.get("exit_code"),
        "stderr": str(result.get("stderr") or "")[:1200],
    }


def compact_result(result: dict[str, Any], *, max_output: int = 1200) -> dict[str, Any]:
    return {
        "command": result.get("command"),
        "ok": result.get("ok"),
        "exit_code": result.get("exit_code"),
        "stdout": str(result.get("stdout") or "")[:max_output],
        "stderr": str(result.get("stderr") or "")[:max_output],
    }


def inventory_executables(
    name: str = "lark-cli",
    *,
    path_value: str | None = None,
    preferred: str | None = None,
) -> list[dict[str, Any]]:
    candidates: list[Path] = []
    preferred_path = Path(preferred).expanduser().absolute() if preferred else None
    if preferred:
        candidates.append(Path(preferred).expanduser())
    for directory in (path_value if path_value is not None else os.environ.get("PATH", "")).split(os.pathsep):
        if directory:
            candidates.append(Path(directory).expanduser() / name)

    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        absolute = candidate.absolute()
        try:
            exists = absolute.is_file() and os.access(absolute, os.X_OK)
        except OSError:
            exists = False
        if not exists and absolute != preferred_path:
            continue
        try:
            resolved = absolute.resolve(strict=exists)
        except OSError:
            resolved = absolute
        key = str(resolved) if exists else str(absolute)
        if key in seen:
            continue
        seen.add(key)
        records.append(
            {
                "path": str(absolute),
                "resolved_path": str(resolved),
                "exists": exists,
                "canonical": not records,
                "owner": package_owner(absolute, resolved),
            }
        )
    return records


def package_owner(path: Path, resolved: Path | None = None) -> str:
    text = f"{path} {resolved or ''}".lower()
    if "/.nvm/versions/node/" in text:
        return "npm-global:nvm"
    if "/opt/homebrew/" in text and ("node_modules" in text or "/bin/lark-cli" in text):
        return "npm-global:homebrew-prefix"
    if "node_modules/@larksuite/cli" in text:
        return "npm-global"
    return "unknown"


def invocation_for(record: dict[str, Any], fallback: str = "lark-cli") -> str:
    return str(record.get("path")) if record.get("exists") else fallback


def parse_version(value: Any) -> str | None:
    match = VERSION_PATTERN.search(str(value or ""))
    return match.group(1) if match else None


def read_plugin_manifest(plugin_root: Path | str) -> dict[str, Any]:
    root = Path(plugin_root).expanduser()
    path = root / ".codex-plugin" / "plugin.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {"ok": False, "path": str(path), "manifest": None, "error": "invalid_manifest"}
    if not isinstance(payload, dict) or not isinstance(payload.get("version"), str):
        return {"ok": False, "path": str(path), "manifest": payload, "error": "missing_version"}
    return {"ok": True, "path": str(path), "manifest": payload, "error": None}


def plugin_version(plugin_root: Path | str) -> str | None:
    report = read_plugin_manifest(plugin_root)
    manifest = report.get("manifest")
    return str(manifest.get("version")) if report["ok"] and isinstance(manifest, dict) else None


def resolve_codex_home(explicit: Path | str | None = None) -> Path:
    if explicit is not None:
        return Path(explicit).expanduser().resolve()
    configured = os.environ.get("CODEX_HOME")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / ".codex").resolve()


def plugin_cache_root(codex_home: Path | str) -> Path:
    return Path(codex_home).expanduser() / "plugins" / "cache" / "cy-codex-skills" / "lark-feishu-ops"


def installed_plugin_candidates(
    version: str,
    *,
    codex_home: Path | str | None = None,
) -> list[Path]:
    home = resolve_codex_home(codex_home)
    root = plugin_cache_root(home)
    candidates = [root / version]
    if root.is_dir():
        candidates.extend(sorted((path for path in root.iterdir() if path.is_dir()), reverse=True))
    result: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key not in seen:
            seen.add(key)
            result.append(candidate)
    return result


def iter_runtime_files(plugin_root: Path | str) -> list[Path]:
    root = Path(plugin_root)
    files: list[Path] = []
    if not root.is_dir():
        return files
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in TRANSIENT_DIRS or part in DEVELOPMENT_DIRS for part in relative.parts):
            continue
        if path.is_symlink() or not path.is_file():
            continue
        if path.suffix in TRANSIENT_SUFFIXES or path.name == ".DS_Store":
            continue
        files.append(path)
    return files


def runtime_relative_files(plugin_root: Path | str) -> list[str]:
    root = Path(plugin_root)
    return [path.relative_to(root).as_posix() for path in iter_runtime_files(root)]


def owner_only_mode(path: Path | str) -> bool:
    try:
        return stat.S_IMODE(Path(path).stat().st_mode) == 0o600
    except OSError:
        return False


def run_json_command(
    command: list[str],
    *,
    required_fields: Iterable[str] = (),
    require_ok_envelope: bool = False,
    timeout: int = 30,
    runner: Callable[[list[str], int], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    execute = runner or (lambda argv, seconds: run_command(argv, timeout=seconds))
    result = execute(command, timeout)
    contract = validate_json_result(
        result,
        required_fields=required_fields,
        require_ok_envelope=require_ok_envelope,
    )
    return {"result": compact_result(result), **contract}
