from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from agent_kb_constants import FORMAL_NOTE_DIRS
from workflow_paths import rel


def formal_notes(vault: Path):
    notes: list[Path] = []
    for directory in FORMAL_NOTE_DIRS:
        root = vault / directory
        if root.exists():
            notes.extend(path for path in root.rglob("*.md") if path.is_file())
    return sorted(notes)


def has_frontmatter(text: str):
    if not text.startswith("---\n"):
        return False
    return "\n---\n" in text[4:]


def frontmatter_fields(text: str):
    if not has_frontmatter(text):
        return set()
    fields: set[str] = set()
    for raw in text.split("---", 2)[1].splitlines():
        if ":" in raw and not raw.startswith(" "):
            fields.add(raw.split(":", 1)[0].strip())
    return fields


def finding(rule: str, path: str, severity: str, message: str):
    return {"rule": rule, "path": path, "severity": severity, "message": message}


def word_count(text: str):
    return len(re.findall(r"\S+", text))


def write_lint_report(vault: Path, project: str, findings: list[dict[str, str]]):
    today = date.today().isoformat()
    path = vault / "20-projects" / project / "proposed-changes" / f"kb-lint-{today}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# KB Lint Report {today}",
        "",
        f"Project: `{project}`",
        "",
        "## Findings",
        "",
    ]
    if findings:
        for item in findings:
            lines.append(f"- [{item['severity']}] `{item['rule']}` in `{item['path']}`: {item['message']}")
    else:
        lines.append("- No findings.")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def relative_note(vault: Path, path: Path):
    return rel(vault, path)
