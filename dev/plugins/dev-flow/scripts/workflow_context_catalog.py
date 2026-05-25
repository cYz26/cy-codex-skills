from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any


def source_tools(source_catalogs: list[Path], source_urls: list[str]) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for catalog in source_catalogs:
        tools.extend(read_catalog(Path(catalog), str(catalog)))
    for url in source_urls:
        tools.extend(read_url_catalog(url))
    return tools


def read_catalog(path: Path, source: str) -> list[dict[str, Any]]:
    if not path.exists():
        return [{"source": source, "error": "missing"}]
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return [{"source": source, "error": str(exc)}]
    return normalize_catalog_tools(data, source)


def read_url_catalog(url: str) -> list[dict[str, Any]]:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # pragma: no cover - network failure shape varies.
        return [{"source": url, "error": str(exc)}]
    return normalize_catalog_tools(data, url)


def normalize_catalog_tools(data: dict[str, Any], source: str) -> list[dict[str, Any]]:
    tools = []
    for plugin in data.get("plugins", []):
        tools.append(
            {
                "source": source,
                "type": "plugin",
                "name": plugin.get("name", ""),
                "description": plugin.get("description", ""),
            }
        )
    return tools
