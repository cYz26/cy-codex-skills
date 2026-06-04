#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_kb_config import discover_agent_kb_config
from agent_kb_lint import lint_agent_kb
from agent_kb_problem_capture import normalize_problem_capture, problem_capture_defaults
from agent_kb_scaffold import scaffold_agent_kb
from workflow_paths import rel, repo_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure and verify AgentKB project problem capture.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--repo", required=True)
    status_parser.add_argument("--json", action="store_true")

    enable_parser = subparsers.add_parser("enable")
    enable_parser.add_argument("--repo", required=True)
    enable_parser.add_argument("--vault", required=True)
    enable_parser.add_argument("--project", required=True)
    enable_parser.add_argument("--owner", default="owner")
    enable_parser.add_argument("--force", action="store_true")
    enable_parser.add_argument("--json", action="store_true")

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--repo", required=True)
    verify_parser.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if args.command == "status":
        report = project_status(args.repo)
    elif args.command == "enable":
        report = enable_project(args.repo, args.vault, args.project, args.owner, force=args.force)
    else:
        report = verify_project(args.repo)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(human_summary(report))
    return 0


def project_status(repo: str | Path):
    repo = repo_path(repo)
    config = discover_agent_kb_config(repo)
    if not config:
        return {
            "ok": True,
            "configured": False,
            "repo": str(repo),
            "problem_capture": disabled_problem_capture(),
        }
    vault = repo_path(config["vault"])
    project = str(config.get("project") or "knowledge-base")
    capture = normalize_problem_capture(config, project)
    return {
        "ok": True,
        "configured": True,
        "repo": str(repo),
        "vault": str(vault),
        "project": project,
        "problem_capture": capture,
        "paths": required_paths(vault, project, capture),
    }


def enable_project(repo: str | Path, vault: str | Path, project: str, owner: str, *, force: bool = False):
    scaffold = scaffold_agent_kb(repo=repo, vault=vault, project=project, owner=owner, force=force)
    status = project_status(repo)
    return {**status, "scaffold": scaffold}


def verify_project(repo: str | Path):
    status = project_status(repo)
    findings: list[dict[str, str]] = []
    if not status["configured"]:
        return {**status, "ok": False, "findings": [{"rule": "not-configured", "path": str(repo)}]}

    vault = repo_path(status["vault"])
    project = status["project"]
    capture = status["problem_capture"]
    for name, relative in required_paths(vault, project, capture).items():
        if not (vault / relative).exists():
            findings.append({"rule": "missing-path", "name": name, "path": relative})

    lint = lint_agent_kb(vault=vault, project=project)
    if lint.get("blocking_findings", 0):
        findings.append(
            {
                "rule": "lint-blocking-findings",
                "path": rel(vault, vault),
                "count": str(lint["blocking_findings"]),
            }
        )
    return {**status, "ok": not findings, "findings": findings, "lint": lint}


def required_paths(vault: Path, project: str, capture: dict[str, object]):
    defaults = problem_capture_defaults(project)
    return {
        "context_pack": f"projects/{project}/context-pack.md",
        "problem_signals": str(capture.get("problem_signals") or defaults["problem_signals"]),
        "reflection_drafts": str(capture.get("reflection_drafts") or defaults["reflection_drafts"]),
    }


def disabled_problem_capture():
    return {
        "enabled": False,
        "auto_capture": False,
        "manual_records": False,
    }


def human_summary(report: dict[str, object]):
    if not report.get("configured"):
        return "AgentKB is not configured for this repository."
    state = "ok" if report.get("ok") else "needs attention"
    return f"AgentKB project {report.get('project')} is {state}."


if __name__ == "__main__":
    raise SystemExit(main())
