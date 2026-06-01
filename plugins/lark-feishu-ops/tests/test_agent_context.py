import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import lark_feishu_ops_agent_context as agent_context


class LarkFeishuAgentContextTests(unittest.TestCase):
    def make_repo(self):
        return Path(tempfile.mkdtemp(prefix="lark-agent-context-test-"))

    def make_request(self, *, action="docs.fetch", identity="user", profile="default", hints=None):
        dispatch_hints = {
            "identity": identity,
            "profile": profile,
            "direct_allowed": True,
            "read_only": action.endswith(".fetch") or action.endswith(".read") or action.endswith(".query"),
            "bounded": True,
            "single_domain": True,
            "cross_domain": False,
            "raw_openapi": False,
            "large_or_paginated": False,
            "requires_auth_profile_change": False,
            "explicit_subagent": False,
        }
        if hints:
            dispatch_hints.update(hints)

        return {
            "request_id": f"req-{action.replace('.', '-')}",
            "action": action,
            "goal": "Return targeted evidence for the parent answer.",
            "intent": "Answer a parent-level question without rediscovering Lark resources.",
            "question": "Does this design document understand Harness well?",
            "target": {"doc_token": "doc-123"},
            "handoff_context": {
                "user_goal": "Evaluate the design document.",
                "parent_context": ["Harness means repeatable agent workflow evaluation."],
                "known_resources": [{"type": "doc", "id": "doc-123", "revision": "7"}],
                "prior_evidence_pack": {},
                "freshness": {"known_revision_id": "7"},
                "non_goals": ["Do not read embedded sheets."],
            },
            "constraints": ["document-only"],
            "dispatch_hints": dispatch_hints,
            "expected_output": "evidence_pack",
            "success_criteria": ["Return coverage, missing evidence, and next resources."],
            "stop_conditions": ["Stop after the requested document read."],
            "return_format": "json",
        }

    def make_result(self):
        return {
            "status": "PASS",
            "action": "docs.fetch",
            "identity": "user",
            "commands_or_tools_used": [
                'curl -H "Authorization: Bearer abc123secret" https://open.feishu.cn'
            ],
            "targets": {"doc_token": "doc-123"},
            "progress": {"last_signal": "fetched doc revision 7", "state": "complete"},
            "result": {
                "evidence_pack": {
                    "question": "Does this design document understand Harness well?",
                    "coverage": "Read the kickoff document sections.",
                    "resource_map": {"sections": ["Background", "Harness"]},
                    "relevant_excerpts": [{"section": "Harness", "text": "short evidence"}],
                    "missing_evidence": ["Runtime failure recovery is thin."],
                    "token": "secret-value",
                },
                "next_resources": [{"type": "sheet", "id": "sheet-456"}],
            },
            "side_effects": [],
            "validation": {"read_back": True},
            "artifacts": [],
            "blockers": [],
            "residual_risk": ["Embedded sheet was not expanded."],
            "context_cache_update": {
                "resource_refs": [
                    {"type": "doc", "id": "doc-123", "revision": "7", "access_token": "secret-value"}
                ],
                "resource_map": {"doc-123": {"title": "Harness kickoff"}},
                "known_command_shapes": [
                    "lark-cli docs +fetch --api-version v2 --doc <doc> --format json"
                ],
                "missing_evidence": ["Runtime failure recovery is thin."],
                "freshness": {"known_revision_id": "7", "ttl_seconds": 86400},
                "provenance": {"command": "lark-cli docs +fetch", "raw_content": "x" * 6000},
            },
        }

    def test_normalize_delegation_request_adds_defaults_and_affinity(self):
        normalized = agent_context.normalize_delegation_request(self.make_request())

        self.assertEqual("docs.fetch", normalized["action"])
        self.assertEqual("req-docs-fetch", normalized["request_id"])
        self.assertEqual({}, normalized["handoff_context"]["prior_evidence_pack"])
        self.assertEqual("read", normalized["risk_class"])
        self.assertIn("doc-123", normalized["resource_refs"])
        self.assertIn("docs", normalized["affinity_key"])
        self.assertIn("doc-123", normalized["affinity_key"])

    def test_snapshot_write_redacts_sensitive_and_large_values(self):
        repo = self.make_repo()
        request = agent_context.normalize_delegation_request(self.make_request())
        result = agent_context.normalize_agent_result(self.make_result())

        snapshot = agent_context.write_context_snapshot(
            repo,
            request,
            result,
            agent_id="agent-doc",
            now=datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc),
        )

        snapshot_text = Path(snapshot["path"]).read_text(encoding="utf-8")
        self.assertNotIn("abc123secret", snapshot_text)
        self.assertNotIn("secret-value", snapshot_text)
        self.assertNotIn("Authorization: Bearer", snapshot_text)
        self.assertNotIn("x" * 2000, snapshot_text)
        self.assertIn("[REDACTED]", snapshot_text)
        self.assertIn("[TRUNCATED", snapshot_text)
        self.assertIn("doc-123", snapshot_text)

    def test_related_active_agent_recommends_reuse(self):
        repo = self.make_repo()
        request = agent_context.normalize_delegation_request(self.make_request())
        agent_context.record_active_agent(
            repo,
            agent_id="agent-doc",
            request=request,
            last_progress_at=datetime(2026, 6, 1, 9, 1, tzinfo=timezone.utc),
        )

        report = agent_context.prepare_dispatch_report(
            repo,
            self.make_request(),
            now=datetime(2026, 6, 1, 9, 2, tzinfo=timezone.utc),
        )

        self.assertEqual("reuse_active", report["dispatch"]["decision"])
        self.assertEqual("agent-doc", report["dispatch"]["agent_id"])
        self.assertEqual("parent_agent_runtime", report["runtime_boundary"]["subagent_primitives"])

    def test_fresh_inactive_snapshot_reconstructs_handoff(self):
        repo = self.make_repo()
        request = agent_context.normalize_delegation_request(self.make_request())
        result = agent_context.normalize_agent_result(self.make_result())
        snapshot = agent_context.write_context_snapshot(
            repo,
            request,
            result,
            agent_id="agent-doc",
            now=datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc),
        )

        report = agent_context.prepare_dispatch_report(
            repo,
            self.make_request(),
            now=datetime(2026, 6, 1, 9, 5, tzinfo=timezone.utc),
        )

        self.assertEqual("reconstruct_from_cache", report["dispatch"]["decision"])
        self.assertEqual(snapshot["snapshot_id"], report["dispatch"]["snapshot_id"])
        reconstructed = report["dispatch"]["reconstructed_request"]
        self.assertIn("prior_evidence_pack", reconstructed["handoff_context"])
        self.assertEqual(
            "Does this design document understand Harness well?",
            reconstructed["handoff_context"]["prior_evidence_pack"]["question"],
        )
        self.assertIn(
            {"type": "doc", "id": "doc-123", "revision": "7"},
            reconstructed["handoff_context"]["known_resources"],
        )

    def test_simple_safe_read_without_continuity_recommends_direct(self):
        repo = self.make_repo()

        report = agent_context.prepare_dispatch_report(
            repo,
            self.make_request(),
            now=datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc),
        )

        self.assertEqual("direct", report["dispatch"]["decision"])
        self.assertIn("bounded low-risk read", report["dispatch"]["reason"])

    def test_stale_snapshot_recommends_fresh_subagent_for_feishuops_work(self):
        repo = self.make_repo()
        request = agent_context.normalize_delegation_request(
            self.make_request(hints={"explicit_subagent": True, "direct_allowed": False})
        )
        result = agent_context.normalize_agent_result(self.make_result())
        agent_context.write_context_snapshot(
            repo,
            request,
            result,
            agent_id="agent-doc",
            now=datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc),
        )

        report = agent_context.prepare_dispatch_report(
            repo,
            self.make_request(hints={"explicit_subagent": True, "direct_allowed": False}),
            now=datetime(2026, 6, 3, 9, 0, tzinfo=timezone.utc),
        )

        self.assertEqual("fresh_subagent", report["dispatch"]["decision"])
        self.assertIn("stale", " ".join(report["dispatch"]["rejected_candidates"]))

    def test_identity_mismatch_recommends_clean_path(self):
        repo = self.make_repo()
        request = agent_context.normalize_delegation_request(self.make_request(identity="user"))
        result = agent_context.normalize_agent_result(self.make_result())
        agent_context.write_context_snapshot(
            repo,
            request,
            result,
            agent_id="agent-user",
            now=datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc),
        )

        report = agent_context.prepare_dispatch_report(
            repo,
            self.make_request(identity="bot", hints={"explicit_subagent": True, "direct_allowed": False}),
            now=datetime(2026, 6, 1, 9, 5, tzinfo=timezone.utc),
        )

        self.assertEqual("fresh_subagent", report["dispatch"]["decision"])
        self.assertIn("identity/profile mismatch", " ".join(report["dispatch"]["rejected_candidates"]))

    def test_read_context_is_not_reused_for_higher_risk_write(self):
        repo = self.make_repo()
        read_request = agent_context.normalize_delegation_request(self.make_request())
        result = agent_context.normalize_agent_result(self.make_result())
        agent_context.write_context_snapshot(
            repo,
            read_request,
            result,
            agent_id="agent-read",
            now=datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc),
        )

        write_request = self.make_request(
            action="docs.upsert",
            hints={
                "direct_allowed": False,
                "read_only": False,
                "explicit_subagent": True,
                "side_effects": True,
            },
        )
        report = agent_context.prepare_dispatch_report(
            repo,
            write_request,
            now=datetime(2026, 6, 1, 9, 5, tzinfo=timezone.utc),
        )

        self.assertEqual("fresh_subagent", report["dispatch"]["decision"])
        self.assertIn("read context cannot seed write", " ".join(report["dispatch"]["rejected_candidates"]))

    def test_prepare_cli_reads_request_and_does_not_spawn_agents(self):
        repo = self.make_repo()
        request_file = repo / "request.json"
        request_file.write_text(json.dumps(self.make_request()), encoding="utf-8")

        exit_code, payload = agent_context.run_cli(
            ["prepare", "--repo", str(repo), "--request-json", str(request_file), "--json"]
        )

        self.assertEqual(0, exit_code)
        self.assertEqual("direct", payload["dispatch"]["decision"])
        self.assertEqual("parent_agent_runtime", payload["runtime_boundary"]["subagent_primitives"])


if __name__ == "__main__":
    unittest.main()
