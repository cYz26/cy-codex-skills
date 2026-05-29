## ADDED Requirements

### Requirement: First-Run Dependency Guidance

Context Fixer SHALL provide optional Codex request trace dependency guidance on
the first explicit session-only CLI run for a repository when no trace file is
supplied, and SHALL NOT require or install claude-tap to complete the audit.

#### Scenario: First session-only run without trace and claude-tap missing
- **WHEN** the user runs `context_fixer --repo <repo> --session-only` for a
  repository that has not previously seen dependency guidance
- **AND** no `--trace` file is supplied
- **AND** `claude-tap` is not available on `PATH`
- **THEN** the report includes a recommendation explaining that claude-tap is an
  optional Codex trace capture dependency and includes an installation command

#### Scenario: First session-only run without trace and claude-tap installed
- **WHEN** the user runs `context_fixer --repo <repo> --session-only` for a
  repository that has not previously seen dependency guidance
- **AND** no `--trace` file is supplied
- **AND** `claude-tap` is available on `PATH`
- **THEN** the report includes a recommendation explaining how to run
  `claude-tap --tap-client codex` and analyze the resulting trace with
  Context Fixer

#### Scenario: Subsequent run suppresses guidance
- **WHEN** the user runs `context_fixer --repo <repo> --session-only` after
  dependency guidance has already been shown for that repository
- **THEN** the report omits the first-run dependency guidance recommendation

#### Scenario: Trace supplied suppresses guidance
- **WHEN** the user runs `context_fixer --repo <repo> --trace <trace.jsonl>`
- **THEN** the report omits first-run dependency guidance because request trace
  evidence was already supplied

#### Scenario: Project files remain unmodified
- **WHEN** first-run dependency guidance is recorded
- **THEN** Context Fixer writes only to user-local cache state and does not
  create dependency guidance marker files inside the audited repository
