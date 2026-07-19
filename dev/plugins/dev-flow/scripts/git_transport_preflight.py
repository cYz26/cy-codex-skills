#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from workflow_git import GIT_TRANSPORT_READY, git_transport_preflight


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Probe a configured Git remote with native Git only. "
            "This command never invokes gh or attempts a push."
        )
    )
    parser.add_argument("--repo", default=".", help="Repository to inspect")
    parser.add_argument("--remote", default="origin", help="Configured Git remote name")
    parser.add_argument("--branch", help="Local branch to evaluate; defaults to the current branch")
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=15.0,
        help="Per-command timeout for the read-only probe",
    )
    parser.add_argument("--json", action="store_true", help="Emit a JSON report")
    args = parser.parse_args(argv)

    report = git_transport_preflight(
        Path(args.repo),
        remote=args.remote,
        branch=args.branch,
        timeout_seconds=args.timeout_seconds,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        remote = report["remote"]
        print(f"Status: {report['status']}")
        print(f"Remote: {remote['name']} ({remote['transport']})")
        print(f"Branch: {report['branch'] or 'unresolved'}")
        print(f"Reason: {report['reason']}")
        if report["diagnostic"]:
            print(f"Diagnostic: {report['diagnostic']}")
        print("Push attempted: no")
        print("Requires gh: no")
    return 0 if report["status"] == GIT_TRANSPORT_READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
