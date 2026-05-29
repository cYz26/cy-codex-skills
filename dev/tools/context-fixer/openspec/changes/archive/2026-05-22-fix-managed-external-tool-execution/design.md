## Context

Context Fixer intentionally does not vendor or install external tools itself.
However, project-local tools are a normal setup pattern for local-first
diagnostics. The managed runner should use these tools automatically when they
are already present in the target project.

## Decisions

### Project-Local Tool Discovery

Tool discovery checks PATH first, then common project-local bin directories:

- `.context-fixer/tools/bin`
- `.context-fixer/tools/node_modules/.bin`
- `.context-fixer/claude-tap-venv/bin`
- `.venv/bin`

The status output includes the discovered executable path and whether it came
from PATH or a project-local bin.

### Claude-Tap Handling

`claude-tap` is a capture wrapper, not a one-shot JSONL exporter. In managed
collection:

- If `--trace` was supplied, the runner marks claude-tap as `reused` and records
  the supplied trace artifact.
- If no trace was supplied but claude-tap is available, the runner probes it with
  `--version` and reports it as `ok` without creating a trace artifact.
- Unsupported flags are not used.

## Verification

- Add tests for project-local discovery.
- Add tests for supplied trace reuse.
- Add tests for claude-tap probing without writing fake trace artifacts.
- Run full unit tests, py_compile, OpenSpec validation, and a real
  `app_ai_doctor` full collect.
