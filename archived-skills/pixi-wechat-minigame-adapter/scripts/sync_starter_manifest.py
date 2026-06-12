#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "assets" / "starter-manifest.json"


def list_files(root: Path) -> list[str]:
    return sorted(
        str(path.relative_to(root)).replace("\\", "/")
        for path in root.rglob("*")
        if path.is_file()
    )


def build_manifest() -> dict:
    starter = ROOT / "assets" / "starter-template"
    skeleton = ROOT / "assets" / "skeleton-template"
    glyph = ROOT / "assets" / "text-modules" / "fixed-copy-glyph"

    return {
        "schemaVersion": 1,
        "skill": "pixi-wechat-minigame-adapter",
        "compatibility": {
            "pixi": "v8",
            "language": "TypeScript",
            "bundler": "Vite",
        },
        "modes": {
            "overlay": {
                "templateDir": "assets/starter-template",
                "files": list_files(starter),
            },
            "skeleton": {
                "templateDir": "assets/skeleton-template",
                "files": list_files(skeleton),
            },
        },
        "textModules": {
            "none": {
                "templateDir": None,
                "files": [],
            },
            "fixed-copy-glyph": {
                "templateDir": "assets/text-modules/fixed-copy-glyph",
                "files": list_files(glyph),
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    manifest = build_manifest()
    serialized = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        current = MANIFEST_PATH.read_text(encoding="utf-8")
        if current != serialized:
            raise SystemExit("starter-manifest.json is out of date")
        print("starter-manifest.json is up to date")
        return 0

    MANIFEST_PATH.write_text(serialized, encoding="utf-8")
    print(f"Wrote {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
