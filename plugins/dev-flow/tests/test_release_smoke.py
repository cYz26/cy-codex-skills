import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ARCHIVE = PLUGIN_ROOT / "scripts" / "devflow_runtime.pyz"


def normalized_text(text):
    return " ".join(text.split())


class ReleaseSmokeTests(unittest.TestCase):
    def test_manifest_uses_packaged_entrypoints(self):
        manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text())

        self.assertEqual(manifest["name"], "dev-flow")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(manifest["hooks"], "./hooks.json")
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
        self.assertTrue((PLUGIN_ROOT / manifest["interface"]["logo"]).exists())
        self.assertTrue((PLUGIN_ROOT / "hooks.json").exists())

    def test_context_tool_facade_is_importable_and_dry_runs(self):
        home = Path(tempfile.mkdtemp(prefix="devflow-release-home-"))
        repo = Path(tempfile.mkdtemp(prefix="devflow-release-repo-"))
        skill = home / "skills" / "example" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: example\ndescription: fixture\n---\n")
        (repo / "package.json").write_text('{"dependencies":{"react":"latest"}}\n')

        audit_result = subprocess.run(
            [
                "python3",
                str(PLUGIN_ROOT / "scripts" / "audit_context_tools.py"),
                "--codex-home",
                str(home),
                "--repo",
                str(repo),
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(audit_result.returncode, 0, audit_result.stderr)
        audit = json.loads(audit_result.stdout)
        self.assertTrue(audit["ok"])
        self.assertIn("inventory", audit)
        self.assertIn("actions", audit)

        plan = repo / "audit.json"
        plan.write_text(json.dumps(audit))
        apply_result = subprocess.run(
            [
                "python3",
                str(PLUGIN_ROOT / "scripts" / "apply_context_tool_actions.py"),
                "--plan",
                str(plan),
                "--all-safe",
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(apply_result.returncode, 0, apply_result.stderr)
        result = json.loads(apply_result.stdout)
        self.assertTrue(result["dryRun"])
        self.assertIn("applied", result)

    def test_runtime_archive_is_packaged(self):
        self.assertTrue(RUNTIME_ARCHIVE.exists())

    def test_subagent_and_repair_guidance_is_packaged(self):
        readme = (PLUGIN_ROOT / "README.md").read_text()
        self.assertIn("## Repair Solution Discipline", readme)
        self.assertIn("## SubAgent Strategy", readme)
        self.assertIn("policy/router layer", readme)
        self.assertIn("does not spawn subagents from scripts or hooks", readme)
        self.assertIn("explicit user authorization", readme)

    def test_goal_slash_command_guidance_is_packaged(self):
        readme = (PLUGIN_ROOT / "README.md").read_text()
        normalized_readme = normalized_text(readme)
        for phrase in [
            "define-goal",
            "Goal Suitability Gate",
            "before context-health drift",
            "long-running",
            "multi-slice",
            "migration",
            "release",
            "cross-context",
            "/goal <objective>",
            "/goal pause",
            "/goal resume",
            "/goal clear",
            "features.goals",
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
                self.assertIn("Goal Suitability Gate", normalized)
                self.assertIn("Goal Quality Gate", normalized)
                self.assertIn("before context-health drift", normalized)
                self.assertIn("/goal <objective>", normalized)
                self.assertIn("/goal pause", normalized)
                self.assertIn("/goal resume", normalized)
                self.assertIn("/goal clear", normalized)
                self.assertIn("features.goals", normalized)
                self.assertIn("codex features enable goals", normalized)
                self.assertNotIn("`codex goal`", normalized.lower())
                self.assertNotIn("codex goal --help", normalized.lower())

        objective = (
            "Implement a release goal quality check, limited to release smoke "
            "validation, excluding live goal tool calls, verified by release "
            "smoke tests with all commands exiting 0, and stop before changing "
            "hook behavior."
        )
        result = subprocess.run(
            [
                "python3",
                str(PLUGIN_ROOT / "scripts" / "validate_goal_quality.py"),
                "--objective",
                objective,
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["ok"])

    def test_decision_grilling_contract_is_packaged(self):
        matrix = PLUGIN_ROOT / "docs" / "decision_grilling_matrix.json"
        self.assertTrue(matrix.exists())
        contract = json.loads(matrix.read_text())
        self.assertEqual(contract["schemaVersion"], 1)
        self.assertIn("one-question-at-a-time", contract["protocol"])
        self.assertIn("OpenSpec", " ".join(contract["canonicalArtifacts"]))

        result = subprocess.run(
            [
                "python3",
                str(PLUGIN_ROOT / "scripts" / "workflow_decision_grilling.py"),
                "--kind",
                "new-feature",
                "--request",
                "Design behavior with open compatibility questions.",
                "--open-question",
                "Which compatibility policy applies?",
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        guidance = json.loads(result.stdout)
        self.assertEqual(guidance["status"], "required")
        self.assertIn("decision-grilling: required", guidance["ledger_entry"])
        self.assertTrue(guidance["local_evidence_first"])

    def test_agent_task_contract_gate_is_packaged(self):
        template = PLUGIN_ROOT / "assets" / "templates" / "AGENT_TASK_CONTRACT.md.template"
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

        contract = Path(tempfile.mkdtemp(prefix="agent-contract-")) / "contract.md"
        contract.write_text(
            """# Agent Task Contract

## Goal
Read the specified files and report the requested review result.

## Scope
Allowed: inspect `dev/plugins/dev-flow/scripts/workflow_state.py`.
Forbidden: do not edit files, do not modify release assets, and do not update
workflow state.

## Constraints
Read-only review. Preserve privacy and avoid copying long logs.

## Verification
Not applicable: this is a read-only explorer task; verify by reporting inspected files.

## Evidence
Report changed files, commands run, test logs or validation results,
unverified areas, and risk notes.

## Human Gate
Wait for review before editing files, expanding scope, or continuing with
missing evidence.
"""
        )
        result = subprocess.run(
            [
                "python3",
                str(PLUGIN_ROOT / "scripts" / "validate_agent_task_contract.py"),
                "--contract",
                str(contract),
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"], report)

    def test_context_health_disposition_cli_is_packaged(self):
        skill = PLUGIN_ROOT / "skills" / "context-health-check" / "SKILL.md"
        self.assertIn("record_context_health_disposition.py", skill.read_text())

        cli = PLUGIN_ROOT / "scripts" / "record_context_health_disposition.py"
        self.assertTrue(cli.exists())

        with zipfile.ZipFile(RUNTIME_ARCHIVE) as archive:
            names = set(archive.namelist())
        self.assertIn("record_context_health_disposition.py", names)
        self.assertIn("workflow_context_health_subagents.py", names)


if __name__ == "__main__":
    unittest.main()
