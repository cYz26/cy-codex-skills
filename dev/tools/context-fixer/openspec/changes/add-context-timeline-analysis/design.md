## Context

Context Fixer currently parses session JSONL and request traces into aggregate statistics and contributors. This is enough for a dashboard snapshot, but it obscures chronology: interrupted probe sessions can distort "latest" fields, while historical peaks and compactions remain hard to explain from the report alone.

The new behavior must remain local-first and sanitized. Prompt bodies, tool arguments, tool outputs, trace payload bodies, and auth headers must not be printed.

## Goals / Non-Goals

**Goals:**

- Produce a chronological report section that explains context growth over time.
- Identify peak usage events, latest valid usage events, large growth jumps, compaction events, request trace events, and abnormal zero-token/incomplete sessions.
- Make timeline data available in JSON and visible in text/HTML reports.
- Keep analysis deterministic and dependency-free.

**Non-Goals:**

- Do not capture traffic directly; request trace capture remains external.
- Do not replay full conversations or expose raw prompt/tool content.
- Do not build an interactive session browser.
- Do not change session discovery semantics beyond interpreting discovered sessions chronologically.

## Decisions

1. Add sanitized event summaries to parsed stats.

   `SessionStats` will expose `timeline_events` records for token counts, compactions, and session anomalies. `TraceStats` will expose request events with method/path/model/status/latency and whether exact usage was found. These events contain timestamps, paths, numeric telemetry, labels, and status flags only.

2. Build a top-level `timeline` object in `analyze_context()`.

   The analyzer will merge session and trace events, sort them by timestamp/path order, and derive:

   - `events`: bounded chronological event list.
   - `peak_event`: event that produced max input tokens.
   - `latest_valid_usage_event`: most recent token event with non-zero usage.
   - `growth_events`: largest token jumps within each session.
   - `compaction_events`: compact markers with surrounding context when available.
   - `anomalies`: zero-token or incomplete sessions/traces.

3. Separate "latest raw" from "latest valid".

   Existing diagnosis fields remain compatible, but diagnosis will gain `latest_valid_input_tokens`, `latest_valid_total_tokens`, and `latest_valid_source`. Recommendations can warn when the raw latest event is zero or incomplete while the latest valid event is earlier.

4. Render concise timeline evidence.

   Text output will include a short "Timeline" section. HTML will add a timeline panel with peak, latest valid usage, compactions, and anomalies. JSON will carry the full sanitized structure for downstream tooling.

## Risks / Trade-offs

- [Risk] Codex session JSONL schemas can vary. → Mitigation: tolerate missing timestamps and fall back to file mtime/path order.
- [Risk] Timeline aggregation can grow large on long histories. → Mitigation: cap rendered event lists while preserving summary counts and key derived events.
- [Risk] Request trace exact usage may be missing for custom providers. → Mitigation: mark trace precision and include request events separately from usage conclusions.
- [Risk] Existing consumers may assume only current top-level keys. → Mitigation: add fields without removing existing report keys.
