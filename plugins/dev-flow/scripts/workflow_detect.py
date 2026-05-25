from __future__ import annotations

from pathlib import Path
from typing import Any

from workflow_constants import BUILD_FILES
from workflow_commands import detect_commands
from workflow_paths import repo_path
from workflow_repo_docs import build_codebase_docs, source_areas
from workflow_repo_probe import contains_code, contains_tests, git_commit_count, has_code_file


def detect_project_mode(repo: Path) -> dict[str, Any]:
    repo = repo_path(repo)
    signals = build_signals(repo)
    mode, confidence, flow = classify_project(signals)
    return {
        "project_mode": mode,
        "confidence": confidence,
        "signals": signals,
        "recommended_flow": flow,
    }


def build_signals(repo: Path) -> dict[str, Any]:
    commits = git_commit_count(repo)
    return {
        "has_git_history": (repo / ".git").exists() or commits > 0,
        "git_commit_count": commits,
        "has_source_code": contains_code(repo),
        "has_tests": contains_tests(repo),
        "has_build_config": any((repo / name).exists() for name in BUILD_FILES),
        "has_agents_md": (repo / "AGENTS.md").exists(),
        "has_openspec": (repo / "openspec").exists(),
        "has_planning": (repo / ".planning").exists(),
        "has_readme": readme_exists(repo),
        "has_docs": (repo / "docs").exists(),
    }


def readme_exists(repo: Path) -> bool:
    return any((repo / name).exists() for name in ("README.md", "README", "readme.md"))


def classify_project(signals: dict[str, Any]) -> tuple[str, float, str]:
    if brownfield_code_signals(signals):
        confidence = 0.9 if strong_brownfield(signals) else 0.78
        return "brownfield", confidence, "brownfield-setup"
    if brownfield_safe_signals(signals):
        return "brownfield", 0.56, "brownfield-safe-setup"
    confidence = 0.72 if signals["has_readme"] else 0.86
    return "greenfield", confidence, "greenfield-setup"


def brownfield_code_signals(signals: dict[str, Any]) -> bool:
    keys = ("has_source_code", "has_tests", "has_build_config")
    return any(signals[key] for key in keys)


def strong_brownfield(signals: dict[str, Any]) -> bool:
    keys = ("has_source_code", "has_tests", "has_build_config")
    return sum(bool(signals[key]) for key in keys) >= 2


def brownfield_safe_signals(signals: dict[str, Any]) -> bool:
    keys = ("has_git_history", "has_openspec", "has_planning", "has_docs")
    return any(signals[key] for key in keys)


__all__ = [
    "build_codebase_docs",
    "contains_code",
    "contains_tests",
    "detect_commands",
    "detect_project_mode",
    "git_commit_count",
    "has_code_file",
    "source_areas",
]
