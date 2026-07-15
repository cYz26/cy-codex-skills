import copy
import json
import os
import stat
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import lark_feishu_ops_agent_context as agent_context


class LarkFeishuAgentContextTests(unittest.TestCase):
    def make_temp_dir(self, prefix):
        temporary = tempfile.TemporaryDirectory(prefix=prefix)
        self.addCleanup(temporary.cleanup)
        return Path(temporary.name)

    def make_repo(self):
        return self.make_temp_dir("lark-agent-context-test-")

    def make_fake_lark_cli(self, skill_names):
        root = self.make_temp_dir("lark-agent-context-cli-")
        executable = root / "lark-cli"
        skills = [
            {
                "name": name,
                "description": f"Synthetic embedded guidance for {name}.",
                "version": "9.9.9-test",
            }
            for name in skill_names
        ]
        executable.write_text(
            "#!/usr/bin/env python3\n"
            "import json\n"
            "import sys\n"
            f"skills = {skills!r}\n"
            "args = sys.argv[1:]\n"
            "if args == ['--version']:\n"
            "    print('lark-cli version 9.9.9-test')\n"
            "    raise SystemExit(0)\n"
            "if args[:2] == ['skills', 'list']:\n"
            "    print(json.dumps({'ok': True, 'skills': skills, 'count': len(skills)}))\n"
            "    raise SystemExit(0)\n"
            "if args[:2] == ['skills', 'read'] and len(args) >= 3:\n"
            "    if args[2] not in {item['name'] for item in skills}:\n"
            "        print(json.dumps({'ok': False, 'error': 'missing synthetic skill'}))\n"
            "        raise SystemExit(2)\n"
            "    print('# synthetic embedded skill\\n')\n"
            "    raise SystemExit(0)\n"
            "print(json.dumps({'ok': False, 'error': 'unsupported synthetic command', 'args': args}))\n"
            "raise SystemExit(2)\n",
            encoding="utf-8",
        )
        executable.chmod(0o755)
        return executable

    def make_request(
        self,
        *,
        action="docs.fetch",
        identity="user",
        profile="default",
        hints=None,
        cache_policy=None,
    ):
        dispatch_hints = {
            "identity": identity,
            "profile": profile,
            "direct_allowed": True,
            "read_only": True,
            "bounded": True,
            "single_domain": True,
            "cross_domain": False,
            "raw_openapi": action.startswith("openapi."),
            "large_or_paginated": False,
            "requires_auth_profile_change": False,
            "explicit_subagent": False,
        }
        if hints:
            dispatch_hints.update(hints)

        request = {
            "request_id": f"req-{action.replace('.', '-')}",
            "action": action,
            "goal": "Return targeted synthetic evidence for the parent answer.",
            "intent": "Exercise the public agent-context contract.",
            "question": "Does the synthetic document cover the requested topic?",
            "target": {"doc_token": "doc-synthetic-123"},
            "handoff_context": {
                "user_goal": "Evaluate a synthetic design document.",
                "parent_context": ["Only bounded synthetic context is required."],
                "known_resources": [
                    {"type": "doc", "id": "doc-synthetic-123", "revision": "7"}
                ],
                "prior_evidence_pack": {},
                "freshness": {
                    "known_revision_id": "7",
                    "known_timestamp": "2026-07-15T01:00:00Z",
                    "known_source": "lark_cli",
                    "require_refetch": False,
                },
                "non_goals": ["Do not expand to other synthetic resources."],
            },
            "constraints": ["synthetic-only"],
            "dispatch_hints": dispatch_hints,
            "expected_output": "evidence_pack",
            "success_criteria": ["Return bounded metadata."],
            "stop_conditions": ["Stop after the requested synthetic read."],
            "return_format": "json",
        }
        if cache_policy is not None:
            request["cache_policy"] = cache_policy
        return request

    def make_result(self, *, status="PASS", state="complete", ttl_seconds=86400):
        return {
            "status": status,
            "action": "docs.fetch",
            "identity": "user",
            "commands_or_tools_used": [
                "lark-cli docs fetch --client-secret synthetic-cli-secret"
            ],
            "targets": {"doc_token": "doc-synthetic-123"},
            "progress": {"last_signal": "synthetic revision 7 fetched", "state": state},
            "result": {
                "evidence_pack": {
                    "question": "Does the synthetic document cover the requested topic?",
                    "document_content": "synthetic-private-document-body",
                    "table_rows": [{"private_cell": "synthetic-private-table-cell"}],
                    "mail_body": "synthetic-private-mail-body",
                    "contact_data": {"email": "synthetic-person@example.invalid"},
                    "raw_evidence": "synthetic-private-raw-evidence",
                },
                "next_resources": [{"type": "sheet", "id": "sheet-synthetic-456"}],
            },
            "side_effects": [],
            "validation": {"read_back": True},
            "artifacts": [],
            "blockers": [],
            "residual_risk": ["Synthetic embedded sheet was not expanded."],
            "context_cache_update": {
                "resource_refs": [
                    {
                        "type": "doc",
                        "id": "doc-synthetic-123",
                        "revision": "7",
                        "access_token": "synthetic-access-token",
                    }
                ],
                "resource_map": {
                    "doc-synthetic-123": {"title": "Synthetic private title"}
                },
                "known_command_shapes": [
                    "lark-cli docs fetch --authorization synthetic-command-secret"
                ],
                "missing_evidence": ["Synthetic private missing-evidence detail."],
                "freshness": {
                    "known_revision_id": "7",
                    "observed_at": "2026-07-15T01:00:00Z",
                    "source": "lark_cli",
                    "ttl_seconds": ttl_seconds,
                },
                "provenance": {
                    "source_type": "lark_cli",
                    "source": "docs.fetch",
                    "observed_at": "2026-07-15T01:00:00Z",
                    "raw_content": "synthetic-private-provenance-body",
                },
            },
        }

    def write_json(self, path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def run_prepare(self, repo, request, *, fake_cli, now=None):
        request_path = repo / "prepare-request.json"
        self.write_json(request_path, request)
        environment = {
            "PATH": f"{fake_cli.parent}{os.pathsep}{os.environ.get('PATH', '')}",
            "LARK_CLI_PATH": str(fake_cli),
        }
        with mock.patch.dict(os.environ, environment):
            exit_code, payload = agent_context.run_cli(
                ["prepare", "--repo", str(repo), "--request-json", str(request_path), "--json"]
            )
        self.assertEqual(0, exit_code, payload)
        return payload

    def run_record_result(self, repo, request, result, *, fake_cli, agent_id=None):
        request_path = repo / "record-request.json"
        result_path = repo / "record-result.json"
        self.write_json(request_path, request)
        self.write_json(result_path, result)
        argv = [
            "record-result",
            "--repo",
            str(repo),
            "--request-json",
            str(request_path),
            "--result-json",
            str(result_path),
            "--json",
        ]
        if agent_id:
            argv.extend(["--agent-id", agent_id])
        environment = {
            "PATH": f"{fake_cli.parent}{os.pathsep}{os.environ.get('PATH', '')}",
            "LARK_CLI_PATH": str(fake_cli),
        }
        with mock.patch.dict(os.environ, environment):
            exit_code, payload = agent_context.run_cli(argv)
        self.assertEqual(0, exit_code, payload)
        return payload

    @classmethod
    def values_for_key(cls, payload, key):
        values = []
        if isinstance(payload, dict):
            for item_key, item_value in payload.items():
                if item_key == key:
                    values.append(item_value)
                values.extend(cls.values_for_key(item_value, key))
        elif isinstance(payload, list):
            for item in payload:
                values.extend(cls.values_for_key(item, key))
        return values

    @classmethod
    def all_keys(cls, payload):
        keys = set()
        if isinstance(payload, dict):
            for key, value in payload.items():
                keys.add(key)
                keys.update(cls.all_keys(value))
        elif isinstance(payload, list):
            for item in payload:
                keys.update(cls.all_keys(item))
        return keys

    @classmethod
    def all_strings(cls, payload):
        strings = []
        if isinstance(payload, str):
            strings.append(payload)
        elif isinstance(payload, dict):
            for key, value in payload.items():
                strings.append(str(key))
                strings.extend(cls.all_strings(value))
        elif isinstance(payload, list):
            for item in payload:
                strings.extend(cls.all_strings(item))
        return strings

    def snapshot_files(self, repo):
        return sorted((agent_context.snapshots_dir(repo)).glob("*.json"))

    def test_ac_01_explicit_bounded_read_remains_direct_eligible(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])

        report = self.run_prepare(repo, self.make_request(), fake_cli=fake_cli)

        self.assertEqual("read", report["request"]["risk_class"])
        self.assertEqual("direct", report["dispatch"]["decision"])

    def test_ac_02_unknown_action_fails_closed_despite_read_hints(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        request = self.make_request(
            action="docs.synthetic-unknown-operation",
            hints={"direct_allowed": True, "read_only": True},
        )

        report = self.run_prepare(repo, request, fake_cli=fake_cli)
        normalized = report["request"]

        self.assertEqual("unknown", normalized["risk_class"])
        self.assertFalse(normalized["dispatch_hints"]["direct_allowed"])
        self.assertFalse(normalized["dispatch_hints"]["read_only"])
        self.assertEqual("fresh_subagent", report["dispatch"]["decision"])
        rejected_hints = self.values_for_key(normalized, "rejected_hints")
        self.assertTrue(rejected_hints, "conflicting caller hints must be reported")

    def test_ac_03_raw_and_mutating_actions_are_never_direct(self):
        fake_cli = self.make_fake_lark_cli(["lark-doc", "lark-approval", "lark-openapi-explorer"])
        for action in (
            "openapi.call",
            "approval.approve",
            "drive.upload",
            "mail.reply",
            "profile.switch",
        ):
            with self.subTest(action=action):
                repo = self.make_repo()
                request = self.make_request(
                    action=action,
                    hints={"direct_allowed": True, "read_only": True, "raw_openapi": action.startswith("openapi.")},
                )
                report = self.run_prepare(repo, request, fake_cli=fake_cli)

                self.assertIn(report["request"]["risk_class"], {"write", "high-risk-write"})
                self.assertFalse(report["request"]["dispatch_hints"]["direct_allowed"])
                self.assertNotEqual("direct", report["dispatch"]["decision"])

    def test_ac_04_known_write_hints_are_rejected_not_preserved(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-im"])
        request = self.make_request(
            action="im.send",
            hints={"direct_allowed": True, "read_only": True, "side_effects": False},
        )

        report = self.run_prepare(repo, request, fake_cli=fake_cli)
        normalized = report["request"]

        self.assertIn(normalized["risk_class"], {"write", "high-risk-write"})
        self.assertFalse(normalized["dispatch_hints"]["direct_allowed"])
        self.assertFalse(normalized["dispatch_hints"]["read_only"])
        self.assertTrue(self.values_for_key(normalized, "rejected_hints"))

    def test_ac_05_declared_side_effect_makes_explicit_read_non_direct(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        request = self.make_request(
            action="docs.fetch",
            hints={"side_effects": True},
        )

        report = self.run_prepare(repo, request, fake_cli=fake_cli)
        normalized = report["request"]

        self.assertEqual("write", normalized["risk_class"])
        self.assertTrue(normalized["dispatch_hints"]["side_effects"])
        self.assertFalse(normalized["dispatch_hints"]["direct_allowed"])
        self.assertFalse(normalized["dispatch_hints"]["read_only"])
        self.assertNotEqual("direct", report["dispatch"]["decision"])

    def test_ac_06_normalized_request_preserves_ephemeral_operation_capsule(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        request = self.make_request(hints={"explicit_subagent": True})
        request["content"] = {"markdown": "Synthetic operation body for FeishuOps."}
        request["evidence_request"] = {
            "mode": "evidence_pack",
            "focus": ["synthetic decision"],
        }
        request["handoff_context"]["prior_evidence_pack"] = {
            "coverage": ["synthetic section"]
        }
        request["authorization"] = "Bearer synthetic-ephemeral-auth-secret"

        report = self.run_prepare(repo, request, fake_cli=fake_cli)
        normalized = report["request"]
        serialized = json.dumps(normalized, sort_keys=True)

        self.assertEqual(request["question"], normalized["question"])
        self.assertEqual(request["content"], normalized["content"])
        self.assertEqual(request["evidence_request"], normalized["evidence_request"])
        self.assertEqual(request["constraints"], normalized["constraints"])
        self.assertEqual(request["success_criteria"], normalized["success_criteria"])
        self.assertEqual(request["stop_conditions"], normalized["stop_conditions"])
        self.assertEqual(
            request["handoff_context"]["user_goal"],
            normalized["handoff_context"]["user_goal"],
        )
        self.assertEqual(
            request["handoff_context"]["parent_context"],
            normalized["handoff_context"]["parent_context"],
        )
        self.assertEqual(
            request["handoff_context"]["prior_evidence_pack"],
            normalized["handoff_context"]["prior_evidence_pack"],
        )
        self.assertEqual(
            request["handoff_context"]["non_goals"],
            normalized["handoff_context"]["non_goals"],
        )
        self.assertNotIn("synthetic-ephemeral-auth-secret", serialized)

    def test_ac_07_ephemeral_content_is_not_silently_truncated(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        request = self.make_request(
            action="docs.upsert",
            hints={"explicit_subagent": True},
        )
        request["content"] = {
            "markdown": "界" * 6000,
            "blocks": [f"synthetic-block-{index:03d}" for index in range(65)],
        }

        report = self.run_prepare(repo, request, fake_cli=fake_cli)

        self.assertEqual(request["content"], report["request"]["content"])
        self.assertEqual("write", report["request"]["risk_class"])
        self.assertNotEqual("direct", report["dispatch"]["decision"])

    def test_gd_01_guidance_uses_dynamic_embedded_skill_inventory(self):
        repo = self.make_repo()
        available_cli = self.make_fake_lark_cli(["lark-doc"])

        available_report = self.run_prepare(repo, self.make_request(), fake_cli=available_cli)
        sources = available_report["request"]["guidance_sources"]
        embedded = next(source for source in sources if source.get("name") == "lark-doc")
        argv = embedded.get("argv", embedded.get("command"))

        self.assertEqual("cli_embedded_skill", embedded["source_type"])
        self.assertEqual(["lark-cli", "skills", "read", "lark-doc"], argv)
        self.assertNotIn("path", embedded)
        self.assertNotIn("inject_as", embedded)

        missing_cli = self.make_fake_lark_cli([])
        missing_report = self.run_prepare(repo, self.make_request(), fake_cli=missing_cli)
        missing_sources = missing_report["request"]["guidance_sources"]
        self.assertFalse(
            any(
                source.get("source_type") == "cli_embedded_skill"
                and source.get("status") in {"available", "loaded"}
                for source in missing_sources
            )
        )
        self.assertTrue(
            any(source.get("source_type") in {"cli_help", "cli_schema"} for source in missing_sources)
        )

    def test_gd_02_arbitrary_guidance_path_is_rejected_without_reading(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        untrusted = repo / "untrusted-guidance.md"
        untrusted.write_text("synthetic-untrusted-guidance-secret", encoding="utf-8")
        request = self.make_request()
        request["guidance_sources"] = [
            {
                "source_type": "skill",
                "domain": "docs",
                "name": "lark-doc",
                "status": "available",
                "path": str(untrusted),
                "inject_as": "skill_file",
            }
        ]

        report = self.run_prepare(repo, request, fake_cli=fake_cli)
        serialized = json.dumps(report, sort_keys=True)

        self.assertNotIn(str(untrusted), serialized)
        self.assertNotIn("synthetic-untrusted-guidance-secret", serialized)
        self.assertNotIn("skill_file", serialized)
        self.assertTrue(self.values_for_key(report, "trust_boundary_warnings"))

    def test_gd_03_fresh_subagent_contract_requires_no_inherited_turns(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        request = self.make_request(hints={"explicit_subagent": True, "direct_allowed": False})

        report = self.run_prepare(repo, request, fake_cli=fake_cli)

        self.assertEqual("fresh_subagent", report["dispatch"]["decision"])
        self.assertIn("none", self.values_for_key(report["dispatch"], "fork_turns"))
        self.assertEqual("parent_agent_runtime", report["runtime_boundary"]["subagent_primitives"])

    def test_gd_07_current_cli_only_domains_use_typed_help_fallbacks(self):
        fake_cli = self.make_fake_lark_cli([])
        cases = {
            "application.inspect": "application",
            "config.inspect": "config",
            "doctor.inspect": "doctor",
            "mindnotes.inspect": "mindnotes",
            "profile.inspect": "profile",
            "schema.inspect": "schema",
            "skills.inspect": "skills",
            "update.inspect": "update",
            "whoami.inspect": "whoami",
        }
        for action, command in cases.items():
            with self.subTest(action=action):
                repo = self.make_repo()
                request = self.make_request(
                    action=action,
                    hints={"direct_allowed": False, "read_only": False},
                )
                report = self.run_prepare(repo, request, fake_cli=fake_cli)
                sources = report["request"]["guidance_sources"]

                self.assertNotEqual("read", report["request"]["risk_class"])
                self.assertIn(
                    ["lark-cli", command, "--help"],
                    [source.get("command") for source in sources],
                )
                self.assertEqual("fresh_subagent", report["dispatch"]["decision"])

    def test_gd_08_unknown_domain_returns_explicit_blocker_guidance(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli([])
        request = self.make_request(
            action="future-domain.inspect",
            hints={"direct_allowed": False, "read_only": False},
        )

        report = self.run_prepare(repo, request, fake_cli=fake_cli)
        sources = report["request"]["guidance_sources"]

        self.assertTrue(
            any(
                source.get("source_type") == "blocker"
                and source.get("status") == "blocked"
                and source.get("domain") == "future-domain"
                for source in sources
            ),
            sources,
        )

    def test_gd_04_active_reuse_is_only_a_runtime_confirmation_candidate(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        now = datetime.now(timezone.utc)
        environment = {
            "PATH": f"{fake_cli.parent}{os.pathsep}{os.environ.get('PATH', '')}",
            "LARK_CLI_PATH": str(fake_cli),
        }
        with mock.patch.dict(os.environ, environment):
            agent_context.record_active_agent(
                repo,
                agent_id="agent-synthetic-doc",
                request=self.make_request(),
                last_progress_at=now,
            )
        report = self.run_prepare(repo, self.make_request(), fake_cli=fake_cli)

        self.assertIn(report["dispatch"]["decision"], {"reuse_active", "reuse_active_candidate"})
        self.assertIn(True, self.values_for_key(report["dispatch"], "requires_runtime_confirmation"))
        self.assertIn(False, self.values_for_key(report["dispatch"], "registry_authoritative"))

    def test_gd_05_terminal_results_retire_active_registry_entries(self):
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        for status, state in (("PASS", "complete"), ("BLOCKED", "blocked"), ("FAILED", "failed")):
            with self.subTest(state=state):
                repo = self.make_repo()
                request = self.make_request()
                agent_context.record_active_agent(
                    repo,
                    agent_id=f"agent-{state}",
                    request=request,
                    last_progress_at=datetime.now(timezone.utc),
                )
                self.run_record_result(
                    repo,
                    request,
                    self.make_result(status=status, state=state),
                    fake_cli=fake_cli,
                    agent_id=f"agent-{state}",
                )

                active_ids = {
                    entry.get("agent_id")
                    for entry in agent_context.read_active_registry(repo).get("agents", [])
                    if entry.get("state") == "active"
                }
                self.assertNotIn(f"agent-{state}", active_ids)

    def test_gd_06_idle_active_metadata_is_pruned_before_dispatch(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        now = datetime.now(timezone.utc)
        agent_context.record_active_agent(
            repo,
            agent_id="agent-idle",
            request=self.make_request(),
            last_progress_at=now - timedelta(minutes=31),
        )

        report = agent_context.prepare_dispatch_report(repo, self.make_request(), now=now)
        active_ids = {
            entry.get("agent_id") for entry in agent_context.read_active_registry(repo).get("agents", [])
        }

        self.assertNotIn(report["dispatch"]["decision"], {"reuse_active", "reuse_active_candidate"})
        self.assertNotIn("agent-idle", active_ids)

    def test_ct_01_snapshot_is_metadata_only_and_reports_excluded_classes(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        request = self.make_request()
        request["authorization"] = "Bearer synthetic-request-secret"
        request["verification_url"] = "https://verify.example.invalid/synthetic-private-code"

        command_result = self.run_record_result(
            repo,
            request,
            self.make_result(),
            fake_cli=fake_cli,
        )
        files = self.snapshot_files(repo)

        self.assertEqual(1, len(files))
        snapshot_text = files[0].read_text(encoding="utf-8")
        snapshot = json.loads(snapshot_text)
        for secret in (
            "synthetic-request-secret",
            "synthetic-private-code",
            "synthetic-cli-secret",
            "synthetic-private-document-body",
            "synthetic-private-table-cell",
            "synthetic-private-mail-body",
            "synthetic-person@example.invalid",
            "synthetic-private-raw-evidence",
            "synthetic-access-token",
            "synthetic-command-secret",
            "synthetic-private-provenance-body",
        ):
            self.assertNotIn(secret, snapshot_text)

        forbidden_keys = {
            "request",
            "evidence_pack",
            "commands_or_tools_used",
            "resource_map",
            "known_command_shapes",
            "missing_evidence",
            "validation",
            "blockers",
            "residual_risk",
            "raw_content",
            "raw_evidence",
        }
        self.assertFalse(forbidden_keys.intersection(self.all_keys(snapshot)))

        excluded = set()
        for value in self.values_for_key(command_result, "excluded_content_classes"):
            if isinstance(value, list):
                excluded.update(str(item) for item in value)
        self.assertTrue(
            {
                "authentication_material",
                "cli_secret_arguments",
                "document_content",
                "table_rows",
                "mail_bodies",
                "contact_data",
                "raw_evidence",
            }.issubset(excluded)
        )

    def test_ct_02_snapshot_enforces_string_list_file_and_ttl_bounds(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        request = self.make_request()
        request["handoff_context"]["known_resources"] = [
            {
                "type": "doc",
                "id": f"doc-synthetic-{index:03d}",
                "revision": "界" * 300 if index == 0 else str(index),
            }
            for index in range(40)
        ]
        result = self.make_result(ttl_seconds=7 * 86400)
        result["result"]["evidence_pack"]["bulk"] = {
            f"field-{index}": "x" * 1000 for index in range(100)
        }

        self.run_record_result(repo, request, result, fake_cli=fake_cli)
        files = self.snapshot_files(repo)

        self.assertEqual(1, len(files))
        self.assertLessEqual(files[0].stat().st_size, 32 * 1024)
        snapshot = json.loads(files[0].read_text(encoding="utf-8"))
        self.assertLessEqual(len(snapshot.get("resource_refs", [])), 32)
        overlong = [value for value in self.all_strings(snapshot) if len(value.encode("utf-8")) > 256]
        self.assertEqual([], overlong)
        created_at = agent_context.parse_time(snapshot.get("created_at"))
        expires_at = agent_context.parse_time(snapshot.get("expires_at"))
        self.assertIsNotNone(created_at)
        self.assertIsNotNone(expires_at)
        self.assertLessEqual(expires_at - created_at, timedelta(hours=24))

    def test_ct_02b_freshness_and_provenance_values_are_typed_metadata(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        result = self.make_result()
        result["context_cache_update"]["freshness"].update(
            {
                "known_revision_id": "synthetic-freshness-secret",
                "observed_at": "Bearer synthetic-time-secret",
                "source": "Bearer synthetic-source-secret",
            }
        )
        result["context_cache_update"]["provenance"].update(
            {
                "source_type": "Bearer synthetic-provenance-secret",
                "observed_at": "Bearer synthetic-provenance-time-secret",
            }
        )

        report = self.run_record_result(
            repo,
            self.make_request(),
            result,
            fake_cli=fake_cli,
        )
        serialized = json.dumps(report, sort_keys=True)

        for secret in (
            "synthetic-freshness-secret",
            "synthetic-time-secret",
            "synthetic-source-secret",
            "synthetic-provenance-secret",
            "synthetic-provenance-time-secret",
        ):
            self.assertNotIn(secret, serialized)
        self.assertFalse(report["persisted"])
        self.assertEqual([], self.snapshot_files(repo))

    def test_ct_02c_missing_result_freshness_or_provenance_is_not_fabricated(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        result = self.make_result()
        result["context_cache_update"].pop("freshness")
        result["context_cache_update"].pop("provenance")

        report = self.run_record_result(
            repo,
            self.make_request(),
            result,
            fake_cli=fake_cli,
        )

        self.assertFalse(report["persisted"])
        self.assertEqual([], self.snapshot_files(repo))
        self.assertNotEqual(
            ["lark_cli"],
            report["result"]["provenance_classifications"],
        )

    def test_ct_02d_future_result_evidence_is_rejected_before_write(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        future = datetime.now(timezone.utc) + timedelta(days=2)
        result = self.make_result()
        result["context_cache_update"]["freshness"]["observed_at"] = (
            agent_context.isoformat(future)
        )
        result["context_cache_update"]["provenance"]["observed_at"] = (
            agent_context.isoformat(future)
        )

        report = self.run_record_result(
            repo,
            self.make_request(),
            result,
            fake_cli=fake_cli,
        )

        self.assertFalse(report["persisted"])
        self.assertEqual([], self.snapshot_files(repo))
        self.assertIn("future", report["snapshot"]["policy_reason"])

    def test_ct_02e_snapshot_total_byte_limit_returns_non_persisted_result(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        result = self.make_result()
        fields = (
            "type",
            "id",
            "revision",
            "revision_id",
            "sheet_id",
            "table_id",
            "chat_id",
            "message_id",
            "event_id",
            "meeting_id",
            "task_id",
            "approval_id",
        )
        result["context_cache_update"]["resource_refs"] = [
            {
                key: f"meta-{index:02d}-{key}-" + "x" * 190
                for key in fields
            }
            for index in range(32)
        ]

        report = self.run_record_result(
            repo,
            self.make_request(),
            result,
            fake_cli=fake_cli,
        )

        self.assertFalse(report["persisted"])
        self.assertEqual([], self.snapshot_files(repo))
        self.assertIn("32 KiB", report["snapshot"]["policy_reason"])

    def test_ct_03_registry_and_snapshot_files_are_owner_only_under_runtime_root(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        request = self.make_request()
        agent_context.record_active_agent(
            repo,
            agent_id="agent-mode-check",
            request=request,
            last_progress_at=datetime.now(timezone.utc),
        )
        self.run_record_result(repo, request, self.make_result(), fake_cli=fake_cli)

        root = agent_context.runtime_root(repo).resolve()
        state_files = sorted(root.rglob("*.json"))
        self.assertTrue(state_files)
        for path in state_files:
            with self.subTest(path=path):
                self.assertTrue(path.resolve().is_relative_to(root))
                self.assertEqual(0o600, stat.S_IMODE(path.stat().st_mode))

    def test_ct_04_snapshot_symlink_escape_is_rejected(self):
        repo = self.make_repo()
        outside = self.make_temp_dir("lark-agent-context-outside-")
        runtime = agent_context.runtime_root(repo)
        runtime.mkdir(parents=True, exist_ok=True)
        agent_context.snapshots_dir(repo).symlink_to(outside, target_is_directory=True)

        try:
            agent_context.write_context_snapshot(repo, self.make_request(), self.make_result())
        except (OSError, RuntimeError, ValueError):
            pass

        self.assertEqual(
            [],
            list(outside.iterdir()),
            "continuity writes must not follow a symlink outside the repo root",
        )

    def test_ct_03b_active_registry_write_and_read_strip_unknown_private_fields(self):
        repo = self.make_repo()
        now = datetime.now(timezone.utc)
        registry = {
            "schema_version": "2.0",
            "agents": [
                {
                    "schema_version": "2.0",
                    "agent_id": "agent-sanitized",
                    "request_id": "req-sanitized",
                    "action": "docs.fetch",
                    "domain": "docs",
                    "affinity_key": "docs:doc-synthetic-123",
                    "resource_refs": ["doc-synthetic-123"],
                    "identity": "user",
                    "profile": "default",
                    "risk_class": "read",
                    "state": "active",
                    "last_progress_at": agent_context.isoformat(now),
                    "token": "synthetic-active-token",
                    "request_body": "synthetic-active-private-body",
                }
            ],
        }

        agent_context.write_active_registry(repo, registry)
        path = agent_context.active_registry_path(repo)
        first_text = path.read_text(encoding="utf-8")
        self.assertNotIn("synthetic-active-token", first_text)
        self.assertNotIn("synthetic-active-private-body", first_text)

        injected = json.loads(first_text)
        injected["agents"][0]["authorization"] = "synthetic-read-path-secret"
        path.write_text(json.dumps(injected), encoding="utf-8")
        path.chmod(0o600)
        visible = agent_context.read_active_registry(repo)

        self.assertNotIn("synthetic-read-path-secret", json.dumps(visible, sort_keys=True))
        self.assertNotIn("authorization", path.read_text(encoding="utf-8"))

    def test_ct_03c_auth_markers_cannot_hide_in_permitted_metadata_fields(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        disguised_secret = "Bearer-SYNTHETIC-SECRET"
        request = self.make_request()
        request["request_id"] = disguised_secret
        request["target"] = {"doc_token": disguised_secret}
        request["handoff_context"]["known_resources"] = [
            {"type": "doc", "id": disguised_secret, "revision": "7"}
        ]
        result = self.make_result()
        result["status"] = disguised_secret
        result["progress"]["state"] = disguised_secret
        result["context_cache_update"]["resource_refs"] = [
            {"type": "doc", "id": disguised_secret, "revision": "7"}
        ]

        report = self.run_record_result(
            repo,
            request,
            result,
            fake_cli=fake_cli,
            agent_id=disguised_secret,
        )
        persisted_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in agent_context.runtime_root(repo).rglob("*.json")
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertNotIn(disguised_secret, persisted_text)
        self.assertNotIn(disguised_secret, serialized)
        self.assertFalse(report["persisted"])

    def test_ct_03d_active_registry_prunes_to_total_byte_budget(self):
        repo = self.make_repo()
        now = datetime.now(timezone.utc)
        agents = []
        for index in range(64):
            agents.append(
                {
                    "schema_version": "2.0",
                    "agent_id": f"agent-{index:02d}",
                    "request_id": f"request-{index:02d}",
                    "action": "docs.fetch",
                    "domain": "docs",
                    "affinity_key": f"docs:resource-{index:02d}",
                    "resource_refs": [
                        f"resource-{index:02d}-{item:02d}-" + "x" * 190
                        for item in range(32)
                    ],
                    "identity": "user",
                    "profile": "default",
                    "risk_class": "read",
                    "state": "active",
                    "last_progress_at": agent_context.isoformat(now),
                }
            )

        agent_context.write_active_registry(
            repo,
            {"schema_version": "2.0", "agents": agents},
        )
        path = agent_context.active_registry_path(repo)
        visible = agent_context.read_active_registry(repo)

        self.assertLessEqual(path.stat().st_size, 32 * 1024)
        self.assertGreater(len(visible["agents"]), 0)
        self.assertLess(len(visible["agents"]), 64)

    def test_ct_05_sensitive_domains_and_disabled_policy_do_not_persist(self):
        fake_cli = self.make_fake_lark_cli(
            ["lark-shared", "lark-contact", "lark-approval", "lark-mail", "lark-doc"]
        )
        cases = (
            ("auth.status", None),
            ("contact.search", "enabled"),
            ("approval.list", "enabled"),
            ("mail.search", "enabled"),
            ("profile.switch", "enabled"),
            ("docs.fetch", "disabled"),
        )
        for action, cache_policy in cases:
            with self.subTest(action=action, cache_policy=cache_policy):
                repo = self.make_repo()
                request = self.make_request(action=action, cache_policy=cache_policy)
                result = self.run_record_result(repo, request, self.make_result(), fake_cli=fake_cli)

                self.assertEqual([], self.snapshot_files(repo))
                self.assertIn(False, self.values_for_key(result, "persisted"))

    def test_ct_06_purge_command_removes_selected_continuity_metadata(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        self.run_record_result(repo, self.make_request(), self.make_result(), fake_cli=fake_cli)
        self.assertTrue(self.snapshot_files(repo))

        try:
            exit_code, payload = agent_context.run_cli(["purge", "--repo", str(repo), "--json"])
        except SystemExit as exc:
            self.fail(f"purge must be a public machine-readable command; argparse exited {exc.code}")

        self.assertEqual(0, exit_code, payload)
        self.assertEqual("PASS", payload["status"])
        self.assertEqual([], self.snapshot_files(repo))
        self.assertTrue(self.values_for_key(payload, "purged"))

    def test_ct_07_require_refetch_prevents_cached_reconstruction(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        self.run_record_result(repo, self.make_request(), self.make_result(), fake_cli=fake_cli)
        request = self.make_request()
        request["handoff_context"]["freshness"]["require_refetch"] = True

        report = self.run_prepare(repo, request, fake_cli=fake_cli)

        self.assertNotEqual("reconstruct_from_cache", report["dispatch"]["decision"])
        self.assertFalse(self.values_for_key(report["dispatch"], "reconstructed_request"))
        self.assertIn("require_refetch", json.dumps(report["dispatch"], sort_keys=True))

    def test_ct_07b_result_or_snapshot_require_refetch_is_never_reused(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        result = self.make_result()
        result["context_cache_update"]["freshness"]["require_refetch"] = True

        rejected_write = self.run_record_result(
            repo,
            self.make_request(),
            result,
            fake_cli=fake_cli,
        )
        self.assertFalse(rejected_write["persisted"])
        self.assertEqual([], self.snapshot_files(repo))

        self.run_record_result(
            repo,
            self.make_request(),
            self.make_result(),
            fake_cli=fake_cli,
        )
        snapshot_path = self.snapshot_files(repo)[0]
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot["freshness"]["require_refetch"] = True
        snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")

        report = self.run_prepare(repo, self.make_request(), fake_cli=fake_cli)
        serialized = json.dumps(report["dispatch"], sort_keys=True)
        self.assertNotEqual("reconstruct_from_cache", report["dispatch"]["decision"])
        self.assertIn("require_refetch", serialized)
        self.assertFalse(snapshot_path.exists())

    def test_ct_08_missing_expiry_or_provenance_is_not_reused_and_is_explained(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        self.run_record_result(repo, self.make_request(), self.make_result(), fake_cli=fake_cli)
        snapshot_path = self.snapshot_files(repo)[0]
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot.pop("expires_at", None)
        snapshot.pop("provenance", None)
        snapshot.pop("provenance_classifications", None)
        snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")

        report = self.run_prepare(repo, self.make_request(), fake_cli=fake_cli)
        serialized = json.dumps(report["dispatch"], sort_keys=True)

        self.assertNotEqual("reconstruct_from_cache", report["dispatch"]["decision"])
        self.assertTrue("expires_at" in serialized or "expiry" in serialized)

    def test_ct_08b_missing_freshness_is_pruned_and_not_reused(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        self.run_record_result(repo, self.make_request(), self.make_result(), fake_cli=fake_cli)
        snapshot_path = self.snapshot_files(repo)[0]
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot.pop("freshness", None)
        snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
        request = self.make_request(hints={"explicit_subagent": True})

        report = self.run_prepare(repo, request, fake_cli=fake_cli)
        serialized = json.dumps(report["dispatch"], sort_keys=True)

        self.assertNotEqual("reconstruct_from_cache", report["dispatch"]["decision"])
        self.assertIn("freshness", serialized)
        self.assertFalse(snapshot_path.exists())

    def test_ct_08c_current_request_revision_overrides_cached_revision(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        self.run_record_result(repo, self.make_request(), self.make_result(), fake_cli=fake_cli)
        request = self.make_request(hints={"explicit_subagent": True})
        request["handoff_context"]["freshness"]["known_revision_id"] = "8"

        report = self.run_prepare(repo, request, fake_cli=fake_cli)
        serialized = json.dumps(report["dispatch"], sort_keys=True)

        self.assertNotEqual("reconstruct_from_cache", report["dispatch"]["decision"])
        self.assertIn("revision", serialized)

    def test_ct_08d_current_v2_snapshot_with_unknown_fields_is_pruned(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        self.run_record_result(repo, self.make_request(), self.make_result(), fake_cli=fake_cli)
        snapshot_path = self.snapshot_files(repo)[0]
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot["token"] = "synthetic-current-v2-token"
        snapshot["provenance"]["raw_content"] = "synthetic-current-v2-private"
        snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")

        exit_code, payload = agent_context.run_cli(["list", "--repo", str(repo), "--json"])
        serialized = json.dumps(payload, sort_keys=True)

        self.assertEqual(0, exit_code, payload)
        self.assertFalse(snapshot_path.exists())
        self.assertNotIn("synthetic-current-v2-token", serialized)
        self.assertNotIn("synthetic-current-v2-private", serialized)

    def test_ct_08e_future_and_overlong_current_v2_snapshots_are_pruned(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        now = datetime.now(timezone.utc)
        self.run_record_result(repo, self.make_request(), self.make_result(), fake_cli=fake_cli)
        seed_path = self.snapshot_files(repo)[0]
        seed = json.loads(seed_path.read_text(encoding="utf-8"))
        seed_path.unlink()

        overlong = copy.deepcopy(seed)
        overlong["snapshot_id"] = "snapshot-overlong"
        overlong["created_at"] = agent_context.isoformat(now)
        overlong["expires_at"] = agent_context.isoformat(now + timedelta(hours=25))
        overlong_path = agent_context.snapshots_dir(repo) / "snapshot-overlong.json"
        overlong_path.write_text(json.dumps(overlong), encoding="utf-8")

        future = copy.deepcopy(seed)
        future_time = now + timedelta(days=2)
        future["snapshot_id"] = "snapshot-future"
        future["created_at"] = agent_context.isoformat(future_time)
        future["expires_at"] = agent_context.isoformat(future_time + timedelta(hours=1))
        future["freshness"]["observed_at"] = agent_context.isoformat(future_time)
        future["provenance"]["observed_at"] = agent_context.isoformat(future_time)
        future_path = agent_context.snapshots_dir(repo) / "snapshot-future.json"
        future_path.write_text(json.dumps(future), encoding="utf-8")

        exit_code, payload = agent_context.run_cli(["list", "--repo", str(repo), "--json"])
        serialized = json.dumps(payload, sort_keys=True).lower()

        self.assertEqual(0, exit_code, payload)
        self.assertFalse(overlong_path.exists())
        self.assertFalse(future_path.exists())
        self.assertIn("ttl", serialized)
        self.assertIn("future", serialized)

    def test_ct_09_invalid_expired_oversized_and_v1_state_is_pruned_without_exposure(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        directory = agent_context.snapshots_dir(repo)
        directory.mkdir(parents=True, exist_ok=True)
        malformed = directory / "malformed.json"
        oversized = directory / "oversized.json"
        expired = directory / "expired.json"
        legacy = directory / "legacy-v1.json"
        malformed.write_text("{not-json", encoding="utf-8")
        oversized.write_text(
            json.dumps(
                {
                    "schema_version": "2.0",
                    "snapshot_id": "oversized",
                    "padding": "oversized-private-value" * 4000,
                }
            ),
            encoding="utf-8",
        )
        expired.write_text(
            json.dumps(
                {
                    "schema_version": "2.0",
                    "snapshot_id": "expired",
                    "created_at": "2000-01-01T00:00:00Z",
                    "expires_at": "2000-01-02T00:00:00Z",
                    "private": "expired-private-value",
                }
            ),
            encoding="utf-8",
        )
        legacy.write_text(
            json.dumps({"schema_version": "1.0", "snapshot_id": "legacy", "private": "legacy-private-value"}),
            encoding="utf-8",
        )

        environment = {
            "PATH": f"{fake_cli.parent}{os.pathsep}{os.environ.get('PATH', '')}",
            "LARK_CLI_PATH": str(fake_cli),
        }
        with mock.patch.dict(os.environ, environment):
            exit_code, payload = agent_context.run_cli(["list", "--repo", str(repo), "--json"])

        self.assertEqual(0, exit_code, payload)
        self.assertFalse(any(path.exists() for path in (malformed, oversized, expired, legacy)))
        serialized = json.dumps(payload, sort_keys=True)
        self.assertNotIn("oversized-private-value", serialized)
        self.assertNotIn("expired-private-value", serialized)
        self.assertNotIn("legacy-private-value", serialized)

    def test_ct_10_snapshot_count_is_pruned_to_repository_limit(self):
        repo = self.make_repo()
        fake_cli = self.make_fake_lark_cli(["lark-doc"])
        now = datetime.now(timezone.utc)
        agent_context.write_context_snapshot(
            repo,
            self.make_request(),
            self.make_result(),
            agent_id="agent-seed",
            now=now,
        )
        seed_path = self.snapshot_files(repo)[0]
        seed = json.loads(seed_path.read_text(encoding="utf-8"))
        seed_path.unlink()
        for index in range(70):
            payload = copy.deepcopy(seed)
            payload["snapshot_id"] = f"snapshot-{index:03d}"
            payload["created_at"] = agent_context.isoformat(now + timedelta(seconds=index))
            payload["expires_at"] = agent_context.isoformat(now + timedelta(hours=1))
            path = agent_context.snapshots_dir(repo) / f"snapshot-{index:03d}.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            path.chmod(0o600)

        agent_context.list_context_snapshots(repo)

        self.assertLessEqual(len(self.snapshot_files(repo)), 64)


if __name__ == "__main__":
    unittest.main()
