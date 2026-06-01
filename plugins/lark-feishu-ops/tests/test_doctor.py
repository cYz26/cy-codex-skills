import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import lark_feishu_ops_doctor


OFFICIAL_LARK_SKILLS = {
    "lark-approval",
    "lark-apps",
    "lark-attendance",
    "lark-base",
    "lark-calendar",
    "lark-contact",
    "lark-doc",
    "lark-drive",
    "lark-event",
    "lark-im",
    "lark-mail",
    "lark-markdown",
    "lark-minutes",
    "lark-okr",
    "lark-openapi-explorer",
    "lark-shared",
    "lark-sheets",
    "lark-skill-maker",
    "lark-slides",
    "lark-task",
    "lark-vc",
    "lark-vc-agent",
    "lark-whiteboard",
    "lark-wiki",
    "lark-workflow-meeting-summary",
    "lark-workflow-standup-report",
}


class LarkFeishuOpsDoctorTests(unittest.TestCase):
    def make_repo(self):
        return Path(tempfile.mkdtemp(prefix="lark-feishu-ops-test-repo-"))

    def write_project_skill(self, repo, name, frontmatter_name=None):
        skill_dir = repo / ".codex" / "skills" / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_name = frontmatter_name or name
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: fixture\n---\n",
            encoding="utf-8",
        )

    def run_check_lark_cli(self, *, offline):
        commands = []

        def fake_run_command(command, timeout=30):
            commands.append(command)
            stdout = ""
            if command == ["lark-cli", "--version"]:
                stdout = "lark-cli version 1.0.43"
            elif command == ["lark-cli", "update", "--check", "--json"]:
                stdout = json.dumps({"action": "already_up_to_date", "ok": True})
            return {
                "command": command,
                "ok": True,
                "exit_code": 0,
                "stdout": stdout,
                "stderr": "",
            }

        with (
            mock.patch.object(lark_feishu_ops_doctor.shutil, "which", return_value="/usr/local/bin/lark-cli"),
            mock.patch.object(lark_feishu_ops_doctor, "run_command", side_effect=fake_run_command),
        ):
            result = lark_feishu_ops_doctor.check_lark_cli(skip_update_check=False, offline=offline)

        self.assertEqual(result["status"], "PASS")
        return commands

    def test_check_lark_cli_runs_online_doctor_by_default(self):
        commands = self.run_check_lark_cli(offline=False)

        self.assertIn(["lark-cli", "doctor"], commands)
        self.assertNotIn(["lark-cli", "doctor", "--offline"], commands)

    def test_check_lark_cli_runs_offline_doctor_when_requested(self):
        commands = self.run_check_lark_cli(offline=True)

        self.assertIn(["lark-cli", "doctor", "--offline"], commands)

    def test_runtime_prompt_keeps_lazy_reference_parity_with_official_lark_skills(self):
        prompt = (PLUGIN_ROOT / "agents" / "runtime-prompts" / "feishu-ops.md").read_text()

        missing = sorted(skill for skill in OFFICIAL_LARK_SKILLS if skill not in prompt)

        self.assertEqual([], missing)

    def test_runtime_prompt_keeps_docs_fetch_bounded(self):
        prompt = (PLUGIN_ROOT / "agents" / "runtime-prompts" / "feishu-ops.md").read_text()

        required = [
            "Do exactly one declared operation",
            "Do not silently continue from `docs.fetch` into `sheets.read`",
            "Default behavior is document-only",
            "`result.next_resources`",
        ]

        for text in required:
            self.assertIn(text, prompt)

    def test_runtime_prompt_supports_intent_carrying_evidence_packs(self):
        prompt = (PLUGIN_ROOT / "agents" / "runtime-prompts" / "feishu-ops.md").read_text()

        required = [
            '"question": "optional user question',
            "Evidence Pack Rules",
            "`result.evidence_pack`",
            "coverage",
            "missing_evidence",
            "Do not make the final product, technical, or business judgment",
            "This applies to every read/query domain, not only documents",
            "Sheets/Base",
            "Calendar/VC/Minutes",
            "IM/Mail",
            "For write operations, return a side-effect evidence pack",
        ]

        for text in required:
            self.assertIn(text, prompt)

    def test_runtime_prompt_documents_context_capsule_rules(self):
        prompt = (PLUGIN_ROOT / "agents" / "runtime-prompts" / "feishu-ops.md").read_text()

        required = [
            '"handoff_context"',
            "Context Capsule Rules",
            "source of truth",
            "known_resources",
            "prior_evidence_pack",
            "freshness",
            "non_goals",
            "Do not require full parent conversation",
        ]

        for text in required:
            self.assertIn(text, prompt)

    def test_runtime_prompt_documents_follow_up_reuse(self):
        prompt = (PLUGIN_ROOT / "agents" / "runtime-prompts" / "feishu-ops.md").read_text()

        required = [
            "Follow-Up Reuse",
            "related follow-up about the same resource",
            "document IDs",
            "revisions",
            "chat IDs",
            "cursors",
            "time windows",
            "If the parent starts a new subagent instead",
        ]

        for text in required:
            self.assertIn(text, prompt)

    def test_skill_documents_progress_aware_parent_waiting(self):
        skill = (PLUGIN_ROOT / "skills" / "lark-feishu-ops" / "SKILL.md").read_text()

        required = [
            "Progress-Aware Waiting",
            "Use an idle timeout for stuck detection",
            "Do not close an agent merely because the overall wall-clock",
            "2-3 minutes is reasonable",
            "60-90 seconds of no progress",
            "do not silently run direct",
        ]

        for text in required:
            self.assertIn(text, skill)

    def test_skill_documents_hybrid_dispatch_policy(self):
        skill = (PLUGIN_ROOT / "skills" / "lark-feishu-ops" / "SKILL.md").read_text()

        required = [
            "Dispatch Policy",
            "Main-agent direct `lark-cli` is allowed",
            "read-only, bounded, and easy to validate",
            "The user did not explicitly ask for `FeishuOps`, subagents, or delegated execution",
            "Escalate to `FeishuOps`",
            "writes, sends, creates, updates, deletes",
            "cross-domain, multi-step",
            "raw-OpenAPI-heavy",
            "If the user explicitly requested FeishuOps/subagent routing",
        ]

        for text in required:
            self.assertIn(text, skill)

    def test_readme_documents_hybrid_dispatch_policy(self):
        readme = (PLUGIN_ROOT / "README.md").read_text()

        required = [
            "hybrid route",
            "direct main-agent `lark-cli` for bounded low-risk reads",
            "The main agent can run `lark-cli` directly",
            "The main agent should route to FeishuOps",
            "explicitly asked for FeishuOps or subagent routing",
            "2-3 minutes is reasonable",
        ]

        for text in required:
            self.assertIn(text, readme)

    def test_skill_documents_intent_and_follow_up_reuse(self):
        skill = (PLUGIN_ROOT / "skills" / "lark-feishu-ops" / "SKILL.md").read_text()

        required = [
            "Intent-Carrying Operations",
            '"question": "optional user question',
            "An evidence pack should be stronger than a summary",
            "This applies across Lark domains, not only documents",
            "Sheets/Base",
            "Calendar/VC/Minutes",
            "IM/Mail/Task/Approval/OKR/Attendance",
            "For write operations, FeishuOps should return a side-effect evidence pack",
            "Related Follow-Ups",
            "prefer reusing the same",
        ]

        for text in required:
            self.assertIn(text, skill)

    def test_skill_documents_context_handoff(self):
        skill = (PLUGIN_ROOT / "skills" / "lark-feishu-ops" / "SKILL.md").read_text()

        required = [
            "Context Handoff",
            '"handoff_context"',
            "Use a context capsule instead of forwarding the whole parent conversation",
            "inherit runtime boundaries",
            "do not automatically inherit the parent thread's full business context",
            "Use full parent-context forking only",
            "prior evidence pack",
            "hidden memory from closed agents",
        ]

        for text in required:
            self.assertIn(text, skill)

    def test_skill_documents_codex_subagent_mechanics(self):
        skill = (PLUGIN_ROOT / "skills" / "lark-feishu-ops" / "SKILL.md").read_text()

        required = [
            "Codex Subagent Mechanics",
            "inherit the parent model selection",
            "Do not assume every parent skill instruction is active",
            "Use context forking only when",
            "Pass the FeishuOps runtime prompt",
            "Waiting primitives normally report final completion or timeout",
            "official primitives solve process mechanics",
            "domain mechanics",
        ]

        for text in required:
            self.assertIn(text, skill)

    def test_agent_instructions_keep_subagent_bounded(self):
        agent = (PLUGIN_ROOT / "agents" / "feishu-ops.toml").read_text()

        required = [
            "`handoff_context`",
            "authoritative parent context",
            "Keep each run bounded to the declared platform operation",
            "result.next_resources",
            "Emit concrete progress updates",
            "result.evidence_pack",
            "For write domains, return a side-effect evidence pack",
            "For related follow-ups in the same subagent",
        ]

        for text in required:
            self.assertIn(text, agent)

    def test_project_lark_skill_audit_passes_empty_repo(self):
        repo = self.make_repo()

        result = lark_feishu_ops_doctor.audit_project_lark_skills(repo)

        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["project_scattered_lark_skills"])
        self.assertEqual([], result["actions"])
        self.assertIn("dispatch_policy", result["suggested_configuration"])
        self.assertIn("bounded low-risk reads", result["suggested_configuration"]["dispatch_policy"])

    def test_project_lark_skill_audit_warns_for_scattered_lark_skills(self):
        repo = self.make_repo()
        self.write_project_skill(repo, "lark-doc")

        result = lark_feishu_ops_doctor.audit_project_lark_skills(repo)

        self.assertEqual("WARN", result["status"])
        self.assertEqual(["lark-doc"], [item["name"] for item in result["project_scattered_lark_skills"]])
        self.assertIn("lark-feishu-ops", " ".join(result["recommendations"]))
        self.assertEqual("remove_project_lark_skill", result["actions"][0]["type"])
        self.assertEqual("lark-doc", result["actions"][0]["skill"])

    def test_project_lark_skill_audit_accepts_dedicated_lark_feishu_ops_skill(self):
        repo = self.make_repo()
        self.write_project_skill(repo, "lark-feishu-ops")

        result = lark_feishu_ops_doctor.audit_project_lark_skills(repo)

        self.assertEqual("PASS", result["status"])
        self.assertEqual(["lark-feishu-ops"], [item["name"] for item in result["project_lark_feishu_ops"]])
        self.assertEqual([], result["project_scattered_lark_skills"])


if __name__ == "__main__":
    unittest.main()
