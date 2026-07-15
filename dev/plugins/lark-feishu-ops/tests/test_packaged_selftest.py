import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SELF_TEST = PLUGIN_ROOT / "scripts" / "test_runtime_contract.py"


class RuntimeContractSelfTestTests(unittest.TestCase):
    def test_self_test_is_read_only_and_passes_from_source(self):
        result = subprocess.run(
            [sys.executable, str(SELF_TEST), "--json"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"], report)
        self.assertEqual("read", report["checks"]["explicit_read_allowed"]["observed"])
        self.assertEqual("unknown", report["checks"]["unknown_action_blocked"]["observed"])
        self.assertFalse(report["checks"]["write_action_not_direct"]["observed"])
        self.assertFalse(report["checks"]["auth_cache_disabled"]["observed"])


if __name__ == "__main__":
    unittest.main()
