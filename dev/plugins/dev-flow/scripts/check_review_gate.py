#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from workflow_generated_artifacts import inspect_generated_artifact_lifecycle


def main() -> int:
    parser = argparse.ArgumentParser(description="Check that a DevFlow review checklist exists.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    repo = Path(args.repo).expanduser().resolve()
    path = repo / "REVIEW_CHECKLIST.md"
    checklist_ok = path.exists() and "Acceptance criteria" in path.read_text()
    lifecycle = generated_artifact_review_status(repo)
    ok = checklist_ok and lifecycle["ok"]
    report = {
        "ok": ok,
        "path": str(path),
        "status": (
            "ready"
            if ok
            else "generated_artifacts_unresolved"
            if checklist_ok
            else "missing_or_incomplete"
        ),
        "generatedArtifacts": lifecycle["generatedArtifacts"],
    }
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(report["status"])
    return 0 if ok else 1


def generated_artifact_review_status(repo: Path) -> dict[str, object]:
    lifecycle = inspect_generated_artifact_lifecycle(repo)
    return {
        "ok": bool(lifecycle["ok"]),
        "generatedArtifacts": lifecycle,
        "nextActions": lifecycle["nextActions"],
    }


if __name__ == "__main__":
    raise SystemExit(main())
