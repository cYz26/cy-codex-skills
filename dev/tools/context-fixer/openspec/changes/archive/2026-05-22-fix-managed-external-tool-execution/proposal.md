## Why

Real-project testing against `app_ai_doctor` showed that managed external tool
execution was not fully usable:

- `tools doctor` did not discover project-local executables such as
  `.context-fixer/claude-tap-venv/bin/claude-tap`.
- `collect --profile full` invoked claude-tap with an unsupported `--jsonl`
  argument, causing the tool to fail even when installed.

The formal flow should discover project-local tools and reuse explicitly supplied
trace artifacts instead of requiring users to manually export PATH or rerun
capture tools.

## What Changes

- Discover project-local tool bins under `.context-fixer/tools/bin`,
  `.context-fixer/tools/node_modules/.bin`, `.context-fixer/claude-tap-venv/bin`,
  and `.venv/bin` in addition to global PATH.
- Make trace-enabled collection reuse explicit `--trace` artifacts for
  claude-tap.
- Probe claude-tap with a supported command when no supplied trace is present,
  without writing version output as a trace artifact.
- Keep tool stdout/stderr bodies out of reports.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `current-system`: managed external tool collection and doctor behavior.

## Impact

- Affected code: `src/context_fixer/tools.py`, `src/context_fixer/cli.py`.
- Affected tests: `tests/test_context_fixer.py`.
- Dependencies: no new Context Fixer production dependencies.
