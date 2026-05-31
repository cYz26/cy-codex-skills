#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from workflow_compact import compact_recommendation
from workflow_lib import repo_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Recommend whether to compact at a workflow boundary.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--boundary", required=True)
    parser.add_argument("--next-stage", default="next_stage")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--continuation-required", dest="continuation_required", action="store_true", default=None)
    group.add_argument("--no-continuation-required", dest="continuation_required", action="store_false")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = compact_recommendation(repo_path(args.repo), args.boundary, args.next_stage, args.continuation_required)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
