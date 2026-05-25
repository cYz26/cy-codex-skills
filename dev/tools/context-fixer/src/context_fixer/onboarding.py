from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def apply_first_run_dependency_guidance(report: dict[str, Any], repo: Path | None, trace_supplied: bool) -> None:
    if repo is None:
        return
    if trace_supplied:
        mark_guidance_seen(repo)
        return
    if guidance_seen(repo):
        return
    guidance = build_dependency_guidance(repo)
    report["onboarding"] = {"dependency_guidance": guidance}
    report.setdefault("compression", {}).setdefault("recommendations", []).append(guidance_to_recommendation(guidance))
    mark_guidance_seen(repo)


def build_dependency_guidance(repo: Path) -> dict[str, Any]:
    installed_path = shutil.which("claude-tap")
    installed = installed_path is not None
    if installed:
        title = "Capture Codex request traces with claude-tap"
        action = (
            "Run `claude-tap --tap-client codex`, then analyze the captured JSONL with "
            "`context-fixer --repo "
            f"{repo} --trace /path/to/trace_*.jsonl --html .context-fixer/report.html`."
        )
    else:
        title = "Set up optional Codex request tracing"
        action = (
            "Install the optional capture tool with `uv tool install claude-tap`, run "
            "`claude-tap --tap-client codex`, then pass the captured JSONL to "
            "`context-fixer --trace`."
        )
    return {
        "title": title,
        "installed": installed,
        "installed_path": installed_path,
        "install_command": "uv tool install claude-tap",
        "capture_command": "claude-tap --tap-client codex",
        "action": action,
    }


def guidance_to_recommendation(guidance: dict[str, Any]) -> dict[str, str]:
    return {
        "priority": "P2",
        "title": str(guidance["title"]),
        "reason": "This is the first Context Fixer CLI run for this repository and no request trace was supplied.",
        "action": str(guidance["action"]),
    }


def render_trace_required_guidance(repo: Path | None) -> str:
    repo_path = resolve_repo(repo or Path("."))
    guidance = build_dependency_guidance(repo_path)
    lines = [
        "Context Fixer",
        "Request trace required by default",
        "",
        "For the most complete Codex context analysis, capture a request trace first.",
        f"- {guidance['title']}: {guidance['action']}",
        "",
        "To explicitly use lower-confidence session log analysis, rerun with `--session-only`.",
    ]
    return "\n".join(lines)


def guidance_seen(repo: Path) -> bool:
    state = load_state()
    return project_key(repo) in state.get("projects", {})


def mark_guidance_seen(repo: Path) -> None:
    state = load_state()
    projects = state.setdefault("projects", {})
    projects[project_key(repo)] = {
        "repo": str(resolve_repo(repo)),
        "dependency_guidance_seen_at": datetime.now(timezone.utc).isoformat(),
    }
    save_state(state)


def load_state() -> dict[str, Any]:
    path = state_path()
    if not path.exists():
        return {"projects": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"projects": {}}
    return data if isinstance(data, dict) else {"projects": {}}


def save_state(state: dict[str, Any]) -> None:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def state_path() -> Path:
    return cache_root() / "onboarding.json"


def cache_root() -> Path:
    override = os.environ.get("CONTEXT_FIXER_CACHE_HOME")
    if override:
        return Path(override).expanduser()
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg).expanduser() / "context-fixer"
    return Path.home() / ".cache" / "context-fixer"


def project_key(repo: Path) -> str:
    digest = hashlib.sha256(str(resolve_repo(repo)).encode("utf-8")).hexdigest()
    return digest[:24]


def resolve_repo(repo: Path) -> Path:
    try:
        return repo.expanduser().resolve()
    except FileNotFoundError:
        return repo.expanduser().absolute()
