from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from agent_kb_constants import AGENT_KB_CONFIG_PATH
from agent_kb_templates import scaffold_files, vault_directories, write_scaffold_file
from workflow_paths import rel, repo_path, write_json


def scaffold_agent_kb(
    repo: Path,
    vault: Path,
    project: str,
    owner: str = "owner",
    force: bool = False,
):
    repo = repo_path(repo)
    vault = repo_path(vault)
    project = sanitize_project(project)
    today = date.today().isoformat()
    result = scaffold_result(repo, vault, project)

    for directory in vault_directories(project):
        path = vault / directory
        path.mkdir(parents=True, exist_ok=True)
        result["directories"].append(directory)

    values = {"project": project, "owner": owner, "today": today}
    for relative, content in scaffold_files(values).items():
        status = write_scaffold_file(vault / relative, content, force=force)
        result[status].append(relative)

    configure_repo(repo, vault, project, force, result)
    return result


def scaffold_result(repo: Path, vault: Path, project: str):
    return {
        "ok": True,
        "project": project,
        "vault": str(vault),
        "repo": str(repo),
        "written": [],
        "skipped": [],
        "directories": [],
        "configured": False,
    }


def configure_repo(
    repo: Path,
    vault: Path,
    project: str,
    force: bool,
    result: dict[str, Any],
):
    config_path = repo / AGENT_KB_CONFIG_PATH
    result["config"] = rel(repo, config_path)
    result["configured"] = True
    if force or not config_path.exists():
        write_json(config_path, kb_config(vault, project))
    else:
        result["skipped"].append(result["config"])


def kb_config(vault: Path, project: str):
    return {
        "enabled": True,
        "schema_version": 2,
        "vault": str(vault),
        "project": project,
        "vault_profile": "personal-first",
        "storage_adapter": "markdown-filesystem",
        "editor_profile": "obsidian-compatible-markdown",
        "editor_adapter": "obsidian-cli",
        "agent_adapter": "codex",
        "context_pack": f"projects/{project}/context-pack.md",
        "index": "_system/indexes/home.md",
        "knowledge_index": "_system/indexes/knowledge-index.md",
        "project_index": "projects/_project-index.md",
        "obsidian_cli": {
            "mode": "auto",
            "command": "obsidian",
            "fallback_command": "/Applications/Obsidian.app/Contents/MacOS/obsidian-cli",
            "require_running_app": True,
        },
    }


def sanitize_project(value: str):
    from workflow_paths import sanitize_filename

    return sanitize_filename(value).replace(".", "-") or "knowledge-base"
