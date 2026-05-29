## ADDED Requirements

### Requirement: Hook Event Ingestion
Context Fixer SHALL ingest explicitly supplied sanitized hook event JSONL as
runtime evidence.

#### Scenario: Supplied hook event JSONL contributes to session growth
- **WHEN** `context-fixer audit --project <repo> --session-only --hook-events hooks/events.jsonl` is run
- **THEN** sanitized hook input and output sizes appear in session growth,
  budget categories, and capability activity
- **AND** raw hook payload bodies do not appear in text, Markdown, JSON, HTML,
  or Web dashboard reports

#### Scenario: Default hook cache is not silently treated as source of truth
- **WHEN** no `--hook-events` path is supplied and no managed collection run
  produced hook records
- **THEN** the audit reports hook collector availability as configuration
  evidence only
- **AND** it does not ingest unrelated cached records from other repositories

#### Scenario: External hook records require explicit override
- **WHEN** a hook event record has a `cwd` outside the audited repository
- **THEN** the parser ignores the record by default
- **AND** the record is included only when the user passes
  `--include-external-hook-events`

#### Scenario: Malformed hook records are tolerated
- **WHEN** the hook event JSONL contains malformed lines or unknown fields
- **THEN** Context Fixer skips malformed records, reports parser findings, and
  continues analyzing valid records
