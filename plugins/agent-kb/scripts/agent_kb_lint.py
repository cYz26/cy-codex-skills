from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_kb_lint_rules import (
    context_pack_findings,
    frontmatter_findings,
    missing_core_file_findings,
    raw_source_findings,
)
from agent_kb_personal_lint import (
    active_archive_reference_findings,
    capture_backlog_findings,
    needs_review_findings,
    promotion_backlog_findings,
)
from agent_kb_markdown import write_lint_report
from agent_kb_scaffold import sanitize_project
from workflow_paths import rel, repo_path


def lint_agent_kb(
    vault: Path,
    project: str,
    write_report: bool = False,
    max_context_words: int = 1200,
    stale_context_days: int = 30,
    raw_stale_days: int = 30,
):
    vault = repo_path(vault)
    project = sanitize_project(project)
    context_pack = vault / "projects" / project / "context-pack.md"
    findings = collect_findings(vault, project, max_context_words, stale_context_days, raw_stale_days)
    report = lint_report(vault, project, context_pack, findings)
    if write_report:
        report_path = write_lint_report(vault, project, findings)
        report["report_path"] = rel(vault, report_path)
    return report


def collect_findings(
    vault: Path,
    project: str,
    max_context_words: int,
    stale_context_days: int,
    raw_stale_days: int,
):
    findings: list[dict[str, str]] = []
    findings.extend(missing_core_file_findings(vault, project))
    findings.extend(frontmatter_findings(vault))
    findings.extend(
        context_pack_findings(
            vault,
            project,
            max_context_words=max_context_words,
            stale_context_days=stale_context_days,
        )
    )
    findings.extend(raw_source_findings(vault, raw_stale_days))
    findings.extend(capture_backlog_findings(vault, raw_stale_days))
    findings.extend(promotion_backlog_findings(vault, raw_stale_days))
    findings.extend(needs_review_findings(vault))
    findings.extend(active_archive_reference_findings(vault))
    return findings


def lint_report(vault: Path, project: str, context_pack: Path, findings: list[dict[str, str]]):
    blocking = sum(1 for item in findings if item["severity"] == "blocking")
    report: dict[str, Any] = {
        "ok": blocking == 0,
        "project": project,
        "vault": str(vault),
        "context_pack": rel(vault, context_pack),
        "finding_count": len(findings),
        "blocking_findings": blocking,
        "findings": findings,
    }
    return report
