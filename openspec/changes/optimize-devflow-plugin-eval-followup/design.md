## Context

Plugin Eval for `plugins/dev-flow` reports:

- Score: 68/100, grade D, risk high.
- Required fix: `deferred_cost_tokens-budget-high` at about 65k tokens.
- Recommended fixes: heavy `trigger_cost_tokens`, heavy `invoke_cost_tokens`, high Python complexity, and Python long lines.
- The largest deferred cost comes from the plugin release tree containing many runtime scripts and templates. Removing those would be a packaging architecture change and is out of scope for this follow-up.

The safe near-term optimization is to reduce the always-considered implicit skill budget and clean obvious readability findings while leaving runtime behavior intact.

## Goals / Non-Goals

**Goals:**

- Reduce Plugin Eval trigger and invoke budget by marking low-frequency DevFlow skills explicit-only.
- Preserve implicit routing for the skills that select workflow paths.
- Eliminate Python long-line warnings visible in the release plugin tree.
- Remove generated `__pycache__` directories so evaluation inputs are not polluted by runtime artifacts.
- Produce before/after Plugin Eval evidence.

**Non-Goals:**

- Do not remove runtime scripts, templates, hooks, or tests from the release plugin package.
- Do not refactor large scripts such as `codex_auto_update_plugins_skills.py`.
- Do not change DevFlow command behavior, hook behavior, or OpenSpec/GSD/Superpowers workflow semantics.
- Do not install new dependencies.

## Decisions

### Decision 1: Keep core routing skills implicit

The implicit skill set remains:

- `project-orchestrator`
- `feature-intake`
- `change-plan`
- `capability-research`

These skills are the entrypoints that route vague or high-level requests to the right workflow. Keeping them implicit preserves ordinary DevFlow ergonomics.

### Decision 2: Mark low-frequency skills explicit-only

The explicit-only skill set is:

- `ai-native-tech-plan`
- `checkpoint-compact`
- `claude-code-delegate`
- `context-health-check`
- `context-tool-audit`
- `execute-task`
- `project-setup`
- `verify-and-archive`
- `workflow-doctor`

These remain available by explicit skill name or via routing guidance from implicit skills, but their full `SKILL.md` bodies no longer count toward implicit invoke budget in Plugin Eval's policy-aware model.

### Decision 3: Use tests to enforce policy split

Release smoke tests will assert that explicit-only skills contain `agents/openai.yaml` with `allow_implicit_invocation: false`, and that core routing skills do not carry that policy. This keeps future edits from accidentally re-expanding implicit budget.

### Decision 4: Use Plugin Eval as the acceptance metric

The target is not to make deferred cost perfect in this change. Acceptance is a measurable improvement in Plugin Eval trigger/invoke budget and removal of the Python long-line warning, while preserving unit/OpenSpec/workflow validation.

## Risks / Trade-offs

- Explicit-only skills may be less likely to auto-trigger directly -> Core routing skills remain implicit and can point to these workflows.
- Plugin Eval may still report high deferred cost -> This is expected until a separate release packaging/splitting change is approved.
- Python complexity may remain high -> Refactoring the largest script is out of scope for this small optimization.
