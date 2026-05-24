from __future__ import annotations

import json
from pathlib import Path


def detect_commands(repo: Path) -> list[str]:
    commands = package_commands(repo)
    if (repo / "pyproject.toml").exists() or (repo / "pytest.ini").exists() or (repo / "tests").exists():
        commands.append("python3 -m pytest")
    if (repo / "go.mod").exists():
        commands.append("go test ./...")
    if (repo / "Cargo.toml").exists():
        commands.append("cargo test")
    if (repo / "Makefile").exists():
        commands.append("make test")
    return sorted(dict.fromkeys(commands))


def package_commands(repo: Path) -> list[str]:
    package = repo / "package.json"
    if not package.exists():
        return []
    try:
        scripts = json.loads(package.read_text()).get("scripts", {})
    except json.JSONDecodeError:
        return []
    return [f"npm run {name}" for name in ("test", "lint", "typecheck", "build") if name in scripts]
