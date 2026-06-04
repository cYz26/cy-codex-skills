#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from agent_kb_source_intake import import_sources


def main() -> int:
    parser = argparse.ArgumentParser(description="Import sources into an AgentKB vault.")
    parser.add_argument("--vault", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--kind", default="auto")
    parser.add_argument("--max-bytes", type=int, default=10 * 1024 * 1024)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    apply = args.apply and not args.dry_run
    result = import_sources(
        args.vault,
        args.project,
        args.source,
        apply=apply,
        kind=args.kind,
        max_bytes=args.max_bytes,
    )
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"{len(result['planned'])} planned, {len(result['imported'])} imported.")
    return 0 if args.dry_run or result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
