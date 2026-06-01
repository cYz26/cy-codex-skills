# Verification: default-plugin-eval-remediation

Timestamp: 2026-06-01T08:11:08+08:00

## Scope

Added a remediation-first Plugin Eval policy for plugin and skill changes.
Evaluation findings now default to fixing or optimization before completion.
Deferral is documented as an exception that must record reason, residual risk,
and follow-up path.

## Commands

- `python3 -m unittest dev.plugins.dev-flow.tests.test_project_orchestrator.ProjectOrchestratorTests.test_plugin_eval_gate_is_required_for_plugin_and_skill_changes`
  - RED before policy text updates: failed for root, dev template, and release template.
  - GREEN after policy text updates: passed.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s dev/plugins/dev-flow/tests`
  - Passed, 72 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s plugins/dev-flow/tests`
  - Passed, 22 tests.
- `openspec validate --all --strict`
  - Passed, 17 items.
- `git diff --check`
  - Passed.
- `PYTHONDONTWRITEBYTECODE=1 python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root plugins/dev-flow --marketplace .agents/plugins/marketplace.json --json`
  - Passed.
- `PYTHONDONTWRITEBYTECODE=1 python3 dev/plugins/dev-flow/scripts/codex_plugin_preflight.py --plugin-root dev/plugins/dev-flow --marketplace .agents/plugins/marketplace.dev.json --json`
  - Passed.
- `node /Users/cy/.codex/plugins/cache/openai-curated/plugin-eval/fef63ecf/scripts/plugin-eval.js analyze plugins/dev-flow --format json --output /tmp/dev-flow-plugin-eval-remediation.json`
  - Passed, score 77/100, grade C, risk high.
- `node /Users/cy/.codex/plugins/cache/openai-curated/plugin-eval/fef63ecf/scripts/plugin-eval.js analyze dev/plugins/dev-flow --format json --output /tmp/dev-flow-plugin-eval-remediation-dev.json`
  - Passed, score 77/100, grade C, risk high.

## Plugin Eval Findings

- `invoke_cost_tokens-budget-high`: warning. Release and dev plugin invoke cost
  remains heavy.
- `deferred_cost_tokens-budget-high`: fail. Release and dev plugin deferred
  token cost remains excessive.
- `py-complexity-high`: warning. At least one Python function remains highly
  complex.

## Deferral Decision

These findings are deferred for this change because this change only adds the
remediation-first policy. Fixing the findings requires broad plugin packaging,
documentation splitting, and helper-script refactors. That work would expand
scope and risk changing runtime behavior.

Residual risk: full-plugin evaluation remains high risk due to context budget
and script complexity.

Follow-up path: create a dedicated DevFlow packaging/token-budget and Python
complexity refactor change. That follow-up should use the new Plugin Eval
policy and fix or explicitly defer each finding.
