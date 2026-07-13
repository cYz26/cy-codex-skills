import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from workflow_archive_policy import (  # noqa: E402
    archive_status,
    mutating_archive_command,
    read_archive_policy,
)
from workflow_roadmap_provider import persist_archived_roadmap_binding  # noqa: E402
from workflow_verification import (  # noqa: E402
    gsd_verification_status,
    record_gsd_verification,
)


class StubGsdAdapter:
    def __init__(self, *, phase="02-core", directory=".planning/phases/02-core", phase_number="02"):
        self.phase = phase
        self.directory = directory
        self.phase_number = phase_number

    def roadmap_get_phase(self, phase):
        return {
            "ok": True,
            "data": {"found": phase == self.phase, "phase_number": self.phase_number},
        }

    def find_phase(self, phase):
        return {
            "ok": True,
            "data": {
                "found": phase == self.phase,
                "directory": self.directory,
                "phase_number": self.phase_number,
            },
        }


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
        (repo / ".planning" / "devflow").mkdir(parents=True)
        archive_text = "true" if archive_allowed else "false"
        (repo / ".planning" / "devflow" / "STATE.md").write_text(
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

    def write_gsd_uat(
        self,
        repo,
        *,
        status="complete",
        phase="02-core",
        result="pass",
        gaps="",
    ):
        path = repo / ".planning" / "phases" / "02-core" / "02-UAT.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"""---
status: {status}
phase: {phase}
source: [02-01-SUMMARY.md]
started: 2026-07-10T00:00:00Z
updated: 2026-07-10T00:01:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Demo behavior
expected: Demo behavior is visible
result: {result}

## Summary

total: 1
passed: {1 if result == 'pass' else 0}
issues: {1 if result == 'issue' else 0}
pending: {1 if result == 'pending' else 0}
skipped: {1 if result == 'skipped' else 0}
blocked: {1 if result == 'blocked' else 0}

## Gaps

{gaps}
"""
        )
        return path

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

    def test_active_gsd_binding_requires_gsd_verification_before_archive(self):
        repo = self.make_repo()
        (repo / ".dev-flow.json").write_text(
            json.dumps(
                {
                    "workflow": {
                        "methodology_profile": "core",
                        "roadmap_provider": "gsd",
                        "roadmap_bindings": {
                            "demo": {
                                "phase_id": "02-core",
                                "milestone": "v1",
                                "status": "active",
                            }
                        },
                    }
                }
            )
        )

        report = archive_status(repo, "demo", explicit_request=True)

        codes = {item["code"] for item in report["risks"]}
        self.assertIn("roadmap_binding_invalid", codes)
        self.assertIn("gsd_verification_required", codes)
        self.assertFalse(report["ready"])

    def test_bound_gsd_verification_evidence_enables_archive_readiness(self):
        repo = self.make_repo()
        (repo / ".dev-flow.json").write_text(
            json.dumps(
                {
                    "workflow": {
                        "methodology_profile": "core",
                        "roadmap_provider": "gsd",
                        "roadmap_bindings": {
                            "demo": {
                                "phase_id": "02-core",
                                "milestone": "v1",
                                "status": "active",
                            }
                        },
                    }
                }
            )
        )
        self.write_gsd_uat(repo)

        evidence = record_gsd_verification(
            repo,
            change="demo",
            phase="02-core",
            command="gsd-verify-work --phase 02-core",
            result="pass",
            notes="Conversational UAT passed.",
            adapter=StubGsdAdapter(),
        )
        with mock.patch(
            "workflow_archive_policy.validate_roadmap_bindings",
            return_value={"ready": True, "blockingReasons": []},
        ):
            report = archive_status(repo, "demo", explicit_request=True)

        self.assertTrue(evidence["ok"], evidence)
        self.assertTrue((repo / evidence["path"]).exists())
        self.assertNotIn("gsd_verification_required", {item["code"] for item in report["risks"]})
        self.assertTrue(report["ready"], report)

    def test_gsd_verification_rejects_phase_not_matching_active_binding(self):
        repo = self.make_repo()
        (repo / ".dev-flow.json").write_text(
            json.dumps(
                {
                    "workflow": {
                        "roadmap_provider": "gsd",
                        "roadmap_bindings": {
                            "demo": {"phase_id": "02-core", "status": "active"}
                        },
                    }
                }
            )
        )

        result = record_gsd_verification(
            repo,
            change="demo",
            phase="03-wrong",
            command="gsd-verify-work --phase 03-wrong",
            result="pass",
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "binding_phase_mismatch")
        self.assertFalse(any((repo / ".planning" / "devflow" / "verification").glob("*gsd*")))

    def test_gsd_verification_does_not_trust_caller_command_or_result(self):
        repo = self.make_repo()
        (repo / ".dev-flow.json").write_text(
            json.dumps(
                {
                    "workflow": {
                        "roadmap_provider": "gsd",
                        "roadmap_bindings": {
                            "demo": {"phase_id": "02-core", "status": "active"}
                        },
                    }
                }
            )
        )

        (repo / ".planning" / "phases" / "02-core").mkdir(parents=True)
        spoofed = record_gsd_verification(
            repo,
            change="demo",
            phase="02-core",
            command="echo pass",
            result="pass",
            notes="UAT passed.",
            adapter=StubGsdAdapter(),
        )
        self.assertEqual(spoofed["status"], "uat_artifact_missing")

        uat = self.write_gsd_uat(repo)
        recorded = record_gsd_verification(
            repo,
            change="demo",
            phase="02-core",
            command="echo fake verifier",
            result="fail",
            adapter=StubGsdAdapter(),
        )

        self.assertTrue(recorded["ok"], recorded)
        self.assertEqual(recorded["result"], "pass")
        self.assertEqual(recorded["uatArtifact"], uat.relative_to(repo).as_posix())
        self.assertEqual(len(recorded["uatSha256"]), 64)
        self.assertTrue(recorded["callerInputIgnored"])

    def test_gsd_verification_fails_closed_on_incomplete_or_mismatched_uat(self):
        cases = (
            ({"status": "partial"}, "uat_status_not_complete"),
            ({"phase": "03-wrong"}, "uat_phase_mismatch"),
            ({"result": "pending"}, "uat_tests_not_passed"),
            ({"result": "issue"}, "uat_tests_not_passed"),
            ({"result": "blocked"}, "uat_tests_not_passed"),
            (
                {
                    "gaps": '- truth: "Demo behavior"\n  status: failed\n  reason: unresolved\n',
                },
                "uat_unresolved_gaps",
            ),
        )
        for overrides, expected in cases:
            with self.subTest(expected=expected):
                repo = self.make_repo()
                (repo / ".dev-flow.json").write_text(
                    json.dumps(
                        {
                            "workflow": {
                                "roadmap_provider": "gsd",
                                "roadmap_bindings": {
                                    "demo": {"phase_id": "02-core", "status": "active"}
                                },
                            }
                        }
                    )
                )
                self.write_gsd_uat(repo, **overrides)

                result = record_gsd_verification(
                    repo,
                    change="demo",
                    phase="02-core",
                    command="gsd-verify-work --phase 02-core",
                    result="pass",
                    adapter=StubGsdAdapter(),
                )

                self.assertFalse(result["ok"], result)
                self.assertEqual(result["status"], expected)

    def test_gsd_verification_status_detects_uat_drift_after_recording(self):
        repo = self.make_repo()
        (repo / ".dev-flow.json").write_text(
            json.dumps(
                {
                    "workflow": {
                        "roadmap_provider": "gsd",
                        "roadmap_bindings": {
                            "demo": {"phase_id": "02-core", "status": "active"}
                        },
                    }
                }
            )
        )
        uat = self.write_gsd_uat(repo)
        adapter = StubGsdAdapter()
        recorded = record_gsd_verification(
            repo,
            change="demo",
            phase="02-core",
            command="ignored",
            result="pass",
            adapter=adapter,
        )
        self.assertTrue(recorded["ok"], recorded)
        self.assertTrue(gsd_verification_status(repo, change="demo", phase="02-core", adapter=adapter)["verified"])

        uat.write_text(uat.read_text().replace("result: pass", "result: issue"))
        status = gsd_verification_status(repo, change="demo", phase="02-core", adapter=adapter)

        self.assertFalse(status["verified"])
        self.assertEqual(status["status"], "uat_tests_not_passed")

    def test_archived_binding_action_derives_all_gates_from_canonical_artifacts(self):
        repo = self.make_repo()
        config_path = repo / ".dev-flow.json"
        config_path.write_text(
            json.dumps(
                {
                    "workflow": {
                        "methodology_profile": "core",
                        "roadmap_provider": "gsd",
                        "roadmap_bindings": {
                            "demo": {
                                "phase_id": "02-core",
                                "milestone": "v1",
                                "status": "active",
                            }
                        },
                    }
                },
                indent=2,
            )
            + "\n"
        )
        self.write_gsd_uat(repo)
        adapter = StubGsdAdapter()
        recorded = record_gsd_verification(
            repo,
            change="demo",
            phase="02-core",
            adapter=adapter,
        )
        self.assertTrue(recorded["ok"], recorded)
        archive = repo / "openspec" / "changes" / "archive" / "2026-07-10-demo"
        archive.parent.mkdir(parents=True)
        (repo / "openspec" / "changes" / "demo").rename(archive)

        planned = persist_archived_roadmap_binding(repo, "demo", adapter=adapter)
        self.assertTrue(planned["ok"], planned)
        self.assertEqual(planned["status"], "planned")
        gate_names = ("openspec_verified", "openspec_archived", "gsd_verified")
        self.assertTrue(all(planned["gates"][name] for name in gate_names))
        persisted = json.loads(config_path.read_text())
        self.assertEqual(persisted["workflow"]["roadmap_bindings"]["demo"]["status"], "active")

        applied = persist_archived_roadmap_binding(
            repo,
            "demo",
            apply=True,
            authorized=True,
            adapter=adapter,
        )

        self.assertTrue(applied["ok"], applied)
        self.assertEqual(applied["status"], "archived")
        persisted = json.loads(config_path.read_text())
        self.assertEqual(persisted["workflow"]["roadmap_bindings"]["demo"]["status"], "archived")

    def test_dirty_gsd_phase_is_not_hidden_as_generic_archive_scope(self):
        repo = self.make_repo()
        phase = repo / ".planning" / "phases" / "02-core" / "02-01-PLAN.md"
        phase.parent.mkdir(parents=True)
        phase.write_text("# Plan\n")
        subprocess.run(["git", "init"], cwd=repo, text=True, capture_output=True, check=True)
        subprocess.run(["git", "add", "."], cwd=repo, text=True, capture_output=True, check=True)
        subprocess.run(
            ["git", "-c", "user.name=DevFlow", "-c", "user.email=devflow@example.com", "commit", "-m", "fixture"],
            cwd=repo,
            text=True,
            capture_output=True,
            check=True,
        )
        phase.write_text("# Changed plan\n")

        report = archive_status(repo, "demo")

        dirty = next(item for item in report["risks"] if item["code"] == "dirty_unrelated_worktree")
        self.assertIn(".planning/phases/02-core/02-01-PLAN.md", dirty["paths"])

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
