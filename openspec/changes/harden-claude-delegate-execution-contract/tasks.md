# Tasks: Harden Claude Code Delegate Execution Contract

## Target State

Claude Code delegation is a complete-task worker flow. Codex scopes and invokes
the delegation, then verifies process and result evidence. Codex does not use
Claude Code only for confirmation while doing the actual delegated work itself.

## Completion Contract

- [x] Wrapper prompts include mode-specific delegation contracts.
- [x] Apply-mode contract says Claude Code owns complete in-scope execution.
- [x] Plan-mode contract says Claude Code owns the complete non-editing
  deliverable.
- [x] Skill and README define Codex as supervisor/verifier, not fallback
  executor.
- [x] Tests cover wrapper prompt composition and packaged skill wording.
- [x] Plugin Eval is run on the changed DevFlow plugin path, and findings are
  fixed or explicitly deferred.
- [x] OpenSpec validates strictly.

## 1. Tests

- [x] 1.1 Add failing tests proving the wrapper passes the complete-task
  contract to Claude in both plan and apply mode.
- [x] 1.2 Add packaged skill coverage for the supervisor/verifier boundary.
- [x] 1.3 Run the focused tests and confirm they fail before implementation.

## 2. Implementation

- [x] 2.1 Add concise mode-specific delegation contracts in the wrapper.
- [x] 2.2 Ensure the original user task remains intact after the wrapper
  contract.
- [x] 2.3 Update development and release `claude-code-delegate` skill files.
- [x] 2.4 Update development and release README guidance.

## 3. Verification

- [x] 3.1 Run focused Claude delegate tests.
- [x] 3.2 Run relevant DevFlow dev and release test suites.
- [x] 3.3 Run `openspec validate --all --strict`.
- [x] 3.4 Run DevFlow workflow-state validation.
- [x] 3.5 Run Plugin Eval on the changed DevFlow plugin path.
- [x] 3.6 Run `git diff --check`.

## Verification Evidence

- RED: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_claude_delegate.py'` failed before implementation because plan and apply prompts did not include the delegation contract.
- RED: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest plugins/dev-flow/tests/test_release_smoke.py -k test_claude_code_delegation_is_packaged` failed before skill wording updates.
- GREEN: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_claude_delegate.py'`: pass, 10 tests.
- GREEN: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s plugins/dev-flow/tests -p 'test_claude_delegate.py'`: pass, 10 tests.
- GREEN: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest plugins/dev-flow/tests/test_release_smoke.py -k test_claude_code_delegation_is_packaged`: pass.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s dev/plugins/dev-flow/tests`: pass, 74 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s plugins/dev-flow/tests`: pass, 24 tests.
- `openspec validate --all --strict`: pass, 18 items.
- `git diff --check`: pass.
- `PYTHONDONTWRITEBYTECODE=1 python3 dev/plugins/dev-flow/scripts/claude_code_delegate.py --repo /Users/cy/Dev/agents-dev/cy-codex-skills --check --json`: pass, Claude Code 2.1.158.
- Dev and release plugin preflight checks passed.
- `codex plugin add dev-flow@cy-codex-skills`: pass; installed cache refreshed.
- Installed cache verification found the complete-task contract in cached skill and wrapper files.
- `PYTHONDONTWRITEBYTECODE=1 python3 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo /Users/cy/Dev/agents-dev/cy-codex-skills --json`: pass.
- Plugin Eval final for `plugins/dev-flow`: score 77/100, grade C, high risk.
- Plugin Eval final for `dev/plugins/dev-flow`: score 77/100, grade C, high risk.

## Deferred Findings

- `deferred_cost_tokens-budget-high`, `invoke_cost_tokens-budget-high`, and
  `py-complexity-high` remain deferred because fixing them requires broad
  plugin packaging and helper-script refactors outside this Claude delegation
  contract change.
- Residual risk: DevFlow plugin-level context cost and script complexity remain
  high for full-plugin evaluation.
- Follow-up path: create a dedicated packaging/token-budget and Python
  complexity refactor change that splits large references/scripts without
  changing this delegation contract.
