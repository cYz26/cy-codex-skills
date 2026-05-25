## Why

Users need to see not only token totals but also which capabilities were active or invoked during a conversation. Existing reports show plugin/skill inventory and tool-output contributors, but they do not present an explicit chronological or aggregated record of tool calls, request tools, MCP/plugin network activity, and enabled capability inventory.

## What Changes

- Add a sanitized `activity` report section for observed capability usage and enabled capability inventory.
- Record observed session tool calls and tool results by name, count, timestamp, and estimated argument/output size without printing bodies.
- Record request trace activity such as model requests, MCP requests, plugin registry calls, connector directory calls, auth calls, and request tool inventories.
- Render capability activity in text and HTML reports.
- Preserve a clear distinction between observed calls and configured/available plugins, skills, and MCP servers.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `current-system`: Add sanitized capability activity reporting to existing context analysis outputs.

## Impact

- Affected code: `src/context_fixer/session.py`, `src/context_fixer/trace.py`, `src/context_fixer/analyzer.py`, `src/context_fixer/render.py`, tests, and README.
- Affected APIs: JSON report gains a top-level `activity` object.
- Dependencies: no new production dependency.
