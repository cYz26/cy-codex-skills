from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from workflow_paths import rel, repo_path, sanitize_filename
from workflow_implementation_readiness import repository_mutation_gate
from workflow_planning_paths import atomic_write_devflow, verification_root
from workflow_state import update_state


def record_verification(repo: Path, command: str, result: str, notes: str = "") -> dict[str, str]:
    repo = repo_path(repo)
    status = result.lower()
    if status == "pass":
        readiness = repository_mutation_gate(repo, ordinary_authority=True)
        if readiness["applicable"] and not readiness["allowed"]:
            return {
                "path": "",
                "result": "blocked",
                "error": "implementation_readiness",
                "nextAction": str(readiness["nextAction"]),
            }
    path = verification_path(repo, command)
    atomic_write_devflow(repo, path, verification_record(command, status, notes))
    update_state(repo, verification_passed=status == "pass", state_updated=True)
    return {"path": rel(repo, path), "result": status}


def verification_path(repo: Path, command: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return verification_root(repo) / f"{timestamp}-{sanitize_filename(command)}.md"


def verification_record(command: str, status: str, notes: str) -> str:
    lines = [
        "# Verification Record",
        "",
        f"- Command: `{command}`",
        f"- Result: `{status}`",
        f"- Recorded: {datetime.now(timezone.utc).isoformat()}",
    ]
    if notes:
        lines.extend(["", "## Notes", "", notes])
    return "\n".join(lines) + "\n"
