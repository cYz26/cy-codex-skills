#!/usr/bin/env python3
"""Run every DevFlow source test that does not require promoted release assets."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_ROOT = REPO_ROOT / "dev" / "plugins" / "dev-flow" / "tests"
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
    print(
        "DevFlow pre-promotion source suite passed: "
        f"{result.testsRun} tests across {len(files)} modules; "
        "release-dependent modules remain mandatory after promotion."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
