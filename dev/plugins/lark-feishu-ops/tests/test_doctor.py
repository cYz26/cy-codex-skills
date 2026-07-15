import json
import os
import re
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
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
    "lark-note",
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


def collect_lark_skill_names(value):
    names = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"name", "skill"} and isinstance(item, str) and item.startswith("lark-"):
                names.add(item)
            names.update(collect_lark_skill_names(item))
    elif isinstance(value, list):
        for item in value:
            names.update(collect_lark_skill_names(item))
    elif isinstance(value, str) and value.startswith("lark-"):
        names.add(value)
    return names


def find_first_key(value, wanted):
    if isinstance(value, dict):
        if wanted in value:
            return value[wanted]
        for item in value.values():
            found = find_first_key(item, wanted)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = find_first_key(item, wanted)
            if found is not None:
                return found
    return None


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

    def write_project_skill(self, repo, name, frontmatter_name=None, root=".agents/skills"):
        skill_dir = repo / root / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_name = frontmatter_name or name
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: fixture\n---\n",
            encoding="utf-8",
        )
        return skill_dir

    def write_skill_lock(self, payload):
        root = self.make_repo()
        lock_path = root / ".agents" / ".skill-lock.json"
        lock_path.parent.mkdir(parents=True)
        lock_path.write_text(json.dumps(payload), encoding="utf-8")
        return lock_path

    def write_fake_lark_cli(self, bin_dir, version="1.0.69", skills=None):
        bin_dir.mkdir(parents=True, exist_ok=True)
        skill_names = sorted(skills or OFFICIAL_LARK_SKILLS)
        skills_payload = json.dumps(
            {
                "ok": True,
                "skills": [
                    {"name": name, "description": f"synthetic {name}", "version": "1.0.0"}
                    for name in skill_names
                ],
                "count": len(skill_names),
            }
        )
        read_payload = json.dumps(
            {
                "skill": "lark-doc",
                "path": "SKILL.md",
                "content": "---\nname: lark-doc\n---\n# Synthetic embedded guidance\n",
                "guidance": "synthetic version-matched guidance",
            }
        )
        executable = bin_dir / "lark-cli"
        executable.write_text(
            "#!/bin/sh\n"
            "case \"$*\" in\n"
            f"  \"--version\") printf '%s\\n' 'lark-cli version {version}' ;;\n"
            f"  \"skills list\"|\"skills list --json\") printf '%s\\n' '{skills_payload}' ;;\n"
            f"  skills\\ read*) printf '%s\\n' '{read_payload}' ;;\n"
            "  \"update --check --json\") printf '%s\\n' "
            "'{\"ok\":true,\"action\":\"already_up_to_date\","
            "\"current_version\":\"1.0.69\",\"latest_version\":\"1.0.69\"}' ;;\n"
            "  *) printf '%s\\n' '{\"ok\":true}' ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
        return executable

    def synthetic_cli_result(self, command, *, update_payload=None, skill_read_payload=None, skills=None):
        tail = list(command[1:])
        stdout = json.dumps({"ok": True})
        if tail == ["--version"]:
            stdout = "lark-cli version 1.0.69"
        elif tail[:2] == ["skills", "list"]:
            skill_names = sorted(skills or OFFICIAL_LARK_SKILLS)
            stdout = json.dumps(
                {
                    "ok": True,
                    "skills": [{"name": name, "version": "1.0.0"} for name in skill_names],
                    "count": len(skill_names),
                }
            )
        elif tail[:3] == ["skills", "read", "lark-doc"]:
            payload = skill_read_payload
            if payload is None:
                payload = {
                    "skill": "lark-doc",
                    "path": "SKILL.md",
                    "content": "---\nname: lark-doc\n---\n# Synthetic embedded guidance\n",
                    "guidance": "synthetic version-matched guidance",
                }
            stdout = payload if isinstance(payload, str) else json.dumps(payload)
        elif tail == ["update", "--check", "--json"]:
            payload = update_payload or {
                "ok": True,
                "action": "already_up_to_date",
                "current_version": "1.0.69",
                "latest_version": "1.0.69",
            }
            stdout = payload if isinstance(payload, str) else json.dumps(payload)
        return {
            "command": command,
            "ok": True,
            "exit_code": 0,
            "stdout": stdout,
            "stderr": "",
        }

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

    def test_doctor_inventories_every_reachable_cli_and_warns_on_version_drift(self):
        root = self.make_repo()
        first = self.write_fake_lark_cli(root / "first-bin", version="1.0.69")
        second = self.write_fake_lark_cli(root / "second-bin", version="1.0.68")

        with mock.patch.dict(os.environ, {"PATH": os.pathsep.join([str(first.parent), str(second.parent)])}):
            result = lark_feishu_ops_doctor.check_lark_cli(
                skip_update_check=True,
                offline=True,
            )

        serialized = json.dumps(result, sort_keys=True)
        with self.subTest("first executable is reported"):
            self.assertIn(str(first), serialized)
        with self.subTest("second executable is reported"):
            self.assertIn(str(second), serialized)
        with self.subTest("canonical executable is explicit"):
            self.assertIn("canonical", serialized.lower())
        with self.subTest("installation owner is explicit"):
            self.assertIn("owner", serialized.lower())
        with self.subTest("version divergence is not a pass"):
            self.assertEqual("WARN", result["status"])

    def test_doctor_reports_canonical_executable_when_reachable_versions_align(self):
        root = self.make_repo()
        first = self.write_fake_lark_cli(root / "first-bin", version="1.0.69")
        second = self.write_fake_lark_cli(root / "second-bin", version="1.0.69")

        with mock.patch.dict(os.environ, {"PATH": os.pathsep.join([str(first.parent), str(second.parent)])}):
            result = lark_feishu_ops_doctor.check_lark_cli(
                skip_update_check=True,
                offline=True,
            )

        serialized = json.dumps(result, sort_keys=True)
        self.assertEqual("PASS", result["status"])
        self.assertIn(str(first), serialized)
        self.assertIn(str(second), serialized)
        self.assertIn("canonical", serialized.lower())

    def test_update_action_uses_canonical_absolute_executable(self):
        root = self.make_repo()
        executable = self.write_fake_lark_cli(root / "bin", version="1.0.68")
        update_payload = {
            "ok": True,
            "action": "update_available",
            "current_version": "1.0.68",
            "latest_version": "1.0.69",
        }

        with (
            mock.patch.dict(os.environ, {"PATH": str(executable.parent)}),
            mock.patch.object(
                lark_feishu_ops_doctor,
                "run_command",
                side_effect=lambda command, timeout=30: self.synthetic_cli_result(
                    command,
                    update_payload=update_payload,
                ),
            ),
        ):
            result = lark_feishu_ops_doctor.check_lark_cli(
                skip_update_check=False,
                offline=False,
                update_check_policy="always",
                cache_path=root / "update-check.json",
            )

        self.assertEqual(str(executable), result["update_action"]["command"][0])

    def test_valid_non_enveloped_skill_read_is_reported_as_success(self):
        root = self.make_repo()
        executable = self.write_fake_lark_cli(root / "bin")

        with (
            mock.patch.dict(os.environ, {"PATH": str(executable.parent)}),
            mock.patch.object(
                lark_feishu_ops_doctor,
                "run_command",
                side_effect=lambda command, timeout=30: self.synthetic_cli_result(command),
            ),
        ):
            result = lark_feishu_ops_doctor.check_lark_cli(
                skip_update_check=True,
                offline=True,
            )

        serialized = json.dumps(result, sort_keys=True)
        self.assertNotEqual("FAIL", result["status"])
        self.assertIn("lark-doc", serialized)
        self.assertIn("SKILL.md", serialized)

    def test_skill_read_missing_required_fields_fails_closed(self):
        root = self.make_repo()
        executable = self.write_fake_lark_cli(root / "bin")

        with (
            mock.patch.dict(os.environ, {"PATH": str(executable.parent)}),
            mock.patch.object(
                lark_feishu_ops_doctor,
                "run_command",
                side_effect=lambda command, timeout=30: self.synthetic_cli_result(
                    command,
                    skill_read_payload={"skill": "lark-doc"},
                ),
            ),
        ):
            result = lark_feishu_ops_doctor.check_lark_cli(
                skip_update_check=True,
                offline=True,
            )

        self.assertIn(result["status"], {"WARN", "FAIL"})
        diagnostics = json.dumps(result).lower()
        self.assertTrue(
            any(marker in diagnostics for marker in ("required", "missing", "content", "path", "schema"))
        )

    def test_enveloped_ok_false_update_check_fails_closed(self):
        root = self.make_repo()
        executable = self.write_fake_lark_cli(root / "bin")
        update_payload = {
            "ok": False,
            "action": "already_up_to_date",
            "error": "synthetic update failure",
        }

        with (
            mock.patch.dict(os.environ, {"PATH": str(executable.parent)}),
            mock.patch.object(
                lark_feishu_ops_doctor,
                "run_command",
                side_effect=lambda command, timeout=30: self.synthetic_cli_result(
                    command,
                    update_payload=update_payload,
                ),
            ),
        ):
            result = lark_feishu_ops_doctor.check_lark_cli(
                skip_update_check=False,
                offline=False,
                update_check_policy="always",
                cache_path=root / "update-check.json",
            )

        self.assertIn(result["status"], {"WARN", "FAIL"})
        self.assertFalse(result["update_check"]["ok"])

    def test_required_json_commands_reject_non_json_output(self):
        root = self.make_repo()
        executable = self.write_fake_lark_cli(root / "bin")

        def fake_run(command, timeout=30):
            if list(command[1:])[:2] == ["skills", "list"]:
                return {
                    "command": command,
                    "ok": True,
                    "exit_code": 0,
                    "stdout": "synthetic non-json output",
                    "stderr": "",
                }
            return self.synthetic_cli_result(command)

        with (
            mock.patch.dict(os.environ, {"PATH": str(executable.parent)}),
            mock.patch.object(lark_feishu_ops_doctor, "run_command", side_effect=fake_run),
        ):
            result = lark_feishu_ops_doctor.check_lark_cli(
                skip_update_check=True,
                offline=True,
            )

        self.assertIn(result["status"], {"WARN", "FAIL"})
        self.assertIn("json", json.dumps(result).lower())

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

    def test_daily_update_cache_is_refreshed_after_cli_version_changes(self):
        commands = []
        cache_path = self.make_repo() / "update-check.json"
        cache_path.write_text(
            json.dumps(
                {
                    "checked_local_date": lark_feishu_ops_doctor.local_date(),
                    "checked_at": "2026-07-15T09:00:00+08:00",
                    "action": "update_available",
                    "current_version": "1.0.63",
                    "latest_version": "1.0.69",
                    "ok": True,
                    "payload": {
                        "action": "update_available",
                        "current_version": "1.0.63",
                        "latest_version": "1.0.69",
                        "ok": True,
                    },
                }
            ),
            encoding="utf-8",
        )

        def fake_run_command(command, timeout=30):
            commands.append(command)
            result = self.synthetic_cli_result(command)
            if command[-3:] == ["update", "--check", "--json"]:
                result["stdout"] = json.dumps(
                    {
                        "action": "already_up_to_date",
                        "current_version": "1.0.69",
                        "latest_version": "1.0.69",
                        "ok": True,
                    }
                )
            return result

        with (
            mock.patch.object(
                lark_feishu_ops_doctor.shutil,
                "which",
                return_value="/usr/local/bin/lark-cli",
            ),
            mock.patch.object(
                lark_feishu_ops_doctor,
                "run_command",
                side_effect=fake_run_command,
            ),
        ):
            result = lark_feishu_ops_doctor.check_lark_cli(
                skip_update_check=False,
                offline=False,
                cache_path=cache_path,
            )

        self.assertIn(
            ["lark-cli", "update", "--check", "--json"],
            commands,
        )
        self.assertFalse(result["update_check"].get("cached", False))
        self.assertIsNone(result["update_action"])
        self.assertEqual("PASS", result["status"])

    def test_daily_update_cache_without_current_version_is_refreshed(self):
        commands = []
        cache_path = self.make_repo() / "update-check.json"
        cache_path.write_text(
            json.dumps(
                {
                    "checked_local_date": lark_feishu_ops_doctor.local_date(),
                    "checked_at": "2026-07-15T09:00:00+08:00",
                    "action": "already_up_to_date",
                    "ok": True,
                    "payload": {"action": "already_up_to_date", "ok": True},
                }
            ),
            encoding="utf-8",
        )

        def fake_run_command(command, timeout=30):
            commands.append(command)
            return self.synthetic_cli_result(command)

        with (
            mock.patch.object(
                lark_feishu_ops_doctor.shutil,
                "which",
                return_value="/usr/local/bin/lark-cli",
            ),
            mock.patch.object(
                lark_feishu_ops_doctor,
                "run_command",
                side_effect=fake_run_command,
            ),
        ):
            result = lark_feishu_ops_doctor.check_lark_cli(
                skip_update_check=False,
                offline=False,
                cache_path=cache_path,
            )

        self.assertIn(["lark-cli", "update", "--check", "--json"], commands)
        self.assertFalse(result["update_check"].get("cached", False))
        self.assertEqual("PASS", result["status"])

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

    def test_skills_out_of_sync_returns_confirmation_action_without_binary_update(self):
        cache_path = self.make_repo() / "update-check.json"

        def fake_run_command(command, timeout=30):
            stdout = ""
            if command == ["lark-cli", "--version"]:
                stdout = "lark-cli version 1.0.60"
            elif command == ["lark-cli", "update", "--check", "--json"]:
                stdout = json.dumps(
                    {
                        "action": "already_up_to_date",
                        "ok": True,
                        "current_version": "1.0.60",
                        "latest_version": "1.0.60",
                        "skills_status": {
                            "current": "1.0.56",
                            "target": "1.0.60",
                            "in_sync": False,
                            "official": 27,
                            "updated": 1,
                            "skipped_deleted": ["lark-doc", "lark-sheets"],
                        },
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
        self.assertIsNone(result["update_action"])
        self.assertTrue(result["skills_sync_action"]["requires_confirmation"])
        self.assertEqual(["lark-cli", "update", "--json"], result["skills_sync_action"]["command"])
        self.assertEqual("1.0.56", result["skills_sync_action"]["current_version"])
        self.assertEqual("1.0.60", result["skills_sync_action"]["target_version"])
        self.assertEqual(["lark-doc", "lark-sheets"], result["skills_sync_action"]["skipped_deleted"])
        self.assertTrue(
            any("official Lark skill guidance" in item for item in result["recommendations"])
        )

    def test_global_audit_recognizes_well_known_and_repository_official_sources(self):
        lock_path = self.write_skill_lock(
            {
                "skills": {
                    "lark-doc": {
                        "source": "open.feishu.cn",
                        "sourceType": "well-known",
                        "sourceUrl": "https://open.feishu.cn/.well-known/skills/lark-doc/SKILL.md",
                    },
                    "lark-sheets": {
                        "source": "larksuite/cli",
                        "sourceType": "github",
                        "sourceUrl": "https://github.com/larksuite/cli/tree/main/skills/lark-sheets",
                    },
                }
            }
        )
        listing = {
            "status": "PASS",
            "npx_path": "/synthetic/bin/npx",
            "skills": [
                {
                    "name": "lark-doc",
                    "path": "/synthetic/.agents/skills/lark-doc",
                    "agents": ["Codex"],
                },
                {
                    "name": "lark-sheets",
                    "path": "/synthetic/.agents/skills/lark-sheets",
                    "agents": ["Codex"],
                },
            ],
            "error": None,
        }

        with (
            mock.patch.object(lark_feishu_ops_doctor, "list_global_skills", return_value=listing),
            mock.patch.object(lark_feishu_ops_doctor, "SKILL_LOCK", lock_path),
        ):
            result = lark_feishu_ops_doctor.audit_global_lark_skills()

        official_names = {item["name"] for item in result["official_global_lark_skills"]}
        effective_names = {item["name"] for item in result["codex_effective_official_lark_skills"]}
        self.assertEqual({"lark-doc", "lark-sheets"}, official_names)
        self.assertEqual({"lark-doc", "lark-sheets"}, effective_names)
        self.assertIn("open.feishu.cn", json.dumps(result))
        self.assertIn("larksuite/cli", json.dumps(result))

    def test_global_audit_reports_unverified_exposure_separately(self):
        lock_path = self.write_skill_lock(
            {
                "skills": {
                    "lark-unknown": {
                        "source": "open.feishu.cn",
                        "sourceType": "well-known",
                        "sourceUrl": "https://open.feishu.cn/.well-known/skills/lark-doc/SKILL.md",
                    }
                }
            }
        )
        listing = {
            "status": "PASS",
            "npx_path": "/synthetic/bin/npx",
            "skills": [
                {
                    "name": "lark-unknown",
                    "path": "/synthetic/.agents/skills/lark-unknown",
                    "agents": ["Codex"],
                }
            ],
            "error": None,
        }

        with (
            mock.patch.object(lark_feishu_ops_doctor, "list_global_skills", return_value=listing),
            mock.patch.object(lark_feishu_ops_doctor, "SKILL_LOCK", lock_path),
        ):
            result = lark_feishu_ops_doctor.audit_global_lark_skills()

        self.assertIn("unverified_global_lark_skills", result)
        self.assertEqual(
            ["lark-unknown"],
            [item["name"] for item in result["unverified_global_lark_skills"]],
        )
        self.assertNotIn(
            "lark-unknown",
            {item["name"] for item in result["official_global_lark_skills"]},
        )

    def test_doctor_accounts_for_all_current_embedded_skills(self):
        root = self.make_repo()
        executable = self.write_fake_lark_cli(root / "bin", skills=OFFICIAL_LARK_SKILLS)

        with (
            mock.patch.dict(os.environ, {"PATH": str(executable.parent)}),
            mock.patch.object(
                lark_feishu_ops_doctor,
                "run_command",
                side_effect=lambda command, timeout=30: self.synthetic_cli_result(
                    command,
                    skills=OFFICIAL_LARK_SKILLS,
                ),
            ),
        ):
            result = lark_feishu_ops_doctor.check_lark_cli(
                skip_update_check=True,
                offline=True,
            )

        reported = collect_lark_skill_names(result)
        self.assertEqual(set(), OFFICIAL_LARK_SKILLS - reported)

    def test_doctor_reports_future_embedded_skill_as_unmapped(self):
        root = self.make_repo()
        skill_names = set(OFFICIAL_LARK_SKILLS) | {"lark-future-domain"}
        executable = self.write_fake_lark_cli(root / "bin", skills=skill_names)

        with (
            mock.patch.dict(os.environ, {"PATH": str(executable.parent)}),
            mock.patch.object(
                lark_feishu_ops_doctor,
                "run_command",
                side_effect=lambda command, timeout=30: self.synthetic_cli_result(
                    command,
                    skills=skill_names,
                ),
            ),
        ):
            result = lark_feishu_ops_doctor.check_lark_cli(
                skip_update_check=True,
                offline=True,
            )

        serialized = json.dumps(result, sort_keys=True).lower()
        self.assertEqual("WARN", result["status"])
        self.assertIn("lark-future-domain", serialized)
        self.assertIn("unmapped", serialized)

    def test_domain_readiness_keeps_event_separate_from_calendar(self):
        root = self.make_repo()
        executable = self.write_fake_lark_cli(root / "bin", skills=OFFICIAL_LARK_SKILLS)

        with (
            mock.patch.dict(os.environ, {"PATH": str(executable.parent)}),
            mock.patch.object(
                lark_feishu_ops_doctor,
                "run_command",
                side_effect=lambda command, timeout=30: self.synthetic_cli_result(
                    command,
                    skills=OFFICIAL_LARK_SKILLS,
                ),
            ),
        ):
            result = lark_feishu_ops_doctor.check_lark_cli(
                skip_update_check=True,
                offline=True,
            )

        event_route = find_first_key(result, "event")
        calendar_route = find_first_key(result, "calendar")
        self.assertIsNotNone(event_route)
        self.assertIn("lark-event", collect_lark_skill_names(event_route))
        self.assertNotIn("lark-event", collect_lark_skill_names(calendar_route))

    def test_missing_npx_is_optional_for_normal_runtime_readiness(self):
        args = SimpleNamespace(
            skip_update_check=True,
            offline=True,
            update_check_policy="never",
            force_update_check=False,
            update_cache_path=None,
            repo=None,
            apply_codex_global_unload=False,
            strict=False,
        )
        healthy_cli = {
            "status": "PASS",
            "canonical_executable": "/synthetic/bin/lark-cli",
            "embedded_skills": {"status": "PASS", "count": 27},
            "recommendations": [],
        }
        npx_unavailable = {
            "status": "WARN",
            "npx_path": None,
            "raw": None,
            "skills": [],
            "error": "`npx` not found; optional installer/global audit unavailable.",
        }

        with (
            mock.patch.object(lark_feishu_ops_doctor, "check_lark_cli", return_value=healthy_cli),
            mock.patch.object(lark_feishu_ops_doctor, "list_global_skills", return_value=npx_unavailable),
        ):
            result = lark_feishu_ops_doctor.build_report(args)

        self.assertEqual("PASS", result["status"])
        self.assertIn("npx", json.dumps(result).lower())

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
        self.assertIn(".agents/skills", result["project_scattered_lark_skills"][0]["path"])

    def test_project_lark_skill_audit_accepts_dedicated_lark_feishu_ops_skill(self):
        repo = self.make_repo()
        self.write_project_skill(repo, "lark-feishu-ops")

        result = lark_feishu_ops_doctor.audit_project_lark_skills(repo)

        self.assertEqual("PASS", result["status"])
        self.assertEqual(["lark-feishu-ops"], [item["name"] for item in result["project_lark_feishu_ops"]])
        self.assertEqual([], result["project_scattered_lark_skills"])

    def test_project_audit_walks_from_working_directory_to_repo_root(self):
        repo = self.make_repo()
        (repo / ".git").mkdir()
        working_directory = repo / "packages" / "feature"
        working_directory.mkdir(parents=True)
        self.write_project_skill(repo, "lark-doc")

        result = lark_feishu_ops_doctor.audit_project_lark_skills(working_directory)

        self.assertEqual("WARN", result["status"])
        self.assertEqual(
            ["lark-doc"],
            [item["name"] for item in result["project_scattered_lark_skills"]],
        )
        self.assertIn(str(repo / ".agents" / "skills"), json.dumps(result))

    def test_project_audit_reports_legacy_codex_skills_separately(self):
        repo = self.make_repo()
        self.write_project_skill(repo, "lark-doc", root=".codex/skills")

        result = lark_feishu_ops_doctor.audit_project_lark_skills(repo)

        self.assertEqual([], result["project_scattered_lark_skills"])
        self.assertIn("legacy_project_lark_skills", result)
        self.assertEqual(
            ["lark-doc"],
            [item["name"] for item in result["legacy_project_lark_skills"]],
        )
        self.assertIn("legacy", json.dumps(result).lower())

    def test_project_audit_reports_symlink_without_following_escape(self):
        repo = self.make_repo()
        external = self.make_repo()
        external_skill = self.write_project_skill(external, "lark-doc")
        skills_root = repo / ".agents" / "skills"
        skills_root.mkdir(parents=True)
        (skills_root / "lark-doc").symlink_to(external_skill, target_is_directory=True)

        result = lark_feishu_ops_doctor.audit_project_lark_skills(repo)

        self.assertEqual([], result["project_scattered_lark_skills"])
        self.assertIn("unsafe_project_lark_skills", result)
        self.assertEqual(
            ["lark-doc"],
            [item["name"] for item in result["unsafe_project_lark_skills"]],
        )
        self.assertIn("symlink", json.dumps(result).lower())


if __name__ == "__main__":
    unittest.main()
