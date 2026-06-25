#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Check that a DevFlow review checklist exists.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    repo = Path(args.repo).expanduser().resolve()
    path = repo / "REVIEW_CHECKLIST.md"
    ok = path.exists() and "Acceptance criteria" in path.read_text()
    report = {"ok": ok, "path": str(path), "status": "ready" if ok else "missing_or_incomplete"}
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(report["status"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
