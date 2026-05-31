## 1. Baseline and Regression Tests

- [x] 1.1 Preserve the Plugin Eval baseline JSON and improvement brief under `.planning/verification/`.
- [x] 1.2 Add failing release smoke coverage for explicit-only skill policy and core routing skill policy.
- [x] 1.3 Add failing release smoke coverage that scans release Python files for lines over 120 characters.
- [x] 1.4 Run `python3 -m unittest plugins/dev-flow/tests/test_release_smoke.py` and confirm the new policy/readability tests fail before implementation.

## 2. Policy and Readability Implementation

- [x] 2.1 Add `agents/openai.yaml` with `policy.allow_implicit_invocation: false` to low-frequency skills in `plugins/dev-flow/skills/`.
- [x] 2.2 Sync the same explicit-only policy files to `dev/plugins/dev-flow/skills/`.
- [x] 2.3 Fix scoped Python long lines in both `plugins/dev-flow/` and `dev/plugins/dev-flow/`.
- [x] 2.4 Remove generated `__pycache__` directories from both plugin trees.
- [x] 2.5 Run `python3 -m unittest plugins/dev-flow/tests/test_release_smoke.py` and confirm focused tests pass.

## 3. Verification and Evaluation

- [x] 3.1 Run `python3 -m unittest discover -s plugins/dev-flow/tests`.
- [x] 3.2 Run `python3 -m unittest discover -s dev/plugins/dev-flow/tests`.
- [x] 3.3 Run `openspec validate --all --strict`.
- [x] 3.4 Run `python3 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo /Users/cy/Dev/agents-dev/cy-codex-skills --json`.
- [x] 3.5 Run Plugin Eval after the optimization and write JSON output under `.planning/verification/`.
- [x] 3.6 Compare before/after Plugin Eval budget and score results.
- [x] 3.7 Record verification evidence and update `.planning/STATE.md`.
