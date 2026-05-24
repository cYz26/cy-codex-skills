from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from workflow_paths import repo_path
from workflow_project_skill_install import ensure_project_local_skills


def activate_project_dependencies(
    repo: Path,
    dry_run: bool = False,
    skip_official_installs: bool = False,
    plugin_root: Path | None = None,
    codex_home: Path | None = None,
) -> dict[str, Any]:
    repo = repo_path(repo)
    plugin_root = repo_path(plugin_root or Path(__file__).resolve().parents[1])
    codex_home = repo_path(codex_home or Path.home() / ".codex")
    commands = official_install_commands(repo)
    command_results = []
    if not skip_official_installs:
        for command in commands:
            command_results.append(run_command(command, repo, dry_run))
    skills_result = ensure_project_local_skills(repo, plugin_root, codex_home, dry_run)
    return {
        "ok": all(item["ok"] for item in command_results) and skills_result["ok"],
        "repo": str(repo),
        "plugin_root": str(plugin_root),
        "codex_home": str(codex_home),
        "dry_run": dry_run,
        "skip_official_installs": skip_official_installs,
        "commands": command_results,
        "local_skills": skills_result,
    }


def official_install_commands(repo: Path) -> list[list[str]]:
    return [
        ["openspec", "init", "--tools", "codex", str(repo), "--force"],
        ["npx", "-y", "get-shit-done-cc@latest", "--codex", "--local", "--profile=standard"],
    ]


def run_command(command: list[str], repo: Path, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"ok": True, "command": command, "skipped": True}
    try:
        result = subprocess.run(command, cwd=repo, text=True, capture_output=True, check=False)
    except FileNotFoundError:
        return {"ok": False, "command": command, "error": f"missing executable: {command[0]}"}
    return {
        "ok": result.returncode == 0,
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
