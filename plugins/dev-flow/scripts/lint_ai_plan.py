#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


ALLOW_MARKER = "ai-native-plan-lint: allow-human-planning-terms"

FORBIDDEN_PATTERNS = [
    r"\bMVP\b",
    r"\bminimum viable\b",
    r"\bPhase\s*[1-9]\b",
    r"一期|二期|三期",
    r"后续优化|后续规划",
    r"\bFuture\s+Work\b",
    r"\bLater\b",
    r"\bRoadmap\b",
    r"预计.*[天周月]",
    r"人天|人月",
    r"\bsprint\b",
]

REQUIRED_HEADINGS = [
    "Target State",
    "Completion Contract",
    "Capability Slices",
    "Acceptance Criteria",
    "Validation Commands",
]


def lint_ai_plan(path: Path, *, skip_required_headings: bool = False) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    findings: list[str] = []

    if ALLOW_MARKER not in text:
        for pattern in FORBIDDEN_PATTERNS:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                line = text[: match.start()].count("\n") + 1
                findings.append(f"line {line}: {match.group(0)!r} matched {pattern!r}")

    missing: list[str] = []
    if not skip_required_headings:
        missing = [heading for heading in REQUIRED_HEADINGS if heading not in text]

    return {
        "ok": not findings and not missing,
        "forbidden": findings,
        "missing": missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint an AI-native technical plan.")
    parser.add_argument("path")
    parser.add_argument("--skip-required-headings", action="store_true")
    args = parser.parse_args()

    report = lint_ai_plan(Path(args.path), skip_required_headings=args.skip_required_headings)
    forbidden = list(report["forbidden"])
    missing = list(report["missing"])

    if forbidden:
        print("Forbidden human-style planning terms found:")
        for item in forbidden:
            print(f"- {item}")

    if missing:
        print("Missing required headings:")
        for heading in missing:
            print(f"- {heading}")

    if forbidden or missing:
        return 1

    print("AI-native plan lint passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
