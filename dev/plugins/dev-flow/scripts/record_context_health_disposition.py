#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

from workflow_context_health_report import render_markdown_report
from workflow_context_health_subagents import RESOLVED_DISPOSITIONS
from workflow_paths import repo_path, write_json
from workflow_state import parse_state


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Record a disposition for the latest DevFlow context-health subagent recommendation."
    )
    parser.add_argument("--repo", required=True)
    parser.add_argument("--report", help="Context-health report path. Defaults to .planning/STATE.md last_report.")
    parser.add_argument(
        "--recommendation-id",
        help="Expected recommendation id. Defaults to the report recommendation.",
    )
    parser.add_argument(
        "--disposition",
        required=True,
        choices=sorted(RESOLVED_DISPOSITIONS),
        help="Resolved disposition for the recommendation.",
    )
    parser.add_argument("--note", help="Reason/evidence note for the disposition.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    repo = repo_path(args.repo)
    note = (args.note or "").strip()
    if not note:
        return fail("--note is required when recording a resolved recommendation disposition.", args.json)

    report_path = resolve_report_path(repo, args.report)
    if not report_path:
        return fail("No context-health report found. Run context_health_check.py --write-report first.", args.json)
    if not report_path.is_file():
        return fail(f"Context-health report not found: {report_path}", args.json)

    try:
        report = json.loads(report_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return fail(f"Could not read context-health report: {exc}", args.json)

    subagents = report.get("subagents")
    if not isinstance(subagents, dict):
        return fail("Context-health report does not contain a subagents recommendation block.", args.json)
    if not subagents.get("dispositionRequired"):
        return fail("Context-health report has no recommendation that requires disposition.", args.json)

    recommendation_id = str(subagents.get("recommendationId") or "").strip()
    if not recommendation_id or recommendation_id == "none":
        return fail("Context-health report does not contain a recommendation id.", args.json)
    expected_id = (args.recommendation_id or recommendation_id).strip()
    if expected_id != recommendation_id:
        return fail(
            f"Recommendation id mismatch: expected {expected_id}, report contains {recommendation_id}.",
            args.json,
        )

    previous = str(subagents.get("disposition") or "pending")
    subagents["disposition"] = args.disposition
    subagents["dispositionNote"] = note
    subagents["dispositionRecordedAt"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    subagents["nextAction"] = next_action(args.disposition)
    write_json(report_path, report)
    rewrite_markdown_report(report_path, report)

    payload = {
        "ok": True,
        "report_file": report_file_value(repo, report_path),
        "recommendationId": recommendation_id,
        "previousDisposition": previous,
        "disposition": args.disposition,
        "note": note,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"recorded {args.disposition} for {recommendation_id}")
    return 0


def resolve_report_path(repo: Path, report_arg: str | None) -> Path | None:
    if report_arg:
        path = Path(report_arg).expanduser()
        return path if path.is_absolute() else repo / path
    state = parse_state(repo)
    last_report = state.get("context_health", {}).get("last_report")
    if not last_report or last_report == "none":
        return None
    return repo / str(last_report)


def rewrite_markdown_report(report_path: Path, report: dict[str, Any]) -> None:
    if report_path.suffix != ".json":
        return
    markdown_path = report_path.with_suffix(".md")
    if markdown_path.exists():
        markdown_path.write_text(render_markdown_report(report), encoding="utf-8")


def report_file_value(repo: Path, report_path: Path) -> str:
    if is_relative_to(report_path, repo):
        return report_path.relative_to(repo).as_posix()
    return str(report_path)


def next_action(disposition: str) -> str:
    if disposition == "accepted":
        return "Execute or review the accepted Agent Task Contract, then record main-agent verification."
    if disposition == "declined":
        return "Continue only if the decline reason explains why a subagent is not useful."
    if disposition == "superseded":
        return "Continue only if another action has resolved the investigation need."
    if disposition == "blocked":
        return "Wait for the missing user authorization or context before dispatching."
    return "No subagent recommendation needs disposition."


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def fail(message: str, json_output: bool) -> int:
    print(message, file=sys.stderr)
    if json_output:
        print(json.dumps({"ok": False, "error": message}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
