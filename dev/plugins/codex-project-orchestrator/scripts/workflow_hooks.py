from __future__ import annotations

import json
from pathlib import Path

from workflow_constants import CODE_EXTENSIONS, SOURCE_DIRS


def hook_mode(repo: Path) -> str:
    config = repo / ".codex-project-orchestrator.json"
    if not config.exists():
        return "warn"
    try:
        mode = json.loads(config.read_text()).get("hook", {}).get("mode", "warn")
    except json.JSONDecodeError:
        return "warn"
    return mode if mode in {"off", "warn", "block"} else "warn"


def production_like_path(repo: Path, file_path: str | None) -> bool:
    if not file_path:
        return False
    relative = relative_tool_path(repo, file_path)
    parts = relative.parts
    if not parts:
        return False
    if parts[0] in {".planning", "openspec", "docs", "tests", "test"}:
        return False
    if str(relative) in generated_workflow_files():
        return False
    return relative.suffix in CODE_EXTENSIONS or parts[0] in SOURCE_DIRS


def relative_tool_path(repo: Path, file_path: str) -> Path:
    path = Path(file_path)
    try:
        return path.resolve().relative_to(repo)
    except Exception:
        return path


def generated_workflow_files() -> set[str]:
    return {
        "AGENTS.md",
        "README.md",
        "setup-report.md",
        "workflow-diagnosis.md",
        "repair-plan.md",
    }


def hook_response(repo: Path, message: str) -> int:
    mode = hook_mode(repo)
    if mode == "off":
        return 0
    print(message)
    return 1 if mode == "block" else 0
