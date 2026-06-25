import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from superpowers_artifact_mapping import validate_promotion_record


class SuperpowersArtifactMappingTests(unittest.TestCase):
    def test_superpowers_plan_requires_canonical_promotion_target(self):
        repo = Path(tempfile.mkdtemp(prefix="devflow-promotion-"))
        source = repo / "docs" / "superpowers" / "plans" / "plan.md"
        source.parent.mkdir(parents=True)
        source.write_text(
            "# Plan\n\n## Global Constraints\n\n## Interfaces\n\n## Validation Commands\n\nNo placeholders.\n"
        )

        missing = validate_promotion_record(
            repo,
            {
                "source": "docs/superpowers/plans/plan.md",
                "promotionType": "plan-to-openspec-tasks",
                "requiredChecks": [
                    "global_constraints_preserved",
                    "interfaces_preserved",
                    "validation_commands_preserved",
                    "no_placeholders",
                ],
            },
        )
        self.assertFalse(missing["ok"], missing)
        self.assertIn("missing target", missing["errors"])

        target = repo / "openspec" / "changes" / "demo" / "tasks.md"
        target.parent.mkdir(parents=True)
        target.write_text(
            "# Tasks\n\n## Global Constraints\n\n## Interfaces\n\n## Validation Commands\n\nNo placeholders.\n"
        )
        ok = validate_promotion_record(
            repo,
            {
                "source": "docs/superpowers/plans/plan.md",
                "target": "openspec/changes/demo/tasks.md",
                "promotionType": "plan-to-openspec-tasks",
                "requiredChecks": [
                    "global_constraints_preserved",
                    "interfaces_preserved",
                    "validation_commands_preserved",
                    "no_placeholders",
                ],
            },
        )
        self.assertTrue(ok["ok"], ok)
        self.assertEqual(ok["promotionType"], "plan-to-openspec-tasks")


if __name__ == "__main__":
    unittest.main()
