#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Record a DevFlow task evidence note.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--claim", required=True)
    parser.add_argument("--command", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    repo = Path(args.repo).expanduser().resolve()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    path = repo / ".planning" / "verification" / f"{timestamp}-{args.task_id}-evidence.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    commands = "\n".join(f"- `{command}`" for command in args.command) or "- none"
    path.write_text(
        f"# Evidence: {args.task_id}\n\n"
        f"## Claim\n{args.claim}\n\n"
        f"## Commands Run\n{commands}\n\n"
        "## Risks / Gaps\n- none recorded\n"
    )
    report = {"ok": True, "path": str(path), "task_id": args.task_id}
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(str(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
