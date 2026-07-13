from __future__ import annotations

from pathlib import Path
from typing import Any

from workflow_detect import build_codebase_docs, detect_commands, source_areas
from workflow_planning_paths import atomic_write_devflow, codebase_root, guard_devflow_write
from workflow_paths import rel, repo_path


def inspect_repo(repo: Path, output: Path | None = None, dry_run: bool = False) -> dict[str, Any]:
    repo = repo_path(repo)
    output = output.resolve() if output else codebase_root(repo)
    guard_devflow_write(repo, output / "inspection.md")
    docs = build_codebase_docs(repo)
    written = []
    for filename, content in docs.items():
        path = output / filename
        written.append(rel(repo, path))
        if not dry_run:
            atomic_write_devflow(repo, path, content)
    return {
        "dry_run": dry_run,
        "output": rel(repo, output),
        "written": written,
        "commands": detect_commands(repo),
        "source_areas": source_areas(repo),
    }
