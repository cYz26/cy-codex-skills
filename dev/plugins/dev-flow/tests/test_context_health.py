import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from workflow_context_health import (
    context_health_check,
    import_codex_sessions,
    read_context_health_events,
    record_context_health_event,
)
from context_health_hook import context_health_signature, should_prompt_context_health
from devflow_stop_hook import context_health_stop_check
from workflow_state import parse_state


def run_script(name, *args, input_text=None, cwd=PLUGIN_ROOT):
    script = PLUGIN_ROOT / "scripts" / name
    return subprocess.run(
        [sys.executable, str(script), *args],
        input=input_text,
        text=True,
        cwd=cwd,
        capture_output=True,
        check=False,
    )


class ContextHealthTests(unittest.TestCase):
    def make_repo(self):
        repo = Path(tempfile.mkdtemp(prefix="devflow-health-repo-"))
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=False)
        (repo / "AGENTS.md").write_text("Project rules\n")
        (repo / "openspec").mkdir()
        (repo / "openspec" / "config.yaml").write_text("project: fixture\n")
        (repo / ".planning").mkdir()
        (repo / ".planning" / "STATE.md").write_text(self.state_text())
        return repo

    def state_text(self, compact_status="not_needed", goal_summary="none"):
        return f"""---
workflow_version: 0.3.0
project_mode: brownfield
current_stage: executing

current_phase:
  id: 01-foundation
  status: planning

current_change:
  id: add-context-health-check
  status: planned

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
  last_checkpoint_id: none
  last_checkpoint_file: none
  compact_recommended: false
  compact_status: {compact_status}
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
  goal_summary: {goal_summary}
---

# Workflow State

## Current Status

Fixture state.

## Next Action

Continue fixture work.
"""

    def test_record_context_health_event_sanitizes_tool_bodies(self):
        repo = self.make_repo()

        event = record_context_health_event(
            repo,
            "post_tool_use",
            {
                "cwd": str(repo),
                "tool_name": "Bash",
                "tool_input": {"command": "python3 -m unittest tests/test_example.py --token SECRET_TOKEN"},
                "tool_response": {
                    "exit_code": 1,
                    "duration_ms": 1200,
                    "output": "SECRET_OUTPUT_SHOULD_NOT_BE_PERSISTED\n" * 4,
                },
            },
        )

        events_path = repo / ".dev-flow" / "context-health" / "events.jsonl"
        text = events_path.read_text()
        self.assertEqual(event["tool"], "Bash")
        self.assertEqual(event["command_category"], "test")
        self.assertEqual(event["status"], "fail")
        self.assertIn("command_hash", event)
        self.assertEqual(event["output_lines"], 4)
        self.assertNotIn("SECRET_OUTPUT_SHOULD_NOT_BE_PERSISTED", text)
        self.assertNotIn("SECRET_TOKEN", text)
        self.assertEqual(len(read_context_health_events(repo)), 1)

    def test_repeated_failed_command_recommends_reconciliation(self):
        repo = self.make_repo()
        payload = {
            "cwd": str(repo),
            "tool_name": "Bash",
            "tool_input": {"command": "python3 -m unittest tests/test_example.py"},
            "tool_response": {"exit_code": 1, "output": "failure\n"},
        }
        record_context_health_event(repo, "post_tool_use", payload)
        record_context_health_event(repo, "post_tool_use", payload)

        report = context_health_check(repo, {"current_objective": "Implement context health checks"})

        self.assertEqual(report["risk"], "medium")
        self.assertEqual(report["decision"], "reconcile")
        self.assertIn("repeated_command_failure", {signal["id"] for signal in report["signals"]})

    def test_pending_compact_is_high_risk(self):
        repo = self.make_repo()
        (repo / ".planning" / "STATE.md").write_text(self.state_text(compact_status="pending"))

        report = context_health_check(repo, {"current_objective": "Continue implementation"})

        self.assertEqual(report["risk"], "high")
        self.assertEqual(report["decision"], "checkpoint_compact")
        self.assertIn("compact_pending", {signal["id"] for signal in report["signals"]})

    def test_missing_goal_generates_goal_mode_prompt(self):
        repo = self.make_repo()
        (repo / "feature.py").write_text("print('changed')\n")
        subprocess.run(["git", "add", "AGENTS.md", "openspec/config.yaml"], cwd=repo, capture_output=True, check=False)
        subprocess.run(["git", "commit", "-m", "baseline"], cwd=repo, capture_output=True, check=False)

        report = context_health_check(
            repo,
            {
                "current_objective": "Add context health checks",
                "validation_commands": ["python3 -m unittest discover -s dev/plugins/dev-flow/tests"],
            },
        )

        self.assertEqual(report["goal"]["status"], "missing")
        self.assertIn("Goal Mode Prompt", report["goal"]["prompt"])
        self.assertIn("Add context health checks", report["goal"]["prompt"])
        self.assertIn("define-goal", report["goal"]["prompt"])
        self.assertIn("active goal", report["goal"]["prompt"])
        self.assertIn("Goal Suitability Gate", report["goal"]["prompt"])
        self.assertIn("Goal Quality Gate", report["goal"]["prompt"])
        self.assertIn("Achieve <outcome>", report["goal"]["prompt"])
        self.assertIn("before context-health drift", report["goal"]["prompt"])
        self.assertIn("/goal <objective>", report["goal"]["prompt"])
        self.assertIn("/goal pause", report["goal"]["prompt"])
        self.assertIn("/goal resume", report["goal"]["prompt"])
        self.assertIn("/goal clear", report["goal"]["prompt"])
        self.assertIn("features.goals", report["goal"]["prompt"])
        self.assertIn("codex features enable goals", report["goal"]["prompt"])
        self.assertNotIn("`codex goal`", report["goal"]["prompt"].lower())
        self.assertNotIn("codex goal --help", report["goal"]["prompt"].lower())
        self.assertIn("Scope", report["goal"]["prompt"])
        self.assertIn("Non-Goals", report["goal"]["prompt"])
        self.assertIn("Stop Conditions", report["goal"]["prompt"])

    def test_weak_goal_routes_to_define_goal_for_repair(self):
        repo = self.make_repo()
        (repo / ".planning" / "STATE.md").write_text(self.state_text(goal_summary="make progress"))

        report = context_health_check(
            repo,
            {
                "current_objective": "Integrate define-goal into DevFlow",
                "validation_commands": ["python3 -m unittest dev/plugins/dev-flow/tests/test_context_health.py"],
            },
        )

        self.assertEqual(report["goal"]["status"], "weak")
        self.assertIn("define-goal", report["goal"]["prompt"])
        self.assertIn("repair", report["goal"]["prompt"])
        self.assertIn("verification evidence", report["goal"]["prompt"])
        self.assertIn("scope boundaries", report["goal"]["prompt"])
        self.assertIn("Goal Quality Gate", report["goal"]["prompt"])

    def test_repeated_file_reads_recommend_explorer_subagent(self):
        repo = self.make_repo()
        for _ in range(4):
            record_context_health_event(
                repo,
                "pre_tool_use",
                {
                    "cwd": str(repo),
                    "tool_name": "Read",
                    "tool_input": {"file_path": str(repo / "dev/plugins/dev-flow/scripts/workflow_state.py")},
                },
            )

        report = context_health_check(repo, {"current_objective": "Diagnose workflow state drift"})

        self.assertEqual(report["subagents"]["recommendation"], "explorer")
        self.assertTrue(report["subagents"]["dispositionRequired"])
        self.assertEqual(report["subagents"]["disposition"], "pending")
        self.assertIn("accepted", report["subagents"]["allowedDispositions"])
        self.assertIn("recommendationId", report["subagents"])
        self.assertIn("workflow_state.py", " ".join(report["subagents"]["scoped_files"]))
        self.assertIn("Agent Task Contract", report["subagents"]["prompt"])
        self.assertIn("Do not edit files", report["subagents"]["prompt"])
        for phrase in [
            "## Goal",
            "## Scope",
            "## Constraints",
            "## Verification",
            "## Evidence",
            "## Human Gate",
            "DONE",
            "DONE_WITH_CONCERNS",
            "NEEDS_CONTEXT",
            "BLOCKED",
            "files changed or inspected",
            "commands or tests run",
            "residual risks",
            "review needs",
        ]:
            self.assertIn(phrase, report["subagents"]["prompt"])

    def test_pending_subagent_recommendation_requires_disposition_before_acknowledgement(self):
        repo = self.make_repo()
        for _ in range(4):
            record_context_health_event(
                repo,
                "pre_tool_use",
                {
                    "cwd": str(repo),
                    "tool_name": "Read",
                    "tool_input": {"file_path": str(repo / "AGENTS.md")},
                },
            )

        first_report = context_health_check(
            repo,
            {
                "current_objective": "Resolve repeated context-health reads",
                "write_report": True,
            },
        )
        self.assertEqual(first_report["subagents"]["disposition"], "pending")

        current_report = context_health_check(repo)

        self.assertTrue(should_prompt_context_health(repo, current_report))
        stop_check = context_health_stop_check(repo)
        self.assertEqual(stop_check["pendingRecommendations"][0]["id"], current_report["subagents"]["recommendationId"])
        self.assertEqual(stop_check["pendingRecommendations"][0]["disposition"], "pending")

    def test_resolved_subagent_recommendation_is_reused_from_last_report(self):
        repo = self.make_repo()
        for _ in range(4):
            record_context_health_event(
                repo,
                "pre_tool_use",
                {
                    "cwd": str(repo),
                    "tool_name": "Read",
                    "tool_input": {"file_path": str(repo / "AGENTS.md")},
                },
            )
        report = context_health_check(
            repo,
            {
                "current_objective": "Resolve repeated context-health reads",
                "write_report": True,
            },
        )
        report_path = repo / report["report_file"]
        report["subagents"]["disposition"] = "accepted"
        report["subagents"]["dispositionNote"] = "Accepted for read-only investigation."
        report_path.write_text(json.dumps(report, indent=2))

        current_report = context_health_check(repo)

        self.assertEqual(current_report["subagents"]["disposition"], "accepted")
        self.assertFalse(should_prompt_context_health(repo, current_report))

    def test_record_context_health_disposition_cli_marks_report_accepted(self):
        repo = self.make_repo()
        for _ in range(4):
            record_context_health_event(
                repo,
                "pre_tool_use",
                {
                    "cwd": str(repo),
                    "tool_name": "Read",
                    "tool_input": {"file_path": str(repo / "AGENTS.md")},
                },
            )
        report = context_health_check(
            repo,
            {
                "current_objective": "Resolve repeated context-health reads",
                "write_report": True,
            },
        )
        recommendation_id = report["subagents"]["recommendationId"]

        result = run_script(
            "record_context_health_disposition.py",
            "--repo",
            str(repo),
            "--recommendation-id",
            recommendation_id,
            "--disposition",
            "accepted",
            "--note",
            "Accepted for read-only investigation.",
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"], payload)
        self.assertEqual(payload["recommendationId"], recommendation_id)
        self.assertEqual(payload["disposition"], "accepted")
        report_path = repo / report["report_file"]
        updated = json.loads(report_path.read_text())
        self.assertEqual(updated["subagents"]["disposition"], "accepted")
        self.assertEqual(
            updated["subagents"]["dispositionNote"],
            "Accepted for read-only investigation.",
        )
        self.assertIn("dispositionRecordedAt", updated["subagents"])

        current_report = context_health_check(repo)
        self.assertEqual(current_report["subagents"]["disposition"], "accepted")
        self.assertFalse(should_prompt_context_health(repo, current_report))

    def test_record_context_health_disposition_cli_requires_note(self):
        repo = self.make_repo()
        for _ in range(4):
            record_context_health_event(
                repo,
                "pre_tool_use",
                {
                    "cwd": str(repo),
                    "tool_name": "Read",
                    "tool_input": {"file_path": str(repo / "AGENTS.md")},
                },
            )
        report = context_health_check(
            repo,
            {
                "current_objective": "Resolve repeated context-health reads",
                "write_report": True,
            },
        )

        result = run_script(
            "record_context_health_disposition.py",
            "--repo",
            str(repo),
            "--recommendation-id",
            report["subagents"]["recommendationId"],
            "--disposition",
            "accepted",
            "--json",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--note is required", result.stderr)

    def test_stop_hook_does_not_repeat_medium_prompt_for_acknowledged_report(self):
        repo = self.make_repo()
        (repo / ".planning" / "STATE.md").write_text(self.state_text(goal_summary="Previous goal"))
        for _ in range(4):
            record_context_health_event(
                repo,
                "pre_tool_use",
                {
                    "cwd": str(repo),
                    "tool_name": "Read",
                    "tool_input": {"file_path": str(repo / "AGENTS.md")},
                },
            )
        first_report = context_health_check(
            repo,
            {
                "current_objective": "Resolve repeated DevFlow Stop hook prompts",
                "write_report": True,
            },
        )

        self.assertEqual(first_report["risk"], "medium")
        self.assertEqual(first_report["goal"]["status"], "stale")
        first_report["subagents"]["disposition"] = "accepted"
        first_report["subagents"]["dispositionNote"] = "Handled by the main agent."
        (repo / first_report["report_file"]).write_text(json.dumps(first_report, indent=2))
        self.assertFalse(should_prompt_context_health(repo, context_health_check(repo)))

        (repo / "new_production_file.py").write_text("print('changed')\n")

        self.assertTrue(should_prompt_context_health(repo, context_health_check(repo)))

    def test_stop_hook_records_new_medium_report_without_feedback_when_acknowledged(self):
        repo = self.make_repo()
        for _ in range(4):
            record_context_health_event(
                repo,
                "pre_tool_use",
                {
                    "cwd": str(repo),
                    "tool_name": "Read",
                    "tool_input": {"file_path": str(repo / "AGENTS.md")},
                },
            )
        acknowledged = context_health_check(
            repo,
            {
                "current_objective": "Resolve repeated DevFlow Stop hook prompts",
                "write_report": True,
            },
        )
        acknowledged["subagents"]["disposition"] = "accepted"
        acknowledged["subagents"]["dispositionNote"] = "Handled by the main agent."
        (repo / acknowledged["report_file"]).write_text(json.dumps(acknowledged, indent=2))

        result = run_script(
            "context_health_hook.py",
            "--event",
            "stop",
            "--check",
            input_text=json.dumps({"cwd": str(repo)}),
            cwd=repo,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        state = parse_state(repo)
        last_report = state["context_health"]["last_report"]
        self.assertNotEqual(last_report, "none")
        report = json.loads((repo / last_report).read_text())
        self.assertEqual(report["risk"], "medium")
        self.assertEqual(
            context_health_signature(report),
            context_health_signature(context_health_check(repo)),
        )
        self.assertIn("Fixture state.", state["body"])
        self.assertIn("Continue fixture work.", state["body"])

    def test_high_context_health_stop_hook_still_emits_block_feedback(self):
        repo = self.make_repo()
        (repo / ".planning" / "STATE.md").write_text(self.state_text(compact_status="pending"))

        result = run_script(
            "context_health_hook.py",
            "--event",
            "stop",
            "--check",
            input_text=json.dumps({"cwd": str(repo)}),
            cwd=repo,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["decision"], "block")
        self.assertIn("context health is high", payload["reason"])
        self.assertNotIn("hookSpecificOutput", payload)

    def test_medium_context_health_without_acknowledged_report_still_prompts(self):
        repo = self.make_repo()
        report = {
            "risk": "medium",
            "decision": "reconcile",
            "signals": [{"id": "repeated_file_read", "severity": "medium"}],
            "repo_truth": {"changed_files": ["AGENTS.md"]},
        }

        self.assertTrue(should_prompt_context_health(repo, report))

    def test_import_codex_sessions_is_best_effort_and_sanitized(self):
        repo = self.make_repo()
        codex_home = Path(tempfile.mkdtemp(prefix="devflow-codex-home-"))
        session = codex_home / "sessions" / "2026" / "05" / "27" / "session-test.jsonl"
        session.parent.mkdir(parents=True)
        session.write_text(
            json.dumps(
                {
                    "cwd": str(repo),
                    "timestamp": "2026-05-27T12:00:00+08:00",
                    "tool_name": "Bash",
                    "tool_input": {"command": "pytest tests/test_example.py"},
                    "tool_response": {"exit_code": 0, "output": "SECRET_SESSION_OUTPUT"},
                }
            )
            + "\n"
            + json.dumps(
                {
                    "tool_name": "Bash",
                    "tool_input": {"command": "pytest unrelated.py"},
                    "tool_response": {"exit_code": 0, "output": "SECRET_NO_CWD_OUTPUT"},
                }
            )
            + "\n"
            + json.dumps(
                {
                    "cwd": str(repo.parent / "other-repo"),
                    "tool_name": "Bash",
                    "tool_input": {"command": "pytest unrelated.py"},
                    "tool_response": {"exit_code": 0, "output": "SECRET_OTHER_REPO_OUTPUT"},
                }
            )
            + "\n"
        )

        report = import_codex_sessions(repo, codex_home)
        imported_path = repo / ".dev-flow" / "context-health" / "imported-events.jsonl"
        imported_text = imported_path.read_text()

        self.assertEqual(report["coverage"], "partial")
        self.assertEqual(report["confidence"], "low")
        self.assertEqual(report["imported_events"], 1)
        self.assertNotIn("SECRET_SESSION_OUTPUT", imported_text)
        self.assertNotIn("SECRET_NO_CWD_OUTPUT", imported_text)
        self.assertNotIn("SECRET_OTHER_REPO_OUTPUT", imported_text)

    def test_context_health_cli_writes_report(self):
        repo = self.make_repo()

        result = run_script(
            "context_health_check.py",
            "--repo",
            str(repo),
            "--current-objective",
            "Implement context health checks",
            "--write-report",
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["report_file"].startswith(".planning/context-health/reports/"))
        self.assertTrue((repo / payload["report_file"]).exists())


if __name__ == "__main__":
    unittest.main()
