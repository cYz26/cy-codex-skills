import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = (
    PLUGIN_ROOT.parents[2]
    if PLUGIN_ROOT.parent.parent.name == "dev"
    else PLUGIN_ROOT.parents[1]
)
RELEASE_PLUGIN_ROOT = REPO_ROOT / "plugins" / "dev-flow"
SCRIPTS = PLUGIN_ROOT / "scripts"
RUNTIME_ARCHIVE = SCRIPTS / "devflow_runtime.pyz"
HOOK_SCRIPT_PREFIX = 'python3 "$PLUGIN_ROOT/scripts/'
if RUNTIME_ARCHIVE.is_file():
    os.environ.setdefault("DEVFLOW_PLUGIN_ROOT", str(PLUGIN_ROOT))
sys.path.insert(0, str(RUNTIME_ARCHIVE if RUNTIME_ARCHIVE.is_file() else SCRIPTS))

from workflow_context_health import context_health_check, record_context_health_event
from workflow_context_tools import apply_context_tool_actions, audit_context_tools
from workflow_compact_recovery import handle_compact_recovery_event
from workflow_dependencies import dependency_report
from workflow_dependency_provenance import default_plugin_root as provenance_plugin_root
from workflow_planning_paths import current_plugin_version
from workflow_routing_matrix import default_plugin_root as routing_plugin_root
from workflow_superpowers_gates import default_plugin_root as superpowers_gate_plugin_root
from codex_auto_update_plugins_skills import plugin_install_results, run_external_updaters
from workflow_decision_grilling import decision_grilling_guidance, load_decision_grilling_matrix


def normalized_text(text):
    return " ".join(text.split())


