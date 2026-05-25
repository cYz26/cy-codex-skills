from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def add_check(checks: list[dict[str, Any]], name: str, ok: bool, detail: str = "") -> None:
    checks.append({"name": name, "ok": bool(ok), "detail": detail})


def marketplace_base(path: Path) -> Path:
    return (path.parent / ".." / "..").resolve()


def asset_exists(plugin_root: Path, value: str | None) -> bool:
    if not value:
        return False
    if value.startswith(("http://", "https://")):
        return True
    return (plugin_root / value).exists()
