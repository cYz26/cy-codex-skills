from __future__ import annotations

import os
import shlex
import shutil
from pathlib import Path


COMMAND_ENVS = ("CRAWL4AI_CMD", "AGENT_KB_CRAWL4AI_CMD")
DEFAULT_COMMANDS = (
    Path.home() / ".codex" / "crawl4ai-venv" / "bin" / "crwl",
    Path.home() / ".codex" / "agent-kb" / "crawl4ai-venv" / "bin" / "crwl",
)


def configured_command() -> list[str] | None:
    for env_name in COMMAND_ENVS:
        command = command_from_env(env_name)
        if command:
            return command
    for command in DEFAULT_COMMANDS:
        if command.exists():
            return [str(command)]
    return command_from_path("crwl")


def command_from_env(env_name: str) -> list[str] | None:
    value = os.environ.get(env_name, "").strip()
    return resolve_command(shlex.split(value)) if value else None


def command_from_path(name: str) -> list[str] | None:
    executable = shutil.which(name)
    return [executable] if executable else None


def resolve_command(command: list[str]) -> list[str] | None:
    if not command:
        return None
    executable = shutil.which(command[0])
    if executable:
        return [executable, *command[1:]]
    return command if Path(command[0]).exists() else None
