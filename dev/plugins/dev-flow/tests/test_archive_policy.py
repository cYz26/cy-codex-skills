import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from workflow_archive_policy import (  # noqa: E402
    archive_status,
    mutating_archive_command,
    read_archive_policy,
)


class ArchivePolicyTests(unittest.TestCase):
    def make_repo(self, *, tasks_complete=True, archive_allowed=False):
        repo = Path(tempfile.mkdtemp(prefix="devflow-archive-policy-"))
        (repo / "AGENTS.md").write_text("# Instructions\n")
        (repo / "openspec" / "changes" / "demo" / "specs" / "demo").mkdir(parents=True)
        (repo / "openspec" / "config.yaml").write_text("schema: spec-driven\n")
        change = repo / "openspec" / "changes" / "demo"
        (change / "proposal.md").write_text("# Proposal\n")
        (change / "design.md").write_text("# Design\n")
        (change / "specs" / "demo" / "spec.md").write_text("## ADDED Requirements\n")
        task_mark = "x" if tasks_complete else " "
        (change / "tasks.md").write_text(f"- [{task_mark}] Implement demo\n")
        (repo / ".planning").mkdir()
        archive_text = "true" if archive_allowed else "false"
        (repo / ".planning" / "STATE.md").write_text(
            f"""---
workflow_version: 0.3.0
project_mode: brownfield
current_stage: review_or_archive
current_phase:
  id: none
  status: none
current_change:
  id: demo
  status: verified
gates:
  workflow_initialized: true
  spec_approved: true
  plan_written: true
  tests_baseline_known: true
  implementation_done: true
  verification_passed: true
  state_updated: true
  archive_allowed: {archive_text}
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
# State
"""
        )
        return repo

    def run_pre_archive_policy(self, repo, command):
        payload = json.dumps({"cwd": str(repo), "tool_name": "Bash", "tool_input": {"command": command}})
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "pre_archive_policy.py")],
            input=payload,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_archive_policy_defaults_to_confirm_on_risk(self):
        repo = self.make_repo()

        policy = read_archive_policy(repo)

        self.assertEqual(policy["policy"], "confirm-on-risk")
        self.assertEqual(policy["source"], "default")

    def test_invalid_archive_policy_falls_back_to_confirm_on_risk(self):
        repo = self.make_repo()
        (repo / ".dev-flow.json").write_text(json.dumps({"archive": {"policy": "fast-and-loose"}}))

        policy = read_archive_policy(repo)

        self.assertEqual(policy["policy"], "confirm-on-risk")
        self.assertEqual(policy["ignoredPolicy"], "fast-and-loose")

    def test_archive_status_separates_readiness_from_approval(self):
        repo = self.make_repo()

        report = archive_status(repo, "demo")

        self.assertTrue(report["ready"], report)
        self.assertTrue(report["approvalRequired"], report)
        self.assertFalse(report["canArchive"], report)
        self.assertEqual(report["policy"], "confirm-on-risk")

    def test_archive_status_allows_clean_explicit_archive_intent(self):
        repo = self.make_repo()

        report = archive_status(repo, "demo", explicit_request=True)

        self.assertTrue(report["ready"], report)
        self.assertFalse(report["approvalRequired"], report)
        self.assertTrue(report["canArchive"], report)
        self.assertEqual(report["nextAction"], "run_archive")

    def test_archive_status_requires_confirmation_for_incomplete_tasks(self):
        repo = self.make_repo(tasks_complete=False)

        report = archive_status(repo, "demo", explicit_request=True)

        self.assertTrue(report["approvalRequired"], report)
        self.assertFalse(report["canArchive"], report)
        self.assertIn("incomplete_tasks", {risk["code"] for risk in report["risks"]})

    def test_archive_status_reports_dirty_unrelated_worktree_risk(self):
        repo = self.make_repo()
        subprocess.run(["git", "init"], cwd=repo, text=True, capture_output=True, check=True)
        subprocess.run(["git", "add", "."], cwd=repo, text=True, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "fixture"],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        (repo / "src.py").write_text("dirty = True\n")

        report = archive_status(repo, "demo", explicit_request=True)

        self.assertTrue(report["approvalRequired"], report)
        self.assertIn("dirty_unrelated_worktree", {risk["code"] for risk in report["risks"]})

    def test_mutating_archive_detection_ignores_read_only_commands(self):
        read_only = [
            "openspec status --change demo --json",
            "openspec validate demo --strict",
            "rg archive openspec/changes",
            "sed -n '1,80p' openspec/changes/demo/tasks.md",
        ]

        for command in read_only:
            with self.subTest(command=command):
                self.assertFalse(mutating_archive_command(command), command)

    def test_mutating_archive_detection_flags_archive_operations(self):
        mutating = [
            "openspec archive demo --yes",
            "openspec-archive-change demo",
            "mv openspec/changes/demo openspec/changes/archive/2026-06-15-demo",
            "git mv openspec/changes/demo openspec/changes/archive/2026-06-15-demo",
            "rm -r openspec/changes/demo",
        ]

        for command in mutating:
            with self.subTest(command=command):
                self.assertTrue(mutating_archive_command(command), command)

    def test_pre_archive_policy_allows_read_only_change_inspection(self):
        repo = self.make_repo()

        result = self.run_pre_archive_policy(repo, "rg archive openspec/changes/demo")

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_pre_archive_policy_blocks_risky_archive_in_block_mode(self):
        repo = self.make_repo(tasks_complete=False)
        (repo / ".dev-flow.json").write_text(json.dumps({"hook": {"mode": "block"}}))

        result = self.run_pre_archive_policy(repo, "openspec archive demo --yes")

        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["hookSpecificOutput"]["hookEventName"], "PreToolUse")
        diagnostic = payload["hookSpecificOutput"]["diagnostic"]
        self.assertEqual(diagnostic["archiveStatus"]["policy"], "confirm-on-risk")
        self.assertIn("incomplete_tasks", {risk["code"] for risk in diagnostic["archiveStatus"]["risks"]})

    def test_confirm_on_risk_blocks_risky_archive_even_in_default_warn_mode(self):
        repo = self.make_repo(tasks_complete=False)

        result = self.run_pre_archive_policy(repo, "openspec archive demo --yes")

        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        diagnostic = payload["hookSpecificOutput"]["diagnostic"]
        self.assertEqual(diagnostic["decision"], "block")
        self.assertIn("incomplete_tasks", {risk["code"] for risk in diagnostic["archiveStatus"]["risks"]})

    def test_archive_hook_off_mode_disables_archive_policy_output(self):
        repo = self.make_repo(tasks_complete=False)
        (repo / ".dev-flow.json").write_text(json.dumps({"hook": {"mode": "off"}}))

        result = self.run_pre_archive_policy(repo, "openspec archive demo --yes")

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_pre_archive_policy_allows_clean_explicit_archive_command(self):
        repo = self.make_repo()

        result = self.run_pre_archive_policy(repo, "openspec archive demo --yes")

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
