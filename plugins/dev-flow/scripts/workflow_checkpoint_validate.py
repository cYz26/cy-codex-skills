from __future__ import annotations

from pathlib import Path
from typing import Any

from workflow_paths import repo_path
from workflow_compact_state import SUPPORTED_COMPACT_STATUSES
from workflow_state import parse_frontmatter, parse_state


CHECKPOINT_REPAIR_GUIDANCE = (
    "Regenerate this checkpoint with create_checkpoint.py or the canonical checkpoint tool before compacting."
)
REQUIRED_FRONTMATTER_KEYS = {
    "checkpoint_id",
    "created_at",
    "boundary",
    "project_mode",
    "phase_id",
    "change_id",
    "compact_recommended",
    "compact_status",
    "next_stage",
}
REQUIRED_SECTIONS = {
    "current_goal": "## Current goal",
    "completed_work": "## Completed work",
    "durable_context_written": "## Durable context written",
    "key_decisions": "## Key decisions",
    "risks": "## Risks",
    "next_action": "## Next action",
}


def validate_checkpoint(repo: Path, checkpoint: str) -> dict[str, Any]:
    repo = repo_path(repo)
    path = repo / checkpoint
    missing: list[str] = []
    if not (repo / ".planning" / "STATE.md").exists():
        missing.append("state")
    if not path.exists():
        return {"valid": False, "missing": ["checkpoint_file"], "compact_allowed": False}
    text = path.read_text()
    frontmatter, _ = parse_frontmatter(text)
    missing.extend(missing_frontmatter(frontmatter))
    missing.extend(missing_sections(text))
    check_active_artifacts(repo, parse_state(repo), missing)
    if frontmatter_value(frontmatter, "boundary") == "verification_passed":
        check_verification_evidence(text, missing)
    missing = sorted(set(missing))
    return {
        "valid": not missing,
        "missing": missing,
        "compact_allowed": not missing,
        "repair": CHECKPOINT_REPAIR_GUIDANCE if missing else "",
    }


def missing_frontmatter(frontmatter: str) -> list[str]:
    if not frontmatter.strip():
        return ["canonical_frontmatter"]
    keys = frontmatter_keys(frontmatter)
    missing = []
    if not REQUIRED_FRONTMATTER_KEYS.issubset(keys):
        missing.append("canonical_frontmatter")
    status = frontmatter_value(frontmatter, "compact_status")
    if status and status not in SUPPORTED_COMPACT_STATUSES:
        missing.append("compact_status")
    return missing


def frontmatter_keys(frontmatter: str) -> set[str]:
    keys = set()
    for line in frontmatter.splitlines():
        if ":" in line and not line.startswith(" "):
            keys.add(line.split(":", 1)[0].strip())
    return keys


def missing_sections(text: str) -> list[str]:
    missing = []
    for key, heading in REQUIRED_SECTIONS.items():
        if not section_has_content(text, heading):
            missing.append(key)
    return missing


def section_has_content(text: str, heading: str) -> bool:
    if heading not in text:
        return False
    start = text.index(heading) + len(heading)
    next_heading = text.find("\n## ", start)
    section = text[start: next_heading if next_heading > -1 else len(text)]
    return bool(section.strip())


def check_active_artifacts(repo: Path, state: dict[str, Any], missing: list[str]) -> None:
    phase_id = state.get("current_phase", {}).get("id")
    change_id = state.get("current_change", {}).get("id")
    if phase_id not in (None, "", "none"):
        phase_root = repo / ".planning" / "phases" / str(phase_id)
        if not any(((phase_root / "PLAN.md").exists(), (phase_root / "SUMMARY.md").exists())):
            missing.append("phase_context")
    if change_id not in (None, "", "none"):
        tasks = repo / "openspec" / "changes" / str(change_id) / "tasks.md"
        if not tasks.exists():
            missing.append("openspec_tasks")


def check_verification_evidence(text: str, missing: list[str]) -> None:
    if not any(result in text for result in ("result: pass", "result: fail")):
        missing.append("verification_evidence")


def frontmatter_value(frontmatter: str, key: str) -> str:
    for line in frontmatter.splitlines():
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip()
    return ""
