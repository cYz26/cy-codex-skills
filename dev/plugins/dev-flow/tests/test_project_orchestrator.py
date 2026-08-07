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
EXPECTED_DEVFLOW_SKILLS = {
    "ai-native-tech-plan",
    "capability-research",
    "change-plan",
    "checkpoint-compact",
    "claude-code-delegate",
    "codex-updater",
    "context-health-check",
    "context-tool-audit",
    "dev-flow-refresh",
    "execute-task",
    "feature-intake",
    "plugin-project-migration",
    "project-orchestrator",
    "project-setup",
    "verify-and-archive",
    "workflow-doctor",
}
REMOVED_SKILL_RESOURCES = {
    Path("ai-native-tech-plan/assets/review-checklist.md"),
    Path("ai-native-tech-plan/references/agents-md-snippet.md"),
    Path("ai-native-tech-plan/references/planning-principles.md"),
    Path("checkpoint-compact/references/boundary-rules.md"),
    Path("checkpoint-compact/references/compact-policy.md"),
    Path("checkpoint-compact/references/recovery-playbook.md"),
}
REQUIRED_SKILL_RESOURCES = {
    Path("ai-native-tech-plan/assets/task-ledger-template.md"),
    Path("ai-native-tech-plan/references/goal-prompt-template.md"),
    Path("context-health-check/references/goal-and-delegation.md"),
    Path("context-health-check/references/session-recovery.md"),
    Path("dev-flow-refresh/references/project-refresh.md"),
}
RESOURCE_USAGE_MARKERS = {
    Path("ai-native-tech-plan/assets/task-ledger-template.md"): "When creating a durable task ledger",
    Path("ai-native-tech-plan/references/goal-prompt-template.md"): "only when the Goal Suitability Gate",
    Path("context-health-check/references/goal-and-delegation.md"): "recording any delegation disposition",
    Path("context-health-check/references/session-recovery.md"): "work that predates DevFlow events",
    Path("dev-flow-refresh/references/project-refresh.md"): "before running its read-only diagnostics",
}


def registered_plugin_path(marketplace_path, plugin_name):
    marketplace = json.loads(marketplace_path.read_text())
    entry = next(item for item in marketplace["plugins"] if item["name"] == plugin_name)
    return (marketplace_path.parents[2] / entry["source"]["path"]).resolve(), entry


