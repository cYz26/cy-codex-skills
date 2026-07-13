#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from workflow_paths import repo_path
from workflow_roadmap_provider import persist_archived_roadmap_binding


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dry-run or explicitly archive one verified GSD roadmap binding."
    )
    parser.add_argument("--repo", required=True)
    parser.add_argument("--change", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--authorize-archive-binding",
        action="store_true",
        help="Authorize canonical config write and verified archive side effects.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.authorize_archive_binding and not args.apply:
        parser.error("--authorize-archive-binding requires --apply")

    report = persist_archived_roadmap_binding(
        repo_path(args.repo),
        args.change,
        apply=args.apply,
        authorized=args.authorize_archive_binding,
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"status={report['status']} changed={str(report.get('changed', False)).lower()}")
        if report.get("missingGates"):
            print(f"missing_gates={','.join(report['missingGates'])}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
