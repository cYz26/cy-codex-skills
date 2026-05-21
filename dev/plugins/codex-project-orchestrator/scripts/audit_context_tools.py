#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from workflow_context_tools import audit_context_tools


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit global and project-local Codex plugins and skills.")
    parser.add_argument("--repo", help="Target repo used for project-local skill and relevance analysis.")
    parser.add_argument("--codex-home", default=str(Path.home() / ".codex"))
    parser.add_argument("--config", help="Codex config path. Defaults to <codex-home>/config.toml.")
    parser.add_argument("--source-catalog", action="append", default=[], help="Local marketplace/catalog JSON to inspect.")
    parser.add_argument("--source-url", action="append", default=[], help="Explicit remote marketplace/catalog JSON URL.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = audit_context_tools(
        codex_home=Path(args.codex_home),
        repo=Path(args.repo) if args.repo else None,
        config_path=Path(args.config) if args.config else None,
        source_catalogs=[Path(path) for path in args.source_catalog],
        source_urls=args.source_url,
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_text_report(report)
    return 0 if report["ok"] else 1


def print_text_report(report: dict) -> None:
    print(f"Context pressure: {report['contextPressure']}")
    print(f"Codex home: {report['codexHome']}")
    if report.get("repo"):
        print(f"Repo: {report['repo']}")
    if report["projectSignals"]:
        print("Project signals: " + ", ".join(report["projectSignals"]))
    print("\nFindings:")
    for finding in report["findings"] or [{"message": "No global context pressure detected."}]:
        print(f"- {finding['message']}")
    print("\nRecommendations:")
    for recommendation in report["recommendations"] or [{"title": "No recommendations.", "reason": ""}]:
        suffix = f" {recommendation['reason']}" if recommendation.get("reason") else ""
        print(f"- {recommendation['title']}.{suffix}")
    print("\nActions:")
    for action in report["actions"] or [{"id": "none", "title": "No actions available"}]:
        print(f"- {action['id']}: {action['title']}")


if __name__ == "__main__":
    raise SystemExit(main())
