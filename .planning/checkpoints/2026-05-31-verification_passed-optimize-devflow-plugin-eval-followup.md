# Checkpoint: optimize-devflow-plugin-eval-followup verification passed

Date: 2026-05-31

## Scope

Optimized the DevFlow release plugin based on Plugin Eval results without splitting the release package or doing broad script refactors.

Completed behavior:

- Marked low-frequency skills explicit-only with `agents/openai.yaml`.
- Kept core routing skills implicit.
- Added release smoke coverage for skill invocation policy and release Python line length.
- Fixed scoped release and dev-copy Python long lines.
- Removed generated `__pycache__` directories.
- Recorded Plugin Eval before/after JSON and comparison evidence.

## Changed Files

- `.planning/STATE.md`
- `.planning/checkpoints/2026-05-31-verification_passed-optimize-devflow-plugin-eval-followup.md`
- `.planning/verification/20260531201318-optimize-devflow-plugin-eval-followup.md`
- `.planning/verification/plugin-eval-dev-flow-before.json`
- `.planning/verification/plugin-eval-dev-flow-brief-before.json`
- `.planning/verification/plugin-eval-dev-flow-after.json`
- `.planning/verification/plugin-eval-dev-flow-brief-after.json`
- `openspec/changes/optimize-devflow-plugin-eval-followup/`
- `plugins/dev-flow/tests/test_release_smoke.py`
- `plugins/dev-flow/scripts/codex_auto_update_plugins_skills.py`
- `plugins/dev-flow/scripts/workflow_compact_policy.py`
- `dev/plugins/dev-flow/scripts/codex_auto_update_plugins_skills.py`
- `dev/plugins/dev-flow/scripts/workflow_compact_policy.py`
- `plugins/dev-flow/skills/*/agents/openai.yaml` for explicit-only low-frequency skills.
- `dev/plugins/dev-flow/skills/*/agents/openai.yaml` for explicit-only low-frequency skills.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s plugins/dev-flow/tests`: pass, 21 tests ran.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s dev/plugins/dev-flow/tests`: pass, 69 tests ran.
- `openspec validate --all --strict`: pass, 14 items.
- `PYTHONDONTWRITEBYTECODE=1 python3 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo /Users/cy/Dev/agents-dev/cy-codex-skills --json`: pass, `ok: true`.
- Plugin Eval after optimization: pass, output written to `.planning/verification/plugin-eval-dev-flow-after.json`.
- `find plugins/dev-flow dev/plugins/dev-flow -type d -name __pycache__ -print`: no output.

## Plugin Eval Result

- Score improved from 68 to 77.
- Grade improved from D to C.
- Trigger budget improved from 264 heavy to 99 moderate.
- Invoke budget improved from 6671 heavy to 2941 heavy.
- Python long-line warning cleared.

## Remaining Risks

- Deferred token budget remains excessive at 65705 tokens because the release package still contains a large amount of supporting documentation, scripts, and workflow surface.
- Python complexity warning remains, primarily around existing large scripts. This was intentionally left for a separate refactor.
- Coverage artifacts remain unavailable because this verification did not introduce coverage report generation.

## Next Action

Review and archive `optimize-devflow-plugin-eval-followup` if the remaining deferred-budget risk is acceptable as follow-up work.
