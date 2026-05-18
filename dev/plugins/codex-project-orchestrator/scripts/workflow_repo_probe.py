from __future__ import annotations

import re
import subprocess
from pathlib import Path

from workflow_constants import CODE_EXTENSIONS, SOURCE_DIRS, TEST_DIRS


def has_code_file(path: Path) -> bool:
    return all((path.is_file(), path.suffix in CODE_EXTENSIONS, "node_modules" not in path.parts))


def contains_code(repo: Path) -> bool:
    for dirname in SOURCE_DIRS:
        root = repo / dirname
        if root.exists() and any(has_code_file(path) for path in root.rglob("*")):
            return True
    return any(has_code_file(path) for path in repo.glob("*.py"))


def contains_tests(repo: Path) -> bool:
    for dirname in TEST_DIRS:
        root = repo / dirname
        if root.exists() and any(path.is_file() for path in root.rglob("*")):
            return True
    return any(test_like(path) for path in repo.rglob("*") if path.is_file())


def test_like(path: Path) -> bool:
    return bool(re.search(r"(test|spec)", path.name, re.IGNORECASE))


def git_commit_count(repo: Path) -> int:
    if not (repo / ".git").exists():
        return 0
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "rev-list", "--count", "HEAD"],
            text=True,
            capture_output=True,
            check=False,
            timeout=3,
        )
    except Exception:
        return 0
    return parse_commit_count(result.stdout) if result.returncode == 0 else 0


def parse_commit_count(value: str) -> int:
    try:
        return int(value.strip())
    except ValueError:
        return 0
