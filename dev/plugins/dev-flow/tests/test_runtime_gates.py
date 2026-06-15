import ast
import contextlib
import importlib
import importlib.util
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
from workflow_state import parse_state, update_state
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

    def test_update_state_preserves_existing_status_body_when_not_overridden(self):
        repo = self.make_repo()
        (repo / ".planning" / "STATE.md").write_text(
            """---
workflow_version: 0.3.0
project_mode: brownfield
current_stage: executing
current_phase:
  id: 01-foundation
  status: planning
current_change:
  id: reduce-medium-context-health-stop-feedback
  status: executing
gates:
  workflow_initialized: true
  spec_approved: true
  plan_written: true
  tests_baseline_known: true
  implementation_done: false
  verification_passed: false
  state_updated: true
  archive_allowed: false
context_management:
  compact_policy: checkpoint_boundary
  last_checkpoint_id: none
  last_checkpoint_file: none
  compact_recommended: false
  compact_status: not_needed
  last_compact_result_file: none
  compact_source: none
  compact_updated_at: none
  compact_skip_reason: none
  compact_error: none
context_health:
  last_report: none
  last_risk: unknown
  last_confidence: unknown
  last_decision: none
  last_goal_status: unknown
  goal_summary: none
---
# Workflow State

## Current Status

Keep this durable status text.

## Next Action

Keep this durable next action.
"""
        )

        update_state(repo, last_context_health_risk="medium")

        state_text = (repo / ".planning" / "STATE.md").read_text()
        self.assertIn("Keep this durable status text.", state_text)
        self.assertIn("Keep this durable next action.", state_text)
        self.assertIn("last_risk: medium", state_text)

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

    def test_hook_response_emits_codex_stop_schema_for_stop_warnings(self):
        repo = self.make_repo()
        self.write_state(repo)
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = hook_response(repo, "DevFlow: context health is medium.", event_name="Stop")

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["decision"], "block")
        self.assertEqual(payload["reason"], "DevFlow: context health is medium.")
        diagnostic = payload.get("diagnostic")
        self.assertIsInstance(diagnostic, dict)
        self.assertEqual(diagnostic["hook_name"], "Stop")
        self.assertEqual(diagnostic["current_stage"], "executing")
        self.assertIn("verification_passed", diagnostic["failed_gates"])
        self.assertEqual(diagnostic["recommended_skill"], "context-health-check")
        self.assertIn("context-health-check", diagnostic["next_action"])
        self.assertNotIn("hookSpecificOutput", payload)

    def test_hook_response_keeps_additional_context_for_non_stop_warnings(self):
        repo = self.make_repo()
        self.write_state(repo)
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = hook_response(repo, "DevFlow: production edit warning.", event_name="PreToolUse")

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["hookSpecificOutput"]["hookEventName"], "PreToolUse")
        self.assertEqual(
            payload["hookSpecificOutput"]["additionalContext"],
            "DevFlow: production edit warning.",
        )
        diagnostic = payload["hookSpecificOutput"].get("diagnostic")
        self.assertIsInstance(diagnostic, dict)
        self.assertEqual(diagnostic["hook_name"], "PreToolUse")
        self.assertEqual(diagnostic["current_stage"], "executing")
        self.assertIn("feature-intake", diagnostic["next_action"])
        self.assertEqual(diagnostic["recommended_skill"], "feature-intake")

    def test_hook_response_preserves_block_mode_exit_code_with_json_output(self):
        repo = self.make_repo()
        self.write_state(repo)
        (repo / ".dev-flow.json").write_text(json.dumps({"hook": {"mode": "block"}}))
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = hook_response(repo, "DevFlow: verification is required.", event_name="Stop")

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["decision"], "block")
        self.assertEqual(payload["reason"], "DevFlow: verification is required.")
        diagnostic = payload.get("diagnostic")
        self.assertIsInstance(diagnostic, dict)
        self.assertIn("verification_passed", diagnostic["failed_gates"])
        self.assertEqual(diagnostic["recommended_skill"], "verify-and-archive")
        self.assertNotIn("hookSpecificOutput", payload)

    def test_hook_response_reports_legacy_skill_layout_next_action(self):
        repo = self.make_repo()
        self.write_state(repo)
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = hook_response(
                repo,
                "DevFlow: legacy skill layout detected under .codex/skills. "
                "Run migration dry-run before applying changes.",
                event_name="PreToolUse",
            )

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        diagnostic = payload["hookSpecificOutput"].get("diagnostic")
        self.assertIsInstance(diagnostic, dict)
        self.assertEqual(diagnostic["legacy_skill_layout_status"], "legacy_detected")
        self.assertEqual(diagnostic["recommended_skill"], "plugin-project-migration")
        self.assertIn("--dry-run", diagnostic["recommended_command"])

    def test_workflow_mode_config_routes_low_risk_work_to_lightweight_ledger(self):
        repo = self.make_repo()
        (repo / ".dev-flow.json").write_text(
            json.dumps({"workflow": {"lightweight_ledger": {"enabled": True}}})
        )
        module = self.workflow_mode_module()

        route = module.route_workflow_mode(repo, kind="docs-only", request="Refresh README examples.")

        self.assertEqual(route["mode"], "lightweight-ledger")
        self.assertEqual(route["label"], "Lightweight Ledger")
        self.assertTrue(route["execution_allowed"])
        self.assertIn("Target State", route["ledger_sections"])
        self.assertIn("Completion Claim", route["ledger_sections"])
        self.assertEqual(route["recommended_skill"], "execute-task")

    def test_workflow_mode_config_cannot_bypass_full_openspec_for_high_risk_work(self):
        repo = self.make_repo()
        (repo / ".dev-flow.json").write_text(
            json.dumps({"workflow": {"lightweight_ledger": {"enabled": True}}})
        )
        module = self.workflow_mode_module()

        route = module.route_workflow_mode(
            repo,
            kind="behavior-change",
            request="Change user-visible behavior in the workflow hook.",
            openspec_ready=False,
        )

        self.assertEqual(route["mode"], "full-openspec")
        self.assertEqual(route["label"], "Full OpenSpec")
        self.assertFalse(route["execution_allowed"])
        self.assertIn("mandatory_full_openspec", route["failed_gates"])
        self.assertIn("proposal, design, specs, and tasks", route["blocker"])

    def test_workflow_mode_routes_explicit_prototype_with_non_production_guardrails(self):
        repo = self.make_repo()
        module = self.workflow_mode_module()

        route = module.route_workflow_mode(repo, kind="tooling", request="Build a proof of concept demo.")

        self.assertEqual(route["mode"], "prototype-mode")
        self.assertEqual(route["label"], "Prototype Mode")
        self.assertFalse(route["production_allowed"])
        self.assertIn("non-production", route["status"])
        self.assertIn("promotion_criteria", route)

    def workflow_mode_module(self):
        spec = importlib.util.find_spec("workflow_mode_routing")
        self.assertIsNotNone(spec, "workflow_mode_routing helper should exist")
        return importlib.import_module("workflow_mode_routing")


if __name__ == "__main__":
    unittest.main()
