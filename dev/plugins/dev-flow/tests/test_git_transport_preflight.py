import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


class GitTransportPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory(prefix="devflow-git-transport-")
        self.root = Path(self.temporary_directory.name)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def run_git(self, *args, cwd=None):
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            text=True,
            capture_output=True,
            check=True,
        )

    def make_remote_fixture(self):
        remote = self.root / "remote.git"
        repo = self.root / "work"
        self.run_git("init", "--bare", str(remote))
        self.run_git("init", "-b", "main", str(repo))
        (repo / "README.md").write_text("fixture\n")
        self.run_git("add", "README.md", cwd=repo)
        self.run_git(
            "-c",
            "user.name=DevFlow Tests",
            "-c",
            "user.email=devflow@example.invalid",
            "commit",
            "-m",
            "fixture",
            cwd=repo,
        )
        self.run_git("remote", "add", "origin", str(remote), cwd=repo)
        self.run_git("push", "-u", "origin", "main", cwd=repo)
        return repo, remote

    def test_push_and_pull_request_route_to_independent_capabilities(self):
        from workflow_git import route_repository_operation

        push = route_repository_operation("push")
        pull_request = route_repository_operation("pull-request")

        self.assertEqual(push["capability"], "native_git_transport")
        self.assertEqual(push["effect"], "git.push")
        self.assertFalse(push["requiresGh"])
        self.assertEqual(pull_request["capability"], "github_control_plane")
        self.assertEqual(pull_request["effect"], "github.control_plane_write")
        self.assertTrue(pull_request["requiresGh"])

    def test_release_route_prefers_repository_actions_without_local_gh(self):
        from workflow_git import route_repository_operation

        release = route_repository_operation("release")

        self.assertEqual(release["capability"], "github_control_plane")
        self.assertEqual(release["effect"], "github.control_plane_write")
        self.assertFalse(release["requiresGh"])
        self.assertTrue(release["directControlPlaneRequiresGh"])
        self.assertEqual(
            release["preferredExecutionPaths"],
            ["github_actions", "github_cli", "human_web"],
        )
        self.assertEqual(
            release["requiredEffects"],
            ["git.push", "github.control_plane_write"],
        )
        self.assertTrue(release["workflowMustBeInTriggerCommit"])
        self.assertTrue(release["immutableTriggerRequired"])
        self.assertTrue(release["leastPrivilegeTokenRequired"])
        self.assertTrue(release["postPublicationReadbackRequired"])
        self.assertTrue(release["localPromotionBlockedUntilReadback"])
        self.assertTrue(release["preserveTriggerOnFailure"])

    def test_non_release_control_plane_route_does_not_gain_actions_first_behavior(self):
        from workflow_git import route_repository_operation

        pull_request = route_repository_operation("pull-request")
        repository_settings = route_repository_operation("repository-settings")

        for route in (pull_request, repository_settings):
            with self.subTest(operation=route["operation"]):
                self.assertTrue(route["requiresGh"])
                self.assertNotIn("preferredExecutionPaths", route)
                self.assertNotIn("requiredEffects", route)

    def test_github_recovery_budget_stops_after_one_diagnosis_and_remediation(self):
        from workflow_git import github_control_plane_recovery_decision

        self.assertEqual(
            github_control_plane_recovery_decision(0, 0)["action"],
            "diagnose",
        )
        self.assertEqual(
            github_control_plane_recovery_decision(1, 0)["action"],
            "remediate",
        )
        exhausted = github_control_plane_recovery_decision(1, 1)
        self.assertEqual(exhausted["action"], "stop")
        self.assertFalse(exhausted["retryAllowed"])
        self.assertEqual(exhausted["effect"], "github.control_plane_write")

    def test_reachable_remote_reports_ready_without_calling_gh_or_pushing(self):
        from workflow_git import GIT_TRANSPORT_READY, git_transport_preflight

        repo, remote = self.make_remote_fixture()
        remote_before = self.run_git("rev-parse", "refs/heads/main", cwd=remote).stdout.strip()
        calls = []

        def native_git_only(command, **kwargs):
            calls.append(command)
            self.assertEqual(command[0], "git")
            self.assertNotIn("push", command)
            return subprocess.run(command, **kwargs)

        report = git_transport_preflight(
            repo,
            remote="origin",
            branch="main",
            runner=native_git_only,
        )
        remote_after = self.run_git("rev-parse", "refs/heads/main", cwd=remote).stdout.strip()

        self.assertEqual(report["status"], GIT_TRANSPORT_READY)
        self.assertEqual(report["operation"], "push")
        self.assertEqual(report["effect"], "git.push")
        self.assertFalse(report["requiresGh"])
        self.assertFalse(report["pushAttempted"])
        self.assertEqual(report["authorizationRequired"], "explicit_user_request")
        self.assertEqual(report["remote"]["transport"], "file")
        self.assertEqual(report["remoteCommit"], remote_before)
        self.assertEqual(remote_before, remote_after)
        self.assertTrue(calls)

    def test_missing_remote_fails_closed_without_gh_or_push(self):
        from workflow_git import GIT_TRANSPORT_BLOCKED, git_transport_preflight

        repo = self.root / "missing-remote"
        self.run_git("init", "-b", "main", str(repo))
        (repo / "README.md").write_text("fixture without remote\n")
        self.run_git("add", "README.md", cwd=repo)
        self.run_git(
            "-c",
            "user.name=DevFlow Tests",
            "-c",
            "user.email=devflow@example.invalid",
            "commit",
            "-m",
            "fixture",
            cwd=repo,
        )
        calls = []

        def native_git_only(command, **kwargs):
            calls.append(command)
            self.assertEqual(command[0], "git")
            self.assertNotIn("push", command)
            return subprocess.run(command, **kwargs)

        report = git_transport_preflight(
            repo,
            remote="origin",
            branch="main",
            runner=native_git_only,
        )

        self.assertEqual(report["status"], GIT_TRANSPORT_BLOCKED)
        self.assertEqual(report["reason"], "remote_not_configured")
        self.assertFalse(report["requiresGh"])
        self.assertFalse(report["pushAttempted"])
        self.assertTrue(calls)

    def test_remote_url_credentials_query_and_fragment_are_redacted(self):
        from workflow_git import redact_remote_url, sanitize_git_diagnostic

        raw = "https://alice:super-secret@example.com/org/repo.git?token=hidden#fragment"
        redacted = redact_remote_url(raw)
        diagnostic = sanitize_git_diagnostic(f"fatal: unable to access '{raw}'", [raw])

        for secret in ["alice", "super-secret", "token=hidden", "fragment"]:
            self.assertNotIn(secret, redacted)
            self.assertNotIn(secret, diagnostic)
        self.assertEqual(redacted, "https://***@example.com/org/repo.git")

    def test_malformed_credential_url_fails_safe_without_exposing_userinfo(self):
        from workflow_git import classify_remote_transport, redact_remote_url

        raw = "https://alice:super-secret@example.com:not-a-port/org/repo.git"

        self.assertEqual(classify_remote_transport(raw), "https")
        redacted = redact_remote_url(raw)
        self.assertEqual(redacted, "https://[redacted]")
        self.assertNotIn("alice", redacted)
        self.assertNotIn("super-secret", redacted)

    def test_json_cli_reports_ready_through_native_git(self):
        repo, _ = self.make_remote_fixture()
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "git_transport_preflight.py"),
                "--repo",
                str(repo),
                "--remote",
                "origin",
                "--branch",
                "main",
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "GIT_TRANSPORT_READY")
        self.assertFalse(report["requiresGh"])
        self.assertFalse(report["pushAttempted"])


if __name__ == "__main__":
    unittest.main()
