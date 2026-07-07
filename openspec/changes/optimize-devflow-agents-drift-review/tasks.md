# Tasks: Optimize DevFlow AGENTS Drift Review

## Target State

DevFlow refresh treats AGENTS drift review as an in-flow project refresh gate.
Template/core-flow drift is visible through generated candidates, active
`AGENTS.md` comparison, validation markers, and final refresh reporting.

## Completion Contract

- [x] OpenSpec change records the refresh/drift-review contract.
- [x] RED tests cover AGENTS template and validator drift detection.
- [x] Dev and release AGENTS templates include DevFlow Refresh Workflow.
- [x] `workflow_validate.py` checks current durable AGENTS guidance markers.
- [x] Focused tests, workflow validation, OpenSpec validation, and diff checks
  pass.
- [x] `.planning/STATE.md` and verification evidence are updated.

## Execution Ledger

- [x] 1. Create OpenSpec change for AGENTS drift review optimization.
- [x] 2. Add failing tests for template and validator behavior.
- [x] 3. Implement template, validator, and skill contract updates.
- [x] 4. Sync release assets.
- [x] 5. Run focused validation.
- [x] 6. Update durable state and report residual risks.

## Validation Commands

- RED: `/opt/homebrew/bin/python3.12 -m unittest dev/plugins/dev-flow/tests/test_dependencies.py dev/plugins/dev-flow/tests/test_release_smoke.py dev/plugins/dev-flow/tests/test_project_orchestrator.py` - failed with 8 expected failures for missing durable AGENTS markers and missing `DevFlow Refresh Workflow` in templates.
- GREEN: `/opt/homebrew/bin/python3.12 -m unittest dev/plugins/dev-flow/tests/test_dependencies.py dev/plugins/dev-flow/tests/test_release_smoke.py dev/plugins/dev-flow/tests/test_project_orchestrator.py` - pass, 114 tests.
- `/opt/homebrew/bin/python3.12 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo /Users/cY/dev/skills/cy-codex-skills --json` - pass, `ok=true`, no issues or warnings.
- `/opt/homebrew/bin/python3.12 dev/plugins/dev-flow/scripts/sync_release_assets.py --eval-target dev/plugins/dev-flow --json` - pass, release target `plugins/dev-flow`.
- `npx -y @fission-ai/openspec@latest validate optimize-devflow-agents-drift-review --strict` - pass.
- `npx -y @fission-ai/openspec@latest validate --all --strict` - pass, 45 items.
- `git diff --check` - pass.
- `node /Users/cY/.codex-switch/homes/internal/plugins/cache/openai-curated/plugin-eval/d6169bef/scripts/plugin-eval.js analyze plugins/dev-flow --format markdown` - pass with score 86/100, 0 failures, 3 token-budget warnings.
- `/opt/homebrew/bin/python3.12 dev/scripts/codex_auto_update_plugins_skills.py --json` - pass dry-run; `dev-flow@cy-codex-skills` would refresh and installed cache differs from source.

## Verification Evidence

- `.planning/verification/20260707155145-optimize-devflow-agents-drift-review.md`
