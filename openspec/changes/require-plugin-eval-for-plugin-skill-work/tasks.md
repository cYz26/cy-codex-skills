# Tasks: Require Plugin Eval For Plugin And Skill Work

## Target State

Future plugin and skill creation or updates in this repository proactively run
Plugin Eval, optimize or explicitly defer findings, and record the score and
decisions as verification evidence.

## Completion Contract

- [x] Root `AGENTS.md` requires Plugin Eval for plugin and skill creation/update
  work.
- [x] DevFlow `AGENTS.md` templates carry the same rule.
- [x] Tests enforce the rule in root instructions and templates.
- [x] Current `codex-updater` skill has been evaluated with Plugin Eval before
  and after optimization.
- [x] A memory note records the user's future preference.
- [x] OpenSpec validates strictly.

## 1. Tests

- [x] 1.1 Add a test that root `AGENTS.md` includes a Plugin Eval gate for plugin
  and skill creation/update work.
- [x] 1.2 Add a test that DevFlow development and release AGENTS templates include
  the same Plugin Eval gate.
- [x] 1.3 Run the focused tests and confirm they fail before instruction updates.

## 2. Implementation

- [x] 2.1 Update root `AGENTS.md` with a concise Plugin Eval quality gate.
- [x] 2.2 Update DevFlow development `AGENTS.md` template.
- [x] 2.3 Sync the release `AGENTS.md` template.
- [x] 2.4 Optimize `codex-updater` skill based on Plugin Eval output while
  preserving dry-run/apply safety boundaries.
- [x] 2.5 Add a memory update note for the user's future Plugin Eval preference.

## 3. Verification

- [x] 3.1 Re-run Plugin Eval on the optimized `codex-updater` skill.
- [x] 3.2 Run Plugin Eval on the changed DevFlow plugin path or relevant bundle.
- [x] 3.3 Run focused and full DevFlow tests.
- [x] 3.4 Run `openspec validate --all --strict`.
- [x] 3.5 Record verification evidence and residual risks.

## Verification Evidence

- RED: `python3 -m unittest dev.plugins.dev-flow.tests.test_project_orchestrator.ProjectOrchestratorTests.test_plugin_eval_gate_is_required_for_plugin_and_skill_changes` failed for root, development template, and release template before the Plugin Eval gate existed.
- Plugin Eval baseline for `dev/plugins/dev-flow/skills/codex-updater`: score 100/100, grade A, active budget 662 tokens, no failures or warnings.
- Plugin Eval final for `dev/plugins/dev-flow/skills/codex-updater`: score 100/100, grade A, active budget 613 tokens, no failures or warnings.
- Plugin Eval final for `dev/plugins/dev-flow`: score 77/100, grade C, high risk due to pre-existing deferred token budget and Python complexity findings; local readability warning was removed.
- Plugin Eval final for `plugins/dev-flow`: score 77/100, grade C, high risk due to pre-existing deferred token budget and Python complexity findings.
- Focused Plugin Eval gate and codex-updater tests passed.
- `python3 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_dependencies.py'` passed: 22 tests.
- `python3 -m unittest discover -s plugins/dev-flow/tests` passed: 22 tests.
- `python3 -m unittest discover -s dev/plugins/dev-flow/tests` passed: 72 tests.
- `openspec validate --all --strict` passed: 16 items.
- Relevant `git diff --check` passed.
- Verification record:
  `.planning/verification/20260531203144-plugin-eval-gate-and-codex-updater-optimization.md`.

## Deferred Findings

- DevFlow plugin-level `deferred_cost_tokens-budget-high`, `invoke_cost_tokens-budget-high`, and `py-complexity-high` remain deferred because they require broad plugin packaging and helper-script refactors outside this request's scope.
