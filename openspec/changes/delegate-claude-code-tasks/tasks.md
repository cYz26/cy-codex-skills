## 1. Capability Evidence and Test Contract

- [x] 1.1 Record local Claude Code evidence in `openspec/changes/delegate-claude-code-tasks/design.md`: executable path, version, relevant CLI flags, local scan, and JSON error-shape probe.
- [x] 1.2 Add focused failing tests in `dev/plugins/dev-flow/tests/test_claude_delegate.py` for missing executable detection, plan-mode command construction, apply-mode dirty-worktree blocking, apply-mode invocation after explicit override, Claude JSON result normalization, Claude non-JSON failure normalization, and metadata logging.
- [x] 1.3 Run `python3 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_claude_delegate.py'` and confirm the new tests fail because implementation does not exist yet.

## 2. Development Plugin Implementation

- [x] 2.1 Add `dev/plugins/dev-flow/scripts/workflow_claude_delegate.py` with a focused API for resolving `claude`, reading version output, checking Git dirty state, building safe command arguments, invoking Claude Code, normalizing output, and writing lightweight run metadata.
- [x] 2.2 Add `dev/plugins/dev-flow/scripts/claude_code_delegate.py` as the CLI facade with arguments for `--repo`, `--task`, `--task-file`, `--apply`, `--allow-dirty`, `--max-budget-usd`, `--model`, `--effort`, `--add-dir`, `--allowed-tool`, `--check`, `--no-log`, and `--json`.
- [x] 2.3 Ensure plan mode is the default and apply mode is explicit, with apply mode blocked on dirty Git state unless `--allow-dirty` is passed.
- [x] 2.4 Ensure normalized JSON handles success JSON, Claude-reported error JSON such as `error_max_budget_usd`, process failures, and non-JSON output.
- [x] 2.5 Ensure metadata written under `.dev-flow/claude-code/runs/` does not store the full task prompt by default.
- [x] 2.6 Run `python3 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_claude_delegate.py'` and confirm the focused tests pass.

## 3. Skill, Documentation, and Release Packaging

- [x] 3.1 Add `dev/plugins/dev-flow/skills/claude-code-delegate/SKILL.md` explaining when Codex may delegate to Claude Code, the plan-first default, apply-mode safety gates, diff review, and verification requirements.
- [x] 3.2 Update `dev/plugins/dev-flow/README.md` with delegation usage examples for capability check, plan-only delegation, and guarded apply-mode delegation.
- [x] 3.3 Sync the implementation, skill, tests, and docs to `plugins/dev-flow/`.
- [x] 3.4 Update release smoke coverage so the packaged plugin includes the delegation skill and callable wrapper module.
- [x] 3.5 Run `python3 -m unittest discover -s plugins/dev-flow/tests` and confirm release-copy coverage passes.

## 4. Verification and Workflow State

- [x] 4.1 Run `python3 -m unittest discover -s dev/plugins/dev-flow/tests`.
- [x] 4.2 Run `python3 -m unittest discover -s plugins/dev-flow/tests`.
- [x] 4.3 Run `openspec validate --all --strict`.
- [x] 4.4 Run `python3 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo /Users/cy/Dev/agents-dev/cy-codex-skills --json`.
- [x] 4.5 Record verification evidence under `.planning/verification/`.
- [x] 4.6 Update this task ledger and `.planning/STATE.md` only after validation evidence supports the update.
