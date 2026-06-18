import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
RELEASE_PLUGIN_ROOT = PLUGIN_ROOT.parents[2] / "plugins" / "dev-flow"
SCRIPTS = PLUGIN_ROOT / "scripts"
HOOK_SCRIPT_PREFIX = (
    'python3 "${CODEX_HOME:-$HOME/.codex}/plugins/cache/cy-codex-skills/'
    'dev-flow/0.3.0+codex.20260529145038/scripts/'
)
sys.path.insert(0, str(SCRIPTS))

from workflow_context_health import context_health_check, record_context_health_event
from workflow_context_tools import apply_context_tool_actions, audit_context_tools
from workflow_compact_recovery import handle_compact_recovery_event
from workflow_dependencies import dependency_report
from codex_auto_update_plugins_skills import plugin_install_results, run_external_updaters


def normalized_text(text):
    return " ".join(text.split())


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
            "ai-native-tech-plan",
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
            "context-health-check",
            "context-tool-audit",
            "codex-updater",
            "plugin-project-migration",
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
            self.write_skill(repo / ".agents" / "skills" / skill / "SKILL.md")
        for agent in ["gsd-phase-researcher", "gsd-planner", "gsd-plan-checker", "gsd-executor"]:
            path = repo / ".codex" / "agents" / f"{agent}.toml"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"name = \"{agent}\"\n")
        runtime = repo / ".codex" / "gsd-core"
        (runtime / "bin").mkdir(parents=True)
        (runtime / "VERSION").write_text("1.4.5\n")
        tools = runtime / "bin" / "gsd-tools.cjs"
        tools.write_text("#!/usr/bin/env node\nconsole.log('2026-06-14T00:00:00Z')\n")
        tools.chmod(0o755)
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

    def test_delegation_skill_remains_explicit_only(self):
        explicit_only = {
            "claude-code-delegate",
        }
        for skill in explicit_only:
            policy = PLUGIN_ROOT / "skills" / skill / "agents" / "openai.yaml"
            with self.subTest(skill=skill):
                self.assertTrue(policy.exists())
                self.assertIn("allow_implicit_invocation: false", policy.read_text())

    def test_core_routing_skills_remain_implicit(self):
        implicit = {
            "project-orchestrator",
            "feature-intake",
            "change-plan",
            "capability-research",
            "ai-native-tech-plan",
            "project-setup",
            "execute-task",
            "verify-and-archive",
            "workflow-doctor",
            "checkpoint-compact",
            "context-health-check",
            "context-tool-audit",
            "codex-updater",
            "plugin-project-migration",
        }
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
        all_hook_commands = [
            hook["command"]
            for group in hooks.values()
            for entry in group
            for hook in entry.get("hooks", [])
        ]
        post_compact_matchers = [group.get("matcher") for group in hooks["PostCompact"]]

        self.assertIn("^manual$", post_compact_matchers)
        self.assertIn(
            f"{HOOK_SCRIPT_PREFIX}compact_recovery_hook.py\" --event post_compact",
            post_compact_commands,
        )
        self.assertTrue(all(command.startswith(HOOK_SCRIPT_PREFIX) for command in all_hook_commands))
        self.assertFalse(any("./scripts/" in command for command in all_hook_commands))
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

    def test_release_runtime_uses_opengsd_core_not_legacy_gsd(self):
        runtime_archive = RELEASE_PLUGIN_ROOT / "scripts" / "devflow_runtime.pyz"
        with zipfile.ZipFile(runtime_archive) as archive:
            data = "\n".join(
                archive.read(name).decode("utf-8", "ignore")
                for name in archive.namelist()
                if name.endswith(".py")
            )

        self.assertIn("@opengsd/gsd-core", data)
        self.assertIn("gsd-tools.cjs", data)
        self.assertNotIn("get-shit-done-cc", data)
        self.assertNotIn("gsd-sdk", data)

    def test_readme_documents_release_runtime_audit_command(self):
        readme = (PLUGIN_ROOT / "README.md").read_text()

        self.assertIn("devflow_runtime.MANIFEST.json", readme)
        self.assertIn("devflow_runtime.sha256", readme)
        self.assertIn("devflow_runtime.SOURCE_COMMIT", readme)
        self.assertIn("verify_release_runtime.py --plugin-root plugins/dev-flow --json", readme)

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

    def test_release_subagent_strategy_is_packaged(self):
        project_orchestrator = (PLUGIN_ROOT / "skills" / "project-orchestrator" / "SKILL.md").read_text()
        for phrase in [
            "## SubAgent Decision Gate",
            "recommend a split without spawning",
            "explicit user authorization",
            "disjoint write sets",
            "main agent owns OpenSpec",
            "gsd-execute-phase",
            "subagent-driven-development",
            "dispatching-parallel-agents",
        ]:
            self.assertIn(phrase, project_orchestrator)

        skill_expectations = {
            "ai-native-tech-plan": [
                "SubAgent Strategy",
                "independent Capability Slices",
                "authorization state",
                "main-agent-owned artifacts",
            ],
            "execute-task": [
                "Delegated Execution",
                "DONE_WITH_CONCERNS",
                "files changed or inspected",
                "shared files remain serialized",
            ],
            "context-health-check": [
                "planning, execution, context-health, and review boundaries",
                "repeated investigation pressure",
                "bounded review or delegation need",
            ],
        }
        for skill, phrases in skill_expectations.items():
            text = (PLUGIN_ROOT / "skills" / skill / "SKILL.md").read_text()
            with self.subTest(skill=skill):
                for phrase in phrases:
                    self.assertIn(phrase, text)

        readme = (PLUGIN_ROOT / "README.md").read_text()
        for phrase in [
            "## SubAgent Strategy",
            "policy/router layer",
            "does not spawn subagents from scripts or hooks",
            "explicit user authorization",
            "main agent owns OpenSpec",
            "status (`DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`)",
        ]:
            self.assertIn(phrase, readme)

    def test_release_skill_routing_ledger_guards_brainstorming_gate(self):
        expectations = {
            "project-orchestrator": [
                "design, research, architecture, or product-shape requests",
                "feature-intake before ai-native-tech-plan",
            ],
            "feature-intake": [
                "Skill Routing Ledger",
                "brainstorming: required/used/skipped",
                "Open Questions",
            ],
            "ai-native-tech-plan": [
                "Skill Routing Ledger",
                "Open Questions remain",
                "draft, not final",
            ],
        }
        for skill, phrases in expectations.items():
            text = (PLUGIN_ROOT / "skills" / skill / "SKILL.md").read_text()
            with self.subTest(skill=skill):
                for phrase in phrases:
                    self.assertIn(phrase, text)

        for rel_path in [
            "assets/templates/AGENTS.md.template",
            "skills/ai-native-tech-plan/assets/task-ledger-template.md",
        ]:
            text = (PLUGIN_ROOT / rel_path).read_text()
            with self.subTest(path=rel_path):
                self.assertIn("Skill Routing Ledger", text)
                self.assertIn("brainstorming: required/used/skipped", text)

    def test_release_goal_workflow_routes_to_define_goal(self):
        readme = (PLUGIN_ROOT / "README.md").read_text()
        skill_expectations = {
            "project-orchestrator": [
                "define-goal",
                "goal-backed",
                "Goal Suitability Gate",
                "ordinary implementation",
            ],
            "feature-intake": [
                "define-goal",
                "active goal",
                "Goal Suitability Gate",
                "verification evidence",
            ],
            "ai-native-tech-plan": [
                "define-goal",
                "Goal Mode Prompt",
                "Goal Suitability Gate",
                "stop conditions",
            ],
        }
        for skill, phrases in skill_expectations.items():
            text = (PLUGIN_ROOT / "skills" / skill / "SKILL.md").read_text()
            with self.subTest(skill=skill):
                normalized = normalized_text(text)
                for phrase in phrases:
                    self.assertIn(normalized_text(phrase), normalized)

        normalized_readme = normalized_text(readme)
        for phrase in [
            "define-goal",
            "goal-backed",
            "Goal Suitability Gate",
            "before context-health drift",
            "long-running",
            "multi-slice",
            "migration",
            "release",
            "cross-context",
            "/goal <objective>",
            "codex features enable goals",
            "does not call goal tools from hooks or scripts",
        ]:
            self.assertIn(normalized_text(phrase), normalized_readme)

        for rel_path in [
            "assets/templates/AGENTS.md.template",
            "skills/ai-native-tech-plan/references/goal-prompt-template.md",
            "skills/context-health-check/SKILL.md",
        ]:
            text = (PLUGIN_ROOT / rel_path).read_text()
            normalized = normalized_text(text)
            with self.subTest(path=rel_path):
                self.assertIn("define-goal", normalized)
                self.assertIn("verification evidence", normalized)
                self.assertIn("Goal Suitability Gate", normalized)
                self.assertIn("before context-health drift", normalized)
                self.assertIn("stop conditions", normalized)
                self.assertIn("/goal <objective>", normalized)
                self.assertIn("/goal pause", normalized)
                self.assertIn("/goal resume", normalized)
                self.assertIn("/goal clear", normalized)
                self.assertIn("features.goals", normalized)
                self.assertIn("codex features enable goals", normalized)
                self.assertNotIn("`codex goal`", normalized.lower())
                self.assertNotIn("codex goal --help", normalized.lower())

    def test_release_hooks_and_scripts_do_not_spawn_subagents(self):
        forbidden = ["spawn_agent", "Task("]
        scan_roots = [
            PLUGIN_ROOT / "hooks.json",
            *sorted((PLUGIN_ROOT / "scripts").glob("*.py")),
        ]
        violations = []
        for path in scan_roots:
            text = path.read_text()
            for token in forbidden:
                if token in text:
                    violations.append(f"{path.relative_to(PLUGIN_ROOT)} contains {token}")

        self.assertEqual(violations, [])

    def test_release_hooks_and_scripts_do_not_execute_goal_tools(self):
        forbidden = [
            "create_goal(",
            "get_goal(",
            "update_goal(",
            "`codex goal`",
            "codex goal --help",
        ]
        scan_roots = [
            PLUGIN_ROOT / "hooks.json",
            *sorted((PLUGIN_ROOT / "scripts").glob("*.py")),
        ]
        violations = []
        for path in scan_roots:
            text = path.read_text().lower()
            for token in forbidden:
                if token in text:
                    violations.append(f"{path.relative_to(PLUGIN_ROOT)} contains {token}")

        self.assertEqual(violations, [])

    def test_plugin_project_migration_skill_is_packaged(self):
        skill_path = PLUGIN_ROOT / "skills" / "plugin-project-migration" / "SKILL.md"
        text = skill_path.read_text()
        hooks = json.loads((PLUGIN_ROOT / "hooks.json").read_text())["hooks"]
        hook_commands = [
            hook["command"]
            for group in hooks.values()
            for entry in group
            for hook in entry.get("hooks", [])
        ]

        self.assertIn("name: plugin-project-migration", text)
        self.assertIn("sync-only", text)
        self.assertIn("explicit", text)
        self.assertIn(
            f"{HOOK_SCRIPT_PREFIX}plugin_project_migration_check.py\" --event user_prompt_submit",
            hook_commands,
        )

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
