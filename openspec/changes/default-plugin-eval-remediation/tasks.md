# Tasks: Default Plugin Eval Remediation

## Target State

Plugin and skill changes still run Plugin Eval proactively, and any failures,
warnings, or fix-first recommendations are fixed or optimized by default before
completion. Deferral remains possible only as an explicit, evidenced exception
with residual risk and follow-up path recorded.

## Completion Contract

- [x] Root `AGENTS.md` states Plugin Eval findings are remediated by default.
- [x] DevFlow development and release AGENTS templates carry the same policy.
- [x] OpenSpec delta modifies the DevFlow Plugin Eval quality requirement.
- [x] Regression tests fail before the policy wording exists and pass after it
  is implemented.
- [x] Plugin Eval runs on the changed DevFlow plugin path and findings are
  fixed by default or explicitly justified.
- [x] OpenSpec validates strictly.

## 1. Tests

- [x] 1.1 Extend the Plugin Eval gate test to require remediation-first wording
  in root and template instructions.
- [x] 1.2 Run the focused test and confirm it fails before instruction updates.

## 2. Implementation

- [x] 2.1 Update root `AGENTS.md` Plugin Eval Gate.
- [x] 2.2 Update development `AGENTS.md` template.
- [x] 2.3 Sync release `AGENTS.md` template.
- [x] 2.4 Update this task ledger with verification evidence.

## 3. Verification

- [x] 3.1 Run the focused Plugin Eval gate test.
- [x] 3.2 Run relevant DevFlow test suites.
- [x] 3.3 Run `openspec validate --all --strict`.
- [x] 3.4 Run Plugin Eval on the changed DevFlow plugin path.
- [x] 3.5 Run `git diff --check`.

## Verification Evidence

- RED: `python3 -m unittest dev.plugins.dev-flow.tests.test_project_orchestrator.ProjectOrchestratorTests.test_plugin_eval_gate_is_required_for_plugin_and_skill_changes` failed for root, development template, and release template before the remediation-first wording existed.
- GREEN: the same focused test passed after updating `AGENTS.md` and both DevFlow templates.
- `python3 -m unittest discover -s dev/plugins/dev-flow/tests`: pass, 72 tests.
- `python3 -m unittest discover -s plugins/dev-flow/tests`: pass, 22 tests.
- `openspec validate --all --strict`: pass, 17 items.
- `git diff --check`: pass.
- Dev and release plugin preflight checks passed.
- Plugin Eval final for `plugins/dev-flow`: score 77/100, grade C, high risk.
- Plugin Eval final for `dev/plugins/dev-flow`: score 77/100, grade C, high risk.

## Deferred Findings

- `deferred_cost_tokens-budget-high`, `invoke_cost_tokens-budget-high`, and
  `py-complexity-high` remain deferred because fixing them requires broad
  plugin packaging and helper-script refactors outside this small policy change.
- Residual risk: DevFlow plugin-level context cost and script complexity remain
  high for full-plugin evaluation.
- Follow-up path: create a dedicated packaging/token-budget and Python
  complexity refactor change that splits large references/scripts without
  changing this remediation policy.
