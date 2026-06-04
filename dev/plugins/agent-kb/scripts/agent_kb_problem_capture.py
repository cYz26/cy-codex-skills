from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from agent_kb_event_security import now_iso
from workflow_paths import rel, repo_path, sanitize_filename


PROBLEM_SIGNAL_DIR = "_agent/problem-signals"


def sanitize_project(value: str):
    return sanitize_filename(value).replace(".", "-") or "knowledge-base"


def reflection_draft_dir(project: str):
    return f"projects/{sanitize_project(project)}/proposed-changes/problem-reflections"


def problem_capture_defaults(project: str):
    project = sanitize_project(project)
    return {
        "enabled": True,
        "auto_capture": True,
        "manual_records": True,
        "problem_signals": PROBLEM_SIGNAL_DIR,
        "reflection_drafts": reflection_draft_dir(project),
        "review_skill": "kb-reflect",
        "promotion_skill": "kb-promote",
    }


def normalize_problem_capture(config: dict[str, Any], project: str):
    defaults = problem_capture_defaults(project)
    current = config.get("problem_capture")
    if not isinstance(current, dict):
        current = {}
    merged = {**defaults, **current}
    merged["problem_signals"] = current_or_default(current, defaults, "problem_signals")
    merged["reflection_drafts"] = current_or_default(current, defaults, "reflection_drafts")
    return merged


def current_or_default(current: dict[str, Any], defaults: dict[str, Any], key: str):
    value = current.get(key)
    return defaults[key] if not value else value


def problem_capture_enabled(config: dict[str, Any], key: str = "enabled"):
    capture = config.get("problem_capture")
    if not isinstance(capture, dict):
        return False
    return capture.get("enabled") is True and capture.get(key) is True


def record_problem_signal(vault: Path, project: str, config: dict[str, Any], event: dict[str, Any]):
    if not problem_capture_enabled(config, "auto_capture"):
        return {"recorded": False, "reason": "problem_capture_disabled"}
    if event.get("event_type") != "post_tool_use":
        return {"recorded": False, "reason": "event_type_not_captured"}
    if event.get("status") != "fail":
        return {"recorded": False, "reason": "status_not_failed"}

    vault = repo_path(vault)
    project = sanitize_project(project)
    capture = normalize_problem_capture(config, project)
    path = vault / capture["problem_signals"] / f"session-{date.today().isoformat()}.jsonl"
    signal = problem_signal_from_event(project, event)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{json.dumps(signal, sort_keys=True)}\n")
    return {"recorded": True, "path": rel(vault, path), "project": project}


def problem_signal_from_event(project: str, event: dict[str, Any]):
    allowed = (
        "command_hash",
        "command_redacted",
        "command_category",
        "output_bytes",
        "output_lines",
        "output_hash",
    )
    signal = {
        "schema": 1,
        "type": "problem-signal",
        "ts": event.get("ts") or now_iso(),
        "project": project,
        "event_type": event.get("event_type"),
        "cwd": event.get("cwd"),
        "tool": event.get("tool"),
        "status": event.get("status"),
        "exit_code": event.get("exit_code"),
        "needs_review": True,
        "review_with": "kb-reflect",
        "promote_with": "kb-promote",
    }
    for key in allowed:
        if key in event:
            signal[key] = event[key]
    return {key: value for key, value in signal.items() if value is not None}


def record_manual_problem(
    repo: Path,
    config: dict[str, Any],
    *,
    incident: str,
    evidence: str = "",
    root_cause: str = "",
    lesson: str = "",
    prevention: str = "",
    validation: str = "",
    residual_risk: str = "",
):
    repo = repo_path(repo)
    vault = repo_path(config["vault"])
    project = sanitize_project(str(config.get("project") or "knowledge-base"))
    if not problem_capture_enabled(config, "manual_records"):
        return {"ok": False, "recorded": False, "reason": "manual_records_disabled"}

    capture = normalize_problem_capture(config, project)
    slug = sanitize_filename(incident)[:48]
    stamp = now_iso().replace(":", "").replace("+", "-").replace(".", "-")
    path = vault / capture["reflection_drafts"] / f"{stamp}-{slug}.md"
    content = manual_problem_markdown(
        project,
        incident=incident,
        evidence=evidence,
        root_cause=root_cause,
        lesson=lesson,
        prevention=prevention,
        validation=validation,
        residual_risk=residual_risk,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {
        "ok": True,
        "recorded": True,
        "needs_review": True,
        "project": project,
        "path": rel(vault, path),
    }


def manual_problem_markdown(
    project: str,
    *,
    incident: str,
    evidence: str,
    root_cause: str,
    lesson: str,
    prevention: str,
    validation: str,
    residual_risk: str,
):
    created = now_iso()
    return (
        "---\n"
        "type: problem-reflection-draft\n"
        f"project: {project}\n"
        "status: proposed\n"
        "confidence: medium\n"
        "agent_readable: true\n"
        "agent_writable: true\n"
        "needs_review: true\n"
        "source: manual\n"
        f"created: {created}\n"
        "---\n\n"
        "# Problem Reflection Draft\n\n"
        "Review this draft with `kb-reflect` before promoting any durable lesson.\n\n"
        "## Incident\n\n"
        f"{field_or_placeholder(incident)}\n\n"
        "## Evidence\n\n"
        f"{field_or_placeholder(evidence)}\n\n"
        "## Root Cause\n\n"
        f"{field_or_placeholder(root_cause)}\n\n"
        "## Generalized Lesson\n\n"
        f"{field_or_placeholder(lesson)}\n\n"
        "## Prevention Mechanism\n\n"
        f"{field_or_placeholder(prevention)}\n\n"
        "## Validation\n\n"
        f"{field_or_placeholder(validation)}\n\n"
        "## Residual Risk\n\n"
        f"{field_or_placeholder(residual_risk)}\n"
    )


def field_or_placeholder(value: str):
    text = value.strip()
    return text if text else "TBD during kb-reflect review."
