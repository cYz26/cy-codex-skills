#!/usr/bin/env python3
"""Run every DevFlow source test that does not require promoted release assets."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_ROOT = REPO_ROOT / "dev" / "plugins" / "dev-flow" / "tests"
DEVFLOW_SCRIPTS = REPO_ROOT / "dev" / "plugins" / "dev-flow" / "scripts"
sys.path.insert(0, str(DEVFLOW_SCRIPTS))

from workflow_release_verification import analyze_project_refresh_impact
from workflow_state import resolve_state
RELEASE_DEPENDENT_TESTS = {
    "test_packaged_runtime.py",
    "test_release_smoke.py",
}


def source_test_files() -> list[Path]:
    return [
        path
        for path in sorted(TEST_ROOT.glob("test_*.py"))
        if path.name not in RELEASE_DEPENDENT_TESTS
    ]


def build_suite(loader: unittest.TestLoader) -> unittest.TestSuite:
    suite = unittest.TestSuite()
    for path in source_test_files():
        suite.addTests(
            loader.discover(
                str(TEST_ROOT),
                pattern=path.name,
            )
        )
    return suite


def main() -> int:
    files = source_test_files()
    if not files:
        print("DevFlow pre-promotion suite found no source tests.", file=sys.stderr)
        return 1
    result = unittest.TextTestRunner(verbosity=2).run(build_suite(unittest.TestLoader()))
    if result.skipped:
        print(
            f"DevFlow pre-promotion suite rejects skipped tests: {len(result.skipped)}.",
            file=sys.stderr,
        )
        return 1
    if not result.wasSuccessful():
        return 1
    state = resolve_state(REPO_ROOT).get("data", {})
    current_change = state.get("current_change", {}) if isinstance(state, dict) else {}
    change_id = str(current_change.get("id") or "") if isinstance(current_change, dict) else ""
    refresh_impact = analyze_project_refresh_impact(
        REPO_ROOT / "dev" / "plugins" / "dev-flow",
        REPO_ROOT / "plugins" / "dev-flow",
        expected_change=change_id or None,
    )
    if not refresh_impact["ok"]:
        print(
            "DevFlow pre-promotion Project Refresh Impact gate failed: "
            + "; ".join(refresh_impact["errors"]),
            file=sys.stderr,
        )
        return 1
    print(
        "DevFlow pre-promotion source suite passed: "
        f"{result.testsRun} tests across {len(files)} modules; "
        "Project Refresh Impact is covered; release-dependent modules remain mandatory after promotion."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
