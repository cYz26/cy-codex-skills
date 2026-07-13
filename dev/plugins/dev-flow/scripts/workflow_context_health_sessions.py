from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from workflow_context_health_events import read_events, record_event
from workflow_planning_paths import context_health_root
from workflow_paths import repo_path


def import_codex_sessions(repo: Path, codex_home: Path) -> dict[str, Any]:
    repo = repo_path(repo)
    codex_home = Path(codex_home).expanduser().resolve()
    imported = 0
    scanned = 0
    for path in codex_session_candidates(codex_home):
        scanned += 1
        for payload in read_jsonl(path):
            if not payload_matches_repo(repo, payload):
                continue
            event_type = str(
                payload.get("event_type")
                or payload.get("type")
                or "imported_session_event"
            )
            record_event(repo, event_type, payload, imported=True)
            imported += 1
    return {
        "ok": True,
        "source": "codex_session_log",
        "coverage": "partial",
        "confidence": "low",
        "scanned_files": scanned,
        "imported_events": imported,
        "missing": [
            "exact_context_usage",
            "prompt_attribution",
            "tool_schema_tokens",
        ],
    }


def codex_session_candidates(codex_home: Path) -> list[Path]:
    candidates = []
    sessions = codex_home / "sessions"
    if sessions.exists():
        candidates.extend(sorted(sessions.rglob("*.jsonl")))
    for name in ("history.jsonl", "log/codex-tui.log"):
        path = codex_home / name
        if path.exists():
            candidates.append(path)
    return candidates


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            items.append(payload)
    return items


def payload_matches_repo(repo: Path, payload: dict[str, Any]) -> bool:
    cwd = payload.get("cwd") or payload.get("working_directory")
    if not isinstance(cwd, str):
        return False
    try:
        path = Path(cwd).expanduser().resolve()
        path.relative_to(repo)
        return True
    except Exception:
        return Path(cwd).expanduser().resolve() == repo


def context_health_history(repo: Path) -> dict[str, Any]:
    repo = repo_path(repo)
    events = read_events(repo) + read_events(repo, imported=True)
    return {
        "ok": True,
        "event_count": len(events),
        "report_risks": read_report_risks(repo),
        "coverage": "partial" if events else "none",
        "confidence": "medium" if events else "low",
    }


def read_report_risks(repo: Path) -> dict[str, int]:
    risks: Counter[str] = Counter()
    reports_root = context_health_root(repo) / "reports"
    if not reports_root.exists():
        return {}
    for report_path in reports_root.glob("*.json"):
        try:
            report = json.loads(report_path.read_text())
        except json.JSONDecodeError:
            continue
        risks[str(report.get("risk", "unknown"))] += 1
    return dict(risks)
