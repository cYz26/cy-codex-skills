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

from workflow_checkpoint_validate import validate_checkpoint
from devflow_stop_hook import checkpoint_stop_check
from workflow_doctor import doctor_workflow
from workflow_validate import validate_workflow_state


class CheckpointCompactContractTests(unittest.TestCase):
    def make_repo(self, *, compact_status: str = "not_needed", skip_reason: str = "none") -> Path:
        repo = Path(tempfile.mkdtemp(prefix="devflow-checkpoint-contract-"))
        self.addCleanup(lambda: shutil.rmtree(repo, ignore_errors=True))
        (repo / "AGENTS.md").write_text("Project rules\n")
        (repo / "openspec").mkdir()
        (repo / "openspec" / "config.yaml").write_text("project: fixture\n")
        (repo / ".planning" / "devflow" / "compact-results").mkdir(parents=True)
        result_file = "none"
        if compact_status == "completed":
            result = repo / ".planning" / "devflow" / "compact-results" / "checkpoint-one.json"
            result.write_text("{}\n")
            result_file = ".planning/devflow/compact-results/checkpoint-one.json"
        (repo / ".planning" / "devflow" / "STATE.md").write_text(
            self.state_text(compact_status=compact_status, skip_reason=skip_reason, result_file=result_file)
        )
        return repo

    def state_text(self, *, compact_status: str, skip_reason: str, result_file: str) -> str:
        return f"""---
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
  tests_baseline_known: true
  implementation_done: false
  verification_passed: false
  state_updated: true
  archive_allowed: false

context_management:
  compact_policy: checkpoint_boundary
  last_checkpoint_id: checkpoint-one
  last_checkpoint_file: .planning/devflow/checkpoints/checkpoint-one.md
  compact_recommended: false
  compact_status: {compact_status}
  last_compact_result_file: {result_file}
  compact_source: checkpoint
  compact_updated_at: none
  compact_skip_reason: {skip_reason}
  compact_error: none
---

# Workflow State

## Current Status

Fixture state.
"""

    def test_unsupported_compact_status_is_validation_issue_and_doctor_recommends_repair(self):
        repo = self.make_repo(compact_status="recommended")

        validation = validate_workflow_state(repo, codex_home=repo / ".codex-home")

        self.assertFalse(validation["ok"])
        self.assertTrue(
            any("compact_status" in issue and "recommended" in issue for issue in validation["issues"]),
            validation,
        )
        self.assertTrue(
            any("pending" in issue and "blocked" in issue for issue in validation["issues"]),
            validation,
        )

        doctor = doctor_workflow(repo)
        self.assertEqual(doctor["diagnosis"], "needs repair")
        self.assertTrue(
            any("compact_status" in recommendation for recommendation in doctor["recommendations"]),
            doctor,
        )

    def test_supported_compact_status_values_keep_status_specific_semantics(self):
        supported = {
            "pending": "warning",
            "not_needed": "ok",
            "completed": "ok",
            "skipped": "ok",
            "failed": "ok",
            "blocked": "ok",
        }
        for status, expected in supported.items():
            with self.subTest(status=status):
                repo = self.make_repo(
                    compact_status=status,
                    skip_reason="context small after checkpoint" if status == "skipped" else "none",
                )

                validation = validate_workflow_state(repo, codex_home=repo / ".codex-home")

                compact_issues = [issue for issue in validation["issues"] if "compact_status" in issue]
                self.assertEqual(compact_issues, [], validation)
                if expected == "warning":
                    self.assertTrue(validation["warnings"], validation)
                else:
                    self.assertFalse(
                        any("compact_status" in warning for warning in validation["warnings"]),
                        validation,
                    )

    def test_pending_compact_does_not_emit_stop_block_response(self):
        repo = self.make_repo(compact_status="pending")

        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "stop_checkpoint_policy.py")],
            input=json.dumps({"cwd": str(repo)}),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result)
        self.assertEqual(result.stdout.strip(), "", result.stdout)
        self.assertEqual(result.stderr.strip(), "", result.stderr)

    def test_aggregate_stop_checkpoint_check_treats_pending_compact_as_advisory(self):
        pending_repo = self.make_repo(compact_status="pending")

        pending = checkpoint_stop_check(pending_repo)

        self.assertTrue(pending["ok"], pending)
        self.assertEqual(pending["status"], "pending")
        self.assertIn("advisory", pending["detail"])

        for status in ("failed", "blocked"):
            with self.subTest(status=status):
                broken = checkpoint_stop_check(self.make_repo(compact_status=status))
                self.assertFalse(broken["ok"], broken)
                self.assertEqual(broken["status"], status)
                self.assertIn("requires action", broken["detail"])

    def test_hand_written_checkpoint_with_required_sections_still_requires_canonical_frontmatter(self):
        repo = self.make_repo()
        checkpoint = repo / ".planning" / "devflow" / "checkpoints" / "manual.md"
        checkpoint.parent.mkdir(parents=True)
        checkpoint.write_text(
            """# Checkpoint: manual

## Current goal

Continue work.

## Completed work

- Some work.

## Durable context written

- .planning/devflow/STATE.md

## Key decisions

- Keep local state.

## Risks

- Manual checkpoint drift.

## Next action

Regenerate if invalid.
"""
        )

        report = validate_checkpoint(repo, ".planning/devflow/checkpoints/manual.md")

        self.assertFalse(report["valid"], report)
        self.assertFalse(report["compact_allowed"], report)
        self.assertIn("canonical_frontmatter", report["missing"])
        self.assertIn("create_checkpoint.py", report["repair"])
        self.assertIn("canonical checkpoint tool", report["repair"])


if __name__ == "__main__":
    unittest.main()
