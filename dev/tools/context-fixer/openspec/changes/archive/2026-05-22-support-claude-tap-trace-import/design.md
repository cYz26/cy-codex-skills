## Context

Context Fixer currently parses generic request/response JSONL passed through
`--trace`. The parser understands top-level `request.body`, `response.body`,
`input`, `messages`, `tools`, `functions`, and common `usage` fields. It does
not explicitly identify claude-tap trace records or Codex Responses-specific
request shapes.

The target integration is Codex only. claude-tap remains responsible for running
as a local proxy and recording API traffic. Context Fixer remains a read-only
analyzer of already captured trace files.

## Goals / Non-Goals

**Goals:**

- Recognize Codex claude-tap JSONL records without a new CLI flag.
- Attribute Codex Responses `instructions`, `input`, `tools`, and tool result
  items as sanitized contributors.
- Extract exact usage from response bodies and trace-level usage fields.
- Report trace format and transport metadata in JSON/HTML-safe structured data.
- Preserve existing generic trace behavior.

**Non-Goals:**

- Do not run, install, vendor, or manage claude-tap.
- Do not implement proxy, forward proxy, TLS/CA, SSE relay, or WebSocket relay
  behavior.
- Do not support non-Codex provider schemas in this change.
- Do not print prompt, message, tool result, header, or body contents.

## Decisions

1. **Keep `--trace` as the integration point.**
   - Rationale: Context Fixer already treats request traces as explicit
     user-supplied evidence. Adding a new capture command would alter product
     boundaries and security posture.
   - Alternative considered: add `context-fixer capture`. Deferred because it
     would imply runtime process management and dependency discovery.

2. **Add Codex-aware normalization inside `trace.py`.**
   - Rationale: the current trace parser is already the single place that turns
     sensitive request bodies into safe contributor summaries. Normalization can
     happen before attribution without leaking contents.
   - Alternative considered: add a separate `claude_tap.py` module. Deferred
     until the parser needs broader provider support.

3. **Represent trace format as metadata, not as a new source of truth.**
   - Rationale: exact usage remains exact only when a `usage` object is present.
     Format detection helps users understand evidence quality but should not
     inflate precision by itself.

4. **Codex-only scope.**
   - Rationale: Codex Responses traces include enough distinct structure
     (`instructions`, typed `input` items, Responses tool result items,
     WebSocket transport metadata) to justify focused support. General
     multi-provider normalization can be planned later.

## Risks / Trade-offs

- **Risk: claude-tap schema shifts.** Mitigation: parse tolerant field names
  (`duration_ms`/`latency_ms`, `request.body`, top-level `usage`,
  `response.body.usage`) and keep missing fields non-fatal.
- **Risk: sensitive body leakage.** Mitigation: all contributors store labels,
  sizes, counts, and metadata only; renderers continue using sanitized report
  data.
- **Risk: WebSocket traces may contain only raw event arrays.** Mitigation:
  support reconstructed bodies now and count event array size as transport
  metadata only when no reconstructed body is available.
- **Risk: users expect Context Fixer to capture traffic.** Mitigation: docs state
  claude-tap capture remains external and optional.
