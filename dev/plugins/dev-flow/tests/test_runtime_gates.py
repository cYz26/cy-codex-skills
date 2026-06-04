import ast
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from workflow_doctor import doctor_workflow
from workflow_hooks import hook_response
from workflow_state import parse_state
from workflow_validate import validate_workflow_state


class RuntimeGateTests(unittest.TestCase):
    def make_repo(self):
        repo = Path(tempfile.mkdtemp(prefix="devflow-runtime-repo-"))
        (repo / "AGENTS.md").write_text("# Instructions\n")
        (repo / "openspec").mkdir()
        (repo / "openspec" / "config.yaml").write_text("schema: spec-driven\n")
        (repo / ".planning").mkdir()
        return repo

    def write_state(self, repo, extra_context=""):
        (repo / ".planning" / "STATE.md").write_text(
            f"""---
workflow_version: 0.3.0
project_mode: brownfield
current_stage: executing
current_phase:
  id: none
  status: none
current_change:
  id: none
  status: none
gates:
  workflow_initialized: true
  spec_approved: true
  plan_written: true
  tests_baseline_known: false
  implementation_done: false
  verification_passed: false
  state_updated: true
  archive_allowed: false
context_management:
  compact_policy: checkpoint_boundary
{extra_context}context_health:
  last_report: none
  last_risk: unknown
  last_confidence: unknown
  last_decision: none
  last_goal_status: unknown
  goal_summary: none
---
# State
"""
        )

    def test_claude_delegate_module_is_python39_syntax_compatible(self):
        source = (SCRIPTS / "workflow_claude_delegate.py").read_text()
        tree = ast.parse(source, filename="workflow_claude_delegate.py", feature_version=(3, 9))
        union_annotations = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr)
        ]

        self.assertEqual(union_annotations, [])

    def test_state_parser_preserves_nested_context_management_lists(self):
        repo = self.make_repo()
        self.write_state(
            repo,
            """  compact_after:
    - OpenSpec change planned
    - verification passed
  skip_compact_for:
    - quick status update
    - read-only review
""",
        )

        state = parse_state(repo)

        context = state["context_management"]
        self.assertEqual(context["compact_after"], ["OpenSpec change planned", "verification passed"])
        self.assertEqual(context["skip_compact_for"], ["quick status update", "read-only review"])
        self.assertNotIn("- OpenSpec change planned", state)
        self.assertNotIn("- quick status update", state)

    def test_validation_and_doctor_report_installed_cache_hook_drift(self):
        repo = self.make_repo()
        self.write_state(repo)
        codex_home = Path(tempfile.mkdtemp(prefix="devflow-runtime-home-"))
        plugin_root = Path(tempfile.mkdtemp(prefix="devflow-runtime-plugin-"))
        cache_root = codex_home / "plugins" / "cache" / "cy-codex-skills" / "dev-flow" / "1.0.0"
        (plugin_root / "scripts").mkdir(parents=True)
        (cache_root / "scripts").mkdir(parents=True)
        (plugin_root / "scripts" / "present_hook.py").write_text("print('source hook')\n")
        (plugin_root / "hooks.json").write_text(
            json.dumps(
                {
                    "hooks": {
                        "Stop": [
                            {
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": (
                                            'python3 "${CODEX_HOME:-$HOME/.codex}/plugins/cache/'
                                            'cy-codex-skills/dev-flow/1.0.0/scripts/present_hook.py"'
                                        ),
                                    }
                                ]
                            }
                        ]
                    }
                }
            )
        )

        validation = validate_workflow_state(repo, plugin_root=plugin_root, codex_home=codex_home)
        doctor = doctor_workflow(repo, plugin_root=plugin_root, codex_home=codex_home)

        self.assertFalse(validation["ok"], validation)
        self.assertTrue(any("source/cache hook drift" in issue for issue in validation["issues"]))
        self.assertEqual(doctor["diagnosis"], "needs repair")
        self.assertTrue(any("present_hook.py" in issue for issue in doctor["issues"]))

    def test_workflow_state_validation_skips_cache_drift_unless_cache_context_is_explicit(self):
        repo = self.make_repo()
        self.write_state(
            repo,
            """  compact_status: not_needed
  compact_skip_reason: none
  last_compact_result_file: none
""",
        )

        validation = validate_workflow_state(repo)

        self.assertTrue(validation["ok"], validation)
        self.assertFalse(any("source/cache hook drift" in issue for issue in validation["issues"]))

    def test_hook_response_emits_structured_json_for_stop_warnings(self):
        repo = self.make_repo()
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = hook_response(repo, "DevFlow: context health is medium.", event_name="Stop")

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["hookSpecificOutput"]["hookEventName"], "Stop")
        self.assertEqual(
            payload["hookSpecificOutput"]["additionalContext"],
            "DevFlow: context health is medium.",
        )

    def test_hook_response_preserves_block_mode_exit_code_with_json_output(self):
        repo = self.make_repo()
        (repo / ".dev-flow.json").write_text(json.dumps({"hook": {"mode": "block"}}))
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = hook_response(repo, "DevFlow: verification is required.", event_name="Stop")

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["hookSpecificOutput"]["hookEventName"], "Stop")
        self.assertEqual(
            payload["hookSpecificOutput"]["additionalContext"],
            "DevFlow: verification is required.",
        )


if __name__ == "__main__":
    unittest.main()