def normalized_text(text):
    return " ".join(text.split())


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
        self.assertTrue((RELEASE_PLUGIN_ROOT / "tests" / "test_packaged_runtime.py").exists())
        self.assertEqual(
            {
                path.relative_to(RELEASE_PLUGIN_ROOT).as_posix()
                for path in (RELEASE_PLUGIN_ROOT / "fixtures").rglob("*")
                if path.is_file()
            },
            {
                "fixtures/implementation-readiness/agents-guidance-markers-revision2.json",
                "fixtures/implementation-readiness/invalid-evidence-missing-capabilities-v1.json",
                "fixtures/implementation-readiness/invalid-provider-override-anonymous-v1.json",
                "fixtures/implementation-readiness/invalid-receipt-not-ready-v1.json",
                "fixtures/implementation-readiness/invalid-requirement-v2.json",
                "fixtures/implementation-readiness/project-refresh-cases-v3.json",
                "fixtures/implementation-readiness/valid-evidence-v1.json",
                "fixtures/implementation-readiness/valid-provider-override-v1.json",
                "fixtures/implementation-readiness/valid-receipt-v1.json",
                "fixtures/implementation-readiness/valid-requirement-v1.json",
                "fixtures/project-refresh/current-v2.json",
                "fixtures/project-refresh/current.json",
                "fixtures/project-refresh/legacy-conflicting-aliases.json",
                "fixtures/project-refresh/legacy-preserve-settings.json",
                "fixtures/project-refresh/legacy-root-selection.json",
                "fixtures/project-refresh/legacy-workflow-selection.json",
                "fixtures/project-refresh/manifest.json",
                "fixtures/test_generated_artifact_lifecycle.py",
            },
        )
        self.assertFalse((RELEASE_PLUGIN_ROOT / "log").exists())

        dev_path, dev_entry = registered_plugin_path(DEV_MARKETPLACE, PLUGIN_ID)
        self.assertEqual(dev_path, PLUGIN_ROOT.resolve())
        self.assertEqual(dev_entry["category"], "Coding")

    def test_all_expected_skills_have_codex_frontmatter(self):
        self.assertEqual(
            {path.name for path in (PLUGIN_ROOT / "skills").iterdir() if path.is_dir()},
            EXPECTED_DEVFLOW_SKILLS,
        )
        for skill in EXPECTED_DEVFLOW_SKILLS:
            text = (PLUGIN_ROOT / "skills" / skill / "SKILL.md").read_text()
            self.assertTrue(text.startswith("---\n"), skill)
            self.assertIn(f"name: {skill}", text)
            self.assertRegex(text, r"description: .+")

    def test_skill_portfolio_matches_catalog_and_project_migration_manifest(self):
        scripts = PLUGIN_ROOT / "scripts"
        sys.path.insert(0, str(scripts))
        try:
            from workflow_dependency_catalog import PROJECT_ORCHESTRATOR_SKILLS
        finally:
            sys.path.remove(str(scripts))

        migration = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "project-migration.json").read_text()
        )
        source_skills = {
            path.name for path in (PLUGIN_ROOT / "skills").iterdir() if path.is_dir()
        }

        self.assertEqual(source_skills, EXPECTED_DEVFLOW_SKILLS)
        self.assertEqual(set(PROJECT_ORCHESTRATOR_SKILLS), EXPECTED_DEVFLOW_SKILLS)
        self.assertEqual(set(migration["projectLocalSkills"]), EXPECTED_DEVFLOW_SKILLS)

    def test_skill_supporting_resources_are_directly_reachable(self):
        skills_root = PLUGIN_ROOT / "skills"
        for skill_name in EXPECTED_DEVFLOW_SKILLS:
            skill_root = skills_root / skill_name
            skill_text = (skill_root / "SKILL.md").read_text()
            resources = [
                path
                for directory in ("assets", "references")
                for path in (skill_root / directory).rglob("*")
                if path.is_file()
            ]
            for resource in resources:
                relative = resource.relative_to(skill_root).as_posix()
                with self.subTest(skill=skill_name, resource=relative):
                    self.assertIn(relative, skill_text)

        self.assertEqual(set(RESOURCE_USAGE_MARKERS), REQUIRED_SKILL_RESOURCES)
        for relative, marker in RESOURCE_USAGE_MARKERS.items():
            skill_name = relative.parts[0]
            skill_text = (skills_root / skill_name / "SKILL.md").read_text()
            with self.subTest(skill=skill_name, usage_marker=str(relative)):
                self.assertIn(normalized_text(marker), normalized_text(skill_text))

    def test_skill_supporting_resource_cleanup_contract(self):
        skills_root = PLUGIN_ROOT / "skills"
        for relative in REQUIRED_SKILL_RESOURCES:
            with self.subTest(required=str(relative)):
                self.assertTrue((skills_root / relative).is_file())
        for relative in REMOVED_SKILL_RESOURCES:
            with self.subTest(removed=str(relative)):
                self.assertFalse((skills_root / relative).exists())

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
        self.assertIn("ai-native-tech-plan", PROJECT_ORCHESTRATOR_SKILLS)
        self.assertIn("claude-code-delegate", PROJECT_ORCHESTRATOR_SKILLS)
        self.assertIn("dev-flow-refresh", PROJECT_ORCHESTRATOR_SKILLS)

    def test_decision_grilling_helper_routes_ambiguity_and_skips_approved_work(self):
        scripts = PLUGIN_ROOT / "scripts"
        sys.path.insert(0, str(scripts))
        try:
            from workflow_decision_grilling import decision_grilling_guidance, load_decision_grilling_matrix
        finally:
            sys.path.remove(str(scripts))

        matrix = load_decision_grilling_matrix(PLUGIN_ROOT)
        self.assertEqual(matrix["schemaVersion"], 2)
        self.assertEqual(matrix["sourcePath"], str(PLUGIN_ROOT / "docs" / "decision_grilling_matrix.json"))
        self.assertEqual(matrix["capabilityGate"], "decision-resolution")
        self.assertNotIn("methodGate", matrix)
        self.assertIn("one-question-at-a-time", matrix["protocol"])

        required = decision_grilling_guidance(
            kind="new-feature",
            request="Design a behavior change with compatibility tradeoffs.",
            open_questions=["Which compatibility policy should this use?"],
            plugin_root=PLUGIN_ROOT,
        )
        self.assertEqual(required["status"], "required")
        self.assertEqual(required["schema_version"], 2)
        self.assertEqual(required["capability_gate"], "decision-resolution")
        self.assertNotIn("method_gate", required)
        self.assertTrue(required["local_evidence_first"])
        self.assertIn("decision-grilling: required", required["ledger_entry"])
        self.assertIn("OpenSpec", " ".join(required["canonical_artifacts"]))
        self.assertIn("ask one question at a time", required["protocol_summary"])

        local = decision_grilling_guidance(
            kind="technical-plan",
            request="Which local skill path is active?",
            open_questions=["Which local skill path is active?"],
            locally_answerable=True,
            plugin_root=PLUGIN_ROOT,
        )
        self.assertEqual(local["status"], "required")
        self.assertEqual(local["next_action"], "inspect-local-evidence-before-asking")

        skipped = decision_grilling_guidance(
            kind="approved-task",
            request="Execute the already approved OpenSpec task.",
            open_questions=[],
            plugin_root=PLUGIN_ROOT,
        )
        self.assertEqual(skipped["schema_version"], 2)
        self.assertEqual(skipped["status"], "skipped")
        self.assertNotIn("method_gate", skipped)
        self.assertIn("approved", skipped["reason"])

        normal = decision_grilling_guidance(
            kind="new-feature",
            request="Implement the resolved design.",
            open_questions=[],
            plugin_root=PLUGIN_ROOT,
        )
        self.assertEqual(normal["schema_version"], 2)
        self.assertEqual(normal["status"], "skipped")
        self.assertNotIn("method_gate", normal)

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

    def test_dev_flow_refresh_description_preserves_independent_refresh_triggers(self):
        text = (PLUGIN_ROOT / "skills" / "dev-flow-refresh" / "SKILL.md").read_text()
        description = next(line for line in text.splitlines() if line.startswith("description: "))

        self.assertEqual(
            description,
            (
                "description: Use when DevFlow has upgraded, when refreshing the local/global "
                "DevFlow plugin installation or installed cache, or when refreshing DevFlow "
                "project-local workflow configuration across active projects."
            ),
        )

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
        self.assertTrue((repo / ".planning" / "devflow" / "STATE.md").exists())
        self.assertFalse((repo / ".planning" / "STATE.md").exists())
        self.assertFalse((repo / ".planning" / "ROADMAP.md").exists())
        self.assertFalse((repo / ".planning" / "phases").exists())
        workflow_config = json.loads((repo / ".dev-flow.json").read_text())
        self.assertEqual(
            workflow_config,
            {"projectContract": 2, "workflow": {"mode": "full-openspec"}},
        )
        self.assertTrue((repo / "openspec" / "changes" / "initial-target-state" / "tasks.md").exists())
        for filename in [
            "ENGINEERING_POLICY.md",
            "TASK_LEDGER.md",
            "EVIDENCE_TEMPLATE.md",
            "REVIEW_CHECKLIST.md",
        ]:
            self.assertTrue((repo / filename).exists(), filename)
        self.assertFalse((repo / "openspec" / "changes" / "initial-mvp").exists())
        self.assertTrue((repo / "setup-report.md").exists())
        state = (repo / ".planning" / "devflow" / "STATE.md").read_text()
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
        self.assertIn("## Capability Routing", agents)
        self.assertIn("## Intake and Planning", agents)
        self.assertIn("Matt Methodology Contract", agents)
        self.assertIn("workflow_methodology.py", agents)
        self.assertNotIn("methodology_profile", agents)
        self.assertNotIn("roadmap_provider", agents)
        self.assertIn("decision resolution", agents)
        self.assertIn("test-first execution", agents)
        self.assertIn("completion proof", agents)
        self.assertIn(".planning/devflow/STATE.md", agents)
        self.assertIn("ENGINEERING_POLICY.md", agents)
        self.assertIn("TASK_LEDGER.md", agents)
        self.assertIn("EVIDENCE_TEMPLATE.md", agents)
        self.assertIn("REVIEW_CHECKLIST.md", agents)

        valid = run_json("validate_workflow_state.py", "--repo", str(repo), "--json")
        self.assertTrue(valid["ok"])
        self.assertFalse(valid["gates"]["archive_allowed"])

    def test_contract_control_plane_validators_report_goal_task_evidence_review(self):
        repo = self.make_repo("greenfield-empty")
        run_json("scaffold_workflow.py", "--repo", str(repo), "--json")
        ledger = repo / "TASK_LEDGER.md"
        ledger.write_text(
            """# Task Ledger

## Goal Contract
- goal_id: optimize-devflow-v040-contract-first
- objective: Complete DevFlow v0.4.0 target state.
- scope_in: dependency governance, hooks, evidence, review
- scope_out: automatic hook trust
- acceptance_criteria: tests and release verification pass
- validation_commands: python3 -m unittest discover -s dev/plugins/dev-flow/tests
- knowledge_update_target: ENGINEERING_POLICY.md

## Tasks
| task_id | summary | owner | write_set | required_evidence | review_gate | status |
|---|---|---|---|---|---|---|
| T1 | Dependency governance | main | dev/plugins/dev-flow/scripts/*.py | red/green | review | planned |
"""
        )

        goal = run_json("validate_goal_contract.py", "--repo", str(repo), "--json")
        task = run_json("validate_task_ledger.py", "--repo", str(repo), "--json")

        self.assertTrue(goal["ok"], goal)
        self.assertEqual(goal["goal"]["goal_id"], "optimize-devflow-v040-contract-first")
        self.assertTrue(task["ok"], task)
        self.assertEqual(task["tasks"][0]["task_id"], "T1")
        self.assertIn("write_set", task["tasks"][0])

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

    def test_matt_notes_map_to_canonical_workflow_artifacts(self):
        agents_template = (PLUGIN_ROOT / "assets" / "templates" / "AGENTS.md.template").read_text()
        for phrase in [
            "## Capability Routing",
            "Matt Methodology Contract",
            "OpenSpec",
            ".planning/devflow/",
        ]:
            self.assertIn(phrase, agents_template)
        self.assertNotIn("docs/provider_profiles.json", agents_template)

        for skill in ["project-orchestrator", "feature-intake", "change-plan", "ai-native-tech-plan"]:
            text = (PLUGIN_ROOT / "skills" / skill / "SKILL.md").read_text()
            self.assertIn("Capability Routing", text, skill)
            self.assertIn("canonical", text, skill)
            self.assertIn("workflow_methodology.py", text, skill)

    def test_plugin_eval_gate_is_required_for_plugin_and_skill_changes(self):
        paths = {
            "root": REPO_ROOT / "AGENTS.md",
            "dev-template": PLUGIN_ROOT / "assets" / "templates" / "AGENTS.md.template",
            "release-template": RELEASE_PLUGIN_ROOT / "assets" / "templates" / "AGENTS.md.template",
        }
        for label, path in paths.items():
            text = path.read_text()
            normalized = normalized_text(text)
            with self.subTest(path=label):
                self.assertIn("## Plugin Eval Gate", text)
                self.assertIn("plugin-eval analyze", text)
                self.assertIn("creating or updating Codex plugins or skills", text)
                self.assertIn(
                    "record the score, findings, and optimization decisions",
                    normalized,
                )
                self.assertIn("default to fixing or optimizing", normalized.lower())
                self.assertIn("Deferral is an exception", text)
                self.assertIn("residual risk and follow-up path", normalized)

    def test_plugin_skill_changes_remind_local_reference_update(self):
        paths = {
            "root": REPO_ROOT / "AGENTS.md",
            "dev-template": PLUGIN_ROOT / "assets" / "templates" / "AGENTS.md.template",
            "release-template": RELEASE_PLUGIN_ROOT / "assets" / "templates" / "AGENTS.md.template",
            "dev-task-ledger": PLUGIN_ROOT
            / "skills"
            / "ai-native-tech-plan"
            / "assets"
            / "task-ledger-template.md",
            "release-task-ledger": RELEASE_PLUGIN_ROOT
            / "skills"
            / "ai-native-tech-plan"
            / "assets"
            / "task-ledger-template.md",
        }
        for label, path in paths.items():
            text = path.read_text()
            normalized = " ".join(text.split())
            with self.subTest(path=label):
                self.assertIn("Local Reference Update Reminder", text)
                self.assertIn("local Codex references", normalized)
                self.assertIn("codex_auto_update_plugins_skills.py --json", text)
                self.assertIn("installed plugin cache", normalized)
                self.assertIn("project-local skill links", normalized)

    def test_devflow_refresh_workflow_is_durable_agents_guidance(self):
        paths = {
            "root": REPO_ROOT / "AGENTS.md",
            "dev-template": PLUGIN_ROOT / "assets" / "templates" / "AGENTS.md.template",
            "release-template": RELEASE_PLUGIN_ROOT / "assets" / "templates" / "AGENTS.md.template",
        }
        for label, path in paths.items():
            text = path.read_text()
            normalized = normalized_text(text)
            with self.subTest(path=label):
                self.assertIn("## DevFlow Refresh Workflow", text)
                self.assertIn("dev-flow-refresh", text)
                self.assertIn("AGENTS.md.generated", text)
                self.assertIn("durable workflow rules", normalized)
                self.assertIn("codex plugin add dev-flow@cy-codex-skills --json", text)

    def test_repair_guidance_is_systemic_first_before_minimal_fix(self):
        paths = {
            "root": REPO_ROOT / "AGENTS.md",
            "dev-template": PLUGIN_ROOT / "assets" / "templates" / "AGENTS.md.template",
            "release-template": RELEASE_PLUGIN_ROOT / "assets" / "templates" / "AGENTS.md.template",
        }
        for label, path in paths.items():
            text = path.read_text()
            normalized = normalized_text(text)
            with self.subTest(path=label):
                self.assertIn("## Repair Solution Discipline", text)
                self.assertIn("systemic and thorough solution first", normalized)
                self.assertIn("minimal fix", text)
                self.assertIn("after investigation", normalized)

        skill_expectations = {
            "feature-intake": ["workflow repair", "systemic solution first", "minimal"],
            "change-plan": ["systemic solution first", "Target State", "Completion Contract"],
            "workflow-doctor": ["systemic repair", "root cause", "minimal"],
            "project-orchestrator": ["workflow-doctor", "root-cause-diagnosis"],
        }
        for skill_name, phrases in skill_expectations.items():
            text = (PLUGIN_ROOT / "skills" / skill_name / "SKILL.md").read_text()
            for phrase in phrases:
                self.assertIn(phrase, text, skill_name)

    def test_skill_routing_ledger_uses_static_capabilities(self):
        core_paths = {
            "root": REPO_ROOT / "AGENTS.md",
            "dev-template": PLUGIN_ROOT / "assets" / "templates" / "AGENTS.md.template",
            "task-ledger": PLUGIN_ROOT
            / "skills"
            / "ai-native-tech-plan"
            / "assets"
            / "task-ledger-template.md",
        }
        for label, path in core_paths.items():
            text = path.read_text()
            with self.subTest(path=label):
                self.assertIn("Skill Routing Ledger", text)
                self.assertIn("decision-resolution: required/used/skipped", text)
                self.assertIn("decision-grilling: required/used/skipped", text)
                self.assertIn("implementation-planning: required/used/skipped", text)
                self.assertIn("architecture-guidance: required/used/skipped", text)
                self.assertIn("artifact-status: draft/final", text)
                self.assertIn("Open Questions", text)
                self.assertNotIn("brainstorming: required/used/skipped", text)
                self.assertNotIn("writing-plans: required/used/skipped", text)

        agents = (PLUGIN_ROOT / "assets" / "templates" / "AGENTS.md.template").read_text()
        for phrase in [
            "Skill Routing Ledger",
            "capability-research: required/used/skipped",
            "decision-resolution: required/used/skipped",
            "decision-grilling: required/used/skipped",
            "implementation-planning: required/used/skipped",
            "architecture-guidance: required/used/skipped",
            "required capabilities",
            "Open Questions",
            "decision resolution",
        ]:
            self.assertIn(phrase, agents)

        skill_expectations = {
            "project-orchestrator": [
                "Capability Routing",
                "decision-resolution",
                "feature-intake",
            ],
            "feature-intake": [
                "Skill Routing Ledger",
                "decision-resolution",
                "Decision grilling",
                "Open Questions",
            ],
            "ai-native-tech-plan": [
                "Skill Routing Ledger",
                "Open Questions",
                "draft, not final",
                "decision-resolution",
            ],
        }
        for skill_name, phrases in skill_expectations.items():
            text = (PLUGIN_ROOT / "skills" / skill_name / "SKILL.md").read_text()
            with self.subTest(skill=skill_name):
                for phrase in phrases:
                    self.assertIn(phrase, text)

    def test_subagent_strategy_is_routed_with_validated_contract(self):
        project_orchestrator = normalized_text(
            (PLUGIN_ROOT / "skills" / "project-orchestrator" / "SKILL.md").read_text()
        )
        for phrase in [
            "## SubAgent Decision Gate",
            "Delegate when independent domains",
            "validated Agent Task Contract",
            "disjoint write sets",
            "main agent owns",
            "execution-orchestration",
        ]:
            self.assertIn(normalized_text(phrase), project_orchestrator)

        ai_plan = normalized_text(
            (PLUGIN_ROOT / "skills" / "ai-native-tech-plan" / "SKILL.md").read_text()
        )
        for phrase in [
            "SubAgent Strategy",
            "independent Capability Slices",
            "authorization state",
            "main-agent-owned",
        ]:
            self.assertIn(normalized_text(phrase), ai_plan)

        execute_task = normalized_text(
            (PLUGIN_ROOT / "skills" / "execute-task" / "SKILL.md").read_text()
        )
        for phrase in [
            "Delegated Execution",
            "DONE_WITH_CONCERNS",
            "files changed or inspected",
            "shared files remain serialized",
        ]:
            self.assertIn(normalized_text(phrase), execute_task)

        context_health = (PLUGIN_ROOT / "skills" / "context-health-check" / "SKILL.md").read_text()
        for phrase in [
            "planning, execution, context-health, and review boundaries",
            "repeated investigation pressure",
            "bounded review or delegation need",
        ]:
            self.assertIn(phrase, context_health)

    def test_agent_task_contract_gate_is_routed_for_delegated_work(self):
        expectations = {
            "project-orchestrator": [
                "Agent Task Contract",
                "validated Agent Task Contract",
                "Goal, Scope, Constraints, Verification, Evidence, and Human Gate",
            ],
            "execute-task": [
                "Agent Task Contract",
                "validate_agent_task_contract.py",
                "contract_path",
            ],
            "context-health-check": [
                "Agent Task Contract",
                "read-only explorer",
                "Human Gate",
                "explicit user authorization or an approved delegated workflow",
            ],
            "feature-intake": [
                "Agent Task Contract",
                "delegated agent, subagent, worker, or parallel execution",
            ],
            "ai-native-tech-plan": [
                "Agent Task Contract",
                "SubAgent Strategy",
                "authorization state",
            ],
        }
        for skill_name, phrases in expectations.items():
            text = (PLUGIN_ROOT / "skills" / skill_name / "SKILL.md").read_text()
            normalized = normalized_text(text)
            with self.subTest(skill=skill_name):
                for phrase in phrases:
                    self.assertIn(normalized_text(phrase), normalized)

        ledger = (PLUGIN_ROOT / "assets" / "templates" / "TASK_LEDGER.md.template").read_text()
        self.assertIn("contract_path", ledger)
        self.assertIn("AGENT_TASK_CONTRACT.md", ledger)

    def test_generated_artifact_cleanup_is_routed_through_execution_receipts(self):
        expectations = {
            "project-orchestrator": [
                "Generated Artifact Lifecycle",
                "fresh `AUTO_CLEAN`",
                "owning process exits",
                "`cleanup --apply`",
                "cleanup receipt",
                "`WAIT_OWNER`",
            ],
            "execute-task": [
                "Generated Artifact Contract",
                "before the owning command",
                "record_task_evidence.py",
                "G41",
                "cleanup_complete",
                "cleanup receipt",
            ],
        }
        for skill_name, phrases in expectations.items():
            text = normalized_text(
                (PLUGIN_ROOT / "skills" / skill_name / "SKILL.md").read_text()
            )
            with self.subTest(skill=skill_name):
                for phrase in phrases:
                    self.assertIn(normalized_text(phrase), text)

    def test_generated_artifact_registration_rule_is_in_every_control_plane_template(self):
        expectations = {
            PLUGIN_ROOT / "assets" / "templates" / "AGENTS.md.template": [
                "Generated Artifact Lifecycle",
                "before creation",
                "registration",
                "`AUTO_CLEAN`",
            ],
            PLUGIN_ROOT / "assets" / "templates" / "ENGINEERING_POLICY.md.template": [
                "Generated Artifact Contract",
                "pre-creation",
                "retroactive",
                "exact paths",
            ],
            PLUGIN_ROOT / "assets" / "templates" / "AGENT_TASK_CONTRACT.md.template": [
                "## Generated Artifact Contract",
                "optional",
                "G41",
                "cleanup_complete",
            ],
            PLUGIN_ROOT / "assets" / "templates" / "TASK_LEDGER.md.template": [
                "generated_artifact_contract",
                "registration-only",
                "cleanup receipt",
            ],
            PLUGIN_ROOT / "assets" / "templates" / "REVIEW_CHECKLIST.md.template": [
                "Generated Artifact Lifecycle",
                "pre-creation",
                "`WAIT_OWNER`",
                "no wildcard or recursive deletion",
            ],
            PLUGIN_ROOT / "skills" / "ai-native-tech-plan" / "SKILL.md": [
                "Generated Artifact Strategy",
                "pre-creation",
                "isolated root",
                "retention",
            ],
            PLUGIN_ROOT
            / "skills"
            / "ai-native-tech-plan"
            / "assets"
            / "task-ledger-template.md": [
                "## Generated Artifact Strategy",
                "registration-only",
                "manifest",
                "cleanup receipt",
            ],
        }
        for path, phrases in expectations.items():
            text = normalized_text(path.read_text())
            with self.subTest(path=path.name):
                for phrase in phrases:
                    self.assertIn(normalized_text(phrase), text)

    def test_generated_artifact_runtime_and_hook_docs_distinguish_all_routes(self):
        expectations = {
            PLUGIN_ROOT / "README.md": [
                "## Generated Artifact Lifecycle",
                "`WAIT_OWNER`",
                "automatic task-owned reclamation",
                "retained evidence",
                "destructive Human Gate",
            ],
            PLUGIN_ROOT / "docs" / "hook-contract.md": [
                "generated artifact lifecycle",
                "exact next action",
                "never invokes `cleanup --apply`",
            ],
            PLUGIN_ROOT / "docs" / "artifact-ownership.md": [
                "Generated Artifact Contract",
                "registration-only",
                "pre-existing",
                "terminal cleanup receipt",
            ],
            PLUGIN_ROOT / "docs" / "generated-artifact-lifecycle.md": [
                "`prepare`",
                "`observe`",
                "`plan`",
                "`cleanup --apply`",
                "`AUTO_CLEAN`",
                "`WAIT_OWNER`",
                "`RETAIN`",
                "`HUMAN_GATE`",
                "G41",
            ],
        }
        for path, phrases in expectations.items():
            self.assertTrue(path.is_file(), path)
            text = normalized_text(path.read_text())
            with self.subTest(path=path.name):
                for phrase in phrases:
                    self.assertIn(normalized_text(phrase), text)

    def test_subagent_strategy_is_documented_in_dev_and_release_readmes(self):
        expectations = [
            "## SubAgent Strategy",
            "policy/router layer",
            "scripts and hooks do not\nspawn subagents",
            "validated Agent Task Contract",
            "Root control-plane files, OpenSpec",
            "`DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or\n  `BLOCKED`",
        ]
        for label, path in {
            "dev": PLUGIN_ROOT / "README.md",
            "release": RELEASE_PLUGIN_ROOT / "README.md",
        }.items():
            text = path.read_text()
            normalized = normalized_text(text)
            with self.subTest(readme=label):
                for phrase in expectations:
                    self.assertIn(normalized_text(phrase), normalized)

    def test_git_transport_and_github_control_plane_guidance_are_independent(self):
        surfaces = {
            "project-orchestrator": PLUGIN_ROOT
            / "skills"
            / "project-orchestrator"
            / "SKILL.md",
            "verify-and-archive": PLUGIN_ROOT
            / "skills"
            / "verify-and-archive"
            / "SKILL.md",
            "root-agents": REPO_ROOT / "AGENTS.md",
            "generated-agents": PLUGIN_ROOT
            / "assets"
            / "templates"
            / "AGENTS.md.template",
        }
        phrases = [
            "Git Transport vs GitHub Control Plane",
            "gh authentication failure is not Git transport failure",
            "git ls-remote",
            "one diagnosis and at most one applicable remediation attempt",
            "github.control_plane_write",
        ]

        for label, path in surfaces.items():
            text = normalized_text(path.read_text())
            with self.subTest(surface=label):
                for phrase in phrases:
                    self.assertIn(normalized_text(phrase), text)

    def test_release_publication_guidance_prefers_repository_actions(self):
        detailed_surfaces = {
            "routing-reference": PLUGIN_ROOT / "docs" / "git_transport_routing.md",
            "project-orchestrator": PLUGIN_ROOT
            / "skills"
            / "project-orchestrator"
            / "SKILL.md",
            "verify-and-archive": PLUGIN_ROOT
            / "skills"
            / "verify-and-archive"
            / "SKILL.md",
        }
        detailed_phrases = [
            "github_actions",
            "github_cli",
            "human_web",
            "workflow exists in the immutable tag target",
            "GITHUB_TOKEN",
            "least privilege",
            "publication readback",
            "preserve the tag",
            "local promotion",
        ]
        summary_surfaces = {
            "root-agents": REPO_ROOT / "AGENTS.md",
            "generated-agents": PLUGIN_ROOT
            / "assets"
            / "templates"
            / "AGENTS.md.template",
        }
        summary_phrases = [
            "validated repository GitHub Actions",
            "local gh authentication",
            "publication readback",
            "preserve the tag",
        ]

        for label, path in detailed_surfaces.items():
            text = normalized_text(path.read_text())
            with self.subTest(surface=label):
                for phrase in detailed_phrases:
                    self.assertIn(normalized_text(phrase), text)

        for label, path in summary_surfaces.items():
            text = normalized_text(path.read_text())
            with self.subTest(surface=label):
                for phrase in summary_phrases:
                    self.assertIn(normalized_text(phrase), text)

    def test_devflow_hooks_and_scripts_do_not_spawn_subagents(self):
        forbidden = ["spawn_agent", "Task("]
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

    def test_devflow_hooks_and_scripts_do_not_execute_goal_tools(self):
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
            RELEASE_PLUGIN_ROOT / "hooks.json",
            *sorted((RELEASE_PLUGIN_ROOT / "scripts").glob("*.py")),
        ]
        violations = []
        for path in scan_roots:
            text = path.read_text().lower()
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
            self.assertTrue((brownfield / ".planning" / "devflow" / "codebase" / name).exists(), name)
        self.assertTrue((brownfield / "openspec" / "specs" / "current-system" / "spec.md").exists())

    def test_validate_reports_existing_agents_generated_merge_needed(self):
        existing = self.make_repo("existing-agents")
        run_json("scaffold_workflow.py", "--repo", str(existing), "--mode", "greenfield", "--json")

        validation = run_json("validate_workflow_state.py", "--repo", str(existing), "--json")

        self.assertFalse(validation["ok"], validation)
        self.assertTrue(
            any("AGENTS.md.generated" in issue and "merge" in issue for issue in validation["issues"]),
            validation,
        )

    def test_validate_warns_when_agents_contains_slice_boundary(self):
        repo = self.make_repo("greenfield-empty")
        run_json("scaffold_workflow.py", "--repo", str(repo), "--json")
        agents = repo / "AGENTS.md"
        agents.write_text(
            agents.read_text()
            + "\n## First Slice Boundary\n\n- Use file storage only in this slice.\n"
        )

        validation = run_json("validate_workflow_state.py", "--repo", str(repo), "--json")

        self.assertTrue(
            any("First Slice Boundary" in warning for warning in validation["warnings"]),
            validation,
        )

    def test_orchestrator_skills_route_stable_capabilities_and_core_skills(self):
        expectations = {
            "project-orchestrator": [
                "ai-native-tech-plan",
                "decision-resolution",
                "implementation-planning",
                "test-first-execution",
                "completion-proof",
            ],
            "ai-native-tech-plan": [
                "Target State",
                "Completion Contract",
                "Capability Slices",
                "Execution Ledger",
                "Validation Commands",
                "Goal Mode Prompt",
                "Continue Prompt",
                "OpenSpec",
                "implementation-planning",
            ],
            "project-setup": ["audit_context_tools.py", "workflow.mode: full-openspec"],
            "feature-intake": [
                "ai-native-tech-plan",
                "openspec-explore",
                "openspec-propose",
                "decision-resolution",
                "architecture-guidance",
            ],
            "change-plan": [
                "ai-native-tech-plan",
                "openspec-explore",
                "openspec-propose",
                "implementation-planning",
            ],
            "execute-task": [
                "Execution Ledger",
                "Completion Contract",
                "openspec-apply-change",
                "test-first-execution",
            ],
            "verify-and-archive": [
                "Completion Contract",
                "Execution Ledger",
                "completion-proof",
                "openspec-sync-specs",
                "openspec-archive-change",
            ],
            "workflow-doctor": ["methodology", "openspec-explore"],
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

    def test_lint_ai_plan_requires_decision_resolution_for_open_questions(self):
        repo = self.make_repo()
        missing_route = repo / "missing-route.md"
        write_ai_plan(
            missing_route,
            "Slice 1: validated capability.",
            target="Design the complete feature.",
            contract="- [ ] Open choices are explicit",
        )
        missing_route.write_text(
            missing_route.read_text()
            + "\n## Open Questions\n\n- Which deployment shape should be selected?\n"
        )

        bad = run_script_allow_failure("lint_ai_plan.py", str(missing_route))
        self.assertEqual(bad.returncode, 1)
        self.assertIn("unresolved Open Questions require decision-resolution", bad.stdout)

        legacy_route = repo / "legacy-route.md"
        write_ai_plan(
            legacy_route,
            "Slice 1: validated capability.",
            preface=(
                "## Skill Routing Ledger\n\n"
                "- kind: new-feature\n"
                "- superpowers:brainstorming: required - product tradeoffs remain.\n"
                "- decision-grilling: required - Open Questions remain.\n"
            ),
            target="Design the complete feature.",
            contract="- [ ] Open choices are explicit",
        )
        legacy_route.write_text(
            legacy_route.read_text()
            + "\n## Open Questions\n\n- Which deployment shape should be selected?\n"
        )

        legacy = run_script_allow_failure("lint_ai_plan.py", str(legacy_route))
        self.assertEqual(legacy.returncode, 1)
        self.assertIn("unresolved Open Questions require decision-resolution", legacy.stdout)

        routed = repo / "routed.md"
        write_ai_plan(
            routed,
            "Slice 1: validated capability.",
            preface=(
                "## Skill Routing Ledger\n\n"
                "- kind: new-feature\n"
                "- artifact-status: draft\n"
                "- decision-resolution: required - product tradeoffs remain.\n"
                "- decision-grilling: skipped - draft records unresolved choices.\n"
            ),
            target="Design the complete feature.",
            contract="- [ ] Open choices are explicit",
        )
        routed.write_text(
            routed.read_text() + "\n## Open Questions\n\n- Which deployment shape should be selected?\n"
        )

        good = run_script_allow_failure("lint_ai_plan.py", str(routed))
        self.assertEqual(good.returncode, 0, good.stdout + good.stderr)

        final_unresolved = repo / "final-unresolved.md"
        write_ai_plan(
            final_unresolved,
            "Slice 1: validated capability.",
            preface=(
                "## Skill Routing Ledger\n\n"
                "- kind: new-feature\n"
                "- artifact-status: final\n"
                "- decision-resolution: required - product tradeoffs remain.\n"
                "- decision-grilling: required - Open Questions remain.\n"
            ),
            target="Design the complete feature.",
            contract="- [ ] Open choices are explicit",
        )
        final_unresolved.write_text(
            final_unresolved.read_text()
            + "\n## Open Questions\n\n- Which deployment shape should be selected?\n"
        )

        final_result = run_script_allow_failure("lint_ai_plan.py", str(final_unresolved))
        self.assertEqual(final_result.returncode, 1)
        self.assertIn("unresolved Open Questions require artifact-status: draft", final_result.stdout)

        placeholder = repo / "placeholder-ledger.md"
        placeholder.write_text(
            (
                PLUGIN_ROOT
                / "skills"
                / "ai-native-tech-plan"
                / "assets"
                / "task-ledger-template.md"
            ).read_text()
            + "\n## Open Questions\n\n- Which deployment shape should be selected?\n"
        )

        placeholder_result = run_script_allow_failure("lint_ai_plan.py", str(placeholder))
        self.assertEqual(placeholder_result.returncode, 1)
        self.assertIn(
            "unresolved Open Questions require decision-resolution",
            placeholder_result.stdout,
        )

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
        state = (repo / ".planning" / "devflow" / "STATE.md").read_text()
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
        self.assertTrue(recorded["path"].startswith(".planning/devflow/verification/"))
        self.assertFalse((repo / ".planning" / "phases").exists())
        state = (repo / ".planning" / "devflow" / "STATE.md").read_text()
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
        self.assertTrue(checkpoint["checkpoint_file"].startswith(".planning/devflow/checkpoints/"))
        self.assertEqual(checkpoint["compact_status"], "pending")
        state = (repo / ".planning" / "devflow" / "STATE.md").read_text()
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

    def test_checkpoint_explicit_no_continuation_is_a_stopping_point(self):
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
            "--change",
            "initial-target-state",
            "--next-stage",
            "review_or_archive",
            "--no-continuation-required",
            "--current-goal",
            "Finish verified work",
            "--completed-work",
            "Verification passed",
            "--decision",
            "Stop at an explicitly declared boundary",
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

        state = (repo / ".planning" / "devflow" / "STATE.md").read_text()
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
            "--no-continuation-required",
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
        checkpoint_text = (repo / checkpoint["checkpoint_file"]).read_text()
        self.assertIn("Compact is recommended", checkpoint_text)
        self.assertNotIn("Run `/compact` before continuing", checkpoint_text)

    def test_validate_checkpoint_reports_missing_required_sections(self):
        repo = self.make_repo("greenfield-empty")
        run_json("scaffold_workflow.py", "--repo", str(repo), "--json")
        checkpoint = repo / ".planning" / "devflow" / "checkpoints" / "bad.md"
        checkpoint.parent.mkdir(parents=True)
        checkpoint.write_text("# Checkpoint: bad\n\n## Current goal\n\nOnly goal is present.\n")
        result = run_json(
            "validate_checkpoint.py",
            "--repo",
            str(repo),
            "--checkpoint",
            ".planning/devflow/checkpoints/bad.md",
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
        self.assertEqual(blocked.returncode, 0)
        blocked_payload = json.loads(blocked.stdout)
        self.assertEqual(
            blocked_payload["hookSpecificOutput"]["permissionDecision"],
            "deny",
        )

        (repo / ".dev-flow.json").write_text(json.dumps({"hook": {"mode": "off"}}))
        off = run_script("pre_edit_policy.py", input_text=payload)
        self.assertEqual(off.stdout.strip(), "")

        (repo / ".dev-flow.json").unlink()
        (repo / ".codex-project-orchestrator.json").write_text(json.dumps({"hook": {"mode": "off"}}))
        legacy_ignored = run_script("pre_edit_policy.py", input_text=payload)
        self.assertIn(DISPLAY_NAME, legacy_ignored.stdout)

    def test_checkpoint_stop_policy_allows_pending_compact_advisory(self):
        repo = self.make_repo("greenfield-empty")
        run_json("scaffold_workflow.py", "--repo", str(repo), "--json")
        self.create_pending_checkpoint(repo)
        payload = json.dumps({"cwd": str(repo), "tool_name": "Stop", "tool_input": {}})
        advisory = run_script("stop_checkpoint_policy.py", input_text=payload)
        self.assertEqual(advisory.returncode, 0)
        self.assertEqual(advisory.stdout.strip(), "")

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

        state = (repo / ".planning" / "devflow" / "STATE.md").read_text()
        self.assertIn("compact_status: completed", state)
        self.assertIn(f"last_compact_result_file: {recorded['compact_result_file']}", state)
        self.assertIn("compact_source: responses_api", state)

    def test_phase_transition_hook_is_retired(self):
        self.assertFalse(
            (PLUGIN_ROOT / "scripts" / "pre_next_phase_checkpoint_policy.py").exists()
        )
        hooks = json.loads((PLUGIN_ROOT / "hooks.json").read_text())
        self.assertNotIn("pre_next_phase", json.dumps(hooks, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
