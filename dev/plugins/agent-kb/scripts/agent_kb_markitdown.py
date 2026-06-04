from __future__ import annotations

import importlib.util
import os
import shlex
import shutil
import subprocess
from pathlib import Path


DEFAULT_COMMAND = Path.home() / ".codex" / "agent-kb" / "markitdown-venv" / "bin" / "markitdown"


def capability():
    command = configured_command()
    module_available = has_module()
    return {
        "name": "markitdown",
        "available": bool(command) or module_available,
        "importance": "optional-but-primary",
        "mode": mode(command, module_available),
        "fallbacks": ["text", "html", "pdf", "docx", "csv", "xlsx"],
    }


def convert(path: Path):
    command = configured_command()
    if command:
        return convert_with_command(path, command)
    if has_module():
        return convert_with_module(path)
    return {"ok": False, "available": False, "extractor": "markitdown", "text": ""}


def configured_command():
    value = os.environ.get("AGENT_KB_MARKITDOWN_CMD", "").strip()
    if value:
        return resolve_command(shlex.split(value))
    if DEFAULT_COMMAND.exists():
        return [str(DEFAULT_COMMAND)]
    return command_from_path("markitdown")


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


def has_module():
    return importlib.util.find_spec("markitdown") is not None


def mode(command: list[str] | None, module_available: bool):
    if command:
        return "command"
    if module_available:
        return "python-module"
    return "unavailable"


def convert_with_module(path: Path):
    try:
        from markitdown import MarkItDown

        result = MarkItDown().convert(str(path))
        return {"ok": True, "available": True, "extractor": "markitdown", "text": result.text_content}
    except Exception as exc:  # pragma: no cover - depends on optional package internals
        return {"ok": False, "available": True, "extractor": "markitdown", "error": str(exc), "text": ""}


def convert_with_command(path: Path, command: list[str]):
    try:
        result = subprocess.run(
            [*command, str(path)],
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
    except Exception as exc:  # pragma: no cover - depends on local command execution
        return {"ok": False, "available": True, "extractor": "markitdown", "error": str(exc), "text": ""}
    if result.returncode == 0:
        return {"ok": True, "available": True, "extractor": "markitdown", "text": result.stdout}
    return {
        "ok": False,
        "available": True,
        "extractor": "markitdown",
        "error": (result.stderr or result.stdout).strip(),
        "text": "",
    }
