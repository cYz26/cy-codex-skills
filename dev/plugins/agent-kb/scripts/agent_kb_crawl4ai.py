from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path


DEFAULT_COMMANDS = (
    Path.home() / ".codex" / "crawl4ai-venv" / "bin" / "crwl",
    Path.home() / ".codex" / "agent-kb" / "crawl4ai-venv" / "bin" / "crwl",
)


def capability():
    command = configured_command()
    return {
        "name": "crawl4ai",
        "available": bool(command),
        "importance": "optional-url-fetcher",
        "mode": "command" if command else "unavailable",
        "command": command,
        "fetches": ["http", "https"],
    }


def fetch_markdown(url: str):
    command = configured_command()
    if not command:
        return unavailable_result()
    return run_crawl4ai(url, command)


def configured_command():
    for env_name in ("CRAWL4AI_CMD", "AGENT_KB_CRAWL4AI_CMD"):
        value = os.environ.get(env_name, "").strip()
        if value:
            return resolve_command(shlex.split(value))
    for command in DEFAULT_COMMANDS:
        if command.exists():
            return [str(command)]
    return command_from_path("crwl")


def resolve_command(command: list[str]):
    executable = shutil.which(command[0])
    if executable:
        return [executable, *command[1:]]
    if Path(command[0]).exists():
        return command
    return None


def command_from_path(name: str):
    executable = shutil.which(name)
    if executable:
        return [executable]
    return None


def unavailable_result():
    return {
        "ok": False,
        "available": False,
        "extractor": "crawl4ai",
        "error": "crawl4ai command unavailable",
        "text": "",
    }


def run_crawl4ai(url: str, command: list[str]):
    try:
        result = subprocess.run(
            [*command, url, "-o", "markdown"],
            text=True,
            capture_output=True,
            check=False,
            timeout=180,
        )
    except Exception as exc:  # pragma: no cover - depends on local command execution
        return failed_result(str(exc))
    if result.returncode != 0:
        return failed_result((result.stderr or result.stdout).strip())
    text = result.stdout.strip()
    if not text:
        return failed_result("crawl4ai returned empty markdown")
    return {"ok": True, "available": True, "extractor": "crawl4ai", "text": result.stdout}


def failed_result(error: str):
    return {
        "ok": False,
        "available": True,
        "extractor": "crawl4ai",
        "error": error,
        "text": "",
    }
