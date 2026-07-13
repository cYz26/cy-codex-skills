import json
import re
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
TARGET_SKILLS = (
    "project-orchestrator",
    "feature-intake",
    "ai-native-tech-plan",
    "change-plan",
    "execute-task",
    "verify-and-archive",
    "project-setup",
    "workflow-doctor",
)
CAPABILITY_IDS = {
    "decision-resolution",
    "implementation-planning",
    "test-first-execution",
    "root-cause-diagnosis",
    "change-review",
    "completion-proof",
    "execution-orchestration",
    "architecture-guidance",
    "goal-definition",
    "roadmap-lifecycle",
}


class ProviderGuidanceTests(unittest.TestCase):
    def test_routing_matrix_routes_capabilities_not_provider_names(self):
        matrix = json.loads((PLUGIN_ROOT / "docs" / "routing.matrix.json").read_text())

        self.assertEqual(matrix["schemaVersion"], 2)
        self.assertEqual(matrix["capabilityRegistry"], "provider_profiles.json#/capabilities")
        routed = set()
        for route in matrix["routes"]:
            self.assertIn("requiredCapabilities", route)
            self.assertIn("conditionalCapabilities", route)
            routed.update(route["requiredCapabilities"])
            routed.update(item["capability"] for item in route["conditionalCapabilities"])
            encoded = json.dumps(route)
            self.assertNotRegex(encoded, r"superpowers:|gsd-")
        self.assertTrue(routed <= CAPABILITY_IDS)
        self.assertIn("completion-proof", routed)
        self.assertIn("test-first-execution", routed)
        full = next(route for route in matrix["routes"] if route["id"] == "mandatory-full-openspec")
        self.assertNotIn("root-cause-diagnosis", full["requiredCapabilities"])
        self.assertIn(
            "root-cause-diagnosis",
            {item["capability"] for item in full["conditionalCapabilities"]},
        )

    def test_active_skills_use_capability_routing_and_namespaced_state(self):
        for skill_name in TARGET_SKILLS:
            with self.subTest(skill=skill_name):
                text = (PLUGIN_ROOT / "skills" / skill_name / "SKILL.md").read_text()
                self.assertIn("Capability Routing", text)
                self.assertNotIn(".planning/STATE.md", text)
                self.assertNotRegex(text, r"(?i)use `?(?:superpowers:|gsd-)")

    def test_provider_specific_details_are_deferred_to_one_reference(self):
        reference = PLUGIN_ROOT / "docs" / "provider-profile-migration.md"
        self.assertTrue(reference.exists())
        text = reference.read_text()
        for marker in (
            "core + none",
            "lean-matt",
            "strict-superpowers",
            ".planning/devflow/",
            "tracked",
            "partially_tracked",
            "local_only",
        ):
            self.assertIn(marker, text)

    def test_generated_guidance_defaults_to_core_none_without_universal_dependencies(self):
        agents = (PLUGIN_ROOT / "assets" / "templates" / "AGENTS.md.template").read_text()
        policy = (PLUGIN_ROOT / "assets" / "templates" / "ENGINEERING_POLICY.md.template").read_text()
        ledger = (PLUGIN_ROOT / "assets" / "templates" / "TASK_LEDGER.md.template").read_text()

        for text in (agents, policy, ledger):
            self.assertNotIn(".planning/STATE.md", text)
        self.assertIn("core + none", agents)
        self.assertIn("methodology_profile", agents)
        self.assertIn("roadmap_provider", agents)
        self.assertIn(".planning/devflow/", agents)
        self.assertIn("provider capability", policy.lower())
        self.assertIn("Provider Selection", ledger)

    def test_guidance_pruning_reduces_static_word_budget(self):
        words = 0
        for skill_name in TARGET_SKILLS:
            text = (PLUGIN_ROOT / "skills" / skill_name / "SKILL.md").read_text()
            words += len(re.findall(r"\S+", text))
        agents_words = len(
            re.findall(r"\S+", (PLUGIN_ROOT / "assets" / "templates" / "AGENTS.md.template").read_text())
        )

        self.assertLessEqual(words, 5000)
        self.assertLessEqual(agents_words, 1800)

    def test_active_guidance_has_no_legacy_devflow_planning_paths(self):
        files = [
            *sorted((PLUGIN_ROOT / "skills").rglob("*.md")),
            *sorted((PLUGIN_ROOT / "assets" / "templates").glob("*.md.template")),
        ]
        legacy_paths = (
            ".planning/STATE.md",
            ".planning/verification/",
            ".planning/checkpoints/",
            ".planning/context-health/",
            ".planning/compact-results/",
        )
        violations = []
        for path in files:
            text = path.read_text()
            for legacy in legacy_paths:
                if legacy in text:
                    violations.append(f"{path.relative_to(PLUGIN_ROOT)}: {legacy}")
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
