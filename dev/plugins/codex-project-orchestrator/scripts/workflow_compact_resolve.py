from __future__ import annotations

from pathlib import Path
from typing import Any

from workflow_compact_options import clean_text, first_text
from workflow_paths import rel
from workflow_state import parse_state


def resolve_checkpoint(repo: Path, options: dict[str, Any]) -> dict[str, Any]:
    state_context = parse_state(repo).get("context_management", {})
    checkpoint_file = first_text(options.get("checkpoint"), state_context.get("last_checkpoint_file"))
    checkpoint_id = first_text(options.get("checkpoint_id"), state_context.get("last_checkpoint_id"))
    issues: list[str] = []
    path = checkpoint_path(repo, checkpoint_file)
    if path:
        checkpoint_id = path.stem
        checkpoint_file = rel(repo, path)
        if not path.exists():
            issues.append(f"Checkpoint file does not exist: {checkpoint_file}")
    elif checkpoint_id:
        path = checkpoint_candidate(repo, checkpoint_id, issues)
        checkpoint_file = rel(repo, path)
    else:
        issues.append("No checkpoint was provided and STATE.md has no last checkpoint")
    return {
        "checkpoint_id": checkpoint_id,
        "checkpoint_file": checkpoint_file,
        "checkpoint_path": path,
        "issues": issues,
    }


def checkpoint_candidate(repo: Path, checkpoint_id: str, issues: list[str]) -> Path:
    candidate = repo / ".planning" / "checkpoints" / f"{checkpoint_id}.md"
    if not candidate.exists():
        issues.append(f"Checkpoint file does not exist: {rel(repo, candidate)}")
    return candidate


def checkpoint_path(repo: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return repo / path


def raw_compact_result(repo: Path, options: dict[str, Any], issues: list[str]) -> str | None:
    if options.get("raw_result") is not None:
        return str(options["raw_result"])
    result_file = clean_text(options.get("result_file"))
    if not result_file:
        return None
    path = checkpoint_path(repo, result_file)
    if not path:
        issues.append(f"Compact result input file does not exist: {result_file}")
        return None
    if not path.exists():
        issues.append(f"Compact result input file does not exist: {result_file}")
        return None
    return path.read_text()
