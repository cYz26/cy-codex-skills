## 1. Characterize Codex claude-tap Trace Behavior

- [x] 1.1 Add a failing unit test fixture for a Codex claude-tap WebSocket trace with reconstructed Responses request/response bodies.
- [x] 1.2 Add assertions that trace metadata reports `claude-tap-codex`, preserves WebSocket transport, and uses exact response usage.
- [x] 1.3 Add assertions that sanitized contributors include Codex instructions, request messages, tool definitions, and tool results without leaking secret bodies or authorization values.

## 2. Implement Codex Trace Import

- [x] 2.1 Extend `TraceStats` with sanitized trace metadata fields for trace format, transport, upstream base URL, request path, and request method.
- [x] 2.2 Update trace parsing to detect Codex claude-tap records from `client`, `transport`, Codex upstream paths, or Responses request shape.
- [x] 2.3 Add Codex Responses attribution for `instructions`, typed `input` items, `tools`/`functions`, and tool-result item variants.
- [x] 2.4 Preserve existing generic request trace behavior and exact usage extraction.

## 3. Documentation and Verification

- [x] 3.1 Update README trace guidance with Codex claude-tap import examples and the no-bundled-capture boundary.
- [x] 3.2 Run the focused test suite for trace behavior.
- [x] 3.3 Run the full unit suite.
- [x] 3.4 Validate the OpenSpec change and update task checkboxes with evidence.
