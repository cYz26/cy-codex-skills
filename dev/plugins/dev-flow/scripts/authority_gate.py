#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from workflow_authority_gate import (
    AuthorityGateError,
    clear_authority_gate,
    record_authority_gate,
)


def read_mapping(path: str) -> dict:
    value = json.loads(Path(path).read_text())
    if not isinstance(value, dict):
        raise AuthorityGateError("authority resolution must be a JSON object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Persist or clear the only DevFlow authority-gate state seam."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    record = subparsers.add_parser("record")
    record.add_argument("--repo", default=".")
    record.add_argument("--resolution", required=True)
    record.add_argument("--next-question", required=True)
    record.add_argument("--prior-receipt")
    clear = subparsers.add_parser("clear")
    clear.add_argument("--repo", default=".")
    clear.add_argument("--resolution", required=True)
    clear.add_argument("--gate-key", required=True)
    clear.add_argument("--resume-stage", required=True)
    args = parser.parse_args(argv)
    try:
        resolution = read_mapping(args.resolution)
        if args.command == "record":
            report = record_authority_gate(
                Path(args.repo),
                resolution,
                next_question=args.next_question,
                prior_receipt=(
                    Path(args.prior_receipt) if args.prior_receipt else None
                ),
            )
        else:
            report = clear_authority_gate(
                Path(args.repo),
                gate_key=args.gate_key,
                resolution=resolution,
                resume_stage=args.resume_stage,
            )
    except (AuthorityGateError, OSError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "status": "blocked", "error": str(error)}))
        return 2
    print(json.dumps({"ok": True, **report}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
