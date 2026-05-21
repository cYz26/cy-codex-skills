from __future__ import annotations

from pathlib import Path

from workflow_constants import SOURCE_DIRS
from workflow_commands import detect_commands


def source_areas(repo: Path) -> list[str]:
    areas = []
    for name in SOURCE_DIRS:
        path = repo / name
        if path.exists():
            count = sum(1 for item in path.rglob("*") if item.is_file())
            areas.append(f"{name}/ ({count} files)")
    return areas or ["No source areas detected"]


def build_codebase_docs(repo: Path) -> dict[str, str]:
    commands_doc = ["# Commands", "", *(f"- `{command}`" for command in command_list(repo))]
    return {
        "ARCHITECTURE.md": architecture_doc(repo),
        "CONVENTIONS.md": conventions_doc(),
        "COMMANDS.md": "\n".join(commands_doc) + "\n",
        "RISKS.md": risks_doc(),
    }


def command_list(repo: Path) -> list[str]:
    return detect_commands(repo) or ["No commands detected"]


def architecture_doc(repo: Path) -> str:
    lines = [
        "# Architecture",
        "",
        "Generated brownfield map. Confirm before treating this as source of truth.",
        "",
        "## Source Areas",
        "",
        *[f"- {item}" for item in source_areas(repo)],
    ]
    return "\n".join(lines) + "\n"


def conventions_doc() -> str:
    lines = [
        "# Conventions",
        "",
        "Generated from repository inspection.",
        "",
        "- Prefer existing module boundaries and naming patterns.",
        "- Add characterization tests before risky behavior changes.",
        "- Avoid broad rewrites during ordinary feature work.",
    ]
    return "\n".join(lines) + "\n"


def risks_doc() -> str:
    lines = [
        "# Risks",
        "",
        "- Brownfield behavior may be incomplete until current-system specs are reviewed.",
        "- Existing tests may not cover all compatibility requirements.",
    ]
    return "\n".join(lines) + "\n"
