from __future__ import annotations

import subprocess
from pathlib import Path


def git_branch(repo: Path) -> str:
    result = run_git(repo, "branch", "--show-current")
    return result or "no-git"


def git_changed_files(repo: Path) -> str:
    result = run_git(repo, "status", "--short")
    if not result:
        return "  - none"
    return "\n".join(f"  - {line}" for line in result.splitlines())


def run_git(repo: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            text=True,
            capture_output=True,
            check=False,
            timeout=3,
        )
    except Exception:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""
