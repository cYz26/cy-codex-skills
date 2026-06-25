#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Report the DevFlow knowledge update target.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--target", default="none")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    allowed = (
        args.target == "none"
        or args.target in {"AGENTS.md", "ENGINEERING_POLICY.md"}
        or args.target.startswith("docs/")
    )
    report = {
        "ok": allowed,
        "target": args.target,
        "status": "accepted" if allowed else "invalid",
        "repo": str(Path(args.repo).expanduser().resolve()),
    }
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(report["status"])
    return 0 if allowed else 1


if __name__ == "__main__":
    raise SystemExit(main())
