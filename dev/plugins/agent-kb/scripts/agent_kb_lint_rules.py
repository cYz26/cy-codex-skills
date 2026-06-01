from __future__ import annotations

from datetime import datetime
from pathlib import Path

from agent_kb_constants import REQUIRED_FRONTMATTER_FIELDS
from agent_kb_markdown import (
    finding,
    formal_notes,
    frontmatter_fields,
    has_frontmatter,
    relative_note,
    word_count,
)
from agent_kb_templates import required_core_files


def missing_core_file_findings(vault: Path, project: str):
    findings: list[dict[str, str]] = []
    personal_first = is_personal_first_vault(vault)
    for relative in required_core_files(project, personal_first=personal_first):
        if not (vault / relative).exists():
            findings.append(finding("missing-core-file", relative, "blocking", "Required KB file is missing."))
    return findings


def is_personal_first_vault(vault: Path):
    return (vault / "_system").exists() or (vault / "knowledge").exists()


def frontmatter_findings(vault: Path):
    findings: list[dict[str, str]] = []
    for note_path in formal_notes(vault):
        findings.extend(note_frontmatter_findings(vault, note_path))
    return findings


def note_frontmatter_findings(vault: Path, note_path: Path):
    relative = relative_note(vault, note_path)
    text = note_path.read_text(encoding="utf-8")
    if not has_frontmatter(text):
        return [finding("missing-frontmatter", relative, "blocking", "Formal note is missing YAML frontmatter.")]
    return missing_field_findings(relative, frontmatter_fields(text))


def missing_field_findings(relative: str, fields: set[str]):
    findings: list[dict[str, str]] = []
    for required in REQUIRED_FRONTMATTER_FIELDS:
        if required not in fields:
            findings.append(
                finding(
                    "missing-frontmatter-field",
                    relative,
                    "blocking",
                    f"Formal note frontmatter is missing `{required}`.",
                )
            )
    return findings


def context_pack_findings(
    vault: Path,
    project: str,
    *,
    max_context_words: int,
    stale_context_days: int,
):
    findings: list[dict[str, str]] = []
    context_pack = vault / "projects" / project / "context-pack.md"
    if not context_pack.exists():
        return findings
    findings.extend(context_size_findings(vault, context_pack, max_context_words))
    findings.extend(context_staleness_findings(vault, context_pack, stale_context_days))
    return findings


def context_size_findings(vault: Path, context_pack: Path, max_context_words: int):
    words = word_count(context_pack.read_text(encoding="utf-8"))
    if words <= max_context_words:
        return []
    return [
        finding(
            "context-pack-oversized",
            relative_note(vault, context_pack),
            "warning",
            f"Context pack has {words} words; compact it below {max_context_words}.",
        )
    ]


def context_staleness_findings(vault: Path, context_pack: Path, stale_context_days: int):
    age_days = file_age_days(context_pack)
    if age_days <= stale_context_days:
        return []
    return [
        finding(
            "context-pack-stale",
            relative_note(vault, context_pack),
            "warning",
            f"Context pack has not been updated for {int(age_days)} days.",
        )
    ]


def raw_source_findings(vault: Path, raw_stale_days: int):
    raw_root = vault / "raw"
    if not raw_root.exists():
        return []
    return [
        stale_raw_source_finding(vault, path)
        for path in raw_root.rglob("*")
        if is_stale_raw_source(path, raw_stale_days)
    ]


def is_stale_raw_source(path: Path, raw_stale_days: int):
    return all((path.is_file(), path.name != ".gitkeep", file_age_days(path) > raw_stale_days))


def stale_raw_source_finding(vault: Path, path: Path):
    return finding(
        "raw-source-unprocessed",
        relative_note(vault, path),
        "warning",
        f"Raw source has been present for {int(file_age_days(path))} days.",
    )


def file_age_days(path: Path):
    return (datetime.now().timestamp() - path.stat().st_mtime) / 86400
