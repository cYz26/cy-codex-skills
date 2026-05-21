from __future__ import annotations

import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from context_fixer.analyzer import analyze_context
from context_fixer.cli import main
from context_fixer.render import render_html, render_text


class ContextFixerTests(unittest.TestCase):
    def test_analyze_context_reports_pressure_attribution_and_audit(self) -> None:
        repo, codex_home, session = self.fixture()
        report = analyze_context(repo=repo, codex_home=codex_home, sessions=[session])

        self.assertEqual(report["diagnosis"]["severity"], "critical")
        self.assertGreaterEqual(report["diagnosis"]["max_context_pct"], 0.91)
        self.assertEqual(report["diagnosis"]["compact_events"], 1)
        labels = {item["label"] for item in report["attribution"]["top_contributors"]}
        self.assertIn("runtime tool output: exec_command", labels)
        self.assertIn("project AGENTS.md", labels)
        self.assertEqual(report["config_audit"]["inventory"]["enabled_global_plugins"], 2)
        self.assertEqual(report["config_audit"]["inventory"]["global_skills"], 1)
        titles = {item["title"] for item in report["compression"]["recommendations"]}
        self.assertIn("Compact before continuing substantial work", titles)
        self.assertIn("Reduce large tool output from runtime tool output: exec_command", titles)

    def test_text_renderer_omits_sensitive_bodies(self) -> None:
        repo, codex_home, session = self.fixture()
        report = analyze_context(repo=repo, codex_home=codex_home, sessions=[session])

        text = render_text(report)

        self.assertIn("runtime tool output: exec_command", text)
        self.assertNotIn("xxxxx", text)
        self.assertNotIn("Keep context focused.", text)

    def test_html_renderer_shows_dashboard_without_sensitive_bodies(self) -> None:
        repo, codex_home, session = self.fixture()
        report = analyze_context(repo=repo, codex_home=codex_home, sessions=[session])

        page = render_html(report)

        self.assertIn("<!doctype html>", page)
        self.assertIn("Context Fixer icon", page)
        self.assertIn("Top Contributors", page)
        self.assertIn("Recommendations", page)
        self.assertIn("Instruction Chain", page)
        self.assertIn("runtime tool output: exec_command", page)
        self.assertNotIn("SECRET_USER_PROMPT", page)
        self.assertNotIn("SECRET_TOOL_ARGUMENT", page)
        self.assertNotIn("Keep context focused.", page)

    def test_dual_source_trace_overrides_usage_and_adds_request_attribution(self) -> None:
        repo, codex_home, session = self.fixture()
        trace = self.trace_fixture(repo.parent)

        report = analyze_context(repo=repo, codex_home=codex_home, sessions=[session], traces=[trace])

        self.assertEqual(report["data_sources"]["session_parser"]["status"], "enabled")
        self.assertEqual(report["data_sources"]["request_trace"]["status"], "enabled")
        self.assertEqual(report["data_sources"]["request_trace"]["events"], 1)
        self.assertEqual(report["data_sources"]["request_trace"]["exact_usage_events"], 1)
        self.assertEqual(report["diagnosis"]["source_of_truth"], "request_trace")
        self.assertEqual(report["diagnosis"]["last_input_tokens"], 97000)
        self.assertGreaterEqual(report["diagnosis"]["max_context_pct"], 0.97)
        self.assertEqual(report["context_policy"]["status"], "red")
        self.assertTrue(report["context_policy"]["compact_recommended"])
        labels = {item["label"] for item in report["attribution"]["top_contributors"]}
        self.assertIn("request messages: system", labels)
        self.assertIn("request messages: user", labels)
        self.assertIn("request tool definitions", labels)
        self.assertIn("request tool results", labels)
        titles = {item["title"] for item in report["compression"]["recommendations"]}
        self.assertIn("Inspect request trace contributors", titles)

        text = render_text(report)
        page = render_html(report)
        self.assertIn("Request trace events: 1", text)
        self.assertIn("Data Sources", page)
        self.assertIn("Policy Status", page)
        self.assertNotIn("SECRET_TRACE_USER", text)
        self.assertNotIn("SECRET_TRACE_USER", page)
        self.assertNotIn("sk-test-secret", page)

    def test_codex_claude_tap_trace_adds_format_metadata_and_codex_attribution(self) -> None:
        repo, codex_home, session = self.fixture()
        trace = self.claude_tap_codex_trace_fixture(repo.parent)

        report = analyze_context(repo=repo, codex_home=codex_home, sessions=[session], traces=[trace])

        trace_summary = report["traces"][0]
        self.assertEqual(trace_summary["trace_format"], "claude-tap-codex")
        self.assertEqual(trace_summary["transport"], "websocket")
        self.assertEqual(trace_summary["upstream_base_url"], "https://chatgpt.com/backend-api/codex")
        self.assertEqual(trace_summary["request_path"], "/v1/responses")
        self.assertEqual(trace_summary["request_method"], "WEBSOCKET")
        self.assertEqual(report["diagnosis"]["source_of_truth"], "request_trace")
        self.assertEqual(report["diagnosis"]["last_input_tokens"], 123456)

        labels = {item["label"] for item in report["attribution"]["top_contributors"]}
        self.assertIn("request codex instructions", labels)
        self.assertIn("request messages: user", labels)
        self.assertIn("request tool definitions", labels)
        self.assertIn("request tool results", labels)

        text = render_text(report)
        page = render_html(report)
        self.assertNotIn("SECRET_CODEX_INSTRUCTIONS", text)
        self.assertNotIn("SECRET_CODEX_USER", page)
        self.assertNotIn("SECRET_CODEX_TOOL_RESULT", page)
        self.assertNotIn("Bearer sk-codex-secret", page)

    def test_timeline_reports_historical_peak_compaction_and_zero_usage_anomaly(self) -> None:
        repo, codex_home, _session = self.fixture()
        latest_zero = self.session_file(
            codex_home,
            "2026/05/20/rollout-latest-zero.jsonl",
            [
                {"timestamp": "2026-05-20T10:00:00Z", "type": "session_meta", "payload": {"cwd": str(repo)}},
                {"timestamp": "2026-05-20T10:00:01Z", "type": "event_msg", "payload": {"type": "task_started", "model_context_window": 100000}},
                {
                    "timestamp": "2026-05-20T10:00:02Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {
                            "model_context_window": 100000,
                            "last_token_usage": {"input_tokens": 0, "total_tokens": 0},
                            "total_token_usage": {"input_tokens": 0},
                        },
                    },
                },
            ],
        )
        historical = self.session_file(
            codex_home,
            "2026/05/19/rollout-history.jsonl",
            [
                {"timestamp": "2026-05-19T09:00:00Z", "type": "session_meta", "payload": {"cwd": str(repo)}},
                {"timestamp": "2026-05-19T09:00:01Z", "type": "event_msg", "payload": {"type": "task_started", "model_context_window": 100000}},
                {
                    "timestamp": "2026-05-19T09:00:02Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {
                            "model_context_window": 100000,
                            "last_token_usage": {"input_tokens": 10000, "total_tokens": 10100},
                            "total_token_usage": {"input_tokens": 10000},
                        },
                    },
                },
                {
                    "timestamp": "2026-05-19T09:05:00Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {
                            "model_context_window": 100000,
                            "last_token_usage": {"input_tokens": 72000, "cached_input_tokens": 40000, "total_tokens": 72400},
                            "total_token_usage": {"input_tokens": 82000},
                        },
                    },
                },
                {"timestamp": "2026-05-19T09:06:00Z", "type": "event_msg", "payload": {"type": "context_compacted"}},
                {
                    "timestamp": "2026-05-19T09:07:00Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {
                            "model_context_window": 100000,
                            "last_token_usage": {"input_tokens": 30000, "total_tokens": 30200},
                            "total_token_usage": {"input_tokens": 112000},
                        },
                    },
                },
            ],
        )

        report = analyze_context(repo=repo, codex_home=codex_home, sessions=[latest_zero, historical])
        timeline = report["timeline"]

        self.assertEqual(report["diagnosis"]["last_input_tokens"], 0)
        self.assertEqual(report["diagnosis"]["latest_valid_input_tokens"], 30000)
        self.assertEqual(report["diagnosis"]["latest_valid_source"], "session_jsonl")
        self.assertEqual(timeline["peak_event"]["input_tokens"], 72000)
        self.assertEqual(timeline["latest_valid_usage_event"]["input_tokens"], 30000)
        self.assertEqual(len(timeline["compaction_events"]), 1)
        self.assertEqual(timeline["growth_events"][0]["delta_input_tokens"], 62000)
        self.assertTrue(any(item["anomaly_type"] == "zero_usage_session" for item in timeline["anomalies"]))
        self.assertIn("Latest session has zero token usage", {item["message"] for item in report["diagnosis"]["findings"]})

        text = render_text(report)
        page = render_html(report)
        raw = json.dumps(report, ensure_ascii=False)
        self.assertIn("Timeline:", text)
        self.assertIn("Timeline", page)
        self.assertNotIn("SECRET_USER_PROMPT", raw)
        self.assertNotIn("SECRET_TOOL_ARGUMENT", page)

    def test_timeline_includes_request_trace_events_without_sensitive_payloads(self) -> None:
        repo, codex_home, session = self.fixture()
        trace = self.trace_fixture(repo.parent)

        report = analyze_context(repo=repo, codex_home=codex_home, sessions=[session], traces=[trace])
        trace_events = [item for item in report["timeline"]["events"] if item["source"] == "request_trace"]

        self.assertEqual(len(trace_events), 1)
        self.assertEqual(trace_events[0]["kind"], "request")
        self.assertEqual(trace_events[0]["path"], "/v1/responses")
        self.assertEqual(trace_events[0]["model"], "gpt-5.5")
        self.assertTrue(trace_events[0]["exact_usage"])
        self.assertEqual(report["timeline"]["summary"]["request_events"], 1)
        self.assertEqual(report["timeline"]["summary"]["exact_usage_events"], 1)
        self.assertNotIn("SECRET_TRACE_USER", json.dumps(report, ensure_ascii=False))
        self.assertNotIn("sk-test-secret", render_html(report))

    def test_activity_reports_observed_calls_inventory_and_trace_categories(self) -> None:
        repo, codex_home, session = self.fixture()
        trace = self.trace_fixture(repo.parent)

        report = analyze_context(repo=repo, codex_home=codex_home, sessions=[session], traces=[trace])
        activity = report["activity"]
        observed = {item["name"]: item for item in activity["observed_calls"]}

        self.assertIn("exec_command", observed)
        self.assertEqual(observed["exec_command"]["call_count"], 1)
        self.assertEqual(observed["exec_command"]["result_count"], 1)
        self.assertGreater(observed["exec_command"]["argument_estimated_tokens"], 0)
        self.assertGreater(observed["exec_command"]["output_estimated_tokens"], 0)
        self.assertEqual(activity["activation_inventory"]["enabled_global_plugins"], 2)
        self.assertEqual(activity["activation_inventory"]["global_skills"], 1)
        self.assertEqual(activity["activation_inventory"]["project_skills"], 1)
        self.assertEqual(activity["activation_inventory"]["mcp_servers"], 1)
        self.assertIn("build-web-apps@openai-curated", activity["activation_inventory"]["enabled_global_plugin_keys"])
        self.assertNotIn("build-web-apps@openai-curated", observed)

        request_categories = {item["category"] for item in activity["request_activity"]}
        self.assertIn("model_request", request_categories)
        self.assertTrue(any(item["path"] == "/v1/responses" for item in activity["request_activity"]))
        self.assertIn("exec_command", activity["available_tools"])
        self.assertIn("shell", activity["available_tools"])

        text = render_text(report)
        page = render_html(report)
        raw = json.dumps(report, ensure_ascii=False)
        self.assertIn("Capability activity:", text)
        self.assertIn("Capability Activity", page)
        self.assertNotIn("SECRET_TOOL_ARGUMENT", raw)
        self.assertNotIn("SECRET_TRACE_USER", page)
        self.assertNotIn("sk-test-secret", raw)

    def test_cli_writes_html_report(self) -> None:
        repo, codex_home, session = self.fixture()
        output = repo.parent / "report.html"

        status = main(["--repo", str(repo), "--codex-home", str(codex_home), "--session", str(session), "--session-only", "--html", str(output)])

        self.assertEqual(status, 0)
        self.assertTrue(output.exists())
        page = output.read_text(encoding="utf-8")
        self.assertIn("Context Fixer", page)
        self.assertIn("Session Telemetry", page)

    def test_cli_without_trace_or_session_only_exits_with_trace_guidance(self) -> None:
        repo, codex_home, session = self.fixture()
        cache_home = repo.parent / "cache"

        status, output = self.run_cli_capture(
            ["--repo", str(repo), "--codex-home", str(codex_home), "--session", str(session)],
            cache_home=cache_home,
            claude_tap_path=None,
        )

        self.assertEqual(status, 3)
        self.assertIn("Request trace required by default", output)
        self.assertIn("uv tool install claude-tap", output)
        self.assertIn("--session-only", output)
        self.assertNotIn("Top contributors:", output)
        self.assertFalse((cache_home / "onboarding.json").exists())

    def test_cli_accepts_request_trace_file(self) -> None:
        repo, codex_home, session = self.fixture()
        trace = self.trace_fixture(repo.parent)
        output = repo.parent / "trace-report.html"

        status = main(
            [
                "--repo",
                str(repo),
                "--codex-home",
                str(codex_home),
                "--session",
                str(session),
                "--trace",
                str(trace),
                "--html",
                str(output),
            ]
        )

        self.assertEqual(status, 0)
        self.assertIn("Request Trace", output.read_text(encoding="utf-8"))

    def test_cli_first_run_recommends_optional_claude_tap_install_once(self) -> None:
        repo, codex_home, session = self.fixture()
        cache_home = repo.parent / "cache"

        first = self.run_cli_capture(
            ["--repo", str(repo), "--codex-home", str(codex_home), "--session", str(session), "--session-only"],
            cache_home=cache_home,
            claude_tap_path=None,
        )
        second = self.run_cli_capture(
            ["--repo", str(repo), "--codex-home", str(codex_home), "--session", str(session), "--session-only"],
            cache_home=cache_home,
            claude_tap_path=None,
        )

        self.assertEqual(first[0], 0)
        self.assertIn("Set up optional Codex request tracing", first[1])
        self.assertIn("uv tool install claude-tap", first[1])
        self.assertEqual(second[0], 0)
        self.assertNotIn("Set up optional Codex request tracing", second[1])
        self.assertFalse((repo / ".context-fixer").exists())

    def test_cli_first_run_recommends_capture_when_claude_tap_is_installed(self) -> None:
        repo, codex_home, session = self.fixture()
        cache_home = repo.parent / "cache"

        status, output = self.run_cli_capture(
            ["--repo", str(repo), "--codex-home", str(codex_home), "--session", str(session), "--session-only"],
            cache_home=cache_home,
            claude_tap_path="/usr/local/bin/claude-tap",
        )

        self.assertEqual(status, 0)
        self.assertIn("Capture Codex request traces with claude-tap", output)
        self.assertIn("claude-tap --tap-client codex", output)

    def test_cli_suppresses_first_run_guidance_when_trace_is_supplied(self) -> None:
        repo, codex_home, session = self.fixture()
        trace = self.trace_fixture(repo.parent)
        cache_home = repo.parent / "cache"

        status, output = self.run_cli_capture(
            [
                "--repo",
                str(repo),
                "--codex-home",
                str(codex_home),
                "--session",
                str(session),
                "--trace",
                str(trace),
            ],
            cache_home=cache_home,
            claude_tap_path=None,
        )

        self.assertEqual(status, 0)
        self.assertNotIn("Set up optional Codex request tracing", output)
        self.assertNotIn("uv tool install claude-tap", output)

    def test_audits_instruction_chain_project_config_and_runtime_sources(self) -> None:
        repo, codex_home, session = self.fixture()
        nested = repo / "packages" / "api"
        nested.mkdir(parents=True)
        (repo / ".codex").mkdir(exist_ok=True)
        (repo / ".codex" / "config.toml").write_text(
            'project_doc_fallback_filenames = ["TEAM_GUIDE.md"]\n'
            "[mcp_servers.local_docs]\n"
            'command = "docs-mcp"\n'
        )
        (repo / "TEAM_GUIDE.md").write_text("fallback project guidance\n")
        (repo / "AGENTS.override.md").write_text("root override guidance\n")
        (repo / "packages" / "AGENTS.md").write_text("package guidance\n")
        (nested / "AGENTS.override.md").write_text("nested override guidance\n")
        (repo / ".planning").mkdir()
        (repo / ".planning" / "STATE.md").write_text("phase: implementation\n")
        (repo / "openspec").mkdir()
        (repo / "openspec" / "config.yaml").write_text("project: lens\n")

        report = analyze_context(repo=repo, cwd=nested, codex_home=codex_home, sessions=[session])
        audit = report["config_audit"]
        labels = {item["label"] for item in report["attribution"]["top_contributors"]}
        recommendation_titles = {item["title"] for item in report["compression"]["recommendations"]}

        self.assertEqual(audit["inventory"]["project_mcp_servers"], 1)
        self.assertTrue(audit["inventory"]["has_project_config"])
        self.assertTrue(audit["inventory"]["has_planning_state"])
        self.assertTrue(audit["inventory"]["has_openspec"])
        self.assertEqual(
            [item["path"] for item in audit["instruction_chain"]["project"]],
            ["AGENTS.override.md", "packages/AGENTS.md", "packages/api/AGENTS.override.md"],
        )
        self.assertIn("turn developer instructions", labels)
        self.assertIn("session conversation messages", labels)
        self.assertIn("runtime tool arguments: exec_command", labels)
        self.assertIn("Create a durable checkpoint before compacting", recommendation_titles)

        text = render_text(report)
        self.assertIn("Instruction chain:", text)
        self.assertNotIn("SECRET_USER_PROMPT", text)
        self.assertNotIn("SECRET_TOOL_ARGUMENT", text)

    def fixture(self) -> tuple[Path, Path, Path]:
        root = Path(tempfile.mkdtemp(prefix="context_fixer-"))
        repo = root / "repo"
        codex_home = root / "codex-home"
        session = codex_home / "sessions" / "2026" / "05" / "18" / "rollout-test.jsonl"
        (repo / ".codex" / "skills" / "project-helper").mkdir(parents=True)
        (codex_home / "skills" / "global-helper").mkdir(parents=True)
        session.parent.mkdir(parents=True)
        (repo / "AGENTS.md").write_text("# Project instructions\n" + ("Keep context focused.\n" * 500))
        (repo / "CLAUDE.md").write_text("Legacy agent notes.\n")
        (repo / ".codex" / "skills" / "project-helper" / "SKILL.md").write_text("---\nname: project-helper\n---\n")
        (codex_home / "skills" / "global-helper" / "SKILL.md").write_text("---\nname: global-helper\n---\n")
        (codex_home / "config.toml").write_text(CONFIG)
        session.write_text("\n".join(json.dumps(event) for event in EVENTS) + "\n")
        return repo, codex_home, session

    def trace_fixture(self, root: Path) -> Path:
        trace = root / "trace.jsonl"
        trace.write_text(json.dumps(TRACE_EVENT) + "\n", encoding="utf-8")
        return trace

    def session_file(self, codex_home: Path, relative_path: str, events: list[dict]) -> Path:
        path = codex_home / "sessions" / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")
        return path

    def run_cli_capture(self, args: list[str], cache_home: Path, claude_tap_path: str | None) -> tuple[int, str]:
        buffer = StringIO()
        with patch.dict(os.environ, {"CONTEXT_FIXER_CACHE_HOME": str(cache_home)}), patch(
            "context_fixer.onboarding.shutil.which", return_value=claude_tap_path
        ), redirect_stdout(buffer):
            status = main(args)
        return status, buffer.getvalue()

    def claude_tap_codex_trace_fixture(self, root: Path) -> Path:
        trace = root / "claude-tap-codex-trace.jsonl"
        trace.write_text(json.dumps(CLAUDE_TAP_CODEX_TRACE_EVENT) + "\n", encoding="utf-8")
        return trace


