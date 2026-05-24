from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from workflow_constants import TEMPLATE_ROOT


def repo_path(value: str | os.PathLike[str]) -> Path:
    return Path(value).expanduser().resolve()


def rel(repo: Path, path: Path) -> str:
    try:
        return path.relative_to(repo).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(payload, indent=2)}\n")


def as_bool_text(value: bool) -> str:
    return "true" if value else "false"


def render_template(name: str, values: dict[str, Any]) -> str:
    text = (TEMPLATE_ROOT / name).read_text()
    for key, value in values.items():
        text = text.replace(f"{{{{{key}}}}}", render_value(value))
    return text


def render_value(value: Any) -> str:
    if isinstance(value, bool):
        return as_bool_text(value)
    if isinstance(value, list):
        return "\n".join(f"- {item}" for item in value) if value else "- None"
    return str(value)


def normalize_project_name(repo: Path) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", repo.name).strip("-") or "project"


def sanitize_filename(value: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower()).strip("-")
    return sanitized[:64] or "verification"
