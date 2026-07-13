from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from workflow_constants import resolve_plugin_root


def default_plugin_root() -> Path:
    return resolve_plugin_root(__file__)


def superpowers_gate_matrix_path(plugin_root: Path | None = None) -> Path:
    root = plugin_root or default_plugin_root()
    return root / "docs" / "superpowers_gate_matrix.json"


def load_superpowers_gate_matrix(plugin_root: Path | None = None) -> dict[str, Any]:
    path = superpowers_gate_matrix_path(plugin_root)
    data = json.loads(path.read_text())
    data["sourcePath"] = str(path)
    return data


def required_gate_ids(plugin_root: Path | None = None) -> list[str]:
    matrix = load_superpowers_gate_matrix(plugin_root)
    return [
        str(gate["id"])
        for gate in matrix.get("gates", [])
        if gate.get("requiredInStrictProfile") is True
    ]
