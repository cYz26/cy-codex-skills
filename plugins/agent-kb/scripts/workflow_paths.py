from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

def repo_path(value: str | os.PathLike[str]) -> Path:
    return Path(value).expanduser().resolve()


def rel(repo: Path, path: Path) -> str:
    try:
        return path.relative_to(repo).as_posix()
    except ValueError:
        return path.as_posix()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(payload, indent=2)}\n")


def sanitize_filename(value: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower()).strip("-")
    return sanitized[:64] or "verification"
