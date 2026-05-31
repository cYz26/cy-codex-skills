import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from workflow_claude_delegate import ClaudeDelegateOptions, check_claude_capability, delegate_to_claude


class FakeRunner:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, args, **kwargs):
        self.calls.append({"args": list(args), "kwargs": kwargs})
        if not self.responses:
            raise AssertionError(f"Unexpected command: {args}")
        response = self.responses.pop(0)
        if callable(response):
            return response(args, **kwargs)
        return response


def completed(args, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=args, returncode=returncode, stdout=stdout, stderr=stderr)


class ClaudeDelegateTests(unittest.TestCase):
    def make_repo(self):
        repo = Path(tempfile.mkdtemp(prefix="devflow-claude-delegate-"))
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=False)
        return repo

    def test_capability_check_reports_missing_optional_claude(self):
        report = check_claude_capability(path_resolver=lambda _: None)

        self.assertFalse(report["ok"], report)
        self.assertEqual(report["reason"], "claude-not-found")
        self.assertIn("optional runtime capability", report["message"])

    def test_capability_check_reports_path_and_version(self):
        runner = FakeRunner([completed(["/bin/claude", "--version"], stdout="2.1.158 (Claude Code)\n")])

        report = check_claude_capability(path_resolver=lambda _: "/bin/claude", runner=runner)

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["claudePath"], "/bin/claude")
        self.assertEqual(report["claudeVersion"], "2.1.158 (Claude Code)")

    def test_plan_mode_is_default_and_uses_noninteractive_json_output(self):
        repo = self.make_repo()
        runner = FakeRunner(
            [
                completed(["/bin/claude", "--version"], stdout="2.1.158 (Claude Code)\n"),
                completed(
                    ["/bin/claude"],
                    stdout=json.dumps(
                        {
                            "type": "result",
                            "subtype": "success",
                            "is_error": False,
                            "session_id": "session-1",
                            "result": "plan text",
                            "total_cost_usd": 0.012,
                        }
                    ),
                ),
            ]
        )

        report = delegate_to_claude(
            ClaudeDelegateOptions(repo=repo, task="Explain the next change", log=False),
            path_resolver=lambda _: "/bin/claude",
            runner=runner,
        )

        command = runner.calls[1]["args"]
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["mode"], "plan")
        self.assertIn("-p", command)
        self.assertIn("--output-format=json", command)
        self.assertIn("--no-session-persistence", command)
        self.assertEqual(command[command.index("--permission-mode") + 1], "plan")
        self.assertEqual(command[command.index("--max-budget-usd") + 1], "1.00")
        self.assertEqual(runner.calls[1]["kwargs"]["input"], "Explain the next change")

    def test_apply_mode_blocks_dirty_worktree_before_invoking_claude(self):
        repo = self.make_repo()
        runner = FakeRunner(
            [
                completed(["/bin/claude", "--version"], stdout="2.1.158 (Claude Code)\n"),
                completed(["git", "status", "--porcelain"], stdout=" M user-file.py\n"),
            ]
        )

        report = delegate_to_claude(
            ClaudeDelegateOptions(repo=repo, task="Edit the code", apply=True, log=False),
            path_resolver=lambda _: "/bin/claude",
            runner=runner,
        )

        self.assertFalse(report["ok"], report)
        self.assertEqual(report["reason"], "dirty-worktree")
        self.assertIn("dirty worktree", report["message"])
        self.assertEqual(len(runner.calls), 2)

    def test_apply_mode_defaults_to_bypass_permissions_when_dirty_is_allowed(self):
        repo = self.make_repo()
        runner = FakeRunner(
            [
                completed(["/bin/claude", "--version"], stdout="2.1.158 (Claude Code)\n"),
                completed(["git", "status", "--porcelain"], stdout=" M user-file.py\n"),
                completed(
                    ["/bin/claude"],
                    stdout=json.dumps(
                        {
                            "type": "result",
                            "subtype": "success",
                            "is_error": False,
                            "session_id": "session-2",
                            "result": "edited",
                        }
                    ),
                ),
            ]
        )

        report = delegate_to_claude(
            ClaudeDelegateOptions(repo=repo, task="Edit the code", apply=True, allow_dirty=True, log=False),
            path_resolver=lambda _: "/bin/claude",
            runner=runner,
        )

        command = runner.calls[2]["args"]
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["mode"], "apply")
        self.assertEqual(command[command.index("--permission-mode") + 1], "bypassPermissions")

    def test_claude_reported_error_json_is_normalized(self):
        repo = self.make_repo()
        runner = FakeRunner(
            [
                completed(["/bin/claude", "--version"], stdout="2.1.158 (Claude Code)\n"),
                completed(
                    ["/bin/claude"],
                    stdout=json.dumps(
                        {
                            "type": "result",
                            "subtype": "error_max_budget_usd",
                            "is_error": True,
                            "session_id": "budget-session",
                            "total_cost_usd": 0.0314,
                            "errors": ["Reached maximum budget ($0.01)"],
                        }
                    ),
                ),
            ]
        )

        report = delegate_to_claude(
            ClaudeDelegateOptions(repo=repo, task="Try a task", max_budget_usd="0.01", log=False),
            path_resolver=lambda _: "/bin/claude",
            runner=runner,
        )

        self.assertFalse(report["ok"], report)
        self.assertEqual(report["resultSubtype"], "error_max_budget_usd")
        self.assertEqual(report["sessionId"], "budget-session")
        self.assertEqual(report["costUsd"], 0.0314)
        self.assertEqual(report["errors"], ["Reached maximum budget ($0.01)"])

    def test_non_json_output_is_reported_as_structured_failure(self):
        repo = self.make_repo()
        runner = FakeRunner(
            [
                completed(["/bin/claude", "--version"], stdout="2.1.158 (Claude Code)\n"),
                completed(["/bin/claude"], returncode=1, stdout="not json\n" * 100, stderr="broken\n"),
            ]
        )

        report = delegate_to_claude(
            ClaudeDelegateOptions(repo=repo, task="Try a task", log=False),
            path_resolver=lambda _: "/bin/claude",
            runner=runner,
        )

        self.assertFalse(report["ok"], report)
        self.assertEqual(report["reason"], "invalid-json")
        self.assertEqual(report["stderr"], "broken")
        self.assertLessEqual(len(report["stdoutPreview"]), 1200)

    def test_metadata_log_omits_full_prompt_by_default(self):
        repo = self.make_repo()
        secret_prompt = "SECRET_PROMPT_SHOULD_NOT_BE_STORED"
        runner = FakeRunner(
            [
                completed(["/bin/claude", "--version"], stdout="2.1.158 (Claude Code)\n"),
                completed(
                    ["/bin/claude"],
                    stdout=json.dumps(
                        {
                            "type": "result",
                            "subtype": "success",
                            "is_error": False,
                            "session_id": "session-3",
                            "result": "ok",
                            "total_cost_usd": 0.001,
                        }
                    ),
                ),
            ]
        )

        report = delegate_to_claude(
            ClaudeDelegateOptions(repo=repo, task=secret_prompt),
            path_resolver=lambda _: "/bin/claude",
            runner=runner,
        )

        log_path = repo / report["runLog"]
        self.assertTrue(log_path.exists())
        log_payload = json.loads(log_path.read_text())
        self.assertEqual(log_payload["mode"], "plan")
        self.assertEqual(log_payload["sessionId"], "session-3")
        self.assertNotIn("task", log_payload)
        self.assertNotIn(secret_prompt, log_path.read_text())


if __name__ == "__main__":
    unittest.main()
