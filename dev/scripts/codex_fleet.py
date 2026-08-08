#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "dev" / "tools" / "codex-fleet" / "src"


def main() -> int:
    sys.path.insert(0, str(SOURCE_ROOT))
    from codex_fleet.cli import main as fleet_main

    return int(fleet_main())


if __name__ == "__main__":
    raise SystemExit(main())
