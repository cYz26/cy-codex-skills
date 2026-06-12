#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    source_path = repo_root / "src" / "ui" / "fixedCopyGlyph" / "strings.json"
    output_path = repo_root / "public" / "assets" / "text" / "fixed-copy-glyph-manifest.json"

    strings = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(strings, list) or not all(isinstance(item, str) for item in strings):
        raise SystemExit("src/ui/fixedCopyGlyph/strings.json must be a JSON string array")

    unique_strings = list(dict.fromkeys(strings))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "module": "fixed-copy-glyph",
                "strings": unique_strings,
                "notes": [
                    "Replace this scaffold with a real atlas generator if your project needs baked glyph textures."
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
