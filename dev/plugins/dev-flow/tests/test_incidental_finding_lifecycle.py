from pathlib import Path
import unittest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLUGIN_ROOT.parents[2]
TEMPLATES = PLUGIN_ROOT / "assets" / "templates"
SKILLS = PLUGIN_ROOT / "skills"

DISPOSITIONS = (
    "CONTINUE_WITH_MINIMAL_GUARD",
    "DEFER_AND_CONTINUE",
    "BLOCKED_AWAITING_HUMAN",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class IncidentalFindingLifecycleTests(unittest.TestCase):
    def assert_dispositions(self, text: str) -> None:
        for disposition in DISPOSITIONS:
            self.assertIn(disposition, text)

    def test_root_and_generated_guidance_define_one_lifecycle(self) -> None:
        root_guidance = read(REPO_ROOT / "AGENTS.md")
        generated_guidance = read(TEMPLATES / "AGENTS.md.template")

        for guidance in (root_guidance, generated_guidance):
            with self.subTest(path="root" if guidance is root_guidance else "template"):
                self.assertIn("## Incidental Finding Lifecycle", guidance)
                self.assert_dispositions(guidance)
                self.assertIn("TASK_LEDGER.md", guidance)
                self.assertIn("required Completion Contract behavior", guidance)
                self.assertIn("human", guidance.lower())

    def test_planning_templates_protect_the_critical_path(self) -> None:
        design = read(TEMPLATES / "OPENSPEC_DESIGN.md.template")
        tasks = read(TEMPLATES / "OPENSPEC_TASKS.md.template")

        for template in (design, tasks):
            self.assertIn("Critical Path", template)
            self.assertIn("Incidental Finding Budget", template)
            self.assertIn("Escalation Triggers", template)
        self.assertIn("one bounded RED/GREEN cycle", design)
        self.assertIn("new dependency", design)
        self.assertIn("expanded write set", design)

    def test_task_ledger_is_the_durable_finding_register(self) -> None:
        for ledger in (
            read(REPO_ROOT / "TASK_LEDGER.md"),
            read(TEMPLATES / "TASK_LEDGER.md.template"),
        ):
            self.assertIn("## Incidental Finding Register", ledger)
            for field in (
                "Finding ID",
                "Disposition",
                "Severity",
                "Evidence",
                "Affected Contract",
                "Impact",
                "Current Mitigation",
                "Disposition Reason",
                "Recommended Follow-up",
                "Follow-up Trigger",
                "Human Disposition",
            ):
                self.assertIn(field, ledger)
            self.assertIn("pending", ledger)
            self.assertIn("accepted", ledger)
            self.assertIn("rejected", ledger)
            self.assertIn("deferred", ledger)
            self.assertIn("does not authorize", ledger.lower())

    def test_engineering_policy_defines_severe_human_stop(self) -> None:
        for policy in (
            read(REPO_ROOT / "ENGINEERING_POLICY.md"),
            read(TEMPLATES / "ENGINEERING_POLICY.md.template"),
        ):
            self.assertIn("## Severe Finding Human Stop", policy)
            self.assertIn("BLOCKED_AWAITING_HUMAN", policy)
            self.assertIn("data loss", policy.lower())
            self.assertIn("authority bypass", policy.lower())
            self.assertIn("read-only diagnosis", policy.lower())
            self.assertIn("one concrete", policy.lower())
            self.assertIn("before resuming", policy.lower())

    def test_evidence_and_review_require_residual_finding_disposition(self) -> None:
        for evidence in (
            read(REPO_ROOT / "EVIDENCE_TEMPLATE.md"),
            read(TEMPLATES / "EVIDENCE_TEMPLATE.md.template"),
        ):
            self.assertIn("## Incidental Finding Disposition", evidence)
            self.assertIn("why it does not block", evidence.lower())
            self.assertIn("follow-up confirmation", evidence.lower())

        for review in (
            read(REPO_ROOT / "REVIEW_CHECKLIST.md"),
            read(TEMPLATES / "REVIEW_CHECKLIST.md.template"),
        ):
            self.assertIn("Incidental Findings", review)
            self.assertIn("BLOCKED_AWAITING_HUMAN", review)
            self.assertIn("accept, reject, or defer", review.lower())

    def test_intake_and_planning_skills_apply_the_finding_gate(self) -> None:
        feature_intake = read(SKILLS / "feature-intake" / "SKILL.md")
        change_plan = read(SKILLS / "change-plan" / "SKILL.md")
        tech_plan = read(SKILLS / "ai-native-tech-plan" / "SKILL.md")

        self.assert_dispositions(feature_intake)
        self.assertIn("before planning", feature_intake.lower())
        self.assertIn("affected Completion Contract", feature_intake)

        self.assertIn("Incidental Finding Lifecycle", change_plan)
        self.assertIn("TASK_LEDGER.md", change_plan)
        self.assertIn("required behavior", change_plan.lower())

        self.assertIn("Critical Path", tech_plan)
        self.assertIn("Incidental Finding Budget", tech_plan)
        self.assertIn("Escalation Triggers", tech_plan)
        self.assertIn("one bounded RED/GREEN cycle", tech_plan)

    def test_execution_and_orchestration_fail_closed(self) -> None:
        execute_task = read(SKILLS / "execute-task" / "SKILL.md")
        orchestrator = read(SKILLS / "project-orchestrator" / "SKILL.md")

        for skill in (execute_task, orchestrator):
            self.assert_dispositions(skill)
            self.assertIn("TASK_LEDGER.md", skill)
            self.assertIn("BLOCKED_AWAITING_HUMAN", skill)
            self.assertIn("human", skill.lower())
        self.assertIn("safe read-only diagnosis", execute_task.lower())
        self.assertIn("before resuming", execute_task.lower())
        self.assertIn("required behavior", execute_task.lower())

    def test_completion_discloses_findings_and_requires_followup_confirmation(self) -> None:
        completion = read(SKILLS / "verify-and-archive" / "SKILL.md")

        self.assertIn("Incidental Findings", completion)
        self.assertIn("DEFER_AND_CONTINUE", completion)
        self.assertIn("BLOCKED_AWAITING_HUMAN", completion)
        self.assertIn("accept, reject, or defer", completion.lower())
        self.assertIn("must not start", completion.lower())
        self.assertIn("completion", completion.lower())
        self.assertIn("archive", completion.lower())

    def test_source_readme_explains_no_automatic_followup(self) -> None:
        readme = read(PLUGIN_ROOT / "README.md")

        self.assertIn("## Incidental Finding Lifecycle", readme)
        self.assert_dispositions(readme)
        self.assertIn("does not authorize", readme.lower())
        self.assertIn("human", readme.lower())
        self.assertIn("follow-up", readme.lower())


if __name__ == "__main__":
    unittest.main()
