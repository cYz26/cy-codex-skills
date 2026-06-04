from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_kb_constants import (
    AGENT_KB_CONFIG_PATH,
    LEGACY_AGENT_KB_CONFIG_PATH,
    LEGACY_OBSIDIAN_CONFIG_PATH,
)
from workflow_paths import repo_path


def discover_agent_kb_config(repo: Path):
    repo = repo_path(repo)
    for path in config_candidates(repo):
        config = read_normalized_config(path)
        if config:
            return config
    return None


def config_candidates(repo: Path):
    return [
        repo / AGENT_KB_CONFIG_PATH,
        repo / LEGACY_AGENT_KB_CONFIG_PATH,
        repo / LEGACY_OBSIDIAN_CONFIG_PATH,
    ]


def read_normalized_config(path: Path):
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return normalize_kb_config(data)


def normalize_kb_config(data: dict[str, Any]):
    section = config_section(data)
    if section.get("enabled") is False:
        return None
    vault = vault_value(section)
    if not isinstance(vault, str) or not vault:
        return None
    return {
        "vault": vault,
        "project": section.get("project") or section.get("name") or "knowledge-base",
        "problem_capture": section.get("problem_capture") if isinstance(section.get("problem_capture"), dict) else {},
    }


def config_section(data: dict[str, Any]):
    if isinstance(data.get("agent_kb"), dict):
        return data["agent_kb"]
    if isinstance(data.get("obsidian_kb"), dict):
        return data["obsidian_kb"]
    return data


def vault_value(section: dict[str, Any]):
    keys = ("vault", "vault_path", "markdown_vault", "obsidian_vault")
    return next((section.get(key) for key in keys if section.get(key)), None)
