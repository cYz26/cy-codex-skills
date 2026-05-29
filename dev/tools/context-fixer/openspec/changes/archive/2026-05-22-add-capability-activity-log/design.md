## Context

Context Fixer already detects static plugin/skill/MCP inventory and estimates contributors from session tool arguments and outputs. Timeline analysis also shows when token pressure changes. The missing layer is an explicit capability activity view: what tools were called, what request-level capabilities were available, and what plugin/connector/MCP network paths appeared.

The report must remain sanitized and local-first. It must not infer that a configured plugin or skill was used unless a session or trace event shows an observed call.

## Goals / Non-Goals

**Goals:**

- Expose observed session tool calls and tool results in a structured `activity` section.
- Expose request trace network activity categories and request tool inventories.
- Expose enabled plugin/skill/MCP inventory beside observed activity with clear labels.
- Render the same information in text and HTML.

**Non-Goals:**

- Do not print tool arguments, outputs, prompts, chat messages, or auth headers.
- Do not claim exact skill invocation when Codex session logs only expose generic tool calls or static skill metadata.
- Do not implement live capture or an interactive activity browser.

## Decisions

1. Add parser-level activity events.

   `SessionStats` will collect sanitized `activity_events` for dynamic tool availability, function/custom/tool-search/web-search calls, and matching tool results. Events include tool name, call type, timestamp/path/order, and estimated token sizes only.

   `TraceStats` will collect sanitized `activity_events` for network request categories and request tool inventories. Categories are derived from request paths, such as `model_request`, `mcp`, `plugin_registry`, `connector_directory`, `auth`, `analytics`, and `repository`.

2. Add analyzer-level `activity`.

   The analyzer will aggregate parser events into:

   - `summary`: counts of observed calls, results, request activity, request tool definitions, and configured inventory counts.
   - `observed_calls`: per-tool call counts and estimated argument/output size.
   - `request_activity`: categorized request trace events.
   - `available_tools`: request/session tool inventories.
   - `activation_inventory`: enabled global plugins, global/project skills, and MCP server keys.
   - `events`: bounded sanitized chronological activity events.

3. Keep distinction explicit.

   Renderers will label inventory as configured/available, and observed calls as observed. This prevents conflating "plugin enabled" with "plugin invoked."

## Risks / Trade-offs

- [Risk] Session logs may not expose plugin or skill activation as first-class events. → Mitigation: report inventory and observed tool calls separately, and avoid overclaiming.
- [Risk] Trace paths may include query parameters with secrets. → Mitigation: reuse sanitized path extraction that strips query strings.
- [Risk] Long sessions can produce many tool events. → Mitigation: cap rendered events while preserving aggregate counts.
