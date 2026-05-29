## 1. Timeline Data Model

- [x] 1.1 Add sanitized session timeline events for token usage, compaction, and zero-usage anomalies.
- [x] 1.2 Add sanitized request trace timeline events with method/path/model/status/latency and exact usage flags.
- [x] 1.3 Build analyzer-level merged timeline summaries with peak event, latest valid usage event, growth jumps, compactions, and anomalies.

## 2. Reporting

- [x] 2.1 Add diagnosis fields that distinguish latest raw state from latest valid non-zero usage.
- [x] 2.2 Render concise timeline summaries in text output.
- [x] 2.3 Render a timeline panel in HTML output.
- [x] 2.4 Keep JSON, text, and HTML timeline output sanitized.

## 3. Verification

- [x] 3.1 Add tests for historical compactions, misleading latest zero-usage sessions, growth jumps, and request trace timeline events.
- [x] 3.2 Run unit tests and strict OpenSpec validation.
- [x] 3.3 Update planning state and create a verification checkpoint.
