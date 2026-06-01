# Verification: harden-claude-delegate-execution-contract

Timestamp: 2026-06-01T08:50:05+08:00

## Scope

Changed `claude-code-delegate` from a confirmation-oriented helper into a
complete-task delegation contract. The wrapper now prepends mode-specific
instructions before invoking Claude Code. Plan mode owns the complete
non-editing deliverable. Apply mode owns complete in-scope execution inside the
Claude Code run. Codex verifies scope, process evidence, diffs, tests, Git
state, workflow records, and blockers after Claude returns.

## Commands

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_claude_delegate.py'`
  - RED before implementation: failed because plan/apply prompts did not
    include the delegation contract.
  - GREEN after implementation: passed, 10 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest plugins/dev-flow/tests/test_release_smoke.py -k test_claude_code_delegation_is_packaged`
  - RED before skill wording updates: failed because packaged skill did not
    define the complete-task boundary.
  - GREEN after skill wording updates: passed.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s plugins/dev-flow/tests -p 'test_claude_delegate.py'`
  - Passed, 10 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s dev/plugins/dev-flow/tests`
  - Passed, 74 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s plugins/dev-flow/tests`
  - Passed, 24 tests.
- `openspec validate --all --strict`
  - Passed, 18 items.
- `git diff --check`
  - Passed.
- `PYTHONDONTWRITEBYTECODE=1 python3 dev/plugins/dev-flow/scripts/claude_code_delegate.py --repo /Users/cy/Dev/agents-dev/cy-codex-skills --check --json`
  - Passed, Claude Code 2.1.158.
- `PYTHONDONTWRITEBYTECODE=1 python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root dev/plugins/dev-flow --repo /Users/cy/Dev/agents-dev/cy-codex-skills --json`
  - Passed.
- `PYTHONDONTWRITEBYTECODE=1 python3 plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root plugins/dev-flow --repo /Users/cy/Dev/agents-dev/cy-codex-skills --json`
  - Passed.
- `node /Users/cy/.codex/plugins/cache/openai-curated/plugin-eval/fef63ecf/scripts/plugin-eval.js analyze plugins/dev-flow --format json > .planning/verification/plugin-eval-dev-flow-claude-contract-release.json`
  - Passed, score 77/100, grade C, risk high.
- `node /Users/cy/.codex/plugins/cache/openai-curated/plugin-eval/fef63ecf/scripts/plugin-eval.js analyze dev/plugins/dev-flow --format json > .planning/verification/plugin-eval-dev-flow-claude-contract-dev.json`
  - Passed, score 77/100, grade C, risk high.
- `codex plugin add dev-flow@cy-codex-skills`
  - Passed. Installed plugin root refreshed:
    `/Users/cy/.codex/plugins/cache/cy-codex-skills/dev-flow/0.3.0+codex.20260529145038`.
- `rg -n "Claude Code owns the complete bounded task|complete all in-scope execution|Codex verifies" /Users/cy/.codex/plugins/cache/cy-codex-skills/dev-flow/0.3.0+codex.20260529145038/skills/claude-code-delegate/SKILL.md /Users/cy/.codex/plugins/cache/cy-codex-skills/dev-flow/0.3.0+codex.20260529145038/scripts/workflow_claude_delegate.py`
  - Passed. Cached skill and wrapper include the new delegation contract.
- `PYTHONDONTWRITEBYTECODE=1 python3 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo /Users/cy/Dev/agents-dev/cy-codex-skills --json`
  - Passed with no issues or warnings.

## Plugin Eval Findings

- `deferred_cost_tokens-budget-high`: fail. Release and dev plugin deferred
  token cost remains excessive.
- `invoke_cost_tokens-budget-high`: warning. Release and dev plugin invoke cost
  remains heavy.
- `py-complexity-high`: warning. At least one Python function remains highly
  complex.
- `coverage-artifacts-unavailable`: info. Coverage artifacts were not present.

## Deferral Decision

The three actionable Plugin Eval findings are deferred for this change because
this change is scoped to the Claude delegation execution contract. Fixing those
findings requires broad plugin packaging, documentation splitting, and
helper-script complexity refactors that would change the risk profile of this
small behavior change.

Residual risk: full-plugin evaluation remains high risk due to context budget
and Python complexity.

Follow-up path: create a dedicated DevFlow packaging/token-budget and Python
complexity refactor change, then rerun Plugin Eval and either fix or explicitly
defer each remaining finding under the remediation-first policy.
