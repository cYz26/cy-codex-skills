import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import devflow_stop_hook
from devflow_stop_hook import continuation_stop_check
from workflow_compact_policy import resolve_continuation_required
from workflow_continuation import (
    AWAIT_HUMAN,
    CHECKPOINT_AND_CONTINUE,
    COMPLETE,
    CONTINUE_NEXT_ITEM,
    READY_FOR_EXTERNAL_EFFECT,
    VERIFY_ACTIVE_CHANGE,
    decide_continuation,
    execution_source,
    is_explicit_human_gate,
)


class ContinuousExecutionContractTests(unittest.TestCase):
    def make_repo(self, change_id="demo-change", verification_passed=False):
        repo = Path(tempfile.mkdtemp(prefix="devflow-continuation-"))
        (repo / ".planning" / "devflow").mkdir(parents=True)
        (repo / "openspec" / "changes" / change_id).mkdir(parents=True)
        (repo / ".planning" / "devflow" / "STATE.md").write_text(
            f"""---
workflow_version: 0.3.0
project_mode: brownfield
current_stage: executing
current_change:
  id: {change_id}
  status: executing
gates:
  verification_passed: {str(verification_passed).lower()}
context_management:
  compact_recommended: false
  compact_status: not_needed
---
# Workflow State

## Current Status

Executing approved work.

## Next Action

Continue the active task.
"""
        )
        return repo

    def test_pure_decision_exposes_all_six_outcomes_with_fail_closed_precedence(self):
        cases = [
            (
                AWAIT_HUMAN,
                dict(
                    source_valid=True,
                    work_remaining=True,
                    checkpoint_recommended=True,
                    verification_passed=False,
                    human_gate=True,
                    external_effect_ready=False,
                ),
            ),
            (
                AWAIT_HUMAN,
                dict(
                    source_valid=False,
                    work_remaining=True,
                    checkpoint_recommended=False,
                    verification_passed=False,
                    human_gate=False,
                    external_effect_ready=False,
                ),
            ),
            (
                CHECKPOINT_AND_CONTINUE,
                dict(
                    source_valid=True,
                    work_remaining=True,
                    checkpoint_recommended=True,
                    verification_passed=False,
                    human_gate=False,
                    external_effect_ready=False,
                ),
            ),
            (
                CONTINUE_NEXT_ITEM,
                dict(
                    source_valid=True,
                    work_remaining=True,
                    checkpoint_recommended=False,
                    verification_passed=False,
                    human_gate=False,
                    external_effect_ready=False,
                ),
            ),
            (
                VERIFY_ACTIVE_CHANGE,
                dict(
                    source_valid=True,
                    work_remaining=False,
                    checkpoint_recommended=False,
                    verification_passed=False,
                    human_gate=False,
                    external_effect_ready=False,
                ),
            ),
            (
                READY_FOR_EXTERNAL_EFFECT,
                dict(
                    source_valid=True,
                    work_remaining=False,
                    checkpoint_recommended=False,
                    verification_passed=True,
                    human_gate=False,
                    external_effect_ready=True,
                ),
            ),
            (
                COMPLETE,
                dict(
                    source_valid=True,
                    work_remaining=False,
                    checkpoint_recommended=False,
                    verification_passed=True,
                    human_gate=False,
                    external_effect_ready=False,
                ),
            ),
        ]

        observed = set()
        for expected, signals in cases:
            with self.subTest(expected=expected):
                decision = decide_continuation(**signals)
                self.assertEqual(decision["action"], expected)
                observed.add(decision["action"])

        self.assertEqual(
            observed,
            {
                AWAIT_HUMAN,
                CHECKPOINT_AND_CONTINUE,
                COMPLETE,
                CONTINUE_NEXT_ITEM,
                READY_FOR_EXTERNAL_EFFECT,
                VERIFY_ACTIVE_CHANGE,
            },
        )

    def test_active_openspec_tasks_take_precedence_over_complete_fallback_ledger(self):
        repo = self.make_repo()
        (repo / "openspec" / "changes" / "demo-change" / "tasks.md").write_text(
            "## Work\n\n- [x] 1.1 First item\n- [ ] 1.2 Second item\n"
        )
        (repo / "TASK_LEDGER.md").write_text(
            "| Task | Status |\n| --- | --- |\n| Legacy | done |\n"
        )

        source = execution_source(repo)

        self.assertEqual(source["kind"], "openspec")
        self.assertEqual(source["path"], "openspec/changes/demo-change/tasks.md")
        self.assertTrue(source["valid"])
        self.assertEqual(source["total"], 2)
        self.assertEqual(source["incomplete"], 1)

    def test_fallback_ledger_retains_strict_status_contract(self):
        repo = self.make_repo(change_id="none")
        (repo / "TASK_LEDGER.md").write_text(
            "| Task | Review Gate | Status |\n"
            "| --- | --- | --- |\n"
            "| First | schema \\| contract | done |\n"
            "| Second | none | in_progress |\n"
        )

        source = execution_source(repo)

        self.assertEqual(source["kind"], "task_ledger")
        self.assertTrue(source["valid"])
        self.assertEqual(source["total"], 2)
        self.assertEqual(source["incomplete"], 1)

    def test_openspec_parser_ignores_fenced_examples_and_fails_closed_on_malformed_tasks(self):
        repo = self.make_repo()
        tasks = repo / "openspec" / "changes" / "demo-change" / "tasks.md"
        tasks.write_text(
            "## Work\n\n```markdown\n- [ ] example only\n```\n\n- [x] 1.1 Real item\n"
        )

        source = execution_source(repo)

        self.assertTrue(source["valid"])
        self.assertEqual(source["total"], 1)
        self.assertEqual(source["incomplete"], 0)

        tasks.write_text("## Work\n\n- [?] ambiguous item\n")
        malformed = execution_source(repo)

        self.assertFalse(malformed["valid"])
        self.assertTrue(any("malformed" in issue for issue in malformed["issues"]))
        self.assertEqual(
            decide_continuation(
                source_valid=malformed["valid"],
                work_remaining=True,
                checkpoint_recommended=False,
                verification_passed=False,
                human_gate=False,
                external_effect_ready=False,
            )["action"],
            AWAIT_HUMAN,
        )

    def test_unsafe_active_change_id_fails_closed_without_path_escape(self):
        repo = self.make_repo()
        state = repo / ".planning" / "devflow" / "STATE.md"
        state.write_text(state.read_text().replace("id: demo-change", "id: ../../outside"))

        source = execution_source(repo)

        self.assertFalse(source["valid"])
        self.assertEqual(source["kind"], "openspec")
        self.assertTrue(any("change id" in issue for issue in source["issues"]))

    def test_human_gate_requires_both_existing_state_markers(self):
        self.assertTrue(
            is_explicit_human_gate(
                {
                    "current_stage": "awaiting_human",
                    "current_change": {"status": "awaiting_human"},
                }
            )
        )
        self.assertFalse(
            is_explicit_human_gate(
                {
                    "current_stage": "review",
                    "current_change": {"status": "awaiting_human"},
                }
            )
        )

    def test_stop_check_blocks_between_items_and_routes_closed_tasks_to_verification(self):
        repo = self.make_repo()
        tasks = repo / "openspec" / "changes" / "demo-change" / "tasks.md"
        tasks.write_text("## Work\n\n- [x] 1.1 First\n- [ ] 1.2 Second\n")

        between = continuation_stop_check(repo)

        self.assertFalse(between["ok"])
        self.assertEqual(between["action"], CONTINUE_NEXT_ITEM)
        self.assertEqual(between["executionSource"]["kind"], "openspec")

        tasks.write_text("## Work\n\n- [x] 1.1 First\n- [x] 1.2 Second\n")
        verification = continuation_stop_check(repo)

        self.assertFalse(verification["ok"])
        self.assertEqual(verification["action"], VERIFY_ACTIVE_CHANGE)

    def test_stop_check_allows_explicit_human_gate_and_is_read_only(self):
        repo = self.make_repo()
        tasks = repo / "openspec" / "changes" / "demo-change" / "tasks.md"
        tasks.write_text("## Work\n\n- [ ] 1.1 Waiting decision\n")
        state = repo / ".planning" / "devflow" / "STATE.md"
        state.write_text(
            state.read_text()
            .replace("current_stage: executing", "current_stage: awaiting_human")
            .replace("status: executing", "status: awaiting_human")
            .replace("Continue the active task.", "Choose the public compatibility behavior.")
        )
        before = {path: path.read_bytes() for path in (tasks, state)}

        check = continuation_stop_check(repo)

        self.assertTrue(check["ok"])
        self.assertEqual(check["action"], AWAIT_HUMAN)
        self.assertEqual(before, {path: path.read_bytes() for path in (tasks, state)})

    def test_aggregate_stop_hook_uses_continuation_as_the_primary_mid_work_gate(self):
        repo = self.make_repo()
        tasks = repo / "openspec" / "changes" / "demo-change" / "tasks.md"
        tasks.write_text("## Work\n\n- [x] 1.1 First\n- [ ] 1.2 Second\n")

        with mock.patch.object(
            devflow_stop_hook,
            "context_health_check",
            return_value={"risk": "low", "decision": "continue"},
        ), mock.patch.object(
            devflow_stop_hook,
            "release_promotion_run_gate",
            return_value={"status": "not_applicable", "message": "not applicable"},
        ):
            report = devflow_stop_hook.run_stop_checks(repo)

        self.assertFalse(report["ok"])
        self.assertEqual(report["failedChecks"], ["execution_continuation"])
        continuation = next(item for item in report["checks"] if item["id"] == "execution_continuation")
        self.assertEqual(continuation["action"], CONTINUE_NEXT_ITEM)
        verification = next(item for item in report["checks"] if item["id"] == "verification")
        self.assertEqual(verification["status"], "not_applicable")

    def test_aggregate_stop_hook_allows_real_human_and_external_effect_boundaries(self):
        human_repo = self.make_repo()
        human_tasks = human_repo / "openspec" / "changes" / "demo-change" / "tasks.md"
        human_tasks.write_text("## Work\n\n- [ ] 1.1 Waiting decision\n")
        human_state = human_repo / ".planning" / "devflow" / "STATE.md"
        human_state.write_text(
            human_state.read_text()
            .replace("current_stage: executing", "current_stage: awaiting_human")
            .replace("status: executing", "status: awaiting_human")
        )

        verified_repo = self.make_repo(verification_passed=True)
        verified_tasks = verified_repo / "openspec" / "changes" / "demo-change" / "tasks.md"
        verified_tasks.write_text("## Work\n\n- [x] 1.1 Complete\n")

        for repo, release_status, expected in (
            (human_repo, "not_applicable", AWAIT_HUMAN),
            (verified_repo, "pending", READY_FOR_EXTERNAL_EFFECT),
        ):
            with self.subTest(expected=expected), mock.patch.object(
                devflow_stop_hook,
                "context_health_check",
                return_value={"risk": "low", "decision": "continue"},
            ), mock.patch.object(
                devflow_stop_hook,
                "release_promotion_run_gate",
                return_value={"status": release_status, "message": release_status},
            ) as gate:
                report = devflow_stop_hook.run_stop_checks(repo)

            self.assertTrue(report["ok"], report)
            continuation = next(
                item for item in report["checks"] if item["id"] == "execution_continuation"
            )
            self.assertEqual(continuation["action"], expected)
            gate.assert_called_once_with(repo.resolve(), apply=False)

    def test_public_guidance_defines_the_enclosing_loop_and_real_human_gates(self):
        root = PLUGIN_ROOT.parents[2]
        surfaces = {
            "project-orchestrator": (
                PLUGIN_ROOT / "skills" / "project-orchestrator" / "SKILL.md",
                ["auto-until-terminal", "execute -> evidence -> decide -> continue", "phase label"],
            ),
            "execute-task": (
                PLUGIN_ROOT / "skills" / "execute-task" / "SKILL.md",
                ["completion receipt", "Return to `project-orchestrator`", "does not end the user request"],
            ),
            "checkpoint-compact": (
                PLUGIN_ROOT / "skills" / "checkpoint-compact" / "SKILL.md",
                ["phase label", "CHECKPOINT_AND_CONTINUE"],
            ),
            "verify-and-archive": (
                PLUGIN_ROOT / "skills" / "verify-and-archive" / "SKILL.md",
                ["active-change verification is not overall completion", "READY_FOR_EXTERNAL_EFFECT"],
            ),
            "feature-intake": (
                PLUGIN_ROOT / "skills" / "feature-intake" / "SKILL.md",
                ["execution policy", "auto-until-terminal"],
            ),
            "ai-native-tech-plan": (
                PLUGIN_ROOT / "skills" / "ai-native-tech-plan" / "SKILL.md",
                ["Continuation Policy", "genuine Human Gate"],
            ),
            "root AGENTS": (
                root / "AGENTS.md",
                ["## Continuous Execution", "auto-until-terminal", "A phase label is not a Human Gate"],
            ),
            "generated AGENTS": (
                PLUGIN_ROOT / "assets" / "templates" / "AGENTS.md.template",
                ["## Continuous Execution", "auto-until-terminal", "A phase label is not a Human Gate"],
            ),
            "root policy": (
                root / "ENGINEERING_POLICY.md",
                ["## Continuous Execution", "active Full OpenSpec task list"],
            ),
            "generated policy": (
                PLUGIN_ROOT / "assets" / "templates" / "ENGINEERING_POLICY.md.template",
                ["## Continuous Execution", "active Full OpenSpec task list"],
            ),
            "hook contract": (
                PLUGIN_ROOT / "docs" / "hook-contract.md",
                ["active Full OpenSpec task list", "execution continuation outcome"],
            ),
        }

        for name, (path, phrases) in surfaces.items():
            text = " ".join(path.read_text().split()).lower()
            for phrase in phrases:
                with self.subTest(surface=name, phrase=phrase):
                    self.assertIn(" ".join(phrase.split()).lower(), text)

    def test_review_and_handoff_labels_continue_unless_explicitly_terminal(self):
        for stage in (None, "", "review", "review_or_archive", "handoff", "new_thread"):
            with self.subTest(stage=stage):
                self.assertTrue(resolve_continuation_required(stage))

        self.assertFalse(resolve_continuation_required("review_or_archive", explicit=False))
        self.assertFalse(resolve_continuation_required("completed"))
        self.assertTrue(resolve_continuation_required("completed", explicit=True))


if __name__ == "__main__":
    unittest.main()
