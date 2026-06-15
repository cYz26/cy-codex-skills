import json
import re
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

INSTALLED_OFFICIAL_LARK_SKILLS = set(OFFICIAL_LARK_SKILLS)


def extract_runtime_official_lark_skills(prompt):
    section = prompt.split("Current official lazy-reference set:", 1)[1]
    section = section.split("Do not install the full official", 1)[0]
    return set(re.findall(r"`(lark-[a-z0-9-]+)`", section))


def read_skill():
    return (PLUGIN_ROOT / "skills" / "lark-feishu-ops" / "SKILL.md").read_text()


def read_protocol_reference():
    return (
        PLUGIN_ROOT
        / "skills"
        / "lark-feishu-ops"
        / "references"
        / "feishuops-protocol.md"
    ).read_text()


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
        cache_path = self.make_repo() / "update-check.json"

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
            result = lark_feishu_ops_doctor.check_lark_cli(
                skip_update_check=False,
                offline=offline,
                cache_path=cache_path,
            )

        self.assertEqual(result["status"], "PASS")
        return commands

    def test_check_lark_cli_runs_online_doctor_by_default(self):
        commands = self.run_check_lark_cli(offline=False)

        self.assertIn(["lark-cli", "doctor"], commands)
        self.assertNotIn(["lark-cli", "doctor", "--offline"], commands)

    def test_check_lark_cli_runs_offline_doctor_when_requested(self):
        commands = self.run_check_lark_cli(offline=True)

        self.assertIn(["lark-cli", "doctor", "--offline"], commands)

    def test_daily_update_check_uses_cache_for_current_local_date(self):
        commands = []
        cache_path = self.make_repo() / "update-check.json"
        today = lark_feishu_ops_doctor.local_date()
        cache_path.write_text(
            json.dumps(
                {
                    "checked_local_date": today,
                    "checked_at": "2026-06-04T20:00:00+08:00",
                    "action": "already_up_to_date",
                    "current_version": "1.0.47",
                    "latest_version": "1.0.47",
                    "ok": True,
                    "payload": {"action": "already_up_to_date", "ok": True},
                }
            ),
            encoding="utf-8",
        )

        def fake_run_command(command, timeout=30):
            commands.append(command)
            stdout = "lark-cli version 1.0.47" if command == ["lark-cli", "--version"] else "{}"
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
            result = lark_feishu_ops_doctor.check_lark_cli(
                skip_update_check=False,
                offline=False,
                cache_path=cache_path,
            )

        self.assertEqual("PASS", result["status"])
        self.assertNotIn(["lark-cli", "update", "--check", "--json"], commands)
        self.assertTrue(result["update_check"]["cached"])
        self.assertEqual("already_up_to_date", result["update_check"]["payload"]["action"])

    def test_force_update_check_bypasses_daily_cache(self):
        commands = []
        cache_path = self.make_repo() / "update-check.json"
        cache_path.write_text(
            json.dumps(
                {
                    "checked_local_date": lark_feishu_ops_doctor.local_date(),
                    "checked_at": "2026-06-04T20:00:00+08:00",
                    "action": "already_up_to_date",
                    "ok": True,
                    "payload": {"action": "already_up_to_date", "ok": True},
                }
            ),
            encoding="utf-8",
        )

        def fake_run_command(command, timeout=30):
            commands.append(command)
            stdout = ""
            if command == ["lark-cli", "--version"]:
                stdout = "lark-cli version 1.0.47"
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
            result = lark_feishu_ops_doctor.check_lark_cli(
                skip_update_check=False,
                offline=False,
                force_update_check=True,
                cache_path=cache_path,
            )

        self.assertEqual("PASS", result["status"])
        self.assertIn(["lark-cli", "update", "--check", "--json"], commands)
        self.assertFalse(result["update_check"].get("cached", False))

    def test_update_available_returns_confirmation_action(self):
        cache_path = self.make_repo() / "update-check.json"

        def fake_run_command(command, timeout=30):
            stdout = ""
            if command == ["lark-cli", "--version"]:
                stdout = "lark-cli version 1.0.43"
            elif command == ["lark-cli", "update", "--check", "--json"]:
                stdout = json.dumps(
                    {
                        "action": "update_available",
                        "ok": True,
                        "current_version": "1.0.43",
                        "latest_version": "1.0.47",
                    }
                )
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
            result = lark_feishu_ops_doctor.check_lark_cli(
                skip_update_check=False,
                offline=False,
                cache_path=cache_path,
            )

        self.assertEqual("WARN", result["status"])
        self.assertTrue(result["update_action"]["requires_confirmation"])
        self.assertEqual(["lark-cli", "update", "--json"], result["update_action"]["command"])
        self.assertEqual("1.0.43", result["update_action"]["current_version"])
        self.assertEqual("1.0.47", result["update_action"]["latest_version"])
        self.assertIn("lark_feishu_ops_sync.py", " ".join(result["update_action"]["followup_command"]))

    def test_global_audit_ignores_unmanaged_lark_directories_after_codex_unload(self):
        listing = {
            "status": "PASS",
            "npx_path": "/usr/local/bin/npx",
            "skills": [
                {
                    "name": "lark-doc",
                    "path": "/Users/cy/.agents/skills/lark-doc",
                    "agents": ["Codex", "Claude Code"],
                }
            ],
            "error": None,
        }

        with (
            mock.patch.object(lark_feishu_ops_doctor, "list_global_skills", return_value=listing),
            mock.patch.object(lark_feishu_ops_doctor, "load_skill_lock_sources", return_value={}),
        ):
            result = lark_feishu_ops_doctor.audit_global_lark_skills()

        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["official_global_lark_skills"])
        self.assertEqual([], result["codex_effective_official_lark_skills"])

    def test_runtime_prompt_keeps_lazy_reference_parity_with_official_lark_skills(self):
        prompt = (PLUGIN_ROOT / "agents" / "runtime-prompts" / "feishu-ops.md").read_text()

        missing = sorted(skill for skill in OFFICIAL_LARK_SKILLS if skill not in prompt)

        self.assertEqual([], missing)

    def test_runtime_prompt_lazy_references_are_installed_official_skills(self):
        prompt = (PLUGIN_ROOT / "agents" / "runtime-prompts" / "feishu-ops.md").read_text()

        advertised = extract_runtime_official_lark_skills(prompt)
        stale = sorted(advertised - INSTALLED_OFFICIAL_LARK_SKILLS)

        self.assertEqual([], stale)

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

    def test_runtime_prompt_documents_context_cache_update(self):
        prompt = (PLUGIN_ROOT / "agents" / "runtime-prompts" / "feishu-ops.md").read_text()

        required = [
            "context_cache_update",
            "resource_refs",
            "known_command_shapes",
            "Do not include full conversation transcripts",
        ]

        for text in required:
            self.assertIn(text, prompt)

    def test_skill_defers_deep_feishuops_protocol(self):
        skill = read_skill()

        self.assertIn("references/feishuops-protocol.md", skill)
        self.assertLess(len(skill.splitlines()), 250)
        self.assertNotIn("## Progress-Aware Waiting", skill)
        self.assertIn("## Progress-Aware Waiting", read_protocol_reference())

    def test_protocol_reference_documents_progress_aware_parent_waiting(self):
        protocol = read_protocol_reference()

        required = [
            "Progress-Aware Waiting",
            "Use an idle timeout for stuck detection",
            "Do not close an agent merely because the overall wall-clock",
            "2-3 minutes is reasonable",
            "60-90 seconds of no progress",
        ]

        for text in required:
            self.assertIn(text, protocol)

    def test_skill_documents_hybrid_dispatch_policy(self):
        skill = read_skill()

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

    def test_readme_documents_agent_continuity_helper(self):
        readme = (PLUGIN_ROOT / "README.md").read_text()

        required = [
            "Agent Continuity Helper",
            "active_agents.json",
            "snapshots/",
            "direct`, `reuse_active`, `reconstruct_from_cache`, or `fresh_subagent`",
            "does not call Codex subagent primitives",
        ]

        for text in required:
            self.assertIn(text, readme)

    def test_skill_documents_intent_and_follow_up_reuse(self):
        protocol = read_protocol_reference()

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
            self.assertIn(text, protocol)

    def test_skill_documents_context_handoff(self):
        protocol = read_protocol_reference()

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
            self.assertIn(text, protocol)

    def test_skill_documents_agent_continuity_helper(self):
        protocol = read_protocol_reference()

        required = [
            "Agent Continuity Helper",
            "lark_feishu_ops_agent_context.py prepare",
            ".dev-flow/lark-feishu-ops/agent-context/",
            "reuse_active",
            "reconstruct_from_cache",
            "fresh_subagent",
            "The helper does not spawn, message, wait for, or close subagents",
            "context_cache_update",
        ]

        for text in required:
            self.assertIn(text, protocol)

    def test_skill_documents_codex_subagent_mechanics(self):
        protocol = read_protocol_reference()

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
            self.assertIn(text, protocol)

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

    def test_agent_instructions_document_context_cache_update(self):
        agent = (PLUGIN_ROOT / "agents" / "feishu-ops.toml").read_text()

        required = [
            "context_cache_update",
            "resource refs",
            "freshness",
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
