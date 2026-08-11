import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"


class HookPythonCompatibilityTests(unittest.TestCase):
    def make_repo(self) -> Path:
        temporary = tempfile.TemporaryDirectory(prefix="devflow-hook-python-compat-")
        self.addCleanup(temporary.cleanup)
        repo = Path(temporary.name)
        (repo / ".dev-flow.json").write_text(
            json.dumps({"projectContract": 8, "workflow": {"mode": "full-openspec"}})
            + "\n"
        )
        return repo

    def environment_without_tomllib(self) -> dict[str, str]:
        shadow = tempfile.TemporaryDirectory(prefix="devflow-shadow-tomllib-")
        self.addCleanup(shadow.cleanup)
        shadow_root = Path(shadow.name)
        (shadow_root / "tomllib.py").write_text(
            "raise ModuleNotFoundError(\"No module named 'tomllib'\")\n"
        )

        codex_home = tempfile.TemporaryDirectory(prefix="devflow-hook-codex-home-")
        self.addCleanup(codex_home.cleanup)

        environment = os.environ.copy()
        python_path = [str(shadow_root)]
        if environment.get("PYTHONPATH"):
            python_path.append(environment["PYTHONPATH"])
        environment["PYTHONPATH"] = os.pathsep.join(python_path)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PLUGIN_ROOT"] = str(PLUGIN_ROOT)
        environment["CODEX_HOME"] = codex_home.name
        return environment

    def run_hook(
        self,
        script_name: str,
        repo: Path,
        *arguments: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPTS / script_name), *arguments],
            cwd=repo,
            env=self.environment_without_tomllib(),
            input=json.dumps({"cwd": str(repo), "stop_hook_active": False}),
            text=True,
            capture_output=True,
            check=False,
        )

    def assert_started_without_import_traceback(
        self,
        result: subprocess.CompletedProcess[str],
    ) -> None:
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("ModuleNotFoundError", result.stderr)

    def test_migration_reminder_starts_without_tomllib(self):
        repo = self.make_repo()

        result = self.run_hook(
            "plugin_project_migration_check.py",
            repo,
            "--event",
            "user_prompt_submit",
        )

        self.assert_started_without_import_traceback(result)
        payload = json.loads(result.stdout)
        self.assertEqual(set(payload), {"hookSpecificOutput"})
        self.assertEqual(
            set(payload["hookSpecificOutput"]),
            {"hookEventName", "additionalContext"},
        )
        self.assertEqual(
            payload["hookSpecificOutput"]["hookEventName"],
            "UserPromptSubmit",
        )

    def test_aggregate_stop_hook_starts_without_tomllib(self):
        repo = self.make_repo()

        result = self.run_hook("devflow_stop_hook.py", repo, "--repo", str(repo))

        self.assert_started_without_import_traceback(result)
        if result.stdout.strip():
            payload = json.loads(result.stdout)
            self.assertEqual(set(payload), {"decision", "reason"})
            self.assertEqual(payload["decision"], "block")


if __name__ == "__main__":
    unittest.main()
