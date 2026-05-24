from __future__ import annotations

from pathlib import Path

from workflow_context_platform import add_platform_signals


def project_signals(repo: Path | None) -> list[str]:
    if repo is None:
        return []
    signals: set[str] = set()
    add_package_signals(repo, signals)
    add_file_signals(repo, signals)
    return sorted(signals)


def add_package_signals(repo: Path, signals: set[str]) -> None:
    package_json = repo / "package.json"
    if not package_json.exists():
        return
    signals.add("javascript")
    text = package_json.read_text(errors="ignore").lower()
    if "react" in text:
        signals.add("react")
    if "next" in text:
        signals.add("nextjs")


def add_file_signals(repo: Path, signals: set[str]) -> None:
    if (repo / "pyproject.toml").exists() or (repo / "requirements.txt").exists():
        signals.add("python")
    if (repo / "go.mod").exists():
        signals.add("go")
    if (repo / "Cargo.toml").exists():
        signals.add("rust")
    if (repo / "Package.swift").exists():
        signals.add("swift")
    add_platform_signals(repo, signals)
