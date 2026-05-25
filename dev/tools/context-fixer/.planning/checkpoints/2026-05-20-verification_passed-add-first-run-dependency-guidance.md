---
checkpoint_id: 2026-05-20-verification_passed-add-first-run-dependency-guidance
created_at: 2026-05-20T18:25:18+08:00
boundary: verification_passed
project_mode: brownfield
phase_id: 01-foundation
change_id: add-first-run-dependency-guidance
compact_recommended: true
compact_status: pending
next_stage: archive-review
---

# Checkpoint: verification passed for add-first-run-dependency-guidance

## Current goal

Add one-time dependency guidance so a repository's first Context Fixer CLI run
can explain optional Codex request trace setup with claude-tap.

## Completed work

- Created OpenSpec change `add-first-run-dependency-guidance`.
- Added CLI tests for missing claude-tap guidance, installed claude-tap guidance,
  second-run suppression, trace-supplied suppression, and no project marker file.
- Added `src/context_fixer/onboarding.py` for user-cache-backed first-run state.
- Updated `src/context_fixer/cli.py` to append onboarding recommendations only
  for CLI-generated reports.
- Updated `README.md` with first-run guidance and cache boundary.
- Updated OpenSpec task checkboxes and `.planning/STATE.md`.

## Durable context written

- AGENTS.md
- .planning/STATE.md
- .planning/phases/01-foundation/PLAN.md
- .planning/phases/01-foundation/SUMMARY.md
- .planning/phases/01-foundation/VERIFICATION.md
- openspec/changes/add-first-run-dependency-guidance/proposal.md
- openspec/changes/add-first-run-dependency-guidance/design.md
- openspec/changes/add-first-run-dependency-guidance/tasks.md

## Key decisions

- The audited repository remains read-only for onboarding state.
- `CONTEXT_FIXER_CACHE_HOME` is supported for tests and custom cache placement.
- `analyze_context()` remains stateless; first-run guidance is CLI-only.
- claude-tap remains optional and externally installed.

## Open questions

- No open questions recorded.

## Risks

- Users can clear the cache and see first-run guidance again.
- The install command assumes `uv`; users without uv may need their preferred
  Python tool installer.

## Validation performed

```text
command: PYTHONPATH=src /opt/homebrew/bin/python3.11 -m unittest tests.test_context_fixer.ContextFixerTests.test_cli_first_run_recommends_optional_claude_tap_install_once tests.test_context_fixer.ContextFixerTests.test_cli_first_run_recommends_capture_when_claude_tap_is_installed tests.test_context_fixer.ContextFixerTests.test_cli_suppresses_first_run_guidance_when_trace_is_supplied -v
result: passed, 3 tests
command: PYTHONPATH=src /opt/homebrew/bin/python3.11 -m unittest discover -s tests -v
result: passed, 11 tests
command: openspec validate "add-first-run-dependency-guidance" --strict
result: passed, change valid
command: openspec validate "support-claude-tap-trace-import" --strict
result: passed, change valid
notes: Onboarding state is stored under user cache in tests and does not create `.context-fixer` inside the audited repository.
```

## Git state

```text
branch: codex/add-project-orchestrator-plugin
changed_files:
  - M ../../../.agents/plugins/marketplace.json
  -  M ../../../.gitignore
  -  M ../../../README.md
  -  M ../../plugins/README.md
  -  M ../../plugins/codex-project-orchestrator/README.md
  -  M ../../plugins/codex-project-orchestrator/scripts/codex_plugin_preflight.py
  -  M ../../plugins/codex-project-orchestrator/scripts/plugin_preflight_runner.py
  -  M ../../plugins/codex-project-orchestrator/scripts/workflow_dependency_catalog.py
  -  M ../../plugins/codex-project-orchestrator/scripts/workflow_lib.py
  -  M ../../plugins/codex-project-orchestrator/skills/project-orchestrator/SKILL.md
  -  M ../../plugins/codex-project-orchestrator/skills/project-setup/SKILL.md
  -  M ../../plugins/codex-project-orchestrator/tests/dependency_support.py
  -  M ../../plugins/codex-project-orchestrator/tests/test_dependencies.py
  -  M ../../plugins/codex-project-orchestrator/tests/test_project_orchestrator.py
  - ?? ../../../.agents/plugins/marketplace.dev.json
  - ?? ../../log/
  - ?? ../../plugins/codex-project-orchestrator/.planning/
  - ?? ../../plugins/codex-project-orchestrator/docs/
  - ?? ../../plugins/codex-project-orchestrator/fixtures/greenfield-empty/
  - ?? ../../plugins/codex-project-orchestrator/openspec/
  - ?? ../../plugins/codex-project-orchestrator/scripts/apply_context_tool_actions.py
  - ?? ../../plugins/codex-project-orchestrator/scripts/audit_context_tools.py
  - ?? ../../plugins/codex-project-orchestrator/scripts/workflow_context_tools.py
  - ?? ../../plugins/codex-project-orchestrator/skills/context-tool-audit/
  - ?? ../../plugins/codex-project-orchestrator/tests/test_context_tools.py
  - ?? ../../skills/
  - ?? ../
  - ?? ../../../docs/
  - ?? ../../../plugins/codex-project-orchestrator/
```

## Next action

The next stage should start by reading:

1. `AGENTS.md`
2. `.planning/STATE.md`
3. this checkpoint file
4. relevant OpenSpec change files
5. relevant phase plan files

Then proceed to: `archive-review`.

## Compact instruction

Checkpoint is complete. Run `/compact` before continuing if using Codex CLI.
If compaction is unavailable, start a new session and provide this checkpoint file as the handoff context.
