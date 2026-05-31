#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import runpy
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_UPDATER = REPO_ROOT / "dev/plugins/dev-flow/scripts/codex_auto_update_plugins_skills.py"


def main() -> int:
    sys.path.insert(0, str(CANONICAL_UPDATER.parent))
    namespace = runpy.run_path(str(CANONICAL_UPDATER))
    return int(namespace["main"]())


if __name__ == "__main__":
    raise SystemExit(main())