def packaged_module_text(name):
    if RUNTIME_ARCHIVE.is_file():
        with zipfile.ZipFile(RUNTIME_ARCHIVE) as archive:
            return archive.read(name).decode("utf-8")
    return (SCRIPTS / name).read_text()


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
            "using-superpowers",
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
        manifest = (
            home
            / "plugins"
            / "cache"
            / "openai-curated"
            / "superpowers"
            / "local"
            / ".codex-plugin"
            / "plugin.json"
        )
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text('{"name":"superpowers","version":"5.1.3","skills":"./skills/"}\n')
        return home

    def make_repo(self):
        repo = Path(tempfile.mkdtemp(prefix="devflow-release-repo-"))
        (repo / "package.json").write_text('{"dependencies":{"react":"latest"}}\n')
        (repo / ".planning" / "devflow").mkdir(parents=True)
        (repo / ".dev-flow.json").write_text(
            '{"workflow":{"methodology_profile":"core","roadmap_provider":"none"}}\n'
        )
        (repo / ".planning" / "devflow" / "STATE.md").write_text(
            """---
workflow_version: 0.3.0
project_mode: brownfield
current_stage: executing
current_phase:
  id: none
  status: none
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
            "dev-flow-refresh",
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
            target = repo / ".agents" / "skills" / skill / "SKILL.md"
            source = PLUGIN_ROOT / "skills" / skill / "SKILL.md"
            if source.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes())
            else:
                self.write_skill(target)
        for agent in ["gsd-phase-researcher", "gsd-planner", "gsd-plan-checker", "gsd-executor"]:
            path = repo / ".codex" / "agents" / f"{agent}.toml"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"name = \"{agent}\"\n")
        runtime = repo / ".codex" / "gsd-core"
        (runtime / "bin").mkdir(parents=True)
        (runtime / "VERSION").write_text("1.6.1\n")
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
        self.assertEqual(manifest["author"]["url"], "https://github.com/cYz26")
        self.assertEqual(manifest["repository"], "https://github.com/cYz26/cy-codex-skills")
        self.assertEqual(
            manifest["homepage"],
            "https://github.com/cYz26/cy-codex-skills/tree/main/plugins/dev-flow",
        )
        self.assertEqual(manifest["interface"]["developerName"], "cY")
        self.assertEqual(manifest["interface"]["websiteURL"], manifest["homepage"])
        self.assertNotIn("github.com/local", json.dumps(manifest))
        self.assertLessEqual(len(manifest["interface"]["defaultPrompt"]), 3)

    def test_runtime_asset_helpers_resolve_the_launcher_plugin_root(self):
        manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text())

        self.assertEqual(provenance_plugin_root(), PLUGIN_ROOT)
        self.assertEqual(routing_plugin_root(), PLUGIN_ROOT)
        self.assertEqual(superpowers_gate_plugin_root(), PLUGIN_ROOT)
        self.assertEqual(current_plugin_version(), manifest["version"])

    def test_capability_research_skill_is_packaged(self):
        skill = (PLUGIN_ROOT / "skills" / "capability-research" / "SKILL.md").read_text()
        self.assertIn("Capability Evidence Gate", skill)
        self.assertIn("authoritative/current capability", skill)
        self.assertIn("local implementation scan", skill)
        self.assertIn("OpenSpec/test contract", skill)

        templates_root = PLUGIN_ROOT / "assets" / "templates"
        self.assertIn("Capability Evidence", (templates_root / "OPENSPEC_DESIGN.md.template").read_text())
        self.assertIn("capability-research", (templates_root / "AGENTS.md.template").read_text())

    def test_decision_grilling_contract_is_packaged(self):
        matrix = load_decision_grilling_matrix(PLUGIN_ROOT)
        self.assertEqual(matrix["schemaVersion"], 1)
        self.assertIn("one-question-at-a-time", matrix["protocol"])
        self.assertIn("OpenSpec", " ".join(matrix["canonicalArtifacts"]))

        guidance = decision_grilling_guidance(
            kind="new-feature",
            request="Design behavior with open compatibility questions.",
            open_questions=["Which compatibility policy applies?"],
            plugin_root=PLUGIN_ROOT,
        )
        self.assertEqual(guidance["status"], "required")
        self.assertIn("decision-grilling: required", guidance["ledger_entry"])
        self.assertTrue(guidance["local_evidence_first"])

    def test_claude_code_delegation_is_packaged(self):
        skill = (PLUGIN_ROOT / "skills" / "claude-code-delegate" / "SKILL.md").read_text()
        self.assertIn("Claude Code Delegation", skill)
        self.assertIn("plan-only delegation", skill)
        self.assertIn("Claude Code owns the complete bounded task", skill)
        self.assertIn("Codex verifies", skill)
        self.assertIn("re-delegate or report a blocker", skill)
        self.assertTrue((PLUGIN_ROOT / "scripts" / "claude_code_delegate.py").exists())
        self.assertIn("class ClaudeDelegateOptions", packaged_module_text("workflow_claude_delegate.py"))

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
            "dev-flow-refresh",
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
        events_text = (
            repo / ".planning" / "devflow" / "context-health" / "events.jsonl"
        ).read_text()
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

    def test_release_runtime_and_provenance_use_opengsd_core_not_legacy_gsd(self):
        runtime_archive = RELEASE_PLUGIN_ROOT / "scripts" / "devflow_runtime.pyz"
        with zipfile.ZipFile(runtime_archive) as archive:
            data = "\n".join(
                archive.read(name).decode("utf-8", "ignore")
                for name in archive.namelist()
                if name.endswith(".py")
            )
        provenance = json.loads(
            (RELEASE_PLUGIN_ROOT / "docs" / "dependency-provenance.json").read_text()
        )
        source = provenance["providerSources"]["gsd-core-1-6-1"]
        dependency = next(
            item for item in provenance["dependencies"] if item["name"] == "gsd-core"
        )

        self.assertIn("gsd-tools.cjs", data)
        self.assertEqual(source["package"], "@opengsd/gsd-core")
        self.assertEqual(source["version"], "1.6.1")
        self.assertIn("@opengsd/gsd-core@1.6.1", source["installCommand"])
        self.assertEqual(dependency["expectedVersion"], "1.6.1")
        self.assertIn("@opengsd/gsd-core@1.6.1", dependency["installCommand"])
        release_contract = data + json.dumps(provenance, sort_keys=True)
        self.assertNotIn("get-shit-done-cc", release_contract)
        self.assertNotIn("gsd-sdk", release_contract)

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

    def test_release_dev_flow_refresh_skill_is_packaged(self):
        skill_path = PLUGIN_ROOT / "skills" / "dev-flow-refresh" / "SKILL.md"
        text = skill_path.read_text()

        self.assertIn("name: dev-flow-refresh", text)
        self.assertIn("codex plugin add dev-flow@cy-codex-skills --json", text)
        self.assertIn("plugin_project_migration.py", text)
        self.assertIn("activate_project_dependencies.py", text)
        self.assertIn("AGENTS.md.generated", text)
        self.assertIn("AGENTS Drift Gate", text)
        self.assertIn("durable workflow rules", text)
        self.assertIn("AGENTS status", text)
        self.assertIn(".codex/skills", text)
        self.assertIn("git status", text)

    def test_release_agents_template_includes_devflow_refresh_workflow(self):
        text = (PLUGIN_ROOT / "assets" / "templates" / "AGENTS.md.template").read_text()
        normalized = normalized_text(text)

        self.assertIn("## DevFlow Refresh Workflow", text)
        self.assertIn("dev-flow-refresh", text)
        self.assertIn("AGENTS.md.generated", text)
        self.assertIn("durable workflow rules", normalized)
        self.assertIn("codex plugin add dev-flow@cy-codex-skills --json", text)

    def test_release_subagent_strategy_is_packaged(self):
        project_orchestrator = normalized_text(
            (PLUGIN_ROOT / "skills" / "project-orchestrator" / "SKILL.md").read_text()
        )
        for phrase in [
            "## SubAgent Decision Gate",
            "Recommend a split without spawning",
            "explicit user authorization",
            "disjoint write sets",
            "main agent owns",
            "execution-orchestration",
        ]:
            self.assertIn(normalized_text(phrase), project_orchestrator)

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
            text = normalized_text((PLUGIN_ROOT / "skills" / skill / "SKILL.md").read_text())
            with self.subTest(skill=skill):
                for phrase in phrases:
                    self.assertIn(normalized_text(phrase), text)

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
                "Capability Routing",
                "decision-resolution",
                "ai-native-tech-plan",
            ],
            "feature-intake": [
                "Skill Routing Ledger",
                "decision-resolution",
                "Open Questions",
            ],
            "ai-native-tech-plan": [
                "Skill Routing Ledger",
                "Open Questions",
                "draft, not final",
            ],
        }
        for skill, phrases in expectations.items():
            text = (PLUGIN_ROOT / "skills" / skill / "SKILL.md").read_text()
            with self.subTest(skill=skill):
                for phrase in phrases:
                    self.assertIn(phrase, text)

        agents = (PLUGIN_ROOT / "assets/templates/AGENTS.md.template").read_text()
        self.assertIn("Skill Routing Ledger", agents)
        self.assertIn("required capabilities", normalized_text(agents))
        ledger = (PLUGIN_ROOT / "skills/ai-native-tech-plan/assets/task-ledger-template.md").read_text()
        self.assertIn("Skill Routing Ledger", ledger)
        self.assertIn("brainstorming: required/used/skipped", ledger)

    def test_release_goal_workflow_routes_to_define_goal(self):
        readme = (PLUGIN_ROOT / "README.md").read_text()
        skill_expectations = {
            "project-orchestrator": [
                "define-goal",
                "goal-backed",
                "Goal Gate",
                "stop conditions",
            ],
            "feature-intake": [
                "define-goal",
                "Goal Suitability Gate",
                "definition of done",
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
            "Goal Quality Gate",
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

        self.assertTrue((PLUGIN_ROOT / "scripts" / "validate_goal_quality.py").exists())
        with zipfile.ZipFile(RELEASE_PLUGIN_ROOT / "scripts" / "devflow_runtime.pyz") as archive:
            names = set(archive.namelist())
        self.assertIn("workflow_goal_quality.py", names)
        self.assertIn("validate_goal_quality.py", names)

        agents = normalized_text((PLUGIN_ROOT / "assets/templates/AGENTS.md.template").read_text())
        for phrase in ["define-goal", "verification evidence", "stop conditions", "long-running"]:
            self.assertIn(phrase, agents)

        for rel_path in [
            "skills/ai-native-tech-plan/references/goal-prompt-template.md",
            "skills/context-health-check/SKILL.md",
        ]:
            text = (PLUGIN_ROOT / rel_path).read_text()
            normalized = normalized_text(text)
            with self.subTest(path=rel_path):
                self.assertIn("define-goal", normalized)
                self.assertIn("verification evidence", normalized)
                self.assertIn("Goal Suitability Gate", normalized)
                self.assertIn("Goal Quality Gate", normalized)
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

    def test_agent_task_contract_gate_is_packaged(self):
        template = RELEASE_PLUGIN_ROOT / "assets" / "templates" / "AGENT_TASK_CONTRACT.md.template"
        self.assertTrue(template.exists())
        text = template.read_text()
        for phrase in [
            "# Agent Task Contract",
            "## Goal",
            "## Scope",
            "## Constraints",
            "## Verification",
            "## Evidence",
            "## Human Gate",
        ]:
            self.assertIn(phrase, text)

        cli = RELEASE_PLUGIN_ROOT / "scripts" / "validate_agent_task_contract.py"
        self.assertTrue(cli.exists())

        with zipfile.ZipFile(RELEASE_PLUGIN_ROOT / "scripts" / "devflow_runtime.pyz") as archive:
            names = set(archive.namelist())
        self.assertIn("workflow_agent_task_contract.py", names)
        self.assertIn("validate_agent_task_contract.py", names)

    def test_context_health_disposition_cli_is_packaged(self):
        skill = RELEASE_PLUGIN_ROOT / "skills" / "context-health-check" / "SKILL.md"
        self.assertIn("record_context_health_disposition.py", skill.read_text())

        cli = RELEASE_PLUGIN_ROOT / "scripts" / "record_context_health_disposition.py"
        self.assertTrue(cli.exists())

        with zipfile.ZipFile(RELEASE_PLUGIN_ROOT / "scripts" / "devflow_runtime.pyz") as archive:
            names = set(archive.namelist())
        self.assertIn("record_context_health_disposition.py", names)
        self.assertIn("workflow_context_health_subagents.py", names)

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

        workflow_lib = packaged_module_text("workflow_lib.py")
        hooks = (PLUGIN_ROOT / "hooks.json").read_text()
        self.assertNotIn("workflow_agent_kb", workflow_lib)
        self.assertNotIn("workflow_obsidian_kb", workflow_lib)
        self.assertNotIn("scaffold_obsidian_kb", workflow_lib)
        self.assertNotIn("record_kb_event", workflow_lib)
        self.assertNotIn("kb_event_hook.py", hooks)


if __name__ == "__main__":
    unittest.main()
