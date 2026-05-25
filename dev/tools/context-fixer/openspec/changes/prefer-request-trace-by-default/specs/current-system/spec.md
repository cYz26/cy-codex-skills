## MODIFIED Requirements

### Requirement: Optional Request Trace Attribution

Context Fixer SHALL treat request trace evidence as an explicit user-supplied
input and SHALL NOT provide proxy or tap capture behavior as part of this
baseline. When a supplied trace is a Codex claude-tap JSONL trace, Context Fixer
SHALL identify the trace format, preserve transport metadata, and include
Codex Responses request-shape attribution in the sanitized report. For CLI
report generation, Context Fixer SHALL prefer request trace evidence by default
and SHALL require explicit `--session-only` confirmation before producing a
session-log-only report.

#### Scenario: Analyze supplied trace file
- **WHEN** the user runs `context_fixer --repo <repo> --trace <trace.jsonl>`
- **THEN** the system combines request usage and request shape attribution with
  session and static-source evidence

#### Scenario: Analyze Codex claude-tap trace file
- **WHEN** the user runs `context_fixer --repo <repo> --trace <trace.jsonl>` and
  the trace contains Codex claude-tap records with Responses request and
  response bodies
- **THEN** the system reports request trace availability as enabled, marks the
  trace format as `claude-tap-codex`, extracts exact usage when present, and
  includes sanitized contributors for Codex instructions, request messages, tool
  definitions, and tool results

#### Scenario: No trace file and no session-only confirmation
- **WHEN** the user runs `context_fixer --repo <repo>` without `--trace` and
  without `--session-only`
- **THEN** the system prints Codex request trace setup guidance and exits without
  rendering a normal audit report

#### Scenario: Explicit session-only analysis
- **WHEN** the user runs `context_fixer --repo <repo> --session-only`
- **THEN** the system reports request trace availability as absent and continues
  using session and static-source evidence
