#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install_starter.py"
MANIFEST = ROOT / "assets" / "starter-manifest.json"


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def assert_exists(root: Path, relative_paths: list[str]) -> None:
    missing = [relative for relative in relative_paths if not (root / relative).exists()]
    if missing:
        raise SystemExit(f"Missing installed files: {missing}")


def validate_manifest() -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("skill") != "pixi-wechat-minigame-adapter":
        raise SystemExit("starter-manifest.json has an unexpected skill name")
    return manifest


def create_overlay_fixture(root: Path) -> None:
    (root / "src" / "shared" / "config").mkdir(parents=True, exist_ok=True)
    (root / "src" / "shared").mkdir(parents=True, exist_ok=True)
    (root / "src" / "platform").mkdir(parents=True, exist_ok=True)
    (root / "src" / "shared" / "contracts.ts").write_text(
        "export interface RuntimePlatform {}\nexport interface SafeAreaInsets { top:number; right:number; bottom:number; left:number; }\nexport interface ViewportSize { width:number; height:number; }\n",
        encoding="utf-8",
    )
    (root / "src" / "shared" / "config" / "gameConfig.ts").write_text(
        "export const UI_COLORS = { backgroundTop: 0x07111d };\n",
        encoding="utf-8",
    )
    (root / "package.json").write_text(
        json.dumps(
            {
                "name": "overlay-fixture",
                "private": True,
                "type": "module",
                "scripts": {},
                "dependencies": {},
                "devDependencies": {},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    manifest = validate_manifest()

    with tempfile.TemporaryDirectory(prefix="pixi-wechat-solution-") as temp_dir:
        temp_root = Path(temp_dir)
        overlay_root = temp_root / "overlay"
        skeleton_root = temp_root / "skeleton"
        overlay_glyph_root = temp_root / "overlay-glyph"
        skeleton_glyph_root = temp_root / "skeleton-glyph"

        create_overlay_fixture(overlay_root)
        create_overlay_fixture(overlay_glyph_root)

        run("python3", str(INSTALLER), "--mode", "overlay", "--text-module", "none", "--target-repo", str(overlay_root))
        run(
            "python3",
            str(INSTALLER),
            "--mode",
            "overlay",
            "--text-module",
            "fixed-copy-glyph",
            "--target-repo",
            str(overlay_glyph_root),
        )
        run("python3", str(INSTALLER), "--mode", "skeleton", "--text-module", "none", "--target-repo", str(skeleton_root))
        run(
            "python3",
            str(INSTALLER),
            "--mode",
            "skeleton",
            "--text-module",
            "fixed-copy-glyph",
            "--target-repo",
            str(skeleton_glyph_root),
        )

        overlay_files = manifest["modes"]["overlay"]["files"]
        skeleton_files = manifest["modes"]["skeleton"]["files"]
        glyph_files = manifest["textModules"]["fixed-copy-glyph"]["files"]

        assert_exists(
            overlay_root,
            [path for path in overlay_files if not path.endswith(("package.scripts.fragment.json", "Makefile.fragment.mk"))],
        )
        assert_exists(
            skeleton_root,
            [path for path in skeleton_files if not path.endswith(("package.scripts.fragment.json", "Makefile.fragment.mk"))],
        )
        assert_exists(
            overlay_glyph_root,
            [path for path in glyph_files if not path.endswith(("package.scripts.fragment.json", "Makefile.fragment.mk"))],
        )
        assert_exists(
            skeleton_glyph_root,
            [path for path in glyph_files if not path.endswith(("package.scripts.fragment.json", "Makefile.fragment.mk"))],
        )

        overlay_package = json.loads((overlay_root / "package.json").read_text(encoding="utf-8"))
        for script_name in ("build:wechat", "build:wechat:debug", "audit:wechat", "test", "lint", "typecheck"):
            if script_name not in overlay_package["scripts"]:
                raise SystemExit(f"overlay package.json missing script {script_name}")
        if "build:copy-glyph-atlas" not in json.loads((overlay_glyph_root / "package.json").read_text(encoding="utf-8"))["scripts"]:
            raise SystemExit("overlay text module did not merge build:copy-glyph-atlas")
        if "build:copy-glyph-atlas" not in json.loads((skeleton_glyph_root / "package.json").read_text(encoding="utf-8"))["scripts"]:
            raise SystemExit("skeleton text module did not merge build:copy-glyph-atlas")

        if not (skeleton_root / "package.json").exists():
            raise SystemExit("skeleton package.json missing")
        if not (skeleton_root / "Makefile").exists():
            raise SystemExit("skeleton Makefile missing")

    print("Canonical Pixi WeChat solution assets validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
