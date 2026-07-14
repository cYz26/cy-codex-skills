#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from workflow_compact import create_checkpoint
from workflow_lib import repo_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a durable checkpoint before compacting context.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--boundary", required=True)
    parser.add_argument("--change")
    parser.add_argument("--next-stage", default="next_stage")
    parser.add_argument("--output")
    parser.add_argument("--current-goal", default="Not recorded.")
    parser.add_argument("--completed-work", action="append", dest="completed_work")
    parser.add_argument("--decision", action="append", dest="decisions")
    parser.add_argument("--open-question", action="append", dest="open_questions")
    parser.add_argument("--risk", action="append", dest="risks")
    parser.add_argument("--validation-command", default="not-run")
    parser.add_argument("--validation-result", default="not-run")
    parser.add_argument("--validation-notes", default="No validation notes recorded.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--continuation-required", dest="continuation_required", action="store_true", default=None)
    group.add_argument("--no-continuation-required", dest="continuation_required", action="store_false")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = create_checkpoint(repo_path(args.repo), vars(args))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
