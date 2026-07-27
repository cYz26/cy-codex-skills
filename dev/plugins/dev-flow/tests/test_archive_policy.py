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

from workflow_archive_policy import (  # noqa: E402
    archive_status,
    mutating_archive_command,
    read_archive_policy,
)
from workflow_spec_sync_evidence import (  # noqa: E402
    record_spec_sync,
    spec_snapshot,
    verify_spec_sync,
)


class ArchivePolicyTests(unittest.TestCase):
    def make_repo(self, *, tasks_complete=True, archive_allowed=False, sync_evidence=True):
        repo = Path(tempfile.mkdtemp(prefix="devflow-archive-policy-"))
        (repo / "AGENTS.md").write_text("# Instructions\n")
        (repo / "openspec" / "changes" / "demo" / "specs" / "demo").mkdir(parents=True)
        (repo / "openspec" / "config.yaml").write_text("schema: spec-driven\n")
        change = repo / "openspec" / "changes" / "demo"
        (change / "proposal.md").write_text("# Proposal\n")
        (change / "design.md").write_text("# Design\n")
        (change / "specs" / "demo" / "spec.md").write_text("## ADDED Requirements\n")
        (repo / "openspec" / "specs" / "demo").mkdir(parents=True)
        (repo / "openspec" / "specs" / "demo" / "spec.md").write_text(
            "# Demo specification\n"
        )
        task_mark = "x" if tasks_complete else " "
        (change / "tasks.md").write_text(f"- [{task_mark}] Implement demo\n")
        (repo / ".planning" / "devflow").mkdir(parents=True)
        (repo / ".planning" / "devflow" / "STATE.md").write_text(
            """---
workflow_version: 0.3.0
project_mode: brownfield
current_stage: review_or_archive
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
  archive_allowed: %s
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
""" % ("true" if archive_allowed else "false")
        )
        if sync_evidence:
            result = record_spec_sync(
                repo,
                "demo",
                command="openspec-sync-specs",
                result="pass",
            )
            self.assertTrue(result["ok"], result)
        return repo

    def run_pre_archive_policy(self, repo, command):
        payload = json.dumps(
            {"cwd": str(repo), "tool_name": "Bash", "tool_input": {"command": command}}
        )
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "pre_archive_policy.py")],
            input=payload,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_archive_policy_defaults_and_rejects_unknown_value(self):
        repo = self.make_repo()
        self.assertEqual(read_archive_policy(repo)["policy"], "confirm-on-risk")

        (repo / ".dev-flow.json").write_text(
            json.dumps({"archive": {"policy": "fast-and-loose"}})
        )
        policy = read_archive_policy(repo)
        self.assertEqual(policy["policy"], "confirm-on-risk")
        self.assertEqual(policy["ignoredPolicy"], "fast-and-loose")

    def test_invalid_or_legacy_config_cannot_enable_archive_policy(self):
        repo = self.make_repo(archive_allowed=True)
        (repo / ".dev-flow.json").write_text(
            json.dumps(
                {
                    "roadmap_provider": "gsd",
                    "archive": {"policy": "auto-after-explicit-request"},
                }
            )
        )

        policy = read_archive_policy(repo)
        report = archive_status(repo, "demo", explicit_request=True)

        self.assertEqual(policy["policy"], "confirm-on-risk")
        self.assertEqual(policy["configStatus"], "invalid")
        self.assertFalse(report["ready"], report)
        self.assertIn(
            "invalid_workflow_config",
            {item["code"] for item in report["risks"]},
        )

    def test_symlinked_config_cannot_enable_archive_policy(self):
        repo = self.make_repo(archive_allowed=True)
        outside = Path(tempfile.mkdtemp(prefix="devflow-archive-config-outside-"))
        external = outside / "config.json"
        external.write_text(
            json.dumps({"archive": {"policy": "auto-after-explicit-request"}})
        )
        (repo / ".dev-flow.json").symlink_to(external)

        policy = read_archive_policy(repo)
        report = archive_status(repo, "demo", explicit_request=True)

        self.assertEqual(policy["policy"], "confirm-on-risk")
        self.assertEqual(policy["configStatus"], "invalid")
        self.assertFalse(report["ready"], report)

    def test_obsolete_legacy_config_is_not_an_active_archive_source(self):
        repo = self.make_repo()
        (repo / ".codex-project-orchestrator.json").write_text(
            json.dumps({"archive": {"policy": "auto-after-explicit-request"}})
        )

        policy = read_archive_policy(repo)

        self.assertEqual(policy["policy"], "confirm-on-risk")
        self.assertEqual(policy["source"], "default")

    def test_archive_status_separates_readiness_from_explicit_approval(self):
        repo = self.make_repo(archive_allowed=True)

        pending = archive_status(repo, "demo")
        approved = archive_status(repo, "demo", explicit_request=True)

        self.assertTrue(pending["ready"], pending)
        self.assertTrue(pending["approvalRequired"], pending)
        self.assertFalse(pending["canArchive"], pending)
        self.assertTrue(approved["ready"], approved)
        self.assertFalse(approved["approvalRequired"], approved)
        self.assertTrue(approved["canArchive"], approved)

    def test_explicit_request_without_durable_authorization_cannot_archive(self):
        report = archive_status(
            self.make_repo(archive_allowed=False),
            "demo",
            explicit_request=True,
        )

        self.assertTrue(report["ready"], report)
        self.assertFalse(report["durableArchiveAuthorization"])
        self.assertTrue(report["approvalRequired"], report)
        self.assertFalse(report["canArchive"], report)

    def test_incomplete_tasks_block_archive_even_with_explicit_request(self):
        report = archive_status(
            self.make_repo(tasks_complete=False, archive_allowed=True),
            "demo",
            explicit_request=True,
            allow_risk=True,
        )

        self.assertFalse(report["ready"], report)
        self.assertFalse(report["canArchive"], report)
        self.assertIn("incomplete_tasks", {risk["code"] for risk in report["risks"]})

    def test_dirty_unrelated_planning_work_is_reported(self):
        repo = self.make_repo()
        plan = repo / ".planning" / "notes" / "PLAN.md"
        plan.parent.mkdir(parents=True)
        plan.write_text("# Plan\n")
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=DevFlow",
                "-c",
                "user.email=devflow@example.com",
                "commit",
                "-m",
                "fixture",
            ],
            cwd=repo,
            capture_output=True,
            check=True,
        )
        plan.write_text("# Changed plan\n")

        report = archive_status(repo, "demo")

        dirty = next(item for item in report["risks"] if item["code"] == "dirty_unrelated_worktree")
        self.assertIn(".planning/notes/PLAN.md", dirty["paths"])

    def test_missing_or_stale_spec_sync_evidence_blocks_archive(self):
        missing = self.make_repo(archive_allowed=True, sync_evidence=False)
        missing_report = archive_status(missing, "demo", explicit_request=True)

        self.assertFalse(missing_report["ready"], missing_report)
        self.assertIn(
            "specs_not_synchronized",
            {item["code"] for item in missing_report["risks"]},
        )

        stale = self.make_repo(archive_allowed=True)
        (stale / "openspec" / "specs" / "demo" / "spec.md").write_text("changed\n")
        stale_report = archive_status(stale, "demo", explicit_request=True)

        self.assertFalse(stale_report["ready"], stale_report)
        sync_risk = next(
            item for item in stale_report["risks"]
            if item["code"] == "specs_not_synchronized"
        )
        self.assertEqual(sync_risk["syncStatus"], "stale_evidence")

    def test_spec_sync_evidence_rejects_symlinked_receipt_parent(self):
        repo = self.make_repo(archive_allowed=True)
        local_root = repo / ".planning" / "devflow" / "spec-sync"
        outside_root = Path(tempfile.mkdtemp(prefix="devflow-sync-receipt-outside-"))
        local_root.replace(outside_root / "spec-sync")
        local_root.symlink_to(outside_root / "spec-sync", target_is_directory=True)

        report = verify_spec_sync(repo, "demo")

        self.assertFalse(report["ready"], report)
        self.assertEqual(report["status"], "missing_evidence")

    def test_archive_rejects_symlinked_external_state_tree(self):
        repo = self.make_repo(archive_allowed=True)
        outside = Path(tempfile.mkdtemp(prefix="devflow-archive-state-outside-"))
        self.addCleanup(lambda: shutil.rmtree(outside, ignore_errors=True))
        planning = repo / ".planning"
        planning.replace(outside / "planning")
        planning.symlink_to(outside / "planning", target_is_directory=True)

        report = archive_status(repo, "demo", explicit_request=True)

        self.assertFalse(report["ready"], report)
        self.assertFalse(report["durableArchiveAuthorization"], report)
        failed = next(
            item for item in report["risks"] if item["code"] == "failed_state_gates"
        )
        self.assertIn("verification_passed", failed["gates"])

    def test_spec_snapshot_rejects_symlinked_delta_and_main_spec_parents(self):
        for side in ("delta", "main"):
            with self.subTest(side=side):
                repo = self.make_repo(sync_evidence=False)
                if side == "delta":
                    root = repo / "openspec" / "changes" / "demo" / "specs"
                else:
                    root = repo / "openspec" / "specs" / "demo"
                outside = Path(tempfile.mkdtemp(prefix=f"devflow-sync-{side}-outside-"))
                moved = outside / root.name
                root.replace(moved)
                root.symlink_to(moved, target_is_directory=True)

                snapshot = spec_snapshot(repo, "demo")

                self.assertFalse(snapshot["ready"], snapshot)
                self.assertTrue(snapshot["missing"], snapshot)

    def test_archive_command_detection_distinguishes_read_only_and_mutating(self):
        for command in [
            "openspec status --change demo --json",
            "openspec validate demo --strict",
            "rg archive openspec/changes",
            "sed -n '1,80p' openspec/changes/demo/tasks.md",
        ]:
            with self.subTest(command=command):
                self.assertFalse(mutating_archive_command(command), command)
        for command in [
            "openspec archive demo --yes",
            "openspec-archive-change demo",
            "mv openspec/changes/demo openspec/changes/archive/2026-06-15-demo",
            "git mv openspec/changes/demo openspec/changes/archive/2026-06-15-demo",
            "rm -r openspec/changes/demo",
        ]:
            with self.subTest(command=command):
                self.assertTrue(mutating_archive_command(command), command)

    def test_pre_archive_policy_allows_read_only_inspection(self):
        result = self.run_pre_archive_policy(
            self.make_repo(),
            "rg archive openspec/changes/demo",
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_pre_archive_policy_blocks_incomplete_archive(self):
        repo = self.make_repo(tasks_complete=False)
        result = self.run_pre_archive_policy(
            repo,
            "openspec archive demo --yes",
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(set(payload), {"hookSpecificOutput"})
        self.assertEqual(
            set(payload["hookSpecificOutput"]),
            {
                "hookEventName",
                "permissionDecision",
                "permissionDecisionReason",
                "additionalContext",
            },
        )
        self.assertEqual(payload["hookSpecificOutput"]["permissionDecision"], "deny")
        report = archive_status(repo, "demo", explicit_request=False, allow_risk=False)
        self.assertIn(
            "incomplete_tasks",
            {risk["code"] for risk in report["risks"]},
        )

    def test_archive_hook_off_mode_disables_output(self):
        repo = self.make_repo(tasks_complete=False)
        (repo / ".dev-flow.json").write_text(json.dumps({"hook": {"mode": "off"}}))

        result = self.run_pre_archive_policy(repo, "openspec archive demo --yes")

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_clean_explicit_archive_command_is_allowed(self):
        result = self.run_pre_archive_policy(
            self.make_repo(archive_allowed=True),
            "openspec archive demo --yes",
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_clean_archive_command_without_durable_authorization_is_blocked(self):
        repo = self.make_repo(archive_allowed=False)
        result = self.run_pre_archive_policy(
            repo,
            "openspec archive demo --yes",
        )

        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["hookSpecificOutput"]["permissionDecision"], "deny")
        status = archive_status(repo, "demo", explicit_request=False, allow_risk=False)
        self.assertFalse(status["durableArchiveAuthorization"])
        self.assertTrue(status["approvalRequired"])


if __name__ == "__main__":
    unittest.main()
