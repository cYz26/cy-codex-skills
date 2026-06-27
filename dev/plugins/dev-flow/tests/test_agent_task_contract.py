import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
TEMPLATES = PLUGIN_ROOT / "assets" / "templates"
sys.path.insert(0, str(SCRIPTS))


VALID_CONTRACT = """# Agent Task Contract

## Goal
Implement the delegated parser change and return a concise summary of the final artifact.

## Scope
Allowed: modify `dev/plugins/dev-flow/scripts/workflow_example.py` and
`dev/plugins/dev-flow/tests/test_example.py`.
Forbidden: do not modify release assets, OpenSpec files, `.planning/STATE.md`,
or files outside the named write set.

## Constraints
Preserve Python 3.9 compatibility, use only the standard library, keep existing
style, and avoid changing public CLI behavior outside the delegated task.

## Verification
Run `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest dev.plugins.dev-flow.tests.test_example`.

## Evidence
Report changed files, commands run, test logs or validation results,
unverified areas, and risk notes.

## Human Gate
Wait for review before expanding scope, touching forbidden files, changing
public APIs, skipping validation, or continuing with failing tests.
"""


class AgentTaskContractTests(unittest.TestCase):
    def test_template_contains_required_sections_and_usage_boundary(self):
        template = (TEMPLATES / "AGENT_TASK_CONTRACT.md.template").read_text()

        for heading in [
            "# Agent Task Contract",
            "## Goal",
            "## Scope",
            "## Constraints",
            "## Verification",
            "## Evidence",
            "## Human Gate",
        ]:
            self.assertIn(heading, template)
        self.assertIn("Allowed", template)
        self.assertIn("Forbidden", template)
        self.assertIn("changed files", template)
        self.assertIn("unverified areas", template)
        self.assertIn("risk notes", template)

    def test_validator_accepts_complete_contract(self):
        from workflow_agent_task_contract import validate_agent_task_contract_text

        report = validate_agent_task_contract_text(VALID_CONTRACT)

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["missingSections"], [])
        self.assertEqual(report["errors"], [])

    def test_validator_rejects_missing_forbidden_scope_and_vague_verification(self):
        from workflow_agent_task_contract import validate_agent_task_contract_text

        invalid = VALID_CONTRACT.replace(
            "Forbidden: do not modify release assets, OpenSpec files, `.planning/STATE.md`,\n"
            "or files outside the named write set.",
            "",
        ).replace(
            "Run `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest dev.plugins.dev-flow.tests.test_example`.",
            "Run tests as needed.",
        )

        report = validate_agent_task_contract_text(invalid)

        self.assertFalse(report["ok"])
        self.assertIn("Scope must include forbidden boundaries.", report["errors"])
        self.assertIn(
            "Verification must list concrete commands or a read-only/not-applicable rationale.",
            report["errors"],
        )

    def test_validator_allows_read_only_verification_rationale(self):
        from workflow_agent_task_contract import validate_agent_task_contract_text

        read_only = VALID_CONTRACT.replace(
            "Run `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest dev.plugins.dev-flow.tests.test_example`.",
            "Not applicable: this is a read-only explorer task; verify by reporting inspected files "
            "and residual risks.",
        )

        report = validate_agent_task_contract_text(read_only)

        self.assertTrue(report["ok"], report)

    def test_cli_reports_json_failure_for_placeholder_contract(self):
        contract = Path(tempfile.mkdtemp(prefix="agent-contract-")) / "contract.md"
        contract.write_text(
            """# Agent Task Contract

## Goal
pending

## Scope
pending

## Constraints
pending

## Verification
pending

## Evidence
pending

## Human Gate
pending
"""
        )

        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "validate_agent_task_contract.py"), "--contract", str(contract), "--json"],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertIn("Goal contains placeholder content.", report["errors"])


if __name__ == "__main__":
    unittest.main()
