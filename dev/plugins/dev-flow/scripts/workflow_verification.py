from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from workflow_paths import rel, repo_path, sanitize_filename
from workflow_state import parse_state, update_state


def record_verification(repo: Path, command: str, result: str, notes: str = "") -> dict[str, str]:
    repo = repo_path(repo)
    status = result.lower()
    path = verification_path(repo, command)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(verification_record(command, status, notes))
    append_phase_verification(repo, command, status, path)
    update_state(repo, verification_passed=status == "pass", state_updated=True)
    return {"path": rel(repo, path), "result": status}


def verification_path(repo: Path, command: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return repo / ".planning" / "verification" / f"{timestamp}-{sanitize_filename(command)}.md"


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


def append_phase_verification(repo: Path, command: str, status: str, record_path: Path) -> None:
    state = parse_state(repo)
    phase_id = state.get("current_phase", {}).get("id", "01-foundation")
    phase_file = repo / ".planning" / "phases" / str(phase_id) / "VERIFICATION.md"
    phase_file.parent.mkdir(parents=True, exist_ok=True)
    with phase_file.open("a") as handle:
        handle.write(f"\n- `{command}`: {status} ({rel(repo, record_path)})\n")