CONFIG = """model = "gpt-5"
project_doc_max_bytes = 4096
project_doc_fallback_filenames = ["TEAM_GUIDE.md"]
[plugins."build-web-apps@openai-curated"]
enabled = true
[plugins."superpowers@openai-curated"]
enabled = true
[mcp_servers.figma]
command = "figma-mcp"
"""


EVENTS = [
    {"type": "session_meta", "payload": {"base_instructions": {"text": "base " * 800}, "dynamic_tools": [{"name": "shell"}, {"name": "web"}]}},
    {"type": "event_msg", "payload": {"type": "task_started", "model_context_window": 100000}},
    {
        "type": "turn_context",
        "payload": {
            "cwd": "/tmp/context_fixer-test/repo",
            "developer_instructions": "SECRET_DEVELOPER_INSTRUCTIONS " * 40,
            "summary": "prior context summary",
        },
    },
    {"type": "event_msg", "payload": {"type": "user_message", "message": "SECRET_USER_PROMPT " * 80}},
    {"type": "event_msg", "payload": {"type": "agent_message", "message": "agent reply " * 40}},
    {"type": "event_msg", "payload": {"type": "token_count", "info": {"model_context_window": 100000, "last_token_usage": {"input_tokens": 91000, "cached_input_tokens": 1000, "output_tokens": 500, "reasoning_output_tokens": 100, "total_tokens": 91500}}}},
    {"type": "response_item", "payload": {"type": "function_call", "call_id": "call-1", "name": "exec_command", "arguments": "SECRET_TOOL_ARGUMENT " * 200}},
    {"type": "response_item", "payload": {"type": "function_call_output", "call_id": "call-1", "output": "x" * 90000}},
    {"type": "event_msg", "payload": {"type": "context_compacted"}},
]


