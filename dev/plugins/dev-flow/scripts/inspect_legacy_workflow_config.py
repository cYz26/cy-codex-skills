#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from legacy_workflow_config import inspect_legacy_workflow_config


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect obsolete DevFlow configuration and project markers in read-only mode."
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Project directory to inspect (default: current directory).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the complete machine-readable report.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = inspect_legacy_workflow_config(Path(args.repo))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"status: {report['status']}")
        print(f"recognized inputs: {len(report['recognizedInputs'])}")
        print(f"legacy artifacts: {len(report['artifacts'])}")
        print(f"conflicts: {len(report['conflicts'])}")
        for action in report["manualActions"]:
            print(f"next: {action}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
