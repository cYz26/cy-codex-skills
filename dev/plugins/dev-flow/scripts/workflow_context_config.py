from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import tomllib  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - depends on runtime Python
    try:
        import tomli as tomllib  # type: ignore[import-not-found]
    except ModuleNotFoundError:  # pragma: no cover - fallback covered through read_config
        tomllib = None


def read_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}
    text = config_path.read_text()
    if tomllib is not None:
        return tomllib.loads(text)
    return parse_minimal_toml(text)


def parse_minimal_toml(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current: dict[str, Any] = data
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[[") and line.endswith("]]"):
            section = line[2:-2].strip()
            current = append_table(data, section)
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            current = table(data, section)
            continue
        if "=" not in line:
            continue
        key, value = [part.strip() for part in line.split("=", 1)]
        current[strip_quotes(key)] = parse_value(value)
    return data


def table(data: dict[str, Any], dotted: str) -> dict[str, Any]:
    current = data
    for part in split_dotted(dotted):
        current = current.setdefault(part, {})
    return current


def append_table(data: dict[str, Any], dotted: str) -> dict[str, Any]:
    parts = split_dotted(dotted)
    current = data
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    entries = current.setdefault(parts[-1], [])
    item: dict[str, Any] = {}
    entries.append(item)
    return item


def split_dotted(value: str) -> list[str]:
    parts: list[str] = []
    current = ""
    in_quotes = False
    for char in value:
        if char == '"':
            in_quotes = not in_quotes
            current += char
        elif char == "." and not in_quotes:
            parts.append(strip_quotes(current.strip()))
            current = ""
        else:
            current += char
    if current:
        parts.append(strip_quotes(current.strip()))
    return parts


def strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return value[1:-1]
    return value


def parse_value(value: str) -> Any:
    value = value.split("#", 1)[0].strip()
    if value in {"true", "false"}:
        return value == "true"
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        return value


def global_plugins(config: dict[str, Any]) -> list[dict[str, Any]]:
    plugins = []
    for key, settings in sorted(config.get("plugins", {}).items()):
        plugins.append(
            {
                "key": key,
                "name": plugin_name(key),
                "enabled": settings.get("enabled") is True,
                "settings": dict(settings),
            }
        )
    return plugins


def disabled_skill_paths(config: dict[str, Any]) -> set[str]:
    disabled = set()
    for entry in config.get("skills", {}).get("config", []):
        if entry.get("enabled") is False and entry.get("path"):
            disabled.add(str(entry["path"]))
    return disabled


def plugin_name(key: str) -> str:
    return key.split("@", 1)[0]
