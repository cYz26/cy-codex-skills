#!/usr/bin/env python3
"""Create per-case QA reports from validation results and generated artifacts."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCRIPT_DIR = Path(__file__).resolve().parent
RIG_VALIDATOR = load_module(SCRIPT_DIR / "validate_rig_meta.py", "validate_rig_meta")
MOTION_VALIDATOR = load_module(SCRIPT_DIR / "validate_motion.py", "validate_motion")


def issue(severity: str, message: str, path: str | None = None) -> dict[str, str]:
    item = {"severity": severity, "message": message}
    if path:
        item["path"] = path
    return item


def summarize(checks: list[dict[str, str]]) -> dict[str, int]:
    return {
        "critical": sum(1 for c in checks if c["severity"] == "critical"),
        "warning": sum(1 for c in checks if c["severity"] == "warning"),
        "info": sum(1 for c in checks if c["severity"] == "info"),
    }


def case_dirs(root: Path) -> list[Path]:
    if (root / "rig_meta.json").exists():
        return [root]
    return sorted(path for path in root.iterdir() if path.is_dir() and (path / "rig_meta.json").exists())


def make_report(case_dir: Path) -> dict[str, Any]:
    rig_path = case_dir / "rig_meta.json"
    checks: list[dict[str, str]] = []
    rig_report = RIG_VALIDATOR.validate_rig(rig_path)
    checks.extend(rig_report["checks"])

    motion_dir = case_dir / "motions"
    motion_paths = sorted(motion_dir.glob("*.json")) if motion_dir.exists() else []
    if not motion_paths:
        checks.append(issue("critical", "no motion JSON files found", str(motion_dir)))
    for motion_path in motion_paths:
        motion_report = MOTION_VALIDATOR.validate_motion(motion_path, rig_path, 0.01)
        checks.extend(motion_report["checks"])

    generated_dir = case_dir / "generated"
    scene_path = generated_dir / f"{case_dir.name}.tscn"
    preview_path = generated_dir / "preview.png"
    if scene_path.exists():
        checks.append(issue("info", "generated Godot scene exists", str(scene_path)))
    else:
        checks.append(issue("critical", "generated Godot scene is missing", str(scene_path)))
    if preview_path.exists() and preview_path.stat().st_size > 0:
        checks.append(issue("info", "preview artifact exists", str(preview_path)))
    else:
        checks.append(issue("warning", "preview artifact is missing or empty", str(preview_path)))

    report = {
        "schema_version": "1.0",
        "case_id": case_dir.name,
        "summary": summarize(checks),
        "checks": checks,
        "artifacts": {
            "scene": str(scene_path.relative_to(case_dir)),
            "preview": str(preview_path.relative_to(case_dir)),
        },
    }
    (case_dir / "qa_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", help="Case directory or directory containing cases")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    reports = [make_report(case_dir) for case_dir in case_dirs(Path(args.root))]
    if args.json:
        print(json.dumps(reports, indent=2))
    else:
        for report in reports:
            print(f"{report['case_id']}: {report['summary']}")
    return 1 if any(report["summary"]["critical"] for report in reports) else 0


if __name__ == "__main__":
    raise SystemExit(main())
