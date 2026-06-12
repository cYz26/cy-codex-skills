#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "assets" / "starter-manifest.json"
MAKEFILE_SECTION_BEGIN = "# >>> pixi-wechat-minigame-adapter"
MAKEFILE_SECTION_END = "# <<< pixi-wechat-minigame-adapter"
MAKE_TARGETS = ("web", "wechat", "wechat-debug", "audit", "audit-wechat", "test", "lint", "typecheck")


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def copy_file(source: Path, target: Path, force: bool) -> None:
    ensure_parent(target)
    if target.exists():
        if target.read_bytes() == source.read_bytes():
            return
        if not force:
            raise SystemExit(f"Refusing to overwrite existing file without --force: {target}")
    shutil.copy2(source, target)


def merge_package_json(target_repo: Path, fragments: list[Path], force: bool) -> None:
    package_path = target_repo / "package.json"
    if not package_path.exists():
        raise SystemExit(f"Missing package.json in {target_repo}")

    package_data = read_json(package_path)
    for fragment_path in fragments:
        fragment = read_json(fragment_path)
        for section in ("scripts", "dependencies", "devDependencies"):
            payload = fragment.get(section)
            if not payload:
                continue
            target_section = package_data.setdefault(section, {})
            for key, value in payload.items():
                if key in target_section and target_section[key] != value and not force:
                    raise SystemExit(
                        f"package.json conflict for {section}.{key}. Rerun with --force to overwrite."
                    )
                target_section[key] = value

    write_json(package_path, package_data)


def extract_make_targets(fragment_text: str) -> set[str]:
    targets: set[str] = set()
    for line in fragment_text.splitlines():
        if ":" not in line:
            continue
        if line.startswith(".") or line.startswith("\t"):
            continue
        target = line.split(":", 1)[0].strip()
        if target in MAKE_TARGETS:
            targets.add(target)
    return targets


def merge_makefile(target_repo: Path, fragments: list[Path], force: bool, mode: str) -> None:
    if not fragments:
        return

    makefile_path = target_repo / "Makefile"
    fragment_text = "\n".join(path.read_text(encoding="utf-8").rstrip() for path in fragments).strip() + "\n"

    if not makefile_path.exists():
        makefile_path.write_text(fragment_text, encoding="utf-8")
        return

    current = makefile_path.read_text(encoding="utf-8")
    if MAKEFILE_SECTION_BEGIN in current and MAKEFILE_SECTION_END in current:
        if not force:
            return
        before, _, remainder = current.partition(MAKEFILE_SECTION_BEGIN)
        _, _, after = remainder.partition(MAKEFILE_SECTION_END)
        current = before.rstrip() + "\n\n"
        current += MAKEFILE_SECTION_BEGIN + "\n" + fragment_text + MAKEFILE_SECTION_END + after
        makefile_path.write_text(current.rstrip() + "\n", encoding="utf-8")
        return

    if mode == "overlay":
        existing_targets = extract_make_targets(current)
        if existing_targets:
            return

    block = f"{MAKEFILE_SECTION_BEGIN}\n{fragment_text}{MAKEFILE_SECTION_END}\n"
    makefile_path.write_text(current.rstrip() + "\n\n" + block, encoding="utf-8")


def install_template(target_repo: Path, template_dir: Path, files: list[str], force: bool) -> tuple[list[Path], list[Path]]:
    package_fragments: list[Path] = []
    makefile_fragments: list[Path] = []

    for relative_path in files:
        source = template_dir / relative_path
        if relative_path.endswith("package.scripts.fragment.json"):
            package_fragments.append(source)
            continue
        if relative_path.endswith("Makefile.fragment.mk"):
            makefile_fragments.append(source)
            continue

        copy_file(source, target_repo / relative_path, force)

    return package_fragments, makefile_fragments


def install_mode(mode: str, text_module: str, target_repo: Path, force: bool) -> None:
    manifest = load_manifest()
    mode_payload = manifest["modes"][mode]
    mode_template = ROOT / mode_payload["templateDir"]
    package_fragments, makefile_fragments = install_template(
        target_repo,
        mode_template,
        mode_payload["files"],
        force,
    )

    module_payload = manifest["textModules"][text_module]
    if module_payload["templateDir"]:
        module_template = ROOT / module_payload["templateDir"]
        module_package_fragments, module_makefile_fragments = install_template(
            target_repo,
            module_template,
            module_payload["files"],
            force,
        )
        package_fragments.extend(module_package_fragments)
        makefile_fragments.extend(module_makefile_fragments)

    if package_fragments:
        merge_package_json(target_repo, package_fragments, force)
    if makefile_fragments:
        merge_makefile(target_repo, makefile_fragments, force, mode)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("overlay", "skeleton"), required=True)
    parser.add_argument("--text-module", choices=("none", "fixed-copy-glyph"), default="none")
    parser.add_argument("--target-repo", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    target_repo = Path(args.target_repo).resolve()
    target_repo.mkdir(parents=True, exist_ok=True)

    install_mode(args.mode, args.text_module, target_repo, args.force)
    print(
        f"Installed pixi-wechat-minigame-adapter mode={args.mode} text_module={args.text_module} into {target_repo}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
