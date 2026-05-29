## Why

Context Fixer has accumulated useful evidence parsers and report views, but the
current implementation is organized around historical feature additions rather
than the Codex Context Lens requirements. This makes baseline budgeting,
session-growth attribution, turn-level deltas, request trace composition, top
offenders, and recommendations harder to reason about as one coherent local
first audit.

This change keeps the existing Python CLI, Context Fixer product name, sanitized
reporting posture, and `codex-context-lens` compatibility path while refactoring
the analyzer around the requirements and technical solution documents supplied
on 2026-05-21.

## What Changes

- Reorganize attribution into explicit baseline, session growth, turn delta,
  request trace, top offender, and recommendation sections.
- Preserve current CLI behavior and add report fields that match the Codex
  Context Lens MVP vocabulary without changing the package language or public
  product name.
- Improve static baseline scanning so AGENTS files, skill metadata, Codex
  config, MCP inventory, hooks, planning, and OpenSpec signals are reported with
  clearer source types and risk signals.
- Improve session JSONL attribution so user/assistant messages, tool arguments,
  tool outputs, bash output, file reads, patch/diff content, web/search output,
  and token telemetry are classified into stable categories.
- Improve request trace attribution so supplied traces report sanitized request
  composition for instructions/system-like content, messages, tool definitions,
  tool results, usage, and request metadata.
- Generate recommendations from the budget model, including AGENTS slimming,
  skill locality, MCP/profile governance, command-output limiting, trace setup,
  compact/checkpoint timing, and repeated-diff/file-read reduction.
- Keep reports local-first and sanitized; prompt bodies, message bodies, tool
  arguments, command output, and trace payloads remain omitted.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `current-system`: refine the accepted Context Fixer behavior to require
  explicit Context Lens MVP sections for baseline budget, session growth, turn
  deltas, request composition, top offenders, and recommendations while
  preserving existing local-first, sanitized, Python CLI behavior.

## Impact

- Affected code: `src/context_fixer/analyzer.py`,
  `src/context_fixer/session.py`, `src/context_fixer/static_sources.py`,
  `src/context_fixer/trace.py`, `src/context_fixer/render.py`,
  `src/context_fixer/cli.py`, compatibility modules under
  `src/codex_context_lens/`, and `tests/test_context_fixer.py`.
- Affected docs: `README.md`, OpenSpec artifacts for this change, and workflow
  state/checkpoint files as required by the repository process.
- Public CLI: no breaking changes planned. Existing entry points and flags remain
  supported.
- Dependencies: no new production dependency planned.
- Data handling: no remote upload, no automatic trace capture, no automatic
  mutation of user Codex/project configuration.
