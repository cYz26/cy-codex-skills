## Why

The complete product should orchestrate declared external tools instead of
asking users to manually run abtop, claude-tap, ccusage, RTK, and OTel steps one
by one. A single Context Fixer collection command should check availability,
start or invoke configured tools, collect artifacts, import them, and report
tool health.

## What Changes

- Add a managed external tool registry and runner.
- Add `collect` profiles: `quick`, `monitor`, `trace`, and `full`.
- Add `tools list` and `tools doctor` commands.
- Automatically invoke supported one-shot exporters and managed collectors
  within a user-selected profile.
- Preserve manual `trace import`, `usage import`, and `otel import` commands as
  advanced/debug flows.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `current-system`: add managed external tool orchestration and tool status
  reporting to the local-first workflow.

## Impact

- Affected code: `src/context_fixer/tools.py`,
  `src/context_fixer/adapters.py`, `src/context_fixer/cli.py`,
  `src/context_fixer/analyzer.py`, renderers, and tests.
- Public CLI: additive `collect`, `tools list`, `tools doctor`,
  `usage import`, and `otel import`.
- Dependencies: uses Python standard library process management. External
  tools are optional runtime executables discovered on PATH.
- Privacy: stdout/stderr and captured artifacts are summarized by size, hash,
  status, and imported sanitized evidence. Raw bodies are not rendered.
