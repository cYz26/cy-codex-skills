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
RELEASE_PLUGIN_ROOT = REPO_ROOT / "plugins" / "dev-flow"
PLUGIN_ID = "dev-flow"
DISPLAY_NAME = "DevFlow"


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


def run_script_allow_failure(name, *args, input_text=None, cwd=PLUGIN_ROOT):
    script = PLUGIN_ROOT / "scripts" / name
    return subprocess.run(
        [sys.executable, str(script), *args],
        input=input_text,
        text=True,
        cwd=cwd,
        capture_output=True,
        check=False,
    )


def run_json(name, *args, input_text=None, cwd=PLUGIN_ROOT):
    result = run_script(name, *args, input_text=input_text, cwd=cwd)
    return json.loads(result.stdout)


def write_ai_plan(
    path,
    capability_line,
    *,
    preface=None,
    title="# Plan",
    target="Build the complete feature.",
    contract="- [ ] Works",
):
    lines = []
    if preface:
        lines.append(preface)
    lines.extend(
        [
            title,
            "",
            "## Target State",
            target,
            "",
            "## Completion Contract",
            contract,
            "",
            "## Capability Slices",
            capability_line,
            "",
            "## Acceptance Criteria",
            "- [ ] Accepted",
            "",
            "## Validation Commands",
            "`python3 -m unittest`",
            "",
        ]
    )
    path.write_text("\n".join(lines))


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
        self.assertEqual(PLUGIN_ROOT.name, PLUGIN_ID)
        self.assertEqual(manifest["name"], PLUGIN_ID)
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(manifest["hooks"], "./hooks.json")
        self.assertEqual(manifest["interface"]["displayName"], DISPLAY_NAME)
        self.assertEqual(manifest["interface"]["category"], "Coding")
        self.assertLessEqual(len(manifest["interface"]["defaultPrompt"]), 3)
        self.assertTrue((PLUGIN_ROOT / manifest["interface"]["logo"]).exists())
        self.assertTrue((PLUGIN_ROOT / manifest["interface"]["composerIcon"]).exists())
        self.assertTrue((PLUGIN_ROOT / "hooks.json").exists())

        release_path, entry = registered_plugin_path(MARKETPLACE, PLUGIN_ID)
        self.assertEqual(release_path, RELEASE_PLUGIN_ROOT.resolve())
        self.assertEqual(entry["category"], "Coding")
        self.assertTrue((RELEASE_PLUGIN_ROOT / ".codex-plugin" / "plugin.json").exists())
        self.assertTrue((RELEASE_PLUGIN_ROOT / "hooks.json").exists())
        release_manifest = json.loads((RELEASE_PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text())
        self.assertLessEqual(len(release_manifest["interface"]["defaultPrompt"]), 3)
        self.assertTrue((RELEASE_PLUGIN_ROOT / "tests" / "test_release_smoke.py").exists())
        self.assertFalse((RELEASE_PLUGIN_ROOT / "fixtures").exists())
        self.assertFalse((RELEASE_PLUGIN_ROOT / "log").exists())

        dev_path, dev_entry = registered_plugin_path(DEV_MARKETPLACE, PLUGIN_ID)
        self.assertEqual(dev_path, PLUGIN_ROOT.resolve())
        self.assertEqual(dev_entry["category"], "Coding")

    def test_all_expected_skills_have_codex_frontmatter(self):
        expected = {
            "capability-research",
            "project-orchestrator",
            "project-setup",
            "checkpoint-compact",
            "feature-intake",
            "change-plan",
            "execute-task",
            "verify-and-archive",
            "workflow-doctor",
            "context-tool-audit",
            "ai-native-tech-plan",
            "claude-code-delegate",
            "context-health-check",
            "codex-updater",
            "plugin-project-migration",
        }
        self.assertEqual({path.name for path in (PLUGIN_ROOT / "skills").iterdir() if path.is_dir()}, expected)
        for skill in expected:
            text = (PLUGIN_ROOT / "skills" / skill / "SKILL.md").read_text()
            self.assertTrue(text.startswith("---\n"), skill)
            self.assertIn(f"name: {skill}", text)
            self.assertRegex(text, r"description: .+")

    def test_capability_research_gate_is_packaged_and_routed(self):
        skill = (PLUGIN_ROOT / "skills" / "capability-research" / "SKILL.md").read_text()
        for phrase in [
            "Capability Evidence Gate",
            "authoritative/current capability",
            "local implementation scan",
            "solution comparison",
            "OpenSpec/test contract",
            "local absence is not platform absence",
        ]:
            self.assertIn(phrase, skill)

        routing_expectations = {
            "project-orchestrator": ["Capability Evidence Gate", "capability-research"],
            "feature-intake": ["capability-research", "current or external capability"],
            "change-plan": ["Capability Evidence", "capability-research"],
            "ai-native-tech-plan": ["capability-research", "unstable platform assumptions"],
        }
        for skill_name, phrases in routing_expectations.items():
            text = (PLUGIN_ROOT / "skills" / skill_name / "SKILL.md").read_text()
            for phrase in phrases:
                self.assertIn(phrase, text, skill_name)

    def test_dependency_catalog_installs_capability_research(self):
        scripts = PLUGIN_ROOT / "scripts"
        sys.path.insert(0, str(scripts))
        try:
            from workflow_dependency_catalog import PROJECT_ORCHESTRATOR_SKILLS
        finally:
            sys.path.remove(str(scripts))

        self.assertIn("capability-research", PROJECT_ORCHESTRATOR_SKILLS)
        self.assertIn("claude-code-delegate", PROJECT_ORCHESTRATOR_SKILLS)

    def test_devflow_no_longer_owns_agent_kb_hooks_or_core_behavior(self):
        forbidden_skills = {
            "kb-ingest",
            "kb-query",
            "kb-update",
            "kb-compact",
            "kb-lint",
            "kb-reflect",
            "kb-promote",
        }
        packaged_skills = {
            path.name
            for path in (PLUGIN_ROOT / "skills").iterdir()
            if path.is_dir()
        }
        self.assertTrue(forbidden_skills.isdisjoint(packaged_skills))

        hooks = (PLUGIN_ROOT / "hooks.json").read_text()
        self.assertNotIn("kb_event_hook.py", hooks)
        self.assertFalse((PLUGIN_ROOT / "scripts" / "workflow_agent_kb.py").exists())
        self.assertFalse((PLUGIN_ROOT / "scripts" / "workflow_obsidian_kb.py").exists())

    def test_high_cost_skill_descriptions_are_concise_and_routable(self):
        expectations = {
            "ai-native-tech-plan": {
                "max_chars": 260,
                "terms": ["technical plans", "Target State", "Completion Contract", "Execution Ledger"],
            },
            "context-tool-audit": {
                "max_chars": 160,
                "terms": ["auditing", "plugins", "skills", "cleanup"],
            },
        }
        for skill, expectation in expectations.items():
            text = (PLUGIN_ROOT / "skills" / skill / "SKILL.md").read_text()
            description = next(line for line in text.splitlines() if line.startswith("description: "))
            self.assertLessEqual(len(description.removeprefix("description: ")), expectation["max_chars"], skill)
            for term in expectation["terms"]:
                self.assertIn(term, description, f"{skill} description should retain {term}")

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
        self.assertTrue((repo / "openspec" / "changes" / "initial-target-state" / "tasks.md").exists())
        self.assertFalse((repo / "openspec" / "changes" / "initial-mvp").exists())
        self.assertTrue((repo / "setup-report.md").exists())
        state = (repo / ".planning" / "STATE.md").read_text()
        self.assertIn("id: initial-target-state", state)
        self.assertIn("context_management:", state)
        self.assertIn("compact_policy: checkpoint_boundary", state)
        agents = (repo / "AGENTS.md").read_text()
        self.assertIn("## AI Coding Planning Rules", agents)
        self.assertIn("Target State", agents)
        self.assertIn("Capability Slices", agents)
        self.assertIn("Execution Ledger", agents)
        self.assertNotIn("Establish MVP scope first", agents)
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

    def test_templates_use_ai_native_plan_sections(self):
        for template in ["OPENSPEC_DESIGN.md.template", "OPENSPEC_TASKS.md.template"]:
            text = (PLUGIN_ROOT / "assets" / "templates" / template).read_text()
            for heading in [
                "Target State",
                "Completion Contract",
                "Capability Slices",
                "Execution Ledger",
                "Acceptance Criteria",
                "Validation Commands",
                "Final Verification",
            ]:
                self.assertIn(heading, text, f"{template} should include {heading}")

    def test_templates_include_capability_evidence_without_agents_procedure(self):
        for template in [
            "OPENSPEC_PROPOSAL.md.template",
            "OPENSPEC_DESIGN.md.template",
            "OPENSPEC_TASKS.md.template",
        ]:
            text = (PLUGIN_ROOT / "assets" / "templates" / template).read_text()
            self.assertIn("Capability Evidence", text, template)
            self.assertIn("authoritative/current", text, template)
            self.assertIn("local", text, template)

        agents = (PLUGIN_ROOT / "assets" / "templates" / "AGENTS.md.template").read_text()
        self.assertIn("capability-research", agents)
        self.assertIn("detailed evidence workflow lives in that skill", agents)
        self.assertNotIn("official capability \u2192 local implementation scan \u2192 solution comparison", agents)

    def test_superpowers_artifacts_map_to_canonical_workflow_artifacts(self):
        agents_template = (PLUGIN_ROOT / "assets" / "templates" / "AGENTS.md.template").read_text()
        for phrase in [
            "## Superpowers Artifact Mapping",
            "Superpowers provides process discipline",
            "OpenSpec, GSD, and DevFlow planning files are the canonical artifacts",
            "docs/superpowers/specs",
            "docs/superpowers/plans",
            "openspec/changes/<change-id>/",
            ".planning/phases/",
        ]:
            self.assertIn(phrase, agents_template)

        for skill in ["project-orchestrator", "feature-intake", "change-plan", "ai-native-tech-plan"]:
            text = (PLUGIN_ROOT / "skills" / skill / "SKILL.md").read_text()
            self.assertIn("Superpowers Artifact Mapping", text, skill)
            self.assertIn("canonical", text, skill)
            self.assertIn("docs/superpowers", text, skill)

    def test_plugin_eval_gate_is_required_for_plugin_and_skill_changes(self):
        paths = {
            "root": REPO_ROOT / "AGENTS.md",
            "dev-template": PLUGIN_ROOT / "assets" / "templates" / "AGENTS.md.template",
            "release-template": RELEASE_PLUGIN_ROOT / "assets" / "templates" / "AGENTS.md.template",
        }
        for label, path in paths.items():
            text = path.read_text()
            with self.subTest(path=label):
                self.assertIn("## Plugin Eval Gate", text)
                self.assertIn("plugin-eval analyze", text)
                self.assertIn("creating or updating Codex plugins or skills", text)
                self.assertIn("record the score, findings, and optimization decisions", text)
                self.assertIn("default to fixing or optimizing", text)
                self.assertIn("Deferral is an exception", text)
                self.assertIn("residual risk and follow-up path", text)

    def test_repair_guidance_is_systemic_first_before_minimal_fix(self):
        paths = {
            "root": REPO_ROOT / "AGENTS.md",
            "dev-template": PLUGIN_ROOT / "assets" / "templates" / "AGENTS.md.template",
            "release-template": RELEASE_PLUGIN_ROOT / "assets" / "templates" / "AGENTS.md.template",
        }
        for label, path in paths.items():
            text = path.read_text()
            with self.subTest(path=label):
                self.assertIn("## Repair Solution Discipline", text)
                self.assertIn("systemic and thorough solution first", text)
                self.assertIn("minimal fix", text)
                self.assertIn("after investigation", text)

        skill_expectations = {
            "feature-intake": ["workflow-repair", "systemic and thorough solution first", "minimal fix"],
            "change-plan": ["systemic and thorough solution first", "Target State", "Completion Contract"],
            "workflow-doctor": ["Repair Solution Discipline", "systemic and thorough solution first", "minimal fix"],
            "project-orchestrator": ["workflow-doctor", "systemic repair framing"],
        }
        for skill_name, phrases in skill_expectations.items():
            text = (PLUGIN_ROOT / "skills" / skill_name / "SKILL.md").read_text()
            for phrase in phrases:
                self.assertIn(phrase, text, skill_name)

    def test_subagent_strategy_is_routed_with_explicit_authorization(self):
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

        ai_plan = (PLUGIN_ROOT / "skills" / "ai-native-tech-plan" / "SKILL.md").read_text()
        for phrase in [
            "SubAgent Strategy",
            "independent Capability Slices",
            "authorization state",
            "main-agent-owned artifacts",
        ]:
            self.assertIn(phrase, ai_plan)

        execute_task = (PLUGIN_ROOT / "skills" / "execute-task" / "SKILL.md").read_text()
        for phrase in [
            "Delegated Execution",
            "DONE_WITH_CONCERNS",
            "files changed or inspected",
            "shared files remain serialized",
        ]:
            self.assertIn(phrase, execute_task)

        context_health = (PLUGIN_ROOT / "skills" / "context-health-check" / "SKILL.md").read_text()
        for phrase in [
            "planning, execution, context-health, and review boundaries",
            "repeated investigation pressure",
            "bounded review or delegation need",
        ]:
            self.assertIn(phrase, context_health)

    def test_subagent_strategy_is_documented_in_dev_and_release_readmes(self):
        expectations = [
            "## SubAgent Strategy",
            "policy/router layer",
            "does not spawn subagents from scripts or hooks",
            "explicit user authorization",
            "main agent owns OpenSpec",
            "status (`DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`)",
        ]
        for label, path in {
            "dev": PLUGIN_ROOT / "README.md",
            "release": RELEASE_PLUGIN_ROOT / "README.md",
        }.items():
            text = path.read_text()
            with self.subTest(readme=label):
                for phrase in expectations:
                    self.assertIn(phrase, text)

    def test_devflow_hooks_and_scripts_do_not_spawn_subagents(self):
        forbidden = ["spawn_agent", "Task(", "/goal"]
        scan_roots = [
            PLUGIN_ROOT / "hooks.json",
            *sorted((PLUGIN_ROOT / "scripts").glob("*.py")),
            RELEASE_PLUGIN_ROOT / "hooks.json",
            *sorted((RELEASE_PLUGIN_ROOT / "scripts").glob("*.py")),
        ]
        violations = []
        for path in scan_roots:
            text = path.read_text()
            for token in forbidden:
                if token in text:
                    violations.append(f"{path.relative_to(REPO_ROOT)} contains {token}")

        self.assertEqual(violations, [])

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
                "ai-native-tech-plan",
                "superpowers:brainstorming",
                "superpowers:writing-plans",
                "openspec-propose",
                "openspec-apply-change",
                "openspec-archive-change",
                "gsd-plan-phase",
                "gsd-verify-work",
                "superpowers:test-driven-development",
            ],
            "ai-native-tech-plan": [
                "Target State",
                "Completion Contract",
                "Capability Slices",
                "Execution Ledger",
                "Validation Commands",
                "Goal Mode Prompt",
                "Continue Prompt",
                "Superpowers",
                "OpenSpec",
                "GSD",
            ],
            "project-setup": ["audit_context_tools.py", "context-tool-audit"],
            "feature-intake": [
                "ai-native-tech-plan",
                "superpowers:brainstorming",
                "superpowers:writing-plans",
                "openspec-explore",
                "openspec-propose",
                "gsd-discuss-phase",
                "gsd-plan-phase",
            ],
            "change-plan": [
                "ai-native-tech-plan",
                "superpowers:brainstorming",
                "superpowers:writing-plans",
                "openspec-explore",
                "openspec-propose",
            ],
            "execute-task": [
                "Execution Ledger",
                "Completion Contract",
                "openspec-apply-change",
                "superpowers:test-driven-development",
                "gsd-execute-phase",
            ],
            "verify-and-archive": [
                "Completion Contract",
                "Execution Ledger",
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

    def test_lint_ai_plan_flags_human_planning_terms(self):
        repo = self.make_repo()
        bad_plan = repo / "bad-plan.md"
        write_ai_plan(bad_plan, "Phase 1: MVP first.")
        bad = run_script_allow_failure("lint_ai_plan.py", str(bad_plan))
        self.assertEqual(bad.returncode, 1)
        self.assertIn("Forbidden human-style planning terms found", bad.stdout)

        good_plan = repo / "good-plan.md"
        write_ai_plan(good_plan, "Slice 1: validated capability.")
        good = run_script_allow_failure("lint_ai_plan.py", str(good_plan))
        self.assertEqual(good.returncode, 0, good.stdout + good.stderr)

        policy_doc = repo / "policy.md"
        write_ai_plan(
            policy_doc,
            "- Policy only",
            preface="<!-- ai-native-plan-lint: allow-human-planning-terms -->",
            title="# Policy",
            target="Explain why MVP framing is not the default.",
            contract="- [ ] Policy is clear",
        )
        allowed = run_script_allow_failure("lint_ai_plan.py", str(policy_doc))
        self.assertEqual(allowed.returncode, 0, allowed.stdout + allowed.stderr)

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
            "initial-target-state",
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

    def test_checkpoint_compact_is_not_blocking_at_stopping_point(self):
        repo = self.make_repo("greenfield-empty")
        run_json("scaffold_workflow.py", "--repo", str(repo), "--json")
        previous = self.create_pending_checkpoint(repo)
        run_json(
            "record_compact_result.py",
            "--repo",
            str(repo),
            "--checkpoint",
            previous["checkpoint_file"],
            "--status",
            "completed",
            "--source",
            "responses_api",
            "--raw-result",
            "previous compact payload",
            "--json",
        )

        checkpoint = run_json(
            "create_checkpoint.py",
            "--repo",
            str(repo),
            "--boundary",
            "verification_passed",
            "--phase",
            "01-foundation",
            "--change",
            "initial-target-state",
            "--next-stage",
            "review_or_archive",
            "--current-goal",
            "Finish verified work",
            "--completed-work",
            "Verification passed",
            "--decision",
            "Stop at review boundary",
            "--risk",
            "No continuation required",
            "--validation-command",
            "python3 -m unittest",
            "--validation-result",
            "pass",
            "--json",
        )

        self.assertFalse(checkpoint["compact_recommended"])
        self.assertEqual(checkpoint["compact_status"], "not_needed")
        checkpoint_text = (repo / checkpoint["checkpoint_file"]).read_text()
        self.assertIn("Compact is optional", checkpoint_text)
        self.assertNotIn("Run `/compact` before continuing", checkpoint_text)

        state = (repo / ".planning" / "STATE.md").read_text()
        self.assertIn(f"last_checkpoint_id: {checkpoint['checkpoint_id']}", state)
        self.assertIn("compact_status: not_needed", state)
        self.assertIn("last_compact_result_file: none", state)
        self.assertIn("compact_source: checkpoint", state)
        self.assertIn("compact_skip_reason: none", state)

        valid = run_json("validate_workflow_state.py", "--repo", str(repo), "--json")
        self.assertTrue(valid["ok"], valid)
        self.assertEqual(valid["warnings"], [])

        recommendation = run_json(
            "compact_recommendation.py",
            "--repo",
            str(repo),
            "--boundary",
            "verification_passed",
            "--next-stage",
            "review_or_archive",
            "--json",
        )
        self.assertFalse(recommendation["recommend_compact"])
        self.assertIn("optional", recommendation["instruction"])

    def test_checkpoint_can_force_continuation_required_for_review_stage(self):
        repo = self.make_repo("greenfield-empty")
        run_json("scaffold_workflow.py", "--repo", str(repo), "--json")

        checkpoint = run_json(
            "create_checkpoint.py",
            "--repo",
            str(repo),
            "--boundary",
            "verification_passed",
            "--phase",
            "01-foundation",
            "--change",
            "initial-target-state",
            "--next-stage",
            "review_or_archive",
            "--continuation-required",
            "--current-goal",
            "Continue review in this thread",
            "--completed-work",
            "Verification passed",
            "--decision",
            "Continue immediately",
            "--risk",
            "Context may be long",
            "--validation-command",
            "python3 -m unittest",
            "--validation-result",
            "pass",
            "--json",
        )

        self.assertTrue(checkpoint["compact_recommended"])
        self.assertEqual(checkpoint["compact_status"], "pending")
        self.assertIn("Run `/compact` before continuing", (repo / checkpoint["checkpoint_file"]).read_text())

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
        self.assertIn(DISPLAY_NAME, warn.stdout)

        (repo / ".dev-flow.json").write_text(json.dumps({"hook": {"mode": "block"}}))
        blocked = subprocess.run(
            [sys.executable, str(PLUGIN_ROOT / "scripts" / "pre_edit_policy.py")],
            input=payload,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(blocked.returncode, 1)

        (repo / ".dev-flow.json").write_text(json.dumps({"hook": {"mode": "off"}}))
        off = run_script("pre_edit_policy.py", input_text=payload)
        self.assertEqual(off.stdout.strip(), "")

        (repo / ".dev-flow.json").unlink()
        (repo / ".codex-project-orchestrator.json").write_text(json.dumps({"hook": {"mode": "off"}}))
        legacy_off = run_script("pre_edit_policy.py", input_text=payload)
        self.assertEqual(legacy_off.stdout.strip(), "")

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
