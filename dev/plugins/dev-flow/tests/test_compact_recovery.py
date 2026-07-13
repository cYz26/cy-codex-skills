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

from workflow_compact_recovery import handle_compact_recovery_event
from workflow_state import parse_state


class CompactRecoveryTests(unittest.TestCase):
    def make_repo(self, *, status="pending", checkpoint_id="checkpoint-one"):
        repo = Path(tempfile.mkdtemp(prefix="devflow-compact-recovery-"))
        self.addCleanup(lambda: shutil.rmtree(repo, ignore_errors=True))
        checkpoint = repo / ".planning" / "devflow" / "checkpoints" / f"{checkpoint_id}.md"
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_text(
            "\n".join(
                [
                    "---",
                    f"checkpoint_id: {checkpoint_id}",
                    f"compact_status: {status}",
                    "---",
                    "",
                    "# Checkpoint",
                    "",
                ]
            )
        )
        (repo / ".planning" / "devflow" / "STATE.md").write_text(
            f"""---
workflow_version: 0.3.0
project_mode: brownfield
current_stage: review_or_archive
current_phase:
  id: 01-foundation
  status: verification_passed
current_change:
  id: compact-fixture
  status: verified
gates:
  workflow_initialized: true
  spec_approved: true
  plan_written: true
  tests_baseline_known: true
  implementation_done: true
  verification_passed: true
  state_updated: true
  archive_allowed: false
context_management:
  compact_policy: checkpoint_boundary
  last_checkpoint_id: {checkpoint_id}
  last_checkpoint_file: .planning/devflow/checkpoints/{checkpoint_id}.md
  compact_recommended: true
  compact_status: {status}
  last_compact_result_file: none
  compact_source: checkpoint
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
# State
"""
        )
        return repo

    def test_manual_post_compact_records_completed_compact(self):
        repo = self.make_repo()

        report = handle_compact_recovery_event(
            repo,
            "post_compact",
            {
                "trigger": "manual",
                "session_id": "session-1",
                "turn_id": "turn-1",
                "model": "gpt-test",
            },
        )

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["action"], "compact_completed")
        state = parse_state(repo)["context_management"]
        self.assertEqual(state["compact_status"], "completed")
        self.assertEqual(state["compact_source"], "cli")
        self.assertEqual(
            state["last_compact_result_file"],
            ".planning/devflow/compact-results/checkpoint-one.json",
        )
        result_file = repo / ".planning" / "devflow" / "compact-results" / "checkpoint-one.json"
        self.assertTrue(result_file.exists())
        result = json.loads(result_file.read_text())
        self.assertEqual(result["source"], "cli")
        self.assertIn("PostCompact", result["raw_result"])
        self.assertFalse((repo / ".dev-flow" / "compact-recovery" / "pending.json").exists())

    def test_auto_post_compact_is_ignored_by_default(self):
        repo = self.make_repo()

        report = handle_compact_recovery_event(repo, "post_compact", {"trigger": "auto"})

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["action"], "ignored_trigger")
        self.assertEqual(parse_state(repo)["context_management"]["compact_status"], "pending")
        self.assertFalse(
            (repo / ".planning" / "devflow" / "compact-results" / "checkpoint-one.json").exists()
        )

    def test_completed_state_does_not_record_again(self):
        repo = self.make_repo(status="completed")

        report = handle_compact_recovery_event(repo, "post_compact", {"trigger": "manual"})

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["action"], "state_not_pending")
        self.assertFalse(
            (repo / ".planning" / "devflow" / "compact-results" / "checkpoint-one.json").exists()
        )

    def test_missing_checkpoint_noops_without_state_change(self):
        repo = self.make_repo()
        (repo / ".planning" / "devflow" / "checkpoints" / "checkpoint-one.md").unlink()

        report = handle_compact_recovery_event(repo, "post_compact", {"trigger": "manual"})

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["action"], "checkpoint_unavailable")
        self.assertEqual(parse_state(repo)["context_management"]["compact_status"], "pending")

    def test_hook_script_accepts_post_compact_payload(self):
        repo = self.make_repo()
        script = PLUGIN_ROOT / "scripts" / "compact_recovery_hook.py"

        result = subprocess.run(
            [sys.executable, str(script), "--event", "post_compact", "--json"],
            input=json.dumps({"cwd": str(repo), "trigger": "manual"}),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["action"], "compact_completed")
        self.assertEqual(parse_state(repo)["context_management"]["compact_status"], "completed")


if __name__ == "__main__":
    unittest.main()
