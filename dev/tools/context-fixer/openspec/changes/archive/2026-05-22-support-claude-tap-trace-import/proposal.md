## Why

Context Fixer can already analyze a generic request trace, but Codex users often
capture real request traffic with claude-tap. Those traces include Codex-specific
Responses API shapes, WebSocket metadata, and reconstructed request/response
bodies that the current parser only partially understands.

## What Changes

- Add first-class import support for Codex claude-tap trace JSONL files passed
  through the existing `--trace` option.
- Attribute Codex Responses request components including `instructions`,
  `input`, `tools`, and tool result items without printing sensitive bodies.
- Read exact usage from reconstructed response bodies and common claude-tap
  event fields when present.
- Surface trace format and transport metadata in structured report data.
- Keep Context Fixer independent from claude-tap at runtime; no proxy capture,
  tap process management, or production dependency is added.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `current-system`: optional request trace attribution expands to support
  Codex-focused claude-tap JSONL traces while preserving explicit file input and
  sanitized reporting.

## Impact

- Affected code: `src/context_fixer/trace.py`, `src/context_fixer/analyzer.py`,
  renderers if needed for new metadata, and tests.
- Affected CLI: existing `--trace` behavior gains Codex claude-tap compatibility
  without new flags.
- Dependencies: no production dependency on claude-tap.
- Security/privacy: reports must continue omitting prompt bodies, headers,
  request bodies, tool result bodies, and authorization values.