TRACE_EVENT = {
    "timestamp": "2026-05-18T09:00:00Z",
    "endpoint": "https://api.openai.com/v1/responses",
    "latency_ms": 321,
    "request": {
        "headers": {
            "authorization": "Bearer sk-test-secret",
            "content-type": "application/json",
        },
        "body": {
            "model": "gpt-5.5",
            "input": [
                {"role": "system", "content": "SECRET_TRACE_SYSTEM " * 60},
                {"role": "user", "content": "SECRET_TRACE_USER " * 90},
                {"role": "assistant", "content": [{"type": "output_text", "text": "assistant reply " * 30}]},
                {"role": "tool", "content": "SECRET_TRACE_TOOL_RESULT " * 240},
            ],
            "tools": [
                {
                    "type": "function",
                    "name": "exec_command",
                    "description": "Run a command",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "cmd": {"type": "string"},
                            "workdir": {"type": "string"},
                        },
                    },
                }
            ],
        },
    },
    "response": {
        "status": 200,
        "body": {
            "usage": {
                "input_tokens": 97000,
                "cached_input_tokens": 41000,
                "output_tokens": 900,
                "reasoning_output_tokens": 120,
                "total_tokens": 97900,
            }
        },
    },
}


CLAUDE_TAP_CODEX_TRACE_EVENT = {
    "timestamp": "2026-05-20T08:00:00Z",
    "request_id": "req_codex_ws",
    "client": "codex",
    "transport": "websocket",
    "upstream_base_url": "https://chatgpt.com/backend-api/codex",
    "duration_ms": 777,
    "request": {
        "method": "WEBSOCKET",
        "path": "/v1/responses",
        "headers": {
            "authorization": "Bearer sk-codex-secret",
            "openai-beta": "responses_websockets=2026-02-06",
        },
        "body": {
            "type": "response.create",
            "model": "gpt-5.5",
            "instructions": "SECRET_CODEX_INSTRUCTIONS " * 80,
            "input": [
                {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "SECRET_CODEX_USER " * 90}]},
                {"type": "function_call_output", "call_id": "call_1", "output": "SECRET_CODEX_TOOL_RESULT " * 240},
            ],
            "tools": [
                {
                    "type": "function",
                    "name": "exec_command",
                    "description": "Run a command",
                    "parameters": {"type": "object", "properties": {"cmd": {"type": "string"}}},
                }
            ],
            "previous_response_id": "resp_previous",
        },
    },
    "response": {
        "status": 101,
        "body": {
            "usage": {
                "input_tokens": 123456,
                "cached_input_tokens": 100000,
                "output_tokens": 2345,
                "reasoning_output_tokens": 456,
                "total_tokens": 125801,
            }
        },
        "ws_events": [{"type": "response.completed"}],
    },
}


if __name__ == "__main__":
    unittest.main()
