from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from workflow_constants import resolve_plugin_root


def default_plugin_root() -> Path:
    return resolve_plugin_root(__file__)


def routing_matrix_path(plugin_root: Path | None = None) -> Path:
    root = plugin_root or default_plugin_root()
    return root / "docs" / "routing.matrix.json"


def load_routing_matrix(plugin_root: Path | None = None) -> dict[str, Any]:
    path = routing_matrix_path(plugin_root)
    data = json.loads(path.read_text())
    data["sourcePath"] = str(path)
    return data


def full_openspec_kinds(plugin_root: Path | None = None) -> set[str]:
    matrix = load_routing_matrix(plugin_root)
    for route in matrix.get("routes", []):
        if route.get("id") == "mandatory-full-openspec":
            return set(route.get("kinds", []))
    return set()


def low_risk_kinds(plugin_root: Path | None = None) -> set[str]:
    matrix = load_routing_matrix(plugin_root)
    for route in matrix.get("routes", []):
        if route.get("id") == "lightweight-ledger-low-risk":
            return set(route.get("kinds", []))
    return set()
