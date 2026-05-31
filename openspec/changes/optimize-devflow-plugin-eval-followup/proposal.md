## Why

Plugin Eval reports `dev-flow` at 68/100 with high risk, driven mainly by heavy static token budgets and smaller Python readability findings. The first safe optimization is to reduce implicit skill-load cost and remove obvious readability noise without changing DevFlow workflow behavior.

## What Changes

- Mark low-frequency DevFlow skills as explicit-only for OpenAI invocation policy so they no longer contribute to implicit trigger and invoke budget.
- Keep core routing skills implicit so ordinary DevFlow requests still route through the plugin.
- Fix remaining Python lines over 120 characters in the development and release plugin copies.
- Remove generated `__pycache__` directories from DevFlow plugin trees.
- Re-run Plugin Eval and record before/after evidence.
- Do not split the release package or refactor large scripts in this change.

## Capabilities

### New Capabilities

- `devflow-plugin-eval-optimization`: Covers Plugin Eval-driven static budget and readability optimization for the DevFlow plugin without changing runtime behavior.

### Modified Capabilities

- None.

## Impact

- Affected files: DevFlow skill metadata under `dev/plugins/dev-flow/skills/` and `plugins/dev-flow/skills/`, targeted Python formatting in both plugin copies, release smoke tests, OpenSpec tasks, and verification records.
- Compatibility: Core implicit routing remains available through `project-orchestrator`, `feature-intake`, `change-plan`, and `capability-research`; low-frequency skills remain explicitly usable by name.
- Dependencies: No new production dependencies.
