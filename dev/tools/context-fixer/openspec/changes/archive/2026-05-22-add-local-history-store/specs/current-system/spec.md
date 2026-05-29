## ADDED Requirements

### Requirement: Local History Store
Context Fixer SHALL persist sanitized audit snapshots in a local SQLite store
when explicitly requested.

#### Scenario: Audit snapshots can be saved locally
- **WHEN** `context-fixer audit --project <repo> --session-only --save --store <db>` is run
- **THEN** a sanitized audit snapshot is persisted in the local SQLite store
- **AND** prompt, message, tool argument, command output, file, and trace
  payload bodies are not stored

#### Scenario: History can be queried
- **WHEN** `context-fixer history --project <repo> --store <db> --format json` is run
- **THEN** saved audit snapshots are listed with timestamp, severity, policy
  status, source-of-truth, peak context, and top offender summary fields

#### Scenario: Snapshot can be loaded
- **WHEN** `context-fixer history show <snapshot-id> --store <db>` is run
- **THEN** the sanitized report for that snapshot is returned in the requested
  format

#### Scenario: Store is initialized safely
- **WHEN** the requested SQLite store does not exist
- **THEN** Context Fixer creates it with the current schema version and parent
  directories as needed

#### Scenario: Persistence is explicit
- **WHEN** the user runs `audit` or `report` without `--save`
- **THEN** Context Fixer does not write a history snapshot unless a managed
  collection profile explicitly enables persistence
