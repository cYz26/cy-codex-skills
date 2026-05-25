from __future__ import annotations

from pathlib import Path


def add_platform_signals(repo: Path, signals: set[str]) -> None:
    if list(repo.glob("*.xcodeproj")) or list(repo.glob("*.xcworkspace")):
        signals.update({"swift", "ios"})
    if (repo / "project.godot").exists():
        signals.add("godot")
    if (repo / "settings.gradle").exists() or (repo / "settings.gradle.kts").exists():
        signals.add("android")
