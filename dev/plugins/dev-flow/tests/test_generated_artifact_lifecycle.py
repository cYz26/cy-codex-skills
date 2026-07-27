"""Discovery shim for the complete Generated Artifact Lifecycle fixture."""

import importlib.util
import unittest
from pathlib import Path


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "test_generated_artifact_lifecycle.py"
)
SPEC = importlib.util.spec_from_file_location(
    "devflow_generated_artifact_lifecycle_fixture",
    FIXTURE,
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"unable to load Generated Artifact Lifecycle fixture: {FIXTURE}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load_tests(loader, _tests, _pattern):
    return loader.loadTestsFromModule(MODULE)


if __name__ == "__main__":
    unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(MODULE)
    )
