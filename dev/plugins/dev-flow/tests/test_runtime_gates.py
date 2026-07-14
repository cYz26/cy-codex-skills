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
from unittest import mock


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from workflow_doctor import doctor_workflow
from workflow_goal_gate import goal_complexity_score
from workflow_hooks import hook_mode, hook_response
from workflow_mode_routing import read_workflow_mode_config
from workflow_state import parse_state, update_state
from workflow_validate import validate_workflow_state


class RuntimeGateTests(unittest.TestCase):
    def make_repo(self):
        repo = Path(tempfile.mkdtemp(prefix="devflow-runtime-repo-"))
        (repo / "AGENTS.md").write_text("# Instructions\n")
        (repo / "openspec").mkdir()
        (repo / "openspec" / "config.yaml").write_text("schema: spec-driven\n")
        (repo / ".planning" / "devflow").mkdir(parents=True)
        return repo

    def write_state(self, repo, extra_context=""):
        (repo / ".planning" / "devflow" / "STATE.md").write_text(
            f"""---
workflow_version: 0.3.0
project_mode: brownfield
current_stage: executing
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
        (repo / ".planning" / "devflow" / "STATE.md").write_text(
            """---
workflow_version: 0.3.0
project_mode: brownfield
current_stage: executing
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

        state_text = (repo / ".planning" / "devflow" / "STATE.md").read_text()
        self.assertIn("Keep this durable status text.", state_text)
        self.assertIn("Keep this durable next action.", state_text)
        self.assertIn("last_risk: medium", state_text)

    def test_validation_accepts_phase_free_state(self):
        repo = self.make_repo()
        self.write_state(
            repo,
            """  last_checkpoint_id: none
  last_checkpoint_file: none
  compact_recommended: false
  compact_status: not_needed
  last_compact_result_file: none
  compact_source: none
  compact_updated_at: none
  compact_skip_reason: none
  compact_error: none
""",
        )
        (repo / ".dev-flow.json").write_text(
            json.dumps({"workflow": {"mode": "full-openspec"}})
        )

        validation = validate_workflow_state(repo)

        self.assertTrue(validation["ok"], validation)

    def test_workflow_config_rejects_invalid_utf8_without_exposing_bytes(self):
        repo = self.make_repo()
        (repo / ".dev-flow.json").write_bytes(b'\xff\xfe"secret-token"')

        config = read_workflow_mode_config(repo)

        self.assertFalse(config["valid"], config)
        self.assertEqual(hook_mode(repo), "block")
        self.assertNotIn("secret-token", json.dumps(config))
        self.assertIn("valid UTF-8 JSON", config["config_errors"][0])

    def test_workflow_config_rejects_symlink_and_blocks_hook_bypass(self):
        repo = self.make_repo()
        outside = Path(tempfile.mkdtemp(prefix="devflow-config-outside-"))
        external = outside / "config.json"
        external.write_text(json.dumps({"hook": {"mode": "off"}}))
        (repo / ".dev-flow.json").symlink_to(external)

        config = read_workflow_mode_config(repo)

        self.assertFalse(config["valid"], config)
        self.assertEqual(hook_mode(repo), "block")

    def test_legacy_selection_key_cannot_disable_hooks(self):
        repo = self.make_repo()
        (repo / ".dev-flow.json").write_text(
            json.dumps(
                {
                    "methodology_profile": "strict-superpowers",
                    "hook": {"mode": "off"},
                }
            )
        )

        config = read_workflow_mode_config(repo)

        self.assertFalse(config["valid"], config)
        self.assertEqual(hook_mode(repo), "block")

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

    def test_goal_gate_warning_when_required_goal_is_missing(self):
        repo = self.make_repo()
        self.write_state(
            repo,
            """  compact_status: not_needed
  compact_skip_reason: none
  last_compact_result_file: none
goal_gate:
  required: true
  status: missing
  reason: long_running_multi_slice_execution
  suggested_goal: "/goal Complete DevFlow work with validation evidence and stop for human gates."
""",
        )

        validation = validate_workflow_state(repo)
        doctor = doctor_workflow(repo)

        self.assertTrue(validation["ok"], validation)
        self.assertTrue(
            any("Goal Suitability Gate requires an active goal" in warning for warning in validation["warnings"])
        )
        self.assertEqual(doctor["diagnosis"], "needs repair")
        self.assertTrue(any("Goal Suitability Gate requires an active goal" in issue for issue in doctor["issues"]))

    def test_goal_complexity_score_requires_goal_for_long_running_multi_slice_work(self):
        report = goal_complexity_score(
            open_spec_changes=2,
            capability_slices=3,
            prompt_text="依次进行接下来的开发和验证，直到需要人工介入或确认",
            governed_surfaces=["data model", "AI"],
            archive_or_release_gate=True,
            resume_or_compaction=True,
        )

        self.assertTrue(report["required"], report)
        self.assertEqual(report["status"], "required")
        self.assertGreaterEqual(report["score"], report["threshold"])

    def test_goal_complexity_score_does_not_require_goal_for_narrow_work(self):
        report = goal_complexity_score(prompt_text="Run the focused test once.")

        self.assertFalse(report["required"], report)
        self.assertFalse(report["recommended"], report)
        self.assertEqual(report["score"], 0)

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

    def test_hooks_use_plugin_root_paths_windows_commands_and_single_stop_entrypoint(self):
        hooks = json.loads((PLUGIN_ROOT / "hooks.json").read_text())["hooks"]
        commands = []
        for entries in hooks.values():
            for entry in entries:
                for hook in entry.get("hooks", []):
                    if hook.get("type") == "command":
                        commands.append(hook)

        self.assertTrue(commands)
        for hook in commands:
            command = hook["command"]
            self.assertIn("$PLUGIN_ROOT", command)
            self.assertNotIn("plugins/cache", command)
            self.assertIn("commandWindows", hook)
            self.assertIn("%PLUGIN_ROOT%", hook["commandWindows"])

        stop_hooks = hooks["Stop"][0]["hooks"]
        self.assertEqual(len(stop_hooks), 1)
        self.assertIn("devflow_stop_hook.py", stop_hooks[0]["command"])

    def test_hook_response_adapter_exposes_event_specific_payloads(self):
        adapter = importlib.import_module("hook_response_adapter")

        pre = adapter.deny_pre_tool_use("blocked", {"failed_gates": ["spec_approved"]})
        self.assertEqual(pre["decision"], "deny")
        self.assertEqual(pre["reason"], "blocked")
        self.assertEqual(pre["hookSpecificOutput"]["hookEventName"], "PreToolUse")

        stop = adapter.block_stop_continue("continue", {"failed_gates": ["verification_passed"]})
        self.assertEqual(stop["decision"], "block")
        self.assertEqual(stop["reason"], "continue")
        self.assertNotIn("hookSpecificOutput", stop)

        advisory = adapter.advisory("PostToolUse", "note", {"status": "warn"})
        self.assertEqual(advisory["hookSpecificOutput"]["hookEventName"], "PostToolUse")

    def test_devflow_stop_hook_aggregates_read_only_checks_without_release_apply(self):
        module = importlib.import_module("devflow_stop_hook")
        repo = self.make_repo()
        self.write_state(repo)

        with mock.patch.object(
            module, "context_health_check", return_value={"risk": "low", "decision": "continue"}
        ), mock.patch.object(
            module, "release_promotion_run_gate", return_value={"status": "pending", "message": "pending"}
        ) as gate, mock.patch.object(
            module, "release_sync_assets"
        ) as sync:
            report = module.run_stop_checks(repo)

        self.assertEqual(report["status"], "blocked")
        self.assertIn("release_promotion", report["failedChecks"])
        gate.assert_called_once_with(repo.resolve(), apply=False)
        sync.assert_not_called()

    def test_stop_hook_uses_ledger_completion_check(self):
        module = importlib.import_module("devflow_stop_hook")
        repo = self.make_repo()
        (repo / "TASK_LEDGER.md").write_text("| Task | Status |\n| --- | --- |\n| A | done |\n")

        check = module.ledger_completion_stop_check(repo)

        self.assertEqual(check["id"], "ledger_completion")
        self.assertNotIn("compatibilityAlias", check)
        self.assertTrue(check["ok"])

    def test_stop_hook_treats_current_ledger_work_statuses_as_incomplete(self):
        module = importlib.import_module("devflow_stop_hook")
        for status in ("todo", "in_progress", "planned", "executing", "review", "blocked"):
            with self.subTest(status=status):
                repo = self.make_repo()
                (repo / "TASK_LEDGER.md").write_text(
                    "| Task | Status |\n| --- | --- |\n" f"| A | {status} |\n"
                )

                check = module.ledger_completion_stop_check(repo)

                self.assertFalse(check["ok"])
                self.assertEqual(check["status"], "incomplete")

    def test_stop_hook_reads_only_the_markdown_status_column(self):
        module = importlib.import_module("devflow_stop_hook")
        repo = self.make_repo()
        (repo / "TASK_LEDGER.md").write_text(
            "| Task | Review Gate | Status |\n"
            "| --- | --- | --- |\n"
            "| A | review | done |\n"
        )

        check = module.ledger_completion_stop_check(repo)

        self.assertTrue(check["ok"])
        self.assertEqual(check["status"], "complete")

    def test_stop_hook_handles_escaped_pipes_before_incomplete_status_rows(self):
        module = importlib.import_module("devflow_stop_hook")
        repo = self.make_repo()
        (repo / "TASK_LEDGER.md").write_text(
            "| Task | Review Gate | Status |\n"
            "| --- | --- | --- |\n"
            "| A | schema \\| contract | done |\n"
            "| B | review | in_progress |\n"
        )

        check = module.ledger_completion_stop_check(repo)

        self.assertFalse(check["ok"])
        self.assertEqual(check["status"], "incomplete")

    def test_stop_hook_fails_closed_for_empty_or_unknown_task_status(self):
        module = importlib.import_module("devflow_stop_hook")
        for status in ("", "mystery"):
            with self.subTest(status=status):
                repo = self.make_repo()
                (repo / "TASK_LEDGER.md").write_text(
                    "| Task | Status |\n"
                    "| --- | --- |\n"
                    f"| A | {status} |\n"
                )

                check = module.ledger_completion_stop_check(repo)

                self.assertFalse(check["ok"])
                self.assertEqual(check["status"], "incomplete")

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
        self.assertIn("routing.matrix.json", route["routing_matrix"])
        self.assertIn("mandatory-full-openspec", route["route_id"])

    def test_routing_matrix_uses_static_methodology_contract(self):
        routing = importlib.import_module("workflow_routing_matrix")
        methodology = importlib.import_module("workflow_methodology")

        matrix = routing.load_routing_matrix(PLUGIN_ROOT)
        self.assertEqual(matrix["schemaVersion"], 2)
        self.assertEqual(
            matrix["capabilityRegistry"],
            "workflow_methodology.py#CAPABILITY_ROUTES",
        )
        self.assertIn("behavior-change", routing.full_openspec_kinds(PLUGIN_ROOT))
        self.assertIn("routing.matrix.json", matrix["sourcePath"])
        self.assertEqual(
            methodology.route_capability("completion-proof")["skills"],
            ["verify-and-archive"],
        )

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
