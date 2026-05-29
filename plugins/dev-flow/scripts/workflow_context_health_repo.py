from __future__ import annotations

from pathlib import Path
from typing import Any

from workflow_git import run_git
from workflow_paths import rel


def collect_repo_truth(repo: Path) -> dict[str, Any]:
    status = run_git(repo, "status", "--short")
    diff_name_only = run_git(repo, "diff", "--name-only")
    changed_files = status_files(status)
    return {
        "branch": run_git(repo, "branch", "--show-current") or "no-git",
        "status_short": status,
        "changed_files": changed_files,
        "diff_files": [line for line in diff_name_only.splitlines() if line],
        "diff_stat": run_git(repo, "diff", "--stat"),
        "diff_numstat": run_git(repo, "diff", "--numstat"),
        "diff_file_count": len(changed_files),
        "production_like_changed_files": [
            path for path in changed_files if production_like_path(path)
        ],
    }


def status_files(status: str) -> list[str]:
    files: list[str] = []
    for line in status.splitlines():
        if not line:
            continue
        files.append(line[3:] if len(line) > 3 else line.strip())
    return sorted(set(files))


def production_like_path(path: str) -> bool:
    ignored_prefixes = (
        ".planning/",
        "openspec/",
        "docs/",
        "tests/",
        "test/",
        ".dev-flow/",
    )
    if path.startswith(ignored_prefixes):
        return False
    suffix = Path(path).suffix
    return suffix in {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".go",
        ".rs",
        ".java",
        ".swift",
        ".kt",
        ".gd",
    }


def collect_workflow_truth(repo: Path, state: dict[str, Any]) -> dict[str, Any]:
    verification_dir = repo / ".planning" / "verification"
    checkpoints_dir = repo / ".planning" / "checkpoints"
    reports_dir = repo / ".planning" / "context-health" / "reports"
    change_id = state.get("current_change", {}).get("id", "none")
    change_root = repo / "openspec" / "changes" / str(change_id)
    return {
        "current_stage": state.get("current_stage", "unknown"),
        "current_change": change_id,
        "current_phase": state.get("current_phase", {}).get("id", "none"),
        "compact_status": state.get("context_management", {}).get(
            "compact_status",
            "unknown",
        ),
        "last_checkpoint": state.get("context_management", {}).get(
            "last_checkpoint_file",
            "none",
        ),
        "verification_records": rel_glob(repo, verification_dir, "*.md"),
        "checkpoints": rel_glob(repo, checkpoints_dir, "*.md"),
        "health_reports": rel_glob(repo, reports_dir, "*.json"),
        "openspec_change_exists": change_root.exists(),
        "openspec_tasks_exists": (change_root / "tasks.md").exists(),
    }


def rel_glob(repo: Path, directory: Path, pattern: str) -> list[str]:
    if not directory.exists():
        return []
    return sorted(rel(repo, path) for path in directory.glob(pattern))
