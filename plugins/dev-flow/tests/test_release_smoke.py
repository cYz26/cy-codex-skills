import json
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from workflow_context_health import context_health_check, record_context_health_event
from workflow_context_tools import apply_context_tool_actions, audit_context_tools
from workflow_compact_recovery import handle_compact_recovery_event
from workflow_dependencies import dependency_report
from codex_auto_update_plugins_skills import plugin_install_results, run_external_updaters


class ReleaseSmokeTests(unittest.TestCase):
    def write_skill(self, path, name=None):
        path.parent.mkdir(parents=True, exist_ok=True)
        skill_name = name or path.parent.name
        path.write_text(f"---\nname: {skill_name}\ndescription: fixture\n---\n")

    def make_codex_home(self):
        home = Path(tempfile.mkdtemp(prefix="devflow-release-home-"))
        (home / "config.toml").write_text(
            "\n".join(
                [
                    '[plugins."example@local"]',
                    "enabled = true",
                ]
            )
            + "\n"
        )
        self.write_skill(home / "skills" / "global-helper" / "SKILL.md")
        self.write_skill(home / "skills" / "another-global-helper" / "SKILL.md")
        return home

    def make_codex_home_with_global_superpowers(self):
        home = self.make_codex_home()
        (home / "config.toml").write_text(
            "\n".join(
                [
                    '[plugins."superpowers@openai-curated"]',
                    "enabled = true",
                ]
            )
            + "\n"
        )
        for skill in [
            "brainstorming",
            "writing-plans",
            "test-driven-development",
            "verification-before-completion",
        ]:
            self.write_skill(
                home
                / "plugins"
                / "cache"
                / "openai-curated"
                / "superpowers"
                / "local"
                / "skills"
                / skill
                / "SKILL.md"
            )
        return home

    def make_repo(self):
        repo = Path(tempfile.mkdtemp(prefix="devflow-release-repo-"))
        (repo / "package.json").write_text('{"dependencies":{"react":"latest"}}\n')
        (repo / ".planning").mkdir()
        (repo / ".planning" / "STATE.md").write_text(
            """---
workflow_version: 0.3.0
project_mode: brownfield
current_stage: executing
current_phase:
  id: 01-foundation
  status: planning
current_change:
  id: release-smoke
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

    def make_dependency_ready_repo(self):
        repo = self.make_repo()
        required_skills = [
            "capability-research",
            "claude-code-delegate",
            "project-orchestrator",
            "project-setup",
            "feature-intake",
            "change-plan",
            "execute-task",
            "verify-and-archive",
            "workflow-doctor",
            "checkpoint-compact",
            "context-tool-audit",
            "brainstorming",
            "writing-plans",
            "test-driven-development",
            "verification-before-completion",
            "gsd-new-project",
            "gsd-discuss-phase",
            "gsd-plan-phase",
            "gsd-execute-phase",
            "gsd-progress",
            "gsd-verify-work",
        ]
        for skill in required_skills:
            self.write_skill(repo / ".codex" / "skills" / skill / "SKILL.md")
        for agent in ["gsd-phase-researcher", "gsd-planner", "gsd-plan-checker", "gsd-executor"]:
            path = repo / ".codex" / "agents" / f"{agent}.toml"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"name = \"{agent}\"\n")
        (repo / "openspec").mkdir(exist_ok=True)
        (repo / "openspec" / "config.yaml").write_text("schema: spec-driven\n")
        return repo

    def test_manifest_uses_three_or_fewer_default_prompts(self):
        manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text())

        self.assertEqual(manifest["name"], "dev-flow")
        self.assertEqual(manifest["interface"]["displayName"], "DevFlow")
        self.assertLessEqual(len(manifest["interface"]["defaultPrompt"]), 3)

    def test_capability_research_skill_is_packaged(self):
        skill = (PLUGIN_ROOT / "skills" / "capability-research" / "SKILL.md").read_text()
        self.assertIn("Capability Evidence Gate", skill)
        self.assertIn("authoritative/current capability", skill)
        self.assertIn("local implementation scan", skill)
        self.assertIn("OpenSpec/test contract", skill)

        templates_root = PLUGIN_ROOT / "assets" / "templates"
        self.assertIn("Capability Evidence", (templates_root / "OPENSPEC_DESIGN.md.template").read_text())
        self.assertIn("capability-research", (templates_root / "AGENTS.md.template").read_text())

    def test_claude_code_delegation_is_packaged(self):
        skill = (PLUGIN_ROOT / "skills" / "claude-code-delegate" / "SKILL.md").read_text()
        self.assertIn("Claude Code Delegation", skill)
        self.assertIn("plan-only delegation", skill)
        self.assertIn("Claude Code owns the complete bounded task", skill)
        self.assertIn("Codex verifies", skill)
        self.assertIn("re-delegate or report a blocker", skill)
        self.assertTrue((PLUGIN_ROOT / "scripts" / "claude_code_delegate.py").exists())
        self.assertTrue((PLUGIN_ROOT / "scripts" / "workflow_claude_delegate.py").exists())

        scripts = str(PLUGIN_ROOT / "scripts")
        sys.path.insert(0, scripts)
        try:
            from workflow_dependency_catalog import PROJECT_ORCHESTRATOR_SKILLS
            from workflow_claude_delegate import ClaudeDelegateOptions
        finally:
            sys.path.remove(scripts)

        self.assertIn("claude-code-delegate", PROJECT_ORCHESTRATOR_SKILLS)
        self.assertEqual(ClaudeDelegateOptions(repo=Path("/tmp/example")).mode, "plan")

    def test_low_frequency_skills_are_explicit_only(self):
        explicit_only = {
            "ai-native-tech-plan",
            "checkpoint-compact",
            "claude-code-delegate",
            "context-health-check",
            "context-tool-audit",
            "execute-task",
            "project-setup",
            "verify-and-archive",
            "workflow-doctor",
        }
        for skill in explicit_only:
            policy = PLUGIN_ROOT / "skills" / skill / "agents" / "openai.yaml"
            with self.subTest(skill=skill):
                self.assertTrue(policy.exists())
                self.assertIn("allow_implicit_invocation: false", policy.read_text())

    def test_core_routing_skills_remain_implicit(self):
        implicit = {"project-orchestrator", "feature-intake", "change-plan", "capability-research"}
        for skill in implicit:
            policy = PLUGIN_ROOT / "skills" / skill / "agents" / "openai.yaml"
            with self.subTest(skill=skill):
                self.assertFalse(policy.exists())

    def test_release_python_lines_stay_under_120_characters(self):
        long_lines = []
        for path in sorted(PLUGIN_ROOT.rglob("*.py")):
            for number, line in enumerate(path.read_text().splitlines(), 1):
                if len(line) > 120:
                    long_lines.append(f"{path.relative_to(PLUGIN_ROOT)}:{number}:{len(line)}")

        self.assertEqual(long_lines, [])

    def test_compact_recovery_hooks_are_packaged(self):
        hooks = json.loads((PLUGIN_ROOT / "hooks.json").read_text())["hooks"]
        post_compact_commands = [
            hook["command"]
            for group in hooks["PostCompact"]
            for hook in group["hooks"]
        ]
        post_compact_matchers = [group.get("matcher") for group in hooks["PostCompact"]]

        self.assertIn("^manual$", post_compact_matchers)
        self.assertIn("./scripts/compact_recovery_hook.py --event post_compact", post_compact_commands)
        self.assertTrue(callable(handle_compact_recovery_event))

    def test_context_tool_facade_audits_and_dry_runs_packaged_behavior(self):
        codex_home = self.make_codex_home()
        repo = self.make_repo()

        report = audit_context_tools(codex_home=codex_home, repo=repo)
        result = apply_context_tool_actions(report, [report["actions"][0]["id"]], apply=False)

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["contextPressure"], "high")
        self.assertIn("javascript", report["projectSignals"])
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["dryRun"])
        self.assertEqual((codex_home / "config.toml.bak-20260518-120000").exists(), False)

    def test_context_health_packaged_behavior_records_and_reports(self):
        repo = self.make_repo()
        payload = {
            "cwd": str(repo),
            "tool_name": "Bash",
            "tool_input": {"command": "python3 -m unittest tests/test_example.py --token SECRET_RELEASE_TOKEN"},
            "tool_response": {"exit_code": 1, "output": "SECRET_RELEASE_OUTPUT"},
        }

        record_context_health_event(repo, "post_tool_use", payload)
        record_context_health_event(repo, "post_tool_use", payload)
        report = context_health_check(repo, {"current_objective": "Release smoke health check"})

        self.assertEqual(report["risk"], "medium")
        self.assertEqual(report["decision"], "reconcile")
        events_text = (repo / ".dev-flow" / "context-health" / "events.jsonl").read_text()
        self.assertNotIn("SECRET_RELEASE_OUTPUT", events_text)
        self.assertNotIn("SECRET_RELEASE_TOKEN", events_text)

    def test_dependency_packaged_behavior_warns_for_global_superpowers(self):
        codex_home = self.make_codex_home_with_global_superpowers()
        repo = self.make_dependency_ready_repo()

        report = dependency_report(
            plugin_root=PLUGIN_ROOT,
            codex_home=codex_home,
            config_path=codex_home / "config.toml",
            repo=repo,
        )

        checks = {item["name"]: item for item in report["checks"]}
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["status"], "ready_with_recommendations")
        self.assertFalse(checks["global plugin inactive: superpowers"]["required"])

    def test_release_updater_excludes_agent_reach(self):
        codex_home = self.make_codex_home()

        results = run_external_updaters(codex_home, apply=False)

        self.assertNotIn("agent-reach", {item["name"] for item in results})

    def test_release_updater_plans_installed_plugin_refresh(self):
        marketplace_root = Path(tempfile.mkdtemp(prefix="devflow-release-marketplace-"))
        source = marketplace_root / "plugins" / "example"
        source.mkdir(parents=True)
        (source / ".codex-plugin").mkdir()
        (source / ".codex-plugin" / "plugin.json").write_text('{"name":"example"}\n')
        catalog = marketplace_root / ".agents" / "plugins"
        catalog.mkdir(parents=True)
        (catalog / "marketplace.json").write_text(
            json.dumps({"plugins": [{"name": "example", "source": {"path": "./plugins/example"}}]})
        )
        config = {
            "marketplaces": {"local": {"source": str(marketplace_root)}},
            "plugins": {"example@local": {"enabled": True}},
        }

        results = plugin_install_results(config, apply=False)

        self.assertEqual(results[0]["kind"], "plugin-install")
        self.assertEqual(results[0]["name"], "example@local")
        self.assertEqual(results[0]["status"], "would-refresh")

    def test_release_codex_updater_skill_is_packaged(self):
        skill_path = PLUGIN_ROOT / "skills" / "codex-updater" / "SKILL.md"
        text = skill_path.read_text()

        self.assertIn("name: codex-updater", text)
        self.assertIn("codex_auto_update_plugins_skills.py --json", text)
        self.assertIn("--apply --json", text)
        self.assertIn("plugin-install", text)
        self.assertIn("plugin-cache-verify", text)
        self.assertIn("do not check, update, or run Agent Reach", text)

    def test_devflow_release_does_not_package_agent_kb_core(self):
        forbidden_skills = {
            "kb-ingest",
            "kb-query",
            "kb-update",
            "kb-compact",
            "kb-lint",
            "kb-reflect",
            "kb-promote",
        }
        packaged_skills = {path.name for path in (PLUGIN_ROOT / "skills").iterdir() if path.is_dir()}
        self.assertTrue(forbidden_skills.isdisjoint(packaged_skills))

        workflow_lib = (PLUGIN_ROOT / "scripts" / "workflow_lib.py").read_text()
        hooks = (PLUGIN_ROOT / "hooks.json").read_text()
        self.assertNotIn("workflow_agent_kb", workflow_lib)
        self.assertNotIn("workflow_obsidian_kb", workflow_lib)
        self.assertNotIn("scaffold_obsidian_kb", workflow_lib)
        self.assertNotIn("record_kb_event", workflow_lib)
        self.assertNotIn("kb_event_hook.py", hooks)


if __name__ == "__main__":
    unittest.main()
