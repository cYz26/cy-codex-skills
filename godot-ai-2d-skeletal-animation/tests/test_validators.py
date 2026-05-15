import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
CASES = ROOT / "fixtures" / "godot_demo_project" / "fixtures" / "cases"
NEGATIVE = ROOT / "fixtures" / "godot_demo_project" / "fixtures" / "negative_cases"


def load_script(name: str):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ValidatorFixtureTest(unittest.TestCase):
    def test_positive_rig_has_no_critical_findings(self):
        validator = load_script("validate_rig_meta")
        report = validator.validate_rig(CASES / "case_01_humanoid_adventurer" / "rig_meta.json")

        self.assertEqual(report["summary"]["critical"], 0)
        self.assertEqual(report["summary"]["warning"], 0)

    def test_missing_part_rig_reports_critical_failure(self):
        validator = load_script("validate_rig_meta")
        report = validator.validate_rig(NEGATIVE / "missing_part" / "rig_meta.json")

        self.assertGreater(report["summary"]["critical"], 0)
        self.assertTrue(any("missing part file" in check["message"] for check in report["checks"]))

    def test_positive_motion_has_no_critical_findings(self):
        validator = load_script("validate_motion")
        case_dir = CASES / "case_01_humanoid_adventurer"
        report = validator.validate_motion(
            case_dir / "motions" / "action.json",
            case_dir / "rig_meta.json",
            0.01,
        )

        self.assertEqual(report["summary"]["critical"], 0)
        self.assertEqual(report["summary"]["warning"], 0)

    def test_action_motion_requires_on_and_off_events(self):
        validator = load_script("validate_motion")
        motion_dir = NEGATIVE / "action_missing_event"
        report = validator.validate_motion(
            motion_dir / "motions" / "action.json",
            motion_dir / "rig_meta.json",
            0.01,
        )

        self.assertGreater(report["summary"]["critical"], 0)
        self.assertTrue(any("requires hitbox/hazard" in check["message"] for check in report["checks"]))


if __name__ == "__main__":
    unittest.main()
