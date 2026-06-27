import json
import subprocess
import sys
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


STRONG_OBJECTIVE = (
    "Implement DevFlow Goal Quality Gate for candidate objectives, limited to "
    "goal quality helper, CLI, context-health goal prompt, routing skill text, "
    "release sync, and verification records, excluding live goal tool calls and "
    "ordinary narrow task routing, verified by focused goal-quality tests, "
    "context-health goal prompt tests, release smoke tests, runtime verification, "
    "and OpenSpec strict validation with all commands exiting 0, and stop before "
    "expanding scope, touching live goal tools, changing hook behavior, or accepting "
    "unresolved validation failures."
)


class GoalQualityTests(unittest.TestCase):
    def test_goal_quality_accepts_complete_objective(self):
        from workflow_goal_quality import goal_quality_report

        report = goal_quality_report(STRONG_OBJECTIVE)

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["missing"], [])
        self.assertTrue(report["checks"]["stop_conditions"])
        self.assertTrue(report["checks"]["success_threshold"])

    def test_goal_quality_rejects_activity_goal_without_stop_conditions(self):
        from workflow_goal_quality import goal_quality_report

        report = goal_quality_report(
            "Implement DevFlow goal quality improvements and run some tests."
        )

        self.assertFalse(report["ok"])
        self.assertIn("scope_boundaries", report["missing"])
        self.assertIn("non_goals", report["missing"])
        self.assertIn("success_threshold", report["missing"])
        self.assertIn("stop_conditions", report["missing"])

    def test_goal_quality_rejects_pure_activity_goal(self):
        from workflow_goal_quality import goal_quality_report

        report = goal_quality_report("make progress")

        self.assertFalse(report["ok"])
        self.assertIn("outcome", report["missing"])

    def test_cli_reports_json(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "validate_goal_quality.py"),
                "--objective",
                STRONG_OBJECTIVE,
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"], report)


if __name__ == "__main__":
    unittest.main()
