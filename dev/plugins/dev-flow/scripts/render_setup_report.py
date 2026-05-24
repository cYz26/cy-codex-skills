#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from workflow_lib import detect_project_mode, render_template, repo_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a setup report without writing workflow files.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    repo = repo_path(args.repo)
    detection = detect_project_mode(repo)
    markdown = render_template(
        "SETUP_REPORT.md.template",
        {
            "project_mode": detection["project_mode"],
            "recommended_flow": detection["recommended_flow"],
            "written": ["No files written by render_setup_report.py"],
            "skipped": ["Not applicable"],
            "risks": ["This is a report-only command."],
            "next_action": "Run scaffold_workflow.py when ready.",
        },
    )
    if args.json:
        print(json.dumps({"report": markdown, "detection": detection}, indent=2))
    else:
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
