from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_FALLBACK = "/Applications/Obsidian.app/Contents/MacOS/obsidian-cli"
ALLOWED_COMMANDS = {
    "status": ["status"],
    "search": ["search"],
    "read": ["read"],
    "daily": ["daily"],
    "daily-append": ["daily:append"],
    "daily:append": ["daily:append"],
    "create": ["create"],
    "tags": ["tags"],
    "diff": ["diff"],
}


def obsidian_cli_status(config: dict[str, Any] | None = None):
    command, reason = discover_obsidian_cli(config or {})
    available = command is not None
    result: dict[str, Any] = {
        "ok": available,
        "available": available,
        "used_command": command,
        "fallback_reason": reason,
    }
    return result


def run_obsidian_cli(
    action: str,
    args: list[str] | None = None,
    config: dict[str, Any] | None = None,
    timeout: int = 15,
):
    if action not in ALLOWED_COMMANDS:
        return unavailable("command-not-allowed")
    status = obsidian_cli_status(config)
    if not status["available"]:
        return {
            "ok": False,
            "available": False,
            "used_command": None,
            "stdout": "",
            "stderr": "",
            "fallback_reason": status["fallback_reason"],
        }

    argv = [status["used_command"], *ALLOWED_COMMANDS[action], *(args or [])]
    completed = subprocess.run(
        argv,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    if completed.returncode != 0:
        return {
            "ok": False,
            "available": True,
            "used_command": status["used_command"],
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "fallback_reason": "cli-command-failed",
        }
    return {
        "ok": True,
        "available": True,
        "used_command": status["used_command"],
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "fallback_reason": None,
    }


def discover_obsidian_cli(config: dict[str, Any]):
    candidates = [
        config.get("command"),
        shutil.which("obsidian"),
        config.get("fallback_command") or DEFAULT_FALLBACK,
    ]
    for candidate in candidates:
        resolved = resolve_command(candidate)
        if resolved:
            return resolved, None
    return None, "cli-not-found"


def resolve_command(command: str | None):
    if not command:
        return None
    path = Path(command).expanduser()
    if path.is_absolute():
        if path.exists() and path.is_file():
            return str(path)
        return None
    found = shutil.which(command)
    return found


def unavailable(reason: str):
    return {
        "ok": False,
        "available": False,
        "used_command": None,
        "stdout": "",
        "stderr": "",
        "fallback_reason": reason,
    }
