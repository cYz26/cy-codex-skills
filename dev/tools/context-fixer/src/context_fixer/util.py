from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any


def approx_tokens(text_or_size: str | int | None) -> int:
    if text_or_size is None:
        return 0
    size = len(text_or_size) if isinstance(text_or_size, str) else int(text_or_size)
    if size <= 0:
        return 0
    return max(1, math.ceil(size / 4))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def json_size(value: Any) -> int:
    try:
        return len(json.dumps(value, ensure_ascii=False, sort_keys=True))
    except TypeError:
        return len(str(value))


def safe_rel(path: Path, root: Path | None) -> str:
    if root is None:
        return str(path)
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = read_text(path)
    try:
        import tomllib

        return tomllib.loads(text)
    except ModuleNotFoundError:
        try:
            import tomli

            return tomli.loads(text)
        except ModuleNotFoundError:
            return parse_basic_toml(text)


def parse_basic_toml(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current: dict[str, Any] = data
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            header = line.strip("[]")
            array = header.startswith("[") and header.endswith("]")
            header = header.strip("[]")
            current = data
            for part in split_header(header):
                current = current.setdefault(part, {})
            if array:
                current.clear()
            continue
        if "=" not in line:
            continue
        key, value = [part.strip() for part in line.split("=", 1)]
        current[key] = parse_basic_value(value)
    return data


def split_header(header: str) -> list[str]:
    parts: list[str] = []
    buf = ""
    quoted = False
    for char in header:
        if char == '"':
            quoted = not quoted
            continue
        if char == "." and not quoted:
            if buf:
                parts.append(buf)
                buf = ""
            continue
        buf += char
    if buf:
        parts.append(buf)
    return parts


def parse_basic_value(value: str) -> Any:
    value = value.strip()
    if value in {"true", "false"}:
        return value == "true"
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [parse_basic_value(part.strip()) for part in inner.split(",")]
    try:
        return int(value)
    except ValueError:
        return value
