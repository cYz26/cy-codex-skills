import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = PLUGIN_ROOT / "fixtures"
MARKETPLACE = next(
    path for path in [PLUGIN_ROOT, *PLUGIN_ROOT.parents] if (path / ".agents" / "plugins" / "marketplace.json").exists()
) / ".agents" / "plugins" / "marketplace.json"
REPO_ROOT = MARKETPLACE.parents[2]
DEV_MARKETPLACE = REPO_ROOT / ".agents" / "plugins" / "marketplace.dev.json"
RELEASE_PLUGIN_ROOT = REPO_ROOT / "plugins" / "codex-project-orchestrator"


def registered_plugin_path(marketplace_path, plugin_name):
    marketplace = json.loads(marketplace_path.read_text())
    entry = next(item for item in marketplace["plugins"] if item["name"] == plugin_name)
    return (marketplace_path.parents[2] / entry["source"]["path"]).resolve(), entry


def run_script(name, *args, input_text=None, cwd=PLUGIN_ROOT):
    script = PLUGIN_ROOT / "scripts" / name
    result = subprocess.run(
        [sys.executable, str(script), *args],
        input=input_text,
        text=True,
        cwd=cwd,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"{name} failed with {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def run_json(name, *args, input_text=None, cwd=PLUGIN_ROOT):
    result = run_script(name, *args, input_text=input_text, cwd=cwd)
    return json.loads(result.stdout)


class ProjectOrchestratorTests(unittest.TestCase):
    def make_repo(self, fixture_name=None):
        tmp = Path(tempfile.mkdtemp(prefix="cpo-test-"))
        if fixture_name:
            source = FIXTURES / fixture_name
            shutil.copytree(source, tmp, dirs_exist_ok=True)
        return tmp

    def create_pending_checkpoint(self, repo):
        return run_json(
            "create_checkpoint.py",
            "--repo",
            str(repo),
            "--boundary",
            "project_setup_completed",
            "--next-stage",
            "feature_intake",
            "--current-goal",
            "Initialize workflow",
            "--completed-work",
            "Created workflow scaffold",
            "--risk",
            "No validation baseline yet",
            "--json",
        )

    def test_manifest_marketplace_assets_and_hooks_are_declared(self):
        manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text())
        self.assertEqual(manifest["name"], "codex-project-orchestrator")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(manifest["hooks"], "./hooks.json")
        self.assertEqual(manifest["interface"]["category"], "Coding")
        self.assertTrue((PLUGIN_ROOT / manifest["interface"]["logo"]).exists())
        self.assertTrue((PLUGIN_ROOT / manifest["interface"]["composerIcon"]).exists())
        self.assertTrue((PLUGIN_ROOT / "hooks.json").exists())

        release_path, entry = registered_plugin_path(MARKETPLACE, "codex-project-orchestrator")
        self.assertEqual(release_path, RELEASE_PLUGIN_ROOT.resolve())
        self.assertEqual(entry["category"], "Coding")
        self.assertTrue((RELEASE_PLUGIN_ROOT / ".codex-plugin" / "plugin.json").exists())
        self.assertTrue((RELEASE_PLUGIN_ROOT / "hooks.json").exists())
        self.assertFalse((RELEASE_PLUGIN_ROOT / "tests").exists())
        self.assertFalse((RELEASE_PLUGIN_ROOT / "fixtures").exists())
        self.assertFalse((RELEASE_PLUGIN_ROOT / "log").exists())

        dev_path, dev_entry = registered_plugin_path(DEV_MARKETPLACE, "codex-project-orchestrator")
        self.assertEqual(dev_path, PLUGIN_ROOT.resolve())
        self.assertEqual(dev_entry["category"], "Coding")

    def test_all_expected_skills_have_codex_frontmatter(self):
        expected = {
            "project-orchestrator",
            "project-setup",
            "checkpoint-compact",
            "feature-intake",
            "change-plan",
            "execute-task",
            "verify-and-archive",
            "workflow-doctor",
            "context-tool-audit",
        }
        self.assertEqual({path.name for path in (PLUGIN_ROOT / "skills").iterdir() if path.is_dir()}, expected)
        for skill in expected:
            text = (PLUGIN_ROOT / "skills" / skill / "SKILL.md").read_text()
            self.assertTrue(text.startswith("---\n"), skill)
            self.assertIn(f"name: {skill}", text)
            self.assertRegex(text, r"description: .+")

    def test_detect_project_mode_greenfield_brownfield_and_uncertain(self):
        empty = self.make_repo("greenfield-empty")
        readme_only = self.make_repo("greenfield-minimal-readme")
        node = self.make_repo("brownfield-node")
        python = self.make_repo("brownfield-python")
        uncertain = self.make_repo()
        (uncertain / ".git").mkdir()
        (uncertain / "docs").mkdir()
        (uncertain / "docs" / "notes.md").write_text("notes\n")

        self.assertEqual(
            run_json("detect_project_mode.py", "--repo", str(empty), "--json")["project_mode"],
            "greenfield",
        )
        self.assertEqual(
            run_json("detect_project_mode.py", "--repo", str(readme_only), "--json")["project_mode"],
            "greenfield",
        )
        self.assertEqual(
            run_json("detect_project_mode.py", "--repo", str(node), "--json")["project_mode"],
            "brownfield",
        )
        self.assertEqual(
            run_json("detect_project_mode.py", "--repo", str(python), "--json")["project_mode"],
            "brownfield",
        )
        uncertain_report = run_json("detect_project_mode.py", "--repo", str(uncertain), "--json")
        self.assertEqual(uncertain_report["project_mode"], "brownfield")
        self.assertEqual(uncertain_report["recommended_flow"], "brownfield-safe-setup")

    def test_scaffold_dry_run_and_greenfield_apply(self):
        repo = self.make_repo("greenfield-empty")
        dry = run_json("scaffold_workflow.py", "--repo", str(repo), "--dry-run", "--json")
        self.assertTrue(dry["dry_run"])
        self.assertGreater(len(dry["planned_writes"]), 5)
        self.assertFalse((repo / "AGENTS.md").exists())

        applied = run_json("scaffold_workflow.py", "--repo", str(repo), "--json")
        self.assertEqual(applied["project_mode"], "greenfield")
        self.assertTrue((repo / "AGENTS.md").exists())
        self.assertTrue((repo / ".planning" / "STATE.md").exists())
        self.assertTrue((repo / ".planning" / "phases" / "01-foundation" / "PLAN.md").exists())
        self.assertTrue((repo / "openspec" / "changes" / "initial-mvp" / "tasks.md").exists())
        self.assertTrue((repo / "setup-report.md").exists())
        state = (repo / ".planning" / "STATE.md").read_text()
        self.assertIn("context_management:", state)
        self.assertIn("compact_policy: checkpoint_boundary", state)
        agents = (repo / "AGENTS.md").read_text()
        self.assertIn("## Context Checkpoint and Compaction", agents)
        self.assertIn("## GSD/OpenSpec Skills", agents)
        self.assertIn("## Brainstorm and Planning Flow", agents)
        self.assertIn("superpowers:brainstorming", agents)
        self.assertIn("superpowers:writing-plans", agents)
        self.assertIn("openspec-propose", agents)
        self.assertIn("openspec-apply-change", agents)
        self.assertIn("openspec-archive-change", agents)
        self.assertIn("gsd-plan-phase", agents)
        self.assertIn("gsd-verify-work", agents)
        self.assertIn("## Superpowers Discipline", agents)
        self.assertIn("superpowers:test-driven-development", agents)
        self.assertIn("superpowers:verification-before-completion", agents)

        valid = run_json("validate_workflow_state.py", "--repo", str(repo), "--json")
        self.assertTrue(valid["ok"])
        self.assertFalse(valid["gates"]["archive_allowed"])

    def test_scaffold_preserves_existing_agents_and_adds_brownfield_docs(self):
        existing = self.make_repo("existing-agents")
        original = (existing / "AGENTS.md").read_text()
        result = run_json("scaffold_workflow.py", "--repo", str(existing), "--mode", "greenfield", "--json")
        self.assertIn("AGENTS.md.generated", result["written"])
        self.assertEqual((existing / "AGENTS.md").read_text(), original)

        brownfield = self.make_repo("brownfield-node")
        result = run_json("scaffold_workflow.py", "--repo", str(brownfield), "--json")
        self.assertEqual(result["project_mode"], "brownfield")
        for name in ["ARCHITECTURE.md", "CONVENTIONS.md", "COMMANDS.md", "RISKS.md"]:
            self.assertTrue((brownfield / ".planning" / "codebase" / name).exists(), name)
        self.assertTrue((brownfield / "openspec" / "specs" / "current-system" / "spec.md").exists())

    def test_orchestrator_skills_name_dependency_skills_explicitly(self):
        expectations = {
            "project-orchestrator": [
                "superpowers:brainstorming",
                "superpowers:writing-plans",
                "openspec-propose",
                "openspec-apply-change",
                "openspec-archive-change",
                "gsd-plan-phase",
                "gsd-verify-work",
                "superpowers:test-driven-development",
            ],
            "project-setup": ["audit_context_tools.py", "context-tool-audit"],
            "feature-intake": [
                "superpowers:brainstorming",
                "superpowers:writing-plans",
                "openspec-explore",
                "openspec-propose",
                "gsd-discuss-phase",
                "gsd-plan-phase",
            ],
            "change-plan": [
                "superpowers:brainstorming",
                "superpowers:writing-plans",
                "openspec-explore",
                "openspec-propose",
            ],
            "execute-task": ["openspec-apply-change", "superpowers:test-driven-development", "gsd-execute-phase"],
            "verify-and-archive": [
                "superpowers:verification-before-completion",
                "gsd-verify-work",
                "openspec-archive-change",
            ],
            "workflow-doctor": ["gsd-progress", "openspec-explore"],
            "context-tool-audit": ["audit_context_tools.py", "apply_context_tool_actions.py"],
        }
        for skill, names in expectations.items():
            text = (PLUGIN_ROOT / "skills" / skill / "SKILL.md").read_text()
            for name in names:
                self.assertIn(name, text, f"{skill} should mention {name}")

    def test_create_change_updates_state_and_validate_reports_missing_artifacts(self):
        repo = self.make_repo("greenfield-empty")
        run_json("scaffold_workflow.py", "--repo", str(repo), "--json")
        created = run_json(
            "create_change.py",
            "--repo",
            str(repo),
            "--change-id",
            "add-search",
            "--title",
            "Add search",
            "--type",
            "new-feature",
            "--json",
        )
        self.assertIn("openspec/changes/add-search/proposal.md", created["written"])
        state = (repo / ".planning" / "STATE.md").read_text()
        self.assertIn("id: add-search", state)

        valid = run_json("validate_workflow_state.py", "--repo", str(repo), "--json")
        self.assertTrue(valid["ok"])
        os.remove(repo / "openspec" / "changes" / "add-search" / "tasks.md")
        invalid = run_json("validate_workflow_state.py", "--repo", str(repo), "--json")
        self.assertFalse(invalid["ok"])
        self.assertTrue(any("tasks.md" in issue for issue in invalid["issues"]))

    def test_record_verification_and_doctor_workflow(self):
        repo = self.make_repo("brownfield-python")
        run_json("scaffold_workflow.py", "--repo", str(repo), "--json")
        recorded = run_json(
            "record_verification.py",
            "--repo",
            str(repo),
            "--command",
            "python3 -m pytest",
            "--result",
            "pass",
            "--notes",
            "fixture verification",
            "--json",
        )
        self.assertTrue((repo / recorded["path"]).exists())
        state = (repo / ".planning" / "STATE.md").read_text()
        self.assertIn("verification_passed: true", state)

        report = run_json("doctor_workflow.py", "--repo", str(repo), "--write-report", "--json")
        self.assertTrue((repo / "workflow-diagnosis.md").exists())
        self.assertIn("diagnosis", report)

    def test_create_validate_and_recommend_checkpoint_compact(self):
        repo = self.make_repo("greenfield-empty")
        run_json("scaffold_workflow.py", "--repo", str(repo), "--json")
        checkpoint = run_json(
            "create_checkpoint.py",
            "--repo",
            str(repo),
            "--boundary",
            "project_setup_completed",
            "--phase",
            "01-foundation",
            "--change",
            "initial-mvp",
            "--next-stage",
            "feature_intake",
            "--current-goal",
            "Initialize workflow",
            "--completed-work",
            "Created workflow scaffold",
            "--decision",
            "Use checkpoint before compact",
            "--risk",
            "No validation baseline yet",
            "--validation-command",
            "not-run",
            "--validation-result",
            "not-run",
            "--json",
        )
        checkpoint_file = repo / checkpoint["checkpoint_file"]
        self.assertTrue(checkpoint_file.exists())
        self.assertEqual(checkpoint["compact_status"], "pending")
        state = (repo / ".planning" / "STATE.md").read_text()
        self.assertIn(f"last_checkpoint_id: {checkpoint['checkpoint_id']}", state)
        self.assertIn("compact_status: pending", state)

        valid = run_json(
            "validate_checkpoint.py",
            "--repo",
            str(repo),
            "--checkpoint",
            checkpoint["checkpoint_file"],
            "--json",
        )
        self.assertTrue(valid["valid"])
        self.assertTrue(valid["compact_allowed"])

        recommendation = run_json(
            "compact_recommendation.py",
            "--repo",
            str(repo),
            "--boundary",
            "project_setup_completed",
            "--next-stage",
            "feature_intake",
            "--json",
        )
        self.assertTrue(recommendation["recommend_compact"])
        self.assertIn("/compact", recommendation["instruction"])

    def test_validate_checkpoint_reports_missing_required_sections(self):
        repo = self.make_repo("greenfield-empty")
        run_json("scaffold_workflow.py", "--repo", str(repo), "--json")
        checkpoint = repo / ".planning" / "checkpoints" / "bad.md"
        checkpoint.parent.mkdir(parents=True)
        checkpoint.write_text("# Checkpoint: bad\n\n## Current goal\n\nOnly goal is present.\n")
        result = run_json(
            "validate_checkpoint.py",
            "--repo",
            str(repo),
            "--checkpoint",
            ".planning/checkpoints/bad.md",
            "--json",
        )
        self.assertFalse(result["valid"])
        self.assertFalse(result["compact_allowed"])
        self.assertIn("next_action", result["missing"])
        self.assertIn("risks", result["missing"])

    def test_hook_scripts_support_off_warn_and_block(self):
        repo = self.make_repo("greenfield-empty")
        run_json("scaffold_workflow.py", "--repo", str(repo), "--json")
        payload = json.dumps(
            {"cwd": str(repo), "tool_name": "Edit", "tool_input": {"file_path": str(repo / "src" / "main.py")}}
        )

        warn = run_script("pre_edit_policy.py", input_text=payload)
        self.assertEqual(warn.returncode, 0)
        self.assertIn("codex-project-orchestrator", warn.stdout)

        (repo / ".codex-project-orchestrator.json").write_text(json.dumps({"hook": {"mode": "block"}}))
        blocked = subprocess.run(
            [sys.executable, str(PLUGIN_ROOT / "scripts" / "pre_edit_policy.py")],
            input=payload,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(blocked.returncode, 1)

        (repo / ".codex-project-orchestrator.json").write_text(json.dumps({"hook": {"mode": "off"}}))
        off = run_script("pre_edit_policy.py", input_text=payload)
        self.assertEqual(off.stdout.strip(), "")

    def test_checkpoint_hooks_warn_on_pending_compact(self):
        repo = self.make_repo("greenfield-empty")
        run_json("scaffold_workflow.py", "--repo", str(repo), "--json")
        self.create_pending_checkpoint(repo)
        payload = json.dumps({"cwd": str(repo), "tool_name": "Stop", "tool_input": {}})
        warning = run_script("stop_checkpoint_policy.py", input_text=payload)
        self.assertEqual(warning.returncode, 0)
        self.assertIn("/compact", warning.stdout)

    def test_record_compact_result_preserves_raw_payload_and_clears_gate(self):
        repo = self.make_repo("greenfield-empty")
        run_json("scaffold_workflow.py", "--repo", str(repo), "--json")
        checkpoint = self.create_pending_checkpoint(repo)
        raw_result = '{"compacted_context":[{"type":"message","content":"keep exactly"}]}'

        recorded = run_json(
            "record_compact_result.py",
            "--repo",
            str(repo),
            "--checkpoint",
            checkpoint["checkpoint_file"],
            "--status",
            "completed",
            "--source",
            "responses_api",
            "--raw-result",
            raw_result,
            "--json",
        )

        self.assertTrue(recorded["ok"])
        self.assertEqual(recorded["checkpoint_id"], checkpoint["checkpoint_id"])
        self.assertEqual(recorded["compact_status"], "completed")
        result_file = repo / recorded["compact_result_file"]
        self.assertTrue(result_file.exists())
        result_payload = json.loads(result_file.read_text())
        self.assertEqual(result_payload["source"], "responses_api")
        self.assertEqual(result_payload["raw_result"], raw_result)

        state = (repo / ".planning" / "STATE.md").read_text()
        self.assertIn("compact_status: completed", state)
        self.assertIn(f"last_compact_result_file: {recorded['compact_result_file']}", state)
        self.assertIn("compact_source: responses_api", state)

        payload = json.dumps({"cwd": str(repo), "tool_name": "Bash", "tool_input": {"command": "true"}})
        warning = run_script("pre_next_phase_checkpoint_policy.py", input_text=payload)
        self.assertEqual(warning.stdout.strip(), "")

    def test_pre_next_phase_requires_skipped_reason(self):
        repo = self.make_repo("greenfield-empty")
        run_json("scaffold_workflow.py", "--repo", str(repo), "--json")
        self.create_pending_checkpoint(repo)
        state_file = repo / ".planning" / "STATE.md"
        state_file.write_text(state_file.read_text().replace("compact_status: pending", "compact_status: skipped"))
        payload = json.dumps({"cwd": str(repo), "tool_name": "Bash", "tool_input": {"command": "true"}})

        warning = run_script("pre_next_phase_checkpoint_policy.py", input_text=payload)
        self.assertIn("skip reason", warning.stdout)

        skipped = run_json(
            "record_compact_result.py",
            "--repo",
            str(repo),
            "--status",
            "skipped",
            "--skip-reason",
            "Context was still small after checkpoint validation.",
            "--json",
        )
        self.assertTrue(skipped["ok"])
        clear = run_script("pre_next_phase_checkpoint_policy.py", input_text=payload)
        self.assertEqual(clear.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
