from __future__ import annotations

from pathlib import Path
from typing import Any


def skill_report(plugin_root: Path) -> dict[str, Any]:
    skill_root = plugin_root / "skills"
    names = skill_names(skill_root)
    invalid: list[str] = []
    for name in names:
        inspect_skill(skill_root, name, invalid)
    return {"count": len(names), "names": names, "invalid": invalid}


def skill_names(skill_root: Path) -> list[str]:
    if not skill_root.exists():
        return []
    return sorted(path.name for path in skill_root.iterdir() if path.is_dir())


def inspect_skill(skill_root: Path, name: str, invalid: list[str]) -> None:
    skill_file = skill_root / name / "SKILL.md"
    if not skill_file.exists():
        invalid.append(f"{name}: missing SKILL.md")
        return
    text = skill_file.read_text()
    frontmatter = text.split("---", 2)[1] if text.startswith("---") else ""
    if not text.startswith("---\n"):
        invalid.append(f"{name}: missing frontmatter")
    if f"name: {name}" not in text:
        invalid.append(f"{name}: missing matching name")
    if "description:" not in frontmatter:
        invalid.append(f"{name}: missing description")
