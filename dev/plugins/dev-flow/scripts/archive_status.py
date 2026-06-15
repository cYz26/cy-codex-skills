#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from workflow_archive_policy import archive_status


def main() -> int:
    parser = argparse.ArgumentParser(description="Report DevFlow OpenSpec archive readiness.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--change", required=True)
    parser.add_argument("--explicit-request", action="store_true")
    parser.add_argument("--allow-risk", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = archive_status(
        Path(args.repo),
        args.change,
        explicit_request=args.explicit_request,
        allow_risk=args.allow_risk,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0


def render_text(report: dict) -> str:
    lines = [
        f"Archive policy: {report['policy']}",
        f"Ready: {str(report['ready']).lower()}",
        f"Approval required: {str(report['approvalRequired']).lower()}",
        f"Next action: {report['nextAction']}",
    ]
    for item in report["risks"]:
        lines.append(f"- {item['code']}: {item['message']}")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
